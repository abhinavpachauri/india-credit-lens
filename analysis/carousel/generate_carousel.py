#!/usr/bin/env python3
"""
LinkedIn Carousel Generator — India Credit Lens
------------------------------------------------
Edit carousel_config.json to change content, then run:
    python3 generate_carousel.py

Output: output/carousel_YYYY-MM-DD.pdf

Dependencies:
    pip install reportlab

Mobile-first: slides are 540×675pt. Viewed on LinkedIn mobile at ~375px
wide (scale ≈ 0.70×). Minimum readable body text = 20pt PDF → 14pt mobile.
"""

import json
import os
import sys
from datetime import date

from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import simpleSplit
from io import BytesIO

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Font registration ─────────────────────────────────────────────────────────
# SFNS (San Francisco) is a variable font bundled with macOS.
# It supports the ₹ glyph (U+20B9) and covers the full Latin range.
# We instantiate two static weights (400 = regular, 700 = bold) at startup
# using fonttools so reportlab can embed them as standard TTF streams.

def _sfns_instance(path, wght):
    """Return a BytesIO of SFNS instantiated at the given weight."""
    from fontTools.ttLib import TTFont as FTFont
    from fontTools.varLib.instancer import instantiateVariableFont
    f = FTFont(path)
    instantiateVariableFont(f, {"wght": wght, "opsz": 28})
    buf = BytesIO()
    f.save(buf)
    buf.seek(0)
    return buf

_SFNS_PATH = "/System/Library/Fonts/SFNS.ttf"

if os.path.exists(_SFNS_PATH):
    try:
        pdfmetrics.registerFont(TTFont("SF",    _sfns_instance(_SFNS_PATH, 400)))
        pdfmetrics.registerFont(TTFont("SF-Bd", _sfns_instance(_SFNS_PATH, 700)))
        FONT_REGULAR = "SF"
        FONT_BOLD    = "SF-Bd"
    except Exception:
        FONT_REGULAR = "Helvetica"
        FONT_BOLD    = "Helvetica-Bold"
else:
    FONT_REGULAR = "Helvetica"
    FONT_BOLD    = "Helvetica-Bold"

# ── Slide dimensions (portrait 4:5) ──────────────────────────────────────────
W      = 540
H      = 675
MARGIN   = 40
FOOTER_Y = 14
BAND_H   = int(H * 0.45)   # coloured top band — 45% of slide height (~304pt)

# ── Colour palette ────────────────────────────────────────────────────────────
BG      = HexColor("#FAF7F2")
DARK    = HexColor("#1E293B")
MUTED   = HexColor("#64748B")
SUBTLE  = HexColor("#334155")
DIVIDER = HexColor("#CBD5E1")

BLUE    = HexColor("#2563EB")
AMBER   = HexColor("#D97706")
GREEN   = HexColor("#16A34A")
PURPLE  = HexColor("#7C3AED")

PILL_MAP = {
    # accent   pill_bg         band_bg        label
    "insight":     (BLUE,  HexColor("#DBEAFE"), HexColor("#EBF2FE"), "INSIGHT"),
    "gap":         (AMBER, HexColor("#FDE68A"), HexColor("#FEF6E4"), "GAP"),
    "opportunity": (GREEN, HexColor("#BBF7D0"), HexColor("#EDFDF4"), "OPPORTUNITY"),
}

# ── Type-size reference (PDF pt → effective mobile pt at 0.70× scale) ─────────
# Stat:         62pt → ~43pt  ✅
# Sublabel:     16pt → ~11pt  ✅
# Body:         20pt → ~14pt  ✅
# Lender note:  18pt → ~13pt  ✅
# Footer:        8pt → ~6pt   ✅ (decorative)

# ── Shared helpers ────────────────────────────────────────────────────────────

def draw_bg(c):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)


def draw_divider(c, y):
    c.setStrokeColor(DIVIDER)
    c.setLineWidth(0.75)
    c.line(MARGIN, y, W - MARGIN, y)


def draw_footer(c, branding):
    c.setFont(FONT_REGULAR, 8)
    c.setFillColor(MUTED)
    c.drawCentredString(W / 2, FOOTER_Y, branding["site"])


