#!/usr/bin/env python3
"""
update_web_data.py — India Credit Lens
----------------------------------------
Stage 1b of the pipeline. Regenerates the consolidated CSV from all SIBC
xlsx files and copies it to web/public/data/ so the dashboard charts
reflect the latest data.

Must be run after any new SIBC xlsx file is added to rbi-analytics/.

What it does:
  1. Calls rbi-analytics/consolidate.py on all SIBC*.xlsx files
  2. Writes rbi-analytics/consolidated/consolidated_long.csv
  3. Copies it to web/public/data/rbi_sibc_consolidated.csv

Deduplication: for any (statement, code, sector, date) overlap across files,
the row from the most recently published file (latest report_date) wins.

Usage:
    python3 update_web_data.py
    python3 update_web_data.py --dry-run

Exit codes:
    0 = web CSV updated
    1 = error
"""

import argparse
import json
import shutil
import sys
from calendar import monthrange
from datetime import date as date_type
from pathlib import Path

import pandas as pd

# ── Repo paths ────────────────────────────────────────────────────────────────

REPO_ROOT     = Path(__file__).resolve().parent.parent
RBI_ANALYTICS = REPO_ROOT / "rbi-analytics"
ANALYSIS      = REPO_ROOT / "analysis"
WEB_DATA      = REPO_ROOT / "web" / "public" / "data"
CONSOLIDATED  = RBI_ANALYTICS / "consolidated" / "consolidated_long.csv"
WEB_CSV       = WEB_DATA / "rbi_sibc_consolidated.csv"

sys.path.insert(0, str(RBI_ANALYTICS))


def _canonical_month_end(d: date_type) -> date_type:
    """
    Map a raw RBI publication date to the canonical last day of its reporting period.

    Rules:
      - Apr 1–7  →  Mar 31 of the same year
            RBI publishes the fortnightly Bank Credit figure (Statement 1:
            Bank Credit, Food Credit, Non-food Credit) on the first Friday
            after March year-end — typically Apr 4–5. That figure is the
            March snapshot, not April's.
      - All other dates  →  last calendar day of the same month
            Weekly sector snapshots land on Fridays within the month
            (e.g. Jan 24, Mar 22). Mapping them to month-end makes every
            period's data land on a single x-axis point in the dashboard.

    Examples:
      2024-04-05  →  2024-03-31   (Apr fortnightly → Mar year-end)
      2025-04-04  →  2025-03-31
      2024-03-22  →  2024-03-31   (weekly sector snapshot)
      2025-03-21  →  2025-03-31
      2024-01-26  →  2024-01-31
      2024-02-23  →  2024-02-29   (2024 is a leap year)
      2025-02-21  →  2025-02-28
      2026-03-31  →  2026-03-31   (already canonical)
    """
    if d.month == 4 and d.day <= 7:
        return date_type(d.year, 3, 31)
    last_day = monthrange(d.year, d.month)[1]
    return date_type(d.year, d.month, last_day)


