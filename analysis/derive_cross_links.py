#!/usr/bin/env python3
"""
derive_cross_links.py — deterministic cross-system candidate derivation
-----------------------------------------------------------------------
The M+N composition step (COMPOSITION_SPEC.md §6). Reads every pipeline's
system_model.json + the shared hub (concepts/channels) and DERIVES candidate
cross-system links through shared concept coordinates — never pairwise authoring.

Three derivation rules (all cross-pipeline only):
  R1 stock↔flow   — same product, one side flow.* and the other stock.*/count.* ⇒ `leads`
                    (flow leads stock; the highest-value, near-deterministic law).
  R2 shared-channel — two entities whose product a channel targets ⇒ `co_driven`.
  R3 corresponds  — same product, count.value ↔ stock.balance ⇒ `corresponds_to`.

Output: analysis/cross_source/candidates.json (regenerable; never hand-edited).
Confirmed links are promoted by hand into analysis/cross_source/composition.json.

Usage:
    python3 analysis/derive_cross_links.py
"""
import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import generate_skeleton as gs

ROOT = gs.ROOT
OUT_DIR = ROOT / "analysis" / "cross_source"


def measure_class(tags):
    m = (tags or {}).get("measure") or ""
    return m.split(".")[0] if m else None


def load_entities():
    """All tagged entities across pipelines, keyed by urn."""
    ents = []
    for pipe, cfg in gs.PIPELINES.items():
        if not cfg["model"].exists():
            continue
        model = gs.load_json(cfg["model"])
        for n in model["nodes"]:
            if n.get("tier") == "entity" and (n.get("concept_tags") or {}).get("product"):
                ents.append({
                    "pipeline": pipe, "urn": n["urn"], "label": n["label"],
                    "product": n["concept_tags"]["product"],
                    "measure": n["concept_tags"].get("measure"),
                    "mclass": measure_class(n["concept_tags"]),
                    "segment": n["concept_tags"].get("segment"),
                })
    return ents


def derive(ents):
    candidates = []

    # R1 + R3 — group by product, pair across pipelines with differing measure class
    by_product = defaultdict(list)
    for e in ents:
        by_product[e["product"]].append(e)
    for product, group in by_product.items():
        for a, b in combinations(group, 2):
            if a["pipeline"] == b["pipeline"]:
                continue
            if a["mclass"] == b["mclass"]:
                continue
            # orient flow → (stock|count)
            flow, other = (a, b) if a["mclass"] == "flow" else (b, a) if b["mclass"] == "flow" else (None, None)
            if flow is not None and other["mclass"] in ("stock", "count"):
                candidates.append({
                    "rule": "R1_stock_flow", "type": "leads",
                    "from": flow["urn"], "to": other["urn"],
                    "shared": {"product": product},
                    "rationale": f"{flow['measure']} flow leads {other['measure']} for product {product}",
                    "status": "candidate",
                })
            elif {a["mclass"], b["mclass"]} == {"count", "stock"}:
                candidates.append({
                    "rule": "R3_corresponds", "type": "corresponds_to",
                    "from": a["urn"], "to": b["urn"],
                    "shared": {"product": product},
                    "rationale": f"same product {product}, {a['measure']} ↔ {b['measure']}",
                    "status": "candidate",
                })

    # R2 — shared channel: entities (cross-pipeline) whose product a channel targets
    channels = gs.load_json(ROOT / "analysis/ontology/channels.json")["channels"]
    for ch in channels:
        target_products = {t.get("product") for t in ch.get("target_concepts", []) if t.get("product")}
        members = [e for e in ents if e["product"] in target_products]
        pipes = {m["pipeline"] for m in members}
        if len(pipes) < 2:
            continue
        for a, b in combinations(members, 2):
            if a["pipeline"] == b["pipeline"]:
                continue
            candidates.append({
                "rule": "R2_shared_channel", "type": "co_driven",
                "from": a["urn"], "to": b["urn"],
                "shared": {"channel": ch["id"], "product_a": a["product"], "product_b": b["product"]},
                "rationale": f"both products are targets of channel {ch['id']}",
                "status": "candidate",
            })
    return candidates


def main():
    ents = load_entities()
    candidates = derive(ents)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = {
        "_meta": {
            "description": "Derived cross-system candidate links (COMPOSITION_SPEC.md §6). "
                           "Regenerable — never hand-edit. Promote confirmed links into composition.json.",
            "spec_ref": "analysis/COMPOSITION_SPEC.md",
            "generated_by": "analysis/derive_cross_links.py",
        },
        "candidates": candidates,
    }
    (OUT_DIR / "candidates.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))

    from collections import Counter
    by_rule = Counter(c["rule"] for c in candidates)
    cross_pairs = Counter(tuple(sorted({c["from"].split("/")[0], c["to"].split("/")[0]})) for c in candidates)
    print(f"derived {len(candidates)} cross-system candidates from {len(ents)} tagged entities")
    for r, n in sorted(by_rule.items()):
        print(f"    {r:20s} {n}")
    print("  sample R1 stock↔flow links:")
    for c in candidates:
        if c["rule"] == "R1_stock_flow":
            print(f"    {c['from']}  --leads-->  {c['to']}  ({c['shared']['product']})")
    print(f"  → wrote {OUT_DIR.relative_to(ROOT)}/candidates.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
