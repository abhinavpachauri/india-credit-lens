#!/usr/bin/env python3
"""
Unit tests for the newsletter v2 rendering + traceability layer.

Covers the semantics the generators rely on:
  - fmt_value unit rendering (the numbers readers see must match what checks accept)
  - md_render block shapes (heading spacing — a silent Substack-paste bug otherwise)
  - check_doc gate: invented template numbers fail, reworded cards fail,
    verbatim cards + grounded template numbers pass (negative-tested live too)

Run: python3 -m pytest analysis/tests/test_newsletter.py -q
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "newsletter"))

from newsletter_render import md_render                    # noqa: E402
from newsletter_sources import STATUS_WORD, fmt_value      # noqa: E402


def test_fmt_value_units():
    assert fmt_value(16.04, "pct") == "16.0%"
    assert fmt_value(20.14, "pp") == "20.1pp"
    assert fmt_value(21211828.0, "lcr_cr") == "₹212.1L Cr"     # stored ₹Cr → shown L Cr
    assert fmt_value(119436129.0, "count") == "11.9 crore"
    assert fmt_value(250000.0, "count") == "2.5 lakh"
    assert fmt_value(None, "pct") == ""


def test_status_words_are_plain_english():
    # reader-facing words — no analyst jargon leaks
    banned = {"strengthening", "weakening", "active", "declining"}
    assert banned.isdisjoint(set(STATUS_WORD.values()))


def test_md_render_h2_has_blank_line_before():
    doc = [{"type": "li", "text": "item"}, {"type": "h2", "text": "Next section"}]
    md = md_render(doc)
    assert "- item\n\n\n## Next section" in md or "- item\n\n## Next section" in md


def test_md_render_card_shape():
    doc = [{"type": "card", "title": "T", "body": "B", "implication": "I"}]
    md = md_render(doc)
    assert "**T**" in md and "> So what: I" in md


def test_check_doc_number_scoping(monkeypatch):
    """The number gate must reject values outside the declared ground truth.
    Ground truth is CONTROLLED here — a live-db fixture proved flaky (a new
    period's series made an 'invented' number collide with a real ratio)."""
    import validate_newsletter as vn

    monkeypatch.setattr(vn, "declared_ground_truth", lambda ids: [16.0, 212.1])
    bad = [{"type": "p", "text": "Bank credit grew 47.31% to ₹9,999.9L Cr."}]
    assert vn.check_doc(bad, ["any"], "t")
    good = [{"type": "p", "text": "Bank credit grew 16.0% to ₹212.1L Cr."}]
    assert vn.check_doc(good, ["any"], "t") == []


def test_check_doc_card_verbatim_live_artifacts():
    """Cards must match a validated feed verbatim — reworded fails, verbatim passes.
    Uses the live feed (stable within a run; text content is the fixture)."""
    import json
    from validate_newsletter import check_doc

    root = Path(__file__).resolve().parents[2]
    feed = json.loads((root / "web/public/data/sibc_l1_annotations.json").read_text())
    card = feed["sections"]["bankCredit"]["insights"][0]

    reworded = [{"type": "card", "title": card["title"], "body": card["body"] + " Truly."}]
    assert check_doc(reworded, [], "t")

    verbatim = [{"type": "card", "title": card["title"], "body": card["body"],
                 "implication": card["implication"]}]
    assert check_doc(verbatim, [], "t") == []
