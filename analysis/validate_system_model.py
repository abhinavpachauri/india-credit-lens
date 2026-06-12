#!/usr/bin/env python3
"""
validate_system_model.py — India Credit Lens
---------------------------------------------
v3.0 system-model validator (SYSTEM_MODEL_SPEC.md §18). Replaces the legacy
validate.py checks 4/5 (v2.0 schema) and validate_claims.py (2c) in the eval
gate. Validates a single pipeline's merged/system_model.json against:

  STRUCTURAL  — code present; tree integrity; role consistency; additivity
                (tolerance-checked, residual reported as a note where the profile
                marks a decomposition non-exhaustive); alternate-decomposition
                independence; reclassification additive:false + basis; completeness
                (every source code is an entity).
  DISCIPLINE  — D1 (no behavioral edge duplicating a composes_into ancestor),
                D2 (no leads across a part-whole chain),
                D3 (cross-decomposition behavioral edges carry double_count_risk).
  BEHAVIORAL  — valid tiers/edge types/polarity/scope; entity claim_type:fact +
                signal_ids key; force signal_evidence + source fields (claim
                sourcing, built in here); risk/opp status; gap gap_type;
                hypothesis source_rationale; loop references resolve;
                schema_version 3.0; ≥1 force, ≥1 entity, ≥1 edge.

Usage:
    python3 analysis/validate_system_model.py --pipeline sibc
    python3 analysis/validate_system_model.py analysis/rbi_atm_pos/merged/system_model.json --pipeline atm_pos

Exit codes: 0 = pass (warnings allowed), 1 = error(s).
"""

import argparse
import sys
from pathlib import Path

# reuse the deterministic profile/CSV plumbing from the emitter
import generate_skeleton as gs  # noqa: E402  (same dir, run from analysis/ or repo root)

ROOT = gs.ROOT
ADDITIVITY_TOL_PCT = 0.5

BEHAVIORAL_EDGE_TYPES = {
    "drives", "suppresses", "amplifies", "reroutes_to", "substitutes", "leads",
    "contrasts_with", "creates_opportunity", "creates_risk", "creates_gap",
    "is_data_gap", "masks",
}
STRUCTURAL_EDGE_TYPES = gs.STRUCTURAL_EDGE_TYPES
VALID_TIERS = {"force", "entity", "risk", "opportunity", "gap"}
VALID_SCOPES = {"intra_group", "inter_group", "cross_source"}
FORCE_SOURCE_FIELDS = ["force_type", "non_observable_reason", "signal_evidence",
                       "source", "source_url", "source_verified_date",
                       "source_excerpt", "source_rationale", "status"]


class Result:
    def __init__(self):
        self.errors, self.warnings, self.notes = [], [], []

    def error(self, check, msg): self.errors.append(f"[{check}] {msg}")
    def warn(self, check, msg): self.warnings.append(f"[{check}] {msg}")
    def note(self, check, msg): self.notes.append(f"[{check}] {msg}")

    def report(self):
        for n in self.notes:
            print(f"  · {n}")
        for w in self.warnings:
            print(f"  ⚠ {w}")
        for e in self.errors:
            print(f"  ✗ {e}")
        ok = not self.errors
        print(f"\n{'✓ PASS' if ok else '✗ FAIL'} — "
              f"{len(self.errors)} error(s), {len(self.warnings)} warning(s), {len(self.notes)} note(s)")
        return ok


# ───────────────── CSV value loading (per profile) ─────────────────