def normalize_to_period_end(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize all raw publication dates to canonical period-end dates.

    Runs AFTER load_and_apply_overrides() so semantic corrections (e.g. an
    early-March date relabelled as February) are already applied. This step
    only does formatting normalisation (weekly snapshot → month-end).

    Preserves the original date in source_date only for rows not already
    tagged by the overrides step — overrides already set source_date to the
    pre-override original, which is the most informative provenance.

    Logs every remapping so the output is auditable.
    """
    df = df.copy()
    dates_parsed = pd.to_datetime(df["date"], errors="coerce")
    canonical    = dates_parsed.apply(
        lambda d: str(_canonical_month_end(d.date())) if pd.notna(d) else None
    )

    changed = canonical != df["date"]
    n_changed = changed.sum()

    if n_changed == 0:
        return df

    print(f"\n  Normalising {n_changed} date(s) to period-end:")
    for orig, canon in sorted(
        set(zip(df.loc[changed, "date"], canonical[changed]))
    ):
        n = ((df["date"] == orig) & changed).sum()
        print(f"    {orig}  →  {canon}  ({n} rows)")

    # Preserve original in source_date only where not already set by overrides
    untagged = changed & (df["source_date"] == "")
    df.loc[untagged, "source_date"] = df.loc[untagged, "date"]

    df.loc[changed, "date"] = canonical[changed]
    return df


def deduplicate_by_month(df: pd.DataFrame) -> pd.DataFrame:
    """
    Collapse multiple rows for the same calendar month into one.

    Why this is needed:
      - The SIBC file contains multiple weekly snapshots per month
        (e.g. 2024-03-08 AND 2024-03-22 are both March 2024).
      - Across files, different publications may cover the same month.

    Rule (applied in order):
      1. Latest report_date wins   — most recently published file is authoritative
      2. Latest date wins          — within the same file, latest weekly snapshot wins

    The surviving row's 'date' is kept as-is (not normalised to month-end).
    """
    before = len(df)

    df = df.copy()
    df["_date_ts"]   = pd.to_datetime(df["date"],        errors="coerce")
    df["_report_ts"] = pd.to_datetime(df["report_date"], errors="coerce")
    df["_year_month"] = df["_date_ts"].dt.to_period("M")

    df = (
        df
        .sort_values(["_report_ts", "_date_ts"], ascending=[False, False])
        .drop_duplicates(
            subset=["statement", "code", "sector", "_year_month"],
            keep="first",
        )
        .drop(columns=["_date_ts", "_report_ts", "_year_month"])
        .sort_values(["statement", "code", "date"])
        .reset_index(drop=True)
    )

    after = len(df)
    if before != after:
        print(f"  Deduped : {before - after} duplicate month rows removed "
              f"({before} → {after} rows)")
    return df


def load_and_apply_overrides(df: pd.DataFrame) -> pd.DataFrame:
    """
    Discover all date_overrides.json files in period directories and apply them.

    For each override record: rows where date == original_iso get their date
    updated to relabelled_iso, and a new 'source_date' column is set to the
    original ISO date (so the frontend can show the raw publication date on hover).
    """
    period_root = ANALYSIS / "rbi_sibc"
    override_files = sorted(period_root.glob("*/date_overrides.json"))

    if not override_files:
        df["source_date"] = ""
        return df

    # Build flat list of override records
    records = []
    for path in override_files:
        with open(path) as f:
            data = json.load(f)
        records.extend(data.get("overrides", []))

    if not records:
        df["source_date"] = ""
        return df

    print(f"\n  Applying {len(records)} date override(s) from {len(override_files)} period(s):")
    df = df.copy()
    df["source_date"] = ""

    for rec in records:
        orig    = rec.get("original_iso", "")
        relabel = rec.get("relabelled_iso", "")
        stmt    = rec.get("statement", "")
        if not orig or not relabel:
            continue

        mask = (df["date"] == orig)
        if stmt:
            mask = mask & (df["statement"] == stmt)

        n = mask.sum()
        if n == 0:
            print(f"  [WARN] Override not matched: {orig} ({stmt}) — 0 rows found")
            continue

        df.loc[mask, "source_date"] = orig
        df.loc[mask, "date"]        = relabel
        print(f"  Relabelled: {orig} → {relabel}  ({n} rows, {stmt})")

    return df


def main(dry_run: bool = False):
    # ── Discover xlsx files ───────────────────────────────────────────────────
    xlsx_files = sorted(
        list(RBI_ANALYTICS.glob("SIBC*.xlsx")) +
        list(RBI_ANALYTICS.glob("*SIBC*.xlsx"))
    )
    # Deduplicate (both patterns can match the same file)
    seen, unique = set(), []
    for f in xlsx_files:
        if f not in seen:
            seen.add(f)
            unique.append(f)
    xlsx_files = sorted(unique)

    if not xlsx_files:
        print(f"ERROR: No SIBC*.xlsx files found in {RBI_ANALYTICS}", file=sys.stderr)
        sys.exit(1)

    print(f"\n  Found {len(xlsx_files)} xlsx file(s):")
    for f in xlsx_files:
        print(f"    {f.name}")

    if dry_run:
        print("\n  [dry-run] Would consolidate and copy to web/public/data/")
        print(f"  Source : {RBI_ANALYTICS}")
        print(f"  Target : {WEB_CSV}")
        return

    # ── Run consolidate.py ────────────────────────────────────────────────────
    try:
        from consolidate import consolidate as run_consolidate
    except ImportError as e:
        print(f"ERROR: Cannot import consolidate.py from {RBI_ANALYTICS}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\n  Consolidating...")
    df = run_consolidate(xlsx_files)

    if df.empty:
        print("ERROR: Consolidation produced empty DataFrame", file=sys.stderr)
        sys.exit(1)

    # ── Step 1: Apply semantic date overrides ────────────────────────────────
    # Overrides remap early-March dates (delayed publications) to their true
    # prior month. Must run first — these are semantic corrections, not just
    # formatting (e.g. 2024-03-08 is actually February data → 2024-02-29).
    df = load_and_apply_overrides(df)

    # ── Step 2: Normalize to canonical period-end dates ───────────────────────
    # Maps all weekly snapshot dates to the last day of their month, and maps
    # early-April Bank Credit fortnightly dates (Apr 1–7) to March 31.
    # This ensures every reporting period lands on a single x-axis point in
    # the dashboard — no split between e.g. 2024-03-22 (sectors) and
    # 2024-04-05 (Bank Credit total) for the same March 2024 snapshot.
    df = normalize_to_period_end(df)

    # ── Step 3: Deduplicate at month level ───────────────────────────────────
    df = deduplicate_by_month(df)

    # Write to rbi-analytics/consolidated/
    CONSOLIDATED.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CONSOLIDATED, index=False)
    print(f"  Wrote   : {CONSOLIDATED}  ({len(df)} rows)")
    print(f"  Dates   : {df['date'].min()} → {df['date'].max()}")
    print(f"  Sectors : {df['code'].nunique()} unique codes")

    # ── Copy to web/public/data/ ──────────────────────────────────────────────
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CONSOLIDATED, WEB_CSV)
    print(f"  Copied  : {WEB_CSV}")

    print(f"\n  ✅ Dashboard data updated — {len(xlsx_files)} file(s) consolidated")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Regenerate consolidated CSV and update web dashboard data")
    ap.add_argument("--dry-run", action="store_true", help="Show what would happen, do not write files")
    args = ap.parse_args()
    main(dry_run=args.dry_run)
