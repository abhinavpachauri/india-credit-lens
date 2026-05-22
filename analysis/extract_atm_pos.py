#!/usr/bin/env python3
"""
extract_atm_pos.py — India Credit Lens
----------------------------------------
Stage 1: Extract ATM/POS xlsx → sections.json

Requires format_report.json confirmed by detect_atm_pos_format.py.
Archives the source XLSX to {period}/raw/.

Usage:
    python3 extract_atm_pos.py path/to/file.xlsx

Exit codes:
    0  sections.json written successfully
    1  format_report.json missing/unconfirmed, or extraction error
"""

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

REPO_ROOT   = Path(__file__).resolve().parent.parent
ANALYSIS    = REPO_ROOT / "analysis"
ATM_POS_DIR = ANALYSIS / "rbi_atm_pos"

GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
RESET  = "\033[0m"

def _c(text, colour):
    return f"{colour}{text}{RESET}"

# Canonical column index → (metric_name, unit)
# Col 0: blank | Col 1: Sr.No. | Col 2: Bank Name | Cols 3–28: data
COLUMN_MAP = {
    3:  ("atm_onsite",             "count"),
    4:  ("atm_offsite",            "count"),
    5:  ("pos_terminals",          "count"),
    6:  ("micro_atms",             "count"),
    7:  ("bharat_qr",              "count"),
    8:  ("upi_qr",                 "count"),
    9:  ("credit_cards",           "count"),
    10: ("debit_cards",            "count"),
    11: ("cc_pos_txn_vol",         "transactions"),
    12: ("cc_pos_txn_val",         "rs_thousands"),
    13: ("cc_ecom_txn_vol",        "transactions"),
    14: ("cc_ecom_txn_val",        "rs_thousands"),
    15: ("cc_other_txn_vol",       "transactions"),
    16: ("cc_other_txn_val",       "rs_thousands"),
    17: ("cc_atm_withdrawal_vol",  "transactions"),
    18: ("cc_atm_withdrawal_val",  "rs_thousands"),
    19: ("dc_pos_txn_vol",         "transactions"),
    20: ("dc_pos_txn_val",         "rs_thousands"),
    21: ("dc_ecom_txn_vol",        "transactions"),
    22: ("dc_ecom_txn_val",        "rs_thousands"),
    23: ("dc_other_txn_vol",       "transactions"),
    24: ("dc_other_txn_val",       "rs_thousands"),
    25: ("dc_atm_withdrawal_vol",  "transactions"),
    26: ("dc_atm_withdrawal_val",  "rs_thousands"),
    27: ("dc_pos_withdrawal_vol",  "transactions"),
    28: ("dc_pos_withdrawal_val",  "rs_thousands"),
}

CATEGORY_HEADERS = {
    "Scheduled Commercial Banks", "Public Sector Banks", "Private Sector Banks",
    "Foreign Banks", "Payment Banks", "Small Finance Banks",
}


def safe_float(val):
    if val is None or (isinstance(val, float) and __import__("math").isnan(val)):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def extract_row_data(row):
    record = {}
    for col_idx, (metric, unit) in COLUMN_MAP.items():
        val = safe_float(row.iloc[col_idx]) if col_idx < len(row) else None
        record[metric] = val
    return record


