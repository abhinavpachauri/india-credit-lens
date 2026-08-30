"""Negative tests for the card↔chart cut check (DASHBOARD_SPEC §15.7).

A gate that has never been shown a fault it must catch is a gate nobody has
measured. Each test injects one defect of a shape the check claims to catch and
asserts it is reported; the clean-baseline tests assert the check does not
invent findings on cards that are already correct.
"""
import json
import sys
from pathlib import Path

import pytest

ANALYSIS = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"
sys.path.insert(0, str(ANALYSIS))
from core import cuts as C                   # noqa: E402
from guards import validate_card_cuts as vcc  # noqa: E402


# ── C1/C3: the cut a signal was computed over ─────────────────────────────────

def test_sibc_cut_reads_a_decomposition_off_the_compute_spec():
    cut = C.sibc_cut({"parent_code": "2.13", "child_level": 3, "statement": "Statement 2"})
    assert cut.shape == "decomposition"
    assert (cut.parent_code, cut.child_level, cut.statement) == ("2.13", 3, "Statement 2")


def test_sibc_cut_is_a_share_when_a_denominator_is_named():
    cut = C.sibc_cut({"parent_code": "2.13", "child_level": 3, "statement": "Statement 2",
                      "denominator_code": "2.13"})
    assert cut.shape == "share_of" and cut.denominator == "2.13"


def test_sibc_scalar_signal_is_a_level_cut():
    """A single entity's own series is the `level` shape — it must not be
    reported as mis-charted, which is the check's main false-rejection risk."""
    cut = C.sibc_cut({"method": "csv_sector_yoy", "code": "4.5"})
    assert cut.shape == "level" and cut.codes == ("4.5",)


def test_atm_pos_share_pulls_in_its_whole_denominator():
    cut = C.atm_pos_cut({"metric": "cc_ecom_txn_vol",
                         "denominator_metrics": ["cc_pos_txn_vol", "cc_ecom_txn_vol"]})
    assert cut.shape == "share_of"
    assert cut.metrics == ("cc_ecom_txn_vol", "cc_pos_txn_vol")


def test_atm_pos_pair_pulls_in_both_sides():
    cut = C.atm_pos_cut({"a": {"metrics": ["pos_terminals"]},
                         "b": {"metrics": ["cc_pos_txn_val", "dc_pos_txn_val"]}})
    assert cut.shape == "pair"
    assert "pos_terminals" in cut.metrics and "dc_pos_txn_val" in cut.metrics


def test_atm_pos_ratio_denominator_is_part_of_the_claim():
    """'UPI QR is 150.5x Bharat QR' is a claim about two metrics. Drawing one of
    them is the payments form of the sub-cut defect."""
    cut = C.atm_pos_cut({"metric": "upi_qr", "denominator_metric": "bharat_qr"})
    assert cut.metrics == ("bharat_qr", "upi_qr")


# ── the live defects this was built for ───────────────────────────────────────

def test_catches_a_cut_the_chart_cannot_draw():
    """The defect that started this — Iron & Steel (children of 2.13) charted as Basic
    Metal (a child of 2) — is fixed in §15.6a, so this drives the check synthetically
    with a cut no chart in the section can render: the children of Power (2.18.1),
    which RBI does not break down."""
    feed = {"sections": {"industryByType": {"insights": [{
        "id": "sibc-industry-type-share-scan",
        "effect": {"cut": {"shape": "decomposition", "parent_code": "2.18.1",
                           "child_level": 4, "statement": "Statement 2"}}}]}}}
    assert any(f.startswith("[C1") for f in vcc.check_sibc(feed=feed))


def test_the_card_that_started_this_is_now_charted_on_its_own_cut():
    """Iron and Steel holds 69.0% of basic-metals credit — and the chart under it now
    draws the two sub-types that share out to 69/31, not the parent's 11.2% of industry."""
    assert not [f for f in vcc.check_sibc() if "sibc-basic-metal-sub-share-scan" in f]


def test_catches_a_highlight_that_renders_nothing():
    """Driven synthetically, not off the live feed: the seven dead highlights this
    found ('Power', 'Education Loans', the raw CSV names) were fixed in §15.4, and a
    check whose only test is a defect that no longer exists is not a tested check."""
    feed = {"sections": {"industryByType": {"insights": [{
        "id": "sibc-industry-type-share-scan",
        "effect": {"highlight": ["Power"],
                   "cut": {"shape": "decomposition", "parent_code": "2",
                           "child_level": 2, "statement": "Statement 2"}}}]}}}
    found = vcc.check_sibc(feed=feed)
    assert any("'Power'" in f and f.startswith("[C2") for f in found)


