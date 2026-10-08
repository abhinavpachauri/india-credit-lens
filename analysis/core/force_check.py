#!/usr/bin/env python3
"""
force_check.py — does a force's line beat its baseline, the way the force says it should?
──────────────────────────────────────────────────────────────────────────────────────────
SYSTEM_MODEL_SPEC §16 Step 3 (v3.1). The v3.0 check called a force `active` when any of its
evidence signals had a direction, and about 80% of signal rows read "up" in a given month, so
every force was active every period. Its edges were judged against zero, so a force that holds
a line back failed whenever the line grew at all: the Nov 2023 unsecured risk weights read
`reversed` on credit cards growing 3.6% while personal loans grew 16.9%.

The question asked here instead, of every force→entity edge:

    did the line beat its BASELINE, in the direction the force predicts,
    by more than the line's own normal wobble, while the force is in its window?

Three readings decide it, and all three are stored or are differences of stored rows:
  growth    the entity's YoY, read from signals.db through `growth_series` (one resolver,
            joined declaratively through the registry, never picked per force)
  baseline  chosen by the entity's place in the skeleton (`baseline_of`), never per force
  noise     median |reading-to-reading change of the gap| over the line's own history

Deterministic. No LLM. Nothing here writes; generate_system_state emits the result.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from statistics import median

# Bootstrap: <repo>/analysis on sys.path so `from core import …` resolves from any cwd
# (same .git walk as the other core/ scripts).
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core import generate_skeleton as gs
from signals.compute.csv_sector import resolve_csv_date

DB = gs.ANALYSIS / "signals" / "signals.db"
DRIVER_SIGN = {"drives": 1, "amplifies": 1, "suppresses": -1}
# A force authored active that the data contradicts this many readings running is `in_doubt`.
# generate_system_state reads its MIX_PERSISTENCE from here, so the two filters cannot drift.
PERSISTENCE = 2
# Fewer reading-to-reading changes than this and the line has no measurable wobble yet.
MIN_HISTORY = 3


# ── 1. Growth: one resolver, declared by the registry ────────────────────────────────────

def _children(model: dict) -> dict[str, list[dict]]:
    by_id = {n["id"]: n for n in model["nodes"] if n.get("tier") == "entity"}
    kids: dict[str, list[dict]] = {}
    for e in model["edges"]:
        if e["type"] == "composes_into" and e["from"] in by_id and e["to"] in by_id:
            kids.setdefault(e["to"], []).append(by_id[e["from"]])
    return kids


def growth_series(pipeline: str, model: dict, con=None) -> dict[str, dict[str, float]]:
    """node_id -> {period: YoY %} for every entity the registry gives a YoY reading.

    The registry already says which YoY signal measures which code, in three shapes:
      csv_sector_yoy   one row per (statement, code)           -> that node
      csv_total_yoy    one row per metric (payments codes ARE the metric) -> that node
      *_scan_yoy       one row per member of a parent's cut, keyed by label -> that child
    A direct reading wins over a scan row for the same node; they are the same CSV numbers,
    and preferring one shape keeps the answer independent of registry order.
    """
    registry = gs.load_json(gs.ANALYSIS / "signals" / "registry.json")["signals"]
    ents = [n for n in model["nodes"] if n.get("tier") == "entity"]
    by_code = {}
    for n in ents:
        by_code[(n.get("statement"), str(n.get("code")))] = n
        by_code.setdefault((None, str(n.get("code"))), n)
    kids = _children(model)
    roots = {n.get("decomposition"): n for n in ents if n.get("structural_role") == "root"}

    own = con is None
    con = con or sqlite3.connect(DB)
    direct: dict[str, dict[str, float]] = {}
    scanned: dict[str, dict[str, float]] = {}
    try:
        def rows(sid, etype=None):
            q = "SELECT period, entity_id, value FROM signals WHERE pipeline=? AND metric_id=?"
            args = [pipeline, sid]
            if etype:
                q += " AND entity_type=?"
                args.append(etype)
            return [(p, e, v) for p, e, v in con.execute(q, args) if v is not None]

        for sid, sig in registry.items():
            if sig.get("pipeline") != pipeline:
                continue
            comp = sig.get("compute", {})
            method = comp.get("method")
            if method == "csv_sector_yoy" or method == "csv_total_yoy":
                code = comp.get("code") if method == "csv_sector_yoy" else comp.get("metric")
                node = by_code.get((comp.get("statement"), str(code))) or by_code.get((None, str(code)))
                if node:
                    for p, e, v in rows(sid):
                        if e == "total":
                            direct.setdefault(node["id"], {})[p] = v
            elif method in ("csv_sector_scan_yoy", "csv_psl_scan_yoy"):
                if method == "csv_psl_scan_yoy":
                    parent = roots.get("psl_lens")
                else:
                    code = str(comp.get("parent_code"))
                    # Codes are unique across the skeleton; the industry-by-type children hang
                    # off the Statement-1 Industry node, so the scan's Statement 2 finds no
                    # (statement, code) match and the code alone resolves it.
                    parent = by_code.get((comp.get("statement"), code)) or by_code.get((None, code))
                if not parent:
                    continue
                label = {c["label"]: c for c in kids.get(parent["id"], [])}
                for p, e, v in rows(sid, comp.get("entity_type")):
                    if e in label:
                        scanned.setdefault(label[e]["id"], {})[p] = v
    finally:
        if own:
            con.close()
    return {**scanned, **direct}


# ── 2. Baseline: chosen by the entity's place in the skeleton ────────────────────────────

def _months(d: str) -> int:
    y, m, _ = (int(x) for x in d.split("-"))
    return y * 12 + m - 1


def window_of(force: dict) -> tuple[int, int] | None:
    """[first, end) as month indices, or None for a standing force (always in window)."""
    if force.get("standing"):
        return None
    first = _months(force["starts"]) + int(force["delay_months"])
    return first, first + int(force["fades_after_months"])


def baseline_of(node: dict, force: dict, parent_of: dict, by_id: dict) -> tuple[str, str | None]:
    """(kind, node_id) — what this entity is compared against. SYSTEM_MODEL_SPEC §16 Step 3.

      child of an additive decomposition         -> its parent            ("parent")
      member of a non-additive lens, dated force  -> itself before `starts` ("own_before")
      anything else                               -> the root of its own tree ("root")
    """
    parent = by_id.get(parent_of.get(node["id"]))
    if parent is not None and parent.get("additive", True) and node.get("additive", True):
        return "parent", parent["id"]
    if parent is not None and not force.get("standing"):
        return "own_before", node["id"]
    top = node
    while parent_of.get(top["id"]) in by_id:
        top = by_id[parent_of[top["id"]]]
    return "root", top["id"]


# ── 3. The verdict ───────────────────────────────────────────────────────────────────────

def edge_history(growth: dict[str, float], base: dict[str, float], periods: list[str],
                 own_before: float | None = None) -> list[tuple[str, float]]:
    """(period, gap_pp) for every period where both readings exist, in period order."""
    out = []
    for p in periods:
        g = growth.get(p)
        b = own_before if own_before is not None else base.get(p)
        if g is not None and b is not None:
            out.append((p, g - b))
    return out


def judge(gaps: list[tuple[str, float]], period: str, expected: int,
          in_window: str) -> dict:
    """One edge at one period. `gaps` is the edge's history up to and including `period`."""
    upto = [(p, g) for p, g in gaps if p <= period]
    if not upto or upto[-1][0] != period:
        return {"verdict": "unassessable", "reason": "no growth or baseline reading this period"}
    deltas = [abs(b[1] - a[1]) for a, b in zip(upto, upto[1:])]
    gap = upto[-1][1]
    out = {"gap_pp": round(gap, 2)}
    if in_window != "in_window":
        return {**out, "verdict": in_window}
    if len(deltas) < MIN_HISTORY:
        return {**out, "verdict": "unassessable",
                "reason": f"{len(deltas)} reading-to-reading changes; the wobble needs {MIN_HISTORY}"}
    noise = median(deltas)
    out["noise_pp"] = round(noise, 2)
    if abs(gap) <= noise:
        return {**out, "verdict": "unclear"}
    return {**out, "verdict": "working" if (gap > 0) == (expected > 0) else "contradicted"}


