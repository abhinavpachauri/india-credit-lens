#!/usr/bin/env python3
"""
coverage.py — how much of this period's movement does the model account for?
─────────────────────────────────────────────────────────────────────────────
SYSTEM_MODEL_SPEC §16 Step 6a (v3.1). The only earlier measure of "unexplained" was S4's
`detect_unexplained`, and it counted a line that was merely growing (Housing, at its usual pace),
called a line explained when any arrow touched it, and stopped at 15. This counts properly, once,
in S3, and S4 reads the result.

    a MOVE      a line (any entity but a root) whose gap to its group changed since the
                previous reading by more than MOVE_FACTOR × its typical change
    EXPLAINED   the first of these that holds, in order:
                  artifact         one bank is most of the move (signals/dominance.py)
                  structural       not a separate event: an ECHO (the group moved the other way),
                                   a TWIN (the same borrowers moved in a linked table), or
                                   CARRIED by one member (the group moved because it did)
                  prices_activity  the line's 1f price index or output moved the same way and
                                   covers at least half the change in its nominal growth
                  cause            a DATED force whose edge to the line is working, sign matching
                  relationship     an entity→entity driver edge whose source moved the way
                                   that pushes this line in the direction it moved
                and otherwise      unexplained → S4

The order matters only for `filed_under`; every explanation that holds is listed in
`also_holds`, so an artifact that also matches a force is visible as both.

Mix state ("money steered toward Services") is never an explanation: it restates the move.
Deterministic. No LLM. Nothing here writes; generate_system_state emits the result.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from statistics import median

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core import force_check as fc  # noqa: E402
from core import generate_skeleton as gs  # noqa: E402

DB = fc.DB
# A price or output change explains a move when it covers at least this share of the change in
# the line's own nominal growth. A starting value (spec §16 Step 6a), confirmed by measurement.
PRICE_SHARE = 0.5
# A move is a change bigger than this many times the line's typical (median) change. At 1×, half
# of any line's readings beat its own median by construction: measured 2026-10-08 over every
# reading, 1× flags 47% of SIBC line-readings, 2× 20%, 3× 11% (payments 43/18/10%). 3× makes a
# move roughly a one-in-ten event per line, close to the usual ~2σ bar for "unusual".
MOVE_FACTOR = 3.0
POLARITY = {"+": 1, "-": -1}
ORDER = ("artifact", "structural", "prices_activity", "cause", "relationship")
# An echo / carried-by-member holds when the other line covers at least this share of the move.
STRUCTURAL_SHARE = 0.5


def sign(x: float) -> int:
    return 1 if x > 0 else -1 if x < 0 else 0


# ── 1. The move ──────────────────────────────────────────────────────────────────────────

def baseline_for(node_id: str, parent_of: dict, by_id: dict, series: dict, period: str):
    """(kind, series) the line is measured against: its parent when it is an additive child,
    else the root of its own tree, else nothing — in which case the move is the line's own
    change in growth. The first one with a reading at `period` wins, so a parent total with no
    YoY signal (payments, today) degrades visibly instead of silently comparing with zero."""
    node = by_id[node_id]
    parent = by_id.get(parent_of.get(node_id))
    if parent is not None and parent.get("additive", True) and node.get("additive", True):
        if period in series.get(parent["id"], {}):
            return "parent", parent["label"], series[parent["id"]]
    top = node_id
    while parent_of.get(top) in by_id:
        top = parent_of[top]
    if top != node_id and period in series.get(top, {}):
        return "root", by_id[top]["label"], series[top]
    return "none", None, {}


def move_of(growth: dict, base: dict, kind: str, periods: list[str], period: str,
            data_month=lambda p: p) -> dict:
    """The line's change against its baseline at `period`, judged against its own wobble."""
    gaps = [(p, growth[p] - (0.0 if kind == "none" else base[p]))
            for p in periods if p <= period and p in growth and (kind == "none" or p in base)]
    if not gaps or gaps[-1][0] != period:
        return {"status": "no_reading", "reason": "no reading this period"}
    changes = fc.monthly_changes(gaps, data_month)
    if not changes or changes[-1][0] != period:
        # The previous reading is not last month (a hole in the history): a change across it
        # spans several months and cannot be judged against a month-to-month wobble.
        return {"status": "no_reading", "reason": "no reading for the month before"}
    if len(changes) < fc.MIN_HISTORY:
        return {"status": "no_reading",
                "reason": f"{len(changes)} month-to-month changes; the wobble needs {fc.MIN_HISTORY}"}
    noise = median(abs(d) for _, d in changes)
    change = changes[-1][1]
    out = {"previous": gaps[-2][0], "gap_change_pp": round(change, 2), "noise_pp": round(noise, 2),
           "threshold_pp": round(MOVE_FACTOR * noise, 2)}
    if abs(change) <= MOVE_FACTOR * noise:
        return {**out, "status": "steady"}
    return {**out, "status": "moved", "direction": sign(change)}


