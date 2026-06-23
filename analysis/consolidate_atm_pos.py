#!/usr/bin/env python3
"""
consolidate_atm_pos.py — India Credit Lens
--------------------------------------------
Stage 3: Append a validated period to atm_pos_consolidated.csv.

Converts sections.json (wide format per bank) to long format rows
and appends to web/public/data/atm_pos_consolidated.csv.

Dedup rule: for any (bank_name, metric, report_date) overlap,
the row from the latest extraction_date wins (handles revised files).

Also updates analysis/rbi_atm_pos/timeline.json.

Usage:
    python3 consolidate_atm_pos.py 2026-03-31

Exit codes:
    0  consolidated successfully
    1  sections.json not found or validation gate not passed
"""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core.paths import ROOT as REPO_ROOT
ANALYSIS    = REPO_ROOT / "analysis"
ATM_POS_DIR = ANALYSIS / "rbi_atm_pos"
WEB_DATA    = REPO_ROOT / "web" / "public" / "data"
CSV_PATH    = WEB_DATA / "atm_pos_consolidated.csv"
TIMELINE    = ATM_POS_DIR / "timeline.json"

GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def _c(text, colour):
    return f"{colour}{text}{RESET}"

CSV_COLUMNS = [
    "report_date", "bank_name", "bank_category", "record_type", "metric", "value", "unit", "data_status",
]

# metric → unit mapping (mirrors extract_atm_pos.py COLUMN_MAP)
METRIC_UNITS = {
    "atm_onsite":             "count",
    "atm_offsite":            "count",
    "pos_terminals":          "count",
    "micro_atms":             "count",
    "bharat_qr":              "count",
    "upi_qr":                 "count",
    "credit_cards":           "count",
    "debit_cards":            "count",
    "cc_pos_txn_vol":         "transactions",
    "cc_pos_txn_val":         "rs_thousands",
    "cc_ecom_txn_vol":        "transactions",
    "cc_ecom_txn_val":        "rs_thousands",
    "cc_other_txn_vol":       "transactions",
    "cc_other_txn_val":       "rs_thousands",
    "cc_atm_withdrawal_vol":  "transactions",
    "cc_atm_withdrawal_val":  "rs_thousands",
    "dc_pos_txn_vol":         "transactions",
    "dc_pos_txn_val":         "rs_thousands",
    "dc_ecom_txn_vol":        "transactions",
    "dc_ecom_txn_val":        "rs_thousands",
    "dc_other_txn_vol":       "transactions",
    "dc_other_txn_val":       "rs_thousands",
    "dc_atm_withdrawal_vol":  "transactions",
    "dc_atm_withdrawal_val":  "rs_thousands",
    "dc_pos_withdrawal_vol":  "transactions",
    "dc_pos_withdrawal_val":  "rs_thousands",
}


def sections_to_long(sections):
    """Convert sections.json wide format → list of long-format dicts."""
    rows = []
    report_date = sections["report_date"]
    data_status = sections["data_status"]

    for record in sections["records"]:
        base = {
            "report_date":   report_date,
            "bank_name":     record["bank_name"],
            "bank_category": record["bank_category"],
            "record_type":   record["record_type"],
            "data_status":   data_status,
        }
        for metric, unit in METRIC_UNITS.items():
            val = record.get(metric)
            if val is None:
                continue
            rows.append({**base, "metric": metric, "value": val, "unit": unit})
    return rows


def load_existing_csv():
    """Load existing CSV rows, keyed by (report_date, bank_name, metric)."""
    if not CSV_PATH.exists():
        return {}, []

    rows = {}
    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row["report_date"], row["bank_name"], row["metric"])
            rows[key] = row
    return rows, list(rows.values())


def update_timeline(sections, period_dir):
    timeline = json.loads(TIMELINE.read_text())
    report_date = sections["report_date"]

    existing = next((p for p in timeline["periods"] if p["report_date"] == report_date), None)

    entry = {
        "period":      sections["report_month"],
        "report_date": report_date,
        "data_status": sections["data_status"],
        "bank_count":  sections["bank_count"],
        "consolidated_at": datetime.now().isoformat(timespec="seconds"),
        "paths": {
            "sections":      f"rbi_atm_pos/{report_date}/sections.json",
            "format_report": f"rbi_atm_pos/{report_date}/format_report.json",
        },
    }

    if existing:
        idx = timeline["periods"].index(existing)
        timeline["periods"][idx] = entry
    else:
        timeline["periods"].append(entry)
        timeline["periods"].sort(key=lambda p: p["report_date"])

    TIMELINE.write_text(json.dumps(timeline, indent=2))


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 consolidate_atm_pos.py YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)

    period_date  = sys.argv[1]
    period_dir   = ATM_POS_DIR / period_date
    sections_path = period_dir / "sections.json"

    if not sections_path.exists():
        print(f"{_c('ERROR', RED)}: sections.json not found: {sections_path}", file=sys.stderr)
        sys.exit(1)

    sections = json.loads(sections_path.read_text())
    new_rows = sections_to_long(sections)

    existing_map, _ = load_existing_csv()

    added   = 0
    updated = 0

    for row in new_rows:
        key = (row["report_date"], row["bank_name"], row["metric"])
        if key in existing_map:
            existing_map[key] = row
            updated += 1
        else:
            existing_map[key] = row
            added += 1

    # Write back sorted by report_date, bank_name, metric
    all_rows = sorted(
        existing_map.values(),
        key=lambda r: (r["report_date"], r["bank_name"], r["metric"]),
    )

    WEB_DATA.mkdir(parents=True, exist_ok=True)
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(all_rows)

    update_timeline(sections, period_dir)

    print(f"  {_c('✓', GREEN)} atm_pos_consolidated.csv — "
          f"+{added} new rows, {updated} updated, {len(all_rows)} total")
    print(f"  {_c('✓', GREEN)} timeline.json updated — {sections['report_month']} registered")
    sys.exit(0)


if __name__ == "__main__":
    main()
