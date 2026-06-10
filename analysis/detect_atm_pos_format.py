#!/usr/bin/env python3
"""
detect_atm_pos_format.py — India Credit Lens
----------------------------------------------
Stage 0: Pre-flight format check for an incoming ATM/POS xlsx file.

Validates:
  1. Sheet name matches "For Website {Month} {Year}"
  2. Column count = 29
  3. Title cell contains "ATM"
  4. Column-number row (row 7) has sequential 1–26 in data columns
  5. Bank count matches canonical_banks.json (64 expected)

Writes format_report.json to the period directory.
Auto-confirms if format matches exactly. Prompts if deviations detected.

Usage:
    python3 detect_atm_pos_format.py path/to/file.xlsx
    python3 detect_atm_pos_format.py ... --check     # non-interactive (for eval gate)
    python3 detect_atm_pos_format.py ... --dry-run   # detect + print, no write

Exit codes:
    0  format confirmed and supported
    1  format unsupported, user aborted, or --check with unconfirmed report
"""

import argparse
import calendar
import json
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd

REPO_ROOT     = Path(__file__).resolve().parent.parent
ANALYSIS      = REPO_ROOT / "analysis"
ATM_POS_DIR   = ANALYSIS / "rbi_atm_pos"
CANONICAL     = ATM_POS_DIR / "canonical_banks.json"

GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

MONTHS = {
    "January": 1, "February": 2, "March": 3, "April": 4,
    "May": 5, "June": 6, "July": 7, "August": 8,
    "September": 9, "October": 10, "November": 11, "December": 12,
}

EXPECTED_COLS    = 29
EXPECTED_BANKS   = 64
SHEET_PREFIX     = "For Website "  # newer RBI format
FORMAT_ID        = "atm_pos_monthly"

CATEGORY_HEADERS = {
    "Scheduled Commercial Banks", "Public Sector Banks", "Private Sector Banks",
    "Foreign Banks", "Payment Banks", "Small Finance Banks",
}


def _c(text, colour):
    return f"{colour}{text}{RESET}"


def parse_sheet_date(sheet_name):
    """'For Website March 2026' or 'March 2026' → ('2026-03-31', 'March 2026')"""
    suffix = sheet_name.replace(SHEET_PREFIX, "").strip()
    parts = suffix.split()
    if len(parts) != 2 or parts[0] not in MONTHS:
        raise ValueError(f"Cannot parse month/year from sheet name: '{sheet_name}'")
    month = MONTHS[parts[0]]
    year  = int(parts[1])
    last  = calendar.monthrange(year, month)[1]
    return date(year, month, last).isoformat(), suffix


def find_data_sheet(wb):
    """Return the data sheet name, accepting both 'For Website {M} {Y}' and '{M} {Y}'."""
    # Prefer newer "For Website" format first
    for s in wb.sheet_names:
        if s.startswith(SHEET_PREFIX):
            parts = s.replace(SHEET_PREFIX, "").strip().split()
            if len(parts) == 2 and parts[0] in MONTHS:
                return s
    # Fall back to bare "{Month} {Year}" format (older RBI files)
    for s in wb.sheet_names:
        parts = s.strip().split()
        if len(parts) == 2 and parts[0] in MONTHS:
            try:
                int(parts[1])
                return s
            except ValueError:
                pass
    return None


