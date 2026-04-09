#!/usr/bin/env python3
"""
generate_newsletter.py v2 — India Credit Lens
----------------------------------------------
Reads three sources, produces one newsletter (HTML + Markdown).

Sources:
  1. system_model.json    → structure (nodes by tier, causal edges)
  2. rbi_sibc.ts          → content  (annotation title, body, implication)
  3. newsletter_config.json → editorial (narrative, featured picks, what_to_watch)

Newsletter follows the system model's causal order:
  HOOK → TL;DR → NARRATIVE [+flowchart] → DRIVERS →
  WHERE CREDIT MOVED → KEY SIGNALS → OPPORTUNITIES [+quadrant] →
  RISKS → GAPS [+sankey] → WHAT TO WATCH → CTA

Usage:
    python3 generate_newsletter.py
    python3 generate_newsletter.py newsletter_config.json

Output:
    output/newsletter_YYYY-MM-DD.html   ← paste into Substack HTML block
    output/newsletter_YYYY-MM-DD.md     ← markdown version
"""

import json
import os
import re
import sys
from pathlib import Path
from datetime import date


# ── Tier colour palette (matches system_model.json / dashboard) ───────────────

TIER_COLOR = {
    "driver":      {"bg": "#1E3A5F", "fg": "#ffffff", "accent": "#7eb8e8"},
    "sector":      {"bg": "#F0FDF4", "fg": "#166534", "accent": "#166534"},
    "gap":         {"bg": "#F9FAFB", "fg": "#374151", "accent": "#6B7280"},
    "opportunity": {"bg": "#0F766E", "fg": "#ffffff", "accent": "#5eead4"},
    "pressure":    {"bg": "#FEF3C7", "fg": "#92400E", "accent": "#B45309"},
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
        "insights":     "insight",
        "gaps":         "gap",
        "opportunities": "opportunity",
    }

    for raw in lines:
        stripped = raw.strip()

        # Track annotation type from containing array key
        for marker, typ in type_map.items():
            if re.match(rf"^\s*{marker}:\s*\[", raw):
                current_type = typ
                break

        # Multi-line field continuation
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
                # Unexpected — close field
                current[in_field] = "".join(field_parts)
                in_field = None
                field_parts = []

        # New annotation: id field
        m = re.match(r'^id:\s+"([^"]+)"', stripped)
        if m:
            if current and "id" in current:
                result[current["id"]] = current
            current = {"id": m.group(1), "type": current_type}
            continue

        if current is None:
            continue

        # Single-line string fields
        for field in ["title", "preferredMode"]:
            m = re.match(rf'^{field}:\s+"([^"]+)"', stripped)
            if m:
                current[field] = m.group(1)
                break

        # Multi-line string fields (body, implication)
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

    # Save last annotation
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


