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
    output/newsletter_YYYY-MM-DD.html           ← styled archive version
    output/newsletter_YYYY-MM-DD_substack.html  ← paste into Substack HTML block
    output/newsletter_YYYY-MM-DD.md             ← markdown version
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

def render_mermaid_diagrams(cfg, mermaid_base: Path, output_dir: Path) -> dict[str, str]:
    """
    Option A: render subsystem .mmd files to PNG using mmdc.

    Discovers .mmd files in mermaid_base matching sub_NN_*.mmd,
    renders each to output_dir/images/, and returns a dict mapping
    subsystem_id → absolute PNG path (file:// URL for local HTML).

    Requires: mmdc (npm install -g @mermaid-js/mermaid-cli)
    """
    import shutil
    import subprocess

    mmdc = shutil.which("mmdc")
    if not mmdc:
        print("  ⚠  mmdc not found — install with: npm install -g @mermaid-js/mermaid-cli")
        return {}

    img_dir = output_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    mmd_files = sorted(mermaid_base.glob("sub_*.mmd"))
    if not mmd_files:
        print(f"  ⚠  No sub_*.mmd files found in {mermaid_base}")
        return {}

    rendered: dict[str, str] = {}
    print(f"\n  Rendering {len(mmd_files)} subsystem diagram(s) via mmdc:")

    for mmd in mmd_files:
        # Extract sub_id from filename (e.g. sub_01_gold_price... → sub_01)
        stem   = mmd.stem                              # sub_01_gold_price_at_record_high
        sub_id = "_".join(stem.split("_")[:2])         # sub_01
        out_png = img_dir / f"{stem}.png"

        result = subprocess.run(
            [mmdc, "-i", str(mmd), "-o", str(out_png), "-t", "default", "-b", "white"],
            capture_output=True, text=True,
        )
        if result.returncode == 0 and out_png.exists():
            rendered[sub_id] = out_png.as_uri()   # file:///... — works in local browser
            print(f"    ✓  {sub_id} → {out_png.name}  ({out_png.stat().st_size // 1024}K)")
        else:
            print(f"    ✗  {sub_id} — mmdc error: {result.stderr.strip()[:120]}")

    return rendered


def apply_rendered_images(cfg: dict, rendered: dict[str, str]) -> dict:
    """
    Inject rendered PNG file:// URLs into newsletter_config editorial fields.
    Only fills image_url where it is currently empty and a rendered PNG exists.
    Returns a modified copy of cfg (does not mutate original).
    """
    import copy
    cfg = copy.deepcopy(cfg)
    edit = cfg.get("editorial", {})
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
    if fmt not in ("system_model_v2", "delta_v1"):
        print(
            f"❌  Unknown format: '{fmt}' in newsletter_config.json.\n"
            "    Supported: 'system_model_v2' (Issue #1) | 'delta_v1' (Issue #2+)"
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

    if fmt == "delta_v1":
        # Option A: auto-render diagrams if --render-diagrams flag is set
        if render_diagrams:
            # Look for mermaid outputs in the latest registered period's mermaid dir
            mermaid_base = (REPO_ROOT / "analysis" / "output" / "mermaid" / "rbi_sibc"
                            if True else None)
            if mermaid_base:
                # Use the most recent mermaid subdirectory
                mermaid_dirs = sorted(mermaid_base.glob("????-??-??")) if mermaid_base.exists() else []
                if mermaid_dirs:
                    latest_mmd = mermaid_dirs[-1]
                    rendered   = render_mermaid_diagrams(cfg, latest_mmd, Path(output_dir))
                    cfg        = apply_rendered_images(cfg, rendered)
                    print(f"  → {len(rendered)} diagrams rendered (Option A)")
                else:
                    print("  ⚠  No mermaid output directories found — skipping diagram rendering")
        html     = build_delta_html(cfg, model, subsystems)
        substack = build_delta_substack(cfg, model, subsystems)
        md       = build_delta_markdown(cfg, model, subsystems)
    else:
        html     = build_html(cfg, model, annotations, subsystems)
        substack = build_substack_html(cfg, model, annotations, subsystems)
        md       = build_markdown(cfg, model, annotations, subsystems)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    with open(substack_path, "w", encoding="utf-8") as f:
        f.write(substack)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)

    wc = len(md.split())

    print(f"\n  ✓  HTML     (archive)  : {html_path}")
    print(f"  ✓  HTML     (substack) : {substack_path}")
    print(f"  ✓  MD                  : {md_path}")
    print(f"\n     Format           : {fmt}")
    print(f"     Period           : {cfg['_meta'].get('period', '')}")

    if fmt == "delta_v1":
        edit = cfg.get("editorial", {})
        print(f"     Prev period      : {cfg['_meta'].get('prev_period', '')}")
        print(f"     Held signals     : {len(edit.get('what_held', []))}")
        print(f"     Changed signals  : {len(edit.get('what_changed', []))}")
        print(f"     New signals      : {len(edit.get('what_new', []))}")
        # Flag any image placeholders that need manual fill
        all_items = (
            edit.get("what_held", []) +
            edit.get("what_changed", []) +
            edit.get("what_new", [])
        )
        placeholders = [i.get("signal", "?") for i in all_items if not i.get("image_url") and i.get("subsystem_id")]
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
    print(f"\n  → Substack: open newsletter_{today}_substack.html in browser → Select All → Copy → paste into Substack editor")
    print(f"  → Archive:  newsletter_{today}.html — full styled version\n")


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
