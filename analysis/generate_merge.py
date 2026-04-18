#!/usr/bin/env python3
"""
generate_merge.py — India Credit Lens
---------------------------------------
Merges multiple per-period sections.json files into a single
sections_merged.json with a continuous time-series across all periods.

Merge rules:
  - All periods are combined at the DATA level (absoluteData rows)
  - Date labels are deduplicated: if the same month appears in multiple
    period files, the LATEST period file's value wins (it's the most
    authoritative revision)
  - growthData and fyData are RECOMPUTED from the merged absoluteData
    using the same YoY / FY-to-date logic as extract_sibc.py
  - The merged file's dataDate = latest period's dataDate

Usage:
    # Auto-discover all periods from analysis/rbi_sibc/timeline.json
    python3 generate_merge.py

    # Explicit period directories (processed in chronological order)
    python3 generate_merge.py \\
        analysis/rbi_sibc/2026-02-27 \\
        analysis/rbi_sibc/2026-03-28

    # Custom output location
    python3 generate_merge.py --out analysis/rbi_sibc/merged/sections_merged.json

Exit codes:
    0 = sections_merged.json written
    1 = error
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ── Repo paths ────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
ANALYSIS  = REPO_ROOT / "analysis"
TIMELINE  = ANALYSIS / "rbi_sibc" / "timeline.json"


# ── Date helpers ──────────────────────────────────────────────────────────────

MONTH_ORDER = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,  "May": 5,  "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

def display_to_sortkey(label: str) -> tuple:
    """'Jan 2024' or 'Jan 2024*' → (2024, 1) for sorting."""
    parts = label.rstrip("*").strip().split()
    if len(parts) != 2:
        return (9999, 99)
    mon, year = parts[0], parts[1]
    return (int(year), MONTH_ORDER.get(mon, 99))


def display_to_date(label: str) -> datetime | None:
    """'Jan 2024' or 'Jan 2024*' → datetime(2024, 1, 1)"""
    label = label.rstrip("*").strip()
    parts = label.split()
    if len(parts) != 2:
        return None
    mon_num = MONTH_ORDER.get(parts[0])
    if mon_num is None:
        return None
    try:
        return datetime(int(parts[1]), mon_num, 1)
    except ValueError:
        return None


def same_month_prior_year(label: str, all_labels: list[str]) -> str | None:
    """'Jan 2025' → 'Jan 2024' if it exists in all_labels."""
    d = display_to_date(label)
    if d is None:
        return None
    target_year = d.year - 1
    target_mon  = d.month
    for lbl in all_labels:
        od = display_to_date(lbl)
        if od and od.year == target_year and od.month == target_mon:
            return lbl
    return None


def most_recent_march(label: str, all_labels: list[str]) -> str | None:
    """Find most recent March label that is ≤ label's date."""
    d = display_to_date(label)
    if d is None:
        return None
    candidates = []
    for lbl in all_labels:
        od = display_to_date(lbl)
        if od and od.month == 3 and od <= d:
            candidates.append((od, lbl))
    return max(candidates, key=lambda x: x[0])[1] if candidates else None


def compute_growth(cur, base) -> float | None:
    """(cur/base - 1) × 100, 1 dp. None if either is missing/zero."""
    if cur is None or base is None:
        return None
    try:
        cv, bv = float(cur), float(base)
        return round((cv / bv - 1) * 100, 1) if bv != 0 else None
    except (TypeError, ValueError):
        return None


# ── Merge logic ───────────────────────────────────────────────────────────────

