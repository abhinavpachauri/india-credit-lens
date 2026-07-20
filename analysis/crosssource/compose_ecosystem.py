#!/usr/bin/env python3
"""
compose_ecosystem.py — cross-system S3 projection (COMPOSITION_SPEC §7 + §21)
------------------------------------------------------------------------------
The federated "combined view" — COMPUTED, never authored. Joins each pipeline's
latest system_state (S3) with the confirmed cross-edges (composition.json) and the
authored meta-model (ecosystem_model.json), and projects:

  cross_edge_states           (v1.0 §7)   aligned | divergent | dormant | linked
  construct_states            (v1.1 §14)  sign-only direction + member basis
  eco_edge_states             (v1.1 §15)  active | reversed | dormant
  eco_loop_states             (v1.1 §16)  same firing rule as per-pipeline S3 loops
  constraint_states           (v1.1 §17)  holds | violated | unobservable (from signals.db)
  ecosystem_observations      (v1.1 §21)
  cross_source_opportunities  (§12.3 + §23.1)  driver ∈ cross_edge | construct | eco_loop | constraint

Sign-only throughout — no magnitude (the locked per-pipeline S3 decision). Reads only
projected state + confirmed/authored structure; never re-derives pipeline internals.

Output: analysis/cross_source/ecosystem_state_{period}.json

Usage:  python3 analysis/crosssource/compose_ecosystem.py
"""
import json
import sqlite3
import sys
from pathlib import Path

# Bootstrap: <repo>/analysis on sys.path so `from core import …` resolves from any cwd now
# that this script lives under crosssource/. Move-safe via .git walk (see core/paths.py).
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core import generate_skeleton as gs  # noqa: E402

ROOT = gs.ROOT
CROSS = ROOT / "analysis" / "cross_source"
DB = gs.ANALYSIS / "signals" / "signals.db"

ROLE_SIGN = {"measures": 1, "proxies": 1, "contra_indicates": -1}
# x-edge state → loop-segment state (aligned flow→stock = the causal segment is running)
X_STATE_AS_EDGE = {"aligned": "active", "divergent": "reversed", "dormant": "dormant"}


def sign(x):
    return (x > 0) - (x < 0)


def _pipe_of(urn):
    try:
        return urn.split(":", 1)[1].split("/", 1)[0]
    except Exception:
        return None


# ── §14 / §15 / §16 / §17 — pure state functions (unit-tested) ────────────────

def construct_direction(construct, urn_dir):
    """Sign-only construct state from member entity directions (§14)."""
    total, observed, acc = 0, 0, 0.0
    members = []
    for m in construct.get("members", []):
        total += 1
        d = urn_dir.get(m["urn"])
        role_sign = ROLE_SIGN.get(m.get("role"), 1)
        if d is None:
            members.append({**m, "direction": None})
            continue
        observed += 1
        acc += d * role_sign * (m.get("weight") or 1)
        members.append({**m, "direction": d})
    return sign(acc), {"observed": observed, "total": total, "members": members}


def eco_edge_state(edge, node_dir):
    """active | reversed | dormant — identical semantics to per-pipeline S3 edges (§15)."""
    d = node_dir.get(edge["from"], 0)
    pol = edge.get("polarity")
    expected = 1 if pol == "+" else -1 if pol == "-" else 0
    if d == 0:
        return "dormant"
    if pol == "~" or sign(d) == expected:
        return "active"
    return "reversed"


def loop_state(loop, resolve_ref):
    """Same firing rule as per-pipeline S3 step 5 (§16). resolve_ref(ref) → state|None."""
    states = [resolve_ref(r) for r in loop.get("member_edges", [])]
    states = [s for s in states if s is not None]
    live = [s for s in states if s in ("active", "reversed")]
    if states and all(s == "active" for s in states):
        st = "active_reinforcing" if loop.get("type") == "reinforcing" else "active_balancing"
    elif live:
        st = "partial"
    else:
        st = "dormant"
    return {"state": st, "type": loop.get("type"), "live_edges": len(live), "total_edges": len(states)}


def eval_constraint(cx, values):
    """Reconciliation constraint (§17). values: {(pipeline, signal_id): value}.
    op 'ratio' (default): v = (a·scale_a) / (b·scale_b); 'diff': a−b.
    Tolerance: corridor [lo, hi] on v · pct/abs on the operand difference."""
    vals = []
    for op in cx.get("operands", []):
        v = values.get((op.get("pipeline"), op.get("signal_id")))
        if v is None:
            return {"state": "unobservable", "value": None}
        vals.append(v * (op.get("scale") or 1))
    if len(vals) != 2:
        return {"state": "unobservable", "value": None}
    kind = cx.get("op", "ratio")
    v = (vals[0] / vals[1]) if kind == "ratio" and vals[1] else (vals[0] - vals[1])
    tol = cx.get("tolerance", {})
    if tol.get("type") == "corridor":
        lo, hi = tol["value"]
        ok = lo <= v <= hi
    elif tol.get("type") == "pct":
        ok = vals[1] != 0 and abs(vals[0] - vals[1]) / abs(vals[1]) * 100 <= tol["value"]
    else:  # abs
        ok = abs(vals[0] - vals[1]) <= tol.get("value", 0)
    return {"state": "holds" if ok else "violated", "value": round(v, 2)}


