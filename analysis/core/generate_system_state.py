#!/usr/bin/env python3
"""
generate_system_state.py — stratum S3 (dynamic causal view)
-----------------------------------------------------------
Computes a period's dynamic state by applying live Layer-1 signal states over a
pipeline's static system model (SYSTEM_MODEL_SPEC §16, COMPOSITION_SPEC S3).
Deterministic — no LLM. Reads signals.db; never authors.

Steps:
  1. Leaf entity directions   — sign of the entity's signal statuses this period.
  2. Mechanical propagation    — aggregate directions roll up composes_into (per decomposition).
  3. Force-instance states     — active | latent from signal_evidence.
  4. Behavioral edge states    — active | reversed | dormant by from-direction × polarity (sign-only).
  5. Loop states               — active_reinforcing | active_balancing | partial | dormant.
  6. System observations       — dominant forces, binding constraints, active loops.

Output: analysis/{pipeline}/merged/system_state_{period}.json  (narrative:null slot for Stage 5.X).

Usage:
    python3 analysis/generate_system_state.py --pipeline sibc    --period 2026-05-29
    python3 analysis/generate_system_state.py --pipeline atm_pos --period 2026-04-30
"""
import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

# Bootstrap: put <repo>/analysis on sys.path so `from core import …` resolves from any
# cwd now that this script lives under core/. Move-safe via .git walk (see core/paths.py).
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core import generate_skeleton as gs  # noqa: E402

DB = gs.ANALYSIS / "signals" / "signals.db"
# Direction map covering every status the L1 compute layer can emit: registry status_rules
# emit strengthening/active/weakening/declining, plus `unknown` when a value is unavailable.
# `unknown` is a genuine zero. Any status OUTSIDE this set is an L1-contract violation and is
# surfaced loudly (never silently zeroed) — a silent `.get(s, 0)` catch-all previously hid
# `reversed`-class statuses from S3 entirely. See HANDOFF_PIPELINE_REVIEW §5.
STATUS_DIR = {"strengthening": 1, "active": 1, "weakening": -1, "declining": -1, "unknown": 0}


def sign(x):
    return 1 if x > 0 else -1 if x < 0 else 0


def load_signal_dirs(pipeline, period):
    """metric_id -> direction (+1/0/-1) for the period. Warns on any status the L1 contract
    does not define rather than silently treating it as no-direction."""
    con = sqlite3.connect(DB)
    rows = con.execute(
        "select metric_id, status from signals where pipeline=? and period=?",
        (pipeline, period)).fetchall()
    con.close()
    unmapped = sorted({s for _, s in rows if s not in STATUS_DIR})
    if unmapped:
        print(f"⚠ generate_system_state: {len(unmapped)} unmapped signal status(es) "
              f"treated as no-direction (not in STATUS_DIR): {unmapped}", file=sys.stderr)
    return {m: STATUS_DIR.get(s, 0) for m, s in rows}, {m: s for m, s in rows}


def load_entity_weights(cfg):
    """entity_id -> absolute CSV value (latest period), for share-weighted propagation.
    Falls back silently to unweighted where a value is unavailable."""
    profile = gs.load_json(cfg["profile"])
    cols = profile["columns"]
    weights = {}
    model = gs.load_json(cfg["model"])
    if profile["hierarchy_source"] == "csv":
        vals = {}
        for r in gs.latest_rows_csv(profile):
            code = r[cols["code"]].strip()
            if code:
                try:
                    vals[(r[cols["partition"]], code)] = abs(float(r[cols["value"]] or 0))
                except ValueError:
                    pass
        for n in model["nodes"]:
            if n.get("tier") == "entity":
                weights[n["id"]] = vals.get((n.get("statement"), n.get("code")), 0.0)
    else:
        import csv as _csv
        rows = list(_csv.DictReader(open(gs.ROOT / profile["source_csv"])))
        for k, v in profile.get("csv_filter", {}).items():
            rows = [r for r in rows if r[k] == v]
        for col in profile.get("period_selection", {}).get("order_by", []):
            mx = max(r[col] for r in rows)
            rows = [r for r in rows if r[col] == mx]
        vals = {}
        for r in rows:
            try:
                vals[r[cols["metric"]]] = abs(float(r[cols["value"]] or 0))
            except ValueError:
                pass
        for n in model["nodes"]:
            if n.get("tier") == "entity" and n.get("metric"):
                weights[n["id"]] = vals.get(n["metric"], 0.0)
    return weights


