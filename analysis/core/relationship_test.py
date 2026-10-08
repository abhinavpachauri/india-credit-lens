#!/usr/bin/env python3
"""
relationship_test.py — does one line really push another, beyond the tide they share?
───────────────────────────────────────────────────────────────────────────────────────
SYSTEM_MODEL_SPEC §16 Step 6b (v3.1). A relationship between two parts of a pipeline enters the
model only after it is PROPOSED with a reason and a predicted sign, and then PASSES this test.
The data cannot find relationships on its own: over ~15 monthly changes, more than half of the
strongly co-moving SIBC pairs appear in a shuffled control too (measured 2026-10-08: 86 pairs at
|r| > 0.6, 48 in the control). So the reason comes first and the data can only refute.

The protocol, fixed before any result is seen:

  measure   the monthly change in each line's gap to its own group: the quantity the coverage
            count (Step 6a) uses when a relationship explains a move
  tide      both changes are regressed on the pipeline root's monthly growth change first.
            Two lines that both follow total bank credit co-move without touching each other:
            the first candidate tested (HFC lending vs direct housing) showed r = +0.46,
            p = 0.03 raw, and r = +0.17, p = 0.43 once the tide was removed
  control   10,000 shuffles of one side; p = share with |r| at least the observed
  verdict   `supported` when the predicted sign holds and p < ALPHA / family at the declared
            lag; `opposite` when the sign is reversed at that bar; otherwise `not_supported`.
            Other lags are reported, never used to rescue a verdict. `family` is how many
            relationships were declared together (Bonferroni): four tested at once each need
            p < 0.0125, or one of them passes by luck one time in five.

Results, nulls included, are recorded in analysis/{pipeline}/relationship_tests.json: a
rejection is evidence about the world and is kept (the same rule as S4's attempts[]).
Deterministic (seeded). No LLM.
"""
from __future__ import annotations

import json
import random
import sys
from datetime import date
from pathlib import Path
from statistics import correlation, linear_regression

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core import coverage as cv  # noqa: E402
from core import force_check as fc  # noqa: E402
from core import generate_skeleton as gs  # noqa: E402

ALPHA = 0.05
SHUFFLES = 10_000
SEED = 20261008
MIN_PAIRS = 10


def gap_changes(nid: str, model: dict, series: dict, periods: list[str], data_month) -> dict[int, float]:
    """month index -> change in the line's gap to its own group, one data month apart."""
    by_id = {n["id"]: n for n in model["nodes"] if n.get("tier") == "entity"}
    parent_of = {e["from"]: e["to"] for e in model["edges"]
                 if e["type"] == "composes_into" and e["from"] in by_id and e["to"] in by_id}
    kind, _, base = cv.baseline_for(nid, parent_of, by_id, series, periods[-1])
    gaps = [(p, series[nid][p] - (0.0 if kind == "none" else base[p]))
            for p in periods if p in series.get(nid, {}) and (kind == "none" or p in base)]
    return {fc._months(data_month(p)): d for p, d in fc.monthly_changes(gaps, data_month)}


def tide(model: dict, series: dict, data_month) -> dict[int, float]:
    """month index -> the root's monthly growth change (the first primary root with a series)."""
    roots = [n for n in model["nodes"] if n.get("tier") == "entity"
             and n.get("structural_role") == "root" and n["id"] in series]
    if not roots:
        return {}
    s = series[roots[0]["id"]]
    return {fc._months(data_month(p)): d
            for p, d in fc.monthly_changes(sorted(s.items()), data_month)}


def residual(a: list[float], t: list[float]) -> list[float]:
    slope, icept = linear_regression(t, a)
    return [u - (slope * v + icept) for u, v in zip(a, t)]


def shuffle_p(x: list[float], y: list[float], seed: int = SEED) -> tuple[float, float]:
    r = correlation(x, y)
    rng, y2, hits = random.Random(seed), list(y), 0
    for _ in range(SHUFFLES):
        rng.shuffle(y2)
        hits += abs(correlation(x, y2)) >= abs(r)
    return r, hits / SHUFFLES