def load_csv_values(profile):
    """Return {(partition, code): value} for the latest period, using the same
    period-selection + identity logic as generate_skeleton."""
    cols = profile["columns"]
    if profile["hierarchy_source"] == "csv":
        rows = gs.latest_rows_csv(profile)
        vocab = set(profile.get("truthy", ["True", "true", "1"]))
        vals, present = {}, set()
        for r in rows:
            code = r[cols["code"]].strip()
            if not code:
                continue
            key = (r[cols["partition"]], code)
            present.add(key)
            try:
                vals[key] = float(r[cols["value"]] or 0)
            except (ValueError, TypeError):
                pass
        return vals, present
    else:
        # profile hierarchy (ATM/POS): values keyed by ('metric', metric)
        import csv as _csv
        rows = list(_csv.DictReader(open(ROOT / profile["source_csv"])))
        for k, v in profile.get("csv_filter", {}).items():
            rows = [r for r in rows if r[k] == v]
        for col in profile.get("period_selection", {}).get("order_by", []):
            mx = max(r[col] for r in rows)
            rows = [r for r in rows if r[col] == mx]
        vals, present = {}, set()
        for r in rows:
            key = ("metric", r[cols["metric"]])
            present.add(key)
            try:
                vals[key] = float(r[cols["value"]] or 0)
            except (ValueError, TypeError):
                pass
        return vals, present


# ───────────────── structural checks ─────────────────

def check_structural(model, profile, result):
    entities = [n for n in model["nodes"] if n.get("tier") == "entity"]
    by_id = {n["id"]: n for n in entities}
    ekey = {(n.get("statement"), n.get("code")): n for n in entities}

    # code present
    for n in entities:
        if not n.get("code"):
            result.error("code", f"entity {n['id']} missing code")

    # tree integrity: every non-root parent_code resolves
    structural_children = {}  # parent_id -> [(child_node, decomposition)]
    for e in model["edges"]:
        if e["type"] == "composes_into":
            structural_children.setdefault(e["to"], []).append(e)
    for n in entities:
        if n.get("structural_role") == "root":
            if n.get("parent_code"):
                result.error("tree", f"root {n['id']} has parent_code {n['parent_code']}")
            continue
        if n.get("reclassification"):
            continue
        pc = n.get("parent_code")
        if pc is None:
            result.error("tree", f"non-root {n['id']} has null parent_code")
            continue
        # parent must exist (same partition, except SIBC parent_statement handled at emit time)
        cand = [m for m in entities if m.get("code") == pc]
        if not cand:
            result.error("tree", f"{n['id']} parent_code '{pc}' resolves to no entity")

    # role consistency
    has_child = {e["to"] for e in model["edges"] if e["type"] == "composes_into"}
    for n in entities:
        if n.get("reclassification"):
            continue
        role = n.get("structural_role")
        if role == "aggregate" and n["id"] not in has_child:
            result.error("role", f"aggregate {n['id']} has no composes_into children")
        if role == "leaf" and n["id"] in has_child:
            result.error("role", f"leaf {n['id']} has composes_into children")

    # reclassification edges
    for e in model["edges"]:
        if e["type"] == "reclassifies":
            src = by_id.get(e["from"])
            if src and src.get("additive") is not False:
                result.error("reclass", f"reclassifies source {e['from']} must be additive:false")
            if not e.get("basis"):
                result.error("reclass", f"reclassifies edge {e['id']} missing basis")

    # additivity (tolerance) + alternate-decomposition independence
    vals, present = load_csv_values(profile)
    _check_additivity(model, profile, entities, ekey, structural_children, vals, result)

    # completeness: every source code is an entity
    _check_completeness(profile, present, ekey, result)


def _val_for(node, vals):
    """CSV value for an entity (SIBC keyed by (statement,code); ATM/POS leaves by metric)."""
    k = (node.get("statement"), node.get("code"))
    if k in vals:
        return vals[k]
    m = node.get("metric")
    if m and ("metric", m) in vals:
        return vals[("metric", m)]
    return None