def draw_pill(c, label, fg, bg_col):
    x, y = MARGIN, H - 28
    c.setFont(FONT_BOLD, 9)
    tw        = c.stringWidth(label, FONT_BOLD, 9)
    pw, ph, r = tw + 18, 19, 7
    c.setFillColor(bg_col)
    c.roundRect(x, y - ph + 4, pw, ph, r, fill=1, stroke=0)
    c.setFillColor(fg)
    c.drawString(x + 9, y - ph + 9, label)


def draw_centered(c, text, font, size, color, y, max_w=None, leading_mult=1.6):
    """Draw centre-aligned wrapped text. Returns y after last line."""
    if max_w is None:
        max_w = W - MARGIN * 2
    c.setFont(font, size)
    c.setFillColor(color)
    lines = simpleSplit(text, font, size, max_w)
    for ln in lines:
        c.drawCentredString(W / 2, y, ln)
        y -= size * leading_mult
    return y


# ── Slide renderers ───────────────────────────────────────────────────────────

def slide_cover(c, cfg, branding, total_slides):
    draw_bg(c)

    # Report name + date
    c.setFont(FONT_REGULAR, 9)
    c.setFillColor(MUTED)
    c.drawString(MARGIN, H - 40, cfg["report_name"])
    c.drawRightString(W - MARGIN, H - 40, cfg["date"])
    draw_divider(c, H - 52)

    # Hook stat
    c.setFont(FONT_BOLD, 52)
    c.setFillColor(DARK)
    c.drawCentredString(W / 2, H * 0.52, cfg["hook_stat"])

    c.setFont(FONT_REGULAR, 13)
    c.setFillColor(MUTED)
    c.drawCentredString(W / 2, H * 0.52 - 26, cfg["hook_label"])

    draw_divider(c, H * 0.52 - 46)

    # Hook detail
    y = H * 0.52 - 72
    y = draw_centered(c, cfg["hook_detail"], FONT_REGULAR, 14, DARK, y)

    draw_divider(c, y - 14)

    # Contents strip
    y -= 36
    draw_centered(c, cfg.get("contents", ""), FONT_REGULAR, 12, MUTED, y)

    # Brand
    c.setFont(FONT_BOLD, 12)
    c.setFillColor(BLUE)
    c.drawCentredString(W / 2, 40, "India Credit Lens")
    draw_footer(c, branding)


def slide_content(c, cfg, slide_type, branding, slide_num, total_slides):
    draw_bg(c)
    fg, pill_bg, band_bg, label = PILL_MAP[slide_type]

    band_bot = H - BAND_H

    # ── Coloured band ─────────────────────────────────────────────────────────
    c.setFillColor(band_bg)
    c.rect(0, band_bot, W, BAND_H, fill=1, stroke=0)

    # Pill + slide counter
    draw_pill(c, label, fg, pill_bg)
    c.setFont(FONT_REGULAR, 9)
    c.setFillColor(MUTED)
    c.drawRightString(W - MARGIN, H - 32, f"{slide_num} / {total_slides}")

    # Stat — vertically centred in upper 60% of the band
    stat_centre_y = band_bot + BAND_H * 0.56
    c.setFont(FONT_BOLD, 62)
    c.setFillColor(fg)
    c.drawCentredString(W / 2, stat_centre_y, cfg["stat"])

    # Sublabel — below stat with proper clearance for a 62pt font
    # Gap = descender depth (~14pt) + visual breath (18pt) = ~32pt below baseline
    sub = cfg.get("stat_sublabel", "")
    if sub:
        sub_y = stat_centre_y - 48
        draw_centered(c, sub, FONT_REGULAR, 16, MUTED, sub_y)

    # ── Content zone (below band) — vertically centred ───────────────────────
    max_w       = W - MARGIN * 2 - 10
    body_lead   = 1.7
    lender_lead = 1.6
    lender      = cfg.get("lender_note", "")

    # Measure body height
    body_lines = simpleSplit(cfg["body"], FONT_BOLD, 20, max_w)
    body_h     = len(body_lines) * 20 * body_lead

    # Measure lender section height (divider gap + label + note)
    if lender:
        lender_lines = simpleSplit(lender, FONT_REGULAR, 18, max_w)
        lender_h     = len(lender_lines) * 18 * lender_lead
        separator_h  = 28 + 26 + 10 + 26   # gap-above-div + gap-below-div + label + gap-below-label
        total_h      = body_h + separator_h + lender_h
    else:
        total_h = body_h

    # Available zone: band_bot down to just above footer
    available = band_bot - (FOOTER_Y + 24)
    top_pad   = max(16, (available - total_h) / 2)
    y         = band_bot - top_pad

    # Draw body
    y = draw_centered(c, cfg["body"], FONT_BOLD, 20, DARK, y,
                      max_w=max_w, leading_mult=body_lead)

    # Draw lender section
    if lender:
        y -= 28
        draw_divider(c, y)
        y -= 26
        c.setFont(FONT_BOLD, 10)
        c.setFillColor(fg)
        c.drawCentredString(W / 2, y, "FOR LENDERS")
        y -= 26
        draw_centered(c, lender, FONT_REGULAR, 18, DARK,
                      y, max_w=max_w, leading_mult=lender_lead)

    draw_footer(c, branding)


