#!/usr/bin/env python3
"""
check_derived_fresh.py — guard against committing stale derived artifacts
-------------------------------------------------------------------------
The 2026-06-13 review found a stale committed S3 artifact: a model edit (S2b force
instances) was committed without re-running the gate that regenerates the dependent
S3 projection, so `system_state_*.json` drifted from its source. The determinism
machinery was correct; the *commit discipline* broke the invariant.

This script re-runs the deterministic (no-LLM) regeneration chain and then checks that no
tracked derived artifact changed. If anything drifted, it has regenerated the file in place
and exits non-zero so the change is surfaced (and can be staged) — converting silent drift
into a hard stop. Intended as a git pre-commit hook (see install below) and runnable by hand.

WHAT IT WATCHES IS NOT WRITTEN HERE. Every stage that rewrites a committed artifact declares
it in its own pipeline manifest (`"derived": [...]`), and this guard runs exactly those stages
in manifest order — which is dependency order. That matters: the previous version kept its own
hand-written copy of both lists and it silently fell behind, leaving `sibc_l1_annotations.json`
and `atm_pos_insights.json` — the two largest artifacts the gate writes — completely unguarded.
Adding a pipeline now teaches the gate and this guard at the same time, in one place.

Excluded by design: signals.db (binary; separate git policy) and everything LLM-generated
(evaluations, opportunity narratives) — neither is reproducible by re-running a script.
Excluded by necessity: ingestion stages, which need the raw XLSX and so cannot re-run here;
they declare no `derived`.

Usage:
    python3 analysis/guards/check_derived_fresh.py            # regenerate + verify clean
    python3 analysis/guards/check_derived_fresh.py --quiet
Install as pre-commit hook:
    ln -sf ../../analysis/git_hooks/pre-commit .git/hooks/pre-commit
"""
import argparse
import sqlite3
import subprocess
import sys
from pathlib import Path

# Bootstrap: <repo>/analysis on sys.path so `from core…` resolves from any cwd now that
# this guard lives under guards/. Move-safe via .git walk (not __file__.parent).
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core.paths import ROOT                        # noqa: E402
from core import manifest as manifest_mod          # noqa: E402

ANALYSIS = ROOT / "analysis"
DB = ANALYSIS / "signals" / "signals.db"
FALLBACK_PERIOD = {"sibc": "2026-05-29", "atm_pos": "2026-04-30"}  # if the DB is empty

# Derived artifacts produced OUTSIDE any pipeline gate: the architecture graph and its
# rendered doc describe the code itself, so they belong to no single pipeline. They are
# regenerated here for the same reason — a stale committed copy is a lying document.
CODE_DERIVED = [
    ("architecture discover", "architecture_discover", []),
    ("architecture render",   "architecture_render",   ["analysis/architecture/graph.json",
                                                        "ARCHITECTURE.generated.md"]),
    # Cross-link candidates are derived from both models but are not a gate stage today.
    ("derive_cross_links",    "derive_cross_links",    ["analysis/cross_source/candidates.json"]),
]


def latest_period(pipeline):
    if not DB.exists():
        return FALLBACK_PERIOD[pipeline]
    con = sqlite3.connect(DB)
    row = con.execute("select max(period) from signals where pipeline=?", (pipeline,)).fetchone()
    con.close()
    return (row and row[0]) or FALLBACK_PERIOD[pipeline]


def run(label, cmd, cwd, quiet):
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"✗ {label} failed:\n{proc.stdout}\n{proc.stderr}", file=sys.stderr)
        return False
    if not quiet:
        print(f"  ✓ {label}")
    return True


def watched_globs():
    """Every committed artifact any pipeline declares, plus the code-derived ones."""
    globs = manifest_mod.derived_globs()
    for _, _, paths in CODE_DERIVED:
        for p in paths:
            if p not in globs:
                globs.append(p)
    return globs


def regenerate(quiet):
    """Re-run every declared regenerating stage, per pipeline, in manifest order."""
    ok = True
    for pid in manifest_mod.PIPELINE_IDS:
        man = manifest_mod.load(pid)
        vars_ = {"$ID": pid, "$LATEST": latest_period(pid), "$PERIOD": "merged", "$XLSX": ""}
        for key, rel in man["paths"].items():
            vars_["$" + key.upper()] = str(ROOT / rel)
        for stage in manifest_mod.regenerating_stages(man):
            cmd, cwd = manifest_mod.resolve(stage, man, vars_)
            ok &= run(f"{stage['id']} {pid}", cmd, cwd, quiet)
    for label, core_name, _ in CODE_DERIVED:
        script, dargs, cwdname = manifest_mod.CORE_MAP[core_name]
        cwd = ANALYSIS if cwdname == "ANALYSIS" else ROOT
        ok &= run(label, [sys.executable, str(ANALYSIS / script)] + dargs, cwd, quiet)
    return ok


def drifted_files(globs):
    """Derived files whose freshly-regenerated content differs from what is staged.
    Uses working-tree-vs-index (`git diff`), NOT vs-HEAD: a commit that correctly
    includes the regenerated output stages it, so regeneration reproduces it and there
    is no unstaged diff (pass). A commit that omits/stales a derived file leaves an
    unstaged diff after regeneration (fail)."""
    out = subprocess.run(["git", "diff", "--name-only", "--"] + globs,
                         cwd=ROOT, capture_output=True, text=True).stdout
    return [ln for ln in out.splitlines() if ln.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--list", action="store_true",
                    help="print the watched artifacts (as declared by the manifests) and exit")
    args = ap.parse_args()

    globs = watched_globs()
    if args.list:
        print(f"{len(globs)} watched derived artifact(s), declared by the pipeline manifests:")
        for g in globs:
            print(f"  {g}")
        return 0

    if not args.quiet:
        print(f"Regenerating {len(globs)} deterministic derived artifacts (no LLM)…")
    if not regenerate(args.quiet):
        print("✗ regeneration failed — fix the pipeline before committing", file=sys.stderr)
        return 2

    drifted = drifted_files(globs)
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