def test(a: dict[int, float], b: dict[int, float], t: dict[int, float], sign: int, lag: int,
         family: int = 1) -> dict:
    """`a` pushes `b` with `sign` after `lag` months. Pure given its inputs."""
    alpha = ALPHA / family
    rows = {}
    for L in sorted({0, 1, 2, 3, lag}):
        months = sorted(k for k in a if k + L in b and k + L in t and k in t)
        if len(months) < MIN_PAIRS:
            rows[L] = {"n": len(months), "verdict": "too_few"}
            continue
        x = residual([a[k] for k in months], [t[k] for k in months])
        y = residual([b[k + L] for k in months], [t[k + L] for k in months])
        r, p = shuffle_p(x, y)
        rows[L] = {"n": len(months), "r": round(r, 3), "p": round(p, 3)}
    main = rows[lag]
    if "r" not in main:
        verdict = "too_few"
    elif main["p"] < alpha and (main["r"] > 0) == (sign > 0):
        verdict = "supported"
    elif main["p"] < alpha:
        verdict = "opposite"
    else:
        verdict = "not_supported"
    return {"verdict": verdict, "at_lag": lag, "family": family, "alpha": round(alpha, 4), "lags": rows}


def run(pipeline: str, source: str, target: str, sign: int, lag: int, reason: str,
        family: int = 1) -> dict:
    model = gs.load_json(gs.pipeline_cfg(pipeline)["model"])
    series, periods = fc.growth_series(pipeline, model), fc.periods_of(pipeline)
    dm = lambda p: fc.resolve_csv_date(pipeline, p)  # noqa: E731
    by_id = {n["id"]: n for n in model["nodes"]}
    res = test(gap_changes(source, model, series, periods, dm),
               gap_changes(target, model, series, periods, dm),
               tide(model, series, dm), sign, lag, family)
    return {"source": source, "source_label": by_id[source]["label"],
            "target": target, "target_label": by_id[target]["label"],
            "predicted_sign": sign, "reason": reason, "tested": date.today().isoformat(),
            "through_period": periods[-1], "protocol": "SYSTEM_MODEL_SPEC §16 Step 6b", **res}


def record(pipeline: str, result: dict, note: str | None = None) -> Path:
    path = gs.pipeline_cfg(pipeline)["model"].parent.parent / "relationship_tests.json"
    doc = json.loads(path.read_text()) if path.exists() else {
        "_meta": {"spec_ref": "analysis/SYSTEM_MODEL_SPEC.md §16 Step 6b",
                  "description": "Every relationship tested, nulls included. Only `supported` may "
                                 "become an entity→entity edge, and only with the editor's yes."},
        "tests": []}
    doc["tests"].append({**result, **({"note": note} if note else {})})
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False))
    return path


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Test a proposed relationship (SYSTEM_MODEL_SPEC §16 Step 6b)")
    ap.add_argument("--pipeline", required=True)
    ap.add_argument("--source", required=True, help="entity id that pushes")
    ap.add_argument("--target", required=True, help="entity id that is pushed")
    ap.add_argument("--sign", type=int, choices=(1, -1), required=True,
                    help="+1 complement (move together), -1 substitute (move apart)")
    ap.add_argument("--lag", type=int, default=0, help="months the push takes, declared up front")
    ap.add_argument("--reason", required=True, help="the real-world reason, one sentence")
    ap.add_argument("--family", type=int, default=1,
                    help="how many relationships were declared together (Bonferroni)")
    ap.add_argument("--note")
    ap.add_argument("--record", action="store_true", help="append the result to relationship_tests.json")
    a = ap.parse_args()
    r = run(a.pipeline, a.source, a.target, a.sign, a.lag, a.reason, a.family)
    print(f"{r['source_label']} → {r['target_label']} (predicted {'+' if a.sign > 0 else '−'}, "
          f"lag {a.lag}m, bar p < {r['alpha']:g})")
    for L, row in r["lags"].items():
        mark = " ← declared" if L == a.lag else ""
        print(f"  lag {L}m: " + (f"n={row['n']} r={row['r']:+.2f} p={row['p']:.3f}" if "r" in row
                                 else f"n={row['n']} too few") + mark)
    print(f"  verdict: {r['verdict']}")
    if a.record:
        print(f"  → recorded in {record(a.pipeline, r, a.note).relative_to(gs.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
