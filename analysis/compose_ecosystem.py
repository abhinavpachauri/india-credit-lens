#!/usr/bin/env python3
"""
compose_ecosystem.py — cross-system S3 projection (COMPOSITION_SPEC §7)
----------------------------------------------------------------------
The federated "combined view" — COMPUTED, never authored. Joins each pipeline's
latest system_state (S3) with the confirmed cross-edges (composition.json) and
projects the cross-system dynamic graph + the premium scope:cross_source
opportunity feed (§12.4). Reads only projected state + confirmed edges.

Output: analysis/cross_source/ecosystem_state_{period}.json

Usage:  python3 analysis/compose_ecosystem.py
"""
import json
import sys
from pathlib import Path

import generate_skeleton as gs

ROOT = gs.ROOT
CROSS = ROOT / "analysis" / "cross_source"


def latest_state(cfg):
    states = sorted(cfg["model"].parent.glob("system_state_*.json"))
    return gs.load_json(states[-1]) if states else None


def main():
    # gather per-pipeline S3 states → global urn → direction
    urn_dir, periods = {}, {}
    for pipe, cfg in gs.PIPELINES.items():
        st = latest_state(cfg)
        if not st:
            print(f"  ⚠ no system_state for {pipe} — run generate_system_state.py first", file=sys.stderr)
            continue
        periods[pipe] = st["_meta"]["period"]
        for urn, s in st["entity_states"].items():
            urn_dir[urn] = s["direction"]

    comp_path = CROSS / "composition.json"
    if not comp_path.exists():
        print("✗ no composition.json", file=sys.stderr)
        return 1
    cross_edges = gs.load_json(comp_path).get("cross_edges", [])

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
            premium.append({
                "id": f"xopp_{e['id']}",
                "scope": "cross_source", "surface": "opportunities",
                "status": "active" if fd > 0 else "watch",
                "label": f"Cross-system signal: {e['shared'].get('product')} "
                         f"{'flow leading stock — origination headroom' if fd > 0 else 'flow softening ahead of stock'}",
                "refs": {"cross_edge": e["id"], "entities": [e["from"], e["to"]]},
                "mechanism": e.get("mechanism"),
            })

    label = max(periods.values()) if periods else "unknown"
    out = {
        "_meta": {"description": "Computed cross-system ecosystem projection (S3 composed). "
                                 "Never hand-edited.", "spec_ref": "analysis/COMPOSITION_SPEC.md §7",
                  "pipeline_periods": periods, "period": label},
        "cross_edge_states": edge_states,
        "cross_source_opportunities": premium,
    }
    CROSS.mkdir(parents=True, exist_ok=True)
    out_path = CROSS / f"ecosystem_state_{label}.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False))

    print(f"[ecosystem {label}] projected {len(edge_states)} cross-edges from {len(urn_dir)} entity states")
    for e in edge_states:
        print(f"    {e['state']:9s} {e['from']}  --{e['type']}-->  {e['to']}  (f={e['from_direction']},t={e['to_direction']})")
    print(f"  premium cross_source opportunities ({len(premium)}):")
    for p in premium:
        print(f"    ✓ {p['status']:6s} {p['label']}")
    print(f"  → wrote {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
