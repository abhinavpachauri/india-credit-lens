#!/usr/bin/env python3
"""
extract_sibc.py — India Credit Lens
--------------------------------------
Parses a raw SIBC .xlsx file and produces sections.json in the correct
period directory under analysis/rbi_sibc/{YYYY-MM-DD}/.

Calls rbi-analytics/parser.py for raw parsing, then maps sector codes
to the dashboard section structure.

All growth rates are computed from absolute outstanding data:
  YoY  = (current / same_month_prior_year  - 1) × 100
  FY   = (current / most_recent_march_base - 1) × 100

This makes the script independent of the yoy_pct/fy_pct columns in the
parser output (those are kept as a cross-check but not used as primary source).

Usage:
    python3 extract_sibc.py path/to/SIBC30032026.xlsx
    python3 extract_sibc.py path/to/SIBC30032026.xlsx --out-dir analysis/rbi_sibc/2026-03-28/
    python3 extract_sibc.py path/to/SIBC30032026.xlsx --dry-run

Exit codes:
    0 = sections.json written successfully
    1 = error (parse failure, missing data, etc.)
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# ── Repo paths ────────────────────────────────────────────────────────────────

REPO_ROOT     = Path(__file__).resolve().parent.parent
RBI_ANALYTICS = REPO_ROOT / "rbi-analytics"
ANALYSIS      = REPO_ROOT / "analysis"

sys.path.insert(0, str(RBI_ANALYTICS))

try:
    from parser import parse_file, parse_filename_date
except ImportError as e:
    print(f"ERROR: Cannot import parser.py from {RBI_ANALYTICS}: {e}", file=sys.stderr)
    sys.exit(1)


# ── Section definitions ───────────────────────────────────────────────────────
#
# Each tuple: (series_label, code, statement, is_priority_sector_memo)
# Rows are looked up by exact code match in the parsed DataFrame.

SECTION_DEFS = [
    {
        "id":    "bankCredit",
        "title": "Bank Credit",
        "series": [
            ("Bank Credit",     "I",   "Statement 1", False),
            ("Food Credit",     "II",  "Statement 1", False),
            ("Non-food Credit", "III", "Statement 1", False),
        ],
    },
    {
        "id":    "mainSectors",
        "title": "Main Sectors",
        "series": [
            ("Agriculture",   "1", "Statement 1", False),
            ("Industry",      "2", "Statement 1", False),
            ("Services",      "3", "Statement 1", False),
            ("Personal Loans","4", "Statement 1", False),
        ],
    },
    {
        "id":    "industryBySize",
        "title": "Industry by Size",
        "series": [
            ("Micro and Small", "2.1", "Statement 1", False),
            ("Medium",          "2.2", "Statement 1", False),
            ("Large",           "2.3", "Statement 1", False),
        ],
    },
    {
        "id":    "services",
        "title": "Services",
        "series": [
            ("Transport Operators",            "3.1",  "Statement 1", False),
            ("Computer Software",              "3.2",  "Statement 1", False),
            ("Tourism, Hotels & Restaurants",  "3.3",  "Statement 1", False),
            ("Shipping",                       "3.4",  "Statement 1", False),
            ("Aviation",                       "3.5",  "Statement 1", False),
            ("Professional Services",          "3.6",  "Statement 1", False),
            ("Trade",                          "3.7",  "Statement 1", False),
            ("Commercial Real Estate",         "3.8",  "Statement 1", False),
            ("NBFCs",                          "3.9",  "Statement 1", False),
            ("Other Services",                 "3.10", "Statement 1", False),
        ],
    },
    {
        "id":    "personalLoans",
        "title": "Personal Loans",
        "series": [
            ("Consumer Durables",         "4.1", "Statement 1", False),
            ("Housing",                   "4.2", "Statement 1", False),
            ("Advances vs Fixed Deposits","4.3", "Statement 1", False),
            ("Advances vs Shares/Bonds",  "4.4", "Statement 1", False),
            ("Credit Card Outstanding",   "4.5", "Statement 1", False),
            ("Education",                 "4.6", "Statement 1", False),
            ("Vehicle Loans",             "4.7", "Statement 1", False),
            ("Gold Loans",                "4.8", "Statement 1", False),
            ("Other Personal Loans",      "4.9", "Statement 1", False),
        ],
    },
    {
        "id":    "prioritySector",
        "title": "Priority Sector",
        "series": [
            ("Agriculture",                          "i",    "Statement 1", True),
            ("Micro and Small Enterprises",          "ii",   "Statement 1", True),
            ("Medium Enterprises",                   "iii",  "Statement 1", True),
            ("Housing",                              "iv",   "Statement 1", True),
            ("Educational Loans",                    "v",    "Statement 1", True),
            ("Renewable Energy",                     "vi",   "Statement 1", True),
            ("Social Infrastructure",                "vii",  "Statement 1", True),
            ("Export Credit",                        "viii", "Statement 1", True),
            ("Others",                               "ix",   "Statement 1", True),
            ("Weaker Sections",                      "x",    "Statement 1", True),
        ],
    },
    # industryByType is built dynamically from all level-2 Statement 2 rows
    {
        "id":    "industryByType",
        "title": "Industry by Type",
        "series": None,   # None = auto-detect from Statement 2, level=2
    },
]


# ── Date helpers ──────────────────────────────────────────────────────────────

def col_to_display(col: str) -> str:
    """'2024-01-26' → 'Jan 2024'"""
    try:
        d = datetime.strptime(col, "%Y-%m-%d")
        return d.strftime("%b %Y")
    except ValueError:
        return col


def same_month_prior_year(col: str, all_cols: list[str]) -> str | None:
    """Find a column from the previous year with the same month, if present."""
    try:
        d = datetime.strptime(col, "%Y-%m-%d")
    except ValueError:
        return None
    prior_year = d.year - 1
    for c in all_cols:
        try:
            cd = datetime.strptime(c, "%Y-%m-%d")
            if cd.year == prior_year and cd.month == d.month:
                return c
        except ValueError:
            continue
    return None


def most_recent_march(col: str, all_cols: list[str]) -> str | None:
    """Find the most recent March column that is before or at this col's date."""
    try:
        d = datetime.strptime(col, "%Y-%m-%d")
    except ValueError:
        return None

    march_cols = []
    for c in all_cols:
        try:
            cd = datetime.strptime(c, "%Y-%m-%d")
            if cd.month == 3 and cd <= d:
                march_cols.append((cd, c))
        except ValueError:
            continue
    if not march_cols:
        return None
    return max(march_cols, key=lambda x: x[0])[1]