def slide_cta(c, cfg, branding, slide_num, total_slides):
    draw_bg(c)

    # Blue accent bar at top
    c.setFillColor(BLUE)
    c.rect(0, H - 5, W, 5, fill=1, stroke=0)

    # Heading
    c.setFont(FONT_BOLD, 26)
    c.setFillColor(DARK)
    c.drawCentredString(W / 2, H - 80, cfg["heading"])

    c.setFont(FONT_REGULAR, 13)
    c.setFillColor(MUTED)
    c.drawCentredString(W / 2, H - 108, cfg["count_line"])

    draw_divider(c, H - 128)

    # CTA cards
    def cta_card(label, url, y_centre, accent):
        bw, bh, r = W - MARGIN * 2, 80, 10
        bx = MARGIN
        by = y_centre - bh / 2
        c.setFillColor(HexColor("#F1F5F9"))
        c.roundRect(bx, by, bw, bh, r, fill=1, stroke=0)
        c.setFillColor(accent)
        c.roundRect(bx, by, 4, bh, 2, fill=1, stroke=0)
        c.setFont(FONT_BOLD, 15)
        c.setFillColor(DARK)
        c.drawCentredString(W / 2, by + bh - 28, label)
        c.setFont(FONT_REGULAR, 13)
        c.setFillColor(accent)
        c.drawCentredString(W / 2, by + 20, url)

    cta_card("Explore on the dashboard",      branding["site"],     H - 265, BLUE)
    cta_card("Get the full monthly analysis",  branding["substack"], H - 420, PURPLE)

    c.setFont(FONT_BOLD, 11)
    c.setFillColor(BLUE)
    c.drawCentredString(W / 2, 42, "India Credit Lens")
    draw_footer(c, branding)


# ── Main ──────────────────────────────────────────────────────────────────────

def generate(config_path=None, output_dir=None):
    base = os.path.dirname(os.path.abspath(__file__))
    config_path = config_path or os.path.join(base, "carousel_config.json")
    output_dir  = output_dir  or os.path.join(base, "output")

    with open(config_path) as f:
        cfg = json.load(f)

    total = (1
             + len(cfg["insights"])
             + len(cfg["gaps"])
             + len(cfg["opportunities"])
             + 1)

    os.makedirs(output_dir, exist_ok=True)
    out = os.path.join(output_dir, f"carousel_{date.today()}.pdf")

    cv = canvas.Canvas(out, pagesize=(W, H))
    b  = cfg["branding"]

    slide_cover(cv, cfg["cover"], b, total)
    cv.showPage()

    n = 2
    for s in cfg["insights"]:
        slide_content(cv, s, "insight", b, n, total);      n += 1;  cv.showPage()
    for s in cfg["gaps"]:
        slide_content(cv, s, "gap", b, n, total);          n += 1;  cv.showPage()
    for s in cfg["opportunities"]:
        slide_content(cv, s, "opportunity", b, n, total);  n += 1;  cv.showPage()

    slide_cta(cv, cfg["cta"], b, n, total)
    cv.showPage()

    cv.save()
    print(f"✓  Generated: {out}  ({total} slides)")


if __name__ == "__main__":
    config = sys.argv[1] if len(sys.argv) > 1 else None
    generate(config)
