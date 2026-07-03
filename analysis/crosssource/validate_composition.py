#!/usr/bin/env python3
"""
validate_composition.py — cross-system composition validator (COMPOSITION_SPEC.md §10 + §20)
---------------------------------------------------------------------------------------------
Part I (v1.0, §10) — composition.json:
  - every cross-edge endpoint is a valid entity URN,
  - the two endpoints live in DIFFERENT pipelines (cross_source scope),
  - 'no monolith' — no pipeline system_model.json references another pipeline's URN
    (or an icl:eco/ construct URN) directly in its own edges.

Part II (v1.1, §20) — ecosystem_model.json + domains.json:
  - constructs: well-formed permanent icl:eco/ URNs; members resolve; members span ≥2
    pipelines; concept_anchor values in the concepts.json vocabulary; role enum,
  - eco_edges: endpoints resolve; ≥1 endpoint is a construct (entity↔entity links belong
    in composition.json or a pipeline model); sourcing required unless claim_type=structural,
  - loops: qualified refs resolve ({pipeline}:{edge_id} | x:{cross_edge} | eco:{eco_edge});
    ≥1 cross-pipeline element; corresponds_to cross-edges barred (structural, not causal),
  - constraints: every operand resolves to a registered signal of the declared pipeline;
    tolerance + severity well-formed,
  - domains: pure lenses — construct refs resolve, concept_scope in vocabulary.

Usage:  python3 analysis/crosssource/validate_composition.py
Exit:   0 = pass, 1 = error(s).
"""
import json
import sys
from pathlib import Path

# Bootstrap: <repo>/analysis on sys.path so `from core import …` resolves from any cwd now
# that this script lives under crosssource/. Move-safe via .git walk (see core/paths.py).
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core import generate_skeleton as gs  # noqa: E402

ROOT = gs.ROOT
CROSS = ROOT / "analysis" / "cross_source"

ROLE_ENUM       = {"measures", "proxies", "contra_indicates"}
ECO_TYPE_ENUM   = {"drives", "suppresses", "feeds", "constrains"}
POLARITY_ENUM   = {"+", "-", "~"}
CLAIM_ENUM      = {"structural", "inference", "hypothesis"}
LOOP_TYPE_ENUM  = {"reinforcing", "balancing"}
SEVERITY_ENUM   = {"warn", "fail"}
TOLERANCE_ENUM  = {"pct", "abs", "corridor"}


def load_indexes():
    """All the reference sets §20 checks resolve against."""
    urn_pipeline, edge_ids = {}, {}          # entity urn → pipeline; pipeline → {edge ids}
    models = {}
    for pipe, cfg in gs.PIPELINES.items():
        if not cfg["model"].exists():
            continue
        m = gs.load_json(cfg["model"])
        models[pipe] = m
        for n in m["nodes"]:
            if n.get("tier") == "entity" and n.get("urn"):
                urn_pipeline[n["urn"]] = pipe
        edge_ids[pipe] = {e.get("id", f"{e['from']}->{e['to']}") for e in m["edges"]}

    concepts = gs.load_json(gs.ANALYSIS / "ontology" / "concepts.json")["dimensions"]
    vocab = {
        "product": set(concepts["product"]["values"]),
        "measure": set(concepts["measure"].get("classes", [])),
        "segment": set(concepts.get("segment", {}).get("values", [])),
    }
    registry = gs.load_json(gs.ANALYSIS / "signals" / "registry.json")["signals"]
    return urn_pipeline, edge_ids, models, vocab, registry


def validate_cross_edges(comp, urn_pipeline):
    errors = []
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
    return errors


def validate_no_monolith(models):
    """A pipeline model must not reference foreign URNs — another pipeline's OR icl:eco/."""
    errors = []
    for pipe, model in models.items():
        own = {n["urn"] for n in model["nodes"] if n.get("tier") == "entity" and n.get("urn")}
        for ed in model["edges"]:
            for endp in ("from", "to"):
                v = ed.get(endp, "")
                if isinstance(v, str) and v.startswith("icl:") and v not in own:
                    errors.append(f"{pipe} edge {ed.get('id')} references foreign URN {v} "
                                  f"directly — cross-system links must go via composition.json")
    return errors


