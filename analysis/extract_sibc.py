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

def build_section(sec_def: dict, stmt1: object, stmt2: object, date_cols: list[str]) -> dict:
    """Build one section dict from parsed DataFrames."""
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

    # ── absoluteData ──────────────────────────────────────────────────────────
    absolute_data = []
    for col in date_cols:
        row_dict = {"date": col_to_display(col)}
        for label in series_names:
            val = series_rows[label].get(col)
            row_dict[label] = round(float(val), 2) if val is not None else None
        absolute_data.append(row_dict)

    # ── growthData (YoY) ──────────────────────────────────────────────────────
    growth_data = []
    for col in date_cols:
        prior = same_month_prior_year(col, date_cols)
        if prior is None:
            continue
        row_dict = {"date": col_to_display(col)}
        for label in series_names:
            cur = series_rows[label].get(col)
            bas = series_rows[label].get(prior)
            row_dict[label] = compute_growth(cur, bas)
        growth_data.append(row_dict)

    # ── fyData (FY-to-date from most recent March) ────────────────────────────
    fy_data = []
    for col in date_cols:
        march = most_recent_march(col, date_cols)
        if march is None or march == col:   # skip if col IS March (no FTD growth for base itself)
            # For March itself: FY growth = YoY growth (full FY elapsed)
            # We still include it if we have a prior-year March
            prior_march = most_recent_march(march or col, date_cols) if march else None
            if march and march != col:
                pass  # handled below
            elif march == col:
                # FY base col is itself — compute YoY of this March
                prior = same_month_prior_year(col, date_cols)
                if prior is None:
                    continue
                row_dict = {"date": col_to_display(col)}
                for label in series_names:
                    cur = series_rows[label].get(col)
                    bas = series_rows[label].get(prior)
                    row_dict[label] = compute_growth(cur, bas)
                fy_data.append(row_dict)
                continue
            else:
                continue
        row_dict = {"date": col_to_display(col)}
        for label in series_names:
            cur = series_rows[label].get(col)
            bas = series_rows[label].get(march)
            row_dict[label] = compute_growth(cur, bas)
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
        section = build_section(sec_def, stmt1, stmt2, date_cols)
        sections.append(section)

    payload = {
        "report":   "rbi_sibc",
        "dataDate": data_date,
        "sections": sections,
    }

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
