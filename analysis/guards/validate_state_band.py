#!/usr/bin/env python3
"""
validate_state_band.py — every number in the standing state band traces to a stored row
────────────────────────────────────────────────────────────────────────────────────────
The state band (DASHBOARD_SPEC §16) is the first surface on the dashboard that publishes a
Layer-2 reading. Layer 2 is exactly where this project has been burned: coherence lives in a
state file rather than signals.db, so Check 4f could not ground it, and an invented `0.73`
passed. The rule that came out of that — *never publish a number a gate cannot ground* — is
what this stage enforces for the band.

Two things make it enforceable at all:

* the band's sentences are rendered in Python and shipped as strings, so there is a single
  text to scan (a browser that formats numbers is a publishing surface no validator sees);
* each block DECLARES the signals it stands on, so the ground truth is that block's own rows
  and not the period-wide pool. Period-wide scope is how a traceability gate quietly dies —
  at SIBC's ~1,700 values per period, "in range somewhere" is not a check.

Policy is `traceability.DISTRIBUTION`, the tightest of the three: the band never reasons
about a magnitude in prose, it quotes stored values at one decimal, so the only honest gap
is display rounding. The card policies' ±0.25 slack would just be a wider net here.

    python3 analysis/guards/validate_state_band.py --pipeline sibc
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

from core.traceability import DISTRIBUTION as POLICY, extract_numbers, matches   # noqa: E402

DATA = ROOT / "web" / "public" / "data"
DB = ROOT / "analysis" / "signals" / "signals.db"


def candidates(conn, registry, pipeline, period, block):
    """The rows this block may quote: its declared signals, at THIS period, for the parent
    total and for the one entity the sentence names.

    Deliberately narrower than `flat_numbers`, which returns a signal's whole history.
    Measured: at history width, four of twenty-three near-miss injections survived — not
    through tolerance slack but by landing on the signal's OWN past readings, a pool of
    160-309 values. The band never quotes history; it quotes this period's value for the
    named entity. Scoping to what it can actually say takes the pool to single digits.

    Non-circular: the entity is read from the block as a LABEL and its numbers are fetched
    independently from signals.db. Nothing the renderer printed is taken on trust.
    """
    wanted = {"total"} | ({block["toward_entity"]} if block.get("toward_entity") else set())
    out: list[float] = []
    for sid in block["source_signals"]:
        if sid not in registry:
            raise SystemExit(f"block declares unknown signal '{sid}'")
        out += [v for (v,) in conn.execute(
            "SELECT value FROM signals WHERE pipeline=? AND period=? AND metric_id=? "
            "AND value IS NOT NULL AND entity_id IN (%s)" % ",".join("?" * len(wanted)),
            (pipeline, period, sid, *sorted(wanted)))]
    return out


def validate(pipeline: str) -> list[str]:
    sidecar = DATA / f"{pipeline}_state.json"
    if not sidecar.exists():
        return [f"{sidecar.name} missing — run stamp_state.py"]
    doc = json.loads(sidecar.read_text())
    period = doc["_meta"]["period"]
    registry = json.loads((ROOT / "analysis" / "signals" / "registry.json").read_text())["signals"]

    failures: list[str] = []
    with sqlite3.connect(DB) as conn:
        for dim, blocks in doc["dimensions"].items():
            for b in blocks:
                cands = candidates(conn, registry, pipeline, period, b)
                for field in ("speed", "speed_short", "mix", "no_speed_note", "no_mix_note"):
                    text = b.get(field)
                    if not text:
                        continue
                    for num in extract_numbers(text, POLICY):
                        if not matches(num, cands, POLICY):
                            failures.append(
                                f"{dim}/{b['cut']}.{field}: {num} traces to none of "
                                f"{b['source_signals']} — “{text}”")
    return failures


def main():
    ap = argparse.ArgumentParser(description="State band number traceability (DASHBOARD_SPEC §16)")
    ap.add_argument("--pipeline", choices=("sibc", "atm_pos"), required=True)
    args = ap.parse_args()

    failures = validate(args.pipeline)
    if failures:
        print(f"  state band traceability FAILED: {len(failures)} ungrounded number(s)")
        for f in failures:
            print(f"    ✗ {f}")
        return 1
    doc = json.loads((DATA / f"{args.pipeline}_state.json").read_text())
    n = sum(len(v) for v in doc["dimensions"].values())
    print(f"  ✓ state band traceable — {n} block(s), every number scoped to its own signals")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