# ── IO helpers ─────────────────────────────────────────────────────────────────

def latest_states(cfg, n=2):
    """The n most recent system_state files for a pipeline (latest first)."""
    states = sorted(cfg["model"].parent.glob("system_state_*.json"), reverse=True)
    return [gs.load_json(p) for p in states[:n]]


def entity_signal_index(models):
    """entity urn → signal ids; aggregates with none inherit one level of composes_into children."""
    idx, children = {}, {}
    for pipe, m in models.items():
        for n in m["nodes"]:
            if n.get("tier") == "entity" and n.get("urn"):
                idx[n["urn"]] = list(n.get("signal_ids") or [])
        for e in m["edges"]:
            if e["type"] == "composes_into":
                children.setdefault(e["to"], []).append(e["from"])
    for pipe, m in models.items():
        by_id = {n["id"]: n for n in m["nodes"] if n.get("tier") == "entity"}
        for n in m["nodes"]:
            urn = n.get("urn")
            if urn and not idx.get(urn):
                kid_sids = []
                for kid in children.get(n["id"], []):
                    kn = by_id.get(kid)
                    if kn and kn.get("urn"):
                        kid_sids += idx.get(kn["urn"], [])
                idx[urn] = kid_sids
    return idx


def db_values(operand_keys, periods):
    """(pipeline, signal_id) → total-level value at that pipeline's latest period."""
    if not DB.exists() or not operand_keys:
        return {}
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    out = {}
    for pipe, sid in operand_keys:
        period = periods.get(pipe)
        if not period:
            continue
        row = con.execute(
            "select value from signals where pipeline=? and period=? and metric_id=? "
            "and entity_type='total' limit 1", (pipe, period, sid)).fetchone()
        if row is None:
            row = con.execute(
                "select value from signals where pipeline=? and period=? and metric_id=? limit 1",
                (pipe, period, sid)).fetchone()
        if row is not None:
            out[(pipe, sid)] = row[0]
    con.close()
    return out


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    # gather per-pipeline S3 states → urn → direction (latest + previous), edge states
    urn_dir, urn_dir_prev, pipe_edge_states, periods = {}, {}, {}, {}
    for pipe, cfg in gs.PIPELINES.items():
        sts = latest_states(cfg, n=2)
        if not sts:
            print(f"  ⚠ no system_state for {pipe} — run core/generate_system_state.py first", file=sys.stderr)
            continue
        periods[pipe] = sts[0]["_meta"]["period"]
        for urn, s in sts[0]["entity_states"].items():
            urn_dir[urn] = s["direction"]
        pipe_edge_states[pipe] = {k: v["state"] for k, v in sts[0].get("edge_states", {}).items()}
        if len(sts) > 1:
            for urn, s in sts[1]["entity_states"].items():
                urn_dir_prev[urn] = s["direction"]

    comp_path = CROSS / "composition.json"
    if not comp_path.exists():
        print("✗ no composition.json", file=sys.stderr)
        return 1
    cross_edges = gs.load_json(comp_path).get("cross_edges", [])
    eco_path = CROSS / "ecosystem_model.json"
    eco = gs.load_json(eco_path) if eco_path.exists() else {}
    models = {p: gs.load_json(cfg["model"]) for p, cfg in gs.PIPELINES.items() if cfg["model"].exists()}
    sig_idx = entity_signal_index(models)

    # ── cross-edge states + cross-edge opportunities (v1.0, unchanged) ──────────
    edge_states, premium = [], []
    for e in cross_edges:
        fd, td = urn_dir.get(e["from"], 0), urn_dir.get(e["to"], 0)
        if e["type"] == "leads":
            state = "dormant" if fd == 0 else ("aligned" if fd == td or td == 0 else "divergent")
        else:  # corresponds_to / structural
            state = "linked"
        item = {"id": e["id"], "type": e["type"], "from": e["from"], "to": e["to"],
                "from_direction": fd, "to_direction": td, "state": state,
                "shared": e.get("shared"), "derived_from": e.get("derived_from")}
        edge_states.append(item)

        # premium cross_source opportunity: an active 'leads' cross-edge is an opening
        if e["type"] == "leads" and fd != 0:
            # Evidence = both endpoints' signals. The endpoints ARE the claim ("flow leads
            # stock"), so the full set is also the firing set — and it gives the narrative
            # step real numbers to reason over (Check 4f validates against evidence_all).
            xsig = list(dict.fromkeys(
                s for u in (e["from"], e["to"]) for s in sig_idx.get(u, [])))
            premium.append({
                "evidence": xsig, "evidence_all": xsig,
                "id": f"xopp_{e['id']}",
                "scope": "cross_source", "surface": "opportunities",
                "driver": {"kind": "cross_edge", "id": e["id"]},
                "status": "active" if fd > 0 else "watch",
                "label": f"Cross-system signal: {e['shared'].get('product')} "
                         f"{'flow leading stock — origination headroom' if fd > 0 else 'flow softening ahead of stock'}",
                "refs": {"cross_edge": e["id"], "entities": [e["from"], e["to"]]},
                "mechanism": e.get("mechanism"),
            })
    x_state = {e["id"]: e["state"] for e in edge_states}

    # ── construct states (§14) ──────────────────────────────────────────────────
    construct_states, node_dir = {}, dict(urn_dir)
    constructs = {c["urn"]: c for c in eco.get("constructs", [])}
    for urn, c in constructs.items():
        d, basis = construct_direction(c, urn_dir)
        d_prev, _ = construct_direction(c, urn_dir_prev)
        involved = sorted({p for m in c.get("members", []) if (p := _pipe_of(m["urn"]))})
        construct_states[urn] = {
            "direction": d, "direction_prev": d_prev, "label": c.get("label"),
            "basis": {**basis, "pipelines": {p: periods.get(p) for p in involved}},
        }
        node_dir[urn] = d

    # ── eco-edge states (§15) ────────────────────────────────────────────────────
    eco_edges = {e["id"]: e for e in eco.get("eco_edges", [])}
    eco_edge_states = {eid: {"state": eco_edge_state(e, node_dir), "from": e["from"],
                             "to": e["to"], "polarity": e.get("polarity"), "type": e.get("type")}
                       for eid, e in eco_edges.items()}

    # ── loop states (§16) ────────────────────────────────────────────────────────
    def resolve_ref(ref):
        kind, _, rest = ref.partition(":")
        if kind == "x":
            return X_STATE_AS_EDGE.get(x_state.get(rest), "dormant")
        if kind == "eco":
            return eco_edge_states.get(rest, {}).get("state", "dormant")
        return pipe_edge_states.get(kind, {}).get(rest)

    eco_loop_states = {}
    for lp in eco.get("loops", []):
        st = loop_state(lp, resolve_ref)
        involved = sorted({r.partition(":")[0] for r in lp.get("member_edges", [])
                           if r.partition(":")[0] in periods})
        st["input_periods"] = {p: periods[p] for p in involved} or dict(periods)
        st["mixed_period"] = len(set(st["input_periods"].values())) > 1
        eco_loop_states[lp["id"]] = st

    # ── constraint states (§17) ──────────────────────────────────────────────────
    operand_keys = [(op.get("pipeline"), op.get("signal_id"))
                    for cx in eco.get("constraints", []) for op in cx.get("operands", [])]
    values = db_values(operand_keys, periods)
    constraint_states = {}
    for cx in eco.get("constraints", []):
        r = eval_constraint(cx, values)
        r["severity"] = cx.get("severity")
        r["tolerance"] = cx.get("tolerance")
        constraint_states[cx["id"]] = r

    # ── eco-driven opportunities (§23.1) ────────────────────────────────────────
    def member_evidence(c):
        firing, declared = [], []
        for m in c.get("members", []):
            sids = sig_idx.get(m["urn"], [])
            declared += sids
            if urn_dir.get(m["urn"]):
                firing += sids
        return list(dict.fromkeys(firing)), list(dict.fromkeys(declared))

    for urn, st in construct_states.items():
        c = constructs[urn]
        d, dp = st["direction"], st["direction_prev"]
        if d != 0 and dp == d:
            status = "active"           # sustained ≥2 composed periods
        elif d != 0 or dp != 0:
            status = "watch"            # new, flipped, or fading
        else:
            continue                    # dormant both periods — nothing to surface
        evidence, evidence_all = member_evidence(c)
        word = "expanding" if d > 0 else "contracting" if d < 0 else "turning"
        premium.append({
            "id": f"xopp_eco_{c['id']}",
            "scope": "cross_source", "surface": "opportunities",
            "driver": {"kind": "construct", "id": c["id"]},
            "status": status,
            "label": f"{c.get('label', c['id'])} — {word} "
                     f"({st['basis']['observed']}/{st['basis']['total']} measurements observed)",
            "refs": {"construct": urn, "entities": [m["urn"] for m in c.get("members", [])]},
            "mechanism": c.get("definition"),
            "evidence": evidence, "evidence_all": evidence_all,
        })

    for lid, st in eco_loop_states.items():
        if st["state"] == "dormant":
            continue
        lp = next(l for l in eco.get("loops", []) if l["id"] == lid)
        status = "active" if st["state"].startswith("active") else "watch"
        ents = []
        for ref in lp.get("member_edges", []):
            kind, _, rest = ref.partition(":")
            if kind == "x":
                xe = next((x for x in cross_edges if x["id"] == rest), None)
                if xe:
                    ents += [xe["from"], xe["to"]]
            elif kind == "eco":
                ee = eco_edges.get(rest)
                if ee:
                    ents += [v for v in (ee["from"], ee["to"]) if v in urn_dir]
        ents = list(dict.fromkeys(ents))
        evidence_all = list(dict.fromkeys(s for u in ents for s in sig_idx.get(u, [])))
        premium.append({
            "id": f"xopp_loop_{lid}",
            "scope": "cross_source", "surface": "opportunities",
            "driver": {"kind": "eco_loop", "id": lid},
            "status": status,
            "label": f"{lp.get('label', lid)} — "
                     f"{'running' if status == 'active' else 'partially engaged'} "
                     f"({st['live_edges']}/{st['total_edges']} segments live)",
            "refs": {"eco_loop": lid, "entities": ents},
            "mechanism": lp.get("description"),
            "evidence": evidence_all if status == "active" else [],
            "evidence_all": evidence_all,
        })

    for cid, st in constraint_states.items():
        if st["state"] != "violated":
            continue
        cx = next(c for c in eco.get("constraints", []) if c["id"] == cid)
        sids = [op["signal_id"] for op in cx.get("operands", [])]
        premium.append({
            "id": f"xrisk_{cid}",
            "scope": "cross_source", "surface": "opportunities", "tier": "risk",
            "driver": {"kind": "constraint", "id": cid},
            "status": "active",
            "label": f"Data check violated: {cx.get('label', cid)}",
            "refs": {"constraint": cid, "entities": []},
            "mechanism": cx.get("relation"),
            "evidence": sids, "evidence_all": sids,
        })

    # ── observations + output ───────────────────────────────────────────────────
    observations = {
        "dominant_constructs": [u for u, s in construct_states.items() if s["direction"] != 0],
        "binding_constraints": [k for k, v in eco_edge_states.items()
                                if v["polarity"] == "-" and v["state"] == "active"],
        "active_loops": [k for k, v in eco_loop_states.items() if v["state"].startswith("active")],
        "reconciliation_violations": [k for k, v in constraint_states.items() if v["state"] == "violated"],
    }

    label = max(periods.values()) if periods else "unknown"
    out = {
        "_meta": {"description": "Computed cross-system ecosystem projection (S3 composed). "
                                 "Never hand-edited.", "spec_ref": "analysis/COMPOSITION_SPEC.md §7 + §21",
                  "pipeline_periods": periods, "period": label},
        "cross_edge_states": edge_states,
        "construct_states": construct_states,
        "eco_edge_states": eco_edge_states,
        "eco_loop_states": eco_loop_states,
        "constraint_states": constraint_states,
        "ecosystem_observations": observations,
        "cross_source_opportunities": premium,
    }
    CROSS.mkdir(parents=True, exist_ok=True)
    out_path = CROSS / f"ecosystem_state_{label}.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False))

    print(f"[ecosystem {label}] projected {len(edge_states)} cross-edges, {len(construct_states)} constructs, "
          f"{len(eco_edge_states)} eco-edges, {len(eco_loop_states)} loops, {len(constraint_states)} constraints "
          f"from {len(urn_dir)} entity states")
    for e in edge_states:
        print(f"    {e['state']:9s} {e['from']}  --{e['type']}-->  {e['to']}  (f={e['from_direction']},t={e['to_direction']})")
    for u, s in construct_states.items():
        print(f"    dir={s['direction']:+d} (prev {s['direction_prev']:+d}) {u}  "
              f"[{s['basis']['observed']}/{s['basis']['total']} observed]")
    for k, v in eco_loop_states.items():
        print(f"    {v['state']:18s} loop {k}  ({v['live_edges']}/{v['total_edges']} live)")
    for k, v in constraint_states.items():
        print(f"    {v['state']:12s} constraint {k}  value={v.get('value')}")
    print(f"  cross_source opportunities ({len(premium)}):")
    for p in premium:
        print(f"    ✓ {p['status']:6s} [{p.get('driver', {}).get('kind', '?'):10s}] {p['label']}")
    print(f"  → wrote {out_path.relative_to(ROOT)}")

    # a violated fail-severity constraint is a data-integrity failure — fail the gate
    hard = [k for k, v in constraint_states.items()
            if v["state"] == "violated" and v.get("severity") == "fail"]
    if hard:
        print(f"✗ FAIL — {len(hard)} fail-severity constraint(s) violated: {hard}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