def test_no_card_in_the_live_feed_highlights_a_series_that_renders_nothing():
    """The §15.4 fix, asserted: highlights are derived from the chart's own
    vocabulary, so none of the 95 cards can name something it does not draw."""
    assert not [f for f in vcc.check_sibc() if f.startswith("[C2")]


def test_catches_a_focus_card_that_is_not_a_section():
    """gap-atm-offsite-decline pointed at 'atm_offsite', which is a METRIC not a
    section; AtmReadMode's `?? SECTION_DEFS.find(d => d.group === group)` resolved
    it to the first infra section, so a card about off-site ATMs drew POS terminals.
    Fixed in §15.4 — driven synthetically so the check stays tested."""
    found = vcc.check_atm_pos(cards=[{"id": "made-up", "effect": {
        "focusCard": "atm_offsite", "cut": {"shape": "level", "metrics": ["atm_offsite"]}}}])
    assert any("is not a section that renders a chart" in f for f in found)


def test_no_live_card_points_at_a_section_that_does_not_exist():
    for f in vcc.check_atm_pos():
        assert "is not a section that renders a chart" not in f


def test_catches_a_level_claim_reaching_outside_its_section():
    """A share or a pair renders on its own metrics now (§15.6 b/c), but a `level` claim
    has no such builder — it must sit on a section that actually draws it."""
    found = vcc.check_atm_pos(cards=[{"id": "made-up", "effect": {
        "focusCard": "upi_qr",
        "cut": {"shape": "level", "metrics": ["pos_terminals"]}}}])
    assert any(f.startswith("[C1") for f in found)


def test_live_pair_cards_now_chart_both_sides():
    assert not [f for f in vcc.check_atm_pos() if "pos-fleet-vs-spend-gap" in f]


def test_catches_an_undeclared_cut():
    """A card that declares nothing must not read as a card that declares the
    right thing — the failure shape this project keeps meeting. Synthetic, because
    §15.4 left the live feeds with none."""
    found = vcc.check_atm_pos(cards=[{"id": "made-up", "effect": {"focusCard": "upi_qr"}}])
    assert any(f.startswith("[C4") for f in found)


def test_every_live_card_declares_a_cut():
    assert not [f for f in vcc.check_sibc() if f.startswith("[C4")]
    assert not [f for f in vcc.check_atm_pos() if f.startswith("[C4")]


def test_a_declared_cut_may_not_disagree_with_the_signal_that_computed_it():
    """C5 — the declaration is the contract, the registry is the cross-check. A
    disagreement means a stale feed, which is the drift this whole check exists
    to make visible."""
    feed = {"sections": {"industryByType": {"insights": [{
        "id": "sibc-basic-metal-sub-share-scan",
        "effect": {"cut": {"shape": "decomposition", "parent_code": "2",
                           "child_level": 2, "statement": "Statement 2"}}}]}}}
    assert any(f.startswith("[C5") for f in vcc.check_sibc(feed=feed))


def test_no_live_card_disagrees_with_its_signal():
    assert not [f for f in vcc.check_sibc() if f.startswith("[C5")]
    assert not [f for f in vcc.check_atm_pos() if f.startswith("[C5")]


# ── false rejection: cards that are correct must stay silent ──────────────────

@pytest.mark.parametrize("card_id", [
    "sibc-industry-type-share-scan",   # children of 2, charted as children of 2
    "sibc-industry-type-yoy-scan",
    "sibc-pl-share-scan",
    "sibc-services-yoy-scan",
    "sibc-industry-rotation",
])
def test_aligned_cards_are_not_flagged(card_id):
    found = vcc.check_sibc(strict=False)
    assert not any(card_id in f for f in found), f"false rejection on {card_id}"


@pytest.mark.parametrize("card_id", ["cc-cards-yoy", "dc-cards-yoy", "infra-upi-yoy",
                                     "cc-bank-divergence", "cc-category-rotation"])
def test_aligned_payments_cards_are_not_flagged(card_id):
    found = vcc.check_atm_pos(strict=False)
    assert not any(card_id in f for f in found), f"false rejection on {card_id}"


def test_label_lookup_is_scoped_by_statement():
    """Code 2.3 is 'Large' in Statement 1 and 'Beverage and Tobacco' in Statement 2.
    An unscoped lookup silently mislabels a whole section — it flagged 20 correct
    cards on the first run of this check."""
    secs = C.sibc_sections()
    assert secs["industryBySize"]["labels"]["2.3"] == "Large"
    assert secs["industryByType"]["labels"]["2.3"] == "Beverage and Tobacco"


