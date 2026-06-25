#!/usr/bin/env python3
"""
generate_mermaid.py — India Credit Lens
-----------------------------------------
Reads system_model.json and generates Mermaid diagram files:

  flowchart.mmd       — layered causal flow (drivers → sectors → outcomes)
  quadrant.mmd        — credit opportunity map (growth rate vs credit stock)
  sankey.mmd          — credit allocation by volume
  sources.json        — audit trail linking nodes to annotation_ids
  subsystems.json     — algorithmically derived causal subsystems
  overview.mmd        — system-level overview (one node per subsystem)
  sub_NN_<slug>.mmd   — focused flowchart per subsystem

Runs validate.py first. Refuses to generate if validation fails.
Writes a sources.json audit trail alongside each diagram.

Usage:
    python3 generate_mermaid.py rbi_sibc/2026-02-27/system_model.json
    python3 generate_mermaid.py rbi_sibc/2026-02-27/system_model.json --skip-validation

Output: output/mermaid/[report_id]/[period_date]/
  flowchart.mmd
  quadrant.mmd
  sankey.mmd
  sources.json
  validation_report.json
  subsystems.json
  overview.mmd
  sub_NN_<slug>.mmd  (one per subsystem)

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

    # ── Build the set of node IDs referenced in at least one edge ────────────
    # Sector nodes not in any edge are orphans (e.g. total_credit, vehicle_loans,
    # housing, trade) — exclude them from the causal flow diagram.
    referenced_ids = set()
    for e in edges:
        referenced_ids.add(e["from"])
        referenced_ids.add(e["to"])

    def include_node(node):
        # Non-sector tiers: always include (all drivers/gaps/opps/pressures are connected)
        if node.get("tier") != "sector":
            return True
        return node["id"] in referenced_ids

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

    lines += [
        "",
        "%% Arrow legend:",
        "%% -->   causes / creates / signals",
        "%% -.->  suppresses / creates_risk / creates_gap",
        "%% ==>   reroutes_demand_to",
        "%% <-->  contrast",
        "",
    ]

    # Subgraphs — no inner direction directive, let Mermaid use outer TD
    for tier in TIER_ORDER:
        nodes = [n for n in tiers.get(tier, []) if include_node(n)]
        if not nodes:
            continue

        sg_label = TIER_SUBGRAPH[tier]
        lines.append(f"    subgraph {tier.upper()}[\"{sg_label}\"]")

        for node in nodes:
            nid             = node["id"]
            open_b, close_b = TIER_SHAPE[tier]
            # Sector: label + stat. Others: label only (cleaner)
            if tier == "sector" and node.get("stat"):
                label = f'{node["label"]}\\n{node["stat"]}'
            else:
                label = node["label"]
            lines.append(f'        {nid}{open_b}"{label}"{close_b}')

        lines += ["    end", ""]

    # Apply style classes (filtered same as above)
    lines.append("%% ── Apply styles ────────────────────────────────────────────────────────")
    for tier in TIER_ORDER:
        nodes = [n for n in tiers.get(tier, []) if include_node(n)]
        if not nodes:
            continue
        id_list = ",".join(n["id"] for n in nodes)
        lines.append(f"    class {id_list} {tier}Node")
    lines.append("")

    # Edges — no labels (arrow style encodes relationship type; labels cluttered diagram)
    lines.append("%% ── Edges ───────────────────────────────────────────────────────────────")
    for edge in edges:
        # Skip edges where either endpoint was filtered out (orphaned sector nodes)
        if edge["from"] not in referenced_ids and \
           tiers_lookup(tiers, edge["from"]) == "sector":
            continue
        if edge["to"] not in referenced_ids and \
           tiers_lookup(tiers, edge["to"]) == "sector":
            continue
        arrow = EDGE_ARROW.get(edge["type"], "-->")
        lines.append(f'    {edge["from"]} {arrow} {edge["to"]}')

    return "\n".join(lines)


def tiers_lookup(tiers, node_id):
    """Return tier name for a node_id, or None if not found."""
    for tier, nodes in tiers.items():
        for n in nodes:
            if n.get("id") == node_id:
                return tier
    return None


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
        "    quadrant-1 Scale",
        "    quadrant-2 Build",
        "    quadrant-3 Watch",
        "    quadrant-4 Harvest",
        "",
        f"%% Axes: x = value_lcr (₹L Cr), y = YoY growth % (clamped to {QUAD_Y_MIN}–{QUAD_Y_MAX}%)",
        "%% Values normalised 0–1. Raw data in sources.json.",
        "",
    ]

    for node, growth, volume in sorted(plottable, key=lambda x: x[2], reverse=True):
        # Quadrant labels: alphanumeric + spaces only — no &, ₹, /, %, —, …
        raw   = node["label"]
        label = re.sub(r"[^A-Za-z0-9 ]", "", raw).strip()
        label = " ".join(label.split())   # collapse multiple spaces
        label = label[:24]                # keep it short
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


# ── Subsystem helpers ─────────────────────────────────────────────────────────

def sanitize_slug(label):
    """Convert a label to a filename-safe slug (max 30 chars)."""
    s = label.lower()
    s = re.sub(r"[^a-z0-9 ]", "", s)      # keep only alphanum + spaces
    s = s.replace(" ", "_")
    s = re.sub(r"_+", "_", s)              # collapse multiple underscores
    s = s.strip("_")
    return s[:30]


def derive_subsystems(model):
    """Algorithmically derive causal subsystems from the system model.

    Returns a list of subsystem dicts, sorted by driver count descending.
    Each dict contains: id, label, chart_type, chart_direction, newsletter,
    drivers, sectors, outcomes, node_ids.
    """
    id_to_node  = {n["id"]: n for n in real_nodes(model)}
    id_to_tier  = {n["id"]: n.get("tier", "") for n in real_nodes(model)}

    outgoing = {}  # from_id -> [(to_id, edge_type)]
    incoming = {}  # to_id   -> [(from_id, edge_type)]
    for e in real_edges(model):
        outgoing.setdefault(e["from"], []).append((e["to"],   e["type"]))
        incoming.setdefault(e["to"],   []).append((e["from"], e["type"]))

    OUTCOME_TIERS = {"gap", "opportunity", "pressure"}

    # Step 1: anchor sectors — sectors with direct outgoing edges to outcome nodes
    anchors = {}  # sector_id -> set of outcome_ids
    for e in real_edges(model):
        if (id_to_tier.get(e["from"]) == "sector"
                and id_to_tier.get(e["to"]) in OUTCOME_TIERS):
            anchors.setdefault(e["from"], set()).add(e["to"])

    # Step 2: group anchors that share at least one outcome node
    groups = []  # list of {"sectors": set, "outcomes": set}
    for sector_id, outcomes in anchors.items():
        merged = False
        for group in groups:
            if group["outcomes"] & outcomes:
                group["sectors"].add(sector_id)
                group["outcomes"] |= outcomes
                merged = True
                break
        if not merged:
            groups.append({"sectors": {sector_id}, "outcomes": set(outcomes)})

    # Step 2.5: compute drivers per group (needed for merging)
    def compute_drivers_for_group(group):
        drivers = set()
        for sid in group["sectors"]:
            for from_id, _ in incoming.get(sid, []):
                if id_to_tier.get(from_id) == "driver":
                    drivers.add(from_id)
        return drivers

    for group in groups:
        group["drivers"] = compute_drivers_for_group(group)

    # Step 2.6: merge single-driver fragment groups into multi-driver groups
    # sharing that same driver. Repeat until stable.
    changed = True
    while changed:
        changed = False
        merged_groups = []
        used = [False] * len(groups)
        for i, grp_i in enumerate(groups):
            if used[i]:
                continue
            if len(grp_i["drivers"]) != 1:
                merged_groups.append(grp_i)
                continue
            shared_driver = next(iter(grp_i["drivers"]))
            # look for a multi-driver group that also has this driver
            target = None
            for j, grp_j in enumerate(groups):
                if i == j or used[j]:
                    continue
                if shared_driver in grp_j["drivers"] and len(grp_j["drivers"]) > 1:
                    target = j
                    break
            if target is not None:
                # merge grp_i into grp_j
                groups[target]["sectors"]  |= grp_i["sectors"]
                groups[target]["outcomes"] |= grp_i["outcomes"]
                groups[target]["drivers"]  |= grp_i["drivers"]
                used[i] = True
                changed = True
            else:
                merged_groups.append(grp_i)
        if changed:
            groups = [g for idx, g in enumerate(groups) if not used[idx]]

    # Step 3: for each group build the subsystem
    sub_labels = model.get("subsystem_labels", {})   # editorial priority order

    subsystems = []
    for group in groups:
        sectors  = group["sectors"]
        drivers  = group["drivers"]
        outcomes = set(group["outcomes"])

        # include direct driver→outcome edges from these same drivers
        for did in drivers:
            for to_id, _ in outgoing.get(did, []):
                if id_to_tier.get(to_id) in OUTCOME_TIERS:
                    outcomes.add(to_id)

        # chart direction heuristic
        if len(drivers) >= 3 or (len(drivers) >= 2 and len(sectors) >= 2):
            direction = "LR"
        elif len(outcomes) >= 3:
            direction = "TD"
        else:
            direction = "LR"

        # label selection — editorial priority first, then most-connected driver
        if drivers:
            # pick first driver that appears in sub_labels (insertion order = priority)
            labeled = [d for d in sub_labels if d in drivers]
            if labeled:
                primary = labeled[0]
            else:
                primary = max(
                    drivers,
                    key=lambda d: sum(1 for to, _ in outgoing.get(d, []) if to in sectors),
                )
            raw_label = sub_labels.get(primary) or id_to_node[primary]["label"]
        else:
            # driverless: name by outcome composition
            has_opp = any(
                id_to_tier.get(o) == "opportunity" for o in outcomes
            )
            sec_name = id_to_node[sorted(sectors)[0]]["label"] if sectors else "Unknown"
            if has_opp:
                raw_label = f"{sec_name} Signal"
            else:
                raw_label = f"Data Quality: {sec_name}"

        node_ids = sorted(drivers | sectors | outcomes)

        subsystems.append({
            "label":           raw_label,
            "chart_type":      "flowchart",
            "chart_direction": direction,
            "newsletter":      False,
            "drivers":         sorted(drivers),
            "sectors":         sorted(sectors),
            "outcomes":        sorted(outcomes),
            "node_ids":        node_ids,
        })

    # sort by driver count descending; assign IDs; mark top 3 for newsletter
    subsystems.sort(key=lambda s: -len(s["drivers"]))
    for i, sub in enumerate(subsystems):
        sub["id"]         = f"sub_{i + 1:02d}"
        sub["newsletter"] = i < 3

    return subsystems


def generate_subsystem_diagram(sub, model):
    """Render a focused flowchart for one subsystem dict.

    Only edges where BOTH endpoints are in sub['node_ids'] are included.
    No edge labels. Returns a mmd string.
    """
    direction  = sub["chart_direction"]
    node_id_set = set(sub["node_ids"])
    id_to_node = {n["id"]: n for n in real_nodes(model)}
    id_to_tier = {n["id"]: n.get("tier", "") for n in real_nodes(model)}

    sub_edges = [
        e for e in real_edges(model)
        if e["from"] in node_id_set and e["to"] in node_id_set
    ]

    lines = [
        "---",
        f"title: {sub['label']}",
        "---",
        f"flowchart {direction}",
        "",
    ]

    # classDef lines
    for tier, style in TIER_STYLE.items():
        lines.append(f"    classDef {tier}Node {style}")
    lines.append("")

    # arrow legend as comment
    lines += [
        "%% --> causes/creates/signals  -.-> suppresses/risk/gap  ==> reroutes  <--> contrast",
        "",
    ]

    # nodes grouped by tier in TIER_ORDER
    nodes_by_t = {}
    for nid in sub["node_ids"]:
        node = id_to_node.get(nid)
        if not node:
            continue
        t = id_to_tier.get(nid, "")
        nodes_by_t.setdefault(t, []).append(node)

    for tier in TIER_ORDER:
        tier_nodes = nodes_by_t.get(tier, [])
        if not tier_nodes:
            continue
        open_b, close_b = TIER_SHAPE[tier]
        for node in tier_nodes:
            if tier == "sector" and node.get("stat"):
                lbl = f'{node["label"]}\\n{node["stat"]}'
            else:
                lbl = node["label"]
            lines.append(f'    {node["id"]}{open_b}"{lbl}"{close_b}')

    lines.append("")

    # classDef assignments
    for tier in TIER_ORDER:
        tier_nodes = nodes_by_t.get(tier, [])
        if tier_nodes:
            lines.append(
                f'    class {",".join(n["id"] for n in tier_nodes)} {tier}Node'
            )
    lines.append("")

    # edges — no labels
    for e in sub_edges:
        arrow = EDGE_ARROW.get(e["type"], "-->")
        lines.append(f'    {e["from"]} {arrow} {e["to"]}')

    return "\n".join(lines)


def generate_overview(subsystems, model):
    """Render a system-level overview diagram.

    One driver meta-node + one sector meta-node + one outcome summary node
    per subsystem, connected LR. Returns a mmd string.
    """
    meta       = model.get("_meta", {})
    id_to_node = {n["id"]: n for n in real_nodes(model)}

    lines = [
        "---",
        f"title: System Overview — {meta.get('period', '')}  |  {len(subsystems)} causal stories",
        "---",
        "flowchart LR",
        "",
        f"    classDef driverNode {TIER_STYLE['driver']}",
        f"    classDef sectorNode {TIER_STYLE['sector']}",
        f"    classDef outcomeNode {TIER_STYLE['opportunity']}",
        "",
    ]

    for sub in subsystems:
        sid = sub["id"]
        has_drivers = len(sub["drivers"]) > 0

        # driver meta-node: only for subsystems that have drivers
        if has_drivers:
            driver_label = sub["label"].replace('"', "'")
            lines.append(f'    {sid}_drv(["{driver_label}"]):::driverNode')

        # sector meta-node: pick sector with highest absolute YoY growth, else first with stat
        def _stat_magnitude(n):
            """Return absolute numeric value from stat string like '+128.8% YoY'."""
            import re as _re
            m = _re.search(r"[-+]?\d+\.?\d*", n.get("stat", "") or "")
            return abs(float(m.group())) if m else 0.0

        candidates = [id_to_node.get(nid) for nid in sub["sectors"] if id_to_node.get(nid)]
        stat_candidates = [n for n in candidates if n.get("stat")]
        primary_sector_node = (
            max(stat_candidates, key=_stat_magnitude) if stat_candidates
            else (candidates[0] if candidates else None)
        )

        if primary_sector_node:
            slabel   = primary_sector_node["label"]
            sstat    = primary_sector_node.get("stat", "")
            sec_text = f'{slabel}\\n{sstat}' if sstat else slabel
        else:
            sec_text = sub["label"]
        lines.append(f'    {sid}_sec["{sec_text}"]:::sectorNode')

        # outcome summary node
        n_opp  = sum(
            1 for nid in sub["outcomes"]
            if id_to_node.get(nid, {}).get("tier") == "opportunity"
        )
        n_gap  = sum(
            1 for nid in sub["outcomes"]
            if id_to_node.get(nid, {}).get("tier") == "gap"
        )
        n_risk = sum(
            1 for nid in sub["outcomes"]
            if id_to_node.get(nid, {}).get("tier") == "pressure"
        )
        parts = []
        if n_opp:  parts.append(f"{n_opp} opp")
        if n_risk: parts.append(f"{n_risk} risk")
        if n_gap:  parts.append(f"{n_gap} gap")
        out_text = " + ".join(parts) if parts else "outcomes"
        lines.append(f'    {sid}_out("{out_text}"):::outcomeNode')

        # edges — driverless subsystems skip the driver node
        if has_drivers:
            lines.append(f'    {sid}_drv --> {sid}_sec')
        lines.append(f'    {sid}_sec --> {sid}_out')
        lines.append("")

    return "\n".join(lines)


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
        # Use period date from _meta.generated so output is tied to data period, not run date
        period_date = meta.get("generated", str(date.today()))
        output_dir = os.path.join(
            base, "output", "mermaid", report_id, period_date
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

    # ── Derive subsystems ─────────────────────────────────────────────────────
    print("  Deriving subsystems algorithmically...")
    subsystems = derive_subsystems(model)
    print(f"  {len(subsystems)} subsystems identified\n")

    # Write subsystems.json for inspection / human override
    sub_json_path = os.path.join(output_dir, "subsystems.json")
    with open(sub_json_path, "w") as f:
        json.dump(subsystems, f, indent=2)
    generated.append(("Subsystems (derived)", sub_json_path))

    # ── System overview ───────────────────────────────────────────────────────
    code = generate_overview(subsystems, model)
    fp   = os.path.join(output_dir, "overview.mmd")
    with open(fp, "w") as f:
        f.write(code)
    generated.append(("System overview", fp))

    # ── Per-subsystem diagrams ────────────────────────────────────────────────
    for sub in subsystems:
        slug  = sanitize_slug(sub["label"])
        code  = generate_subsystem_diagram(sub, model)
        fname = f'{sub["id"]}_{slug}.mmd'
        fp    = os.path.join(output_dir, fname)
        with open(fp, "w") as f:
            f.write(code)
        n_flag = " [newsletter]" if sub["newsletter"] else ""
        generated.append((f'Subsystem: {sub["label"]}{n_flag}', fp))

    # ── Summary ───────────────────────────────────────────────────────────────
    n_subsystems = len(subsystems)
    print(f"  Output directory:\n  {output_dir}\n")
    for name, path in generated:
        fname = os.path.basename(path)
        print(f"  ✓  {name:<42} {fname}")

    print(f"""
  ─────────────────────────────────────────────
  {n_subsystems} subsystems derived | 3 flagged for newsletter
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
