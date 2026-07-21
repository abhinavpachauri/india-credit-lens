#!/usr/bin/env python3
"""
reconcile.py — validate the prose docs against the code (the "docs can't lie" guard)
-----------------------------------------------------------------------------------
The living markdown docs (CLAUDE.md, PIPELINE_ARCHITECTURE.md, the per-dir CLAUDE.md)
are dense with structural claims — script names, artifact paths — that drift silently
as the code changes. Nothing guards them today, on a platform whose #1 principle is
"single source of truth + deterministic freshness check". This closes that gap: code
is ground truth (the discovered graph + on-disk reality); the docs are VALIDATED
against it.

Two HARD checks (gate-able via --strict):
  1. Script references — every `xxx.py` named in a doc must exist on disk.
  2. Artifact references — every repo-relative artifact path (web/… or analysis/…
     ending .json/.csv/.db/.ts) named in a doc must exist on disk.
One ADVISORY signal (never fails):
  3. Scripts in the graph never mentioned in any living doc (undocumented surface).

Templates ({period}/{pipeline}) and globs (*) are skipped — they can't be checked
literally. Designed to be wired into run_evals / run_atm_pos_evals once stable.

Usage:
    python3 analysis/architecture/reconcile.py            # advisory (exit 0)
    python3 analysis/architecture/reconcile.py --strict   # hard-fail on drift (exit 1)
    python3 analysis/architecture/reconcile.py --quiet
"""
import argparse
import json
import re
import sys
from pathlib import Path

ANALYSIS = Path(__file__).resolve().parent.parent
ROOT = ANALYSIS.parent
GRAPH = ANALYSIS / "architecture" / "graph.json"

# The LIVING docs (system-of-record prose). Handoffs/strategy are historical snapshots
# and intentionally reference retired scripts, so they're excluded.
DOCS = [
    "CLAUDE.md", "CLAUDE.local.md", "PIPELINE_ARCHITECTURE.md", "ARCHITECTURE.md",
    "web/CLAUDE.md", "analysis/rbi_atm_pos/CLAUDE.md",
    "analysis/distribution/NEWSLETTER_CONTEXT.md",
    "analysis/distribution/DISTRIBUTION_SPEC.md",
    # Per-directory READMEs — guarded so the navigational map can't drift from the tree.
    "analysis/core/README.md", "analysis/guards/README.md",
    "analysis/crosssource/README.md", "analysis/pipelines/README.md",
    "analysis/signals/README.md", "analysis/architecture/README.md",
    "analysis/legacy/README.md",
]

# PY: not preceded by a word char or `*` (so the glob `*_atm_pos.py` isn't a ref).
PY_REF_RE = re.compile(r'(?<![\w*])([A-Za-z_][A-Za-z0-9_]*\.py)\b')
# ART: tsx before ts, trailing (?![A-Za-z]) so `.tsx` isn't truncated to `.ts`.
ART_REF_RE = re.compile(
    r'((?:web|analysis)/[A-Za-z0-9_./*{}-]+\.(?:json|csv|db|tsx|ts|mmd)(?![A-Za-z]))')
# Phrases that mark a ref as a deliberate forward reference (planned/unbuilt).
FUTURE = ("does not yet exist", "not yet", "planned", "unbuilt", "pending",
          "to be built", "tbd", "(future")


def known_py():
    skip = {"node_modules", ".git", "__pycache__", ".next"}
    return {p.name for p in ROOT.rglob("*.py") if not (skip & set(p.parts))}


def is_templated(s):
    return "{" in s or "*" in s


def check_doc(rel, pyset):
    path = ROOT / rel
    if not path.exists():
        return [], [], [], f"(missing doc: {rel})"
    bad_py, bad_art, future = set(), set(), set()
    for line in path.read_text(encoding="utf-8").splitlines():
        is_future = any(f in line.lower() for f in FUTURE)
        for m in PY_REF_RE.findall(line):
            if m not in pyset:
                (future if is_future else bad_py).add(m)
        for m in ART_REF_RE.findall(line):
            if is_templated(m) or (ROOT / m).exists():
                continue
            (future if is_future else bad_art).add(m)
    # A ref acknowledged as planned anywhere in the doc is exempt everywhere.
    bad_py -= future
    bad_art -= future
    return sorted(bad_py), sorted(bad_art), sorted(future), None


def undocumented(pyset_in_graph, doc_text):
    return sorted(s for s in pyset_in_graph
                  if Path(s).name not in doc_text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="exit 1 on any hard drift")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    pyset = known_py()
    hard, future_total = 0, 0
    all_text = ""
    for rel in DOCS:
        bad_py, bad_art, future, miss = check_doc(rel, pyset)
        if miss:
            if not args.quiet:
                print(f"  ⚠ {miss}")
            continue
        all_text += (ROOT / rel).read_text(encoding="utf-8")
        future_total += len(future)
        if bad_py or bad_art:
            print(f"✗ {rel}")
            for p in bad_py:
                print(f"    stale script ref:   {p}  (no such .py on disk)")
            for a in bad_art:
                print(f"    dangling artifact:  {a}  (path does not exist)")
            hard += len(bad_py) + len(bad_art)
        elif not args.quiet:
            print(f"✓ {rel}")
        if future and not args.quiet:
            for f in future:
                print(f"    · forward-ref (planned, not a failure): {f}")

    # Advisory: graph scripts whose basename appears in no living doc.
    if GRAPH.exists():
        scripts = json.load(open(GRAPH))["scripts"]
        graph_py = {Path(s["path"]).name for s in scripts.values() if "path" in s}
        undoc = sorted(s for s in graph_py if s not in all_text)
        if not args.quiet:
            print(f"\nadvisory: {len(undoc)} script(s) not mentioned in any living doc")
            for s in undoc[:30]:
                print(f"    · {s}")

    if hard:
        print(f"\n✗ {hard} hard drift finding(s) — docs disagree with code/disk.")
        if args.strict:
            return 1
        print("  (advisory mode — run with --strict to gate)")
    elif not args.quiet:
        print("\n✓ no hard drift — living docs agree with code/disk.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
