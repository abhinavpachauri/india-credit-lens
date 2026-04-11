#!/usr/bin/env python3
"""
generate_newsletter.py v3 — India Credit Lens
----------------------------------------------
Reads four sources, produces one newsletter (HTML + Markdown).

Sources:
  1. system_model.json       → structure (nodes by tier, causal edges)
  2. rbi_sibc.ts             → content  (annotation title, body, implication)
  3. newsletter_config.json  → editorial (narrative, featured picks, what_to_watch)
  4. subsystems.json         → derived causal stories (newsletter-flagged subsystems)

Newsletter structure:
  HEADER → HERO STAT → TL;DR →
  WHERE CREDIT MOVED (table) → KEY SIGNALS →
  SYSTEM OVERVIEW (image + narrative + signposts) →
  STORY 1 → STORY 2 → STORY 3 →
  WHAT TO WATCH → CTA

From issue #2 onwards: WHAT CHANGED section slides in between TL;DR and
WHERE CREDIT MOVED, auto-generated from delta_model.json (not yet wired).

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

def generate(config_path=None, output_dir=None):
    base = os.path.dirname(os.path.abspath(__file__))
    config_path = config_path or os.path.join(base, "newsletter_config.json")

    with open(config_path) as f:
        cfg = json.load(f)

    fmt = cfg.get("_meta", {}).get("format", "")
    if fmt != "system_model_v2":
        print(
            "❌  This generator requires format: 'system_model_v2' in newsletter_config.json.\n"
            "    Use the new schema."
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
    html_path     = os.path.join(output_dir, f"newsletter_{today}.html")
    substack_path = os.path.join(output_dir, f"newsletter_{today}_substack.html")
    md_path       = os.path.join(output_dir, f"newsletter_{today}.md")

    html     = build_html(cfg, model, annotations, subsystems)
    substack = build_substack_html(cfg, model, annotations, subsystems)
    md       = build_markdown(cfg, model, annotations, subsystems)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    with open(substack_path, "w", encoding="utf-8") as f:
        f.write(substack)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)

    tiers = nodes_by_tier(model)
    wc = len(md.split())

    print(f"\n  ✓  HTML     (archive)  : {html_path}")
    print(f"  ✓  HTML     (substack) : {substack_path}")
    print(f"  ✓  MD                  : {md_path}")
    print(f"\n     Period           : {model.get('_meta', {}).get('period', '')}")
    print(f"     Annotations      : {len(annotations)} parsed")
    print(f"     Featured signals : {len(featured)}")
    print(f"     Newsletter stories: {sum(1 for s in subsystems if s.get('newsletter'))}")
    print(f"     Nodes rendered   :")
    for tier in ["driver", "sector", "gap", "opportunity", "pressure"]:
        count = len(tiers.get(tier, []))
        if count:
            print(f"       {tier:<12} {count}")
    print(f"     Word count       : ~{wc}")
    print(f"\n  → Substack: open newsletter_{today}_substack.html in browser → Select All → Copy → paste into Substack editor")
    print(f"  → Archive:  newsletter_{today}.html — full styled version\n")


if __name__ == "__main__":
    generate(sys.argv[1] if len(sys.argv) > 1 else None)