def extract(xlsx_path, period_dir, format_report):
    sheet_name = format_report["sheet_name"]
    report_date = format_report["report_date"]
    report_month = format_report["report_month"]
    data_status = "provisional"

    wb = pd.ExcelFile(xlsx_path)
    df = wb.parse(sheet_name, header=None)

    records = []
    current_category = None

    for i, row in df.iterrows():
        if i < 8:
            continue

        cell1 = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
        cell2 = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ""

        # Category header row
        if cell1 in CATEGORY_HEADERS:
            current_category = cell1
            continue

        # Total row
        if cell1 == "Total":
            data = extract_row_data(row)
            records.append({
                "bank_name":     "Total",
                "bank_category": "Total",
                "record_type":   "total",
                **data,
            })
            continue

        # Bank data row
        try:
            sr = int(float(cell1))
        except (ValueError, TypeError):
            continue

        if 1 <= sr <= 100 and cell2:
            data = extract_row_data(row)
            records.append({
                "bank_name":     cell2,
                "bank_category": current_category or "Unknown",
                "record_type":   "bank",
                **data,
            })

    bank_count = sum(1 for r in records if r["record_type"] == "bank")

    sections = {
        "report_date":  report_date,
        "report_month": report_month,
        "data_status":  data_status,
        "source_file":  xlsx_path.name,
        "extracted_at": datetime.now().isoformat(timespec="seconds"),
        "bank_count":   bank_count,
        "records":      records,
    }

    return sections


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 extract_atm_pos.py path/to/file.xlsx", file=sys.stderr)
        sys.exit(1)

    xlsx_path = Path(sys.argv[1]).resolve()
    if not xlsx_path.exists():
        print(f"{_c('ERROR', RED)}: File not found: {xlsx_path}", file=sys.stderr)
        sys.exit(1)

    # Load format_report to find period_dir + confirm
    # Run detect first to get the report_date without re-running full detection
    import subprocess
    result = subprocess.run(
        [sys.executable, str(ANALYSIS / "detect_atm_pos_format.py"), str(xlsx_path), "--check"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        # format_report.json may not exist yet — locate it via sheet name
        import openpyxl
        wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
        sheet_name = next(
            (s for s in wb.sheetnames if s.startswith("For Website ") or
             (len(s.split()) == 2 and s.split()[0] in ("January","February","March","April","May","June","July","August","September","October","November","December"))),
            None,
        )
        wb.close()
        if not sheet_name:
            print(f"{_c('ERROR', RED)}: Run detect_atm_pos_format.py first.", file=sys.stderr)
            sys.exit(1)
        # Run detection interactively
        det = subprocess.run(
            [sys.executable, str(ANALYSIS / "detect_atm_pos_format.py"), str(xlsx_path)],
        )
        if det.returncode != 0:
            sys.exit(1)

    # Re-read format_report
    import calendar
    wb2 = pd.ExcelFile(xlsx_path)
    _months = ("January","February","March","April","May","June","July","August","September","October","November","December")
    sheet_name = next(
        (s for s in wb2.sheet_names if s.startswith("For Website ") or
         (len(s.split()) == 2 and s.split()[0] in _months)),
        None,
    )
    suffix = sheet_name.replace("For Website ", "").strip().split()
    MONTHS = {
        "January": 1, "February": 2, "March": 3, "April": 4,
        "May": 5, "June": 6, "July": 7, "August": 8,
        "September": 9, "October": 10, "November": 11, "December": 12,
    }
    month = MONTHS[suffix[0]]
    year  = int(suffix[1])
    last  = calendar.monthrange(year, month)[1]
    from datetime import date
    report_date = date(year, month, last).isoformat()

    period_dir   = ATM_POS_DIR / report_date
    report_path  = period_dir / "format_report.json"

    if not report_path.exists():
        print(f"{_c('ERROR', RED)}: format_report.json not found at {report_path}", file=sys.stderr)
        sys.exit(1)

    format_report = json.loads(report_path.read_text())

    print(f"  Extracting {format_report['report_month']} → {report_date}")

    sections = extract(xlsx_path, period_dir, format_report)

    # Write sections.json
    out_path = period_dir / "sections.json"
    out_path.write_text(json.dumps(sections, indent=2))
    print(f"  {_c('✓', GREEN)} sections.json — {sections['bank_count']} banks, "
          f"{len(sections['records'])} records")

    # Archive XLSX
    raw_dir = period_dir / "raw"
    raw_dir.mkdir(exist_ok=True)
    dest = raw_dir / xlsx_path.name
    if not dest.exists():
        shutil.copy2(xlsx_path, dest)
        print(f"  {_c('✓', GREEN)} XLSX archived → {dest.relative_to(REPO_ROOT)}")
    else:
        print(f"  {_c('⚠', YELLOW)} XLSX already in raw/ — not overwriting")

    sys.exit(0)


if __name__ == "__main__":
    main()
