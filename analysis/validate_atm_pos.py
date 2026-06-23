#!/usr/bin/env python3
"""
validate_atm_pos.py — India Credit Lens
-----------------------------------------
Stage 2: Validate sections.json for an ATM/POS period.

Checks:
  A. All banks present and names match canonical_banks.json
  B. No negative values in outstanding columns (counts can't be negative)
  C. Transaction volume > 0 implies value > 0 (no orphaned volume records)
  D. Total record = sum of bank records within 0.1% tolerance
  E. report_date is a valid ISO date and matches a valid month-end

Usage:
    python3 validate_atm_pos.py 2026-03-31
    python3 validate_atm_pos.py 2026-03-31 --strict   # treat warnings as failures

Exit codes:
    0  all checks passed (warnings are printed but not fatal unless --strict)
    1  one or more checks failed
"""

import argparse
import json
import math
import sys
from datetime import date
from pathlib import Path

import sys
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core.paths import ROOT as REPO_ROOT
ANALYSIS    = REPO_ROOT / "analysis"
ATM_POS_DIR = ANALYSIS / "rbi_atm_pos"
CANONICAL   = ATM_POS_DIR / "canonical_banks.json"

GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def _c(text, colour):
    return f"{colour}{text}{RESET}"

OUTSTANDING_METRICS = {
    "atm_onsite", "atm_offsite", "pos_terminals", "micro_atms",
    "bharat_qr", "upi_qr", "credit_cards", "debit_cards",
}

VOL_VAL_PAIRS = [
    ("cc_pos_txn_vol",        "cc_pos_txn_val"),
    ("cc_ecom_txn_vol",       "cc_ecom_txn_val"),
    ("cc_other_txn_vol",      "cc_other_txn_val"),
    ("cc_atm_withdrawal_vol", "cc_atm_withdrawal_val"),
    ("dc_pos_txn_vol",        "dc_pos_txn_val"),
    ("dc_ecom_txn_vol",       "dc_ecom_txn_val"),
    ("dc_other_txn_vol",      "dc_other_txn_val"),
    ("dc_atm_withdrawal_vol", "dc_atm_withdrawal_val"),
    ("dc_pos_withdrawal_vol", "dc_pos_withdrawal_val"),
]

TOLERANCE = 0.001  # 0.1%


def load_canonical_names(report_date=None):
    data = json.loads(CANONICAL.read_text())
    names = set()
    for b in data["banks"]:
        status = b.get("status", "active")
        if status == "active":
            # Use former_name for periods before the rename took effect
            if report_date and b.get("former_name") and b.get("renamed_from"):
                if report_date < b["renamed_from"]:
                    names.add(b["former_name"])
                else:
                    names.add(b["name"])
            else:
                names.add(b["name"])
        elif status == "closed" and report_date:
            closed_from = b.get("closed_from", "9999-12-31")
            if report_date < closed_from:  # bank was active for this period
                names.add(b["name"])
    return names


def check_a(bank_records, canonical_names):
    found_names    = {r["bank_name"] for r in bank_records}
    missing        = canonical_names - found_names
    unexpected     = found_names - canonical_names
    issues         = []
    warnings       = []
    if missing:
        issues.append(f"Missing banks: {sorted(missing)}")
    if unexpected:
        warnings.append(
            f"Unexpected bank names (possible rename/merger): {sorted(unexpected)}. "
            "Update canonical_banks.json if confirmed."
        )
    return issues, warnings


def check_b(bank_records):
    issues = []
    for r in bank_records:
        for metric in OUTSTANDING_METRICS:
            val = r.get(metric)
            if val is not None and not math.isnan(val) and val < 0:
                issues.append(f"{r['bank_name']}: {metric} = {val} (negative outstanding)")
    return issues


def check_c(bank_records):
    issues = []
    for r in bank_records:
        for vol_key, val_key in VOL_VAL_PAIRS:
            vol = r.get(vol_key)
            val = r.get(val_key)
            vol_ok = vol is not None and not math.isnan(vol) and vol > 0
            val_ok = val is not None and not math.isnan(val) and val > 0
            if vol_ok and not val_ok:
                issues.append(
                    f"{r['bank_name']}: {vol_key}={vol} but {val_key}={val} (volume without value)"
                )
    return issues


