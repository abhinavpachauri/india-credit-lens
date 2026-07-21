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


# ── Per-block scoping (rescoped 2026-07-21) ───────────────────────────────────
# The gate used to pool every declared signal for the whole issue and match with the
# card policy's ratio grounding. Measured, it caught 0% of injections. These lock the
# properties that fixed it, because the failure was invisible to hand-written tests.

def test_a_block_is_judged_only_by_the_signals_it_declares():
    """A stat cannot be justified by a neighbouring stat's value."""
    from validate_newsletter import check_doc
    import newsletter_sources as ns
    sibc, atm = "sibc-bank-credit-yoy", "cc-outstanding-yoy"
    vals = ns.total_values("sibc", ns.latest_period("sibc"))
    if sibc not in vals:
        return
    real = ns.fmt_value(*vals[sibc][:2])
    # correct signal → grounded; someone else's signal → not
    ok = [{"type": "statgrid", "items": [{"value": real, "label": "x", "signal": sibc}]}]
    bad = [{"type": "statgrid", "items": [{"value": real, "label": "x", "signal": atm}]}]
    assert check_doc(ok, [sibc]) == []
    assert check_doc(bad, [atm]) != []


def test_an_undeclared_block_grounds_nothing():
    """No fall-back to the issue-wide pool: connective prose carries no figures."""
    from validate_newsletter import check_doc
    doc = [{"type": "p", "text": "The figure stood at 47.3% this month."}]
    assert check_doc(doc, ["sibc-bank-credit-yoy"]) != []


def test_meta_blocks_count_the_document_not_the_data():
    from validate_newsletter import check_doc
    assert check_doc([{"type": "small", "meta": True,
                       "text": "…and 10 more on the dashboard."}], []) == []
    assert check_doc([{"type": "small", "text": "…and 10 more on the dashboard."}], []) != []


def test_headline_keeps_its_quoted_card_after_ungluing():
    """Card text is stripped BEFORE the magnitude unglue — reversing the order made
    the H1's quoted card title read as an ungrounded claim of the template's own."""
    from validate_newsletter import check_doc, legit_card_texts
    card = next((c for c in legit_card_texts() if "L Cr" in c), None)
    if not card:
        return
    assert check_doc([{"type": "h1", "text": f"RBI data, May 2026: {card}"}], []) == []


def test_rendered_magnitudes_are_grounded_by_the_renderer_itself():
    """"₹2.9L Cr" is the reader's form of 294534.6 — the gate accepts it because
    fmt_value produced it, not because a tolerance happened to be wide enough."""
    from validate_newsletter import declared_ground_truth
    from core.traceability import DISTRIBUTION, extract_numbers, matches
    sid = "sibc-pl-cc-abs"
    gt = declared_ground_truth([sid])
    import newsletter_sources as ns
    vals = ns.total_values("sibc", ns.latest_period("sibc"))
    if sid not in vals:
        return
    shown = ns.fmt_value(vals[sid][0], vals[sid][1])          # e.g. "₹2.9L Cr"
    for num in extract_numbers(shown.replace("L Cr", " L Cr"), DISTRIBUTION):
        assert matches(num, gt, DISTRIBUTION), f"{num} from {shown!r} not grounded"


def test_live_issues_still_pass_their_own_gate():
    """The generators must survive the tightening — a gate that blocks true issues
    gets switched off, which is worse than a loose one."""
    import newsletter_sources as ns
    import generate_release_read as release
    import generate_deep_read as deep
    from validate_newsletter import check_doc
    for pipeline in ("sibc", "atm_pos"):
        period = ns.latest_period(pipeline)
        if not period:
            continue
        doc, declared = release.build_doc(pipeline, period)
        assert check_doc(doc, declared, label=pipeline) == []
    doc, _, declared = deep.build_doc()
    assert check_doc(doc, declared, label="deep") == []
