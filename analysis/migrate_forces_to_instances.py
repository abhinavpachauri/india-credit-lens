#!/usr/bin/env python3
"""
migrate_forces_to_instances.py — one-time v3.0 → v4.0 transform
---------------------------------------------------------------
Splits the v3.0 behavioral `force` nodes into:
  - S2a causal channels  → already authored in analysis/ontology/channels.json (shared hub),
  - S2b force instances  → a `force_instances[]` array in each pipeline's system_model.json.

Each force KEEPS its id and is relocated from `nodes[]` to `force_instances[]`, gaining
`instance_of` (channel id) + `scope_entities` (URNs of the entities its drives/suppresses/
amplifies edges point at). Because the id is unchanged, every existing edge and loop that
references it still resolves — no edge/loop rewrite needed. Schema bumps to 4.0.

Idempotent: re-running on an already-migrated (4.0) model is a no-op.

Usage:
    python3 analysis/migrate_forces_to_instances.py --pipeline sibc
    python3 analysis/migrate_forces_to_instances.py --pipeline atm_pos
"""
import argparse
import json
import sys

import generate_skeleton as gs

FORCE_TO_CHANNEL = {
    "sibc": {
        "force_gold_price_surge": "ch_collateral_price_secured",
        "force_rbi_unsecured_tightening": "ch_capital_weight_unsecured",
        "force_psl_limit_revision": "ch_psl_threshold_reclassification",
        "force_pli_manufacturing": "ch_industrial_capex_supplychain",
        "force_msme_formalisation": "ch_formalisation_underwritability",
        "force_nbfc_regulatory_recovery": "ch_wholesale_funding_intermediation",
        "force_msp_procurement_growth": "ch_procurement_policy_food",
        "force_infra_cycle_maturing": "ch_project_lifecycle_origination",
    },
    "atm_pos": {
        "force_upi_zero_mdr": "ch_zero_mdr_acceptance_mix",
        "force_rbi_paytm_action": "ch_institutional_exit_card_stock",
        "force_rbi_card_lifecycle_norms": "ch_card_lifecycle_norms",
        "force_ncmc_transit_rollout": "ch_embedded_payment_card_other",
    },
}

INSTANTIATION_EDGE_TYPES = {"drives", "suppresses", "amplifies"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pipeline", required=True, choices=list(gs.PIPELINES))
    args = ap.parse_args()

    cfg = gs.PIPELINES[args.pipeline]
    model = gs.load_json(cfg["model"])
    channels = {c["id"] for c in gs.load_json(gs.ANALYSIS / "ontology" / "channels.json")["channels"]}
    fmap = FORCE_TO_CHANNEL[args.pipeline]

    if model.get("_meta", {}).get("schema_version") == "4.0" and model.get("force_instances"):
        print(f"[{args.pipeline}] already v4.0 — {len(model['force_instances'])} instances, no-op")
        return 0

    urn_of = {n["id"]: n.get("urn") for n in model["nodes"] if n.get("tier") == "entity"}

    # scope_entities per force = entity targets of its instantiation edges
    scope = {}
    for e in model["edges"]:
        if e.get("type") in INSTANTIATION_EDGE_TYPES and e["from"] in fmap:
            tgt = urn_of.get(e["to"])
            if tgt:
                scope.setdefault(e["from"], []).append(tgt)

    force_instances, kept_nodes, missing = [], [], []
    for n in model["nodes"]:
        if n.get("tier") != "force":
            kept_nodes.append(n)
            continue
        ch = fmap.get(n["id"])
        if ch is None or ch not in channels:
            missing.append((n["id"], ch))
            kept_nodes.append(n)            # leave unmigrated rather than lose it
            continue
        inst = dict(n)
        inst["tier"] = "force_instance"
        inst["instance_of"] = ch
        inst["scope_entities"] = sorted(set(scope.get(n["id"], [])))
        # the durable mechanism + polarity now live on the channel; drop force_type duplication note
        force_instances.append(inst)

    model["nodes"] = kept_nodes
    model["force_instances"] = force_instances

    # annotate instantiation edges with their channel (mechanism text now lives on the channel)
    for e in model["edges"]:
        if e["from"] in fmap:
            e["channel"] = fmap[e["from"]]

    meta = model.setdefault("_meta", {})
    meta["schema_version"] = "4.0"
    meta["composition_spec_ref"] = "analysis/COMPOSITION_SPEC.md"

    cfg["model"].write_text(json.dumps(model, indent=2, ensure_ascii=False))
    print(f"[{args.pipeline}] migrated to v4.0: {len(force_instances)} force_instances "
          f"(channels in hub), {len(kept_nodes)} nodes remain")
    for fi in force_instances:
        print(f"    {fi['id']:32s} → {fi['instance_of']:34s} scope={len(fi['scope_entities'])} entities")
    if missing:
        print(f"  ⚠ unmapped forces (left as-is): {missing}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