def merge_sections(period_files: list[Path]) -> dict:
    """
    Load all sections.json files in chronological order and merge.
    Later files override earlier files for the same date label.
    """
    if not period_files:
        print("ERROR: No period files to merge.", file=sys.stderr)
        sys.exit(1)

    # Load all in order
    loaded = []
    latest_date = ""
    for pf in period_files:
        with open(pf) as f:
            data = json.load(f)
        loaded.append(data)
        if data.get("dataDate", "") > latest_date:
            latest_date = data["dataDate"]
        print(f"  Loaded: {pf}  (dataDate={data.get('dataDate')})")

    # Collect dateOverrides from all periods
    all_date_overrides = []
    seen_orig = set()
    for data in loaded:
        for rec in data.get("dateOverrides", []):
            key = rec.get("original_iso", "")
            if key and key not in seen_orig:
                seen_orig.add(key)
                all_date_overrides.append(rec)

    # Gather all section IDs in order from the first file
    section_ids = [s["id"] for s in loaded[0]["sections"]]

    merged_sections = []

    for sec_id in section_ids:
        # Collect all section blocks across periods
        sec_blocks = []
        for data in loaded:
            for sec in data["sections"]:
                if sec["id"] == sec_id:
                    sec_blocks.append(sec)
                    break

        if not sec_blocks:
            continue

        title       = sec_blocks[-1]["title"]
        series_names = sec_blocks[-1]["seriesNames"]

        # ── Merge absoluteData ────────────────────────────────────────────────
        # Key: date label → {series: value}. Later periods override earlier.
        abs_map: dict[str, dict] = {}
        for block in sec_blocks:
            for row in block.get("absoluteData", []):
                date_lbl = row["date"]
                if date_lbl not in abs_map:
                    abs_map[date_lbl] = {}
                for key, val in row.items():
                    if key != "date":
                        abs_map[date_lbl][key] = val

        # Sort by date
        sorted_labels = sorted(abs_map.keys(), key=display_to_sortkey)

        absolute_data = []
        for lbl in sorted_labels:
            row = {"date": lbl}
            for sn in series_names:
                row[sn] = abs_map[lbl].get(sn)
            absolute_data.append(row)

        # ── Recompute growthData (YoY) ────────────────────────────────────────
        growth_data = []
        for lbl in sorted_labels:
            prior = same_month_prior_year(lbl, sorted_labels)
            if prior is None:
                continue
            row = {"date": lbl}
            for sn in series_names:
                row[sn] = compute_growth(abs_map[lbl].get(sn), abs_map[prior].get(sn))
            growth_data.append(row)

        # ── Recompute fyData (FY-to-date from most recent March) ──────────────
        fy_data = []
        for lbl in sorted_labels:
            march = most_recent_march(lbl, sorted_labels)
            if march is None:
                continue
            if march == lbl:
                # The label IS a March date — FY growth = YoY growth
                prior = same_month_prior_year(lbl, sorted_labels)
                if prior is None:
                    continue
                row = {"date": lbl}
                for sn in series_names:
                    row[sn] = compute_growth(abs_map[lbl].get(sn), abs_map[prior].get(sn))
                fy_data.append(row)
            else:
                row = {"date": lbl}
                for sn in series_names:
                    row[sn] = compute_growth(abs_map[lbl].get(sn), abs_map[march].get(sn))
                fy_data.append(row)

        merged_sections.append({
            "id":           sec_id,
            "title":        title,
            "seriesNames":  series_names,
            "absoluteData": absolute_data,
            "growthData":   growth_data,
            "fyData":       fy_data,
        })

    return {
        "report":        "rbi_sibc",
        "dataDate":      latest_date,
        "merged":        True,
        "periods":       [str(pf) for pf in period_files],
        "sections":      merged_sections,
        "dateOverrides": all_date_overrides,
    }


# ── Auto-discover periods from timeline.json ──────────────────────────────────

def discover_periods() -> list[Path]:
    if not TIMELINE.exists():
        print(f"ERROR: timeline.json not found at {TIMELINE}", file=sys.stderr)
        sys.exit(1)
    with open(TIMELINE) as f:
        timeline = json.load(f)
    periods = []
    for entry in timeline.get("periods", []):
        date_str = entry.get("dataDate")
        if not date_str:
            continue
        p = ANALYSIS / "rbi_sibc" / date_str / "sections.json"
        if p.exists():
            periods.append(p)
        else:
            print(f"  [WARN] timeline entry {date_str}: sections.json not found at {p}")
    return sorted(periods)  # chronological by directory name


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Merge per-period sections.json → sections_merged.json")
    ap.add_argument(
        "period_dirs", nargs="*",
        help="Period directories (e.g. analysis/rbi_sibc/2026-02-27). "
             "If omitted, auto-discovers from timeline.json.",
    )
    ap.add_argument(
        "--out",
        default=str(ANALYSIS / "rbi_sibc" / "merged" / "sections_merged.json"),
        help="Output path (default: analysis/rbi_sibc/merged/sections_merged.json)",
    )
    args = ap.parse_args()

    # Resolve input files
    if args.period_dirs:
        period_files = []
        for d in args.period_dirs:
            p = Path(d) / "sections.json"
            if not p.exists():
                # Maybe they passed the file directly
                p = Path(d)
            if not p.exists():
                print(f"ERROR: Cannot find sections.json in {d}", file=sys.stderr)
                sys.exit(1)
            period_files.append(p)
        period_files = sorted(period_files)
    else:
        period_files = discover_periods()

    print(f"\n  Merging {len(period_files)} period(s):")
    merged = merge_sections(period_files)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(merged, f, indent=2)

    n_sections = len(merged["sections"])
    total_rows = sum(len(s["absoluteData"]) for s in merged["sections"])
    print(f"\n  ✅ Written : {out_path}")
    print(f"  Sections  : {n_sections}")
    print(f"  Data rows : {total_rows} total across all sections")
    print(f"  dataDate  : {merged['dataDate']}")

    # ── Post-merge validation ─────────────────────────────────────────────────
    # Auto-run validate_sections.py --merged to catch data integrity issues
    # immediately. Exits non-zero if validation fails so the caller knows the
    # merged file should not be used for downstream analysis.
    print(f"\n  Running post-merge validation (validate_sections.py --merged)...")
    val_cmd = [sys.executable, str(ANALYSIS / "validate_sections.py"),
               str(out_path), "--merged"]
    proc = subprocess.run(val_cmd, cwd=str(ANALYSIS), capture_output=True, text=True)
    # Print the last few lines of output (skip verbose per-section notes)
    output_lines = (proc.stdout + proc.stderr).strip().splitlines()
    summary_lines = [l for l in output_lines if any(
        kw in l for kw in ["PASSED", "FAILED", "ERROR", "WARNING", "✅", "❌", "⚠️"]
    )]
    for line in summary_lines[-6:]:
        print(f"  {line.strip()}")

    if proc.returncode != 0:
        print(f"\n  ❌ Post-merge validation FAILED — sections_merged.json has errors.")
        print(f"     Fix errors before running Stage 6 (Claude merged analysis).")
        sys.exit(1)
    else:
        print(f"  Post-merge validation passed — sections_merged.json is ready.")