def roll_up(edge_verdicts: list[str]) -> str:
    """A force over its edges: §16 Step 3. Window verdicts carry through when nothing is in it."""
    assessed = [v for v in edge_verdicts if v in ("working", "contradicted", "unclear")]
    if not assessed:
        for w in ("not_yet_due", "faded"):
            if edge_verdicts and all(v == w for v in edge_verdicts):
                return w
        return "unassessable"
    w, c = assessed.count("working"), assessed.count("contradicted")
    return "working" if w > c else "contradicted" if c > w else "unclear"


def check(pipeline: str, model: dict, period: str, series: dict[str, dict[str, float]],
          periods: list[str], data_month=None) -> dict:
    """Every force in `model`, judged at `period`. Pure given its inputs.

    `periods` is the pipeline's full reading list (signals.db order); `data_month` maps a
    period key to the month its data describes (SIBC keys run a month ahead of their data).
    `in_doubt` looks back over the force's own verdicts at earlier readings, recomputed here
    from the same series, never read from an older state file that a previous rule wrote.
    """
    data_month = data_month or (lambda p: resolve_csv_date(pipeline, p))
    by_id = {n["id"]: n for n in model["nodes"] if n.get("tier") == "entity"}
    parent_of = {e["from"]: e["to"] for e in model["edges"]
                 if e["type"] == "composes_into" and e["from"] in by_id and e["to"] in by_id}
    upto = [p for p in periods if p <= period]

    def window_state(force, p):
        w = window_of(force)
        if w is None:
            return "in_window"
        m = _months(data_month(p))
        return "not_yet_due" if m < w[0] else "faded" if m >= w[1] else "in_window"

    def edges_at(force, p):
        out = {}
        for e in model["edges"]:
            if e["from"] != force["id"] or e["type"] not in DRIVER_SIGN or e["to"] not in by_id:
                continue
            node = by_id[e["to"]]
            kind, base_id = baseline_of(node, force, parent_of, by_id)
            g = series.get(node["id"], {})
            own_before = None
            if kind == "own_before":
                first = _months(force["starts"])
                before = [q for q in periods if q in g and _months(data_month(q)) < first]
                if not before:
                    out[e.get("id", f"{e['from']}->{e['to']}")] = {
                        "entity": node["label"], "baseline_kind": kind, "verdict": "unassessable",
                        "reason": "no reading before the force started"}
                    continue
                own_before = g[before[-1]]
            gaps = edge_history(g, series.get(base_id, {}), periods, own_before)
            res = judge(gaps, p, DRIVER_SIGN[e["type"]], window_state(force, p))
            out[e.get("id", f"{e['from']}->{e['to']}")] = {
                "entity": node["label"], "type": e["type"],
                "growth": None if g.get(p) is None else round(g[p], 2),
                "baseline_kind": kind,
                "baseline_of": by_id[base_id]["label"],
                "baseline": (round(own_before, 2) if own_before is not None
                             else None if series.get(base_id, {}).get(p) is None
                             else round(series[base_id][p], 2)),
                **res,
            }
        return out

    result = {}
    for f in model.get("force_instances", []):
        edges = edges_at(f, period)
        verdict = roll_up([x["verdict"] for x in edges.values()])
        reason = None
        if not edges:
            # Loud, not silent: the model never said which way this force pushes, so there is
            # nothing to test. That is an authoring gap for the model pass, not a reading.
            reason = "no drives/suppresses/amplifies edge: the model does not say which way it pushes"
        elif verdict == "unassessable":
            reason = "; ".join(sorted({x.get("reason", "") for x in edges.values()} - {""}))
        recent = [roll_up([x["verdict"] for x in edges_at(f, p).values()])
                  for p in upto[-PERSISTENCE:]]
        result[f["id"]] = {
            "verdict": verdict,
            "window": window_state(f, period),
            "in_doubt": (f.get("status") == "active" and len(recent) == PERSISTENCE
                         and all(v == "contradicted" for v in recent)),
            "edges": edges,
            **({"reason": reason} if reason else {}),
        }
    return result