def diagram_box(title, filename, description):
    return (
        f'<div style="margin:28px 0;padding:28px 24px;background:#f4f0e8;'
        f'border:2px dashed #c9a96e;text-align:center;border-radius:3px">'
        f'<div style="font-size:1.6em;margin-bottom:8px">📊</div>'
        f'<div style="font-family:system-ui,sans-serif;font-weight:700;'
        f'color:#7a5c30;margin-bottom:4px">{title}</div>'
        f'<div style="font-family:system-ui,sans-serif;font-size:0.85em;color:#9a7c55">'
        f'{description}</div>'
        f'<div style="font-family:system-ui,sans-serif;font-size:0.75em;'
        f'color:#b8a080;margin-top:6px">'
        f'Preview: paste <code style="background:#e8ddc8;padding:2px 5px">'
        f'{filename}</code> at mermaid.live → Export PNG → replace this box</div>'
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


def build_narrative(editorial):
    narrative = editorial.get("system_narrative", "")
    return (
        f'<div style="padding:0 40px">'
        + section_heading("", "The System This Month", "#1a0f00", "#c9a96e")
        + f'<p style="color:#2c1e0f;line-height:1.85;font-size:1.02em">{narrative}</p>'
        + f'</div>'
    )


def build_drivers(driver_nodes):
    if not driver_nodes:
        return ""
    cards = ""
    for d in driver_nodes:
        stat_html = (
            f'<span style="font-family:system-ui;font-size:0.78em;'
            f'color:#7eb8e8;margin-left:10px">{d["stat"]}</span>'
        ) if d.get("stat") else ""
        cards += (
            f'<div style="margin:10px 0;padding:16px 20px;'
            f'background:#1E3A5F;border-radius:2px">'
            f'<div style="font-family:system-ui,sans-serif;font-weight:600;'
            f'color:#ffffff;margin-bottom:5px">{d["label"]}{stat_html}</div>'
            f'<div style="color:#a0b8d4;font-size:0.88em;line-height:1.5">'
            f'{d.get("description", "")}</div>'
            f'</div>'
        )
    return (
        f'<div style="padding:0 40px">'
        + section_heading("⚡", "What's Driving This", "#1E3A5F", "#1E3A5F")
        + f'<p style="color:#7a5c30;font-size:0.88em;margin:-12px 0 16px">'
        + f'Seven macro forces moving the credit system. '
        + f'Understanding these is more useful than reading the headline numbers.</p>'
        + cards
        + f'</div>'
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


def build_opportunities(opp_nodes, annotations):
    if not opp_nodes:
        return ""
    cards = ""
    for node in opp_nodes:
        ann   = node_primary_annotation(node, annotations)
        stat  = node.get("stat", "")
        desc  = node.get("description", "")
        body  = ann.get("body", desc) if ann else desc
        impl  = ann.get("implication", "") if ann else ""
        if len(body) > 320:
            body = body[:317] + "…"
        cards += side_card(stat, node["label"], body, impl, "#0F766E", "#0F766E")
    return (
        f'<div style="padding:0 40px">'
        + section_heading("🎯", "Where to Play", "#0F766E", "#0F766E")
        + cards
        + f'</div>'
    )


def build_risks(pressure_nodes, annotations):
    if not pressure_nodes:
        return ""
    cards = ""
    for node in pressure_nodes:
        ann  = node_primary_annotation(node, annotations)
        impl = ann.get("implication", "") if ann else ""
        cards += side_card(
            node.get("stat", ""), node["label"],
            node.get("description", ""), impl,
            "#B45309", "#B45309", "#92400E"
        )
    return (
        f'<div style="padding:0 40px">'
        + section_heading("⚠️", "What Could Break", "#B45309", "#B45309")
        + f'<p style="color:#7a5c30;font-size:0.88em;margin:-12px 0 16px">'
        + f'Latent risks not visible in the headline growth number.</p>'
        + cards
        + f'</div>'
    )


def build_gaps(gap_nodes, annotations):
    if not gap_nodes:
        return ""
    cards = ""
    for node in gap_nodes:
        ann  = node_primary_annotation(node, annotations)
        impl = ann.get("implication", "") if ann else ""
        cards += side_card(
            node.get("stat", ""), node["label"],
            node.get("description", ""), impl,
            "#6B7280", "#6B7280", "#374151"
        )
    return (
        f'<div style="padding:0 40px">'
        + section_heading("🔍", "What We Can't See", "#374151", "#6B7280")
        + f'<p style="color:#7a5c30;font-size:0.88em;margin:-12px 0 16px">'
        + f'Data gaps that limit or distort interpretation of the numbers above.</p>'
        + cards
        + f'</div>'
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


# ── HTML builder ──────────────────────────────────────────────────────────────

def build_html(cfg, model, annotations):
    meta  = model.get("_meta", {})
    edit  = cfg.get("editorial", {})
    tiers = nodes_by_tier(model)

    parts = [
        build_header(cfg, meta),
        build_hook(meta),
        build_tldr(edit),
        divider(),
        build_narrative(edit),
        diagram_box(
            "SYSTEM FLOW DIAGRAM", "flowchart.mmd",
            "Causal map: what's driving the system → where credit moved → risks & opportunities"
        ),
        divider(),
        build_drivers(tiers.get("driver", [])),
        divider(),
        build_sectors_scoreboard(tiers.get("sector", [])),
        divider(),
        build_key_signals(edit.get("featured_annotation_ids", []), tiers, annotations),
        divider(),
        build_opportunities(tiers.get("opportunity", []), annotations),
        diagram_box(
            "CREDIT OPPORTUNITY MAP", "quadrant.mmd",
            "Growth rate vs credit stock — where to build, scale, or harvest"
        ),
        divider(),
        build_risks(tiers.get("pressure", []), annotations),
        divider(),
        build_gaps(tiers.get("gap", []), annotations),
        diagram_box(
            "CREDIT ALLOCATION — SANKEY", "sankey.mmd",
            "Where ₹204.8L Cr is flowing across sectors (band width = ₹L Cr)"
        ),
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

def build_markdown(cfg, model, annotations):
    meta  = model.get("_meta", {})
    edit  = cfg.get("editorial", {})
    tiers = nodes_by_tier(model)
    period  = meta.get("period", "")
    total   = meta.get("total_credit_lcr", "")
    growth  = meta.get("yoy_growth_pct", "")
    issue   = cfg["_meta"].get("issue_number", 1)
    pub     = cfg["_meta"].get("published", "")
    brand   = cfg.get("branding", {})
    cta_cfg = cfg.get("cta", {})
    issue_t = edit.get("issue_title", period)
    featured = edit.get("featured_annotation_ids", [])

    lines = []
    lines += [
        f"# India Credit Lens — {period}: {issue_t}",
        f"*Issue #{issue} · {pub} · {brand.get('site', '')}*",
        "",
        "---",
        "",
        f"## ₹{total}L Cr",
        f"**Total bank credit outstanding · {period}**",
        f"+{growth}% YoY — fastest growth rate in this dataset.",
        "",
        "---",
        "",
        "## TL;DR",
        "",
    ]
    for b in edit.get("tldr", []):
        lines.append(f"- {b}")
    lines += ["", "---", ""]

    lines += ["## The System This Month", "", edit.get("system_narrative", ""), "",
              "> 📊 **[DIAGRAM: flowchart.mmd]**", "", "---", ""]

    lines += ["## ⚡ What's Driving This", ""]
    for d in tiers.get("driver", []):
        s = f" · {d['stat']}" if d.get("stat") else ""
        lines += [f"**{d['label']}{s}**", d.get("description", ""), ""]
    lines += ["---", ""]

    # Sectors scoreboard
    EXCLUDE = {"sector_total_credit"}
    sector_rows = sorted(
        [(n, parse_growth_pct(n.get("stat"))) for n in tiers.get("sector", [])
         if n["id"] not in EXCLUDE],
        key=lambda x: x[1] if x[1] is not None else -9999,
        reverse=True,
    )
    lines += ["## 📊 Where Credit Moved", "",
              "| Sector | YoY Growth | Outstanding |",
              "| --- | --- | --- |"]
    for node, _ in sector_rows:
        vol = f'₹{node["value_lcr"]}L Cr' if node.get("value_lcr") else "—"
        lines.append(f'| {node["label"]} | {node.get("stat","—")} | {vol} |')
    lines += ["", "---", ""]

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
        lines.append("")
    lines += ["---", ""]

    lines += ["## 🎯 Where to Play", ""]
    for node in tiers.get("opportunity", []):
        ann  = node_primary_annotation(node, annotations)
        stat = node.get("stat", "")
        desc = node.get("description", "")
        body = ann.get("body", desc) if ann else desc
        impl = ann.get("implication", "") if ann else ""
        lines += [f"**{node['label']}** · {stat}", body,
                  f"*{impl}*" if impl else "", ""]
    lines += ["> 📊 **[DIAGRAM: quadrant.mmd]**", "", "---", ""]

    lines += ["## ⚠️ What Could Break", ""]
    for node in tiers.get("pressure", []):
        s = f" · {node['stat']}" if node.get("stat") else ""
        lines += [f"**{node['label']}{s}**", node.get("description", ""), ""]
    lines += ["---", ""]

    lines += ["## 🔍 What We Can't See", ""]
    for node in tiers.get("gap", []):
        ann  = node_primary_annotation(node, annotations)
        impl = ann.get("implication", "") if ann else ""
        s    = f" · {node['stat']}" if node.get("stat") else ""
        lines += [f"**{node['label']}{s}**", node.get("description", ""),
                  f"*{impl}*" if impl else "", ""]
    lines += ["> 📊 **[DIAGRAM: sankey.mmd]**", "", "---", ""]

    watch = edit.get("what_to_watch", {})
    lines += ["## 📅 What to Watch Next",
              f"*Next release: {watch.get('next_release', '')}*", ""]
    for b in watch.get("bullets", []):
        lines.append(f"- {b}")
    lines += ["", "---", ""]

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

def generate(config_path=None, output_dir=None):
    base = os.path.dirname(os.path.abspath(__file__))
    config_path = config_path or os.path.join(base, "newsletter_config.json")

    with open(config_path) as f:
        cfg = json.load(f)

    fmt = cfg.get("_meta", {}).get("format", "")
    if fmt != "system_model_v2":
        print(
            "❌  This generator requires format: 'system_model_v2' in newsletter_config.json.\n"
            "    The old simple/full format is superseded. Use the new schema."
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

    featured = cfg.get("editorial", {}).get("featured_annotation_ids", [])
    for fid in featured:
        if fid not in annotations:
            print(f"  ⚠️   Featured annotation '{fid}' not found — skipped")

    output_dir = output_dir or os.path.join(base, "output")
    os.makedirs(output_dir, exist_ok=True)
    today = date.today()

    html_content = build_html(cfg, model, annotations)
    md_content   = build_markdown(cfg, model, annotations)

    html_path = os.path.join(output_dir, f"newsletter_{today}.html")
    md_path   = os.path.join(output_dir, f"newsletter_{today}.md")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    meta  = model.get("_meta", {})
    tiers = nodes_by_tier(model)
    words = len(md_content.split())

    print(f"\n  ✓  HTML : {html_path}")
    print(f"  ✓  MD   : {md_path}")
    print(f"\n     Period           : {meta.get('period', '')}")
    print(f"     Annotations      : {len(annotations)} parsed")
    print(f"     Featured signals : {len(featured)}")
    print(f"     Nodes rendered   :")
    for tier, nodes in tiers.items():
        print(f"       {tier:<12} {len(nodes)}")
    print(f"     Word count       : ~{words}")
    print(f"\n  → Open {os.path.basename(html_path)} in browser to preview")
    print(f"  → Paste HTML into Substack Settings → Custom HTML block")
    print()


if __name__ == "__main__":
    config = sys.argv[1] if len(sys.argv) > 1 else None
    generate(config)
