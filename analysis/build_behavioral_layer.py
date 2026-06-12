#!/usr/bin/env python3
"""
build_behavioral_layer.py — one-time FOUNDATION helper
------------------------------------------------------
Re-anchors the behavioral content (forces, risks, opportunities, gaps, behavioral
edges, loops) from a stale pre-skeleton draft onto a freshly-generated v3.0
skeleton, enforcing the SPEC §9 discipline rules:
  - drops any behavioral edge that duplicates a composes_into ancestor link (D1),
  - tags cross-decomposition behavioral edges with double_count_risk (D3).
Writes the merged behavioral layer INTO the pipeline's system_model.json (the
generate_skeleton merge then preserves it on every future regeneration).

Usage:
    python3 analysis/build_behavioral_layer.py --pipeline sibc   --draft analysis/rbi_sibc/merged/system_model_v3_draft.json --map sibc
    python3 analysis/build_behavioral_layer.py --pipeline atm_pos --draft analysis/rbi_atm_pos/merged/system_model_draft.json --map atm_pos
"""
import argparse
import json
import sys
from pathlib import Path

import generate_skeleton as gs

# old draft entity-id  ->  (statement/partition, code) in the new skeleton
ENTITY_MAPS = {
    "sibc": {
        "entity_bank_credit": ("Statement 1", "I"),
        "entity_food_credit": ("Statement 1", "II"),
        "entity_industry": ("Statement 1", "2"),
        "entity_services": ("Statement 1", "3"),
        "entity_personal_loans": ("Statement 1", "4"),
        "entity_msme": ("Statement 1", "2.1"),
        "entity_large_corporate": ("Statement 1", "2.3"),
        "entity_medium_enterprise": ("Statement 1", "2.2"),
        "entity_all_engineering": ("Statement 2", "2.14"),
        "entity_infrastructure_credit": ("Statement 2", "2.18"),
        "entity_chemicals_petroleum": ("Statement 2", "2.9"),
        "entity_basic_metals": ("Statement 2", "2.13"),
        "entity_computer_software": ("Statement 1", "3.2"),
        "entity_trade": ("Statement 1", "3.7"),
        "entity_transport": ("Statement 1", "3.1"),
        "entity_gold_loans": ("Statement 1", "4.8"),
        "entity_credit_cards": ("Statement 1", "4.5"),
        "entity_vehicle_loans": ("Statement 1", "4.7"),
        "entity_consumer_durables": ("Statement 1", "4.1"),
        "entity_psl_housing": ("Statement 1", "iv"),
        "entity_export_credit": ("Statement 1", "viii"),
    },
    "atm_pos": {
        # draft conflates value+volume into one txn entity; anchor to the value node
        "entity_pos_terminals": ("infrastructure", "pos_terminals"),
        "entity_upi_qr": ("infrastructure", "upi_qr"),
        "entity_atm_onsite": ("infrastructure", "atm_onsite"),
        "entity_atm_offsite": ("infrastructure", "atm_offsite"),
        "entity_micro_atm": ("infrastructure", "micro_atms"),
        "entity_cc_outstanding": ("cards", "credit_cards"),
        "entity_dc_outstanding": ("cards", "debit_cards"),
        "entity_cc_pos_txn": ("spend_value", "cc_pos_txn_val"),
        "entity_cc_ecom_txn": ("spend_value", "cc_ecom_txn_val"),
        "entity_cc_other_txn": ("spend_value", "cc_other_txn_val"),
        "entity_dc_atm_txn": ("spend_value", "dc_atm_withdrawal_val"),
        "entity_dc_pos_txn": ("spend_value", "dc_pos_txn_val"),
        "entity_dc_ecom_txn": ("spend_value", "dc_ecom_txn_val"),
    },
}