def _check_additivity(model, profile, entities, ekey, structural_children, vals, result):
    by_id = {n["id"]: n for n in entities}
    # build non-exhaustive set keyed by (partition, code)
    non_exh = {}
    for ne in profile.get("exhaustive_decompositions", {}).get("non_exhaustive", []):
        non_exh[(ne["partition"], ne["code"])] = ne.get("expected_residual_pct")

    for parent in entities:
        edges = structural_children.get(parent["id"], [])
        if not edges:
            continue
        if parent.get("aggregation") == "grouping":
            result.note("additivity", f"{parent['code']} is a grouping container — additivity not checked")
            continue
        pv = _val_for(parent, vals)
        if pv is None or pv == 0:
            continue  # no independent parent value (e.g. ATM/POS computed aggregate)
        # group children by decomposition
        by_decomp = {}
        for e in edges:
            child = by_id.get(e["from"])
            by_decomp.setdefault(e.get("decomposition", "primary"), []).append(child)
        for decomp, kids in by_decomp.items():
            csum = sum((_val_for(k, vals) or 0) for k in kids)
            resid_pct = (pv - csum) / pv * 100
            key = (parent.get("statement"), parent.get("code"))
            if abs(resid_pct) <= ADDITIVITY_TOL_PCT:
                continue
            if key in non_exh:
                result.note("additivity",
                            f"{parent['code']} [{decomp}] residual {resid_pct:+.2f}% "
                            f"(expected non-exhaustive ~{non_exh[key]}%)")
            else:
                result.warn("additivity",
                            f"{parent['code']} [{decomp}] children sum off by {resid_pct:+.2f}% "
                            f"(parent={pv:.0f}, children={csum:.0f})")


def _check_completeness(profile, present, ekey, result):
    if profile["hierarchy_source"] == "csv":
        cols = profile["columns"]
        missing = [k for k in present if k not in ekey]
        if missing:
            result.error("completeness", f"{len(missing)} source codes have no entity: {missing[:10]}")
        else:
            result.note("completeness", f"all {len(present)} source codes mapped to entities")
    else:
        # every CSV total metric must map to a leaf carrying that metric
        entity_metrics = {n.get("metric") for n in ekey.values() if n.get("metric")}
        missing = [k[1] for k in present if k[1] not in entity_metrics]
        if missing:
            result.error("completeness", f"CSV metrics with no entity: {missing}")
        else:
            result.note("completeness", f"all {len(present)} CSV metrics mapped to leaves")


# ───────────────── discipline checks (D1/D2/D3) ─────────────────

def _ancestors(node_id, parent_edge_map):
    seen, cur = set(), node_id
    while cur in parent_edge_map:
        cur = parent_edge_map[cur]
        if cur in seen:
            break
        seen.add(cur)
    return seen


def check_discipline(model, result):
    entities = {n["id"]: n for n in model["nodes"] if n.get("tier") == "entity"}
    # child_id -> parent_id via composes_into
    parent_of = {e["from"]: e["to"] for e in model["edges"] if e["type"] == "composes_into"}

    def in_chain(a, b):
        """True if a is an ancestor or descendant of b in the composes_into tree."""
        return b in _ancestors(a, parent_of) or a in _ancestors(b, parent_of)

    for e in model["edges"]:
        if e["type"] not in BEHAVIORAL_EDGE_TYPES:
            continue
        f, t = e.get("from"), e.get("to")
        if f not in entities or t not in entities:
            continue  # edges touching force/risk/opp/gap are out of D1/D2 scope
        # D1 — no behavioral edge duplicating a composes_into ancestor link
        if in_chain(f, t):
            if e["type"] in {"drives", "amplifies", "suppresses", "leads", "reroutes_to", "substitutes"}:
                result.error("D1", f"behavioral edge {e['id']} ({e['type']}) duplicates a "
                                    f"part-whole link between {f} and {t}")
        # D2 — no leads across a composition boundary
        if e["type"] == "leads" and in_chain(f, t):
            result.error("D2", f"leads edge {e['id']} runs across a part-whole chain ({f}->{t})")
        # D3 — cross-decomposition behavioral edges must carry double_count_risk
        nf, nt = entities[f], entities[t]
        if (nf.get("parent_code") == nt.get("parent_code")
                and nf.get("decomposition") != nt.get("decomposition")
                and nf.get("parent_code") is not None):
            if not e.get("double_count_risk"):
                result.error("D3", f"cross-decomposition edge {e['id']} ({f}/{nf.get('decomposition')} "
                                   f"<-> {t}/{nt.get('decomposition')}) missing double_count_risk:true")


