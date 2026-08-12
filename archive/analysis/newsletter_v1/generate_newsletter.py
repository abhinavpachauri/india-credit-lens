#!/usr/bin/env python3
"""
generate_newsletter.py v4 — India Credit Lens
----------------------------------------------
Supports two config formats:

  system_model_v2  (Issue #1, standalone)
    Sources: system_model.json, rbi_sibc.ts, newsletter_config.json, subsystems.json
    Structure: HEADER → HERO → TL;DR → WHERE CREDIT MOVED → KEY SIGNALS →
               SYSTEM OVERVIEW → STORIES → WHAT TO WATCH → CTA

  delta_v1  (Issue #2+, delta from previous period)
    Sources: merged system_model.json, rbi_sibc.ts, newsletter_config.json,
             merged subsystems.json
    Structure: HEADER → HERO → WHAT HELD → WHAT CHANGED → WHAT'S NEW →
               WHAT TO WATCH → CTA
    Editorial fields: what_held[], what_changed[], what_new[], what_to_watch
    Image support (Option B): image_url per signal — if empty, renders dashed
                              placeholder; if set, renders <img> tag.

Usage:
    python3 generate_newsletter.py
    python3 generate_newsletter.py newsletter_config.json

Output:
    output/newsletter_YYYY-MM-DD_substack.html  ← paste into Substack editor
"""

import json
import os
import re
import sys
from pathlib import Path
from datetime import date


# ── Node ID → CSV sector name mapping (for YoY computation from consolidated CSV) ──
# Keys = system_model node IDs (stable across issues)
# Values = exact sector name in rbi_sibc_consolidated.csv
NODE_TO_CSV_SECTOR = {
    "sector_bank_credit":     "Bank Credit (II + III)",
    "sector_personal_loans":  "Personal Loans",
    "sector_gold_loans":      "Loans against gold jewellery",
    "sector_credit_cards":    "Credit Card Outstanding",
    "sector_vehicle_loans":   "Vehicle Loans",
    "sector_housing":         "Housing",
    "sector_msme_industry":   "Micro and Small",
    "sector_large_corporate": "Large",
    "sector_nbfcs":           "Non-Banking Financial Companies (NBFCs)",
    "sector_all_engineering": "All Engineering",
    "sector_gems_jewellery":  "Gems and Jewellery",
    "sector_infrastructure":  "Infrastructure",
    "sector_renewable_energy":"Renewable Energy",
    "sector_psl_housing":     "Housing (Including Priority Sector Housing)",
    "sector_export_credit":   "Export Credit",
}


def compute_yoy_from_csv(csv_path: str, curr_date: str, prev_year_month: str) -> dict:
    """
    Compute YoY % for each node in NODE_TO_CSV_SECTOR.
    curr_date: exact date string in CSV (e.g. '2026-02-28')
    prev_year_month: YYYY-MM prefix (e.g. '2025-02') — uses latest available date
                     per sector within that month (handles sectors on different dates)

    Returns: {node_id: {"yoy_pct": float, "fmt": "+X.Y% YoY", "outstanding_lcr": float}}
    """
    try:
        import pandas as pd
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"  ⚠  Could not load CSV for YoY: {e}")
        return {}

    # Build per-sector prior-year lookup: latest value in the prev_year_month
    prev_month_data = df[df["date"].str.startswith(prev_year_month)]
    if prev_month_data.empty:
        print(f"  ⚠  No prior-year data found for {prev_year_month} in CSV")
        return {}
    # Keep latest date per sector (some sectors appear on multiple dates within month)
    prev_rows = (
        prev_month_data.sort_values("date")
        .groupby("sector")["outstanding_cr"]
        .last()
    )
    curr_rows = df[df["date"] == curr_date].set_index("sector")["outstanding_cr"]

    result = {}
    for node_id, csv_name in NODE_TO_CSV_SECTOR.items():
        curr_val = curr_rows.get(csv_name)
        prev_val = prev_rows.get(csv_name)
        if curr_val is None or prev_val is None or prev_val == 0:
            continue
        yoy = (curr_val - prev_val) / prev_val * 100
        sign = "+" if yoy >= 0 else ""
        result[node_id] = {
            "yoy_pct": yoy,
            "fmt": f"{sign}{yoy:.1f}% YoY",
            "outstanding_lcr": round(curr_val / 100000, 2),  # crores → L Cr
        }
    return result


# ── Tier colour palette ───────────────────────────────────────────────────────

TIER_COLOR = {
    "driver":      {"bg": "#1E3A5F", "fg": "#ffffff", "accent": "#7eb8e8"},
    "sector":      {"bg": "#F0FDF4", "fg": "#166534", "accent": "#166534"},
    "gap":         {"bg": "#F9FAFB", "fg": "#374151", "accent": "#6B7280"},
    "opportunity": {"bg": "#0F766E", "fg": "#ffffff", "accent": "#5eead4"},
    "pressure":    {"bg": "#FEF3C7", "fg": "#92400E", "accent": "#B45309"},
}

OUTCOME_BORDER = {
    "opportunity": "#0F766E",
    "pressure":    "#B45309",
    "gap":         "#6B7280",
}

OUTCOME_STAT_COLOR = {
    "opportunity": "#0F766E",
    "pressure":    "#B45309",
    "gap":         "#6B7280",
}

OUTCOME_TEXT_COLOR = {
    "opportunity": "#2c1e0f",
    "pressure":    "#92400E",
    "gap":         "#374151",
}


# ── Annotation parser ─────────────────────────────────────────────────────────

def parse_growth_pct(stat_str):
    """Extract numeric growth rate from stat string. '+128.8% YoY' → 128.8"""
    if not stat_str:
        return None
    m = re.search(r"([+-]?\d+\.?\d*)\s*%", stat_str)
    return float(m.group(1)) if m else None


def parse_annotations(ts_path):
    """
    Parse all annotation objects from a TypeScript annotations file.
    Returns: {annotation_id: {id, title, body, implication, type}}

    Handles multi-line string concatenation:
        body: "Part one. " +
              "Part two.",
    """
    with open(ts_path, encoding="utf-8") as f:
        lines = f.readlines()

    result = {}
    current = None
    in_field = None
    field_parts = []
    current_type = "insight"

    type_map = {
        "insights":      "insight",
        "gaps":          "gap",
        "opportunities": "opportunity",
    }

    for raw in lines:
        stripped = raw.strip()

        for marker, typ in type_map.items():
            if re.match(rf"^\s*{marker}:\s*\[", raw):
                current_type = typ
                break

        if in_field is not None:
            m = re.match(r'^\s*"([^"]*)"', stripped)
            if m:
                field_parts.append(m.group(1))
                if not stripped.rstrip().endswith("+"):
                    current[in_field] = "".join(field_parts)
                    in_field = None
                    field_parts = []
                continue
            else:
                current[in_field] = "".join(field_parts)
                in_field = None
                field_parts = []

        m = re.match(r'^id:\s+"([^"]+)"', stripped)
        if m:
            if current and "id" in current:
                result[current["id"]] = current
            current = {"id": m.group(1), "type": current_type}
            continue

        if current is None:
            continue

        for field in ["title", "preferredMode"]:
            m = re.match(rf'^{field}:\s+"([^"]+)"', stripped)
            if m:
                current[field] = m.group(1)
                break

        for field in ["body", "implication"]:
            m = re.match(rf'^{field}:\s+"([^"]*)"', stripped)
            if m:
                in_field = field
                field_parts = [m.group(1)]
                if not stripped.rstrip().endswith("+"):
                    current[field] = m.group(1)
                    in_field = None
                    field_parts = []
                break

    if current and "id" in current:
        if in_field and field_parts:
            current[in_field] = "".join(field_parts)
        result[current["id"]] = current

    return result


# ── System model helpers ──────────────────────────────────────────────────────

def real_nodes(model):
    return [n for n in model.get("nodes", []) if "id" in n]


def nodes_by_tier(model):
    tiers = {}
    for n in real_nodes(model):
        tiers.setdefault(n.get("tier"), []).append(n)
    return tiers


def node_primary_annotation(node, annotations):
    """Return first annotation for this node that has body text."""
    for aid in node.get("annotation_ids", []):
        ann = annotations.get(aid)
        if ann and ann.get("body"):
            return ann
    return None


def find_best_node_for_annotation(aid, tiers):
    """Find the most informative node for a given annotation ID.
    Preference: sector node with stat > any node with stat > any node.
    """
    candidates = []
    for nodes in tiers.values():
        for node in nodes:
            if aid in node.get("annotation_ids", []):
                candidates.append(node)
    for node in candidates:
        if node.get("tier") == "sector" and node.get("stat"):
            return node
    for node in candidates:
        if node.get("stat"):
            return node
    return candidates[0] if candidates else {}


# ── HTML primitives ───────────────────────────────────────────────────────────

def divider():
    return '<hr style="border:none;border-top:1px solid #e2d9c5;margin:36px 0">'


def section_heading(emoji, title, color, border):
    return (
        f'<h2 style="font-family:system-ui,sans-serif;font-size:0.82em;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:2px;color:{color};'
        f'border-bottom:2px solid {border};padding-bottom:10px;margin:40px 0 20px">'
        f'{emoji}&nbsp; {title}</h2>'
    )


def image_placeholder(title, filename, description):
    """Dashed box standing in for a PNG the user will manually export and insert."""
    return (
        f'<div style="margin:24px 0;padding:24px;background:#f4f0e8;'
        f'border:2px dashed #c9a96e;text-align:center;border-radius:3px">'
        f'<div style="font-size:1.4em;margin-bottom:8px">🖼</div>'
        f'<div style="font-family:system-ui,sans-serif;font-weight:700;'
        f'color:#7a5c30;margin-bottom:4px">{title}</div>'
        f'<div style="font-family:system-ui,sans-serif;font-size:0.82em;'
        f'color:#9a7c55;margin-bottom:10px">{description}</div>'
        f'<code style="font-family:monospace;font-size:0.78em;background:#e8ddc8;'
        f'padding:3px 10px;color:#5c4a2a;border-radius:2px">Insert: {filename}</code>'
        f'</div>'
    )


def callout_box(stat, title, body, note, tier="opportunity"):
    c = TIER_COLOR.get(tier, TIER_COLOR["opportunity"])
    bg, fg, accent = c["bg"], c["fg"], c["accent"]
    note_style = (
        f'color:{accent};font-style:italic;font-size:0.88em;'
        f'margin:12px 0 0;line-height:1.55;opacity:0.9'
    )
    return (
        f'<div style="margin:20px 0;padding:28px 32px;background:{bg};border-radius:2px">'
        f'<div style="font-family:system-ui,sans-serif;font-size:2.2em;font-weight:800;'
        f'color:{fg};line-height:1;margin-bottom:8px">{stat}</div>'
        f'<div style="font-family:system-ui,sans-serif;font-size:1em;font-weight:600;'
        f'color:{fg};margin-bottom:12px">{title}</div>'
        f'<p style="color:{fg};margin:0;line-height:1.75;opacity:0.92">{body}</p>'
        + (f'<p style="{note_style}">{note}</p>' if note else '')
        + '</div>'
    )


def side_card(stat, label, description, implication, border_color, stat_color,
              text_color="#2c1e0f"):
    stat_html = (
        f'<div style="font-family:system-ui,sans-serif;font-weight:700;'
        f'color:{stat_color};font-size:0.83em;margin-bottom:4px">{stat}</div>'
    ) if stat else ""
    impl_html = (
        f'<p style="margin:8px 0 0;color:#7a5c30;font-style:italic;'
        f'font-size:0.85em;line-height:1.5">{implication}</p>'
    ) if implication else ""
    return (
        f'<div style="margin:14px 0;padding:18px 22px;'
        f'border-left:3px solid {border_color};background:#fffcf5">'
        f'{stat_html}'
        f'<div style="font-family:system-ui,sans-serif;font-weight:600;'
        f'color:{text_color};margin-bottom:6px">{label}</div>'
        f'<p style="margin:0;color:#4b3a2a;font-size:0.9em;line-height:1.6">'
        f'{description}</p>'
        f'{impl_html}'
        f'</div>'
    )


# ── Section builders ──────────────────────────────────────────────────────────

def build_header(cfg, meta):
    brand  = cfg.get("branding", {})
    edit   = cfg.get("editorial", {})
    period = meta.get("period", "")
    issue  = cfg["_meta"].get("issue_number", 1)
    pub    = cfg["_meta"].get("published", "")
    title  = edit.get("issue_title", period)
    author = brand.get("author", "India Credit Lens")
    return (
        f'<div style="padding:36px 40px 0">'
        f'<div style="font-family:system-ui,sans-serif;font-size:10px;'
        f'text-transform:uppercase;letter-spacing:3px;color:#b45309;margin-bottom:12px">'
        f'India Credit Lens &nbsp;·&nbsp; Issue #{issue} &nbsp;·&nbsp; {pub}</div>'
        f'<h1 style="font-size:2em;margin:0 0 6px;color:#1a0f00;line-height:1.2">'
        f'{period}: {title}</h1>'
        f'<div style="color:#7a5c30;font-size:0.9em">'
        f'RBI Sector/Industry-wise Bank Credit &nbsp;·&nbsp; by {author}</div>'
        f'</div>'
    )


def build_hook(meta):
    total  = meta.get("total_credit_lcr", "")
    growth = meta.get("yoy_growth_pct", "")
    period = meta.get("period", "")
    return (
        f'<div style="margin:28px 0 0;padding:36px 40px;background:#1E3A5F">'
        f'<div style="font-family:system-ui,sans-serif;font-size:3.2em;font-weight:800;'
        f'color:#ffffff;line-height:1">₹{total}L Cr</div>'
        f'<div style="font-family:system-ui,sans-serif;color:#a0b8d4;'
        f'font-size:0.9em;margin:6px 0 16px">Total bank credit outstanding · {period}</div>'
        f'<div style="color:#ffffff;font-size:1em;line-height:1.65;'
        f'border-top:1px solid rgba(255,255,255,0.15);padding-top:16px">'
        f'<strong style="color:#7eb8e8">+{growth}% YoY</strong> — fastest growth rate in '
        f'this dataset. ₹25.8L Cr added in 12 months vs ₹18.1L Cr the year before. '
        f'The system is not just growing — it is accelerating.</div>'
        f'</div>'
    )


def build_tldr(editorial):
    bullets = editorial.get("tldr", [])
    items = "".join(
        f'<li style="margin-bottom:9px;line-height:1.65">{b}</li>'
        for b in bullets
    )
    return (
        f'<div style="padding:24px 40px;background:#fffcf5;border-left:4px solid #b45309">'
        f'<div style="font-family:system-ui,sans-serif;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:1.5px;font-size:0.75em;'
        f'color:#b45309;margin-bottom:12px">TL;DR — Four things to know</div>'
        f'<ul style="margin:0;padding-left:20px;color:#2c1e0f;line-height:1.7">'
        f'{items}</ul>'
        f'</div>'
    )