def periods_of(pipeline: str, con=None) -> list[str]:
    own = con is None
    con = con or sqlite3.connect(DB)
    try:
        return [r[0] for r in con.execute(
            "SELECT DISTINCT period FROM signals WHERE pipeline=? ORDER BY period", (pipeline,))]
    finally:
        if own:
            con.close()


# ── Measurement: old rule vs this one, every period × every force ────────────────────────

def history(pipeline: str) -> list[dict]:
    """One row per (period, force): the v3.0 state beside this check's verdict.

    The measurement SYSTEM_MODEL_SPEC §16 Step 3 asks for before the check is trusted. It
    enumerates every period in signals.db and every force in the model; nothing is sampled.
    """
    from core import generate_system_state as g3
    model = gs.load_json(gs.pipeline_cfg(pipeline)["model"])
    series, periods = growth_series(pipeline, model), periods_of(pipeline)
    rows = []
    for p in periods:
        old = g3.compute(model, g3.load_signal_dirs(pipeline, p)[0])["force_states"]
        new = check(pipeline, model, p, series, periods)
        for fid, x in new.items():
            rows.append({"period": p, "data_month": resolve_csv_date(pipeline, p)[:7],
                         "force": fid, "old": old[fid]["state"], "new": x["verdict"],
                         "in_doubt": x["in_doubt"]})
    return rows