def compute_growth(current_val, base_val) -> float | None:
    """(current/base - 1) × 100, rounded to 1 dp. None if either is None/zero."""
    if current_val is None or base_val is None:
        return None
    try:
        cv = float(current_val)
        bv = float(base_val)
        if bv == 0:
            return None
        return round((cv / bv - 1) * 100, 1)
    except (TypeError, ValueError):
        return None


# ── Delayed-publication detection ─────────────────────────────────────────────

def detect_anomalous_dates(date_cols: list[str], stmt_name: str) -> list[dict]:
    """
    Find dates that may be delayed publications from the prior calendar month.

    Pattern: within the same calendar month, two dates exist where
      - one is early  (day ≤ 14) — possible delayed prior-month snapshot
      - one is late   (day ≥ 15) — genuine current-month snapshot

    Returns a list of anomaly dicts; empty list if no anomalies.
    """
    from collections import defaultdict
    month_map: dict[str, list[str]] = defaultdict(list)
    for col in date_cols:
        try:
            d = datetime.strptime(col, "%Y-%m-%d")
            month_map[d.strftime("%Y-%m")].append(col)
        except ValueError:
            continue

    anomalies = []
    for _month, cols in sorted(month_map.items()):
        if len(cols) < 2:
            continue
        early = [c for c in cols if datetime.strptime(c, "%Y-%m-%d").day <= 14]
        late  = [c for c in cols if datetime.strptime(c, "%Y-%m-%d").day >= 15]
        if not (early and late):
            continue
        for e in early:
            import calendar
            d  = datetime.strptime(e, "%Y-%m-%d")
            pm = d.month - 1 if d.month > 1 else 12
            py = d.year if d.month > 1 else d.year - 1
            # Use the last day of the prior month so the relabelled date sits at
            # the natural end of that month on the proportional time axis.
            # Keeping the original day number (e.g. 8) would place it only ~13
            # days after the previous month's observation, visually cramping the
            # chart even though a full month has elapsed.
            last_day = calendar.monthrange(py, pm)[1]
            rel = datetime(py, pm, last_day)
            anomalies.append({
                "statement":          stmt_name,
                "early_date":         e,
                "late_date":          late[0],
                "original_display":   d.strftime("%b %Y"),
                "relabelled_iso":     rel.strftime("%Y-%m-%d"),
                "relabelled_display": rel.strftime("%b %Y") + "*",
            })
    return anomalies