def build_sectors_scoreboard(sector_nodes):
    """All sectors ranked by YoY growth — the scoreboard at a glance."""
    EXCLUDE = {"sector_total_credit"}
    rows = []
    for n in sector_nodes:
        if n["id"] in EXCLUDE:
            continue
        g = parse_growth_pct(n.get("stat"))
        rows.append((n, g if g is not None else -9999))
    rows.sort(key=lambda x: x[1], reverse=True)

    def g_color(g):
        if g is None or g < -50:   return "#6B7280"   # grey — broken series
        if g < 0:                   return "#B45309"   # amber — declining
        if g > 25:                  return "#0F766E"   # teal — high growth
        if g > 14.6:                return "#166534"   # green — above system avg
        return "#374151"                               # below avg

    table_rows = ""
    for node, growth in rows:
        stat  = node.get("stat", "—")
        vol   = f'₹{node["value_lcr"]}L Cr' if node.get("value_lcr") else "—"
        label = node["label"]
        c     = g_color(growth)
        table_rows += (
            f'<tr>'
            f'<td style="padding:8px 12px 8px 0;color:#2c1e0f;font-size:0.87em;'
            f'border-bottom:1px solid #f0e8d8">{label}</td>'
            f'<td style="padding:8px 12px;font-family:system-ui;font-weight:700;'
            f'color:{c};font-size:0.87em;white-space:nowrap;'
            f'border-bottom:1px solid #f0e8d8;text-align:right">{stat}</td>'
            f'<td style="padding:8px 0 8px 12px;color:#7a5c30;font-size:0.82em;'
            f'white-space:nowrap;border-bottom:1px solid #f0e8d8;text-align:right">{vol}</td>'
            f'</tr>'
        )
    th = (
        'font-family:system-ui;font-size:0.72em;font-weight:600;'
        'text-transform:uppercase;letter-spacing:1px;color:#7a5c30;'
        'padding-bottom:8px;border-bottom:2px solid #e2d9c5'
    )
    avg_note = (
        '<p style="font-size:0.76em;color:#9a7c55;margin:8px 0 0;font-style:italic">'
        '<span style="color:#0F766E">■</span> above +25% &nbsp;'
        '<span style="color:#166534">■</span> above system avg (+14.6%) &nbsp;'
        '<span style="color:#374151">■</span> below avg &nbsp;'
        '<span style="color:#B45309">■</span> declining &nbsp;'
        '<span style="color:#6B7280">■</span> broken series'
        '</p>'
    )
    return (
        f'<div style="padding:0 40px">'
        + section_heading("📊", "Where Credit Moved", "#166534", "#166534")
        + f'<table style="width:100%;border-collapse:collapse">'
        + f'<thead><tr>'
        + f'<th style="text-align:left;{th}">Sector</th>'
        + f'<th style="text-align:right;{th}">YoY Growth</th>'
        + f'<th style="text-align:right;{th}">Outstanding</th>'
        + f'</tr></thead>'
        + f'<tbody>{table_rows}</tbody>'
        + f'</table>'
        + avg_note
        + f'</div>'
    )


def build_key_signals(featured_ids, tiers, annotations):
    if not featured_ids:
        return ""
    boxes = ""
    for aid in featured_ids:
        ann = annotations.get(aid)
        if not ann:
            continue
        node  = find_best_node_for_annotation(aid, tiers)
        stat  = node.get("stat", "")
        title = ann.get("title", "")
        body  = ann.get("body", "")
        impl  = ann.get("implication", "")
        tier  = node.get("tier", "opportunity")
        if tier not in TIER_COLOR:
            tier = "opportunity"
        boxes += callout_box(stat, title, body, impl, tier)
    return (
        f'<div style="padding:0 40px">'
        + section_heading("🔎", "Key Signals This Month", "#2c1e0f", "#c9a96e")
        + f'<p style="color:#7a5c30;font-size:0.88em;margin:-12px 0 16px">'
        + f'Three signals selected as most consequential for lenders.</p>'
        + boxes
        + f'</div>'
    )


def build_system_overview(editorial, subsystems):
    """System narrative + overview diagram placeholder + subsystem signposts."""
    narrative = editorial.get("system_narrative", "")
    nl_subs   = [s for s in subsystems if s.get("newsletter")]

    signposts = "".join(
        f'<li style="margin-bottom:8px;line-height:1.6;font-family:system-ui;'
        f'font-size:0.9em">'
        f'<strong style="color:#1E3A5F">{s["label"]}</strong></li>'
        for s in nl_subs
    )

    return (
        f'<div style="padding:0 40px">'
        + section_heading("🗺", "The System This Month", "#1a0f00", "#c9a96e")
        + f'<p style="color:#2c1e0f;line-height:1.85;font-size:1.02em">{narrative}</p>'
        + image_placeholder(
            "SYSTEM OVERVIEW",
            "overview.png",
            f"All {len(subsystems)} causal stories — how they connect"
        )
        + (
            f'<p style="font-family:system-ui;font-size:0.85em;color:#7a5c30;'
            f'margin:20px 0 10px">Three structural stories in this issue:</p>'
            f'<ul style="padding-left:20px;margin:0 0 8px">{signposts}</ul>'
            if nl_subs else ""
        )
        + f'</div>'
    )


def build_subsystem_story(sub, id_to_node, annotations):
    """One causal story block: driver chips + sector stats + diagram + outcome cards."""
    label = sub["label"]

    # Driver chips — compact inline tags
    driver_chips = ""
    for did in sub.get("drivers", []):
        d = id_to_node.get(did)
        if d:
            driver_chips += (
                f'<span style="display:inline-block;background:#1E3A5F;color:#a0b8d4;'
                f'font-family:system-ui,sans-serif;font-size:0.73em;padding:3px 10px;'
                f'border-radius:2px;margin:2px 4px 2px 0">{d["label"]}</span>'
            )

    # Sector stat row — show all sectors with growth colour
    sector_stats = ""
    for sid in sub.get("sectors", []):
        s = id_to_node.get(sid)
        if not s:
            continue
        stat = s.get("stat", "")
        g    = parse_growth_pct(stat)
        if g is None or g < -50:   c = "#6B7280"
        elif g < 0:                 c = "#B45309"
        elif g > 25:                c = "#0F766E"
        elif g > 14.6:              c = "#166534"
        else:                       c = "#374151"
        sector_stats += (
            f'<div style="display:inline-block;margin:4px 20px 4px 0">'
            f'<span style="font-family:system-ui,sans-serif;font-weight:800;'
            f'color:{c};font-size:1.1em">{stat}</span>'
            f'<span style="font-family:system-ui,sans-serif;color:#7a5c30;'
            f'font-size:0.8em;margin-left:6px">{s["label"]}</span>'
            f'</div>'
        )

    # Diagram placeholder — filename matches generate_mermaid.py output convention
    slug       = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")[:30]
    sub_id     = sub.get("id", "sub_xx")
    img_file   = f"{sub_id}_{slug}.png"

    # Outcome nodes: pressure + gap + opportunity — all rendered as side cards
    outcome_cards = ""
    for oid in sub.get("outcomes", []):
        o = id_to_node.get(oid)
        if not o:
            continue
        tier  = o.get("tier", "gap")
        ann   = node_primary_annotation(o, annotations)
        impl  = ann.get("implication", "") if ann else ""
        desc  = o.get("description", "")
        bc    = OUTCOME_BORDER.get(tier, "#6B7280")
        sc    = OUTCOME_STAT_COLOR.get(tier, "#6B7280")
        tc    = OUTCOME_TEXT_COLOR.get(tier, "#374151")
        outcome_cards += side_card(o.get("stat", ""), o["label"], desc, impl, bc, sc, tc)

    return (
        f'<div style="padding:0 40px;margin-top:32px">'
        f'<h3 style="font-family:system-ui,sans-serif;font-size:1.05em;font-weight:700;'
        f'color:#1a0f00;border-left:3px solid #1E3A5F;padding-left:14px;margin:0 0 14px">'
        f'{label}</h3>'
        + (
            f'<div style="margin-bottom:14px">{driver_chips}</div>'
            if driver_chips else ""
        )
        + (
            f'<div style="padding:14px 0;border-top:1px solid #f0e8d8;'
            f'border-bottom:1px solid #f0e8d8;margin-bottom:4px">{sector_stats}</div>'
            if sector_stats else ""
        )
        + image_placeholder(label.upper(), img_file, f"Causal diagram: {label}")
        + outcome_cards
        + f'</div>'
    )


def build_subsystem_stories(subsystems, model, annotations):
    """Render one story block per newsletter-flagged subsystem."""
    nl_subs    = [s for s in subsystems if s.get("newsletter")]
    id_to_node = {n["id"]: n for n in real_nodes(model)}

    if not nl_subs:
        return ""

    blocks = "".join(
        build_subsystem_story(sub, id_to_node, annotations)
        for sub in nl_subs
    )
    return (
        f'<div style="padding:0 40px">'
        + section_heading("📖", "The Three Stories", "#1a0f00", "#1E3A5F")
        + f'<p style="color:#7a5c30;font-size:0.88em;margin:-12px 0 4px">'
        + f'Each story names the force, shows where credit moved, '
        + f'and flags what to watch.</p>'
        + f'</div>'
        + blocks
    )


def build_what_to_watch(editorial):
    watch    = editorial.get("what_to_watch", {})
    next_rel = watch.get("next_release", "")
    items = "".join(
        f'<li style="margin-bottom:10px;color:#2c1e0f;line-height:1.65">{b}</li>'
        for b in watch.get("bullets", [])
    )
    return (
        f'<div style="padding:0 40px">'
        + section_heading("📅", "What to Watch Next", "#2c1e0f", "#e2d9c5")
        + f'<p style="color:#7a5c30;font-size:0.88em;margin:-12px 0 16px">'
        + f'Next release: <strong>{next_rel}</strong></p>'
        + f'<ul style="padding-left:20px;margin:0;line-height:1.8">{items}</ul>'
        + f'</div>'
    )


def _delta_image(image_url: str, subsystem_id: str, signal: str) -> str:
    """Option B: render <img> if image_url is set, else dashed placeholder."""
    if image_url:
        return (
            f'<div style="margin:16px 0;text-align:center">'
            f'<img src="{image_url}" alt="{signal}" '
            f'style="max-width:100%;border-radius:2px;border:1px solid #e2d9c5">'
            f'</div>'
        )
    slug = re.sub(r"[^a-z0-9]+", "_", signal.lower()).strip("_")[:30]
    return image_placeholder(
        signal.upper()[:40],
        f"{subsystem_id}_{slug}.png",
        "Causal diagram — export from mermaid.live and insert here",
    )


def _badge_pill(badge_text: str, color: str, bg: str) -> str:
    return (
        f'<div style="display:inline-block;background:{bg};color:{color};'
        f'font-family:system-ui,sans-serif;font-size:0.68em;font-weight:700;'
        f'letter-spacing:0.8px;padding:4px 12px;border-radius:12px;margin-bottom:10px">'
        f'{badge_text}</div>'
    )


def build_delta_dominant_forces(what_held: list) -> str:
    """THE DOMINANT FORCES — structural signals confirmed across multiple data points."""
    if not what_held:
        return ""

    cards = ""
    for item in what_held:
        signal    = item.get("signal", "")
        badge     = item.get("badge", "▲ Confirmed this month")
        prev_stat = item.get("prev_stat", "")
        curr_stat = item.get("curr_stat", "")
        note      = item.get("note", "")
        image_url = item.get("image_url", "")
        sub_id    = item.get("subsystem_id", "")

        cards += (
            f'<div style="margin:20px 0;padding:24px 28px;background:#F0FDF4;'
            f'border-left:3px solid #166534;border-radius:0 2px 2px 0">'
            + _badge_pill(badge, "#166534", "#dcfce7")
            + f'<div style="font-family:system-ui,sans-serif;font-weight:700;'
            f'color:#14532d;font-size:1em;margin-bottom:14px;line-height:1.4">{signal}</div>'
            f'<div style="display:flex;gap:24px;margin-bottom:16px;flex-wrap:wrap;'
            f'padding:14px;background:rgba(255,255,255,0.6);border-radius:2px">'
            f'<div style="flex:1;min-width:160px">'
            f'<div style="font-size:0.7em;color:#166534;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:1px;margin-bottom:4px">Last issue</div>'
            f'<div style="font-size:0.85em;color:#374151;line-height:1.5">{prev_stat}</div></div>'
            f'<div style="flex:1;min-width:160px">'
            f'<div style="font-size:0.7em;color:#166534;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:1px;margin-bottom:4px">Now (merged)</div>'
            f'<div style="font-size:0.85em;color:#14532d;font-weight:600;line-height:1.5">'
            f'{curr_stat}</div></div></div>'
            + (f'<p style="margin:0;color:#374151;font-size:0.9em;line-height:1.75">'
               f'{note}</p>' if note else '')
            + (_delta_image(image_url, sub_id, signal) if (image_url or sub_id) else '')
            + f'</div>'
        )

    return (
        f'<div style="padding:0 40px">'
        + section_heading("▲", "The Dominant Forces", "#14532d", "#166534")
        + f'<p style="color:#7a5c30;font-size:0.88em;margin:-12px 0 20px">'
        f'Three structural forces shaping Indian credit — confirmed across multiple data points.</p>'
        + cards
        + f'</div>'
    )


def build_delta_one_correction(what_changed: list) -> str:
    """ONE CORRECTION — signals where the interpretation materially updated."""
    if not what_changed:
        return ""

    cards = ""
    for item in what_changed:
        signal      = item.get("signal", "")
        badge       = item.get("badge", "⟳ Updated read")
        prev_read   = item.get("prev_read", "")
        curr_read   = item.get("curr_read", "")
        implication = item.get("implication", "")
        image_url   = item.get("image_url", "")
        sub_id      = item.get("subsystem_id", "")

        cards += (
            f'<div style="margin:20px 0;padding:24px 28px;background:#FEF3C7;'
            f'border-left:3px solid #B45309;border-radius:0 2px 2px 0">'
            + _badge_pill(badge, "#92400E", "#fde68a")
            + f'<div style="font-family:system-ui,sans-serif;font-weight:700;'
            f'color:#92400E;font-size:1em;margin-bottom:16px;line-height:1.4">{signal}</div>'
            f'<div style="margin-bottom:14px;padding:12px 16px;background:rgba(255,255,255,0.5);'
            f'border-radius:2px">'
            f'<div style="font-size:0.7em;color:#B45309;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">What it looked like</div>'
            f'<p style="margin:0;color:#78350f;font-size:0.88em;line-height:1.65;'
            f'font-style:italic">{prev_read}</p></div>'
            f'<div style="margin-bottom:14px;padding:12px 16px;background:#fff7ed;'
            f'border-radius:2px">'
            f'<div style="font-size:0.7em;color:#B45309;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">What it actually is</div>'
            f'<p style="margin:0;color:#92400E;font-size:0.88em;line-height:1.65;'
            f'font-weight:600">{curr_read}</p></div>'
            + (f'<p style="margin:0;color:#78350f;font-size:0.88em;line-height:1.7;'
               f'border-top:1px solid rgba(180,83,9,0.15);padding-top:12px">'
               f'<strong>Implication:</strong> {implication}</p>' if implication else '')
            + (_delta_image(image_url, sub_id, signal) if (image_url or sub_id) else '')
            + f'</div>'
        )

    return (
        f'<div style="padding:0 40px">'
        + section_heading("⟳", "One Correction", "#92400E", "#B45309")
        + f'<p style="color:#7a5c30;font-size:0.88em;margin:-12px 0 20px">'
        f'A number in the headlines this month that is not what it looks like — '
        f'and what it actually means.</p>'
        + cards
        + f'</div>'
    )