def main() -> int:
    import argparse
    from collections import Counter
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--pipeline", required=True)
    ap.add_argument("--history", action="store_true",
                    help="old vs new for every period × force (the measurement)")
    ap.add_argument("--period", help="one period's full edge detail")
    args = ap.parse_args()

    if args.history:
        rows = history(args.pipeline)
        forces = list(dict.fromkeys(r["force"] for r in rows))
        months = list(dict.fromkeys(r["data_month"] for r in rows))
        cell = {(r["force"], r["data_month"]): r for r in rows}
        short = {"working": "W", "contradicted": "C", "unclear": "u", "not_yet_due": "·",
                 "faded": "f", "unassessable": "?"}
        print(f"{args.pipeline}: {len(forces)} forces × {len(months)} readings "
              f"({months[0]} … {months[-1]})")
        print("  W working · C contradicted · u unclear · · not yet due · f faded · ? unassessable"
              " · ! in doubt\n")
        w = max(len(f) for f in forces)
        for f in forces:
            line = "".join(short[cell[(f, m)]["new"]] + ("!" if cell[(f, m)]["in_doubt"] else " ")
                           for m in months)
            print(f"  {f:<{w}}  {line}")
        old, new = Counter(r["old"] for r in rows), Counter(r["new"] for r in rows)
        print(f"\n  old rule over {len(rows)} force-readings: {dict(old)}")
        print(f"  new rule over {len(rows)} force-readings: {dict(new)}")
        print(f"  in doubt: {sum(r['in_doubt'] for r in rows)} force-readings")
        return 0

    model = gs.load_json(gs.pipeline_cfg(args.pipeline)["model"])
    periods = periods_of(args.pipeline)
    period = args.period or periods[-1]
    res = check(args.pipeline, model, period, growth_series(args.pipeline, model), periods)
    for fid, x in res.items():
        flag = "  ⚠ IN DOUBT" if x["in_doubt"] else ""
        print(f"{fid}: {x['verdict']} ({x['window']}){flag}  {x.get('reason', '')}")
        for e in x["edges"].values():
            print(f"    {e['entity']}: {e.get('growth')} vs {e.get('baseline_kind')} "
                  f"{e.get('baseline_of', '')} {e.get('baseline')} → gap {e.get('gap_pp')} "
                  f"(noise {e.get('noise_pp')}) {e['verdict']}  {e.get('reason', '')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
