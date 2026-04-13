#!/usr/bin/env python3
"""
run_evals.py — India Credit Lens
----------------------------------
Master evaluation orchestrator. Runs all validation checks against a given
period's outputs and prints a summary table.

Checks run (in order):
  1. validate_sections.py          on rbi_sibc/<period>/sections.json
  2. validate_annotations.py       on rbi_sibc/<period>/annotations_draft.ts
  3. validate_annotations.py       on web/lib/reports/rbi_sibc.ts  (live)
  4. validate.py                   on rbi_sibc/<period>/system_model.json
  5. validate.py --check-subsystems on system_model.json + subsystems.json
  6. tsc --noEmit + npm run build   in web/

Usage:
    # Run against Jan 2026 period (default)
    python3 run_evals.py

    # Run against a specific period
    python3 run_evals.py --period 2026-02-27

    # Run against merged outputs
    python3 run_evals.py --merged

    # Skip the TypeScript/build check (useful when web/ hasn't changed)
    python3 run_evals.py --skip-build

Exit codes:
    0 = all checks passed
    1 = one or more checks failed
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
from datetime import date

# ── Repo root ─────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
ANALYSIS  = REPO_ROOT / "analysis"
WEB       = REPO_ROOT / "web"

# ── ANSI colours ──────────────────────────────────────────────────────────────

GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
RESET  = "\033[0m"
BOLD   = "\033[1m"


def col(text, colour):
    return f"{colour}{text}{RESET}"


# ── Run a subprocess check ────────────────────────────────────────────────────

def run_check(label, cmd, cwd=None):
    """Run a shell command, capture output, return (passed, stdout, stderr)."""
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd or REPO_ROOT),
            capture_output=True,
            text=True,
        )
        return proc.returncode == 0, proc.stdout, proc.stderr
    except FileNotFoundError as e:
        return False, "", f"Command not found: {e}"


# ── Individual checks ─────────────────────────────────────────────────────────

def check_web_data():
    """Verify web/public/data/rbi_sibc_consolidated.csv exists and is non-empty."""
    csv_path = WEB / "public" / "data" / "rbi_sibc_consolidated.csv"
    if not csv_path.exists():
        return False, "", f"Web CSV not found: {csv_path} — run update_web_data.py"
    size = csv_path.stat().st_size
    if size < 1000:
        return False, "", f"Web CSV suspiciously small ({size} bytes) — may be empty"
    # Count rows quickly
    with open(csv_path) as f:
        rows = sum(1 for _ in f) - 1  # minus header
    return True, f"{rows} data rows", ""


def check_sections(period_dir, merged=False):
    sections_path = period_dir / "sections.json"
    if not sections_path.exists():
        return False, "", f"File not found: {sections_path}"
    cmd = [sys.executable, str(ANALYSIS / "validate_sections.py"), str(sections_path)]
    if merged:
        cmd.append("--merged")
    return run_check("sections", cmd, cwd=ANALYSIS)


def check_annotations_draft(period_dir):
    ann_path = period_dir / "annotations_draft.ts"
    if not ann_path.exists():
        return None, "", f"File not found (skipped): {ann_path}"
    cmd = [sys.executable, str(ANALYSIS / "validate_annotations.py"), str(ann_path)]
    return run_check("annotations_draft", cmd, cwd=ANALYSIS)


def check_annotations_live():
    live_path = WEB / "lib" / "reports" / "rbi_sibc.ts"
    if not live_path.exists():
        return False, "", f"File not found: {live_path}"
    cmd = [sys.executable, str(ANALYSIS / "validate_annotations.py"), str(live_path)]
    return run_check("annotations_live", cmd, cwd=ANALYSIS)


def check_system_model(period_dir):
    model_path = period_dir / "system_model.json"
    if not model_path.exists():
        return False, "", f"File not found: {model_path}"
    ann_path = WEB / "lib" / "reports" / "rbi_sibc.ts"
    cmd = [
        sys.executable, str(ANALYSIS / "validate.py"),
        str(model_path),
        "--annotations", str(ann_path),
    ]
    return run_check("system_model", cmd, cwd=ANALYSIS)


def check_subsystems(period_dir, subsystems_path):
    model_path = period_dir / "system_model.json"
    if not model_path.exists():
        return False, "", f"system_model.json not found: {model_path}"
    if not Path(subsystems_path).exists():
        return False, "", f"subsystems.json not found: {subsystems_path}"
    cmd = [
        sys.executable, str(ANALYSIS / "validate.py"),
        str(model_path),
        "--check-subsystems",
        "--subsystems-path", str(subsystems_path),
    ]
    return run_check("subsystems", cmd, cwd=ANALYSIS)


def check_build():
    # Step 1: tsc --noEmit
    tsc_passed, tsc_out, tsc_err = run_check(
        "tsc",
        ["npx", "tsc", "--noEmit"],
        cwd=WEB,
    )
    if not tsc_passed:
        return False, tsc_out, tsc_err

    # Step 2: npm run build
    build_passed, build_out, build_err = run_check(
        "build",
        ["npm", "run", "build"],
        cwd=WEB,
    )
    return build_passed, build_out, build_err


# ── Summary table ─────────────────────────────────────────────────────────────

def print_summary(results):
    w = 72
    print(f"\n{'═' * w}")
    print(f"  {BOLD}India Credit Lens — Eval Summary{RESET}   ({date.today()})")
    print(f"{'═' * w}")
    print(f"  {'Check':<38} {'Status':<10} {'Notes'}")
    print(f"  {'-' * 68}")

    overall = True
    for label, passed, notes in results:
        if passed is None:
            status = col("SKIPPED", YELLOW)
        elif passed:
            status = col("PASS   ", GREEN)
        else:
            status = col("FAIL   ", RED)
            overall = False
        print(f"  {label:<38} {status}  {notes}")

    print(f"{'═' * w}")
    if overall:
        print(f"  {col('✅  ALL CHECKS PASSED', GREEN + BOLD)}")
    else:
        print(f"  {col('❌  ONE OR MORE CHECKS FAILED — resolve errors before proceeding', RED + BOLD)}")
    print(f"{'═' * w}\n")

    return overall


# ── Helpers to extract a one-line summary from subprocess output ──────────────

def one_line_summary(stdout, stderr, passed):
    """Extract the final PASSED/FAILED line or first error line from output."""
    output = (stdout + stderr).strip()
    lines = [l.strip() for l in output.splitlines() if l.strip()]
    # Look for the summary line
    for line in reversed(lines):
        if "PASSED" in line or "FAILED" in line or "ERROR" in line or "error" in line.lower():
            # Shorten to fit column
            return line[:50]
    if lines:
        return lines[-1][:50]
    return ""


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Run all India Credit Lens eval checks")
    ap.add_argument("--period",     default="2026-02-27",
                    help="Period directory name under analysis/rbi_sibc/ (default: 2026-02-27)")
    ap.add_argument("--merged",     action="store_true",
                    help="Also run merged-continuity check on sections.json")
    ap.add_argument("--skip-build", action="store_true",
                    help="Skip tsc + npm run build (use when web/ hasn't changed)")
    args = ap.parse_args()

    period_dir      = ANALYSIS / "rbi_sibc" / args.period
    subsystems_path = ANALYSIS / "rbi_sibc" / args.period / "subsystems.json"

    print(f"\n  Running evals for period: {args.period}")
    print(f"  Period dir : {period_dir}")
    print(f"  Subsystems : {subsystems_path}\n")

    results = []

    # ── Check 1: sections.json ────────────────────────────────────────────────
    passed, out, err = check_sections(period_dir, merged=args.merged)
    notes = one_line_summary(out, err, passed)
    results.append(("1.  sections.json", passed, notes))
    if not passed:
        print(out)
        print(err, file=sys.stderr)

    # ── Check 1b: web CSV ─────────────────────────────────────────────────────
    passed, out, err = check_web_data()
    notes = out if passed else err
    results.append(("1b. web CSV (rbi_sibc_consolidated.csv)", passed, notes[:50]))

    # ── Check 2: annotations_draft.ts ────────────────────────────────────────
    passed, out, err = check_annotations_draft(period_dir)
    label = "2.  annotations_draft.ts"
    if passed is None:
        results.append((label, None, err))
    else:
        notes = one_line_summary(out, err, passed)
        results.append((label, passed, notes))
        if not passed:
            print(out)
            print(err, file=sys.stderr)

    # ── Check 3: live annotations (web/lib/reports/rbi_sibc.ts) ──────────────
    passed, out, err = check_annotations_live()
    notes = one_line_summary(out, err, passed)
    results.append(("3.  annotations live (rbi_sibc.ts)", passed, notes))
    if not passed:
        print(out)
        print(err, file=sys.stderr)

    # ── Check 4: system_model.json ────────────────────────────────────────────
    passed, out, err = check_system_model(period_dir)
    notes = one_line_summary(out, err, passed)
    results.append(("4.  system_model.json", passed, notes))
    if not passed:
        print(out)
        print(err, file=sys.stderr)

    # ── Check 5: subsystems.json ──────────────────────────────────────────────
    passed, out, err = check_subsystems(period_dir, subsystems_path)
    notes = one_line_summary(out, err, passed)
    results.append(("5.  subsystems.json", passed, notes))
    if not passed:
        print(out)
        print(err, file=sys.stderr)

    # ── Check 6: TypeScript build ─────────────────────────────────────────────
    if args.skip_build:
        results.append(("6.  tsc + npm run build", None, "skipped (--skip-build)"))
    else:
        print("  Running tsc + npm run build (this may take ~30s)...")
        passed, out, err = check_build()
        notes = one_line_summary(out, err, passed)
        results.append(("6.  tsc + npm run build", passed, notes))
        if not passed:
            print(out)
            print(err, file=sys.stderr)

    # ── Summary ───────────────────────────────────────────────────────────────
    overall = print_summary(results)
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