def build_delta_series_reveals(what_new: list) -> str:
    """WHAT THE SERIES REVEALS — signals only visible across multiple periods."""
    if not what_new:
        return ""

    cards = ""
    for item in what_new:
        signal      = item.get("signal", "")
        badge       = item.get("badge", "★ Only visible across time")
        stat        = item.get("stat", "")
        body        = item.get("body", "")
        implication = item.get("implication", "")
        image_url   = item.get("image_url", "")
        sub_id      = item.get("subsystem_id", "")

        cards += (
            f'<div style="margin:20px 0;padding:24px 28px;background:#1E3A5F;'
            f'border-radius:2px">'
            + _badge_pill(badge, "#7eb8e8", "#162d4a")
            + f'<div style="font-family:system-ui,sans-serif;font-size:2em;font-weight:800;'
            f'color:#ffffff;line-height:1;margin-bottom:10px">{stat}</div>'
            f'<div style="font-family:system-ui,sans-serif;font-weight:600;'
            f'color:#a0b8d4;font-size:0.92em;margin-bottom:16px;line-height:1.4">{signal}</div>'
            f'<p style="margin:0 0 14px;color:#e2eaf5;font-size:0.9em;line-height:1.8">'
            f'{body}</p>'
            + (f'<p style="margin:0;color:#7eb8e8;font-style:italic;font-size:0.86em;'
               f'line-height:1.65;border-top:1px solid rgba(126,184,232,0.2);padding-top:12px">'
               f'{implication}</p>' if implication else '')
            + (_delta_image(image_url, sub_id, signal) if (image_url or sub_id) else '')
            + f'</div>'
        )

    return (
        f'<div style="padding:0 40px">'
        + section_heading("★", "What the Series Reveals", "#1E3A5F", "#1E3A5F")
        + f'<p style="color:#7a5c30;font-size:0.88em;margin:-12px 0 20px">'
        f'Two signals that require connecting multiple months of data — '
        f'invisible in any single RBI publication.</p>'
        + cards
        + f'</div>'
    )


# ── Signal registry ───────────────────────────────────────────────────────────

_REGISTRY_STATUS_ICON = {
    "confirmed": "✅",
    "stronger":  "↗",
    "unchanged": "↔",
    "weakening": "↘",
    "refuted":   "❌",
    "new":       "★",
}


def load_signal_registry(registry_path):
    """Load signal_registry.json from path relative to CWD or absolute."""
    import os
    path = Path(registry_path) if not os.path.isabs(registry_path) \
        else Path(registry_path)
    if not path.exists():
        # Try relative to this script's directory
        alt = Path(__file__).parent / registry_path
        if alt.exists():
            path = alt
        else:
            print(f"  ⚠  signal_registry.json not found at {registry_path}")
            return None
    with open(path) as f:
        return json.load(f)


def _registry_prior_signals_html(registry, current_issue):
    """Render the Prior Signals section from the cumulative registry.

    Shows every signal introduced before the current issue, with:
    - Status icon from the latest history entry
    - Current story arc name
    - Latest stat
    - Link to introducing issue + link to latest update (if different)
    """
    if not registry:
        return ""

    signals = [
        s for s in registry.get("signals", [])
        if s.get("introduced_issue", 0) < current_issue
    ]
    if not signals:
        return ""

    rows = []
    for sig in signals:
        history = sig.get("history", [])
        if not history:
            continue
        latest   = history[-1]
        status   = latest.get("status", "confirmed")
        icon     = _REGISTRY_STATUS_ICON.get(status, "•")
        arc      = latest.get("story_arc") or sig.get("story_arc", "")
        stat     = latest.get("stat", "")
        intro_n  = sig.get("introduced_issue", "?")
        intro_url = sig.get("introduced_url", "#")
        latest_n = latest.get("issue", intro_n)
        latest_url = latest.get("url", intro_url)

        # Link to introducing issue; if latest update is in a different issue also link that
        if latest_n != intro_n:
            links = (
                f'<a href="{intro_url}">Issue #{intro_n}</a>'
                f' · <a href="{latest_url}">Updated #{latest_n}</a>'
            )
        else:
            links = f'<a href="{intro_url}">Issue #{intro_n}</a>'

        rows.append(
            f'<li>{icon} <strong>{arc}</strong>'
            + (f' — {stat}' if stat else '')
            + f' — {links}</li>'
        )

    return (
        '<hr>'
        '<h2>📋 Signal Tracker — All Prior Issues</h2>'
        '<p><em>Every signal we have published, with current status. '
        'Follow the links for the original analysis.</em></p>'
        '<ul>' + ''.join(rows) + '</ul>'
    )


def _registry_prior_signals_md(registry, current_issue):
    """Markdown version of the prior signals tracker from registry."""
    if not registry:
        return []

    signals = [
        s for s in registry.get("signals", [])
        if s.get("introduced_issue", 0) < current_issue
    ]
    if not signals:
        return []

    lines = [
        "## 📋 Signal Tracker — All Prior Issues", "",
        "*Every signal we have published, with current status. "
        "Follow the links for the original analysis.*", "",
    ]
    for sig in signals:
        history = sig.get("history", [])
        if not history:
            continue
        latest    = history[-1]
        status    = latest.get("status", "confirmed")
        icon      = _REGISTRY_STATUS_ICON.get(status, "•")
        arc       = latest.get("story_arc") or sig.get("story_arc", "")
        stat      = latest.get("stat", "")
        intro_n   = sig.get("introduced_issue", "?")
        intro_url = sig.get("introduced_url", "#")
        latest_n  = latest.get("issue", intro_n)
        latest_url = latest.get("url", intro_url)

        if latest_n != intro_n:
            links = (
                f"[Issue #{intro_n}]({intro_url})"
                f" · [Updated #{latest_n}]({latest_url})"
            )
        else:
            links = f"[Issue #{intro_n}]({intro_url})"

        lines.append(
            f"- {icon} **{arc}**"
            + (f" — {stat}" if stat else "")
            + f" — {links}"
        )
    lines += ["", "---", ""]
    return lines


# ── delta_v2 builders ─────────────────────────────────────────────────────────

def _source_entries_for_sub(subsystem_id, subsystems, id_to_node):
    """Return deduplicated list of (label, url) for inference/data nodes in a subsystem."""
    sub = next((s for s in subsystems if s.get("id") == subsystem_id), None)
    if not sub:
        return []
    seen_urls = set()
    entries = []
    for nid in sub.get("node_ids", []):
        n = id_to_node.get(nid)
        if not n:
            continue
        ct  = n.get("claim_type", "")
        src = n.get("source", "").strip()
        url = n.get("source_url", "").strip()
        if ct not in ("inference", "data") or not src:
            continue
        # Deduplicate by URL (same circular cited by multiple nodes)
        key = url or src
        if key in seen_urls:
            continue
        seen_urls.add(key)
        # Shorten source label: take up to first semicolon or 90 chars
        short = src.split(";")[0].split(",")[0].strip()
        if len(short) > 90:
            short = short[:87] + "…"
        entries.append((short, url))
    return entries


def _sources_block_html(subsystem_id, subsystems, id_to_node):
    """Render a compact sources footnote block for a signal card (HTML)."""
    entries = _source_entries_for_sub(subsystem_id, subsystems, id_to_node)
    if not entries:
        return ""
    rows = ""
    for label, url in entries:
        if url:
            rows += (
                f'<div style="margin-bottom:3px">'
                f'<span style="color:#6b7280">↗</span> '
                f'<a href="{url}" style="color:#4b5563;text-decoration:underline;'
                f'text-underline-offset:2px">{label}</a>'
                f'</div>'
            )
        else:
            rows += (
                f'<div style="margin-bottom:3px">'
                f'<span style="color:#6b7280">↗ {label}</span>'
                f'</div>'
            )
    return (
        f'<div style="margin-top:16px;padding:12px 16px;'
        f'background:#f9fafb;border-radius:2px;border-top:1px solid #e5e7eb">'
        f'<div style="font-family:system-ui,sans-serif;font-size:0.68em;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.8px;color:#9ca3af;margin-bottom:6px">'
        f'Sources</div>'
        f'<div style="font-family:system-ui,sans-serif;font-size:0.75em;line-height:1.6;color:#6b7280">'
        + rows
        + f'</div></div>'
    )


def _sources_block_substack(subsystem_id, subsystems, id_to_node):
    """Render sources footnote for Substack (plain HTML, no inline styles needed)."""
    entries = _source_entries_for_sub(subsystem_id, subsystems, id_to_node)
    if not entries:
        return ""
    lines = ["<p><em>Sources:</em></p><ul>"]
    for label, url in entries:
        if url:
            lines.append(f'<li><a href="{url}">{label}</a></li>')
        else:
            lines.append(f'<li>{label}</li>')
    lines.append("</ul>")
    return "\n".join(lines)


def _hypothesis_nodes_for_sub(subsystem_id, subsystems, id_to_node):
    """Return list of hypothesis nodes linked to a subsystem (any node_ids field).

    Only driver/pressure/gap tier nodes are included — opportunity nodes with
    claim_type="hypothesis" belong in the opportunity block, not the disclaimer
    note.  Mixing them produces confusing combined labels like
    "NBFC credit recovery; EV-specific vehicle credit products" on an NBFC card.
    """
    sub = next((s for s in subsystems if s.get("id") == subsystem_id), None)
    if not sub:
        return []
    all_ids = sub.get("node_ids", [])
    return [
        id_to_node[nid] for nid in all_ids
        if nid in id_to_node
        and id_to_node[nid].get("claim_type") == "hypothesis"
        and id_to_node[nid].get("tier") != "opportunity"   # opportunities rendered separately
    ]


def _hypothesis_note_html(subsystem_id, subsystems, id_to_node):
    """Amber inline note listing hypothesis nodes for a signal card (HTML)."""
    nodes = _hypothesis_nodes_for_sub(subsystem_id, subsystems, id_to_node)
    if not nodes:
        return ""
    labels = "; ".join(n["label"] for n in nodes)
    return (
        f'<div style="margin-top:14px;padding:10px 14px;'
        f'background:#fffbeb;border-left:3px solid #d97706;border-radius:0 2px 2px 0">'
        f'<span style="font-family:system-ui,sans-serif;font-size:0.75em;font-weight:700;'
        f'color:#92400e;text-transform:uppercase;letter-spacing:0.8px">⚠ Working hypothesis</span>'
        f'<p style="margin:4px 0 0;font-family:system-ui,sans-serif;font-size:0.78em;'
        f'color:#78350f;line-height:1.55">'
        f'{labels} — mechanism inferred from data pattern; not yet independently sourced.</p>'
        f'</div>'
    )


def _hypothesis_note_substack(subsystem_id, subsystems, id_to_node):
    """Plain-text hypothesis note for Substack signal blocks."""
    nodes = _hypothesis_nodes_for_sub(subsystem_id, subsystems, id_to_node)
    if not nodes:
        return ""
    labels = "; ".join(n["label"] for n in nodes)
    return f'<p><em>⚠ Working hypothesis: {labels} — mechanism inferred from data pattern, not independently sourced.</em></p>'


def _d2_outcomes(subsystem_id, subsystems, id_to_node, annotations, prior_opp_ids=None):
    """Return rendered outcome cards (✅/⚠️/🔍) for a subsystem.

    prior_opp_ids: set of outcome node IDs already published in a prior issue.
    Those are silently skipped to prevent cross-issue repetition.
    """
    prior_opp_ids = prior_opp_ids or set()
    sub = next((s for s in subsystems if s.get("id") == subsystem_id), None)
    if not sub:
        return ""
    cards = ""
    for oid in sub.get("outcomes", []):
        if oid in prior_opp_ids:
            continue   # already featured in a prior issue — do not repeat
        o = id_to_node.get(oid)
        if not o:
            continue
        tier = o.get("tier", "gap")
        icon = {"opportunity": "✅", "pressure": "⚠️", "gap": "🔍"}.get(tier, "•")
        bc   = OUTCOME_BORDER.get(tier, "#6B7280")
        sc   = OUTCOME_STAT_COLOR.get(tier, "#6B7280")
        tc   = OUTCOME_TEXT_COLOR.get(tier, "#374151")
        ann  = node_primary_annotation(o, annotations)
        impl = ann.get("implication", "") if ann else ""
        desc = o.get("description", "")
        label_with_icon = f"{icon} {o['label']}"
        cards += side_card(o.get("stat", ""), label_with_icon, desc, impl, bc, sc, tc)
    return cards


def _d2_outcomes_md(subsystem_id, subsystems, id_to_node, annotations, prior_opp_ids=None):
    """Return outcome lines for markdown output.

    prior_opp_ids: set of outcome node IDs already published in a prior issue.
    """
    prior_opp_ids = prior_opp_ids or set()
    sub = next((s for s in subsystems if s.get("id") == subsystem_id), None)
    if not sub:
        return []
    lines = []
    for oid in sub.get("outcomes", []):
        if oid in prior_opp_ids:
            continue   # already featured in a prior issue — do not repeat
        o = id_to_node.get(oid)
        if not o:
            continue
        tier = o.get("tier", "gap")
        icon = {"opportunity": "✅", "pressure": "⚠️", "gap": "🔍"}.get(tier, "•")
        ann  = node_primary_annotation(o, annotations)
        impl = ann.get("implication", "") if ann else ""
        lines += [f"{icon} **{o['label']}**", o.get("description", "")]
        if impl:
            lines.append(f"*{impl}*")
        lines.append("")
    return lines


def _d2_diagram_html(item):
    """Render diagram img or placeholder for HTML output.
    If mermaid_file is explicitly null (None), no diagram or placeholder is shown."""
    image_url   = item.get("image_url", "")
    sub_id      = item.get("subsystem_id", "")
    signal      = item.get("signal", "")
    mermaid_file = item.get("mermaid_file")   # None = explicitly no diagram
    if image_url:
        return (
            f'<div style="margin:20px 0;text-align:center">'
            f'<img src="{image_url}" alt="{signal}" '
            f'style="max-width:100%;border-radius:2px;border:1px solid #e2d9c5">'
            f'</div>'
        )
    if sub_id and mermaid_file is not None:
        # mermaid_file set (even empty string) → show placeholder
        slug = re.sub(r"[^a-z0-9]+", "_", signal.lower()).strip("_")[:30]
        return image_placeholder(signal.upper()[:40], f"{sub_id}_{slug}.png",
                                 "Causal diagram — auto-rendered via mmdc")
    return ""   # mermaid_file=null → no diagram, no placeholder


def _d2_diagram_substack(item):
    """Return image tag or placeholder for Substack output.
    If mermaid_file is explicitly null, returns empty string."""
    mermaid_file = item.get("mermaid_file")
    if item.get("image_url"):
        return f'<p><img src="{item["image_url"]}" alt="{item.get("signal","")}" style="max-width:100%"></p>'
    sub_id = item.get("subsystem_id", "")
    if sub_id and mermaid_file is not None:
        slug = re.sub(r"[^a-z0-9]+", "_", item.get("signal","").lower()).strip("_")[:30]
        return f'<p><em>[Insert image: {sub_id}_{slug}.png]</em></p>'
    return ""


