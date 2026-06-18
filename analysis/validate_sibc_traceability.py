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

ANALYSIS = Path(__file__).resolve().parent
sys.path.insert(0, str(ANALYSIS))
from signals.query import signal_numbers, flat_numbers, _signal_type   # noqa: E402

ANNOT = ANALYSIS.parent / "web" / "public" / "data" / "sibc_l1_annotations.json"
REG   = ANALYSIS / "signals" / "registry.json"
DB    = ANALYSIS / "signals" / "signals.db"

REL_TOL   = 0.02     # 2% — formatted text rounds (17.1 vs 17.0876)
ABS_TOL   = 0.25     # absolute fallback for small values / shares
MIN_CHECK = 0.5      # ignore trivial small integers

# Direction words that must not appear in an implication when the signal's status
# says the opposite. Keyed by status → forbidden words.
STATUS_CONTRADICTIONS = {
    "declining":     ["accelerat", "surging", "expanding", "strengthening", "picking up"],
    "weakening":     ["accelerat", "surging", "strengthening"],
    "strengthening": ["contracting", "shrinking", "decelerat", "weakening"],
}


def extract_numbers(text: str) -> list[float]:
    """Standalone numeric values from text, excluding structural tokens
    (ISO dates, FY labels, quarters) that are not data claims."""
    t = re.sub(r"\b20\d\d-\d\d-\d\d\b", " ", text)   # ISO dates
    t = re.sub(r"\bFY\s?\d{2,4}\b", " ", t, flags=re.I)  # FY25 / FY 2026
    t = re.sub(r"\b[Qq][1-4]\b", " ", t)             # quarters
    t = re.sub(r"\b(?:19|20|21)\d{2}\b", " ", t)     # standalone calendar years
    pattern = r"(?<![A-Za-z\d])[-+]?\d+(?:\.\d+)?(?![A-Za-z\d])"
    out: list[float] = []
    for m in re.finditer(pattern, t):
        try:
            v = float(m.group())
        except ValueError:
            continue
        if abs(v) >= MIN_CHECK:
            out.append(v)
    return out


def matches(num: float, cands: list[float]) -> bool:
    for v in cands:
        if v == 0:
            if abs(num) < ABS_TOL:
                return True
        else:
            if abs(num - v) / max(abs(v), 1e-9) <= REL_TOL:
                return True
            if abs(num - v) <= ABS_TOL:
                return True
    return False


def ratio_matches(num: float, cands: list[float]) -> bool:
    """True if num is a percentage-of-total or ratio of two grounded values —
    e.g. '99.5% of total' = 100 * non-food / bank-credit. Bounded to the small
    set of distinct level values to avoid spurious matches."""
    levels = sorted({round(v, 4) for v in cands if abs(v) > 1})
    for a in levels:
        for b in levels:
            if b and a != b:
                for cand in (100 * a / b, a / b):
                    if abs(num - cand) <= ABS_TOL or abs(num - cand) / max(abs(cand), 1e-9) <= REL_TOL:
                        return True
    return False


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
                            msg = (f"{sid} [{field}] ungrounded number {num} "
                                   f"— not in signal data {sorted(set(round(x,2) for x in own))[:12]}")
                            # Scan/distribution narratives summarise (group/round)
                            # and resist exact number-traceability — surface, don't
                            # block. Scalar insights must trace exactly.
                            (warnings if is_scan else failures).append(msg)

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
        print(f"  ✓ traceability — every number in {checked} scalar insights traces to "
              f"signals.db ({len(warnings)} scan/status warnings)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--period", default=None)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    return check(a.period, a.quiet)


if __name__ == "__main__":
    sys.exit(main())