def validate_constructs(eco, urn_pipeline, vocab):
    errors, construct_urns = [], set()
    for c in eco.get("constructs", []):
        cid, urn = c.get("id", "?"), c.get("urn", "")
        if urn != f"icl:eco/{cid}":
            errors.append(f"construct {cid}: urn {urn!r} must be exactly 'icl:eco/{cid}'")
        if urn in construct_urns:
            errors.append(f"construct {cid}: duplicate URN {urn}")
        construct_urns.add(urn)
        pipes = set()
        for m in c.get("members", []):
            murn = m.get("urn")
            if murn not in urn_pipeline:
                errors.append(f"construct {cid}: member {murn!r} is not a known entity URN")
            else:
                pipes.add(urn_pipeline[murn])
            if m.get("role") not in ROLE_ENUM:
                errors.append(f"construct {cid}: member {murn} role {m.get('role')!r} not in {sorted(ROLE_ENUM)}")
        if len(pipes) < 2:
            errors.append(f"construct {cid}: members span only {sorted(pipes)} — a construct must span "
                          f"≥2 pipelines (a single-pipeline bundle belongs in that pipeline's model)")
        anchor = c.get("concept_anchor") or {}
        for dim, allowed in vocab.items():
            vals = anchor.get(dim)
            if vals is None:
                continue
            for v in (vals if isinstance(vals, list) else [vals]):
                if v not in allowed:
                    errors.append(f"construct {cid}: concept_anchor.{dim} {v!r} not in concepts.json vocabulary")
    return errors, construct_urns


def validate_eco_edges(eco, urn_pipeline, construct_urns):
    errors, eco_edge_ids = [], set()
    for e in eco.get("eco_edges", []):
        eid = e.get("id", "?")
        eco_edge_ids.add(eid)
        endpoints = [e.get("from"), e.get("to")]
        for v in endpoints:
            if v not in urn_pipeline and v not in construct_urns:
                errors.append(f"eco_edge {eid}: endpoint {v!r} resolves to neither an entity nor a construct URN")
        if not any(v in construct_urns for v in endpoints):
            errors.append(f"eco_edge {eid}: no construct endpoint — entity↔entity links belong in "
                          f"composition.json (cross-pipeline) or the pipeline model (intra)")
        if e.get("type") not in ECO_TYPE_ENUM:
            errors.append(f"eco_edge {eid}: type {e.get('type')!r} not in {sorted(ECO_TYPE_ENUM)}")
        if e.get("polarity") not in POLARITY_ENUM:
            errors.append(f"eco_edge {eid}: polarity {e.get('polarity')!r} not in {sorted(POLARITY_ENUM)}")
        claim = e.get("claim_type")
        if claim not in CLAIM_ENUM:
            errors.append(f"eco_edge {eid}: claim_type {claim!r} not in {sorted(CLAIM_ENUM)}")
        elif claim != "structural" and not (e.get("source") and e.get("source_url")):
            errors.append(f"eco_edge {eid}: claim_type '{claim}' requires source + source_url (v3.0 §13)")
        if not e.get("mechanism"):
            errors.append(f"eco_edge {eid}: mechanism prose is required")
    return errors, eco_edge_ids


def validate_loops(eco, edge_ids, comp, eco_edge_ids):
    errors = []
    xedges = {e["id"]: e for e in comp.get("cross_edges", [])}
    for lp in eco.get("loops", []):
        lid = lp.get("id", "?")
        if lp.get("type") not in LOOP_TYPE_ENUM:
            errors.append(f"loop {lid}: type {lp.get('type')!r} not in {sorted(LOOP_TYPE_ENUM)}")
        cross_element, intra_pipes = False, set()
        for ref in lp.get("member_edges", []):
            kind, _, rest = ref.partition(":")
            if kind == "x":
                cross_element = True
                xe = xedges.get(rest)
                if not xe:
                    errors.append(f"loop {lid}: x:{rest} not found in composition.json")
                elif xe.get("type") == "corresponds_to":
                    errors.append(f"loop {lid}: x:{rest} is corresponds_to — structural identities "
                                  f"are barred from causal loops (§16)")
            elif kind == "eco":
                cross_element = True
                if rest not in eco_edge_ids:
                    errors.append(f"loop {lid}: eco:{rest} not found in ecosystem_model.eco_edges")
            elif kind in edge_ids:
                intra_pipes.add(kind)
                if rest not in edge_ids[kind]:
                    errors.append(f"loop {lid}: {kind}:{rest} not found in {kind} model edges")
            else:
                errors.append(f"loop {lid}: unrecognised ref {ref!r} — expected "
                              f"{{pipeline}}:{{edge_id}} | x:{{id}} | eco:{{id}}")
        if not cross_element and len(intra_pipes) < 2:
            errors.append(f"loop {lid}: no cross-pipeline element — a single-pipeline loop "
                          f"belongs in that pipeline's model (§16)")
    return errors