def _d2_signal_new_html(item, subsystems, id_to_node, annotations):
    """★ NEW signal card — dark blue, full diagram, outcome rows."""
    story_arc   = item.get("story_arc", "")
    signal      = item.get("signal", "")
    stat        = item.get("stat", "")
    body        = item.get("body", "")
    implication = item.get("implication", "")
    outcomes    = _d2_outcomes(item.get("subsystem_id",""), subsystems, id_to_node, annotations)

    return (
        f'<div style="margin:28px 0">'
        f'<div style="font-family:system-ui,sans-serif;font-size:0.68em;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:1.5px;color:#7eb8e8;margin-bottom:8px">'
        f'★ New this issue</div>'
        f'<div style="padding:28px 32px;background:#1E3A5F;border-radius:2px">'
        + _badge_pill(f'★ {story_arc}', "#7eb8e8", "#162d4a")
        + (f'<div style="font-family:system-ui,sans-serif;font-size:1.9em;font-weight:800;'
           f'color:#ffffff;line-height:1;margin:10px 0">{stat}</div>' if stat else '')
        + f'<div style="font-family:system-ui,sans-serif;font-weight:600;color:#a0b8d4;'
        f'font-size:0.95em;margin-bottom:16px;line-height:1.4">{signal}</div>'
        f'<p style="margin:0 0 14px;color:#e2eaf5;font-size:0.9em;line-height:1.8">{body}</p>'
        + (f'<p style="margin:0;color:#7eb8e8;font-style:italic;font-size:0.86em;'
           f'line-height:1.65;border-top:1px solid rgba(126,184,232,0.2);padding-top:12px">'
           f'{implication}</p>' if implication else '')
        + _hypothesis_note_html(item.get("subsystem_id",""), subsystems, id_to_node)
        + _sources_block_html(item.get("subsystem_id",""), subsystems, id_to_node)
        + f'</div>'
        + _d2_diagram_html(item)
        + outcomes
        + f'</div>'
    )


def _d2_signal_correction_html(item, subsystems, id_to_node, annotations):
    """⟳ CORRECTION card — amber, diagram, prev/now read."""
    story_arc   = item.get("story_arc", "")
    signal      = item.get("signal", "")
    prev_read   = item.get("prev_read", "")
    curr_read   = item.get("curr_read", "")
    implication = item.get("implication", "")
    outcomes    = _d2_outcomes(item.get("subsystem_id",""), subsystems, id_to_node, annotations)

    return (
        f'<div style="margin:28px 0">'
        f'<div style="font-family:system-ui,sans-serif;font-size:0.68em;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:1.5px;color:#B45309;margin-bottom:8px">'
        f'⟳ Correction from Issue #1</div>'
        f'<div style="padding:24px 28px;background:#FEF3C7;'
        f'border-left:3px solid #B45309;border-radius:0 2px 2px 0">'
        + _badge_pill(f'⟳ {story_arc}', "#92400E", "#fde68a")
        + f'<div style="font-family:system-ui,sans-serif;font-weight:700;'
        f'color:#92400E;font-size:1em;margin-bottom:16px;line-height:1.4">{signal}</div>'
        f'<div style="margin-bottom:12px;padding:12px 16px;background:rgba(255,255,255,0.5);border-radius:2px">'
        f'<div style="font-size:0.7em;color:#B45309;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:1px;margin-bottom:6px">What it looked like</div>'
        f'<p style="margin:0;color:#78350f;font-size:0.88em;line-height:1.65;font-style:italic">{prev_read}</p></div>'
        f'<div style="margin-bottom:12px;padding:12px 16px;background:#fff7ed;border-radius:2px">'
        f'<div style="font-size:0.7em;color:#B45309;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:1px;margin-bottom:6px">What it actually is</div>'
        f'<p style="margin:0;color:#92400E;font-size:0.88em;line-height:1.65;font-weight:600">{curr_read}</p></div>'
        + (f'<p style="margin:0;color:#78350f;font-size:0.88em;line-height:1.7;'
           f'border-top:1px solid rgba(180,83,9,0.15);padding-top:12px">'
           f'<strong>Implication:</strong> {implication}</p>' if implication else '')
        + _hypothesis_note_html(item.get("subsystem_id",""), subsystems, id_to_node)
        + _sources_block_html(item.get("subsystem_id",""), subsystems, id_to_node)
        + f'</div>'
        + _d2_diagram_html(item)
        + outcomes
        + f'</div>'
    )


def _d2_signal_confirmed_html(item, subsystems, id_to_node, prev_issue_url=""):
    """▲ CONFIRMED card — compact green row: badge + stat delta + CTA link only."""
    story_arc      = item.get("story_arc", "")
    signal         = item.get("signal", "")
    badge          = item.get("badge", "▲ Confirmed")
    curr_stat      = item.get("curr_stat", "")
    prev_issue_num = item.get("prev_issue_number", 1)
    cta_url        = prev_issue_url or "#"

    sub_id   = item.get("subsystem_id", "")
    hyp_note = _hypothesis_note_html(sub_id, subsystems, id_to_node)
    src_block = _sources_block_html(sub_id, subsystems, id_to_node)
    return (
        f'<div style="margin:16px 0;background:#F0FDF4;'
        f'border-left:3px solid #166534;border-radius:0 2px 2px 0">'
        f'<div style="padding:16px 20px;display:flex;align-items:flex-start;gap:16px;flex-wrap:wrap">'
        + _badge_pill(badge, "#166534", "#dcfce7")
        + f'<div style="flex:1;min-width:200px">'
        f'<div style="font-family:system-ui,sans-serif;font-weight:700;'
        f'color:#14532d;font-size:0.92em;margin-bottom:4px">{story_arc}</div>'
        f'<div style="font-family:system-ui,sans-serif;font-size:0.82em;'
        f'color:#374151;line-height:1.5">{curr_stat}</div>'
        f'</div>'
        f'<a href="{cta_url}" style="display:inline-block;align-self:center;'
        f'font-family:system-ui,sans-serif;font-size:0.75em;font-weight:600;'
        f'color:#166534;border:1px solid #166534;padding:5px 12px;'
        f'border-radius:2px;text-decoration:none;white-space:nowrap">'
        f'Full analysis → Issue #{prev_issue_num}</a>'
        f'</div>'
        + (f'<div style="padding:0 20px 8px">{hyp_note}</div>' if hyp_note else '')
        + (f'<div style="padding:0 20px 16px">{src_block}</div>' if src_block else '')
        + f'</div>'
    )


def build_d2_signals_html(signals, subsystems, id_to_node, annotations, prev_issue_url=""):
    """Render all signals in editorial order (new → correction → confirmed)."""
    new_blocks       = ""
    correction_blocks = ""
    confirmed_blocks  = ""

    for item in signals:
        t = item.get("type", "")
        if t == "new":
            new_blocks += _d2_signal_new_html(item, subsystems, id_to_node, annotations)
        elif t == "correction":
            correction_blocks += _d2_signal_correction_html(item, subsystems, id_to_node, annotations)
        elif t == "confirmed":
            confirmed_blocks += _d2_signal_confirmed_html(item, subsystems, id_to_node, prev_issue_url)

    # Group confirmed signals under a single sub-heading
    confirmed_section = ""
    if confirmed_blocks:
        confirmed_section = (
            f'<div style="margin-top:36px">'
            f'<div style="font-family:system-ui,sans-serif;font-size:0.72em;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:1.5px;color:#166534;margin-bottom:12px">'
            f'▲ Confirmed from previous issue — full causal analysis in Issue #1</div>'
            + confirmed_blocks
            + f'</div>'
        )

    return (
        f'<div style="padding:0 40px">'
        + section_heading("📡", "The Signals", "#1a0f00", "#c9a96e")
        + new_blocks
        + correction_blocks
        + confirmed_section
        + f'</div>'
    )


def build_d2_scoreboard(period_model, yoy_lookup: dict = None):
    """Where Credit Moved — uses true YoY from CSV where available, falls back to model stat."""
    tiers = nodes_by_tier(period_model)
    EXCLUDE = {"sector_total_credit"}
    yoy_lookup = yoy_lookup or {}

    # Compute system avg YoY from lookup (use total credit if available)
    sys_avg = 13.8   # default
    if "sector_bank_credit" in yoy_lookup:
        sys_avg = round(yoy_lookup["sector_bank_credit"]["yoy_pct"], 1)

    # Build rows: prefer YoY lookup, fall back to model stat
    rows = []
    for n in tiers.get("sector", []):
        if n["id"] in EXCLUDE:
            continue
        nid = n["id"]
        if nid in yoy_lookup:
            yoy_data = yoy_lookup[nid]
            g        = yoy_data["yoy_pct"]
            stat_str = yoy_data["fmt"]
            vol      = f'₹{yoy_data["outstanding_lcr"]}L Cr'
        else:
            g        = parse_growth_pct(n.get("stat"))
            stat_str = n.get("stat", "—")
            vol      = f'₹{n["value_lcr"]}L Cr' if n.get("value_lcr") else "—"
        rows.append((n["label"], stat_str, vol, g))

    rows.sort(key=lambda x: x[3] if x[3] is not None else -9999, reverse=True)

    def g_color(g):
        if g is None or g < -50: return "#6B7280"
        if g < 0:                return "#B45309"
        if g > 25:               return "#0F766E"
        if g > sys_avg:          return "#166534"
        return "#374151"

    table_rows = ""
    for label, stat_str, vol, growth in rows:
        c = g_color(growth)
        table_rows += (
            f'<tr>'
            f'<td style="padding:8px 12px 8px 0;color:#2c1e0f;font-size:0.87em;'
            f'border-bottom:1px solid #f0e8d8">{label}</td>'
            f'<td style="padding:8px 12px;font-family:system-ui;font-weight:700;'
            f'color:{c};font-size:0.87em;white-space:nowrap;'
            f'border-bottom:1px solid #f0e8d8;text-align:right">{stat_str}</td>'
            f'<td style="padding:8px 0 8px 12px;color:#7a5c30;font-size:0.82em;'
            f'white-space:nowrap;border-bottom:1px solid #f0e8d8;text-align:right">{vol}</td>'
            f'</tr>'
        )
    th = ('font-family:system-ui;font-size:0.72em;font-weight:600;'
          'text-transform:uppercase;letter-spacing:1px;color:#7a5c30;'
          'padding-bottom:8px;border-bottom:2px solid #e2d9c5')
    avg_note = (
        f'<p style="font-size:0.76em;color:#9a7c55;margin:8px 0 0;font-style:italic">'
        f'<span style="color:#0F766E">■</span> above +25% &nbsp;'
        f'<span style="color:#166534">■</span> above system avg (+{sys_avg}% YoY) &nbsp;'
        f'<span style="color:#374151">■</span> below avg &nbsp;'
        f'<span style="color:#B45309">■</span> declining</p>'
    )
    return (
        f'<div style="padding:0 40px">'
        + section_heading("📊", "Where Credit Moved", "#166534", "#166534")
        + f'<table style="width:100%;border-collapse:collapse">'
        + f'<thead><tr>'
        + f'<th style="text-align:left;{th}">Sector</th>'
        + f'<th style="text-align:right;{th}">YoY Growth</th>'
        + f'<th style="text-align:right;{th}">Outstanding</th>'
        + f'</tr></thead>'
        + f'<tbody>{table_rows}</tbody>'
        + f'</table>'
        + avg_note
        + f'</div>'
    )


def build_d2_system_section(editorial):
    """System narrative — connecting paragraph, no diagram."""
    narrative = editorial.get("system_narrative", "")
    return (
        f'<div style="padding:0 40px">'
        + section_heading("🗺", "The System This Month", "#1a0f00", "#c9a96e")
        + f'<p style="color:#2c1e0f;line-height:1.85;font-size:1.02em">{narrative}</p>'
        + f'</div>'
    )


def build_delta_v2_html(cfg, model, period_model, subsystems, annotations, yoy_lookup=None):
    edit          = cfg.get("editorial", {})
    meta          = cfg.get("_meta", {})
    issue         = meta.get("issue_number", 2)
    pub           = meta.get("published", "")
    period        = meta.get("period", "")
    brand         = cfg.get("branding", {})
    author        = brand.get("author", "India Credit Lens")
    signals       = edit.get("signals", [])
    prev_issue_url = meta.get("prev_issue_url", "")
    id_to_node    = {n["id"]: n for n in real_nodes(model)}

    header = (
        f'<div style="padding:36px 40px 0">'
        f'<div style="font-family:system-ui,sans-serif;font-size:10px;'
        f'text-transform:uppercase;letter-spacing:3px;color:#b45309;margin-bottom:12px">'
        f'India Credit Lens &nbsp;·&nbsp; Issue #{issue} &nbsp;·&nbsp; {pub}</div>'
        f'<h1 style="font-size:2em;margin:0 0 6px;color:#1a0f00;line-height:1.2">'
        f'{period}: {edit.get("issue_title","")}</h1>'
        f'<div style="color:#7a5c30;font-size:0.9em">'
        f'RBI Sector/Industry-wise Bank Credit &nbsp;·&nbsp; by {author}</div>'
        f'</div>'
    )

    context_text = edit.get("context_strip", "")
    context_strip = (
        f'<div style="margin:24px 40px 0;padding:16px 20px;background:#f4f0e8;'
        f'border-left:3px solid #c9a96e;border-radius:0 2px 2px 0">'
        f'<p style="margin:0;font-family:system-ui,sans-serif;font-size:0.83em;'
        f'color:#7a5c30;line-height:1.7">'
        f'<strong style="color:#5c4a2a">What is this?</strong> {context_text}</p>'
        f'</div>'
    ) if context_text else ""

    hero = (
        f'<div style="margin:28px 0 0;padding:36px 40px;background:#1E3A5F">'
        f'<p style="color:#ffffff;font-size:1.08em;line-height:1.85;margin:0">'
        f'{edit.get("hero_narrative","")}</p>'
        f'</div>'
    )

    tldr_items = "".join(
        f'<li style="margin-bottom:9px;line-height:1.65">{b}</li>'
        for b in edit.get("tldr", [])
    )
    tldr = (
        f'<div style="padding:24px 40px;background:#fffcf5;border-left:4px solid #b45309">'
        f'<div style="font-family:system-ui,sans-serif;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:1.5px;font-size:0.75em;'
        f'color:#b45309;margin-bottom:12px">TL;DR — Four things to know</div>'
        f'<ul style="margin:0;padding-left:20px;color:#2c1e0f;line-height:1.7">'
        f'{tldr_items}</ul>'
        f'</div>'
    ) if edit.get("tldr") else ""

    parts = [
        header, context_strip, hero, tldr,
        divider(),
        build_d2_scoreboard(period_model, yoy_lookup),
        divider(),
        build_d2_system_section(edit),
        divider(),
        build_d2_signals_html(signals, subsystems, id_to_node, annotations, prev_issue_url),
        divider(),
        build_what_to_watch(edit),
        divider(),
        build_cta(cfg),
        build_footer(cfg),
    ]
    return HTML_SHELL.format(title=f"India Credit Lens — {period}", body="\n".join(parts))