def test_declared_section_cut_matches_what_the_chart_is_drawn_from():
    """section_cuts.json is a second description of what buildSections() renders.
    It may not drift: every declared payments metric must exist in the artifact
    the chart actually reads."""
    found = vcc.check_atm_pos(strict=False)
    assert not any("is not in atm_pos_chart_series.json" in f for f in found)


def test_c2_tests_the_literal_string_not_resolvability():
    """The web layer matches a highlight by string equality. When `chart_label`
    learned to resolve raw CSV names — which the fix needs — reusing it for C2
    silently dropped two real findings. A card emitting the raw CSV name where the
    chart draws an override highlights nothing, and must still be reported, with
    the correction attached."""
    feed = {"sections": {"services": {"insights": [{
        "id": "sibc-services-share-scan",
        "effect": {"highlight": ["Non-Banking Financial Companies (NBFCs)"],
                   "cut": {"shape": "decomposition", "parent_code": "3",
                           "child_level": 2, "statement": "Statement 1"}}}]}}}
    hits = [f for f in vcc.check_sibc(feed=feed) if f.startswith("[C2")]
    assert hits, "resolvable-but-not-literal highlight was not reported"
    assert "draws it as 'NBFCs'" in hits[0]


def test_chart_label_speaks_both_vocabularies():
    """A renamed series has two names and callers arrive with either: the compute
    layer works in raw CSV names, the chart draws the override."""
    s = C.sibc_sections()
    assert C.chart_label(s, "services", "Non-Banking Financial Companies (NBFCs)") == "NBFCs"
    assert C.chart_label(s, "services", "3.9") == "NBFCs"
    assert C.chart_label(s, "services", "NBFCs") == "NBFCs"
    assert C.chart_label(s, "industryByType", "Power") is None      # on no chart at all


# ── §15.2: every card declares its cut ────────────────────────────────────────

def test_every_sibc_card_declares_a_cut():
    """The contract is total — a card with no cut is not expressible."""
    feed = json.loads((vcc.REPO / "web/public/data/sibc_l1_annotations.json").read_text())
    for sec, bucket in feed["sections"].items():
        for kind in bucket:
            for card in bucket[kind]:
                cut = (card.get("effect") or {}).get("cut")
                assert cut and cut.get("shape") in {"level", "decomposition", "share_of", "pair"}, \
                    f"{sec}.{card['id']} declares no cut"


def test_a_spread_is_a_pair_over_two_entities():
    """§15.3 first claimed SIBC had no pair shape. csv_sector_yoy_spread names two
    entities and quotes the distance between them — the same claim shape as a
    payments ratio, on the entity axis. A hand-typed chart_series had been carrying
    both names, which is how a missing shape stayed invisible."""
    cut = C.sibc_cut({"method": "csv_sector_yoy_spread", "code_a": "2.1", "code_b": "2.3",
                      "statement": "Statement 1"})
    assert cut.shape == "pair" and cut.codes == ("2.1", "2.3")


def test_a_named_set_keeps_every_entity_it_names():
    """'How many of these four grew' is a claim about all four. Deriving only a
    single `code` dropped both multi-entity cards' highlights on the first run."""
    cut = C.sibc_cut({"method": "csv_sector_count_positive_yoy",
                      "child_codes": ["1", "2", "3", "4"], "statement": "Statement 1"})
    assert cut.shape == "level" and len(cut.codes) == 4


# ── §15.6: the charts render the cut ──────────────────────────────────────────

def test_both_pipelines_are_clean_so_the_check_can_be_strict():
    """Step 3 gave the charts the ability to draw every declared cut, which is what
    lets stage 5.7 run strict. If this fails, the gate fails — deliberately."""
    assert vcc.check_sibc() == []
    assert vcc.check_atm_pos() == []


def test_strict_actually_fails():
    """A strict flag that never returns non-zero is decoration."""
    feed = {"sections": {"industryByType": {"insights": [{
        "id": "sibc-basic-metal-sub-share-scan",
        "effect": {"highlight": ["Power"],
                   "cut": {"shape": "decomposition", "parent_code": "2.13",
                           "child_level": 3, "statement": "Statement 2"}}}]}}}
    assert vcc.check_sibc(feed=feed)          # the dead highlight is still reported


