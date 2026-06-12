#!/usr/bin/env python3
"""
validate_composition.py — cross-system composition validator (COMPOSITION_SPEC.md §10)
--------------------------------------------------------------------------------------
Validates analysis/cross_source/composition.json against the federated pipeline models:
  - every cross-edge endpoint is a valid entity URN,
  - the two endpoints live in DIFFERENT pipelines (cross_source scope),
  - 'no monolith' — no pipeline system_model.json references another pipeline's URN
    directly in its own edges (cross-system links must go through composition.json).

Usage:  python3 analysis/validate_composition.py
Exit:   0 = pass, 1 = error(s).
"""
import json
import sys

import generate_skeleton as gs

ROOT = gs.ROOT


def main():
    # global URN → pipeline index
    urn_pipeline = {}
    for pipe, cfg in gs.PIPELINES.items():
        if not cfg["model"].exists():
            continue
        for n in gs.load_json(cfg["model"])["nodes"]:
            if n.get("tier") == "entity" and n.get("urn"):
                urn_pipeline[n["urn"]] = pipe

    errors = []
    comp_path = ROOT / "analysis/cross_source/composition.json"
    if not comp_path.exists():
        print("no composition.json yet — nothing to validate")
        return 0
    comp = gs.load_json(comp_path)

    for e in comp.get("cross_edges", []):
        for endp in ("from", "to"):
            if e.get(endp) not in urn_pipeline:
                errors.append(f"cross-edge {e.get('id')} {endp} {e.get(endp)!r} is not a known entity URN")
        if e.get("from") in urn_pipeline and e.get("to") in urn_pipeline:
            if urn_pipeline[e["from"]] == urn_pipeline[e["to"]]:
                errors.append(f"cross-edge {e['id']} connects two entities in the SAME pipeline "
                              f"({urn_pipeline[e['from']]}) — not a cross-system link")
        if e.get("scope") != "cross_source":
            errors.append(f"cross-edge {e.get('id')} must have scope 'cross_source'")

    # 'no monolith' — a pipeline model must not reference foreign URNs in its own edges
    for pipe, cfg in gs.PIPELINES.items():
        if not cfg["model"].exists():
            continue
        model = gs.load_json(cfg["model"])
        own = {n["urn"] for n in model["nodes"] if n.get("tier") == "entity" and n.get("urn")}
        for ed in model["edges"]:
            for endp in ("from", "to"):
                v = ed.get(endp, "")
                if isinstance(v, str) and v.startswith("icl:") and v not in own:
                    errors.append(f"{pipe} edge {ed.get('id')} references foreign URN {v} "
                                  f"directly — cross-system links must go via composition.json")

    n = len(comp.get("cross_edges", []))
    if errors:
        for e in errors:
            print(f"  ✗ {e}")
        print(f"\n✗ FAIL — {len(errors)} error(s)")
        return 1
    print(f"✓ PASS — {n} confirmed cross-edge(s), all endpoints resolve across distinct pipelines; "
          f"no monolith references")
    return 0


if __name__ == "__main__":
    sys.exit(main())
