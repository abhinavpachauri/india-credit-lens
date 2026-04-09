#!/usr/bin/env python3
"""
generate_mermaid.py — India Credit Lens
-----------------------------------------
Reads system_model.json and generates three Mermaid diagram files:

  flowchart.mmd  — layered causal flow (drivers → sectors → outcomes)
  quadrant.mmd   — credit opportunity map (growth rate vs credit stock)
  sankey.mmd     — credit allocation by volume

Runs validate.py first. Refuses to generate if validation fails.
Writes a sources.json audit trail alongside each diagram.

Usage:
    python3 generate_mermaid.py rbi_sibc_2026-02-27/system_model.json
    python3 generate_mermaid.py rbi_sibc_2026-02-27/system_model.json --skip-validation

Output: output/mermaid/[report_id]_[date]/
  flowchart.mmd
  quadrant.mmd
  sankey.mmd
  sources.json
  validation_report.json

Preview: paste any .mmd file at https://mermaid.live
"""

import json
import os
import re
import sys
import argparse
from pathlib import Path
from datetime import date

# ── Import validator ───────────────────────────────────────────────────────────

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate import validate, print_report, write_report, parse_growth_pct


# ── Node/edge filters ─────────────────────────────────────────────────────────

def real_nodes(model):
    # The JSON uses _comment as an inline field on the first item of each group.
    # A real node always has an "id" field.
    return [n for n in model.get("nodes", []) if "id" in n]


def real_edges(model):
    # A real edge always has a "from" field.
    return [e for e in model.get("edges", []) if "from" in e]


def nodes_by_tier(model):
    result = {}
    for node in real_nodes(model):
        result.setdefault(node.get("tier"), []).append(node)
    return result


# ── Label helpers ─────────────────────────────────────────────────────────────

def short(text, max_len=28):
    """Truncate to max_len chars for diagram readability."""
    if not text:
        return ""
    return text if len(text) <= max_len else text[:max_len - 1] + "…"


def node_label(node, include_stat=True, include_volume=True):
    """Build multi-line node label from available fields."""
    parts = [short(node["label"])]
    if include_stat and node.get("stat"):
        parts.append(node["stat"])
    if include_volume and node.get("value_lcr"):
        parts.append(f"₹{node['value_lcr']}L Cr")
    return "\\n".join(parts)


# ── Flowchart ─────────────────────────────────────────────────────────────────

# Mermaid shape syntax by tier
TIER_SHAPE = {
    "driver":      ("([", "])"),   # stadium  — forces, macro
    "sector":      ("[",  "]"),    # rectangle — credit data
    "gap":         ("{{", "}}"),   # hexagon   — data warnings
    "opportunity": ("(",  ")"),    # rounded   — positive outcomes
    "pressure":    ("[/", "/]"),   # parallelogram — risks
}

# CSS class fill/stroke/colour by tier
TIER_STYLE = {
    "driver":      "fill:#1E3A5F,stroke:#1E3A5F,color:#ffffff",
    "sector":      "fill:#F0FDF4,stroke:#166534,color:#166534",
    "gap":         "fill:#F9FAFB,stroke:#6B7280,color:#374151",
    "opportunity": "fill:#0F766E,stroke:#0F766E,color:#ffffff",
    "pressure":    "fill:#B45309,stroke:#B45309,color:#ffffff",
}

# Subgraph header labels
TIER_SUBGRAPH = {
    "driver":      "⚡ WHAT'S DRIVING THE SYSTEM",
    "sector":      "📊 WHERE CREDIT IS MOVING",
    "gap":         "🔍 DATA GAPS — what we can't see",
    "opportunity": "🎯 OPPORTUNITIES — where to play",
    "pressure":    "⚠️ RISKS — what could break",
}

# Ordered rendering sequence
TIER_ORDER = ["driver", "sector", "gap", "opportunity", "pressure"]

# Mermaid arrow syntax by edge type
EDGE_ARROW = {
    "causes":              "-->",
    "suppresses":          "-.->",
    "reroutes_demand_to":  "==>",
    "reinforces":          "-->",
    "creates_risk":        "-.->",
    "creates_opportunity": "-->",
    "is_data_gap":         "-.->",
    "creates_gap":         "-.->",
    "signals":             "-->",
    "contrast":            "<-->",
}