def test_a_pair_keeps_its_two_sides():
    """A side can be a BUNDLE — "value transacted at POS" is CC POS value plus DC POS
    value. Flattening the sides into one metric list drew three unlabelled lines for a
    two-sided claim, and lost the labels the card's own prose uses."""
    cut = C.atm_pos_cut({
        "a": {"metrics": ["pos_terminals"], "label": "POS terminals deployed"},
        "b": {"metrics": ["cc_pos_txn_val", "dc_pos_txn_val"], "label": "value transacted at POS"},
    })
    sides = cut.as_json()["sides"]
    assert [s["label"] for s in sides] == ["POS terminals deployed", "value transacted at POS"]
    assert sides[1]["metrics"] == ["cc_pos_txn_val", "dc_pos_txn_val"]


def test_side_metrics_serialise_as_lists():
    """Sides are stored as tuples to keep the Cut hashable. A tuple left in the wire
    form compares unequal to the list that round-trips back through the feed, which C5
    correctly reported as drift on two live cards."""
    cut = C.atm_pos_cut({"metric": "upi_qr", "denominator_metric": "bharat_qr"})
    for side in cut.as_json()["sides"]:
        assert isinstance(side["metrics"], list)


def test_every_sibc_sub_cut_a_card_declares_is_drawable():
    """§15.6a: the section's chart gained a sub-cut for every code RBI breaks down
    further, and the check's model of the chart tracks it. A card declaring a cut the
    chart cannot draw is the original defect."""
    secs = C.sibc_sections()
    assert "2.13" in secs["industryByType"]["sub_cuts"]     # Basic Metal → Iron & Steel / Other
    assert "3.9" in secs["services"]["sub_cuts"]            # NBFCs → HFCs / PFIs
    assert secs["industryByType"]["sub_cuts"]["2.13"]["child_level"] == 3


# ── §15.8: the prose fixes ────────────────────────────────────────────────────

def test_a_growth_scan_names_the_leader_size():
    """The inverse of the movement family's pairing rule. There a share is never
    published without its speed, because a falling share alone reads as decline; here a
    speed is never published without its size, because a rate alone reads as scale.
    Jute Textiles led textiles at 21.4% on 1.7% of the book — ₹5,354 Cr."""
    feed = json.loads((vcc.REPO / "web/public/data/sibc_l1_annotations.json").read_text())
    card = next(c for b in feed["sections"].values() for k in b for c in b[k]
                if c["id"] == "sibc-textiles-sub-yoy-scan")
    assert "1.7% of textiles credit" in card["implication"]
    assert "Other Textiles at 45.5%" in card["implication"]
    # and the size it quotes is declared, so Check 2g scopes to both signals
    assert card["sourceSignals"] == ["sibc-textiles-sub-yoy-scan", "sibc-textiles-sub-share-scan"]


def test_a_cut_with_no_share_scan_loses_the_size_clause_rather_than_inventing_one():
    """Two SIBC cuts have no share scan at all. An honest null beats a near-miss: an
    early version matched on the compute keys alone and paired the PSL scan, whose keys
    are all None, with three payments signals."""
    reg = json.loads((ANALYSIS / "signals/registry.json").read_text())["signals"]
    from pipelines.sibc.generate_analysis_report import _sibling_share_scan
    assert _sibling_share_scan(reg, "sibc-psl-yoy-scan", reg["sibc-psl-yoy-scan"]) is None
    assert _sibling_share_scan(reg, "sibc-textiles-sub-yoy-scan",
                               reg["sibc-textiles-sub-yoy-scan"]) == "sibc-textiles-sub-share-scan"


def test_no_card_tells_the_reader_what_to_do():
    """`core.voice` has linted the distribution surfaces for a year; the dashboard — the
    surface most people read — was linted by nothing, and a card said "Move everything to
    UPI QR". Our own prose hard-fails; the eval's warns, because the fix there is the
    prompt, not a hand-edit of a validated artifact."""
    from guards import validate_card_prose as vcp
    for pipeline in ("sibc", "atm_pos"):
        fails, _ = vcp.check(pipeline)
        assert fails == [], f"{pipeline}: {fails}"


def test_a_relative_clause_is_not_advice():
    """"banks that focus on underserved segments" defines what small finance banks are.
    Measured before narrowing: one suppression across 409 texts, and it was this one."""
    from core import voice
    assert voice.advice("banks that focus on underserved segments") == []
    assert voice.advice("lenders should focus on gold loans")


def test_digit_grouping_commas_are_one_number():
    """"73,426" is one number; the extractor's pattern has no comma in it, so it read 73
    and 426 and rejected both. Narrow by design — a comma is a grouping comma only
    between digits with exactly three following."""
    from core.traceability import extract_numbers, ATM_POS
    assert extract_numbers("now 73,426), while onsite", ATM_POS) == [73426.0]
    assert extract_numbers("In 2026, 45% of the total", ATM_POS) == [2026.0, 45.0]