# ───────────────── behavioral-layer checks ─────────────────

def check_behavioral(model, result):
    meta = model.get("_meta", {})
    if meta.get("schema_version") != "4.0":
        result.error("schema", f"schema_version must be '4.0', got {meta.get('schema_version')!r}")

    nodes = model["nodes"]
    instances = model.get("force_instances", [])
    ids = {n["id"] for n in nodes} | {fi["id"] for fi in instances}
    tiers = {}
    for n in nodes:
        t = n.get("tier")
        tiers[t] = tiers.get(t, 0) + 1
        if t not in VALID_TIERS:
            result.error("tier", f"node {n.get('id')} has invalid tier {t!r}")
        if t == "entity":
            if n.get("claim_type") != "fact":
                result.error("entity", f"entity {n['id']} claim_type must be 'fact'")
            if "signal_ids" not in n:
                result.error("entity", f"entity {n['id']} missing signal_ids key")
        elif t in ("risk", "opportunity"):
            if not n.get("status"):
                result.error(t, f"{t} {n['id']} missing status")
        elif t == "gap":
            if not n.get("gap_type"):
                result.error("gap", f"gap {n['id']} missing gap_type")

    # S2b force instances — sourcing (v3.0 §13) still applies; plus instance_of
    for fi in instances:
        for fld in FORCE_SOURCE_FIELDS:
            if fld not in fi:
                result.error("instance", f"force_instance {fi['id']} missing required field '{fld}'")
        if fi.get("claim_type") == "hypothesis" and not fi.get("source_rationale"):
            result.error("instance", f"hypothesis instance {fi['id']} missing source_rationale")
        if not fi.get("signal_evidence"):
            result.warn("instance", f"force_instance {fi['id']} has empty signal_evidence")

    if tiers.get("entity", 0) < 1:
        result.error("count", "model must have ≥1 entity node")
    if len(instances) < 1:
        result.error("count", "model must have ≥1 force_instance")

    # edges
    n_behav = 0
    for e in model["edges"]:
        et = e.get("type")
        if et in STRUCTURAL_EDGE_TYPES:
            if e.get("polarity") != "structural":
                result.error("edge", f"structural edge {e.get('id')} must have polarity:structural")
            continue
        if et not in BEHAVIORAL_EDGE_TYPES:
            result.error("edge", f"edge {e.get('id')} has unknown type {et!r}")
            continue
        n_behav += 1
        if "polarity" not in e:
            result.error("edge", f"behavioral edge {e.get('id')} missing polarity")
        if e.get("scope") not in VALID_SCOPES:
            result.error("edge", f"behavioral edge {e.get('id')} invalid scope {e.get('scope')!r}")
        for endp in ("from", "to"):
            if e.get(endp) and e[endp] not in ids:
                result.error("edge", f"edge {e.get('id')} {endp} '{e[endp]}' references unknown node")
        if et == "leads" and e.get("scope") == "intra_group":
            result.error("edge", f"leads edge {e['id']} may not be intra_group")
        if et == "substitutes" and e.get("scope") != "intra_group":
            result.error("edge", f"substitutes edge {e['id']} must be intra_group")
    if len(model["edges"]) < 1:
        result.error("count", "model must have ≥1 edge")

    # loops
    for lp in model.get("loops", []):
        for nid in lp.get("participating_nodes", []):
            if nid not in ids:
                result.error("loop", f"loop {lp.get('id')} references unknown node {nid}")
        edge_ids = {e.get("id") for e in model["edges"]}
        for eid in lp.get("participating_edges", []):
            if eid not in edge_ids:
                result.error("loop", f"loop {lp.get('id')} references unknown edge {eid}")

    result.note("summary", f"tiers={tiers}, force_instances={len(instances)}, "
                           f"behavioral_edges={n_behav}, loops={len(model.get('loops', []))}")