def generate_flowchart(model, meta):
    tiers  = nodes_by_tier(model)
    edges  = real_edges(model)
    period = meta.get("period", "")
    total  = meta.get("total_credit_lcr", "")
    yoy    = meta.get("yoy_growth_pct", "")

    lines = [
        "---",
        f"title: India Credit System — {period}  |  ₹{total}L Cr total  |  +{yoy}% YoY",
        "---",
        "flowchart TD",
        "",
        "%% ── Style classes by node tier ─────────────────────────────────────────",
    ]

    for tier, style in TIER_STYLE.items():
        lines.append(f"    classDef {tier}Node {style}")
    lines.append("")

    # Subgraphs (one per tier, LR layout inside)
    for tier in TIER_ORDER:
        nodes = tiers.get(tier, [])
        if not nodes:
            continue

        sg_label = TIER_SUBGRAPH[tier]
        lines += [
            f"    subgraph {tier.upper()}[\"{sg_label}\"]",
            "        direction LR",
        ]

        for node in nodes:
            nid        = node["id"]
            open_b, close_b = TIER_SHAPE[tier]
            label      = node_label(node)
            lines.append(f'        {nid}{open_b}"{label}"{close_b}')

        lines += ["    end", ""]

    # Apply style classes
    lines.append("%% ── Apply styles ────────────────────────────────────────────────────────")
    for tier in TIER_ORDER:
        nodes = tiers.get(tier, [])
        if not nodes:
            continue
        id_list = ",".join(n["id"] for n in nodes)
        lines.append(f"    class {id_list} {tier}Node")
    lines.append("")

    # Edges — labels verbatim from system_model.json (no inference)
    lines.append("%% ── Edges — labels from system_model.json only ──────────────────────────")
    for edge in edges:
        arrow  = EDGE_ARROW.get(edge["type"], "-->")
        label  = short(edge.get("label", edge["type"]), max_len=45)
        lines.append(f'    {edge["from"]} {arrow}|"{label}"| {edge["to"]}')

    return "\n".join(lines)


# ── Quadrant ──────────────────────────────────────────────────────────────────

# y-axis bounds — growth rates are clamped to this range before normalising
QUAD_Y_MIN = -20.0
QUAD_Y_MAX = 150.0


def generate_quadrant(model, meta):
    tiers  = nodes_by_tier(model)
    period = meta.get("period", "")

    # Exclude the total-credit root node — it's the system aggregate, not a sector to plot
    QUADRANT_EXCLUDE = {"sector_total_credit"}

    plottable = []
    for node in tiers.get("sector", []):
        if node["id"] in QUADRANT_EXCLUDE:
            continue
        growth = parse_growth_pct(node.get("stat"))
        volume = node.get("value_lcr")
        if growth is not None and volume is not None:
            plottable.append((node, growth, volume))

    if not plottable:
        return None  # caller handles skip

    max_vol = max(v for _, _, v in plottable)

    def norm_x(v):
        # Scale volume to (0.05, 0.95) — avoid touching the axes
        return round(min(v / max_vol * 0.88 + 0.05, 0.95), 2)

    def norm_y(g):
        clamped = max(QUAD_Y_MIN, min(QUAD_Y_MAX, g))
        return round((clamped - QUAD_Y_MIN) / (QUAD_Y_MAX - QUAD_Y_MIN), 2)

    lines = [
        "quadrantChart",
        f"    title Credit Opportunity Map — {period}",
        "    x-axis Low Credit Stock --> High Credit Stock",
        "    y-axis Low Growth --> High Growth",
        "    quadrant-1 Scale — large book + high growth",
        "    quadrant-2 Build — small book + high growth",
        "    quadrant-3 Watch — small book + low growth",
        "    quadrant-4 Harvest — large book + low growth",
        "",
        f"%% Axes: x = value_lcr (₹L Cr), y = YoY growth % (clamped to {QUAD_Y_MIN}–{QUAD_Y_MAX}%)",
        "%% Values normalised 0–1. Raw data in sources.json.",
        "",
    ]

    for node, growth, volume in sorted(plottable, key=lambda x: x[2], reverse=True):
        label = short(node["label"], max_len=22)
        x     = norm_x(volume)
        y     = norm_y(growth)
        lines.append(f"    {label}: [{x}, {y}]")

    return "\n".join(lines)


# ── Sankey ────────────────────────────────────────────────────────────────────

SANKEY_MIN_VOLUME = 1.0   # Sectors below this ₹L Cr are grouped into "Other"