def detect(xlsx_path):
    """Run all format checks. Returns (issues, warnings, report_dict)."""
    issues   = []
    warnings = []

    wb = pd.ExcelFile(xlsx_path)

    # Check 1: sheet name (accepts "For Website {M} {Y}" or bare "{M} {Y}")
    sheet_name = find_data_sheet(wb)
    if not sheet_name:
        issues.append(f"No recognised data sheet found. Sheets: {wb.sheet_names}")
        return issues, warnings, {}

    try:
        report_date, report_month = parse_sheet_date(sheet_name)
    except ValueError as e:
        issues.append(str(e))
        return issues, warnings, {}

    df = wb.parse(sheet_name, header=None)

    # Check 2: column count
    if df.shape[1] != EXPECTED_COLS:
        issues.append(
            f"Column count mismatch: expected {EXPECTED_COLS}, got {df.shape[1]}. "
            "Pipeline column map needs updating."
        )

    # Check 3: title cell — search rows 0–2 (older files lack a blank leading row)
    title = ""
    for title_row in range(min(3, df.shape[0])):
        candidate = str(df.iloc[title_row, 1]) if df.shape[1] > 1 else ""
        if "ATM" in candidate.upper():
            title = candidate
            break
    if not title:
        # Report what was found at rows 0-2 for diagnosis
        found = str(df.iloc[1, 1]) if df.shape[0] > 1 else ""
        issues.append(f"Title cell does not contain 'ATM': '{found[:80]}'")

    # Check 4: column number row — accept row index 6 or 7 (offset by 1 in older files)
    col_num_found = False
    for col_row in (7, 6):
        if df.shape[0] > col_row:
            col_nums = []
            for c in range(3, min(29, df.shape[1])):
                try:
                    col_nums.append(int(float(df.iloc[col_row, c])))
                except (ValueError, TypeError):
                    col_nums.append(None)
            if col_nums == list(range(1, 27)):
                col_num_found = True
                break
    if not col_num_found:
        issues.append(
            f"Column-number row (rows 6–7) mismatch. Expected 1–26, got: {col_nums[:10]}..."
        )

    # Check 5: bank count
    bank_count = 0
    for _, row in df.iterrows():
        cell1 = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
        try:
            idx = int(float(cell1))
            if 1 <= idx <= 100:
                bank_count += 1
        except (ValueError, TypeError):
            pass

    if bank_count != EXPECTED_BANKS:
        msg = f"Bank count: expected {EXPECTED_BANKS}, found {bank_count}."
        if abs(bank_count - EXPECTED_BANKS) <= 2:
            warnings.append(msg + " May be a merger or new entrant — verify canonical_banks.json.")
        else:
            issues.append(msg + " Structural change — investigate before proceeding.")

    report = {
        "format_id":         FORMAT_ID,
        "description":       "Monthly ATM/POS/Card Statistics",
        "sheet_name":        sheet_name,
        "report_date":       report_date,
        "report_month":      report_month,
        "column_count":      df.shape[1],
        "bank_count":        bank_count,
        "supported":         len(issues) == 0,
        "confirmed_by_user": False,
        "detected_at":       datetime.now().isoformat(timespec="seconds"),
        "source_file":       Path(xlsx_path).name,
        "issues":            issues,
        "warnings":          warnings,
    }

    return issues, warnings, report


def print_report(issues, warnings, report):
    print(f"\n  Format Detection — {report.get('report_month', '?')}")
    print(f"  Sheet    : {report.get('sheet_name', '?')}")
    print(f"  Date     : {report.get('report_date', '?')}")
    print(f"  Columns  : {report.get('column_count', '?')} (expected {EXPECTED_COLS})")
    print(f"  Banks    : {report.get('bank_count', '?')} (expected {EXPECTED_BANKS})")

    if warnings:
        for w in warnings:
            print(f"  {_c('⚠  ' + w, YELLOW)}")
    if issues:
        for i in issues:
            print(f"  {_c('✗  ' + i, RED)}")
    else:
        print(f"  {_c('✓  Format matches expected structure', GREEN)}")


def main():
    ap = argparse.ArgumentParser(description="Stage 0: ATM/POS format detection")
    ap.add_argument("xlsx", help="Path to ATM/POS xlsx file")
    ap.add_argument("--check",    action="store_true",
                    help="Non-interactive: exit 0 if format_report.json confirmed, else 1")
    ap.add_argument("--dry-run",  action="store_true",
                    help="Detect and print only — no writes, no prompt")
    args = ap.parse_args()

    xlsx_path = Path(args.xlsx).resolve()
    if not xlsx_path.exists():
        print(f"{_c('ERROR', RED)}: File not found: {xlsx_path}", file=sys.stderr)
        sys.exit(1)

    issues, warnings, report = detect(xlsx_path)

    if not report:
        sys.exit(1)

    report_date  = report["report_date"]
    period_dir   = ATM_POS_DIR / report_date
    report_path  = period_dir / "format_report.json"

    # --check mode: just verify existing report
    if args.check:
        if not report_path.exists():
            print(f"format_report.json missing for {report_date} — run detect_atm_pos_format.py first",
                  file=sys.stderr)
            sys.exit(1)
        existing = json.loads(report_path.read_text())
        if not existing.get("confirmed_by_user"):
            print(f"Format not confirmed for {report_date}", file=sys.stderr)
            sys.exit(1)
        if not existing.get("supported"):
            print(f"Format marked unsupported for {report_date}", file=sys.stderr)
            sys.exit(1)
        print(f"  format={existing['format_id']}, confirmed=true, supported=true")
        sys.exit(0)

    print_report(issues, warnings, report)

    if args.dry_run:
        sys.exit(0 if not issues else 1)

    # Hard stop on issues
    if issues:
        print(f"\n  {_c('BLOCKED', RED + BOLD)}: Format issues detected. Resolve before extraction.")
        sys.exit(1)

    # Auto-confirm if clean; prompt only if warnings
    if warnings:
        ans = input(f"\n  Warnings present. Confirm and proceed? [y/N] ").strip().lower()
        if ans != "y":
            print("  Aborted.")
            sys.exit(1)

    period_dir.mkdir(parents=True, exist_ok=True)
    report["confirmed_by_user"] = True
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\n  {_c('✓ format_report.json written', GREEN)}: {report_path.relative_to(REPO_ROOT)}")
    sys.exit(0)


if __name__ == "__main__":
    main()