# ───────────────── composition checks (v4.0) ─────────────────

def check_composition(model, profile, pipeline, result):
    """COMPOSITION_SPEC.md §10: URN integrity, concept_tags, channel/instance references."""
    concepts = gs.load_json(ROOT / "analysis/ontology/concepts.json")
    channels = gs.load_json(ROOT / "analysis/ontology/channels.json")
    channel_ids = {c["id"] for c in channels["channels"]}
    vocab = {dim: set(spec.get("values", [])) for dim, spec in concepts["dimensions"].items()}

    entities = [n for n in model["nodes"] if n.get("tier") == "entity"]
    by_urn = {}
    for n in entities:
        urn = n.get("urn")
        if not urn:
            result.error("urn", f"entity {n['id']} missing urn")
            continue
        if not urn.startswith(f"icl:{pipeline}/"):
            result.error("urn", f"entity {n['id']} urn {urn!r} not namespaced to pipeline")
        if urn in by_urn:
            result.error("urn", f"duplicate urn {urn}")
        by_urn[urn] = n

    # concept_tags: product+measure required on leaves (containers/aggregates exempt); values in vocab
    for n in entities:
        tags = n.get("concept_tags") or {}
        is_leaf = n.get("structural_role") == "leaf"
        for req in ("product", "measure"):
            if is_leaf and not tags.get(req):
                result.warn("concept_tags", f"leaf {n['code']} missing {req} (tagging gap)")
        for dim, val in tags.items():
            if val is not None and dim in vocab and vocab[dim] and val not in vocab[dim]:
                result.error("concept_tags", f"{n['code']} {dim}={val!r} not in concepts vocabulary")

    # force instances: instance_of resolves; scope_entities are valid URNs
    for fi in model.get("force_instances", []):
        ch = fi.get("instance_of")
        if ch not in channel_ids:
            result.error("instance", f"force_instance {fi['id']} instance_of {ch!r} is not a known channel")
        for urn in fi.get("scope_entities", []):
            if urn not in by_urn:
                result.error("instance", f"force_instance {fi['id']} scope_entity {urn} is not an entity urn")

    # edges carrying a channel ref must resolve
    for e in model["edges"]:
        if e.get("channel") and e["channel"] not in channel_ids:
            result.error("channel", f"edge {e.get('id')} channel {e['channel']!r} is not a known channel")

    tagged = sum(1 for n in entities if (n.get("concept_tags") or {}).get("product"))
    result.note("composition", f"{len(entities)} entities, {tagged} product-tagged, "
                              f"{len(model.get('force_instances', []))} instances over "
                              f"{len({fi.get('instance_of') for fi in model.get('force_instances', [])})} channels")


# ───────────────── main ─────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model_path", nargs="?", default=None)
    ap.add_argument("--pipeline", required=True, choices=list(gs.PIPELINES))
    args = ap.parse_args()

    cfg = gs.PIPELINES[args.pipeline]
    model_path = Path(args.model_path) if args.model_path else cfg["model"]
    if not model_path.exists():
        print(f"✗ model not found: {model_path}")
        return 1
    model = gs.load_json(model_path)
    profile = gs.load_json(cfg["profile"])

    print(f"Validating {model_path.relative_to(ROOT)} (pipeline={args.pipeline}, v4.0)")
    result = Result()
    check_structural(model, profile, result)
    check_discipline(model, result)
    check_behavioral(model, result)
    check_composition(model, profile, args.pipeline, result)
    ok = result.report()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