def build_tree(model):
    """child_id -> parent_id and ancestor test from the skeleton composes_into edges."""
    parent_of = {e["from"]: e["to"] for e in model["edges"] if e["type"] == "composes_into"}
    decomp = {n["id"]: n.get("decomposition") for n in model["nodes"] if n.get("tier") == "entity"}
    pcode = {n["id"]: n.get("parent_code") for n in model["nodes"] if n.get("tier") == "entity"}

    def ancestors(nid):
        seen, cur = set(), nid
        while cur in parent_of:
            cur = parent_of[cur]
            if cur in seen:
                break
            seen.add(cur)
        return seen

    def in_chain(a, b):
        return b in ancestors(a) or a in ancestors(b)

    return parent_of, decomp, pcode, in_chain


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pipeline", required=True, choices=list(gs.PIPELINES))
    ap.add_argument("--draft", required=True)
    ap.add_argument("--map", required=True, choices=list(ENTITY_MAPS))
    args = ap.parse_args()

    cfg = gs.PIPELINES[args.pipeline]
    model = gs.load_json(cfg["model"])           # freshly generated skeleton
    draft = gs.load_json(Path(args.draft))
    emap = ENTITY_MAPS[args.map]

    skeleton_ids = {n["id"] for n in model["nodes"]}
    entity_ids = {n["id"] for n in model["nodes"] if n.get("tier") == "entity"}

    def remap(old_id):
        """Map a draft node id to its skeleton id. Entities are remapped via emap;
        force/risk/opp/gap ids pass through unchanged."""
        if old_id in emap:
            return gs.entity_id(*emap[old_id])
        return old_id

    # 1) carry forward non-entity behavioral nodes (forces, risks, opps, gaps)
    behavioral_nodes = []
    for n in draft["nodes"]:
        if n.get("tier") == "entity":
            continue
        n = dict(n)
        n.pop("subsystem_id", None)
        behavioral_nodes.append(n)
    behavioral_node_ids = {n["id"] for n in behavioral_nodes}

    parent_of, decomp, pcode, in_chain = build_tree(model)
    BEHAV_DISALLOW_IN_CHAIN = {"drives", "amplifies", "suppresses", "leads",
                               "reroutes_to", "substitutes"}

    # 2) transform edges
    edges, dropped, old_to_new_edge = [], [], {}
    for e in draft["edges"]:
        of, ot = e["from"], e["to"]
        nf, nt = remap(of), remap(ot)
        et = e["type"]
        both_entities = nf in entity_ids and nt in entity_ids
        # D1/D2: drop behavioral edge that duplicates a part-whole link
        if both_entities and et in BEHAV_DISALLOW_IN_CHAIN and in_chain(nf, nt):
            dropped.append((of, ot, et, "D1 part-whole duplication"))
            continue
        # validate endpoints resolve
        if nf not in skeleton_ids and nf not in behavioral_node_ids:
            dropped.append((of, ot, et, f"unresolved from {nf}"))
            continue
        if nt not in skeleton_ids and nt not in behavioral_node_ids:
            dropped.append((of, ot, et, f"unresolved to {nt}"))
            continue
        ne = dict(e)
        ne["from"], ne["to"] = nf, nt
        ne["id"] = f"{nf}__{et}__{nt}"
        # D3: cross-decomposition behavioral edge between two children of same parent
        if (both_entities and pcode.get(nf) == pcode.get(nt) and pcode.get(nf) is not None
                and decomp.get(nf) != decomp.get(nt)):
            ne["double_count_risk"] = True
            ne.setdefault("note", "Endpoints sit in different decompositions of the same parent; "
                                  "the same underlying credit may be counted in both.")
        edges.append(ne)
        old_to_new_edge[f"{of}→{ot}"] = ne["id"]

    # 3) transform loops — remap node + edge references, drop refs to dropped edges
    loops = []
    for lp in draft.get("loops", []):
        lp = dict(lp)
        lp["participating_nodes"] = [remap(x) for x in lp.get("participating_nodes", [])]
        new_edges, keep_nodes = [], set()
        for eref in lp.get("participating_edges", []):
            nid = old_to_new_edge.get(eref)
            if nid:
                new_edges.append(nid)
                e = next(x for x in edges if x["id"] == nid)
                keep_nodes.update([e["from"], e["to"]])
        lp["participating_edges"] = new_edges
        # keep only nodes still wired by a surviving edge, plus any non-entity node
        lp["participating_nodes"] = [n for n in lp["participating_nodes"]
                                     if n in keep_nodes or n in behavioral_node_ids]
        loops.append(lp)

    # 4) write back: skeleton entities + structural edges, then behavioral layer
    model["nodes"] = [n for n in model["nodes"] if n.get("tier") == "entity"] + behavioral_nodes
    model["edges"] = [e for e in model["edges"] if e["type"] in gs.STRUCTURAL_EDGE_TYPES] + edges
    model["loops"] = loops
    meta = model.setdefault("_meta", {})
    meta.update({
        "mode": "foundation",
        "last_foundation_date": "2026-06-11",
        "behavioral_source_draft": args.draft,
    })
    meta.pop("status", None)

    cfg["model"].write_text(json.dumps(model, indent=2, ensure_ascii=False))
    print(f"[{args.pipeline}] behavioral layer built:")
    print(f"  {len(behavioral_nodes)} behavioral nodes, {len(edges)} behavioral edges, {len(loops)} loops")
    print(f"  dropped {len(dropped)} edges:")
    for of, ot, et, why in dropped:
        print(f"    - {of} --{et}--> {ot}  ({why})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
