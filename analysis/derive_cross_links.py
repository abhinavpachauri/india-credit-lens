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


def _pipe(urn):
    # urn = icl:{pipeline}/{partition}/{code}
    return urn.split(":", 1)[1].split("/", 1)[0]


def derive(ents):
    candidates = []
    # Unordered URN pairs already captured by a stronger rule (R1/R3). A shared-channel
    # (R2 co_driven) candidate between the same two entities is redundant — the stock↔flow
    # law already relates them — so we suppress it to cut R2 noise without losing signal.
    strong_pairs = set()

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
                strong_pairs.add(frozenset((flow["urn"], other["urn"])))
                candidates.append({
                    "rule": "R1_stock_flow", "type": "leads", "priority": 1,
                    # group folds the flow fan-out: many flow measures of one product → one stock
                    "group": f"R1:{product}:{_pipe(flow['urn'])}->{_pipe(other['urn'])}",
                    "from": flow["urn"], "to": other["urn"],
                    "shared": {"product": product},
                    "rationale": f"{flow['measure']} flow leads {other['measure']} for product {product}",
                    "status": "candidate",
                })
            elif {a["mclass"], b["mclass"]} == {"count", "stock"}:
                strong_pairs.add(frozenset((a["urn"], b["urn"])))
                candidates.append({
                    "rule": "R3_corresponds", "type": "corresponds_to", "priority": 2,
                    "group": f"R3:{product}",
                    "from": a["urn"], "to": b["urn"],
                    "shared": {"product": product},
                    "rationale": f"same product {product}, {a['measure']} ↔ {b['measure']}",
                    "status": "candidate",
                })

    # R2 — shared channel: entities (cross-pipeline) whose product a channel targets.
    # Skip pairs already captured by R1/R3 (redundant) and de-duplicate identical pairs
    # that several channels would otherwise emit repeatedly.
    channels = gs.load_json(ROOT / "analysis/ontology/channels.json")["channels"]
    seen_r2 = set()
    for ch in channels:
        target_products = {t.get("product") for t in ch.get("target_concepts", []) if t.get("product")}
        members = [e for e in ents if e["product"] in target_products]
        pipes = {m["pipeline"] for m in members}
        if len(pipes) < 2:
            continue
        for a, b in combinations(members, 2):
            if a["pipeline"] == b["pipeline"]:
                continue
            pair = frozenset((a["urn"], b["urn"]))
            if pair in strong_pairs:
                continue  # stock↔flow already relates them — co_driven adds nothing
            key = (ch["id"], pair)
            if key in seen_r2:
                continue
            seen_r2.add(key)
            candidates.append({
                "rule": "R2_shared_channel", "type": "co_driven", "priority": 3,
                "group": f"R2:{ch['id']}",
                "from": a["urn"], "to": b["urn"],
                "shared": {"channel": ch["id"], "product_a": a["product"], "product_b": b["product"]},
                "rationale": f"both products are targets of channel {ch['id']}",
                "status": "candidate",
            })
    # Highest-value (near-deterministic) law first; R2 noise last.
    candidates.sort(key=lambda c: (c["priority"], c.get("group", ""), c["from"], c["to"]))
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
    groups_by_rule = defaultdict(set)
    for c in candidates:
        groups_by_rule[c["rule"]].add(c.get("group"))
    print(f"derived {len(candidates)} cross-system candidates from {len(ents)} tagged entities")
    for r, n in sorted(by_rule.items()):
        print(f"    {r:20s} {n:3d} candidate(s) across {len(groups_by_rule[r])} group(s)  (priority {candidates and next(c['priority'] for c in candidates if c['rule']==r)})")
    print("  sample R1 stock↔flow links:")
    for c in candidates:
        if c["rule"] == "R1_stock_flow":
            print(f"    {c['from']}  --leads-->  {c['to']}  ({c['shared']['product']})")
    print(f"  → wrote {OUT_DIR.relative_to(ROOT)}/candidates.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