def prompt_date_override(anomalies: list[dict], out_dir: Path) -> dict[str, str]:
    """
    Prompt the user to decide how to handle each anomalous date.

    Returns iso_overrides: {original_iso: relabelled_iso}
      - "__EXCLUDE__" as value means drop the date entirely.
      - Empty dict means keep as-is.

    Saves date_overrides.json to out_dir when choice is B.
    """
    print("\n" + "=" * 64)
    print("⚠️  DATE ANOMALY DETECTED — manual decision required")
    print("=" * 64)
    print(f"\n  {len(anomalies)} potential delayed-publication date(s) found:\n")
    for a in anomalies:
        print(f"  Statement : {a['statement']}")
        print(f"  Early date: {a['early_date']}  "
              f"(day ≤ 14 — may be delayed {a['relabelled_display'].rstrip('*')} data)")
        print(f"  Late date : {a['late_date']}  "
              f"(genuine {a['original_display']} snapshot)")
        print()

    print("  How should the early date(s) be treated?")
    print("  [A] Keep as-is          — original month label (YoY may be null)")
    print("  [B] Relabel to prior month — display as 'Feb YYYY*' (recommended)")
    print("  [C] Exclude             — drop these dates from output entirely")
    print("  [D] Abort               — stop extraction; inspect raw file first")
    print()

    try:
        choice = input("  Choice (A/B/C/D): ").strip().upper()
    except (EOFError, KeyboardInterrupt):
        print("\n  No terminal — defaulting to [A] (keep as-is). Re-run interactively to relabel.")
        return {}

    if choice == "D":
        print("\n  Aborting. Re-run after inspecting the raw file.")
        sys.exit(0)

    if choice == "B":
        from datetime import date as _date
        iso_overrides: dict[str, str] = {}
        records = []
        for a in anomalies:
            iso_overrides[a["early_date"]] = a["relabelled_iso"]
            records.append({
                "statement":          a["statement"],
                "original_iso":       a["early_date"],
                "relabelled_iso":     a["relabelled_iso"],
                "original_display":   a["original_display"],
                "relabelled_display": a["relabelled_display"],
                "reason":             "delayed_publication",
                "decided_by":         "user",
                "decided_at":         _date.today().isoformat(),
            })
        overrides_path = out_dir / "date_overrides.json"
        with open(overrides_path, "w") as f:
            json.dump({"overrides": records}, f, indent=2)
        print(f"\n  ✅ Saved overrides → {overrides_path}")
        for a in anomalies:
            print(f"     {a['early_date']}  →  {a['relabelled_iso']}  "
                  f"('{a['relabelled_display']}')")
        return iso_overrides

    if choice == "C":
        print(f"\n  Excluding {len(anomalies)} early date(s) from output.")
        return {a["early_date"]: "__EXCLUDE__" for a in anomalies}

    # A or unrecognised
    print("\n  Keeping dates as-is. YoY for affected months may be null.")
    return {}


# ── Row lookup ────────────────────────────────────────────────────────────────

