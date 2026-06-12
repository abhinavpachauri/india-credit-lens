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
  4. Behavioral edge states    — active | dominant | dormant | reversed by from-direction × polarity.
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

import generate_skeleton as gs

DB = gs.ANALYSIS / "signals" / "signals.db"
STATUS_DIR = {"strengthening": 1, "active": 1, "weakening": -1, "declining": -1}


def sign(x):
    return 1 if x > 0 else -1 if x < 0 else 0


def load_signal_dirs(pipeline, period):
    """metric_id -> direction (+1/0/-1) for the period."""
    con = sqlite3.connect(DB)
    rows = con.execute(
        "select metric_id, status from signals where pipeline=? and period=?",
        (pipeline, period)).fetchall()
    con.close()
    return {m: STATUS_DIR.get(s, 0) for m, s in rows}, {m: s for m, s in rows}


def compute(model, sig_dir):
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
        # per-decomposition mean, then combine across decompositions by sign of sum
        by_dec = defaultdict(list)
        for cid, dec in kids:
            by_dec[dec].append(resolve(cid, seen))
        # if a leaf-derived signal already set this aggregate, keep the stronger evidence:
        own = entity_dir.get(nid, 0)
        agg = sign(sum(sign(sum(v)) for v in by_dec.values()))
        entity_dir[nid] = own if own != 0 else agg
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
    edge_states = {}
    for e in model["edges"]:
        pol = e.get("polarity")
        if pol not in ("+", "-", "~"):
            continue
        d = node_dir(e["from"])
        expected = 1 if pol == "+" else -1 if pol == "-" else 0
        if d == 0:
            st = "dormant"
        elif pol == "~":
            st = "active"
        elif sign(d) == expected:
            st = "dominant" if abs(d) >= 1 else "active"
        else:
            st = "reversed"
        edge_states[e.get("id", f"{e['from']}->{e['to']}")] = {
            "state": st, "type": e["type"], "polarity": pol,
            "from": e["from"], "to": e["to"]}

    # Step 5 — loop states
    loop_states = {}
    for lp in model.get("loops", []):
        states = [edge_states.get(eid, {}).get("state") for eid in lp.get("participating_edges", [])]
        live = [s for s in states if s in ("active", "dominant", "reversed")]
        if states and all(s in ("active", "dominant") for s in states):
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
                                if v["polarity"] == "-" and v["state"] in ("active", "dominant")],
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

    state = compute(model, sig_dir)
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