# ── 2. The explanations ──────────────────────────────────────────────────────────────────

def prices_activity(real: dict | None, output: dict | None, growth: dict, period: str,
                    previous: str, direction: int) -> tuple[str, dict]:
    """('holds' | 'does_not_hold' | 'not_decomposable', detail) for one move.

    `real` is {period: operands} from the 1f real-growth row (carries `deflator_yoy`);
    `output` is {period: output growth %}. A line no reference series is matched to cannot be
    tested, and says so: "no price effect" and "price effect not measurable" must not read alike.
    """
    if not real and not output:
        return "not_decomposable", {"reason": "no 1f match for this line"}
    if period not in growth or previous not in growth:
        return "not_decomposable", {"reason": "no nominal growth at both readings"}
    d_nominal = growth[period] - growth[previous]
    if sign(d_nominal) != direction:
        # The line moved against its group because the GROUP moved; its own price cannot be why.
        return "does_not_hold", {"nominal_change_pp": round(d_nominal, 2)}
    tested, detail = False, {"nominal_change_pp": round(d_nominal, 2)}
    for name, now, then in (
            ("deflator", (real or {}).get(period, {}).get("deflator_yoy"),
             (real or {}).get(previous, {}).get("deflator_yoy")),
            ("output", (output or {}).get(period), (output or {}).get(previous))):
        if now is None or then is None:
            continue
        tested = True
        d = now - then
        detail[f"{name}_change_pp"] = round(d, 2)
        if sign(d) == direction and abs(d) >= PRICE_SHARE * abs(d_nominal):
            return "holds", {**detail, "by": name}
    if not tested:
        return "not_decomposable", {**detail, "reason": "1f reading missing at one of the two readings"}
    return "does_not_hold", detail


def causes(node_id: str, direction: int, checked: dict, model: dict) -> list[str]:
    """Dated forces whose edge to this line is working, pushing the way it moved. A standing
    force explains a steady gap, never a change (§10.1), so it never files a move."""
    by_force = {f["id"]: f for f in model.get("force_instances", [])}
    out = []
    for e in model["edges"]:
        if e["to"] != node_id or e["type"] not in fc.DRIVER_SIGN or e["from"] not in by_force:
            continue
        if by_force[e["from"]].get("standing"):
            continue
        res = checked.get(e["from"], {}).get("edges", {}).get(e.get("id", f"{e['from']}->{e['to']}"), {})
        if res.get("verdict") == "working" and fc.DRIVER_SIGN[e["type"]] == direction:
            out.append(e["from"])
    return out


def relationships(node_id: str, direction: int, moves: dict, model: dict,
                  verdicts: dict | None = None, lagged_move=None) -> list[str]:
    """Entity→entity arrows into this line that explain its move: the arrow's relationship test
    (Step 6b) is `supported`, and its source moved, `lag` months earlier, the way that pushes
    this line in the direction it moved. An untested or unsupported arrow explains nothing:
    an authored arrow is a hypothesis until the data admits it (all 12 tested 2026-10-10 were
    not supported)."""
    out = []
    for e in model["edges"]:
        if e["to"] != node_id or e["from"] not in moves:
            continue
        t = (verdicts or {}).get((e["from"], e["to"]))
        if not t or t["verdict"] != "supported":
            continue
        src = moves[e["from"]] if not t["lag"] else (lagged_move(e["from"], t["lag"]) if lagged_move else {})
        if src.get("status") == "moved" and src["direction"] * t["sign"] == direction:
            out.append(e["from"])
    return out


