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
import shutil
import sys
from pathlib import Path

import pandas as pd

# ── Repo paths ────────────────────────────────────────────────────────────────

REPO_ROOT     = Path(__file__).resolve().parent.parent
RBI_ANALYTICS = REPO_ROOT / "rbi-analytics"
WEB_DATA      = REPO_ROOT / "web" / "public" / "data"
CONSOLIDATED  = RBI_ANALYTICS / "consolidated" / "consolidated_long.csv"
WEB_CSV       = WEB_DATA / "rbi_sibc_consolidated.csv"

sys.path.insert(0, str(RBI_ANALYTICS))


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

    # ── Deduplicate at month level ────────────────────────────────────────────
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
