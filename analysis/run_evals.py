#!/usr/bin/env python3
"""
run_evals.py — India Credit Lens
----------------------------------
Master evaluation orchestrator. Runs all validation checks against a given
period's outputs and prints a summary table.

Checks run (in order):
  0.  validate_timeline.py          on rbi_sibc/timeline.json (always runs first)
  1.  validate_sections.py          on rbi_sibc/<period>/sections.json
  1b. web CSV duplicate-month check  on web/public/data/rbi_sibc_consolidated.csv
                                     auto-fixes by re-running update_web_data.py
  2.  validate_annotations.py       on rbi_sibc/<period>/annotations_draft.ts
  2b. validate_content.py           on annotations_draft.ts + insights/gaps/opp .md
                                     checks dates, growth rates, ₹ values vs sections.json
  2c. validate_claims.py            on rbi_sibc/<period>/system_model.json
                                     checks claim_type + source on driver/opp/pressure/gap nodes
                                     FAIL if claim_type missing or inference has no source
                                     WARN (non-blocking) if hypothesis nodes present
  3.  validate_annotations.py       on web/lib/reports/rbi_sibc.ts  (live)
  4.  validate.py                   on rbi_sibc/<period>/system_model.json
  5.  validate.py --check-subsystems on system_model.json + subsystems.json
  6.  tsc --noEmit + npm run build   in web/

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
import json
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
    """
    Check web/public/data/rbi_sibc_consolidated.csv:
      - Exists and is non-empty
      - No month-level duplicate rows (same statement/code/sector/year-month)

    If duplicates are found, automatically re-runs update_web_data.py to fix
    them in-place, then re-checks. Reports what was auto-fixed.
    """
    import pandas as pd

    csv_path = WEB / "public" / "data" / "rbi_sibc_consolidated.csv"

    if not csv_path.exists():
        return False, "", f"Web CSV not found — run update_web_data.py"
    if csv_path.stat().st_size < 1000:
        return False, "", f"Web CSV suspiciously small — may be empty"

    def count_dupes(path):
        df = pd.read_csv(path, dtype=str)
        df["_ym"] = pd.to_datetime(df["date"], errors="coerce").dt.to_period("M").astype(str)
        dupes = df.groupby(["statement", "code", "sector", "_ym"])["date"].nunique()
        return int((dupes > 1).sum()), len(df)

    dupe_count, row_count = count_dupes(csv_path)

    def check_canonical_dates(path):
        """All dates must be the last day of their month (canonical period-end)."""
        from calendar import monthrange
        df = pd.read_csv(path, dtype=str)
        bad = []
        for raw in df["date"].dropna().unique():
            try:
                d = pd.to_datetime(raw).date()
            except Exception:
                bad.append(f"unparseable: {raw}")
                continue
            # Apr 1-7 should have been normalised to Mar 31
            if d.month == 4 and d.day <= 7:
                bad.append(f"{raw} (should be {d.year}-03-31 — Apr fortnightly not normalised)")
                continue
            last = monthrange(d.year, d.month)[1]
            if d.day != last:
                bad.append(f"{raw} (should be {d.year}-{d.month:02d}-{last:02d})")
        return bad

    if dupe_count == 0:
        bad_dates = check_canonical_dates(csv_path)
        if bad_dates:
            return False, "", (
                f"{len(bad_dates)} non-canonical date(s) — run update_web_data.py to normalise: "
                + "; ".join(bad_dates[:3])
            )
        return True, f"{row_count} rows, 0 duplicate months", ""

    # ── Duplicates found — auto-fix via update_web_data.py ───────────────────
    fix_note = f"{dupe_count} duplicate month(s) found — auto-fixing..."
    print(f"\n  ⚠️  {fix_note}")

    fix_passed, fix_out, fix_err = run_check(
        "update_web_data",
        [sys.executable, str(ANALYSIS / "update_web_data.py")],
        cwd=REPO_ROOT,
    )

    if not fix_passed:
        return False, "", (
            f"{dupe_count} duplicate month(s) found; "
            f"auto-fix via update_web_data.py failed: {fix_err[:80]}"
        )

    # Re-check after fix
    dupe_count_after, row_count_after = count_dupes(csv_path)
    if dupe_count_after > 0:
        return False, "", (
            f"Still {dupe_count_after} duplicate month(s) after auto-fix — "
            "investigate update_web_data.py"
        )

    return True, (
        f"{row_count_after} rows — auto-fixed {dupe_count} duplicate month(s)"
    ), ""


def check_timeline():
    """Check 0: validate timeline.json — always runs first, regardless of period."""
    timeline_path = ANALYSIS / "rbi_sibc" / "timeline.json"
    if not timeline_path.exists():
        return False, "", f"timeline.json not found: {timeline_path}"
    cmd = [sys.executable, str(ANALYSIS / "validate_timeline.py"),
           "--path", str(timeline_path)]
    return run_check("timeline", cmd, cwd=ANALYSIS)


def check_format(period_dir):
    """Check 0.5: verify format_report.json exists, format is confirmed and supported.

    Reads the report written by detect_format.py.  Missing report is a WARN
    (backwards-compat for periods processed before this check was added).
    Unsupported or unconfirmed format is a hard FAIL.
    """
    if period_dir.name == "merged":
        return None, "", "skipped for merged"

    report_path = period_dir / "format_report.json"
    if not report_path.exists():
        return None, "", "format_report.json missing — run detect_format.py first (skipped for legacy periods)"

    try:
        with open(report_path) as f:
            report = json.load(f)
    except Exception as e:
        return False, "", f"Cannot read format_report.json: {e}"

    fmt_id    = report.get("format_id", "unknown")
    supported = report.get("supported", False)
    confirmed = report.get("confirmed_by_user", False)

    if not confirmed:
        return False, "", f"Format not confirmed by user — re-run detect_format.py"
    if not supported:
        return False, "", (
            f"Format '{fmt_id}' not supported — add parser support, "
            f"then re-run extract_sibc.py"
        )
    return True, f"format={fmt_id}, confirmed=true, supported=true", ""


def check_sections(period_dir, merged=False):
    # Merged directory uses sections_merged.json; per-period uses sections.json
    sections_path = period_dir / ("sections_merged.json" if period_dir.name == "merged" else "sections.json")
    if not sections_path.exists():
        return False, "", f"File not found: {sections_path}"
    cmd = [sys.executable, str(ANALYSIS / "validate_sections.py"), str(sections_path)]
    if merged or period_dir.name == "merged":
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
    # Prefer annotations_draft.ts (per-period), then annotations_merged.ts (merged),
    # then fall back to live rbi_sibc.ts.
    draft_path  = period_dir / "annotations_draft.ts"
    merged_path = period_dir / "annotations_merged.ts"
    live_path   = WEB / "lib" / "reports" / "rbi_sibc.ts"
    ann_path = (draft_path if draft_path.exists()
                else merged_path if merged_path.exists()
                else live_path)
    cmd = [
        sys.executable, str(ANALYSIS / "validate.py"),
        str(model_path),
        "--annotations", str(ann_path),
    ]
    return run_check("system_model", cmd, cwd=ANALYSIS)


def check_content(period_dir, sections_path):
    """Content accuracy check: dates, growth rates, ₹ values in annotations + markdown."""
    # For merged directory, sections_merged.json is the authoritative file
    if period_dir.name == "merged" and not sections_path.exists():
        sections_path = period_dir / "sections_merged.json"
    if not sections_path.exists():
        return None, "", f"sections.json not found — skipping content check"
    ann_ts = period_dir / "annotations_draft.ts"
    if not ann_ts.exists():
        ann_ts = period_dir / "annotations_merged.ts"
    if not ann_ts.exists():
        return None, "", f"No annotations file found — skipping content check"
    cmd = [
        sys.executable, str(ANALYSIS / "validate_content.py"),
        "--period", period_dir.name,
    ]
    # For merged, use --merged flag
    if period_dir.name == "merged":
        cmd = [sys.executable, str(ANALYSIS / "validate_content.py"), "--merged"]
    return run_check("content", cmd, cwd=ANALYSIS)


def check_claims(period_dir):
    """Check 2c: validate claim_type + source on merged system model nodes.

    Always checks the merged model — that is the authoritative source of cross-period
    structural claims (drivers, opportunities, pressures, gaps). Per-period models are
    raw analysis snapshots and are not subject to this check.
    """
    # Always validate the merged model regardless of which per-period is active
    merged_model = ANALYSIS / "rbi_sibc" / "merged" / "system_model.json"
    model_path = merged_model if merged_model.exists() else period_dir / "system_model.json"
    if not model_path.exists():
        return None, "", f"system_model.json not found — skipping claim check"
    cmd = [sys.executable, str(ANALYSIS / "validate_claims.py"), str(model_path)]
    return run_check("claims", cmd, cwd=ANALYSIS)


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
    ap.add_argument("--period",     default="2026-03-30",
                    help="Period directory name under analysis/rbi_sibc/ (default: 2026-03-30)")
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

    # ── Check 0: timeline.json ────────────────────────────────────────────────
    passed, out, err = check_timeline()
    notes = one_line_summary(out, err, passed)
    results.append(("0.  timeline.json", passed, notes))
    if not passed:
        print(out)
        print(err, file=sys.stderr)

    # ── Check 0.5: format_report.json ────────────────────────────────────────
    passed, out, err = check_format(period_dir)
    label = "0.5 format_report.json"
    if passed is None:
        results.append((label, None, err))
    else:
        notes = out if passed else err
        results.append((label, passed, notes[:60]))
        if not passed:
            print(err, file=sys.stderr)

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

    # ── Check 2b: content accuracy (numbers/dates in annotation bodies + docs) ─
    sections_path = period_dir / ("sections_merged.json" if period_dir.name == "merged" else "sections.json")
    passed, out, err = check_content(period_dir, sections_path)
    label = "2b. content accuracy (annotations + docs)"
    if passed is None:
        results.append((label, None, err))
    else:
        notes = one_line_summary(out, err, passed)
        if passed:
            # Extract the summary line from stdout for display
            summary_lines = [l.strip() for l in (out + err).splitlines() if '✅' in l or '⚠️' in l]
            notes = summary_lines[-1][:50] if summary_lines else "passed"
        results.append((label, passed, notes))
        if not passed:
            print(out)
            print(err, file=sys.stderr)

    # ── Check 2c: claim sourcing (claim_type + source on system model nodes) ──
    passed, out, err = check_claims(period_dir)
    label = "2c. claim sourcing (system_model.json)"
    if passed is None:
        results.append((label, None, err))
    else:
        notes = one_line_summary(out, err, passed)
        # Extract hypothesis warning line for display if present
        for line in (out + err).splitlines():
            if "hypothesis" in line.lower() and ("◈" in line or "warn" in line.lower()):
                notes = line.strip()[:50]
                break
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