def structural(nid: str, m: dict, moves: dict, model: dict, by_id: dict, parent_of: dict,
               series: dict, period: str, weights: dict) -> list[str]:
    """Why this move is not a separate event, from the skeleton alone. SYSTEM_MODEL_SPEC §16
    Step 6a. Each points at the line that holds the event, which keeps its own filing, so an
    event is counted once:

      echo     the line moved against its group because the GROUP moved the other way, by at
               least half the line's change (non-food credit "falls" when food credit jumps)
      twin     a lens member (PSL) whose linked main-table line moved the same way this month:
               the same borrowers in a second table. The main-table line keeps the event
      carried  a group whose move one member carries: that member moved the same way and its
               weighted change is at least half the group's own change. The member keeps it
    """
    d, prev, out = m["direction"], m["previous"], []
    node = by_id[nid]
    base = m.get("base_change")
    if base is not None and -d * base > 0 and abs(base) >= STRUCTURAL_SHARE * abs(m["gap_change_pp"]):
        out.append(f"echo of {m['baseline_of']}")
    if not node.get("additive", True):
        for e in model["edges"]:
            if e["type"] != "reclassifies" or nid not in (e["from"], e["to"]):
                continue
            other = e["to"] if e["from"] == nid else e["from"]
            if other in by_id and by_id[other].get("additive", True) \
                    and moves.get(other, {}).get("direction") == d:
                out.append(f"twin of {by_id[other]['label']}")
    own = series.get(nid, {})
    if prev in own and period in own and weights.get(nid):
        d_group = own[period] - own[prev]
        for k, parent in parent_of.items():
            km = moves.get(k, {})
            if parent != nid or km.get("direction") != d or not weights.get(k):
                continue
            kser = series.get(k, {})
            if prev not in kser or period not in kser:
                continue
            carried = weights[k] / weights[nid] * (kser[period] - kser[prev])
            if sign(carried) == sign(d_group) != 0 and abs(carried) >= STRUCTURAL_SHARE * abs(d_group):
                out.append(f"carried by {by_id[k]['label']}")
    return out


# ── 3. The count ─────────────────────────────────────────────────────────────────────────