def build_delta_v2_substack(cfg, model, period_model, subsystems, annotations, yoy_lookup=None):
    """Clean semantic HTML for Substack paste — delta_v2."""
    edit          = cfg.get("editorial", {})
    meta          = cfg.get("_meta", {})
    issue         = meta.get("issue_number", 2)
    pub           = meta.get("published", "")
    period        = meta.get("period", "")
    brand         = cfg.get("branding", {})
    cta_cfg       = cfg.get("cta", {})
    signals       = edit.get("signals", [])
    watch         = edit.get("what_to_watch", {})
    prev_issue_url = meta.get("prev_issue_url", "#")
    id_to_node    = {n["id"]: n for n in real_nodes(model)}
    yoy_lookup    = yoy_lookup or {}

    # Scoreboard: prefer YoY lookup, fall back to period model stats
    tiers = nodes_by_tier(period_model)
    EXCLUDE = {"sector_total_credit"}
    raw_nodes = [n for n in tiers.get("sector", []) if n["id"] not in EXCLUDE]
    sector_rows = []
    for n in raw_nodes:
        nid = n["id"]
        if nid in yoy_lookup:
            g        = yoy_lookup[nid]["yoy_pct"]
            stat_str = yoy_lookup[nid]["fmt"]
            vol      = f'₹{yoy_lookup[nid]["outstanding_lcr"]}L Cr'
        else:
            g        = parse_growth_pct(n.get("stat"))
            stat_str = n.get("stat", "—")
            vol      = f'₹{n["value_lcr"]}L Cr' if n.get("value_lcr") else "—"
        sector_rows.append((n["label"], stat_str, vol, g))
    sector_rows.sort(key=lambda x: x[3] if x[3] is not None else -9999, reverse=True)

    p = []

    # Header
    p.append(f'<h1>{period}: {edit.get("issue_title","")}</h1>')
    p.append(
        f'<p><em>Issue #{issue} &nbsp;·&nbsp; {pub}'
        f' &nbsp;·&nbsp; by {brand.get("author","India Credit Lens")}'
        f' &nbsp;·&nbsp; <a href="https://{brand.get("site","")}">'
        f'{brand.get("site","")}</a></em></p>'
    )

    ctx = edit.get("context_strip", "")
    if ctx:
        p.append(f'<blockquote><p>{ctx}</p></blockquote>')
    p.append('<hr>')

    # Hero + TL;DR
    p.append(f'<p>{edit.get("hero_narrative","")}</p>')
    if edit.get("tldr"):
        p.append('<h2>TL;DR</h2>')
        p.append('<ul>' + ''.join(f'<li>{b}</li>' for b in edit["tldr"]) + '</ul>')
    p.append('<hr>')

    # Scoreboard
    p.append('<h2>📊 Where Credit Moved</h2>')
    rows_html = "".join(
        f'<tr><td>{label}</td><td><strong>{stat_str}</strong></td><td>{vol}</td></tr>'
        for label, stat_str, vol, _ in sector_rows
    )
    p.append(
        f'<table><thead><tr><th>Sector</th><th>YoY Growth</th>'
        f'<th>Outstanding</th></tr></thead><tbody>{rows_html}</tbody></table>'
    )
    p.append('<hr>')

    # System narrative (no diagram)
    p.append('<h2>🗺 The System This Month</h2>')
    p.append(f'<p>{edit.get("system_narrative","")}</p>')
    p.append('<hr>')

    # ── Signals ────────────────────────────────────────────────────────────────
    # New/correction signals get full treatment.
    # Prior-issue signals (confirmed/unchanged/updated/refuted) are rendered as
    # a compact status list — no body, no hypothesis, no sources.  The reader
    # follows the link to the prior issue for full context.
    # ──────────────────────────────────────────────────────────────────────────
    prior_opp_ids = set(meta.get("prior_published_opportunity_ids", []))

    # Status icon for prior-issue entries derived from item["status"] or badge prefix.
    _PRIOR_STATUS_ICON = {
        "confirmed":  "✅",
        "stronger":   "↗",
        "unchanged":  "↔",
        "weakening":  "↘",
        "refuted":    "❌",
    }

    def _prior_status_icon(item):
        s = item.get("status", "").lower()
        if s in _PRIOR_STATUS_ICON:
            return _PRIOR_STATUS_ICON[s]
        # Fall back to badge prefix if no explicit status field
        badge = item.get("badge", "")
        if badge.startswith("▲") or badge.startswith("✅"): return "✅"
        if badge.startswith("="): return "↔"
        if badge.startswith("↘") or badge.startswith("▼"): return "↘"
        if badge.startswith("❌"): return "❌"
        return "✅"

    NEW_TYPES  = {"new", "correction"}
    PRIOR_TYPES = {"confirmed", "unchanged", "updated", "refuted"}

    new_signals   = [s for s in signals if s.get("type") in NEW_TYPES]
    prior_signals = [s for s in signals if s.get("type") in PRIOR_TYPES]

    # ── Section A: New signals ─────────────────────────────────────────────────
    p.append('<h2>📡 New This Issue</h2>')
    for item in new_signals:
        t          = item.get("type", "")
        story_arc  = item.get("story_arc", "")
        signal     = item.get("signal", "")
        sub_id     = item.get("subsystem_id", "") or ""

        if t == "new":
            p.append(f'<h3>★ {story_arc}</h3>')
            p.append(f'<p><em>New this issue</em></p>')
            if item.get("stat"):
                p.append(f'<p><strong>{item["stat"]}</strong></p>')
            p.append(f'<p>{signal}</p>')
            if item.get("body"):
                p.append(f'<p>{item["body"]}</p>')
            if item.get("implication"):
                p.append(f'<blockquote><p><em>{item["implication"]}</em></p></blockquote>')
            hyp = _hypothesis_note_substack(sub_id, subsystems, id_to_node)
            if hyp: p.append(hyp)
            src = _sources_block_substack(sub_id, subsystems, id_to_node)
            if src: p.append(src)
            p.append(_d2_diagram_substack(item))

        elif t == "correction":
            prev_num = item.get("prev_issue_number", 1)
            p.append(f'<h3>⟳ {story_arc}</h3>')
            p.append(f'<p><em>Correction from Issue #{prev_num}</em></p>')
            p.append(f'<p><strong>{signal}</strong></p>')
            p.append(f'<p><strong>What it looked like:</strong> <em>{item.get("prev_read","")}</em></p>')
            p.append(f'<p><strong>What it actually is:</strong> {item.get("curr_read","")}</p>')
            if item.get("implication"):
                p.append(f'<blockquote><p><strong>Implication:</strong> {item["implication"]}</p></blockquote>')
            hyp = _hypothesis_note_substack(sub_id, subsystems, id_to_node)
            if hyp: p.append(hyp)
            src = _sources_block_substack(sub_id, subsystems, id_to_node)
            if src: p.append(src)
            p.append(_d2_diagram_substack(item))

        # Outcomes: new + correction only, skip prior-issue opportunities
        sub = next((s for s in subsystems if s.get("id") == sub_id), None)
        if sub:
            for oid in sub.get("outcomes", []):
                if oid in prior_opp_ids:
                    continue
                o = id_to_node.get(oid)
                if not o:
                    continue
                tier = o.get("tier", "gap")
                icon = {"opportunity": "✅", "pressure": "⚠️", "gap": "🔍"}.get(tier, "•")
                ann  = node_primary_annotation(o, annotations)
                impl = ann.get("implication", "") if ann else ""
                p.append(
                    f'<blockquote>'
                    f'<p><strong>{icon} {o["label"]}</strong></p>'
                    f'<p>{o.get("description","")}</p>'
                    + (f'<p><em>{impl}</em></p>' if impl else '')
                    + '</blockquote>'
                )

    # ── Section B: Prior signals — registry takes priority, inline list as fallback
    registry_path = meta.get("signal_registry_path", "")
    if registry_path:
        registry = load_signal_registry(registry_path)
        current_issue = meta.get("issue_number", 1)
        reg_html = _registry_prior_signals_html(registry, current_issue)
        if reg_html:
            p.append(reg_html)
    elif prior_signals:
        # Fallback: inline confirmed entries from newsletter_config.json signals list
        p.append('<hr>')
        p.append('<h2>📋 Prior Signals — Status Update</h2>')
        p.append(
            '<p><em>Signals first published in earlier issues. '
            'Status reflects new data in this period. '
            'Follow the link for the original analysis.</em></p>'
        )
        rows = []
        for item in prior_signals:
            icon      = _prior_status_icon(item)
            arc       = item.get("story_arc", "")
            badge     = item.get("badge", "")
            curr_stat = item.get("curr_stat", "")
            prev_num  = item.get("prev_issue_number", 1)
            item_url  = item.get("prev_issue_url", prev_issue_url or "#")
            note_parts = [p_ for p_ in [badge, curr_stat] if p_]
            note = " — ".join(note_parts) if note_parts else ""
            rows.append(
                f'<li>{icon} <strong>{arc}</strong>'
                + (f' — {note}' if note else '')
                + f' <a href="{item_url}">Issue #{prev_num} →</a></li>'
            )
        p.append('<ul>' + ''.join(rows) + '</ul>')

    p.append('<hr>')

    # What to Watch
    p.append('<h2>📅 What to Watch Next</h2>')
    p.append(f'<p><em>Next release: {watch.get("next_release","")}</em></p>')
    p.append('<ul>' + ''.join(f'<li>{b}</li>' for b in watch.get("bullets", [])) + '</ul>')
    p.append('<hr>')

    # CTA
    p.append(f'<p><strong><a href="{cta_cfg.get("dashboard_url","")}">'
             f'{cta_cfg.get("dashboard_label","")} →</a></strong></p>')
    p.append(f'<p><a href="{cta_cfg.get("digest_url","")}">'
             f'{cta_cfg.get("digest_label","")} →</a></p>')
    p.append(f'<p><em>{brand.get("tagline","")} &nbsp;·&nbsp; '
             f'<a href="https://{brand.get("site","")}">{brand.get("site","")}</a></em></p>')

    return SUBSTACK_SHELL.format(title=f"India Credit Lens — {period}", body="\n".join(p))


def build_delta_v2_markdown(cfg, model, period_model, subsystems, annotations, yoy_lookup=None):
    """Markdown output for delta_v2."""
    edit          = cfg.get("editorial", {})
    meta          = cfg.get("_meta", {})
    issue         = meta.get("issue_number", 2)
    pub           = meta.get("published", "")
    period        = meta.get("period", "")
    brand         = cfg.get("branding", {})
    cta_cfg       = cfg.get("cta", {})
    signals       = edit.get("signals", [])
    watch         = edit.get("what_to_watch", {})
    prev_issue_url = meta.get("prev_issue_url", "#")
    id_to_node    = {n["id"]: n for n in real_nodes(model)}
    yoy_lookup    = yoy_lookup or {}

    # Scoreboard rows with YoY
    tiers = nodes_by_tier(period_model)
    EXCLUDE = {"sector_total_credit"}
    raw_nodes = [n for n in tiers.get("sector", []) if n["id"] not in EXCLUDE]
    sector_rows = []
    for n in raw_nodes:
        nid = n["id"]
        if nid in yoy_lookup:
            g        = yoy_lookup[nid]["yoy_pct"]
            stat_str = yoy_lookup[nid]["fmt"]
            vol      = f'₹{yoy_lookup[nid]["outstanding_lcr"]}L Cr'
        else:
            g        = parse_growth_pct(n.get("stat"))
            stat_str = n.get("stat", "—")
            vol      = f'₹{n["value_lcr"]}L Cr' if n.get("value_lcr") else "—"
        sector_rows.append((n["label"], stat_str, vol, g))
    sector_rows.sort(key=lambda x: x[3] if x[3] is not None else -9999, reverse=True)

    lines = [
        f"# India Credit Lens — {period}: {edit.get('issue_title','')}",
        f"*Issue #{issue} · {pub} · by {brand.get('author','')} · {brand.get('site','')}*",
        "",
    ]

    ctx = edit.get("context_strip", "")
    if ctx:
        lines += [f"> {ctx}", ""]

    lines += ["---", "", edit.get("hero_narrative", ""), "", "---", ""]

    if edit.get("tldr"):
        lines += ["## TL;DR", ""]
        for b in edit["tldr"]:
            lines.append(f"- {b}")
        lines += ["", "---", ""]

    # Scoreboard
    lines += [
        "## 📊 Where Credit Moved", "",
        "| Sector | YoY Growth | Outstanding |",
        "| --- | --- | --- |",
    ]
    for label, stat_str, vol, _ in sector_rows:
        lines.append(f'| {label} | {stat_str} | {vol} |')
    lines += ["", "---", ""]

    # System narrative (no diagram)
    lines += ["## 🗺 The System This Month", "", edit.get("system_narrative", ""), "", "---", ""]

    # ── Signals ─────────────────────────────────────────────────────────────────
    # New/correction → full treatment under "New This Issue".
    # Prior-issue types (confirmed/unchanged/updated/refuted) → compact status
    # list under "Prior Signals — Status Update". No body, no sources. Reader
    # follows the link to the prior issue for the original analysis.
    # ────────────────────────────────────────────────────────────────────────────
    prior_opp_ids_md = set(meta.get("prior_published_opportunity_ids", []))

    _PRIOR_ICON_MD = {
        "confirmed": "✅", "stronger": "↗", "unchanged": "↔",
        "weakening": "↘", "refuted": "❌",
    }

    def _prior_icon_md(item):
        s = item.get("status", "").lower()
        if s in _PRIOR_ICON_MD:
            return _PRIOR_ICON_MD[s]
        badge = item.get("badge", "")
        if badge.startswith("▲") or badge.startswith("✅"): return "✅"
        if badge.startswith("="): return "↔"
        if badge.startswith("↘") or badge.startswith("▼"): return "↘"
        if badge.startswith("❌"): return "❌"
        return "✅"

    NEW_TYPES_MD   = {"new", "correction"}
    PRIOR_TYPES_MD = {"confirmed", "unchanged", "updated", "refuted"}

    new_items_md   = [s for s in signals if s.get("type") in NEW_TYPES_MD]
    prior_items_md = [s for s in signals if s.get("type") in PRIOR_TYPES_MD]

    # Section A — new signals
    lines += ["## 📡 New This Issue", ""]
    for item in new_items_md:
        t         = item.get("type", "")
        story_arc = item.get("story_arc", "")
        signal    = item.get("signal", "")
        sub_id    = item.get("subsystem_id", "") or ""

        if t == "new":
            lines += [f"### ★ {story_arc}", "", "*New this issue*", ""]
            if item.get("stat"):
                lines += [f"**{item['stat']}**", ""]
            lines += [f"**{signal}**", ""]
            if item.get("body"):
                lines += [item["body"], ""]
            if item.get("implication"):
                lines += [f"*{item['implication']}*", ""]
            mmd_file = item.get("mermaid_file")
            if item.get("image_url"):
                lines += [f"![{signal}]({item['image_url']})", ""]
            elif mmd_file is not None:
                slug = re.sub(r"[^a-z0-9]+", "_", signal.lower()).strip("_")[:30]
                lines += [f"> 🖼 `[Insert: {sub_id}_{slug}.png]`", ""]

        elif t == "correction":
            prev_num = item.get("prev_issue_number", 1)
            lines += [f"### ⟳ {story_arc}", "", f"*Correction from Issue #{prev_num}*", ""]
            lines += [f"**{signal}**", ""]
            lines += [
                f"**What it looked like:** *{item.get('prev_read','')}*", "",
                f"**What it actually is:** {item.get('curr_read','')}", "",
            ]
            if item.get("implication"):
                lines += [f"> **Implication:** {item['implication']}", ""]
            if item.get("image_url"):
                lines += [f"![{signal}]({item['image_url']})", ""]
            else:
                slug = re.sub(r"[^a-z0-9]+", "_", signal.lower()).strip("_")[:30]
                lines += [f"> 🖼 `[Insert: {sub_id}_{slug}.png]`", ""]

        # Outcomes: new + correction only, skip prior-issue opportunities
        lines += _d2_outcomes_md(sub_id, subsystems, id_to_node, annotations,
                                  prior_opp_ids=prior_opp_ids_md)
        lines += ["---", ""]

    # Section B — prior signals: registry takes priority, inline list as fallback
    registry_path_md = meta.get("signal_registry_path", "")
    if registry_path_md:
        registry_md = load_signal_registry(registry_path_md)
        current_issue_md = meta.get("issue_number", 1)
        lines += _registry_prior_signals_md(registry_md, current_issue_md)
    elif prior_items_md:
        lines += ["## 📋 Prior Signals — Status Update", ""]
        lines.append(
            "*Signals from earlier issues. New data this period. "
            "Follow the link for the original analysis.*"
        )
        lines.append("")
        for item in prior_items_md:
            icon      = _prior_icon_md(item)
            arc       = item.get("story_arc", "")
            badge     = item.get("badge", "")
            curr_stat = item.get("curr_stat", "")
            prev_num  = item.get("prev_issue_number", 1)
            item_url  = item.get("prev_issue_url", prev_issue_url or "#")
            note_parts = [p_ for p_ in [badge, curr_stat] if p_]
            note = " — ".join(note_parts) if note_parts else ""
            lines.append(
                f"- {icon} **{arc}**"
                + (f" — {note}" if note else "")
                + f" [Issue #{prev_num} →]({item_url})"
            )
        lines += ["", "---", ""]

    # What to Watch
    lines += [
        "## 📅 What to Watch Next",
        f"*Next release: {watch.get('next_release','')}*", "",
    ]
    for b in watch.get("bullets", []):
        lines.append(f"- {b}")
    lines += ["", "---", ""]

    # CTA
    lines += [
        f"**{cta_cfg.get('dashboard_label','')}**",
        f"→ {cta_cfg.get('dashboard_url','')}",
        "",
        f"**{cta_cfg.get('digest_label','')}**",
        f"→ {cta_cfg.get('digest_url','')}",
        "",
        "---",
        f"*{brand.get('tagline','')} · {brand.get('site','')}*",
        "",
    ]
    return "\n".join(lines)


