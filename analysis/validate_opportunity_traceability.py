#!/usr/bin/env python3
"""
validate_opportunity_traceability.py — Check 2h: opportunity number traceability
--------------------------------------------------------------------------------
Opportunities derive from the Layer 2 system model and aggregate multiple (often
cross-system) signals, so a single card's numbers can span BOTH pipelines. This
holds opportunity body/chain/implication to the same standard as insight
Check 2g: every number must trace to a value the computed signals produced in
signals.db.

Ground truth: each opportunity is scoped to its declared `evidence` signals'
numbers (small, same-domain set — meaningful matching). A period-wide fallback
is deliberately NOT used: across both pipelines that set is ~3.8k mixed-magnitude
values where almost any number matches by coincidence (the check would be
vacuous). Consequence: a card that cites a number but declares no `evidence`
fails — it must declare its sources to be verifiable (same rule as payments'
sourceSignals). Number-free cards (e.g. qualitative cross-system narratives)
pass. Matching (direct + ratio + tolerance, unit-aware) reused from Check 2g.

Usage: python3 analysis/validate_opportunity_traceability.py [--quiet]
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

ANALYSIS = Path(__file__).resolve().parent
sys.path.insert(0, str(ANALYSIS))
from signals.query import signal_numbers, flat_numbers          # noqa: E402
from validate_sibc_traceability import extract_numbers, matches, ratio_matches  # noqa: E402

FEED = ANALYSIS.parent / "web" / "public" / "data" / "opportunities_feed.json"
REG  = ANALYSIS / "signals" / "registry.json"
DB   = ANALYSIS / "signals" / "signals.db"


def _latest_periods(conn) -> dict:
    return dict(conn.execute(
        "SELECT pipeline, MAX(period) FROM signals GROUP BY pipeline").fetchall())


def _numbers_for(conn, registry, latest, sids) -> list[float]:
    """Union of flat_numbers for the given signal ids (each at its pipeline's latest)."""
    nums: list[float] = []
    for sid in sids:
        sig = registry.get(sid)
        if not sig:
            continue
        pl = sig.get("pipeline")
        if pl in latest:
            nums += flat_numbers(signal_numbers(conn, sid, sig, pl, latest[pl]))
    return nums


def _opps(feed) -> list[dict]:
    out: list[dict] = []
    for _pl, v in feed.get("pipelines", {}).items():
        out += v if isinstance(v, list) else v.get("items", [])
    out += feed.get("cross_system", [])
    return out


def check(quiet: bool = False, strict: bool = False) -> int:
    registry = json.loads(REG.read_text())["signals"]
    feed     = json.loads(FEED.read_text())
    conn     = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    latest   = _latest_periods(conn)

    failures: list[str] = []
    checked = 0
    for opp in _opps(feed):
        checked += 1
        oid = opp.get("id", "?")
        evidence = opp.get("evidence") or []
        texts = {
            "body":        opp.get("body", ""),
            "implication": opp.get("implication", ""),
            "chain":       " ".join(opp.get("chain") or []),
        }
        legit = _numbers_for(conn, registry, latest, evidence) if evidence else []
        for field, text in texts.items():
            for num in extract_numbers(text):
                if not evidence:
                    failures.append(
                        f"{oid} [{field}] number {num} but the card declares no "
                        f"evidence signals to trace it to")
                elif not matches(num, legit) and not ratio_matches(num, legit):
                    failures.append(
                        f"{oid} [{field}] ungrounded number {num} — not in evidence "
                        f"signals {sorted(set(round(x, 1) for x in legit))[:14]}")

    conn.close()

    if failures:
        tag = "✗ FAILED" if strict else "⚠ warnings"
        print(f"  {tag} — opportunity traceability: {len(failures)} ungrounded number(s) "
              f"across {checked} opportunities{'' if strict else ' (non-blocking)'}:",
              file=sys.stderr)
        for f in failures[:30]:
            print(f"    {f}", file=sys.stderr)
        if len(failures) > 30:
            print(f"    ... and {len(failures) - 30} more", file=sys.stderr)
        # Default = advisory (Layer 2 narratives are LLM + complex cross-signal;
        # grounding loop is a follow-up). --strict turns it into a hard gate once
        # generate_opportunity_narrative.py is fully grounded.
        return 1 if strict else 0

    if not quiet:
        print(f"  ✓ opportunity traceability — every number in {checked} opportunities "
              f"traces to its evidence signals")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--strict", action="store_true",
                    help="hard-fail on ungrounded opportunity numbers (default: advisory warning)")
    a = ap.parse_args()
    return check(a.quiet, a.strict)


if __name__ == "__main__":
    sys.exit(main())