def validate_constraints(eco, registry):
    errors = []
    for cx in eco.get("constraints", []):
        cid = cx.get("id", "?")
        for op in cx.get("operands", []):
            sid = op.get("signal_id")
            sig = registry.get(sid)
            if not sig:
                errors.append(f"constraint {cid}: operand signal {sid!r} not in registry.json")
            elif sig.get("pipeline") != op.get("pipeline"):
                errors.append(f"constraint {cid}: operand {sid} declares pipeline {op.get('pipeline')!r} "
                              f"but registry says {sig.get('pipeline')!r}")
        tol = cx.get("tolerance") or {}
        if tol.get("type") not in TOLERANCE_ENUM:
            errors.append(f"constraint {cid}: tolerance.type {tol.get('type')!r} not in {sorted(TOLERANCE_ENUM)}")
        elif tol.get("type") == "corridor" and (not isinstance(tol.get("value"), list) or len(tol["value"]) != 2):
            errors.append(f"constraint {cid}: corridor tolerance needs value=[lo, hi]")
        if cx.get("severity") not in SEVERITY_ENUM:
            errors.append(f"constraint {cid}: severity {cx.get('severity')!r} not in {sorted(SEVERITY_ENUM)}")
        if not cx.get("relation"):
            errors.append(f"constraint {cid}: relation (prose + formula) is required")
    return errors


def validate_domains(domains, vocab, construct_urns):
    errors = []
    for d in domains.get("domains", []):
        did = d.get("id", "?")
        for v in d.get("concept_scope", []):
            if v not in vocab["product"]:
                errors.append(f"domain {did}: concept_scope {v!r} not in product vocabulary")
        for urn in d.get("constructs", []):
            if urn not in construct_urns:
                errors.append(f"domain {did}: construct ref {urn!r} does not resolve")
        # a domain is a lens: any structural key present is a spec violation (§18)
        for forbidden in ("members", "edges", "loops", "eco_edges"):
            if forbidden in d:
                errors.append(f"domain {did}: carries '{forbidden}' — domains are lenses with ZERO structure")
    return errors


def main():
    urn_pipeline, edge_ids, models, vocab, registry = load_indexes()

    comp_path = CROSS / "composition.json"
    comp = gs.load_json(comp_path) if comp_path.exists() else {}
    eco_path = CROSS / "ecosystem_model.json"
    eco = gs.load_json(eco_path) if eco_path.exists() else {}
    dom_path = gs.ANALYSIS / "ontology" / "domains.json"
    domains = gs.load_json(dom_path) if dom_path.exists() else {}

    errors = []
    errors += validate_cross_edges(comp, urn_pipeline)
    errors += validate_no_monolith(models)
    construct_errors, construct_urns = validate_constructs(eco, urn_pipeline, vocab)
    errors += construct_errors
    eco_edge_errors, eco_edge_ids = validate_eco_edges(eco, urn_pipeline, construct_urns)
    errors += eco_edge_errors
    errors += validate_loops(eco, edge_ids, comp, eco_edge_ids)
    errors += validate_constraints(eco, registry)
    errors += validate_domains(domains, vocab, construct_urns)

    if errors:
        for e in errors:
            print(f"  ✗ {e}")
        print(f"\n✗ FAIL — {len(errors)} error(s)")
        return 1
    print(f"✓ PASS — {len(comp.get('cross_edges', []))} cross-edge(s), "
          f"{len(eco.get('constructs', []))} construct(s), {len(eco.get('eco_edges', []))} eco-edge(s), "
          f"{len(eco.get('loops', []))} loop(s), {len(eco.get('constraints', []))} constraint(s), "
          f"{len(domains.get('domains', []))} domain(s) — all references resolve; no monolith")
    return 0


if __name__ == "__main__":
    sys.exit(main())