def build_delta_html(cfg, model, subsystems):
    """Full HTML output for delta_v1 format."""
    edit        = cfg.get("editorial", {})
    issue       = cfg["_meta"].get("issue_number", 2)
    pub         = cfg["_meta"].get("published", "")
    period      = cfg["_meta"].get("period", "")
    prev_period = cfg["_meta"].get("prev_period", "")
    brand       = cfg.get("branding", {})
    author      = brand.get("author", "India Credit Lens")

    what_held    = edit.get("what_held", [])
    what_changed = edit.get("what_changed", [])
    what_new     = edit.get("what_new", [])

    header = (
        f'<div style="padding:36px 40px 0">'
        f'<div style="font-family:system-ui,sans-serif;font-size:10px;'
        f'text-transform:uppercase;letter-spacing:3px;color:#b45309;margin-bottom:12px">'
        f'India Credit Lens &nbsp;·&nbsp; Issue #{issue} &nbsp;·&nbsp; {pub}</div>'
        f'<h1 style="font-size:2em;margin:0 0 6px;color:#1a0f00;line-height:1.2">'
        f'{period}: {edit.get("issue_title", "")}</h1>'
        f'<div style="color:#7a5c30;font-size:0.9em">'
        f'RBI Sector/Industry-wise Bank Credit &nbsp;·&nbsp; by {author}</div>'
        f'</div>'
    )

    context_strip_text = edit.get("context_strip", "")
    context_strip = (
        f'<div style="margin:24px 40px 0;padding:16px 20px;background:#f4f0e8;'
        f'border-left:3px solid #c9a96e;border-radius:0 2px 2px 0">'
        f'<p style="margin:0;font-family:system-ui,sans-serif;font-size:0.83em;'
        f'color:#7a5c30;line-height:1.7">'
        f'<strong style="color:#5c4a2a">What is this?</strong> {context_strip_text}</p>'
        f'</div>'
    ) if context_strip_text else ""

    hero = (
        f'<div style="margin:28px 0 0;padding:36px 40px;background:#1E3A5F">'
        f'<div style="font-family:system-ui,sans-serif;font-size:0.72em;font-weight:600;'
        f'text-transform:uppercase;letter-spacing:2px;color:#7eb8e8;margin-bottom:14px">'
        f'February 2026 &nbsp;·&nbsp; RBI SIBC</div>'
        f'<p style="color:#ffffff;font-size:1.08em;line-height:1.85;margin:0">'
        f'{edit.get("hero_narrative", "")}</p>'
        f'</div>'
    )

    parts = [
        header,
        context_strip,
        hero,
        divider(),
        build_delta_dominant_forces(what_held),
        divider(),
        build_delta_one_correction(what_changed),
        divider(),
        build_delta_series_reveals(what_new),
        divider(),
        build_what_to_watch(edit),
        divider(),
        build_cta(cfg),
        build_footer(cfg),
    ]

    return HTML_SHELL.format(
        title=f"India Credit Lens — {period}",
        body="\n".join(parts),
    )


def _substack_image(item: dict) -> str:
    """Return image tag or placeholder line for Substack output."""
    signal = item.get("signal", "")
    sub_id = item.get("subsystem_id", "")
    if item.get("image_url"):
        return f'<p><img src="{item["image_url"]}" alt="{signal}" style="max-width:100%"></p>'
    elif sub_id:
        slug = re.sub(r"[^a-z0-9]+", "_", signal.lower()).strip("_")[:30]
        return f'<p><em>[Insert image: {sub_id}_{slug}.png]</em></p>'
    return ""


def build_delta_substack(cfg, model, subsystems):
    """
    Clean semantic HTML for Substack paste — delta_v1 format.

    Usage: open _substack.html in browser → Select All → Copy →
    paste into Substack visual editor (not HTML embed block).
    Substack preserves headings, bold, italic, blockquotes, lists, links.
    """
    edit        = cfg.get("editorial", {})
    issue       = cfg["_meta"].get("issue_number", 2)
    pub         = cfg["_meta"].get("published", "")
    period      = cfg["_meta"].get("period", "")
    brand       = cfg.get("branding", {})
    cta_cfg     = cfg.get("cta", {})
    what_held    = edit.get("what_held", [])
    what_changed = edit.get("what_changed", [])
    what_new     = edit.get("what_new", [])
    watch        = edit.get("what_to_watch", {})

    p = []

    # ── Header ────────────────────────────────────────────────────────────────
    p.append(f'<h1>{period}: {edit.get("issue_title", "")}</h1>')
    p.append(
        f'<p><em>Issue #{issue} &nbsp;·&nbsp; {pub}'
        f' &nbsp;·&nbsp; by {brand.get("author", "India Credit Lens")}'
        f' &nbsp;·&nbsp; <a href="https://{brand.get("site", "")}">'
        f'{brand.get("site", "")}</a></em></p>'
    )

    # ── Context strip (for new readers) ───────────────────────────────────────
    context = edit.get("context_strip", "")
    if context:
        p.append(f'<blockquote><p>{context}</p></blockquote>')

    p.append('<hr>')

    # ── Hero ──────────────────────────────────────────────────────────────────
    p.append(f'<p>{edit.get("hero_narrative", "")}</p>')
    p.append('<hr>')

    # ── The Dominant Forces ───────────────────────────────────────────────────
    if what_held:
        p.append('<h2>▲ The Dominant Forces</h2>')
        p.append(
            '<p><em>Three structural forces shaping Indian credit — '
            'confirmed across multiple data points.</em></p>'
        )
        for item in what_held:
            badge     = item.get("badge", "")
            signal    = item.get("signal", "")
            prev_stat = item.get("prev_stat", "")
            curr_stat = item.get("curr_stat", "")
            note      = item.get("note", "")

            p.append(f'<h3>{signal}</h3>')
            if badge:
                p.append(f'<p><strong>{badge}</strong></p>')
            p.append(
                f'<p><strong>Last issue:</strong> {prev_stat}<br>'
                f'<strong>Now (merged):</strong> {curr_stat}</p>'
            )
            if note:
                p.append(f'<p>{note}</p>')
            p.append(_substack_image(item))

        p.append('<hr>')

    # ── One Correction ────────────────────────────────────────────────────────
    if what_changed:
        p.append('<h2>⟳ One Correction</h2>')
        p.append(
            '<p><em>A number in the headlines this month that is not what it '
            'looks like — and what it actually means.</em></p>'
        )
        for item in what_changed:
            badge      = item.get("badge", "")
            signal     = item.get("signal", "")
            prev_read  = item.get("prev_read", "")
            curr_read  = item.get("curr_read", "")
            implication = item.get("implication", "")

            p.append(f'<h3>{signal}</h3>')
            if badge:
                p.append(f'<p><strong>{badge}</strong></p>')
            p.append(f'<p><strong>What it looked like:</strong> <em>{prev_read}</em></p>')
            p.append(f'<p><strong>What it actually is:</strong> {curr_read}</p>')
            if implication:
                p.append(
                    f'<blockquote><p><strong>Implication:</strong> {implication}</p></blockquote>'
                )
            p.append(_substack_image(item))

        p.append('<hr>')

    # ── What the Series Reveals ───────────────────────────────────────────────
    if what_new:
        p.append('<h2>★ What the Series Reveals</h2>')
        p.append(
            '<p><em>Two signals that require connecting multiple months of data — '
            'invisible in any single RBI publication.</em></p>'
        )
        for item in what_new:
            badge       = item.get("badge", "")
            signal      = item.get("signal", "")
            stat        = item.get("stat", "")
            body        = item.get("body", "")
            implication = item.get("implication", "")

            p.append(f'<h3>{signal}</h3>')
            if badge:
                p.append(f'<p><strong>{badge}</strong></p>')
            if stat:
                p.append(f'<p><strong>{stat}</strong></p>')
            if body:
                p.append(f'<p>{body}</p>')
            if implication:
                p.append(f'<blockquote><p><em>{implication}</em></p></blockquote>')
            p.append(_substack_image(item))

        p.append('<hr>')

    # ── What to Watch ─────────────────────────────────────────────────────────
    p.append('<h2>📅 What to Watch Next</h2>')
    p.append(f'<p><em>Next release: {watch.get("next_release", "")}</em></p>')
    wl = "".join(f'<li>{b}</li>' for b in watch.get("bullets", []))
    p.append(f'<ul>{wl}</ul>')
    p.append('<hr>')

    # ── CTA ───────────────────────────────────────────────────────────────────
    p.append(
        f'<p><strong>'
        f'<a href="{cta_cfg.get("dashboard_url", "")}">'
        f'{cta_cfg.get("dashboard_label", "")} →</a></strong></p>'
    )
    p.append(
        f'<p><a href="{cta_cfg.get("digest_url", "")}">'
        f'{cta_cfg.get("digest_label", "")} →</a></p>'
    )
    p.append(
        f'<p><em>{brand.get("tagline", "")} &nbsp;·&nbsp; '
        f'<a href="https://{brand.get("site", "")}">{brand.get("site", "")}</a></em></p>'
    )

    return SUBSTACK_SHELL.format(
        title=f"India Credit Lens — {period}",
        body="\n".join(p),
    )


def build_delta_markdown(cfg, model, subsystems):
    """Markdown output for delta_v1 format."""
    edit        = cfg.get("editorial", {})
    issue       = cfg["_meta"].get("issue_number", 2)
    pub         = cfg["_meta"].get("published", "")
    period      = cfg["_meta"].get("period", "")
    brand       = cfg.get("branding", {})
    cta_cfg     = cfg.get("cta", {})
    what_held    = edit.get("what_held", [])
    what_changed = edit.get("what_changed", [])
    what_new     = edit.get("what_new", [])
    watch        = edit.get("what_to_watch", {})

    lines = [
        f"# India Credit Lens — {period}: {edit.get('issue_title', '')}",
        f"*Issue #{issue} · {pub} · by {brand.get('author', '')} · {brand.get('site', '')}*",
        "",
    ]

    # Context strip
    context = edit.get("context_strip", "")
    if context:
        lines += [f"> {context}", ""]

    lines += ["---", "", edit.get("hero_narrative", ""), "", "---", ""]

    # The Dominant Forces
    if what_held:
        lines += ["## ▲ The Dominant Forces", ""]
        lines.append(
            "*Three structural forces shaping Indian credit — "
            "confirmed across multiple data points.*"
        )
        lines.append("")
        for item in what_held:
            signal = item.get("signal", "")
            badge  = item.get("badge", "")
            lines += [f"### {signal}", ""]
            if badge:
                lines += [f"**{badge}**", ""]
            lines += [
                f"**Last issue:** {item.get('prev_stat', '')}",
                f"**Now (merged):** {item.get('curr_stat', '')}",
                "",
            ]
            if item.get("note"):
                lines += [item["note"], ""]
            sub_id = item.get("subsystem_id", "")
            if item.get("image_url"):
                lines += [f"![{signal}]({item['image_url']})", ""]
            elif sub_id:
                slug = re.sub(r"[^a-z0-9]+", "_", signal.lower()).strip("_")[:30]
                lines += [f"> 🖼 `[Insert: {sub_id}_{slug}.png]`", ""]
        lines += ["---", ""]

    # One Correction
    if what_changed:
        lines += ["## ⟳ One Correction", ""]
        lines.append(
            "*A number in the headlines this month that is not what it "
            "looks like — and what it actually means.*"
        )
        lines.append("")
        for item in what_changed:
            signal = item.get("signal", "")
            badge  = item.get("badge", "")
            lines += [f"### {signal}", ""]
            if badge:
                lines += [f"**{badge}**", ""]
            lines += [
                f"**What it looked like:** *{item.get('prev_read', '')}*",
                "",
                f"**What it actually is:** {item.get('curr_read', '')}",
                "",
            ]
            if item.get("implication"):
                lines += [f"> **Implication:** {item['implication']}", ""]
            sub_id = item.get("subsystem_id", "")
            if item.get("image_url"):
                lines += [f"![{signal}]({item['image_url']})", ""]
            elif sub_id:
                slug = re.sub(r"[^a-z0-9]+", "_", signal.lower()).strip("_")[:30]
                lines += [f"> 🖼 `[Insert: {sub_id}_{slug}.png]`", ""]
        lines += ["---", ""]

    # What the Series Reveals
    if what_new:
        lines += ["## ★ What the Series Reveals", ""]
        lines.append(
            "*Two signals that require connecting multiple months of data — "
            "invisible in any single RBI publication.*"
        )
        lines.append("")
        for item in what_new:
            signal = item.get("signal", "")
            badge  = item.get("badge", "")
            lines += [f"### {signal}", ""]
            if badge:
                lines += [f"**{badge}**", ""]
            if item.get("stat"):
                lines += [f"**{item['stat']}**", ""]
            if item.get("body"):
                lines += [item["body"], ""]
            if item.get("implication"):
                lines += [f"*{item['implication']}*", ""]
            sub_id = item.get("subsystem_id", "")
            if item.get("image_url"):
                lines += [f"![{signal}]({item['image_url']})", ""]
            elif sub_id:
                slug = re.sub(r"[^a-z0-9]+", "_", signal.lower()).strip("_")[:30]
                lines += [f"> 🖼 `[Insert: {sub_id}_{slug}.png]`", ""]
        lines += ["---", ""]

    # What to Watch
    lines += [
        "## 📅 What to Watch Next",
        f"*Next release: {watch.get('next_release', '')}*", "",
    ]
    for b in watch.get("bullets", []):
        lines.append(f"- {b}")
    lines += ["", "---", ""]

    # CTA
    lines += [
        f"**{cta_cfg.get('dashboard_label', '')}**",
        f"→ {cta_cfg.get('dashboard_url', '')}",
        "",
        f"**{cta_cfg.get('digest_label', '')}**",
        f"→ {cta_cfg.get('digest_url', '')}",
        "",
        "---",
        f"*{brand.get('tagline', '')} · {brand.get('site', '')}*",
        "",
    ]
    return "\n".join(lines)