def check_d(bank_records, total_record):
    if total_record is None:
        return ["Total row missing from sections.json"]

    issues = []
    all_metrics = list(OUTSTANDING_METRICS) + [v for pair in VOL_VAL_PAIRS for v in pair]

    for metric in all_metrics:
        computed = sum(
            (r.get(metric) or 0)
            for r in bank_records
            if r.get(metric) is not None and not math.isnan(r.get(metric))
        )
        reported = total_record.get(metric)
        if reported is None or math.isnan(reported):
            continue
        if reported == 0:
            continue
        diff = abs(computed - reported) / abs(reported)
        if diff > TOLERANCE:
            issues.append(
                f"{metric}: computed {computed:,.0f} vs reported {reported:,.0f} "
                f"(diff {diff*100:.2f}% > {TOLERANCE*100}%)"
            )
    return issues


def check_e(report_date_str):
    import calendar
    try:
        d = date.fromisoformat(report_date_str)
    except ValueError:
        return [f"report_date '{report_date_str}' is not a valid ISO date"]

    last_day = calendar.monthrange(d.year, d.month)[1]
    if d.day != last_day:
        return [
            f"report_date '{report_date_str}' is not a month-end "
            f"(expected {d.year}-{d.month:02d}-{last_day:02d})"
        ]
    return []


def print_check(label, issues, warnings=None, passed=None):
    if passed is None:
        passed = len(issues) == 0
    status = _c("PASS", GREEN) if passed else _c("FAIL", RED)
    print(f"  Check {label}: {status}")
    for i in (issues or []):
        print(f"    {_c('✗', RED)} {i}")
    for w in (warnings or []):
        print(f"    {_c('⚠', YELLOW)} {w}")


def main():
    ap = argparse.ArgumentParser(description="Stage 2: Validate ATM/POS sections.json")
    ap.add_argument("period", help="Period date (YYYY-MM-DD), e.g. 2026-03-31")
    ap.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    args = ap.parse_args()

    period_dir   = ATM_POS_DIR / args.period
    sections_path = period_dir / "sections.json"

    if not sections_path.exists():
        print(f"{_c('ERROR', RED)}: sections.json not found: {sections_path}", file=sys.stderr)
        sys.exit(1)

    sections = json.loads(sections_path.read_text())
    canonical_names = load_canonical_names(report_date=args.period)

    bank_records  = [r for r in sections["records"] if r["record_type"] == "bank"]
    total_records = [r for r in sections["records"] if r["record_type"] == "total"]
    total_record  = total_records[0] if total_records else None

    print(f"\n  ATM/POS Validation — {sections.get('report_month', args.period)}")
    print(f"  Banks: {len(bank_records)} | Total row: {'yes' if total_record else 'NO'}\n")

    results = []
    has_failure = False
    has_warning = False

    # Check A
    issues_a, warns_a = check_a(bank_records, canonical_names)
    print_check("A (bank registry)", issues_a, warns_a)
    if issues_a:
        has_failure = True
    if warns_a and args.strict:
        has_failure = True
    if warns_a:
        has_warning = True

    # Check B
    issues_b = check_b(bank_records)
    print_check("B (no negatives)", issues_b)
    if issues_b:
        has_failure = True

    # Check C
    issues_c = check_c(bank_records)
    print_check("C (vol→val integrity)", issues_c)
    if issues_c:
        has_failure = True

    # Check D
    issues_d = check_d(bank_records, total_record)
    print_check("D (total = sum of banks)", issues_d)
    if issues_d:
        has_failure = True

    # Check E
    issues_e = check_e(sections.get("report_date", ""))
    print_check("E (report_date validity)", issues_e)
    if issues_e:
        has_failure = True

    print()
    if has_failure:
        print(f"  {_c('❌  VALIDATION FAILED — fix errors before consolidation', RED + BOLD)}\n")
        sys.exit(1)
    elif has_warning:
        print(f"  {_c('⚠   PASSED WITH WARNINGS — review before proceeding', YELLOW + BOLD)}\n")
        sys.exit(0)
    else:
        print(f"  {_c('✅  ALL CHECKS PASSED', GREEN + BOLD)}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
