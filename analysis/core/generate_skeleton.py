#!/usr/bin/env python3
"""
generate_skeleton.py — India Credit Lens
-----------------------------------------
Deterministic structural-skeleton emitter for a pipeline's Layer 2a system model
(SYSTEM_MODEL_SPEC.md v3.0 §6). Reads the pipeline's consolidated CSV + its
skeleton_profile.json and emits the entity nodes plus the structural edges
(composes_into, reclassifies). No forces, no behavioral edges, no judgment — the
only authored inputs come from the profile (reclassification target map and, for
SIBC, the II/III->I parent overrides).

Two hierarchy sources (declared by the profile):
  - csv     : parent links are carried in CSV columns (SIBC).
  - profile : parent links are authored in the profile `nodes` list (ATM/POS,
              whose CSV is long-format with no parent column).

MERGE SEMANTICS (the scalability contract):
  The skeleton is the source of truth for tier:'entity' nodes and the two
  structural edge types ONLY. Every authored behavioral artifact in an existing
  system_model.json — force/risk/opportunity/gap nodes, behavioral edges, loops —
  is PRESERVED verbatim. Each ingestion regenerates the skeleton in place; new
  codes/metrics appear as a printed new-entity diff; authored content is never
  clobbered. Run with --check to fail (non-zero) if the on-disk model is stale
  relative to a fresh skeleton (for the eval gate).

Usage:
    python3 analysis/generate_skeleton.py --pipeline sibc
    python3 analysis/generate_skeleton.py --pipeline atm_pos
    python3 analysis/generate_skeleton.py --pipeline sibc --check       # no write; exit 1 if stale
    python3 analysis/generate_skeleton.py --pipeline sibc --skeleton-only --out /tmp/sk.json

Exit codes:
    0 = written (or --check passed)
    1 = error, or --check found drift
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import sys
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core.paths import ROOT
ANALYSIS = ROOT / "analysis"

PIPELINES = {
    "sibc": {
        "profile": ANALYSIS / "rbi_sibc" / "skeleton_profile.json",
        "model": ANALYSIS / "rbi_sibc" / "merged" / "system_model.json",
        "report_id": "rbi_sibc",
        "report_name": "RBI Sector/Industry-wise Bank Credit — System Model",
    },
    "atm_pos": {
        "profile": ANALYSIS / "rbi_atm_pos" / "skeleton_profile.json",
        "model": ANALYSIS / "rbi_atm_pos" / "merged" / "system_model.json",
        "report_id": "rbi_atm_pos",
        "report_name": "RBI ATM/POS & Card Statistics — System Model",
    },
}

STRUCTURAL_EDGE_TYPES = {"composes_into", "reclassifies"}


# ───────────────────────── helpers ─────────────────────────

def load_json(path):
    with open(path) as f:
        return json.load(f)


def truthy(val, vocab):
    return str(val).strip() in vocab


def entity_id(partition, code):
    """Deterministic, stable entity id. Slug keeps codes readable + collision-free
    across partitions (the identity key is (partition, code)). Case is PRESERVED:
    SIBC reuses roman codes in two cases — root 'I/II/III' vs PSL lens 'i/ii/iii' —
    which must not collapse together, so do not lowercase the code."""
    p = str(partition).replace("Statement ", "S").replace(" ", "")
    c = str(code).replace(".", "_")
    return f"e_{p}_{c}" if p else f"e_{c}"


# ──────────────────── signal attachment (shared) ────────────────────

def build_signal_index(pipeline, registry_path):
    """Return helpers that resolve which entity keys a registry L1 signal touches.
    Both pipelines key off compute.* fields; the variants below cover every L1
    compute method present in registry.json."""
    reg = load_json(ANALYSIS.parent / registry_path) if not Path(registry_path).is_absolute() \
        else load_json(registry_path)
    signals = list(reg["signals"].values()) if isinstance(reg["signals"], dict) else reg["signals"]
    l1 = [s for s in signals if s.get("pipeline") == pipeline and s.get("layer") == 1]

    # entity_key -> set(signal_id), and entity_key -> [domains] (for registry_domain)
    by_key = defaultdict(set)
    domains = defaultdict(list)
    for s in l1:
        c = s.get("compute") or {}
        for key in resolve_signal_keys(pipeline, c):
            by_key[key].add(s["id"])
            if s.get("domain"):
                domains[key].append(s["domain"])
    return by_key, domains


def derive_registry_domain(domains):
    """Most-common signal domain for an entity, or None when no signals / ambiguous tie."""
    if not domains:
        return None
    from collections import Counter
    ranked = Counter(domains).most_common()
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return ranked[0][0]  # deterministic: Counter preserves insertion order on ties
    return ranked[0][0]


def resolve_signal_keys(pipeline, compute):
    """Map a single signal's compute spec to a list of entity identity keys.
    SIBC keys are (statement, code); ATM/POS keys are ('metric', metric)."""
    keys = []
    if pipeline == "atm_pos":
        m = compute.get("metric")
        if m:
            keys.append(("metric", m))
        return keys

    # SIBC variants
    stmt = compute.get("statement")
    if "code" in compute:                      # direct (yoy/share/abs/fy/streak)
        keys.append((stmt, compute["code"]))
    if "parent_code" in compute:               # scan -> attach to the family parent
        keys.append((compute.get("statement"), compute["parent_code"]))
    for k in ("code_a", "code_b"):             # spread
        if k in compute:
            keys.append((stmt, compute[k]))
    if "child_codes" in compute:               # count-positive
        for cc in compute["child_codes"]:
            keys.append((stmt, cc))
    if compute.get("method") == "csv_psl_scan_yoy":  # PSL lens scan -> all reclass entities
        keys.append(("__psl_lens__", None))
    return keys


# ──────────────────── skeleton emission: CSV hierarchy (SIBC) ────────────────────

def latest_rows_csv(profile):
    cols = profile["columns"]
    csv_path = ROOT / profile["source_csv"]
    rows = list(csv.DictReader(open(csv_path)))
    order = profile.get("period_selection", {}).get("order_by", [])
    # progressively filter to the max of each ordering column
    for col in order:
        mx = max(r[col] for r in rows)
        rows = [r for r in rows if r[col] == mx]
    return rows


def emit_skeleton_csv(profile, signal_index, domain_index):
    cols = profile["columns"]
    vocab = set(profile.get("truthy", ["True", "true", "1"]))
    rows = latest_rows_csv(profile)

    # filter artifact rows
    if profile.get("artifact_skip", {}).get("empty_code"):
        rows = [r for r in rows if r[cols["code"]].strip()]

    # index raw rows by (partition, code)
    raw = {}
    for r in rows:
        key = (r[cols["partition"]], r[cols["code"]])
        raw[key] = r

    # apply authored parent overrides (e.g. SIBC II,III -> I)
    overrides = {}
    for ov in profile.get("parent_overrides", []):
        overrides[(ov["partition"], ov["code"])] = ov

    def parent_of(key):
        if key in overrides:
            ov = overrides[key]
            return (ov["parent_partition"], ov["parent_code"]), ov.get("decomposition")
        r = raw[key]
        pc = r.get(cols["parent_code"], "").strip()
        if not pc:
            return None, None
        pp = r.get(cols["parent_partition"], "").strip() or r[cols["partition"]]
        return (pp, pc), None

    reclass_map = profile.get("reclass_target_map", {}).get("entries", {})
    labels = profile.get("decomposition", {}).get("labels", {})
    decomp_default = profile.get("decomposition", {}).get("default", "primary")

    # determine children grouping to detect alternate decompositions
    children = defaultdict(list)   # parent_key -> [child_key]
    reclass_keys = []
    for key, r in raw.items():
        if truthy(r[cols["reclass_flag"]], vocab):
            reclass_keys.append(key)
            continue
        pkey, _ = parent_of(key)
        if pkey is not None:
            children[pkey].append(key)

    # parent -> set of partitions among its children (>1 => alternate decompositions)
    parent_partitions = {pk: {ck[0] for ck in cks} for pk, cks in children.items()}

    nodes, edges = [], []

    # --- entity nodes (primary tree) ---
    for key in sorted(raw, key=lambda k: (k[0], _level(raw[k], cols), _codesort(k[1]))):
        partition, code = key
        r = raw[key]
        if truthy(r[cols["reclass_flag"]], vocab):
            continue  # reclass handled below
        pkey, ov_decomp = parent_of(key)
        kids = children.get(key, [])
        role = "root" if pkey is None else ("aggregate" if kids else "leaf")
        # decomposition tag
        if pkey is not None and len(parent_partitions.get(pkey, set())) > 1:
            decomposition = labels.get(partition, partition)
        else:
            decomposition = ov_decomp or decomp_default
        sids = sorted(signal_index.get((partition, code), set()))
        nodes.append(_entity_node(
            eid=entity_id(partition, code), label=r[cols["label"]].strip(),
            code=code, statement=partition, role=role, level=int(_level(r, cols)),
            decomposition=decomposition,
            parent_code=(pkey[1] if pkey else None),
            parent_statement=(pkey[0] if pkey else None),
            additive=True, signal_ids=sids,
            registry_domain=derive_registry_domain(domain_index.get((partition, code), [])),
        ))
        if pkey is not None:
            edges.append(_edge(entity_id(partition, code), entity_id(*pkey),
                               "composes_into", decomposition=decomposition))

    # --- reclassification lens entities ---
    psl_lens_ids = []
    for key in sorted(reclass_keys, key=lambda k: (k[0], _codesort(k[1]))):
        partition, code = key
        r = raw[key]
        ent = reclass_map.get(code, {})
        target = ent.get("target")
        sids = sorted(signal_index.get((partition, code), set()) | signal_index.get(("__psl_lens__", None), set()))
        psl_lens_ids.append(entity_id(partition, code))
        nodes.append(_entity_node(
            eid=entity_id(partition, code), label=r[cols["label"]].strip(),
            code=code, statement=partition, role="leaf", level=int(_level(r, cols)),
            decomposition="reclassification", parent_code=None,
            additive=False, signal_ids=sids, reclass=True,
            registry_domain=derive_registry_domain(domain_index.get((partition, code), [])),
        ))
        if target:
            edges.append(_edge(
                entity_id(partition, code), entity_id(target["partition"], target["code"]),
                "reclassifies", basis=ent.get("basis", ""), additive=False))
        else:
            # PSL-native: reclassifies -> null (recorded as basis-only, no edge target)
            edges.append(_edge(
                entity_id(partition, code), None, "reclassifies",
                basis=ent.get("basis", ""), additive=False))

    return nodes, edges


def _level(r, cols):
    try:
        return int(r[cols["level"]])
    except (KeyError, ValueError, TypeError):
        return 0


def _partition_slug(s):
    return str(s).replace(" ", "")


def resolve_concept_tags(profile, key, parent_of_key):
    """Resolve an entity's 5-dimension concept_tags (COMPOSITION_SPEC.md §4) from the
    profile's `concept` block: defaults → partition defaults → per-(statement,code) tag →
    ancestor inheritance for the declared inheritable fields (product/segment)."""
    conc = profile.get("concept", {})
    if not conc:
        return None
    out = dict(conc.get("defaults", {}))
    out.update(conc.get("defaults_by_partition", {}).get(key[0], {}))
    tags = conc.get("tags", {})
    tagkey = lambda k: f"{k[0]}::{k[1]}"
    out.update(tags.get(tagkey(key), {}))
    inherit = conc.get("inherit_from_ancestor", ["product", "segment"])
    cur, seen = key, set()
    while any(out.get(f) is None for f in inherit) and cur in parent_of_key and cur not in seen:
        seen.add(cur)
        cur = parent_of_key[cur]
        ptag = tags.get(tagkey(cur), {})
        for f in inherit:
            if out.get(f) is None and ptag.get(f) is not None:
                out[f] = ptag[f]
    for f in inherit:
        out.setdefault(f, None)
    return out


def apply_urn_and_concepts(nodes, pipeline, profile):
    """Post-pass: stamp every entity with its global URN and resolved concept_tags."""
    parent_of_key = {}
    for n in nodes:
        if n.get("parent_code"):
            parent_of_key[(n["statement"], n["code"])] = (
                n.get("parent_statement") or n["statement"], n["parent_code"])
    for n in nodes:
        n["urn"] = f"icl:{pipeline}/{_partition_slug(n['statement'])}/{n['code']}"
        tags = resolve_concept_tags(profile, (n["statement"], n["code"]), parent_of_key)
        if tags is not None:
            n["concept_tags"] = tags


def _codesort(code):
    """Sort codes like 2, 2.1, 2.10, 2.2 in human order; roman/letters fall back to string."""
    parts = []
    for seg in str(code).split("."):
        parts.append((0, int(seg)) if seg.isdigit() else (1, seg))
    return parts


# ──────────────────── skeleton emission: profile hierarchy (ATM/POS) ────────────────────

def emit_skeleton_profile(profile, signal_index, domain_index):
    cols = profile["columns"]
    # CSV totals -> metric availability (for leaf verification + new-metric diff)
    csv_path = ROOT / profile["source_csv"]
    rows = list(csv.DictReader(open(csv_path)))
    flt = profile.get("csv_filter", {})
    for k, v in flt.items():
        rows = [r for r in rows if r[k] == v]
    order = profile.get("period_selection", {}).get("order_by", [])
    for col in order:
        mx = max(r[col] for r in rows)
        rows = [r for r in rows if r[col] == mx]
    csv_metrics = {r[cols["metric"]] for r in rows}

    decl = profile["nodes"]
    decl_by_code = {n["code"]: n for n in decl}
    childset = defaultdict(list)
    for n in decl:
        if n["parent_code"]:
            childset[n["parent_code"]].append(n["code"])

    nodes, edges = [], []
    covered_metrics = set()
    for n in sorted(decl, key=lambda x: (x["partition"], x["level"], x["code"])):
        code = n["code"]
        pc = n["parent_code"]
        kids = childset.get(code, [])
        role = "root" if pc is None else ("aggregate" if kids else "leaf")
        metric = n.get("metric")
        sids = sorted(signal_index.get(("metric", metric), set())) if metric else []
        if metric:
            covered_metrics.add(metric)
        # additive: a node contributes to its parent unless the parent is a grouping container
        parent_agg = decl_by_code.get(pc, {}).get("aggregation") if pc else None
        additive = parent_agg != "grouping"
        node = _entity_node(
            eid=entity_id(n["partition"], code), label=n["label"], code=code,
            statement=n["partition"], role=role, level=n["level"],
            decomposition="primary", parent_code=pc,
            parent_statement=(n["partition"] if pc else None),
            additive=additive, signal_ids=sids,
            registry_domain=derive_registry_domain(
                domain_index.get(("metric", metric), []) if metric else []),
        )
        node["aggregation"] = n.get("aggregation", "leaf" if role == "leaf" else "sum")
        node["unit"] = n.get("unit")
        node["metric"] = metric
        nodes.append(node)
        if pc is not None:
            edges.append(_edge(entity_id(n["partition"], code), entity_id(n["partition"], pc),
                               "composes_into", decomposition="primary"))

    # new-metric diff: CSV total metrics not covered by any declared node
    new_metrics = sorted(csv_metrics - covered_metrics)
    return nodes, edges, new_metrics


# ──────────────────── node/edge builders ────────────────────

def _entity_node(eid, label, code, statement, role, level, decomposition,
                 parent_code, additive, signal_ids, reclass=False, registry_domain=None,
                 parent_statement=None):
    node = {
        "id": eid,
        "tier": "entity",
        "label": label,
        "claim_type": "fact",
        "code": code,
        "statement": statement,
        "structural_role": role,
        "level": level,
        "decomposition": decomposition,
        "parent_code": parent_code,
        "parent_statement": parent_statement,
        "additive": additive,
        "registry_domain": registry_domain,
        "data_section": None,
        "data_series": None,
        "signal_ids": signal_ids,
        "annotation_ids": [],
        "description": f"{label} — structural node ({statement} {code}).",
    }
    if reclass:
        node["reclassification"] = True
    return node


def _edge(src, dst, etype, decomposition=None, basis=None, additive=None):
    e = {
        "id": f"{etype}__{src}__{dst or 'null'}",
        "type": etype,
        "from": src,
        "to": dst,
        "polarity": "structural",
        "scope": "intra_group",
    }
    if decomposition is not None:
        e["decomposition"] = decomposition
    if basis is not None:
        e["basis"] = basis
    if additive is not None:
        e["additive"] = additive
    return e


# ──────────────────── merge + write ────────────────────

def merge_model(pipeline, cfg, profile, nodes, edges, new_entities):
    model_path = cfg["model"]
    existing = load_json(model_path) if model_path.exists() else {}

    # Preserve behavioral content from any v3.x/v4.x model. A pre-existing v2.0
    # model (or none) is treated as empty: its behavioral nodes reference the old
    # entity-id scheme and are superseded by the re-anchored behavioral layer.
    if existing.get("_meta", {}).get("schema_version") not in ("3.0", "4.0"):
        existing = {}

    # preserve authored behavioral content
    prev_nodes = existing.get("nodes", [])
    prev_edges = existing.get("edges", [])
    behavioral_nodes = [n for n in prev_nodes if n.get("tier") != "entity"]
    behavioral_edges = [e for e in prev_edges if e.get("type") not in STRUCTURAL_EDGE_TYPES]
    loops = existing.get("loops", [])
    force_instances = existing.get("force_instances", [])   # S2b — preserved across regen

    # carry forward authored entity bridge-fields across regeneration (keyed by
    # (statement, code)); structural fields + signal_ids are always refreshed.
    prev_entity_by_key = {(n.get("statement"), n.get("code")): n
                          for n in prev_nodes if n.get("tier") == "entity"}
    for n in nodes:
        prev = prev_entity_by_key.get((n["statement"], n["code"]))
        if not prev:
            continue
        for fld in ("data_section", "data_series"):
            if prev.get(fld):
                n[fld] = prev[fld]
        if prev.get("annotation_ids"):
            n["annotation_ids"] = prev["annotation_ids"]
        if prev.get("registry_domain") and not n.get("registry_domain"):
            n["registry_domain"] = prev["registry_domain"]
        # preserve an authored (non-default) description
        if prev.get("description") and not prev["description"].endswith(f"{n['code']})."):
            n["description"] = prev["description"]

    prev_entity_keys = set(prev_entity_by_key)
    cur_entity_keys = {(n["statement"], n["code"]) for n in nodes}
    added = sorted(cur_entity_keys - prev_entity_keys)
    removed = sorted(prev_entity_keys - cur_entity_keys)

    meta = existing.get("_meta", {})
    meta.update({
        "report_id": cfg["report_id"],
        "report_name": cfg["report_name"],
        "schema_version": meta.get("schema_version", "3.0"),   # preserve 4.0 once migrated
        "spec_ref": "analysis/SYSTEM_MODEL_SPEC.md",
        "skeleton_node_count": len(nodes),
        "skeleton_generated_by": "analysis/generate_skeleton.py",
    })

    model = {
        "_meta": meta,
        "nodes": nodes + behavioral_nodes,        # skeleton first, then behavioral
        "edges": edges + behavioral_edges,
        "force_instances": force_instances,       # S2b — preserved verbatim
        "loops": loops,
    }
    return model, added, removed, new_entities


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pipeline", required=True, choices=list(PIPELINES))
    ap.add_argument("--check", action="store_true",
                    help="Do not write; exit 1 if the on-disk skeleton differs from a fresh emit.")
    ap.add_argument("--skeleton-only", action="store_true",
                    help="Write only the skeleton (no behavioral merge) to --out.")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    cfg = PIPELINES[args.pipeline]
    profile = load_json(cfg["profile"])
    signal_index, domain_index = build_signal_index(
        args.pipeline, profile["signal_attach"]["registry"])

    new_entities = []
    if profile["hierarchy_source"] == "csv":
        nodes, edges = emit_skeleton_csv(profile, signal_index, domain_index)
    else:
        nodes, edges, new_entities = emit_skeleton_profile(profile, signal_index, domain_index)

    # determinism: stable order
    nodes.sort(key=lambda n: (n["statement"], n["level"], _codesort(n["code"])))

    # stamp global URNs + resolved concept_tags (COMPOSITION_SPEC.md §3, §4)
    apply_urn_and_concepts(nodes, args.pipeline, profile)

    expected = profile.get("_meta", {}).get("expected_node_count")
    print(f"[{args.pipeline}] emitted {len(nodes)} entities, {len(edges)} structural edges"
          + (f" (expected {expected})" if expected else ""))
    if expected and len(nodes) != expected:
        print(f"  ⚠ node count {len(nodes)} != expected {expected}", file=sys.stderr)
    if new_entities:
        print(f"  ⚠ CSV metrics not covered by profile (new-entity diff): {new_entities}",
              file=sys.stderr)

    if args.skeleton_only:
        out = Path(args.out) if args.out else (ROOT / "tmp_skeleton.json")
        out.write_text(json.dumps({"nodes": nodes, "edges": edges}, indent=2))
        print(f"  wrote skeleton-only → {out}")
        return 0

    model, added, removed, new_entities = merge_model(
        args.pipeline, cfg, profile, nodes, edges, new_entities)

    sig_total = sum(len(n["signal_ids"]) for n in nodes)
    gaps = [n["code"] for n in nodes if n["tier"] == "entity" and not n["signal_ids"]]
    print(f"  signal_ids attached: {sig_total} across entities; "
          f"{len(gaps)} entities with no L1 signal (L1-gap audit)")
    if added:
        print(f"  new entities since last run: {[k[1] for k in added]}")
    if removed:
        print(f"  ⚠ entities removed since last run: {[k[1] for k in removed]}")

    if args.check:
        # gate mode: compare freshly-emitted skeleton against on-disk
        on_disk = load_json(cfg["model"]) if cfg["model"].exists() else {"nodes": []}
        disk_entities = sorted((n.get("statement"), n.get("code"))
                               for n in on_disk.get("nodes", []) if n.get("tier") == "entity")
        fresh_entities = sorted((n["statement"], n["code"]) for n in nodes)
        if disk_entities != fresh_entities:
            print("  ✗ on-disk skeleton is STALE — run generate_skeleton.py to regenerate",
                  file=sys.stderr)
            return 1
        print("  ✓ on-disk skeleton matches fresh emit")
        return 0

    out_path = Path(args.out) if args.out else cfg["model"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(model, indent=2, ensure_ascii=False))
    print(f"  wrote {len(model['nodes'])} nodes "
          f"({len(nodes)} entity + {len(model['nodes']) - len(nodes)} behavioral), "
          f"{len(model['edges'])} edges, {len(model['loops'])} loops → "
          f"{out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
