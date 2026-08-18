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

Three HARD checks (gate-able via --strict):
  1. Script references — every `xxx.py` named in a doc must exist on disk.
  2. Artifact references — every repo-relative artifact path (web/… or analysis/…
     ending .json/.csv/.db/.ts) named in a doc must exist on disk.
  3. COUNTS — a doc that states how many signals or tests exist must state the real number.
     Paths were guarded from the start; counts were not, and they rotted exactly as you would
     expect. CLAUDE.md claimed 225 signals in one row and 90 in another while the registry held
     230, and still described the test suite as "9 tests" after it had grown past 300. A number
     in a living doc is a claim about the system, so it gets checked like a path.
One ADVISORY signal (never fails):
  4. Scripts in the graph never mentioned in any living doc (undocumented surface).

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
    "analysis/cross/README.md", "analysis/pipelines/README.md",
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


# ── Check 4: evidence pointers inside JSON ───────────────────────────────────
# reconcile has always read the prose docs and never the data files, so a measurement could cite
# a script that no longer exists and nothing noticed. The AI PM register's own admission rule is
# "no publish without a value AND a source file" — which only means something if the source file
# is real. Two of its published measurements cited analysis/newsletter/validate_newsletter.py,
# deleted when the newsletter folded into distribution/ in July.

EVIDENCE_JSON = [
    ("analysis/distribution/ai_pm_register.json", "topics[].measurements[].source"),
]

_PATH_TOKEN = re.compile(r"(?:analysis|web|archive)/[\w./-]+\.(?:py|json|ts|tsx|csv|db|md)")


def _register_sources(doc: dict):
    for topic in doc.get("topics", []):
        for meas in topic.get("measurements", []):
            if meas.get("source"):
                yield topic.get("id"), meas["source"]


def check_evidence_pointers() -> list[str]:
    """Every file path named as a measurement's source must exist."""
    findings = []
    for rel, where in EVIDENCE_JSON:
        path = ROOT / rel
        if not path.exists():
            findings.append(f"{rel}: missing (declared as an evidence source in {where})")
            continue
        doc = json.loads(path.read_text())
        for topic_id, source in _register_sources(doc):
            # A source may name several files, joined by + or ·. Check each real path token.
            for token in _PATH_TOKEN.findall(source):
                if not (ROOT / token).exists():
                    findings.append(f"{rel}: topic {topic_id} cites {token}, which does not exist")
    return findings


# ── Check 3: stated counts ────────────────────────────────────────────────────
# Each entry: a human name, how to count it for real, and the patterns that state it in prose.
# Deliberately narrow — only counts with one unambiguous source of truth. A doc is free to say
# "~200 signals"; this fires on a precise figure that is precisely wrong.

def _registry_signal_count() -> int:
    return len(json.loads((ANALYSIS / "signals" / "registry.json").read_text())["signals"])


def _test_count() -> int:
    """Test functions across the suite, counted the way pytest collects the simple cases."""
    total = 0
    for f in (ANALYSIS / "tests").glob("test_*.py"):
        total += len(re.findall(r"^def (test_\w+)", f.read_text(), re.M))
    return total


COUNT_CHECKS = [
    ("registry signals", _registry_signal_count,
     [r"registry\.json \(\*\*(\d+) signals\*\*\)", r"Universal signal catalog — (\d+) signals"]),
    ("test functions", _test_count,
     [r"(\d+) tests? \(was \d+\)"]),
]


def check_counts(docs_text: dict) -> list[str]:
    findings = []
    for name, truth_fn, patterns in COUNT_CHECKS:
        try:
            actual = truth_fn()
        except Exception as e:                       # noqa: BLE001 — a broken source is not a doc bug
            findings.append(f"count check '{name}' could not resolve its source: {e}")
            continue
        for doc, text in docs_text.items():
            for pat in patterns:
                for m in re.finditer(pat, text):
                    stated = int(m.group(1))
                    if stated != actual:
                        findings.append(
                            f"{doc}: states {stated} {name}, actual is {actual}")
    return findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="exit 1 on any hard drift")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    pyset = known_py()
    hard, future_total = 0, 0
    all_text = ""
    docs_text = {}
    for rel in DOCS:
        bad_py, bad_art, future, miss = check_doc(rel, pyset)
        if miss:
            if not args.quiet:
                print(f"  ⚠ {miss}")
            continue
        docs_text[rel] = (ROOT / rel).read_text(encoding="utf-8")
        all_text += docs_text[rel]
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

    # Check 3: numbers a doc states about the system must be the real numbers.
    count_findings = check_counts(docs_text)
    if count_findings:
        print("✗ stated counts disagree with the system")
        for f in count_findings:
            print(f"    {f}")
        hard += len(count_findings)
    elif not args.quiet:
        print("✓ stated counts match the system")

    # Check 4: evidence pointers inside declared JSON.
    evidence_findings = check_evidence_pointers()
    if evidence_findings:
        print("✗ evidence pointers name files that do not exist")
        for f in evidence_findings:
            print(f"    {f}")
        hard += len(evidence_findings)
    elif not args.quiet:
        print("✓ evidence pointers resolve")

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
