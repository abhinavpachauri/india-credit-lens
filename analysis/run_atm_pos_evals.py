#!/usr/bin/env python3
"""
run_atm_pos_evals.py — India Credit Lens
------------------------------------------
Master eval gate for the ATM/POS pipeline. Runs Stages 0–3, then 4b/4c/4d,
then a web CSV integrity check, signal history integrity check, and TypeScript build gate.

Usage:
    # Ingest one or more new XLSX files (full pipeline)
    python3 run_atm_pos_evals.py --xlsx file1.xlsx [file2.xlsx ...]

    # Re-validate + re-consolidate an already-extracted period
    python3 run_atm_pos_evals.py --period 2026-03-31

    # Skip insight generation (Stages 4b/4c/4d) — data-only run
    python3 run_atm_pos_evals.py --xlsx file.xlsx --skip-insights

    # Skip TypeScript build (use when web/ hasn't changed)
    python3 run_atm_pos_evals.py --xlsx file.xlsx --skip-build

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


def check_atm_pos_csv():
    """
    Validate web/public/data/atm_pos_consolidated.csv:
      - Exists and is non-empty
      - No duplicate (report_date, bank_name, metric) rows
      - All report_date values are canonical end-of-month
    """
    import pandas as pd
    from calendar import monthrange

    csv_path = REPO_ROOT / "web" / "public" / "data" / "atm_pos_consolidated.csv"
    if not csv_path.exists():
        return False, "atm_pos_consolidated.csv not found — run consolidate_atm_pos.py"
    if csv_path.stat().st_size < 1000:
        return False, "atm_pos_consolidated.csv suspiciously small — may be empty"

    df = pd.read_csv(csv_path, dtype=str)

    # Duplicate check
    key_cols = ["report_date", "bank_name", "metric"]
    missing = [c for c in key_cols if c not in df.columns]
    if missing:
        return False, f"Expected columns missing: {missing}"

    dupe_count = int(df.duplicated(subset=key_cols).sum())
    if dupe_count > 0:
        return False, f"{dupe_count} duplicate (report_date, bank_name, metric) row(s)"

    # Canonical end-of-month date check
    bad_dates = []
    for raw in df["report_date"].dropna().unique():
        try:
            import datetime
            d = datetime.date.fromisoformat(raw)
        except Exception:
            bad_dates.append(f"unparseable: {raw}")
            continue
        last = monthrange(d.year, d.month)[1]
        if d.day != last:
            bad_dates.append(f"{raw} (should be {d.year}-{d.month:02d}-{last:02d})")

    if bad_dates:
        return False, f"{len(bad_dates)} non-canonical date(s): {'; '.join(bad_dates[:3])}"

    row_count   = len(df)
    date_count  = df["report_date"].nunique()
    bank_count  = df[df["bank_name"].notna()]["bank_name"].nunique()
    return True, f"{row_count} rows · {date_count} periods · {bank_count} banks/totals"


def check_signal_history():
    """Check 2e: signal history integrity — registry schema + history file consistency."""
    passed, out = run(
        "signal_history",
        [sys.executable, str(ANALYSIS / "validate_signal_history.py")],
    )
    # Extract a short summary line
    lines = out.splitlines()
    summary = next((l.strip() for l in lines if "passed" in l.lower() or "failure" in l.lower()), "")
    return passed, summary or (out[:60] if out else "passed")


def check_signal_freshness():
    """Check 5b2: signals.db == a fresh recompute from the current CSV (atm_pos).
    Catches stale rows left behind when the CSV changes but not every period is
    re-appended (root cause of the FY-acceleration phantom jump)."""
    passed, out = run(
        "signal_freshness",
        [sys.executable, str(ANALYSIS / "check_signal_freshness.py"), "--pipeline", "atm_pos"],
    )
    line = next((l.strip() for l in out.splitlines() if "signals.db" in l), "")
    return passed, (line.lstrip("✓✗ ").strip()[:60] if line else (out[:60] if out else "passed"))


def latest_db_period(pipeline):
    import sqlite3
    db = ANALYSIS / "signals" / "signals.db"
    if not db.exists():
        return None
    con = sqlite3.connect(db)
    row = con.execute("select max(period) from signals where pipeline=?", (pipeline,)).fetchone()
    con.close()
    return row[0] if row else None


def check_system_state():
    """Stage 5d: S3 dynamic state + live opportunity feed for the latest period."""
    period = latest_db_period("atm_pos")
    if not period:
        return None, "no signals in db"
    ok1, o1 = run("system_state", [sys.executable, str(ANALYSIS / "generate_system_state.py"),
                                   "--pipeline", "atm_pos", "--period", period])
    if not ok1:
        return False, (o1.splitlines()[-1] if o1 else "state failed")[:55]
    ok2, o2 = run("opportunities", [sys.executable, str(ANALYSIS / "derive_opportunities.py"),
                                    "--pipeline", "atm_pos", "--period", period])
    return ok2, f"state + opportunities @ {period}"


def check_opportunity_traceability():
    """Check 4f: opportunity number traceability (STRICT). Runs over the shared
    opportunities_feed.json (both pipelines) — wired into BOTH gates so the L2
    grounding contract is enforced identically for SIBC and payments (the L2
    analog of Check 2g)."""
    ok, out = run("opportunity_traceability",
                  [sys.executable, str(ANALYSIS / "validate_opportunity_traceability.py"), "--strict"])
    tline = [l.strip() for l in out.splitlines()
             if "opportunit" in l.lower() and ("✓" in l or "⚠" in l or "✗" in l)]
    note = (tline[0].lstrip("✓✗⚠ ").strip()[:60]) if tline else "ran"
    return ok, note


def check_system_model():
    """Stage 5c: regenerate the ATM/POS structural skeleton deterministically from the
    CSV + profile (preserving the authored behavioral layer), then validate the merged
    system_model.json against SYSTEM_MODEL_SPEC v3.0."""
    gen_ok, gen_out = run(
        "skeleton",
        [sys.executable, str(ANALYSIS / "generate_skeleton.py"), "--pipeline", "atm_pos"],
    )
    if not gen_ok:
        return False, (gen_out.splitlines()[-1] if gen_out else "skeleton gen failed")[:60]
    val_ok, val_out = run(
        "system_model",
        [sys.executable, str(ANALYSIS / "validate_system_model.py"), "--pipeline", "atm_pos"],
    )
    summary = next((l.strip() for l in val_out.splitlines() if "PASS" in l or "FAIL" in l), "")
    return val_ok, (summary or val_out[:60])


def check_build():
    """tsc --noEmit then npm run build in web/."""
    WEB = REPO_ROOT / "web"
    tsc_proc = subprocess.run(
        ["npx", "tsc", "--noEmit"],
        cwd=str(WEB), capture_output=True, text=True,
    )
    if tsc_proc.returncode != 0:
        return False, (tsc_proc.stdout + tsc_proc.stderr).strip()
    build_proc = subprocess.run(
        ["npm", "run", "build"],
        cwd=str(WEB), capture_output=True, text=True,
    )
    out = (build_proc.stdout + build_proc.stderr).strip()
    return build_proc.returncode == 0, out


def run_insight_stages():
    """Stages 4a/4b/4c/4d — refresh signals payload, generate + validate insights.
    Runs once after all extractions."""
    results = []

    # Stage 4a: rebuild the deterministic signals payload (signals.json) from the latest
    # consolidated CSV. MUST run before 4b — generate_atm_pos_insights.py reads this file,
    # and if it is not refreshed the dashboard silently serves a stale prior period (the
    # 2026-06-13 review found it frozen a full month behind the data).
    passed, out = run(
        "Stage 4a",
        [sys.executable, str(ANALYSIS / "compute_atm_pos_signals.py")],
    )
    results.append(("4a. Refresh signals payload", passed, out))
    if not passed:
        return results

    # Stage 4a-series: precompute the compact chart-series JSON the web loads (compute-once,
    # ship-compact). Replaces client-side parsing of the 4.6 MB consolidated CSV on /payments.
    passed, out = run(
        "Stage 4a-series",
        [sys.executable, str(ANALYSIS / "generate_chart_series.py"), "--pipeline", "atm_pos"],
    )
    results.append(("4a-series. Chart series JSON", passed, out))
    if not passed:
        return results

    # Stage 4b: generate insights
    passed, out = run(
        "Stage 4b",
        [sys.executable, str(ANALYSIS / "generate_atm_pos_insights.py")],
    )
    results.append(("4b. Generate insights", passed, out))
    if not passed:
        return results

    # Stage 4c: validate numbers in insights
    passed, out = run(
        "Stage 4c",
        [sys.executable, str(ANALYSIS / "validate_atm_pos_insights.py")],
    )
    results.append(("4c. Validate numbers", passed, out))
    if not passed:
        return results

    # Stage 4d: validate declared signal claims
    passed, out = run(
        "Stage 4d",
        [sys.executable, str(ANALYSIS / "validate_atm_pos_claims.py")],
    )
    results.append(("4d. Validate claims", passed, out))

    return results


def main():
    ap = argparse.ArgumentParser(description="ATM/POS pipeline eval gate")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--xlsx",   nargs="+", help="One or more XLSX files to ingest")
    group.add_argument("--period", help="Re-validate existing period (YYYY-MM-DD)")
    ap.add_argument("--skip-insights", action="store_true",
                    help="Skip Stages 4b/4c/4d (data-only run)")
    ap.add_argument("--skip-build", action="store_true",
                    help="Skip tsc + npm run build (use when web/ hasn't changed)")
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

    # Run insight stages unless skipped or prior stages failed
    if not args.skip_insights:
        prior_ok = all(r[1] is True or r[1] is None for r in all_results)
        if prior_ok:
            print("\n  Running insight stages (4b/4c/4d)…")
            all_results.extend(run_insight_stages())
        else:
            all_results.append(("4b/4c/4d. Insights", None, "skipped — upstream failures"))

    # Web CSV integrity check
    prior_ok = all(r[1] is True or r[1] is None for r in all_results)
    if prior_ok:
        passed, note = check_atm_pos_csv()
        all_results.append(("5.  Web CSV integrity", passed, note))
    else:
        all_results.append(("5.  Web CSV integrity", None, "skipped — upstream failures"))

    # Signal history integrity check
    prior_ok = all(r[1] is True or r[1] is None for r in all_results)
    if prior_ok:
        passed, note = check_signal_history()
        all_results.append(("5b. Signal history integrity", passed, note))
    else:
        all_results.append(("5b. Signal history integrity", None, "skipped — upstream failures"))

    # Signal freshness — DB rows must match a fresh recompute from the CSV
    prior_ok = all(r[1] is True or r[1] is None for r in all_results)
    if prior_ok:
        passed, note = check_signal_freshness()
        all_results.append(("5b2. Signal freshness (DB vs CSV)", passed, note))
    else:
        all_results.append(("5b2. Signal freshness (DB vs CSV)", None, "skipped — upstream failures"))

    # Stage 5c: system model (skeleton regen + v3.0 validation)
    prior_ok = all(r[1] is True or r[1] is None for r in all_results)
    if prior_ok:
        passed, note = check_system_model()
        all_results.append(("5c. system_model.json (v4.0 skeleton + causal)", passed, note))
    else:
        all_results.append(("5c. system_model.json (v3.0)", None, "skipped — upstream failures"))

    # Stage 5d: S3 dynamic state + live opportunities
    prior_ok = all(r[1] is True or r[1] is None for r in all_results)
    if prior_ok:
        passed, note = check_system_state()
        all_results.append(("5d. system_state + opportunities (S3)", passed, note))
    else:
        all_results.append(("5d. system_state + opportunities (S3)", None, "skipped — upstream failures"))

    # Check 4f: opportunity number traceability (advisory) — same gate as SIBC
    prior_ok = all(r[1] is True or r[1] is None for r in all_results)
    if prior_ok:
        passed, note = check_opportunity_traceability()
        all_results.append(("4f. opportunity traceability (strict)", passed, note))
    else:
        all_results.append(("4f. opportunity traceability (strict)", None, "skipped — upstream failures"))

    # Stage 5.5: generate UI annotation JSON from evaluation output
    prior_ok = all(r[1] is True or r[1] is None for r in all_results)
    report_script = ANALYSIS / "generate_atm_pos_analysis_report.py"
    if prior_ok and report_script.exists():
        passed, out = run(
            "Stage 5.5",
            [sys.executable, str(report_script)],
        )
        last_line = (out.splitlines()[-1] if out else "")[:45]
        all_results.append(("5.5 generate_atm_pos_report", passed, last_line))
    else:
        reason = "script not found" if not report_script.exists() else "skipped — upstream failures"
        all_results.append(("5.5 generate_atm_pos_report", None, reason))

    # TypeScript build gate
    if args.skip_build:
        all_results.append(("6.  tsc + npm run build", None, "skipped (--skip-build)"))
    else:
        prior_ok = all(r[1] is True or r[1] is None for r in all_results)
        if prior_ok:
            print("\n  Running tsc + npm run build (this may take ~30s)…")
            passed, out = check_build()
            last_line = (out.splitlines()[-1] if out else "")[:50]
            all_results.append(("6.  tsc + npm run build", passed, last_line))
        else:
            all_results.append(("6.  tsc + npm run build", None, "skipped — upstream failures"))

    overall = print_summary(all_results)
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