def lookup_row(df, code: str, statement: str, is_priority: bool):
    """Return the single matching row or None."""
    mask = (
        (df["code"] == code) &
        (df["statement"] == statement) &
        (df["is_priority_sector_memo"] == is_priority)
    )
    matches = df[mask]
    if len(matches) == 0:
        return None
    if len(matches) > 1:
        print(f"  [WARN] Multiple rows matched code={code!r} statement={statement!r} — using first")
    return matches.iloc[0]


# ── Section builder ───────────────────────────────────────────────────────────

def build_section(
    sec_def: dict,
    stmt1: object,
    stmt2: object,
    date_cols: list[str],
    iso_overrides: dict[str, str] | None = None,
) -> dict:
    """
    Build one section dict from parsed DataFrames.

    iso_overrides maps original ISO date → relabelled ISO date (or "__EXCLUDE__").
    Relabelled dates are displayed with a trailing '*' to signal delayed publication.
    """
    section_id = sec_def["id"]
    title      = sec_def["title"]
    series_def = sec_def["series"]

    # industryByType: auto-detect level-2 rows from Statement 2
    if series_def is None:
        sub = stmt2[
            (stmt2["level"] == 2) &
            (stmt2["is_priority_sector_memo"] == False)
        ].copy()
        series_def = [
            (row["sector"], row["code"], "Statement 2", False)
            for _, row in sub.iterrows()
        ]

    series_names = [s[0] for s in series_def]

    # Build lookup: series_label → row values
    series_rows = {}
    for label, code, statement, is_priority in series_def:
        df = stmt1 if statement == "Statement 1" else stmt2
        row = lookup_row(df, code, statement, is_priority)
        if row is None:
            print(f"  [WARN] Section '{section_id}': code={code!r} not found — skipping '{label}'")
            series_names = [s for s in series_names if s != label]
        else:
            series_rows[label] = row

    if not series_rows:
        print(f"  [ERROR] Section '{section_id}': no rows matched — section will be empty")
        return {
            "id": section_id, "title": title, "seriesNames": [],
            "absoluteData": [], "growthData": [], "fyData": [],
        }

    # ── Apply iso_overrides to produce (orig_col, eff_col) pairs ─────────────
    # orig_col = key for DataFrame value lookup
    # eff_col  = ISO date used for month arithmetic (YoY / FY)
    col_pairs: list[tuple[str, str]] = []
    for col in date_cols:
        if iso_overrides and col in iso_overrides:
            eff = iso_overrides[col]
            if eff == "__EXCLUDE__":
                continue   # drop this date entirely
            col_pairs.append((col, eff))
        else:
            col_pairs.append((col, col))

    eff_to_orig: dict[str, str] = {eff: orig for orig, eff in col_pairs}

    def _display(eff_col: str, orig_col: str) -> str:
        label = col_to_display(eff_col)
        return label + ("*" if eff_col != orig_col else "")

    # ── absoluteData ──────────────────────────────────────────────────────────
    # Later col_pair overwrites earlier one for the same display month.
    abs_by_label: dict[str, dict] = {}
    for orig_col, eff_col in col_pairs:
        disp = _display(eff_col, orig_col)
        row_dict = {"date": disp}
        for label in series_names:
            val = series_rows[label].get(orig_col)
            row_dict[label] = round(float(val), 2) if val is not None else None
        abs_by_label[disp] = row_dict

    # Preserve display order (latest per display month at end)
    seen_labels: list[str] = []
    for orig_col, eff_col in col_pairs:
        disp = _display(eff_col, orig_col)
        if disp in seen_labels:
            seen_labels.remove(disp)
        seen_labels.append(disp)
    absolute_data = [abs_by_label[lbl] for lbl in dict.fromkeys(seen_labels)]

    # Rebuild deduped effective ISO date list (latest eff_col per display month)
    deduped_eff_map: dict[str, str] = {}   # display → eff_col
    for orig_col, eff_col in col_pairs:
        disp = _display(eff_col, orig_col)
        deduped_eff_map[disp] = eff_col
    deduped_eff_cols = list(deduped_eff_map.values())

    # ── growthData (YoY) ──────────────────────────────────────────────────────
    growth_data = []
    for eff_col in deduped_eff_cols:
        prior_eff = same_month_prior_year(eff_col, deduped_eff_cols)
        if prior_eff is None:
            continue
        orig_col   = eff_to_orig.get(eff_col, eff_col)
        orig_prior = eff_to_orig.get(prior_eff, prior_eff)
        disp = _display(eff_col, orig_col)
        row_dict = {"date": disp}
        for label in series_names:
            row_dict[label] = compute_growth(
                series_rows[label].get(orig_col),
                series_rows[label].get(orig_prior),
            )
        growth_data.append(row_dict)

    # ── fyData (FY-to-date from most recent March) ────────────────────────────
    fy_data = []
    for eff_col in deduped_eff_cols:
        march_eff = most_recent_march(eff_col, deduped_eff_cols)
        if march_eff is None:
            continue
        orig_col   = eff_to_orig.get(eff_col, eff_col)
        orig_march = eff_to_orig.get(march_eff, march_eff)
        disp = _display(eff_col, orig_col)

        if march_eff == eff_col:
            # This column IS a March-end — FY growth = YoY growth
            prior_eff  = same_month_prior_year(eff_col, deduped_eff_cols)
            if prior_eff is None:
                continue
            orig_prior = eff_to_orig.get(prior_eff, prior_eff)
            row_dict = {"date": disp}
            for label in series_names:
                row_dict[label] = compute_growth(
                    series_rows[label].get(orig_col),
                    series_rows[label].get(orig_prior),
                )
            fy_data.append(row_dict)
        else:
            row_dict = {"date": disp}
            for label in series_names:
                row_dict[label] = compute_growth(
                    series_rows[label].get(orig_col),
                    series_rows[label].get(orig_march),
                )
            fy_data.append(row_dict)

    return {
        "id":           section_id,
        "title":        title,
        "seriesNames":  series_names,
        "absoluteData": absolute_data,
        "growthData":   growth_data,
        "fyData":       fy_data,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def extract(xlsx_path: Path, out_dir: Path | None = None, dry_run: bool = False) -> dict:
    print(f"\n  Parsing: {xlsx_path.name}")

    # ── Parse ─────────────────────────────────────────────────────────────────
    try:
        frames = parse_file(xlsx_path)
    except Exception as e:
        print(f"ERROR: parse_file failed: {e}", file=sys.stderr)
        sys.exit(1)

    stmt1 = frames.get("statement1_wide") if frames.get("statement1_wide") is not None else frames.get("stmt1_wide")
    stmt2 = frames.get("statement2_wide") if frames.get("statement2_wide") is not None else frames.get("stmt2_wide")

    if stmt1 is None or stmt2 is None:
        # Try to auto-detect by key prefix
        for key in frames:
            if "1" in key and "wide" in key and stmt1 is None:
                stmt1 = frames[key]
            if "2" in key and "wide" in key and stmt2 is None:
                stmt2 = frames[key]

    if stmt1 is None or stmt2 is None:
        print(f"ERROR: Could not find Statement 1 and Statement 2 in parsed output.", file=sys.stderr)
        print(f"       Available keys: {list(frames.keys())}", file=sys.stderr)
        sys.exit(1)

    # Normalise boolean column (CSV round-trip may return strings)
    for df in (stmt1, stmt2):
        if df["is_priority_sector_memo"].dtype == object:
            df["is_priority_sector_memo"] = df["is_priority_sector_memo"].map(
                {"True": True, "False": False, True: True, False: False}
            )

    # ── Date columns — per statement ──────────────────────────────────────────
    import re
    stmt1_date_cols = sorted([c for c in stmt1.columns if re.match(r"\d{4}-\d{2}-\d{2}", c)])
    stmt2_date_cols = sorted([c for c in stmt2.columns if re.match(r"\d{4}-\d{2}-\d{2}", c)])
    print(f"  Statement 1 date columns: {stmt1_date_cols}")
    print(f"  Statement 2 date columns: {stmt2_date_cols}")

    # ── Detect delayed-publication dates and prompt user ─────────────────────
    # Must resolve out_dir before prompting (needed to save date_overrides.json)
    if out_dir is None:
        _tmp_out_dir = ANALYSIS / "rbi_sibc" / parse_filename_date(xlsx_path).strftime("%Y-%m-%d")
    else:
        _tmp_out_dir = Path(out_dir)
    _tmp_out_dir.mkdir(parents=True, exist_ok=True)

    stmt1_anomalies = detect_anomalous_dates(stmt1_date_cols, "Statement 1")
    stmt2_anomalies = detect_anomalous_dates(stmt2_date_cols, "Statement 2")
    all_anomalies   = stmt1_anomalies + stmt2_anomalies

    iso_overrides: dict[str, str] = {}
    if all_anomalies and not dry_run:
        iso_overrides = prompt_date_override(all_anomalies, _tmp_out_dir)
    elif all_anomalies and dry_run:
        print(f"\n  [dry-run] {len(all_anomalies)} date anomaly(ies) detected — "
              f"would prompt for override decision")

    # ── Report date from filename ─────────────────────────────────────────────
    report_date = parse_filename_date(xlsx_path)
    if report_date is None:
        print(f"ERROR: Cannot parse report date from filename: {xlsx_path.name}", file=sys.stderr)
        sys.exit(1)
    data_date = report_date.strftime("%Y-%m-%d")
    print(f"  Report/publication date : {data_date}")

    # ── Build sections ────────────────────────────────────────────────────────
    sections = []
    for sec_def in SECTION_DEFS:
        print(f"  Building section: {sec_def['id']}")
        # industryByType (series=None) auto-detects from Statement 2 — use stmt2 dates
        date_cols = stmt2_date_cols if sec_def["series"] is None else stmt1_date_cols
        section = build_section(sec_def, stmt1, stmt2, date_cols, iso_overrides=iso_overrides)
        sections.append(section)

    # ── Section-specific distribution overrides ───────────────────────────────
    # bankCredit: "Bank Credit" = "Food Credit" + "Non-food Credit" (aggregate).
    # Distribution chart must use only the two components so they sum to 100%.
    DISTRIBUTION_OVERRIDES: dict[str, list[str]] = {
        "bankCredit": ["Food Credit", "Non-food Credit"],
    }
    for section in sections:
        override = DISTRIBUTION_OVERRIDES.get(section["id"])
        if override:
            section["distributionSeriesNames"] = override

    payload = {
        "report":   "rbi_sibc",
        "dataDate": data_date,
        "sections": sections,
    }

    # Attach override record if one was saved this run
    overrides_path = _tmp_out_dir / "date_overrides.json"
    if overrides_path.exists():
        with open(overrides_path) as f:
            payload["dateOverrides"] = json.load(f).get("overrides", [])

    # ── Output ────────────────────────────────────────────────────────────────
    if out_dir is None:
        out_dir = ANALYSIS / "rbi_sibc" / data_date

    out_dir = Path(out_dir)

    if dry_run:
        print(f"\n  [dry-run] Would write sections.json → {out_dir}/sections.json")
        print(f"  Sections: {[s['id'] for s in sections]}")
        return payload

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "sections.json"
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"\n  ✅ Written: {out_path}")
    print(f"  Sections : {[s['id'] for s in sections]}")
    return payload


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Extract SIBC xlsx → sections.json")
    ap.add_argument("xlsx",      help="Path to SIBC .xlsx file")
    ap.add_argument("--out-dir", help="Output directory (default: analysis/rbi_sibc/{date}/)")
    ap.add_argument("--dry-run", action="store_true", help="Parse and print, do not write files")
    args = ap.parse_args()

    extract(
        xlsx_path=Path(args.xlsx),
        out_dir=Path(args.out_dir) if args.out_dir else None,
        dry_run=args.dry_run,
    )
