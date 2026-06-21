#!/usr/bin/env python3
"""
check_derived_fresh.py — guard against committing stale derived artifacts
-------------------------------------------------------------------------
The 2026-06-13 review found a stale committed S3 artifact: a model edit (S2b force
instances) was committed without re-running the gate that regenerates the dependent
S3 projection, so `system_state_*.json` drifted from its source. The determinism
machinery was correct; the *commit discipline* broke the invariant.

This script re-runs the full DETERMINISTIC (no-LLM) regeneration chain and then checks
that no tracked derived artifact changed. If anything drifted, it regenerated the file
in place and exits non-zero so the change is surfaced (and can be staged) — converting
silent drift into a hard stop. Intended as a git pre-commit hook (see install below)
and runnable by hand.

Chain (all deterministic): skeleton → system_state → derive_opportunities →
compose_ecosystem → derive_cross_links → generate_opportunities_feed.
Excluded by design: signals.db (binary; separate git policy), all LLM narrative.

Usage:
    python3 analysis/check_derived_fresh.py            # regenerate + verify clean
    python3 analysis/check_derived_fresh.py --quiet
Install as pre-commit hook:
    ln -sf ../../analysis/git_hooks/pre-commit .git/hooks/pre-commit
"""
import argparse
import sqlite3
import subprocess
import sys
from pathlib import Path

ANALYSIS = Path(__file__).resolve().parent
ROOT = ANALYSIS.parent
DB = ANALYSIS / "signals" / "signals.db"
PIPELINES = {"sibc": "2026-05-29", "atm_pos": "2026-04-30"}  # fallback if DB empty

# Tracked derived artifacts whose freshness this guard enforces (globs, repo-relative).
DERIVED_GLOBS = [
    "analysis/rbi_sibc/merged/system_model.json",
    "analysis/rbi_atm_pos/merged/system_model.json",
    "analysis/rbi_sibc/merged/system_state_*.json",
    "analysis/rbi_atm_pos/merged/system_state_*.json",
    "analysis/rbi_sibc/merged/opportunities_*.json",
    "analysis/rbi_atm_pos/merged/opportunities_*.json",
    "analysis/cross_source/candidates.json",
    "analysis/cross_source/ecosystem_state_*.json",
    "web/public/data/opportunities_feed.json",
    "web/public/data/atm_pos_chart_series.json",
]


def latest_period(pipeline):
    if not DB.exists():
        return PIPELINES[pipeline]
    con = sqlite3.connect(DB)
    row = con.execute("select max(period) from signals where pipeline=?", (pipeline,)).fetchone()
    con.close()
    return (row and row[0]) or PIPELINES[pipeline]


def run(label, args, quiet):
    proc = subprocess.run([sys.executable, str(ANALYSIS / args[0])] + args[1:],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"✗ {label} failed:\n{proc.stdout}\n{proc.stderr}", file=sys.stderr)
        return False
    if not quiet:
        print(f"  ✓ {label}")
    return True


def regenerate(quiet):
    ok = True
    for p in ("sibc", "atm_pos"):
        per = latest_period(p)
        ok &= run(f"skeleton {p}", ["generate_skeleton.py", "--pipeline", p], quiet)
        ok &= run(f"system_state {p}", ["generate_system_state.py", "--pipeline", p, "--period", per], quiet)
        ok &= run(f"opportunities {p}", ["derive_opportunities.py", "--pipeline", p, "--period", per], quiet)
    ok &= run("compose_ecosystem", ["compose_ecosystem.py"], quiet)
    ok &= run("derive_cross_links", ["derive_cross_links.py"], quiet)
    ok &= run("opportunities_feed", ["generate_opportunities_feed.py"], quiet)
    ok &= run("chart_series atm_pos", ["generate_chart_series.py", "--pipeline", "atm_pos"], quiet)
    return ok


def drifted_files():
    """Derived files whose freshly-regenerated content differs from what is staged.
    Uses working-tree-vs-index (`git diff`), NOT vs-HEAD: a commit that correctly
    includes the regenerated output stages it, so regeneration reproduces it and there
    is no unstaged diff (pass). A commit that omits/stales a derived file leaves an
    unstaged diff after regeneration (fail)."""
    out = subprocess.run(["git", "diff", "--name-only", "--"] + DERIVED_GLOBS,
                         cwd=ROOT, capture_output=True, text=True).stdout
    return [ln for ln in out.splitlines() if ln.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if not args.quiet:
        print("Regenerating deterministic derived artifacts (no LLM)…")
    if not regenerate(args.quiet):
        print("✗ regeneration failed — fix the pipeline before committing", file=sys.stderr)
        return 2

    drifted = drifted_files()
    if drifted:
        print("\n✗ STALE DERIVED ARTIFACTS — these were out of sync with their sources and have\n"
              "  been regenerated. Review and stage them, then re-commit:", file=sys.stderr)
        for f in drifted:
            print(f"    {f}", file=sys.stderr)
        print("\n  (run: git add " + " ".join(drifted) + " )", file=sys.stderr)
        return 1
    if not args.quiet:
        print("✓ all derived artifacts are fresh — safe to commit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