def generate_sankey(model, meta):
    tiers  = nodes_by_tier(model)
    period = meta.get("period", "")
    total  = meta.get("total_credit_lcr", "")

    # Collect sector nodes with volume, excluding the total-credit root node.
    # Note: sector volumes sum > total because sub-sectors overlap with parent sectors
    # (e.g. PSL Housing is a subset of Housing Loans). The sankey shows allocation
    # by volume, not a balanced flow. This is noted in the diagram comments.
    SANKEY_EXCLUDE = {"sector_total_credit"}
    sectors = [
        (n, n["value_lcr"])
        for n in tiers.get("sector", [])
        if n.get("value_lcr") and n["id"] not in SANKEY_EXCLUDE
    ]
    sectors.sort(key=lambda x: x[1], reverse=True)

    large = [(n, v) for n, v in sectors if v >= SANKEY_MIN_VOLUME]
    small = [(n, v) for n, v in sectors if v <  SANKEY_MIN_VOLUME]

    source = f"Bank Credit {period}"

    lines = [
        "---",
        "config:",
        "  sankey:",
        "    showValues: true",
        "---",
        "sankey-beta",
        "",
        f"%% Credit allocation — {period} | Total ₹{total}L Cr",
        f"%% Band width = ₹L Cr. Direction = allocation, not causality.",
        f"%% Sectors < ₹{SANKEY_MIN_VOLUME}L Cr grouped into 'Other'.",
        "",
    ]

    for node, vol in large:
        label = node["label"]
        lines.append(f"{source},{label},{vol}")

    if small:
        other_vol = round(sum(v for _, v in small), 2)
        lines.append(f"{source},Other Sectors,{other_vol}")

    return "\n".join(lines)


# ── Sources audit trail ────────────────────────────────────────────────────────

def generate_sources(model):
    """Map every node to its annotation_ids — the audit trail linking
    each diagram element back to the source analysis."""
    return {
        node["id"]: {
            "label":          node["label"],
            "tier":           node.get("tier"),
            "stat":           node.get("stat"),
            "value_lcr":      node.get("value_lcr"),
            "annotation_ids": node.get("annotation_ids", []),
        }
        for node in real_nodes(model)
    }


# ── Entry point ───────────────────────────────────────────────────────────────

def generate(model_path, skip_validation=False, output_dir=None):
    base = os.path.dirname(os.path.abspath(__file__))

    # ── Step 1: Validate ──────────────────────────────────────────────────────
    print("\n" + "─" * 64)
    if not skip_validation:
        print("Step 1/2 — Validating system_model.json...\n")
        result, model = validate(model_path)
        print_report(result, model_path)

        if not result.passed:
            print("❌  Generation blocked — resolve errors above first.\n")
            sys.exit(1)

        print("✅  Validation passed — proceeding to diagram generation.\n")
    else:
        print("⚠️   Validation skipped (--skip-validation). Proceeding.\n")
        with open(model_path) as f:
            model = json.load(f)
        result = None

    # ── Step 2: Setup output directory ────────────────────────────────────────
    meta       = model.get("_meta", {})
    report_id  = meta.get("report_id", "report")

    if not output_dir:
        output_dir = os.path.join(
            base, "output", "mermaid", f"{report_id}_{date.today()}"
        )
    os.makedirs(output_dir, exist_ok=True)

    print("─" * 64)
    print("Step 2/2 — Generating Mermaid diagrams...\n")

    generated = []

    # ── Flowchart ─────────────────────────────────────────────────────────────
    code = generate_flowchart(model, meta)
    fp   = os.path.join(output_dir, "flowchart.mmd")
    with open(fp, "w") as f:
        f.write(code)
    generated.append(("Flowchart (causal flow)", fp))

    # ── Quadrant ──────────────────────────────────────────────────────────────
    code = generate_quadrant(model, meta)
    if code:
        fp = os.path.join(output_dir, "quadrant.mmd")
        with open(fp, "w") as f:
            f.write(code)
        generated.append(("Quadrant (opportunity map)", fp))
    else:
        print("  ⚠️   Quadrant skipped — insufficient sector nodes with both value_lcr and stat.\n")

    # ── Sankey ────────────────────────────────────────────────────────────────
    code = generate_sankey(model, meta)
    fp   = os.path.join(output_dir, "sankey.mmd")
    with open(fp, "w") as f:
        f.write(code)
    generated.append(("Sankey (credit allocation)", fp))

    # ── Sources audit trail ───────────────────────────────────────────────────
    sources = generate_sources(model)
    fp      = os.path.join(output_dir, "sources.json")
    with open(fp, "w") as f:
        json.dump(sources, f, indent=2)
    generated.append(("Sources audit trail", fp))

    # ── Validation report (if ran) ────────────────────────────────────────────
    if result:
        fp = write_report(result, model_path, output_dir)
        generated.append(("Validation report", fp))

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"  Output directory:\n  {output_dir}\n")
    for name, path in generated:
        fname = os.path.basename(path)
        print(f"  ✓  {name:<30} {fname}")

    print(f"""
  ─────────────────────────────────────────────
  Preview diagrams:
  → Paste any .mmd file at https://mermaid.live
  → Export PNG for newsletter / Canva import
  ─────────────────────────────────────────────
""")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate Mermaid diagrams from system_model.json"
    )
    parser.add_argument("model",              help="Path to system_model.json")
    parser.add_argument("--skip-validation",  action="store_true",
                        help="Skip validation step (not recommended)")
    parser.add_argument("--output",           help="Output directory override")
    args = parser.parse_args()

    generate(args.model, args.skip_validation, args.output)
