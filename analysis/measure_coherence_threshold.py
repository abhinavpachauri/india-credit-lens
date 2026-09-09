#!/usr/bin/env python3
"""
measure_coherence_threshold.py — what `coherence_min` actually buys, measured
────────────────────────────────────────────────────────────────────────────
`coherence_min = 0.90` has decided, on every dashboard card in the movement
family since 2026-08-19, whether an `alloc` figure is published. It shipped
with a *proof* (the bound `max|share of net| <= 1/coherence`) and no
*measurement*, which the standing AI PM rule forbids. This closes that.

What the threshold is for
─────────────────────────
`alloc` = `100 * delta_i / net` answers "of the net new units, how many went
here". When entities move against each other the net shrinks toward zero while
the numerators do not, so a single entity's share of the net can exceed the
whole net. "Of every Rs 100 of new credit, telecoms took Rs 137" is
arithmetically true and reads as impossible.

So the threshold's job is precisely: **withhold `alloc` when it would read as
impossible.** That is a testable claim, and this measures it.

Note what a miss costs here, because it is NOT a gate (decision: coherence
ROUTES, never gates). A withheld window is not silence — `contribution` rows
still publish and the card switches to the contested/handover sentence. So a
false rejection costs a *less direct sentence*, not a lost story. A miss, by
contrast, puts an impossible-looking number on the dashboard.

Method — enumerate, do not sample
─────────────────────────────────
Every momentum window in signals.db, both pipelines, every period. The
counterfactual `alloc` is reconstructed from the stored per-entity deltas and
the `total` aggregate, so windows the threshold *withheld* can still be scored
— which is the only way to compute a false-rejection rate at all.

The threshold is read from the registry's own `compute.coherence_min`, never
hardcoded here, so this measures what actually ships.

Usage:  python3 analysis/measure_coherence_threshold.py [--unsafe-at 100]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / "signals" / "signals.db"
REGISTRY = ROOT / "signals" / "registry.json"


def momentum_signals() -> list[dict]:
    """Every registered signal computing the momentum method, either pipeline."""
    reg = json.loads(REGISTRY.read_text())["signals"]
    return [
        s for s in reg.values()
        if "momentum" in ((s.get("compute") or {}).get("method", ""))
    ]


def declared_threshold() -> float:
    """The shipping value, read off the allocation signals rather than assumed.

    If the registry ever disagrees with itself we would rather fail loudly than
    measure a threshold nothing uses.
    """
    reg = json.loads(REGISTRY.read_text())["signals"]
    mins = {
        (s.get("compute") or {}).get("coherence_min")
        for s in reg.values()
        if "allocation" in ((s.get("compute") or {}).get("method", ""))
    }
    mins.discard(None)
    if len(mins) != 1:
        raise SystemExit(f"allocation signals declare {len(mins)} thresholds: {mins}")
    return float(mins.pop())


def windows() -> list[dict]:
    """One record per (pipeline, cut, period), with the alloc that WOULD publish."""
    ids = [s["id"] for s in momentum_signals()]
    if not ids:
        raise SystemExit("no momentum signals in the registry")

    con = sqlite3.connect(DB)
    q = ",".join("?" * len(ids))
    rows = con.execute(
        f"SELECT pipeline, metric_id, period, entity_type, entity_id, value "
        f"FROM signals WHERE metric_id IN ({q})",
        ids,
    ).fetchall()
    con.close()

    agg: dict[tuple, dict] = defaultdict(dict)
    ents: dict[tuple, list] = defaultdict(list)
    for pipeline, mid, period, etype, eid, value in rows:
        key = (pipeline, mid, period)
        if etype == "aggregate":
            agg[key][eid] = value
        else:
            ents[key].append((eid, value))

    out = []
    for key, a in agg.items():
        net, coherence = a.get("total"), a.get("coherence")
        if net is None or coherence is None or not ents[key]:
            continue
        if abs(net) < 1e-9:
            # A net of exactly zero is pure churn; alloc is undefined, not large.
            # It cannot be scored either way, so it is reported, never counted.
            out.append(dict(zip(("pipeline", "cut", "period"), key),
                            coherence=coherence, worst=None, net=net))
            continue
        worst_eid, worst = max(
            ((eid, abs(100.0 * d / net)) for eid, d in ents[key]),
            key=lambda t: t[1],
        )
        out.append(dict(zip(("pipeline", "cut", "period"), key),
                        coherence=coherence, worst=worst, net=net,
                        worst_entity=worst_eid))
    return sorted(out, key=lambda w: w["coherence"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--unsafe-at", type=float, default=100.0,
        help="a window is UNSAFE when some |alloc| exceeds this percent of net "
             "(default 100 — a share larger than the whole it is a share of)",
    )
    args = ap.parse_args()

    cmin = declared_threshold()
    all_w = windows()
    scored = [w for w in all_w if w["worst"] is not None]
    undefined = len(all_w) - len(scored)

    unsafe = [w for w in scored if w["worst"] > args.unsafe_at]
    safe = [w for w in scored if w["worst"] <= args.unsafe_at]
    withheld = [w for w in scored if w["coherence"] < cmin]
    published = [w for w in scored if w["coherence"] >= cmin]

    caught = [w for w in unsafe if w["coherence"] < cmin]
    missed = [w for w in unsafe if w["coherence"] >= cmin]
    false_rej = [w for w in safe if w["coherence"] < cmin]

    print(f"coherence_min = {cmin}   (read from the registry)")
    print(f"unsafe when some |alloc| > {args.unsafe_at:.0f}% of net\n")
    print(f"windows enumerated        {len(all_w)}"
          f"   ({len(scored)} scorable, {undefined} zero-net/undefined)")
    print(f"  would publish alloc     {len(published)}")
    print(f"  withheld by threshold   {len(withheld)}")
    print(f"  genuinely unsafe        {len(unsafe)}\n")

    catch = 100.0 * len(caught) / len(unsafe) if unsafe else float("nan")
    frr = 100.0 * len(false_rej) / len(safe) if safe else float("nan")
    print(f"CATCH RATE            {catch:6.1f}%   ({len(caught)}/{len(unsafe)} unsafe windows withheld)")
    print(f"FALSE-REJECTION RATE  {frr:6.1f}%   ({len(false_rej)}/{len(safe)} safe windows withheld)")

    if published:
        worst_published = max(published, key=lambda w: w["worst"])
        print(f"\nworst |alloc| that actually publishes: {worst_published['worst']:.1f}% "
              f"({worst_published['cut']} {worst_published['period']})")
        print(f"  bound at coherence {cmin} predicts <= {100.0 / cmin:.1f}%")

    if missed:
        print(f"\nMISSES — unsafe but published:")
        for w in missed:
            print(f"  {w['cut']:<24} {w['period']}  coh={w['coherence']:.3f}  "
                  f"|alloc|={w['worst']:.1f}%  ({w['worst_entity']})")

    # The empirical floor: the highest coherence at which an unsafe window exists.
    # Any threshold at or below it would start publishing impossible shares.
    if unsafe:
        floor = max(w["coherence"] for w in unsafe)
        print(f"\nempirical floor: highest coherence carrying an unsafe window = {floor:.3f}")
        print(f"  so any threshold <= {floor:.3f} would publish one; "
              f"{cmin} clears it by {cmin - floor:.3f}")

    print("\nthreshold sweep (catch / false-rejection):")
    for t in (0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95):
        c = sum(1 for w in unsafe if w["coherence"] < t)
        f = sum(1 for w in safe if w["coherence"] < t)
        mark = "  <- shipping" if abs(t - cmin) < 1e-9 else ""
        print(f"  {t:.2f}   catch {100.0*c/len(unsafe):5.1f}%   "
              f"false-rej {100.0*f/len(safe):5.1f}%{mark}")

    print("\nwindows the threshold withheld that were in fact safe:")
    for w in sorted(false_rej, key=lambda w: -w["coherence"]):
        print(f"  {w['pipeline']:<8} {w['cut']:<24} {w['period']}  "
              f"coh={w['coherence']:.3f}  worst|alloc|={w['worst']:5.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