def compute(model: dict, period: str, series: dict, periods: list[str], checked: dict,
            real: dict | None = None, output: dict | None = None, artifact=None,
            data_month=lambda p: p, weights: dict | None = None,
            verdicts: dict | None = None) -> dict:
    """Pure given its inputs. `artifact(node) -> True | False | None` (None = not testable);
    `data_month(period)` is the month a period key's data describes (SIBC keys run a month ahead);
    `weights` is entity_id -> size (latest CSV value), for `carried`."""
    weights = weights or {}
    real, output = real or {}, output or {}
    artifact = artifact or (lambda node: None)
    by_id = {n["id"]: n for n in model["nodes"] if n.get("tier") == "entity"}
    parent_of = {e["from"]: e["to"] for e in model["edges"]
                 if e["type"] == "composes_into" and e["from"] in by_id and e["to"] in by_id}

    # Every entity's move, so a relationship can read its source's move even when the source is
    # an aggregate outside the counted population.
    moves = {}
    for nid in by_id:
        if nid not in series:
            moves[nid] = {"status": "no_reading", "reason": "no YoY signal for this line in signals.db"}
            continue
        kind, of, base = baseline_for(nid, parent_of, by_id, series, period)
        mv = move_of(series[nid], base, kind, periods, period, data_month)
        if mv.get("previous") in base and period in base:
            mv["base_change"] = base[period] - base[mv["previous"]]
        moves[nid] = {**mv, "baseline_kind": kind, "baseline_of": of}

    def lagged_move(nid: str, lag: int) -> dict:
        """The source's move `lag` data months before this period (for a delayed arrow)."""
        target = fc._months(data_month(period)) - lag
        at = next((q for q in periods if fc._months(data_month(q)) == target), None)
        if at is None or nid not in series:
            return {}
        kind, _, base = baseline_for(nid, parent_of, by_id, series, at)
        return move_of(series[nid], base, kind, periods, at, data_month)

    # Every line but a root. Moves are measured against the line's group, so a force acting on a
    # group (Services, All Engineering) cancels out of its members' moves and can only explain
    # the GROUP beating its own parent: groups are counted for that reason.
    lines = [n for n in by_id.values() if n.get("structural_role") != "root"]
    records, no_reading, steady = [], [], 0
    for n in lines:
        m = moves[n["id"]]
        if m["status"] == "no_reading":
            no_reading.append({"entity": n["label"], "urn": n.get("urn"), "reason": m["reason"]})
            continue
        if m["status"] == "steady":
            steady += 1
            continue
        d = m["direction"]
        held = {}
        if artifact(n):
            held["artifact"] = ["one bank is most of the move"]
        st = structural(n["id"], m, moves, model, by_id, parent_of, series, period, weights)
        if st:
            held["structural"] = st
        pa, pa_detail = prices_activity(real.get(n["id"]), output.get(n["id"]), series[n["id"]],
                                        period, m["previous"], d)
        if pa == "holds":
            held["prices_activity"] = [pa_detail["by"]]
        c = causes(n["id"], d, checked, model)
        if c:
            held["cause"] = c
        r = relationships(n["id"], d, moves, model, verdicts, lagged_move)
        if r:
            held["relationship"] = [by_id[x]["label"] for x in r]
        filed = next((k for k in ORDER if k in held), "unexplained")
        records.append({
            "entity": n["label"], "urn": n.get("urn"),
            "product": (n.get("concept_tags") or {}).get("product"),
            "direction": "up" if d > 0 else "down",
            "level": n.get("structural_role"),
            "gap_change_pp": m["gap_change_pp"], "noise_pp": m["noise_pp"],
            "threshold_pp": m["threshold_pp"],
            "baseline_kind": m["baseline_kind"], "baseline_of": m["baseline_of"],
            "filed_under": filed, "also_holds": held,
            "prices_activity": pa, **({"prices_detail": pa_detail} if pa_detail else {}),
        })

    count = {k: sum(1 for r in records if r["filed_under"] == k) for k in (*ORDER, "unexplained")}
    return {
        "summary": {"lines": len(lines), "moves": len(records), "steady": steady, **count,
                    "no_reading": len(no_reading)},
        "moves": records,
        "no_reading": no_reading,
    }


# ── Inputs from signals.db, all joined through the registry ──────────────────────────────

def reference_rows(pipeline: str, model: dict, con=None) -> tuple[dict, dict]:
    """(real, output): node_id -> {period: operands} and node_id -> {period: output %}, from
    the 1f signals. Each names its cut; the cut's `-yoy-scan` names the parent whose children
    the rows are keyed by label — the same join growth_series uses."""
    registry = gs.load_json(gs.ANALYSIS / "signals" / "registry.json")["signals"]
    by_id = {n["id"]: n for n in model["nodes"] if n.get("tier") == "entity"}
    by_code = {}
    for n in by_id.values():
        by_code[(n.get("statement"), str(n.get("code")))] = n
        by_code.setdefault((None, str(n.get("code"))), n)
    kids = fc._children(model)
    own = con is None
    con = con or sqlite3.connect(DB)
    real, output = {}, {}
    try:
        for sid, sig in registry.items():
            comp = sig.get("compute", {})
            method = comp.get("method")
            if sig.get("pipeline") != pipeline or method not in ("csv_sector_real_growth",
                                                                 "csv_sector_output_growth"):
                continue
            scan = registry.get(f"{comp.get('cut')}-yoy-scan", {}).get("compute", {})
            code = str(scan.get("parent_code"))
            parent = by_code.get((scan.get("statement"), code)) or by_code.get((None, code))
            if not parent:
                continue
            label = {c["label"]: c["id"] for c in kids.get(parent["id"], [])}
            for p, e, v, ops in con.execute(
                    "SELECT period, entity_id, value, operands FROM signals WHERE pipeline=? "
                    "AND metric_id=? AND entity_type=?", (pipeline, sid, comp.get("entity_type"))):
                if e not in label:
                    continue
                if method == "csv_sector_real_growth" and ops:
                    real.setdefault(label[e], {})[p] = json.loads(ops)
                elif method == "csv_sector_output_growth" and v is not None:
                    output.setdefault(label[e], {})[p] = v
    finally:
        if own:
            con.close()
    return real, output


