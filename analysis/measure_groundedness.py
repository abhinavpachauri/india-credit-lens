#!/usr/bin/env python3
"""
measure_groundedness.py — how good is a traceability gate, actually?
---------------------------------------------------------------------
Every published surface on this platform is guarded by a check that says "every
number here traces to a computed signal". Until now, not one of those checks had a
measured catch rate — and a gate that never fails looks identical to a gate that
cannot fail. On 2026-07-21 the distribution gate turned out to be catching 41.5% of
invented numbers while passing every hand-written negative test, because its
ground-truth pool was wide enough to account for almost anything.

So: measure them. For each gate, this injects numbers that should be rejected and
reports how many were, plus the error rate that matters just as much — how often the
gate rejects text that is true. Tightening one moves the other, and a gate that blocks
the truth gets switched off by the person using it.

Two attacks, because they fail differently:

  near-miss     a real value nudged past rounding (8.5% → 9.1%). The realistic
                hallucination: right shape, wrong digit. Caught by tolerance.
  in-range      a fresh value drawn from the range the document already talks in.
                Caught only by SCOPE — a pool of thousands, or one that admits
                derived ratios, will wave these through however tight the tolerance.

    python3 analysis/measure_groundedness.py                 # every gate
    python3 analysis/measure_groundedness.py --gate newsletter --n 400

Add a gate by writing one `Target` — that is the point of this file. AI PM topic #1
(`analysis/distribution/ai_pm_register.json`); log what it prints.
"""
import argparse
import copy
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))
sys.path.insert(0, str(ROOT / "analysis" / "newsletter"))

SEED = 7
INJECTIONS = 200


@dataclass
class Target:
    """One gate, described well enough to attack.

    cases   → real artifacts the gate accepts today
    check   → the gate itself: artifact → list of failures (empty = passed)
    inject  → put `value` into the artifact's own template text, where a fabricated
              number would actually appear
    values  → the numbers the artifact legitimately states, used to aim the attacks
    """
    name: str
    cases: Callable[[], list]
    check: Callable[[object], list]
    inject: Callable[[object, float], object]
    values: Callable[[object], list[float]]


# ── The attacks ───────────────────────────────────────────────────────────────

def near_miss(rng, real):
    """A real value nudged well past display rounding — wrong digit, right shape."""
    v = rng.choice(real)
    delta = max(abs(v) * rng.uniform(0.06, 0.30), 0.2)
    return round(v + delta * rng.choice([1, -1]), 1)


def in_range(rng, real):
    """A number this document could plausibly have said, but didn't."""
    lo, hi = min(real), max(real)
    if lo == hi:
        lo, hi = lo * 0.5, hi * 1.5
    return round(rng.uniform(lo, hi), 1)


ATTACKS = {"near-miss": near_miss, "in-range": in_range}


def measure(target, n=INJECTIONS, seed=SEED):
    cases = target.cases()
    if not cases:
        return None

    # False rejections first: a gate that blocks the truth is worse than a loose one,
    # because it gets turned off. Measured on the untouched artifacts.
    false_rejections = sum(1 for c in cases if target.check(c))

    results = {}
    for attack_name, attack in ATTACKS.items():
        rng = random.Random(seed)
        caught = attempted = 0
        for i in range(n):
            case = cases[i % len(cases)]
            real = [v for v in target.values(case) if abs(v) > 0.5]
            if not real:
                continue
            value = attack(rng, real)
            if any(abs(value - v) < 0.05 for v in real):
                continue                      # accidentally landed on a true value
            attempted += 1
            caught += bool(target.check(target.inject(copy.deepcopy(case), value)))
        results[attack_name] = (caught, attempted)

    return {"cases": len(cases), "false_rejections": false_rejections,
            "attacks": results}


# ── Gate: the newsletter (validate_newsletter.check_doc) ──────────────────────

def _newsletter_target():
    import newsletter_sources as ns
    from validate_newsletter import check_doc
    import generate_release_read as release
    import generate_deep_read as deep
    from core.traceability import SIBC, extract_numbers

    def cases():
        out = []
        for pipeline in ("sibc", "atm_pos"):
            period = ns.latest_period(pipeline)
            if period:
                doc, declared = release.build_doc(pipeline, period)
                out.append({"doc": doc, "declared": declared,
                            "label": f"release_read {pipeline}"})
        doc, _, declared = deep.build_doc()
        out.append({"doc": doc, "declared": declared, "label": "deep_read"})
        return out

    def check(case):
        return check_doc(case["doc"], case["declared"], label=case["label"])

    def inject(case, value):
        # Into the template's own prose — the place a fabricated number would live.
        for block in case["doc"]:
            if block.get("type") == "p":
                block["text"] += f" The figure stood at {value}% this month."
                break
        return case

    def values(case):
        nums = []
        for block in case["doc"]:
            if block.get("type") == "statgrid":
                for item in block.get("items", []):
                    nums += extract_numbers(item.get("value", ""), SIBC)
            elif block.get("type") in ("p", "li", "stat"):
                nums += extract_numbers(block.get("text", ""), SIBC)
        return nums

    return Target("newsletter", cases, check, inject, values)


# ── Gate: the distribution slots (validate_distribution.check_slate) ──────────

def _distribution_target():
    from distribution import generate_slot as gen
    from distribution.validate_distribution import check_slate
    from core.traceability import DISTRIBUTION, extract_numbers

    def cases():
        out = []
        for slot, cats in (("1st", ["C1", "C5"]), ("7th", ["C2", "C3"]),
                           ("14th", ["C6", "C7"]), ("28th", ["C8"])):
            slate = gen.build_slate(slot, "2026-08-01", cats, False)
            if slate and any(not c.get("verbatim") for c in slate["claims"]):
                out.append(slate)
        return out

    def inject(slate, value):
        for claim in slate["claims"]:
            if not claim.get("verbatim"):       # verbatim claims are checked differently
                claim["body"] += f" The gap stood at {value} pp this month."
                break
        return slate

    def values(slate):
        nums = []
        for claim in slate["claims"]:
            nums += extract_numbers(f"{claim['title']} {claim['body']}", DISTRIBUTION)
        return nums

    return Target("distribution", cases, check_slate, inject, values)


GATES = {"newsletter": _newsletter_target, "distribution": _distribution_target}


def main():
    ap = argparse.ArgumentParser(description="Measure traceability gates by injection")
    ap.add_argument("--gate", choices=list(GATES), action="append")
    ap.add_argument("--n", type=int, default=INJECTIONS)
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()

    print(f"{'gate':<14} {'cases':>5} {'false rej':>10}  "
          + "  ".join(f"{a:>12}" for a in ATTACKS))
    print("-" * 62)
    for name in (args.gate or list(GATES)):
        result = measure(GATES[name](), args.n, args.seed)
        if not result:
            print(f"{name:<14} no cases")
            continue
        rates = []
        for attack in ATTACKS:
            caught, attempted = result["attacks"][attack]
            rates.append(f"{100.0 * caught / attempted:>11.1f}%" if attempted else "        n/a")
        print(f"{name:<14} {result['cases']:>5} "
              f"{result['false_rejections']:>4}/{result['cases']:<5}  " + "  ".join(rates))
    print(f"\nn={args.n} injections per attack per gate, seed={args.seed}. "
          "Catch rate = share rejected.\nFalse rejections = untouched, true artifacts "
          "the gate rejected. Both matter.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