def build_cta(cfg):
    cta   = cfg.get("cta", {})
    brand = cfg.get("branding", {})
    db_label = cta.get("dashboard_label", "Explore the dashboard")
    db_url   = cta.get("dashboard_url", "https://indiacreditlens.com")
    st_label = cta.get("digest_label", "Subscribe")
    st_url   = cta.get("digest_url", "https://indiacreditlens.substack.com")
    return (
        f'<div style="margin:40px 0 0;padding:36px 40px;background:#1E3A5F;text-align:center">'
        f'<div style="font-family:system-ui,sans-serif;font-size:1em;font-weight:700;'
        f'color:#ffffff;margin-bottom:24px">Go deeper on any of these signals</div>'
        f'<a href="{db_url}" style="display:inline-block;background:#0F766E;color:#ffffff;'
        f'text-decoration:none;padding:13px 26px;font-family:system-ui,sans-serif;'
        f'font-weight:600;font-size:0.9em;border-radius:3px;margin:6px">'
        f'{db_label} →</a>'
        f'<br>'
        f'<a href="{st_url}" style="display:inline-block;background:transparent;'
        f'color:#a0b8d4;text-decoration:none;padding:13px 26px;font-family:system-ui,sans-serif;'
        f'font-weight:600;font-size:0.9em;border-radius:3px;'
        f'border:1px solid rgba(160,184,212,0.35);margin:6px">'
        f'{st_label} →</a>'
        f'</div>'
    )


def build_footer(cfg):
    brand = cfg.get("branding", {})
    site  = brand.get("site", "")
    tag   = brand.get("tagline", "")
    return (
        f'<div style="padding:20px 40px 32px;text-align:center;'
        f'border-top:1px solid #e2d9c5;margin-top:0">'
        f'<div style="font-family:system-ui,sans-serif;font-size:0.78em;color:#7a5c30">'
        f'{tag} &nbsp;·&nbsp; '
        f'<a href="https://{site}" style="color:#b45309;text-decoration:none">{site}</a>'
        f'</div>'
        f'</div>'
    )


# ── HTML shell ────────────────────────────────────────────────────────────────

HTML_SHELL = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
</head>
<body style="margin:0;padding:24px 0;background:#ede8df;
             font-family:Georgia,'Times New Roman',serif">
  <div style="max-width:640px;margin:0 auto;background:#faf6ef;color:#2c1e0f;
              box-shadow:0 2px 16px rgba(0,0,0,0.10)">
    {body}
    <div style="height:1px"></div>
  </div>
