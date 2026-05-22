#!/usr/bin/env python3
"""
run_atm_pos_evals.py — India Credit Lens
------------------------------------------
Master eval gate for the ATM/POS pipeline. Runs Stages 0–3 in sequence.

Usage:
    # Ingest one or more new XLSX files (full pipeline)
    python3 run_atm_pos_evals.py --xlsx file1.xlsx [file2.xlsx ...]

    # Re-validate + re-consolidate an already-extracted period
    python3 run_atm_pos_evals.py --period 2026-03-31

Exit codes:
    0  all stages passed
    1  one or more stages failed
"""

import argparse
import calendar
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO_ROOT   = Path(__file__).resolve().parent.parent
ANALYSIS    = REPO_ROOT / "analysis"
ATM_POS_DIR = ANALYSIS / "rbi_atm_pos"

GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def _c(text, colour):
    return f"{colour}{text}{RESET}"

MONTHS = {
    "January": 1, "February": 2, "March": 3, "April": 4,
    "May": 5, "June": 6, "July": 7, "August": 8,
    "September": 9, "October": 10, "November": 11, "December": 12,
}


def run(label, cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    out  = (proc.stdout + proc.stderr).strip()
    return proc.returncode == 0, out


def period_from_xlsx(xlsx_path):
    """Extract YYYY-MM-DD from sheet name without full detection run."""
    import pandas as pd
    wb = pd.ExcelFile(xlsx_path)
    # Accept "For Website {M} {Y}" (newer) or bare "{M} {Y}" (older RBI format)
    sheet = next((s for s in wb.sheet_names if s.startswith("For Website ")), None)
    if not sheet:
        sheet = next(
            (s for s in wb.sheet_names
             if len(s.split()) == 2 and s.split()[0] in MONTHS),
            None,
        )
    if not sheet:
        return None
    parts = sheet.replace("For Website ", "").strip().split()
    if len(parts) != 2 or parts[0] not in MONTHS:
        return None
    month = MONTHS[parts[0]]
    year  = int(parts[1])
    last  = calendar.monthrange(year, month)[1]
    return date(year, month, last).isoformat()


def print_summary(results):
    w = 64
    print(f"\n{'═' * w}")
    print(f"  {BOLD}ATM/POS Pipeline Summary{RESET}")
    print(f"{'═' * w}")
    overall = True
    for label, passed, notes in results:
        if passed is None:
            status = _c("SKIP  ", YELLOW)
        elif passed:
            status = _c("PASS  ", GREEN)
        else:
            status = _c("FAIL  ", RED)
            overall = False
        note_str = (notes.splitlines()[-1] if notes else "")[:45]
        print(f"  {label:<30} {status}  {note_str}")
    print(f"{'═' * w}")
    if overall:
        print(f"  {_c('✅  ALL STAGES PASSED', GREEN + BOLD)}")
    else:
        print(f"  {_c('❌  PIPELINE FAILED — resolve errors above', RED + BOLD)}")
    print(f"{'═' * w}\n")
    return overall


def run_pipeline_for_xlsx(xlsx_path):
    results = []
    period  = period_from_xlsx(xlsx_path)
    label_prefix = Path(xlsx_path).name[:20]

    print(f"\n  Processing: {Path(xlsx_path).name}")

    # Stage 0: format detection
    passed, out = run(
        "Stage 0",
        [sys.executable, str(ANALYSIS / "detect_atm_pos_format.py"), str(xlsx_path)],
    )
    results.append((f"0. Format detect ({label_prefix})", passed, out))
    if not passed:
        return results

    # Stage 1: extraction
    passed, out = run(
        "Stage 1",
        [sys.executable, str(ANALYSIS / "extract_atm_pos.py"), str(xlsx_path)],
    )
    results.append((f"1. Extract       ({label_prefix})", passed, out))
    if not passed:
        return results

    if not period:
        results.append(("2. Validate", False, "Could not determine period date"))
        return results

    # Stage 2: validation
    passed, out = run(
        "Stage 2",
        [sys.executable, str(ANALYSIS / "validate_atm_pos.py"), period],
    )
    results.append((f"2. Validate      ({period})", passed, out))
    if not passed:
        return results

    # Stage 3: consolidation
    passed, out = run(
        "Stage 3",
        [sys.executable, str(ANALYSIS / "consolidate_atm_pos.py"), period],
    )
    results.append((f"3. Consolidate   ({period})", passed, out))

    return results


def run_pipeline_for_period(period):
    results = []

    # Stage 0 check: format_report.json confirmed?
    passed, out = run(
        "Stage 0 check",
        [sys.executable, str(ANALYSIS / "detect_atm_pos_format.py"),
         str(ATM_POS_DIR / period / "raw" / "placeholder"), "--check"],
    )
    # Stage 0 check requires the xlsx path — skip and just validate/consolidate
    # when working from an existing period directory
    results.append(("0. Format (pre-confirmed)", None, "skipped — period already extracted"))

    # Stage 2: validation
    passed, out = run(
        "Stage 2",
        [sys.executable, str(ANALYSIS / "validate_atm_pos.py"), period],
    )
    results.append((f"2. Validate      ({period})", passed, out))
    if not passed:
        return results

    # Stage 3: consolidation
    passed, out = run(
        "Stage 3",
        [sys.executable, str(ANALYSIS / "consolidate_atm_pos.py"), period],
    )
    results.append((f"3. Consolidate   ({period})", passed, out))

    return results


def main():
    ap = argparse.ArgumentParser(description="ATM/POS pipeline eval gate")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--xlsx",   nargs="+", help="One or more XLSX files to ingest")
    group.add_argument("--period", help="Re-validate existing period (YYYY-MM-DD)")
    args = ap.parse_args()

    all_results = []

    if args.xlsx:
        # Sort files by derived period date so older months go first
        files = sorted(args.xlsx, key=lambda f: (period_from_xlsx(f) or ""))
        for xlsx in files:
            results = run_pipeline_for_xlsx(xlsx)
            all_results.extend(results)
    else:
        all_results = run_pipeline_for_period(args.period)

    overall = print_summary(all_results)
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