ALIGNED_MIN, CONTESTED_MIN = 0.90, 0.50
MIX_PERSISTENCE = 2       # same noise filter derive_opportunities uses before `active`


# Momentum across every pipeline's own decomposition. Payments computed these from the
# day the family shipped; nothing read them, so `mix_states` returned {} for the pipeline
# whose mixes actually move — SIBC runs coherence 0.99-1.00 at every depth while debit
# cards sit at 0.525 and POS terminals at 0.864.
MOMENTUM_METHODS = ("csv_sector_momentum", "csv_category_momentum")


def mix_states(pipeline: str, period: str, model: dict) -> dict:
    """§16 Step 2b — is this hierarchy's mix being MANAGED, and toward what?

    Steps 1-2 reduce every signal to a sign, which cannot express the one thing a credit mix
    actually does. This reads the Layer-1 movement rows (signals/README.md) straight from
    signals.db and returns a state per parent entity. No new registry signals: the registry
    stays L1-computed-only, and this is a computed field on the node, like `coherence`.

    Joined declaratively — a momentum signal's `compute.parent_code` + `statement` name the
    entity whose children it measures, so adding a cut is a registry entry and nothing else.
    """
    registry = gs.load_json(gs.ANALYSIS / "signals" / "registry.json")["signals"]
    # Code is unique across the skeleton (industry-by-type children hang off the same
    # Statement-1 industry node as industry-by-size), so join on code alone.
    by_code = {str(n.get("code")): n
               for n in model["nodes"] if n.get("tier") == "entity" and n.get("code")}
    con = sqlite3.connect(DB)
    out: dict[str, dict] = {}
    try:
        for sid, sig in registry.items():
            comp = sig.get("compute", {})
            if sig.get("pipeline") != pipeline or comp.get("method") not in MOMENTUM_METHODS:
                continue
            # A momentum signal names the node whose mix it measures in one of two ways,
            # because the two pipelines decompose differently: SIBC splits a parent CODE
            # into child sectors, payments splits one METRIC across bank categories. Both
            # resolve against the same node index — payments entity nodes carry the metric
            # name as their code — so this is a second key, not a second mechanism.
            node = by_code.get(str(comp.get("parent_code") or comp.get("metric")))
            if node is None:
                continue          # e.g. the PSL memo block is a child of no code
            alloc_sid = sid.replace("-momentum", "-allocation")

            def rows(metric, etype, per=period):
                return {e: v for e, v in con.execute(
                    "SELECT entity_id, value FROM signals WHERE pipeline=? AND period=? "
                    "AND metric_id=? AND entity_type=?", (pipeline, per, metric, etype))}

            coh = rows(sid, "aggregate").get("coherence")
            alloc, weight = rows(alloc_sid, "alloc"), rows(alloc_sid, "weight")
            if coh is None or not weight:
                continue
            tilt = {k: alloc[k] - weight[k] for k in alloc if k in weight}

            state, toward, toward_tilt, away = "drifting", None, None, None
            if coh < CONTESTED_MIN:
                state = "reallocating"
            elif coh < ALIGNED_MIN:
                state = "contested"
            elif tilt:
                # `toward` is the biggest POSITIVE tilt — the child the new money is favouring.
                # argmax|tilt| would name the biggest mover in either direction, so a mix
                # steered AWAY from something would be reported as steered toward it.
                toward = max(tilt, key=lambda k: tilt[k])
                away   = min(tilt, key=lambda k: tilt[k])
                toward_tilt = tilt[toward]
                # "Material" is measured against THIS cut's own history, never a constant: max
                # |tilt| scales with the number of children (5.6pp median across 4 main sectors,
                # 23.7pp across 19 industry types), so one threshold would call the same
                # behaviour material in one cut and noise in another.
                hist, periods = [], [r[0] for r in con.execute(
                    "SELECT DISTINCT period FROM signals WHERE pipeline=? AND metric_id=? "
                    "ORDER BY period", (pipeline, alloc_sid))]
                leads = []
                for per in periods:
                    a, w = rows(alloc_sid, "alloc", per), rows(alloc_sid, "weight", per)
                    t = {k: a[k] - w[k] for k in a if k in w}
                    if t:
                        top = max(t, key=lambda k: t[k])
                        hist.append(t[top]); leads.append((per, top))
                typical = sorted(hist)[len(hist) // 2] if hist else 0.0
                held = sum(1 for _, l in leads[-MIX_PERSISTENCE:] if l == toward)
                if toward_tilt >= typical and held >= MIX_PERSISTENCE:
                    state = "steered"
            # Keyed by CUT, not by entity: industry carries two decompositions (by size on
            # Statement 1, by type on Statement 2) that hang off the same node, and they are
            # different mixes with different states. Keying by entity would silently drop one.
            out[sid] = {
                "entity_urn": node.get("urn") or node["id"],
                "decomposition": comp.get("statement"),
                "mix_state": state, "coherence": round(coh, 4),
                "toward": toward, "away_from": away,
                "toward_tilt_pp": round(toward_tilt, 2) if toward_tilt is not None else None,
                "children": len(tilt),
            }
    finally:
        con.close()
    return out


def compute(model, sig_dir, weights=None):
    weights = weights or {}
    entities = [n for n in model["nodes"] if n.get("tier") == "entity"]
    by_id = {n["id"]: n for n in entities}
    children = defaultdict(list)   # parent_id -> [(child_id, decomposition)]
    for e in model["edges"]:
        if e["type"] == "composes_into":
            children[e["to"]].append((e["from"], e.get("decomposition", "primary")))

    # Step 1 — leaf directions from signals
    entity_dir, entity_basis = {}, {}
    for n in entities:
        sids = n.get("signal_ids") or []
        dirs = [sig_dir[s] for s in sids if s in sig_dir]
        d = sign(sum(dirs)) if dirs else 0
        entity_dir[n["id"]] = d
        entity_basis[n["id"]] = {"signals": len(sids), "observed": len(dirs)}

    # Step 2 — propagate aggregates bottom-up (leaves already set; recompute aggregates)
    def resolve(nid, seen=None):
        seen = seen or set()
        if nid in seen:
            return entity_dir.get(nid, 0)
        seen.add(nid)
        kids = children.get(nid)
        if not kids:
            return entity_dir.get(nid, 0)
        # share-weighted within a decomposition (dominant children win); decompositions
        # combined by sign of their weighted directions. Falls back to unit weights.
        by_dec = defaultdict(float)
        contrib = defaultdict(list)     # decomposition -> [signed child contributions]
        for cid, dec in kids:
            d = resolve(cid, seen)
            c = d * (weights.get(cid, 0.0) or 1.0)
            by_dec[dec] += c
            contrib[dec].append(c)
        own = entity_dir.get(nid, 0)
        agg = sign(sum(sign(v) for v in by_dec.values()))
        entity_dir[nid] = own if own != 0 else agg

        # How much did the children AGREE? A parent reading +1 because every child rose
        # and one reading +1 because three rose while two fell are the same number today,
        # and every downstream consumer — edge firing, loop state, opportunity status,
        # narrative — inherits that blindness. Measured on the PRIMARY decomposition:
        # the alternates are other views of the same total, so pooling them double-counts.
        prim = contrib.get("primary") or next(iter(contrib.values()), [])
        gross = sum(abs(c) for c in prim)
        if gross:
            entity_basis.setdefault(nid, {})["coherence"] = round(abs(sum(prim)) / gross, 4)
            entity_basis[nid]["children"] = len(prim)
        return entity_dir[nid]

    for n in entities:
        if n.get("structural_role") in ("root", "aggregate"):
            resolve(n["id"])

    # Step 3 — force-instance states
    force_states = {}
    for fi in model.get("force_instances", []):
        ev = fi.get("signal_evidence") or []
        observed = [sig_dir[s] for s in ev if s in sig_dir]
        firing = any(d != 0 for d in observed)
        force_states[fi["id"]] = {
            "state": "active" if firing else "latent",
            "instance_of": fi.get("instance_of"),
            "evidence_observed": len(observed), "evidence_total": len(ev),
            "authored_status": fi.get("status"),
            "mismatch": (fi.get("status") == "active" and not firing),
        }

    # Step 4 — behavioral edge states
    def node_dir(nid):
        if nid in entity_dir:
            return entity_dir[nid]
        if nid in force_states:
            return 1 if force_states[nid]["state"] == "active" else 0
        return 0
    # Edge firing state. Node direction is sign-only ({-1, 0, +1}) — S3 deliberately does not
    # model magnitude (see HANDOFF_PIPELINE_REVIEW §5), so there is no dominant/active split:
    # an edge fires in its expected direction ("active"), against it ("reversed"), or not at
    # all ("dormant"). The prior `"dominant" if abs(d) >= 1` branch was unreachable because
    # abs(d) is always 1 when d != 0.
    edge_states = {}
    for e in model["edges"]:
        pol = e.get("polarity")
        if pol not in ("+", "-", "~"):
            continue
        d = node_dir(e["from"])
        expected = 1 if pol == "+" else -1 if pol == "-" else 0
        if d == 0:
            st = "dormant"
        elif pol == "~" or sign(d) == expected:
            st = "active"
        else:
            st = "reversed"
        edge_states[e.get("id", f"{e['from']}->{e['to']}")] = {
            "state": st, "type": e["type"], "polarity": pol,
            "from": e["from"], "to": e["to"]}

    # Step 5 — loop states
    loop_states = {}
    for lp in model.get("loops", []):
        states = [edge_states.get(eid, {}).get("state") for eid in lp.get("participating_edges", [])]
        live = [s for s in states if s in ("active", "reversed")]
        if states and all(s == "active" for s in states):
            st = "active_reinforcing" if lp.get("type") == "reinforcing" else "active_balancing"
        elif live:
            st = "partial"
        else:
            st = "dormant"
        loop_states[lp["id"]] = {"state": st, "type": lp.get("type"),
                                 "live_edges": len(live), "total_edges": len(states)}

    # Step 6 — observations
    obs = {
        "dominant_forces": [k for k, v in force_states.items() if v["state"] == "active"],
        "binding_constraints": [k for k, v in edge_states.items()
                                if v["polarity"] == "-" and v["state"] == "active"],
        "active_reinforcing_loops": [k for k, v in loop_states.items() if v["state"] == "active_reinforcing"],
        "active_balancing_loops": [k for k, v in loop_states.items() if v["state"] == "active_balancing"],
        "authored_vs_observed_mismatches": [k for k, v in force_states.items() if v["mismatch"]],
    }
    return {
        "entity_states": {by_id[i]["urn"]: {"direction": entity_dir[i], **entity_basis.get(i, {})}
                          for i in entity_dir if i in by_id},
        "force_states": force_states,
        "edge_states": edge_states,
        "loop_states": loop_states,
        "system_observations": obs,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pipeline", required=True, choices=list(gs.PIPELINES))
    ap.add_argument("--period", required=True)
    args = ap.parse_args()

    cfg = gs.PIPELINES[args.pipeline]
    model = gs.load_json(cfg["model"])
    sig_dir, sig_status = load_signal_dirs(args.pipeline, args.period)
    if not sig_dir:
        print(f"✗ no signals in DB for {args.pipeline} {args.period}", file=sys.stderr)
        return 1

    weights = load_entity_weights(cfg)
    state = compute(model, sig_dir, weights)
    state["mix_states"] = mix_states(args.pipeline, args.period, model)
    out = {
        "_meta": {
            "pipeline": args.pipeline, "period": args.period,
            "schema_version": "4.0", "spec_ref": "analysis/SYSTEM_MODEL_SPEC.md §16",
            "computed_from": "signals.db", "signals_observed": len(sig_dir),
        },
        **state,
        "narrative": None,
    }
    out_path = cfg["model"].parent / f"system_state_{args.period}.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False))

    o = state["system_observations"]
    print(f"[{args.pipeline} {args.period}] state computed from {len(sig_dir)} signals")
    print(f"  dominant forces ({len(o['dominant_forces'])}): {o['dominant_forces']}")
    print(f"  binding constraints (active '-' edges): {len(o['binding_constraints'])}")
    print(f"  active loops: reinforcing={o['active_reinforcing_loops']} balancing={o['active_balancing_loops']}")
    if o["authored_vs_observed_mismatches"]:
        print(f"  ⚠ S2b/S3 mismatches (authored active, not firing): {o['authored_vs_observed_mismatches']}")
    print(f"  → wrote {out_path.relative_to(gs.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