def test_the_dominance_guard_keeps_a_number_that_is_the_subject():
    """It stripped EVERY number from a headline, not just a trailing stale rate, so
    "India now has 80 UPI QR codes per POS terminal" shipped with no number at all."""
    feed = json.loads((vcc.REPO / "web/public/data/atm_pos_insights.json").read_text())
    cards = feed["insights"] if isinstance(feed, dict) else feed
    title = next(c["title"] for c in cards if c["id"] == "infra-qr-per-pos")
    assert any(ch.isdigit() for ch in title.split(" — ")[0]), title


def test_counts_read_in_lakh_and_crore():
    """The eval layer normalises LLM prose to Indian units and core.voice flags M/K as a
    voice problem, but the deterministic payments cards were still writing "792.6M"."""
    from pipelines.atm_pos.generate_atm_pos_insights import fmt_num
    assert fmt_num(792_600_000) == "79.3 crore"
    assert fmt_num(5_270_000) == "52.7 lakh"
    assert fmt_num(73_426) == "73,426"


# ── residuals: a remainder is not a sector ────────────────────────────────────

def test_catch_alls_are_detected_structurally_not_by_a_list():
    """RBI's naming convention AND never broken down. Measured over the whole CSV:
    every "Other…" entity is a leaf in all 21 periods, so the two conditions together
    identify the set exactly and source #3 inherits the rule."""
    from core import residuals
    found = residuals.catch_alls("sibc")
    for name in ("Others", "Other Textiles", "Other Personal Loans", "Other Services",
                 "Other Industries", "Other Infrastructure", "Other Metal and Metal Product"):
        assert name in found, name
    for name in ("Cotton Textiles", "Wholesale Trade", "Loans against gold jewellery",
                 "Power", "Housing"):
        assert name not in found, name


def test_pure_others_and_a_named_remainder_read_differently():
    """"Others" says nothing about what is inside it; "Other Textiles" says the noun.
    Calling the second unclassified would be LESS accurate than the card already is."""
    from core import residuals
    assert residuals.kind("Others") == "pure"
    assert residuals.kind("Other Textiles") == "named_remainder"
    assert residuals.kind("Cotton Textiles") is None


def test_a_remainder_never_headlines():
    """The defect: "Other Textiles is the biggest slice of textiles credit at 45.5%" —
    the exact sentence `_is_residual`'s docstring forbade, live for months because the
    bucket is called "Other Textiles" and the matcher tested for "Others"."""
    feed = json.loads((vcc.REPO / "web/public/data/sibc_l1_annotations.json").read_text())
    card = next(c for b in feed["sections"].values() for k in b for c in b[k]
                if c["id"] == "sibc-textiles-sub-share-scan")
    assert card["title"] == "Cotton Textiles is the biggest named block of textiles credit at 35.5%"
    assert "45.5% sits in Other Textiles, which RBI does not break down" in card["body"]


def test_a_remainder_is_not_quoted_as_a_peer_in_a_growth_scan():
    """"Edible Oils leads at 50.6%, Others at 18.7%" put a bucket holding 77.4% of
    food-processing credit in the runner-up slot. The remainder still appears — in its
    own clause, labelled — because a large one moving is real news."""
    feed = json.loads((vcc.REPO / "web/public/data/sibc_l1_annotations.json").read_text())
    card = next(c for b in feed["sections"].values() for k in b for c in b[k]
                if c["id"] == "sibc-food-processing-sub-yoy-scan")
    assert "Others at 18.7%;" not in card["body"]
    assert "Others, which RBI does not break down, grew 18.7%" in card["body"]


def test_the_gate_catches_a_headlined_remainder():
    """Driven synthetically — the live defects are fixed, and a check tested only by
    them stops being tested."""
    from guards.validate_card_prose import _residual_problems
    for title in ("Other Textiles is the biggest slice of textiles credit at 45.5%",
                  "Personal loans mix rotating toward Other Personal Loans (+1.2 pp)",
                  "Other Personal Loans took 24.8% of all new personal loans"):
        assert _residual_problems({"title": title}, "sibc"), title
    for title in ("Cotton Textiles is the biggest named block of textiles credit at 35.5%",
                  "Housing took 34.8% of all new personal loans in the past year",
                  "Services credit mix rotating toward Non-Banking Financial Companies"):
        assert not _residual_problems({"title": title}, "sibc"), title


def test_payments_has_the_shape_but_it_does_not_bite():
    """"Other Transactions" is 0.62% of credit-card volume. A binary rule would caveat
    it; the consequence scales with what is unclassified, so nothing fires there."""
    from core import residuals
    assert residuals.catch_alls("atm_pos") == frozenset()