def artifact_test(pipeline: str, model: dict, period: str):
    """node -> True/False/None: does one bank dominate this line's move? Only lines with a
    per-bank scan can be tested (payments); everything else answers None, not False."""
    from signals import dominance
    registry = gs.load_json(gs.ANALYSIS / "signals" / "registry.json")["signals"]
    yoy_of = {sig["compute"].get("metric"): sid for sid, sig in registry.items()
              if sig.get("pipeline") == pipeline and sig.get("compute", {}).get("method") == "csv_total_yoy"}
    con = sqlite3.connect(DB)

    def test(node):
        sid = yoy_of.get(node.get("code"))
        if not sid:
            return None
        d = dominance.move_dominance(pipeline, sid, period, conn=con)
        return None if d is None else d.dominant
    return test


def for_period(pipeline: str, model: dict, period: str, series=None, periods=None,
               checked=None) -> dict:
    series = series if series is not None else fc.growth_series(pipeline, model)
    periods = periods if periods is not None else fc.periods_of(pipeline)
    checked = checked if checked is not None else fc.check(pipeline, model, period, series, periods)
    from core.generate_system_state import load_entity_weights
    from core.relationship_test import latest_verdicts
    real, output = reference_rows(pipeline, model)
    return compute(model, period, series, periods, checked, real, output,
                   artifact_test(pipeline, model, period),
                   lambda p: fc.resolve_csv_date(pipeline, p),
                   load_entity_weights(gs.pipeline_cfg(pipeline)),
                   latest_verdicts(pipeline))


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Explanation coverage (SYSTEM_MODEL_SPEC §16 Step 6a)")
    ap.add_argument("--pipeline", required=True)
    ap.add_argument("--period")
    ap.add_argument("--history", action="store_true", help="the summary for every period")
    args = ap.parse_args()
    model = gs.load_json(gs.pipeline_cfg(args.pipeline)["model"])
    series, periods = fc.growth_series(args.pipeline, model), fc.periods_of(args.pipeline)
    cols = ("moves", "steady", *ORDER, "unexplained", "no_reading")
    if args.history:
        print(f"{args.pipeline}: explanation coverage over every reading "
              f"(a move = a change > {MOVE_FACTOR:g}× the line's typical change)")
        print("  " + "period".ljust(12) + "".join(c[:12].rjust(13) for c in cols))
        for p in periods:
            s = for_period(args.pipeline, model, p, series, periods)["summary"]
            print("  " + p.ljust(12) + "".join(str(s[c]).rjust(13) for c in cols))
        return 0
    p = args.period or periods[-1]
    r = for_period(args.pipeline, model, p, series, periods)
    print(f"{args.pipeline} {p}: " + "  ".join(f"{c} {r['summary'][c]}" for c in ("lines", *cols)))
    for m in r["moves"]:
        print(f"  {m['direction']:4} {m['entity'][:44]:44} Δgap {m['gap_change_pp']:+7.2f} "
              f"(> {m['threshold_pp']:.2f}, vs {m['baseline_kind']}) → {m['filed_under']}"
              f"  {m['also_holds'] or ''}  prices: {m['prices_activity']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
