#!/usr/bin/env python3
"""
validate_sibc_traceability.py — Check 2g: SIBC insight traceability
-------------------------------------------------------------------
The insight TEXT is LLM-generated; this check is the deterministic enforcement
that keeps it honest. Every number in an L1 insight's body, chain
(basis.inferences) and implication must be traceable to a value the signal
actually produced in signals.db — the current value, a prior/Series value, a
range bound, a component rate, or a plain difference of two such values. An
ungrounded number is an LLM-invented figure and fails the gate.

Also checks status-consistency: the implication must not assert a direction
that contradicts the signal's computed status (e.g. "accelerating" when the
status is declining).

Ground truth = signals.db (kept honest by check_signal_freshness.py). This file
never trusts the eval JSON for its numbers.

Usage:
    python3 analysis/validate_sibc_traceability.py [--period YYYY-MM-DD]
"""
import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

# Resolve the real <repo>/analysis dir (location-independent) — this module moved to
# pipelines/sibc/ in the §4 cutover, so __file__.parent is no longer analysis/.
ANALYSIS = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"
sys.path.insert(0, str(ANALYSIS))
from signals.query import signal_numbers, flat_numbers, _signal_type   # noqa: E402
from core.traceability import (                                          # noqa: E402
    SIBC as _POLICY, extract_numbers as _extract,
    matches as _matches_core, ratio_matches as _ratio_core,
)

ANNOT = ANALYSIS.parent / "web" / "public" / "data" / "sibc_l1_annotations.json"
REG   = ANALYSIS / "signals" / "registry.json"
DB    = ANALYSIS / "signals" / "signals.db"

# Number extraction + match tolerances live in core.traceability (SIBC policy); the three
# thin wrappers below preserve this module's public surface (and Check 2g test access).

# Direction words that must not appear in an implication when the signal's status
# says the opposite. Keyed by status → forbidden words.
STATUS_CONTRADICTIONS = {
    "declining":     ["accelerat", "surging", "expanding", "strengthening", "picking up"],
    "weakening":     ["accelerat", "surging", "strengthening"],
    "strengthening": ["contracting", "shrinking", "decelerat", "weakening"],
}


def extract_numbers(text: str) -> list[float]:
    """SIBC-policy number extraction (strips ISO dates / FY / quarters / years)."""
    return _extract(text, _POLICY)


def matches(num: float, cands: list[float]) -> bool:
    return _matches_core(num, cands, _POLICY)


def ratio_matches(num: float, cands: list[float]) -> bool:
    """True if num is a percentage-of-total or ratio of two grounded values (SIBC policy)."""
    return _ratio_core(num, cands, _POLICY)


def check(period: str | None = None, quiet: bool = False) -> int:
    registry = json.loads(REG.read_text())["signals"]
    data = json.loads(ANNOT.read_text())
    ann_period = period or data.get("period")
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)

    # Ground truth = every number the period's computed signals produced. A
    # number is "traceable" if it exists anywhere in this period's data — an
    # insight may legitimately reference a related signal's value (e.g. an
    # absolute-add chain citing the YoY rate). A figure that matches NOTHING in
    # the entire period is an invention.
    facts_by_sid: dict[str, dict] = {}
    period_numbers: list[float] = []
    for sid, sig in registry.items():
        if sig.get("pipeline") != "sibc" or sig.get("layer") != 1:
            continue
        f = signal_numbers(conn, sid, sig, "sibc", ann_period)
        facts_by_sid[sid] = f
        period_numbers += flat_numbers(f)

    failures: list[str] = []   # hard — scalar ungrounded numbers (block the gate)
    warnings: list[str] = []   # soft — scan numbers + status checks (surface only)
    checked = 0

    for section, blocks in data.get("sections", {}).items():
        for kind in ("insights", "gaps"):
            for ann in blocks.get(kind, []):
                sid = ann.get("id")
                sig = registry.get(sid)
                if not sig:
                    continue
                checked += 1
                facts = facts_by_sid.get(sid) or signal_numbers(conn, sid, sig, "sibc", ann_period)

                # Scan signals (entity distributions) are where the model most
                # often invents values, and their numbers are specific — validate
                # them STRICTLY against this signal's own entity values. Scalars
                # may legitimately reference a related signal's number or a ratio,
                # so they validate against the period-wide set + ratios.
                is_scan  = _signal_type(sig) == "scan"
                own      = flat_numbers(facts)
                cand     = own if is_scan else period_numbers

                # 1) Number traceability across body + chain + implication.
                basis = ann.get("basis", {})
                texts = {
                    "body":        ann.get("body", ""),
                    "implication": ann.get("implication", ""),
                    "chain":       " ".join(basis.get("inferences", []) or []),
                }
                for field, text in texts.items():
                    for num in extract_numbers(text):
                        ok = matches(num, cand) or (not is_scan and ratio_matches(num, cand))
                        if not ok:
                            failures.append(
                                f"{sid} [{field}] ungrounded number {num} "
                                f"— not in signal data {sorted(set(round(x,2) for x in own))[:12]}")

                # 2) Status-consistency of the implication (substring heuristic →
                #    can trip on hedged/conditional language → warn, don't block).
                status = (facts.get("status") or "").lower()
                impl   = ann.get("implication", "").lower()
                for bad in STATUS_CONTRADICTIONS.get(status, []):
                    if bad in impl:
                        warnings.append(
                            f"{sid} [implication] says '{bad}…' but signal status is '{status}'"
                        )

    conn.close()

    if warnings and not quiet:
        print(f"  ⚠ {len(warnings)} traceability warning(s) (scan summaries / status) "
              f"— review, non-blocking:", file=sys.stderr)
        for w in warnings[:20]:
            print(f"    {w}", file=sys.stderr)
        if len(warnings) > 20:
            print(f"    ... and {len(warnings) - 20} more", file=sys.stderr)

    if failures:
        print(f"  ✗ traceability FAILED — {len(failures)} scalar insight(s) cite an "
              f"ungrounded number (across {checked} insights):", file=sys.stderr)
        for f in failures[:30]:
            print(f"    {f}", file=sys.stderr)
        return 1

    if not quiet:
        print(f"  ✓ traceability — every number in {checked} insights traces to "
              f"signals.db ({len(warnings)} status warning(s))")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--period", default=None)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    return check(a.period, a.quiet)


if __name__ == "__main__":
    sys.exit(main())