</body>
</html>
"""


# ── Substack shell (minimal styles — survives paste) ─────────────────────────

SUBSTACK_SHELL = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — Substack</title>
  <style>
    body {{ max-width:680px; margin:40px auto; font-family:Georgia,serif;
            color:#1a1a1a; line-height:1.75; font-size:17px; }}
    h1,h2,h3 {{ font-family:system-ui,sans-serif; line-height:1.25; }}
    h1 {{ font-size:1.9em; margin-bottom:6px; }}
    h2 {{ font-size:1.15em; margin:36px 0 10px; border-bottom:1px solid #e5e5e5;
          padding-bottom:6px; }}
    h3 {{ font-size:1em; margin:28px 0 8px; }}
    table {{ width:100%; border-collapse:collapse; font-size:0.9em; }}
    th {{ text-align:left; padding:6px 10px; border-bottom:2px solid #ddd;
          font-family:system-ui; font-size:0.8em; text-transform:uppercase;
          letter-spacing:0.05em; color:#555; }}
    td {{ padding:7px 10px; border-bottom:1px solid #f0f0f0; }}
    blockquote {{ border-left:3px solid #ccc; margin:20px 0;
                  padding:14px 20px; background:#f9f9f9; border-radius:2px; }}
    blockquote p {{ margin:6px 0; }}
    hr {{ border:none; border-top:1px solid #e5e5e5; margin:36px 0; }}
    a {{ color:#1a1a1a; }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


# ── Substack HTML builder ─────────────────────────────────────────────────────

def build_substack_html(cfg, model, annotations, subsystems):
    """Semantic HTML only — no inline styles. Open in browser → Select All →
    Copy → paste into Substack editor. Substack keeps headings, bold, italic,
    blockquotes, tables, and links.
    """
    meta       = model.get("_meta", {})
    edit       = cfg.get("editorial", {})
    tiers      = nodes_by_tier(model)
    period     = meta.get("period", "")
    total      = meta.get("total_credit_lcr", "")
    growth     = meta.get("yoy_growth_pct", "")
    issue      = cfg["_meta"].get("issue_number", 1)
    pub        = cfg["_meta"].get("published", "")
    brand      = cfg.get("branding", {})
    cta_cfg    = cfg.get("cta", {})
    issue_t    = edit.get("issue_title", period)
    featured   = edit.get("featured_annotation_ids", [])
    nl_subs    = [s for s in subsystems if s.get("newsletter")]
    id_to_node = {n["id"]: n for n in real_nodes(model)}

    p = []   # parts list

    # ── Header ────────────────────────────────────────────────────────────────
    p.append(f'<h1>{period}: {issue_t}</h1>')
    p.append(
        f'<p><em>Issue #{issue} &nbsp;·&nbsp; {pub} &nbsp;·&nbsp; '
        f'by {brand.get("author", "India Credit Lens")}</em></p>'
    )
    p.append('<hr>')

    # ── Hero stat ─────────────────────────────────────────────────────────────
    p.append(f'<h2>₹{total}L Cr &nbsp;—&nbsp; +{growth}% YoY</h2>')
    p.append(
        f'<p>Total bank credit outstanding · {period}. '
        f'₹25.8L Cr added in 12 months vs ₹18.1L Cr the year before. '
        f'The system is not just growing — it is accelerating.</p>'
    )
    p.append('<hr>')

    # ── TL;DR ─────────────────────────────────────────────────────────────────
    p.append('<h2>TL;DR</h2>')
    bullets = "".join(f'<li>{b}</li>' for b in edit.get("tldr", []))
    p.append(f'<ul>{bullets}</ul>')
    p.append('<hr>')

    # ── Future: What Changed (issue #2+) ──────────────────────────────────────

    # ── Where credit moved ────────────────────────────────────────────────────
    EXCLUDE = {"sector_total_credit"}
    sector_rows = sorted(
        [(n, parse_growth_pct(n.get("stat"))) for n in tiers.get("sector", [])
         if n["id"] not in EXCLUDE],
        key=lambda x: x[1] if x[1] is not None else -9999,
        reverse=True,
    )
    p.append('<h2>Where Credit Moved</h2>')
    rows_html = "".join(
        f'<tr><td>{n["label"]}</td><td><strong>{n.get("stat","—")}</strong></td>'
        f'<td>{"₹" + str(n["value_lcr"]) + "L Cr" if n.get("value_lcr") else "—"}</td></tr>'
        for n, _ in sector_rows
    )
    p.append(
        f'<table><thead><tr><th>Sector</th><th>YoY Growth</th>'
        f'<th>Outstanding</th></tr></thead><tbody>{rows_html}</tbody></table>'
    )
    p.append('<hr>')

    # ── Key signals ───────────────────────────────────────────────────────────
    p.append('<h2>Key Signals This Month</h2>')
    p.append('<p><em>Three signals selected as most consequential for lenders.</em></p>')
    for aid in featured:
        ann = annotations.get(aid)
        if not ann:
            continue
        node  = find_best_node_for_annotation(aid, tiers)
        stat  = node.get("stat", "")
        title = ann.get("title", "")
        body  = ann.get("body", "")
        impl  = ann.get("implication", "")
        p.append(
            f'<blockquote>'
            f'<p><strong>{stat} — {title}</strong></p>'
            f'<p>{body}</p>'
            + (f'<p><em>{impl}</em></p>' if impl else '')
            + '</blockquote>'
        )
    p.append('<hr>')

    # ── System overview ───────────────────────────────────────────────────────
    p.append('<h2>The System This Month</h2>')
    p.append(f'<p>{edit.get("system_narrative", "")}</p>')
    p.append('<p><em>[Insert image: overview.png]</em></p>')
    if nl_subs:
        p.append('<p>Three structural stories in this issue:</p>')
        sl = "".join(f'<li><strong>{s["label"]}</strong></li>' for s in nl_subs)
        p.append(f'<ul>{sl}</ul>')
    p.append('<hr>')

    # ── Subsystem stories ─────────────────────────────────────────────────────
    p.append('<h2>The Three Stories</h2>')
    for sub in nl_subs:
        label = sub["label"]
        p.append(f'<h3>{label}</h3>')

        # Drivers as italic label row
        driver_labels = []
        for did in sub.get("drivers", []):
            d = id_to_node.get(did)
            if d:
                driver_labels.append(d["label"])
        if driver_labels:
            p.append(f'<p><em>{" · ".join(driver_labels)}</em></p>')

        # Sector stats
        for sid in sub.get("sectors", []):
            s = id_to_node.get(sid)
            if s:
                p.append(
                    f'<p><strong>{s.get("stat", "")}</strong>'
                    f'&nbsp; {s["label"]}</p>'
                )

        # Diagram placeholder
        slug     = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")[:30]
        sub_id   = sub.get("id", "sub_xx")
        img_file = f"{sub_id}_{slug}.png"
        p.append(f'<p><em>[Insert image: {img_file}]</em></p>')

        # Outcome nodes — risks, gaps, opportunities as blockquotes
        for oid in sub.get("outcomes", []):
            o = id_to_node.get(oid)
            if not o:
                continue
            tier = o.get("tier", "gap")
            icon = {"opportunity": "✅", "pressure": "⚠️", "gap": "🔍"}.get(tier, "•")
            ann  = node_primary_annotation(o, annotations)
            impl = ann.get("implication", "") if ann else ""
            p.append(
                f'<blockquote>'
                f'<p><strong>{icon} {o["label"]}</strong></p>'
                f'<p>{o.get("description", "")}</p>'
                + (f'<p><em>{impl}</em></p>' if impl else '')
                + '</blockquote>'
            )

        p.append('<hr>')

    # ── What to watch ─────────────────────────────────────────────────────────
    watch = edit.get("what_to_watch", {})
    p.append('<h2>What to Watch Next</h2>')
    p.append(f'<p><em>Next release: {watch.get("next_release", "")}</em></p>')
    wl = "".join(f'<li>{b}</li>' for b in watch.get("bullets", []))
    p.append(f'<ul>{wl}</ul>')
    p.append('<hr>')

    # ── CTA ───────────────────────────────────────────────────────────────────
    p.append(
        f'<p><strong>'
        f'<a href="{cta_cfg.get("dashboard_url", "")}">'
        f'{cta_cfg.get("dashboard_label", "Explore the dashboard")} →</a>'
        f'</strong></p>'
    )
    p.append(
        f'<p><a href="{cta_cfg.get("digest_url", "")}">'
        f'{cta_cfg.get("digest_label", "Subscribe")} →</a></p>'
    )
    p.append(
        f'<p><em>{brand.get("tagline", "")} &nbsp;·&nbsp; '
        f'<a href="https://{brand.get("site", "")}">{brand.get("site", "")}</a></em></p>'
    )

    return SUBSTACK_SHELL.format(
        title=f"India Credit Lens — {period}",
        body="\n".join(p),
    )


# ── HTML builder ──────────────────────────────────────────────────────────────

def build_html(cfg, model, annotations, subsystems):
    meta  = model.get("_meta", {})
    edit  = cfg.get("editorial", {})
    tiers = nodes_by_tier(model)

    parts = [
        build_header(cfg, meta),
        build_hook(meta),
        build_tldr(edit),
        # ── Future: build_what_changed(delta) here (issue #2 onwards) ──
        divider(),
        build_sectors_scoreboard(tiers.get("sector", [])),
        divider(),
        build_key_signals(edit.get("featured_annotation_ids", []), tiers, annotations),
        divider(),
        build_system_overview(edit, subsystems),
        build_subsystem_stories(subsystems, model, annotations),
        divider(),
        build_what_to_watch(edit),
        divider(),
        build_cta(cfg),
        build_footer(cfg),
    ]

    period = meta.get("period", "")
    return HTML_SHELL.format(
        title=f"India Credit Lens — {period}",
        body="\n".join(parts),
    )


# ── Markdown builder ──────────────────────────────────────────────────────────

def build_markdown(cfg, model, annotations, subsystems):
    meta    = model.get("_meta", {})
    edit    = cfg.get("editorial", {})
    tiers   = nodes_by_tier(model)
    period  = meta.get("period", "")
    total   = meta.get("total_credit_lcr", "")
    growth  = meta.get("yoy_growth_pct", "")
    issue   = cfg["_meta"].get("issue_number", 1)
    pub     = cfg["_meta"].get("published", "")
    brand   = cfg.get("branding", {})
    cta_cfg = cfg.get("cta", {})
    issue_t = edit.get("issue_title", period)
    featured = edit.get("featured_annotation_ids", [])
    nl_subs  = [s for s in subsystems if s.get("newsletter")]
    id_to_node = {n["id"]: n for n in real_nodes(model)}

    lines = []

    # Header
    lines += [
        f"# India Credit Lens — {period}: {issue_t}",
        f"*Issue #{issue} · {pub} · {brand.get('site', '')}*",
        "", "---", "",
        f"## ₹{total}L Cr",
        f"**Total bank credit outstanding · {period}**",
        f"+{growth}% YoY — fastest growth rate in this dataset.",
        "", "---", "", "## TL;DR", "",
    ]
    for b in edit.get("tldr", []):
        lines.append(f"- {b}")
    lines += ["", "---", ""]

    # Future: ## What Changed Since Last Issue (delta section, issue #2 onwards)

    # Where credit moved
    EXCLUDE = {"sector_total_credit"}
    sector_rows = sorted(
        [(n, parse_growth_pct(n.get("stat"))) for n in tiers.get("sector", [])
         if n["id"] not in EXCLUDE],
        key=lambda x: x[1] if x[1] is not None else -9999,
        reverse=True,
    )
    lines += [
        "## 📊 Where Credit Moved", "",
        "| Sector | YoY Growth | Outstanding |",
        "| --- | --- | --- |",
    ]
    for node, _ in sector_rows:
        vol = f'₹{node["value_lcr"]}L Cr' if node.get("value_lcr") else "—"
        lines.append(f'| {node["label"]} | {node.get("stat","—")} | {vol} |')
    lines += ["", "---", ""]

    # Key signals
    lines += ["## 🔎 Key Signals This Month", ""]
    for aid in featured:
        ann = annotations.get(aid)
        if not ann:
            continue
        node = find_best_node_for_annotation(aid, tiers)
        stat = node.get("stat", "")
        lines += [f"### {stat} — {ann.get('title', '')}", "", ann.get("body", ""), ""]
        if ann.get("implication"):
            lines += [f"*{ann['implication']}*", ""]
    lines += ["---", ""]

    # System overview
    lines += ["## 🗺 The System This Month", "", edit.get("system_narrative", ""), ""]
    lines += ["> 🖼 `[Insert: overview.png]`", ""]
    if nl_subs:
        lines += ["Three structural stories in this issue:", ""]
        for s in nl_subs:
            lines.append(f"- **{s['label']}**")
    lines += ["", "---", ""]

    # Subsystem stories
    lines += ["## 📖 The Three Stories", ""]
    for sub in nl_subs:
        lines += [f"### {sub['label']}", ""]

        # Driver chips (inline text)
        driver_labels = []
        for did in sub.get("drivers", []):
            d = id_to_node.get(did)
            if d:
                driver_labels.append(d["label"])
        if driver_labels:
            lines += [f"**Drivers:** {' · '.join(driver_labels)}", ""]

        # Sector stats
        for sid in sub.get("sectors", []):
            s = id_to_node.get(sid)
            if s:
                lines.append(f"**{s.get('stat', '')}** {s['label']}")
        lines.append("")

        # Diagram placeholder
        slug     = re.sub(r"[^a-z0-9]+", "_", sub["label"].lower()).strip("_")[:30]
        sub_id   = sub.get("id", "sub_xx")
        img_file = f"{sub_id}_{slug}.png"
        lines += [f"> 🖼 `[Insert: {img_file}]`", ""]

        # Outcome nodes
        for oid in sub.get("outcomes", []):
            o = id_to_node.get(oid)
            if not o:
                continue
            tier   = o.get("tier", "gap")
            icon   = {"opportunity": "✅", "pressure": "⚠️", "gap": "🔍"}.get(tier, "•")
            ann    = node_primary_annotation(o, annotations)
            impl   = ann.get("implication", "") if ann else ""
            lines += [f"{icon} **{o['label']}**", o.get("description", "")]
            if impl:
                lines += [f"*{impl}*"]
            lines.append("")

        lines += ["---", ""]

    # What to watch
    watch = edit.get("what_to_watch", {})
    lines += [
        "## 📅 What to Watch Next",
        f"*Next release: {watch.get('next_release', '')}*", "",
    ]
    for b in watch.get("bullets", []):
        lines.append(f"- {b}")
    lines += ["", "---", ""]

    # CTA
    lines += [
        f"**{cta_cfg.get('dashboard_label', '')}**",
        f"→ {cta_cfg.get('dashboard_url', '')}",
        "",
        f"**{cta_cfg.get('digest_label', '')}**",
        f"→ {cta_cfg.get('digest_url', '')}",
        "",
        "---",
        f"*{brand.get('tagline', '')} · {brand.get('site', '')}*",
        "",
    ]
    return "\n".join(lines)


# ── Entry point ───────────────────────────────────────────────────────────────

def render_mermaid_diagrams(cfg, mermaid_base: Path, output_dir: Path) -> dict:
    """
    Option A: render .mmd files to PNG via mmdc and return as base64 data URLs.

    Each newsletter item can specify a 'mermaid_file' path (relative to the
    newsletter/ directory) pointing to the exact .mmd file to use. If not set,
    falls back to matching sub_NN_*.mmd files in mermaid_base by sub_id prefix.

    Returns: dict mapping subsystem_id → "data:image/png;base64,..." URL.
    Images are embedded inline — no hosted URLs needed, works in Substack paste.

    Requires: mmdc (npm install -g @mermaid-js/mermaid-cli)
    """
    import base64
    import copy
    import shutil
    import subprocess

    mmdc = shutil.which("mmdc")
    if not mmdc:
        print("  ⚠  mmdc not found — install with: npm install -g @mermaid-js/mermaid-cli")
        return {}

    img_dir = output_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    # Build list of (key, mmd_path) to render
    # key = subsystem_id for signal diagrams, "_overview" for the overview diagram
    nl_dir  = Path(__file__).resolve().parent
    fmt     = cfg.get("_meta", {}).get("format", "")
    edit    = cfg.get("editorial", {})
    tasks: list[tuple[str, Path]] = []
    seen_keys: set[str] = set()

    # Overview diagram (delta_v2 only)
    if fmt == "delta_v2":
        ov_rel = cfg.get("_meta", {}).get("overview_mermaid_file", "")
        if ov_rel:
            ov_path = (nl_dir / ov_rel).resolve()
            if ov_path.exists():
                tasks.append(("_overview", ov_path))
            else:
                print(f"  ⚠  overview_mermaid_file not found: {ov_path}")

    # Per-signal diagrams
    if fmt == "delta_v2":
        signal_items = edit.get("signals", [])
    else:
        signal_items = []
        for section in ("what_held", "what_changed", "what_new"):
            signal_items += edit.get(section, [])

    for item in signal_items:
        sub_id  = item.get("subsystem_id", "")
        mmd_rel = item.get("mermaid_file") or ""   # None → ""
        if not sub_id or sub_id in seen_keys:
            continue
        # confirmed signals with mermaid_file=null → skip rendering
        if fmt == "delta_v2" and item.get("type") == "confirmed":
            continue
        seen_keys.add(sub_id)

        raw_mmd = item.get("mermaid_file")   # None means explicitly "no diagram"
        if raw_mmd is None:
            # Explicitly set to null in config — no diagram for this signal
            continue
        mmd_rel = str(raw_mmd).strip()
        if mmd_rel:
            mmd_path = (nl_dir / mmd_rel).resolve()
            if mmd_path.exists():
                tasks.append((sub_id, mmd_path))
            else:
                print(f"  ⚠  mermaid_file not found for {sub_id}: {mmd_path}")
        else:
            # Empty string — fallback glob
            matches = sorted(mermaid_base.glob(f"{sub_id}_*.mmd"))
            if matches:
                tasks.append((sub_id, matches[0]))
            else:
                print(f"  ⚠  No .mmd found for {sub_id} in {mermaid_base}")

    if not tasks:
        print("  ⚠  No mermaid files to render.")
        return {}

    rendered: dict[str, str] = {}
    print(f"\n  Rendering {len(tasks)} diagram(s) via mmdc (embedded as base64):")

    for sub_id, mmd in tasks:
        out_png = img_dir / f"{mmd.stem}.png"
        result  = subprocess.run(
            [mmdc, "-i", str(mmd), "-o", str(out_png), "-t", "default", "-b", "white"],
            capture_output=True, text=True,
        )
        if result.returncode == 0 and out_png.exists():
            with open(out_png, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            rendered[sub_id] = f"data:image/png;base64,{b64}"
            print(f"    ✓  {sub_id} → {mmd.name}  ({out_png.stat().st_size // 1024}K, embedded)")
        else:
            print(f"    ✗  {sub_id} ({mmd.name}) — {result.stderr.strip()[:120]}")

    return rendered


def apply_rendered_images(cfg: dict, rendered: dict[str, str]) -> dict:
    """
    Inject base64 image data URLs into newsletter_config editorial fields.
    Only fills image_url where it is currently empty and a rendered image exists.
    Also stores _overview_image_url in _meta for delta_v2.
    Returns a modified copy of cfg (does not mutate original).
    """
    import copy
    cfg  = copy.deepcopy(cfg)
    fmt  = cfg.get("_meta", {}).get("format", "")
    edit = cfg.get("editorial", {})

    # Overview image (delta_v2)
    if "_overview" in rendered:
        cfg["_meta"]["_overview_image_url"] = rendered["_overview"]

    if fmt == "delta_v2":
        for item in edit.get("signals", []):
            sub_id = item.get("subsystem_id", "")
            if not item.get("image_url") and sub_id in rendered:
                item["image_url"] = rendered[sub_id]
    else:
        for section in ("what_held", "what_changed", "what_new"):
            for item in edit.get(section, []):
                sub_id = item.get("subsystem_id", "")
                if not item.get("image_url") and sub_id in rendered:
                    item["image_url"] = rendered[sub_id]
    return cfg


def generate(config_path=None, output_dir=None, render_diagrams=False):
    REPO_ROOT = Path(__file__).resolve().parent.parent.parent
    base = os.path.dirname(os.path.abspath(__file__))
    config_path = config_path or os.path.join(base, "newsletter_config.json")

    with open(config_path) as f:
        cfg = json.load(f)

    fmt = cfg.get("_meta", {}).get("format", "")
    if fmt not in ("system_model_v2", "delta_v1", "delta_v2"):
        print(
            f"❌  Unknown format: '{fmt}' in newsletter_config.json.\n"
            "    Supported: 'system_model_v2' (Issue #1) | 'delta_v1' | 'delta_v2' (Issue #2+)"
        )
        sys.exit(1)

    config_dir = Path(config_path).resolve().parent
    model_path = (config_dir / cfg["_meta"]["system_model_path"]).resolve()
    ann_path   = (config_dir / cfg["_meta"]["annotations_path"]).resolve()

    for p, label in [(model_path, "system_model.json"), (ann_path, "annotations .ts")]:
        if not p.exists():
            print(f"❌  {label} not found: {p}")
            sys.exit(1)

    print(f"\n  → Loading system model:  {model_path.name}")
    with open(model_path) as f:
        model = json.load(f)

    print(f"  → Parsing annotations:   {ann_path.name}")
    annotations = parse_annotations(str(ann_path))
    print(f"     {len(annotations)} annotations parsed")

    # Load subsystems.json (required for subsystem story sections)
    subsystems = []
    subs_rel = cfg["_meta"].get("subsystems_path", "")
    if subs_rel:
        subs_path = (config_dir / subs_rel).resolve()
        if subs_path.exists():
            with open(subs_path) as f:
                subsystems = json.load(f)
            nl_count = sum(1 for s in subsystems if s.get("newsletter"))
            print(f"  → Subsystems loaded:     {len(subsystems)} total, {nl_count} for newsletter")
        else:
            print(f"  ⚠  subsystems.json not found at {subs_path} — subsystem stories will be empty")
            print(f"     Run: python3 generate_mermaid.py first")
    else:
        print("  ⚠  subsystems_path not set in _meta — subsystem stories will be empty")

    featured = cfg.get("editorial", {}).get("featured_annotation_ids", [])
    for fid in featured:
        if fid not in annotations:
            print(f"  ⚠  featured annotation not found: {fid}")

    if not output_dir:
        output_dir = os.path.join(base, "output")
    os.makedirs(output_dir, exist_ok=True)

    today = str(date.today())
    substack_path = os.path.join(output_dir, f"newsletter_{today}_substack.html")

    if fmt in ("delta_v1", "delta_v2"):
        # Auto-render diagrams if --render-diagrams flag is set
        if render_diagrams:
            mermaid_base = REPO_ROOT / "analysis" / "output" / "mermaid" / "rbi_sibc"
            mermaid_dirs = sorted(mermaid_base.glob("????-??-??")) if mermaid_base.exists() else []
            if mermaid_dirs:
                latest_mmd = mermaid_dirs[-1]
                rendered   = render_mermaid_diagrams(cfg, latest_mmd, Path(output_dir))
                cfg        = apply_rendered_images(cfg, rendered)
                print(f"  → {len(rendered)} diagrams rendered (Option A)")
            else:
                print("  ⚠  No mermaid output directories found — skipping diagram rendering")

        if fmt == "delta_v2":
            # Load current-period model for scoreboard data (has stat + value_lcr)
            period_model = model  # fallback
            curr_model_rel = cfg["_meta"].get("current_period_model_path", "")
            if curr_model_rel:
                curr_model_path = (config_dir / curr_model_rel).resolve()
                if curr_model_path.exists():
                    with open(curr_model_path) as f:
                        period_model = json.load(f)
                    print(f"  → Current-period model : {curr_model_path.name} ({curr_model_path.parent.name})")
                else:
                    print(f"  ⚠  current_period_model_path not found: {curr_model_path}")

            # Compute true YoY from consolidated CSV
            yoy_lookup = {}
            csv_rel = cfg["_meta"].get("csv_path", "")
            curr_date = cfg["_meta"].get("csv_curr_date", "")
            prev_ym   = cfg["_meta"].get("csv_prev_year_month", "")
            if csv_rel and curr_date and prev_ym:
                csv_path = (config_dir / csv_rel).resolve()
                yoy_lookup = compute_yoy_from_csv(str(csv_path), curr_date, prev_ym)
                matched = len([k for k in yoy_lookup if k != "sector_bank_credit"])
                print(f"  → YoY from CSV         : {len(yoy_lookup)} sectors computed ({curr_date} vs {prev_ym})")
            else:
                print("  ⚠  csv_path/curr_date/prev_year_month not set — scoreboard uses model FY stats")

            substack = build_delta_v2_substack(cfg, model, period_model, subsystems, annotations, yoy_lookup)
        else:
            substack = build_delta_substack(cfg, model, subsystems)
    else:
        substack = build_substack_html(cfg, model, annotations, subsystems)

    with open(substack_path, "w", encoding="utf-8") as f:
        f.write(substack)

    wc = len(substack.split())

    print(f"\n  ✓  Substack HTML : {substack_path}")
    print(f"\n     Format           : {fmt}")
    print(f"     Period           : {cfg['_meta'].get('period', '')}")

    if fmt in ("delta_v1", "delta_v2"):
        edit = cfg.get("editorial", {})
        print(f"     Prev period      : {cfg['_meta'].get('prev_period', '')}")
        if fmt == "delta_v2":
            sigs = edit.get("signals", [])
            new_c  = sum(1 for s in sigs if s.get("type") == "new")
            corr_c = sum(1 for s in sigs if s.get("type") == "correction")
            conf_c = sum(1 for s in sigs if s.get("type") == "confirmed")
            print(f"     New signals      : {new_c}")
            print(f"     Corrections      : {corr_c}")
            print(f"     Confirmed signals: {conf_c}")
            all_items = sigs
        else:
            print(f"     Held signals     : {len(edit.get('what_held', []))}")
            print(f"     Changed signals  : {len(edit.get('what_changed', []))}")
            print(f"     New signals      : {len(edit.get('what_new', []))}")
            all_items = (
                edit.get("what_held", []) + edit.get("what_changed", []) + edit.get("what_new", [])
            )
        # Flag confirmed signals (no diagram expected) and others missing images
        placeholders = [i.get("signal", "?") for i in all_items
                        if not i.get("image_url") and i.get("subsystem_id")
                        and not (fmt == "delta_v2" and i.get("type") == "confirmed")
                        and i.get("mermaid_file") is not None]
        if placeholders:
            print(f"\n  ⚠  Image placeholders (Option B — fill manually):")
            for sig in placeholders:
                sub_id = next((i.get("subsystem_id","") for i in all_items if i.get("signal") == sig), "")
                slug   = re.sub(r"[^a-z0-9]+", "_", sig.lower()).strip("_")[:30]
                print(f"       {sub_id}_{slug}.png")
            print(f"     → Export from mermaid.live, set image_url in newsletter_config.json,")
            print(f"       then re-run to replace placeholders with real images.")
    else:
        tiers = nodes_by_tier(model)
        print(f"     Annotations      : {len(annotations)} parsed")
        print(f"     Featured signals : {len(featured)}")
        print(f"     Newsletter stories: {sum(1 for s in subsystems if s.get('newsletter'))}")
        print(f"     Nodes rendered   :")
        for tier in ["driver", "sector", "gap", "opportunity", "pressure"]:
            count = len(tiers.get(tier, []))
            if count:
                print(f"       {tier:<12} {count}")

    print(f"     Word count       : ~{wc}")
    print(f"\n  → Open newsletter_{today}_substack.html in browser → Select All → Copy → paste into Substack editor\n")


if __name__ == "__main__":
    import argparse as _ap
    _parser = _ap.ArgumentParser(description="Generate India Credit Lens newsletter")
    _parser.add_argument("config", nargs="?", help="Path to newsletter_config.json")
    _parser.add_argument(
        "--render-diagrams",
        action="store_true",
        help="Option A: auto-render subsystem .mmd files to PNG via mmdc and embed in newsletter",
    )
    _args = _parser.parse_args()
    generate(
        config_path=_args.config,
        render_diagrams=_args.render_diagrams,
    )
