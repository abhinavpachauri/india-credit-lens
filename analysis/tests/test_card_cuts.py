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
from guards import validate_card_cuts as vcc  # noqa: E402


# ── C1/C3: the cut a signal was computed over ─────────────────────────────────

def test_sibc_cut_reads_a_decomposition_off_the_compute_spec():
    cut = vcc.sibc_cut({"parent_code": "2.13", "child_level": 3, "statement": "Statement 2"})
    assert cut == {"shape": "decomposition", "parent_code": "2.13", "child_level": 3,
                   "statement": "Statement 2", "denominator": None}


def test_sibc_cut_is_a_share_when_a_denominator_is_named():
    cut = vcc.sibc_cut({"parent_code": "2.13", "child_level": 3, "statement": "Statement 2",
                        "denominator_code": "2.13"})
    assert cut["shape"] == "share_of" and cut["denominator"] == "2.13"


def test_sibc_scalar_signal_has_no_cut():
    """A single entity's own series is the `level` shape — it must not be
    reported as mis-charted, which is the check's main false-rejection risk."""
    assert vcc.sibc_cut({"method": "csv_sector_yoy", "code": "4.5"}) is None


def test_atm_pos_share_pulls_in_its_whole_denominator():
    cut = vcc.atm_pos_cut({"metric": "cc_ecom_txn_vol",
                           "denominator_metrics": ["cc_pos_txn_vol", "cc_ecom_txn_vol"]})
    assert cut["shape"] == "share_of"
    assert cut["metrics"] == ["cc_ecom_txn_vol", "cc_pos_txn_vol"]


def test_atm_pos_pair_pulls_in_both_sides():
    cut = vcc.atm_pos_cut({"a": {"metrics": ["pos_terminals"]},
                           "b": {"metrics": ["cc_pos_txn_val", "dc_pos_txn_val"]}})
    assert cut["shape"] == "pair"
    assert "pos_terminals" in cut["metrics"] and "dc_pos_txn_val" in cut["metrics"]


def test_atm_pos_ratio_denominator_is_part_of_the_claim():
    """'UPI QR is 150.5x Bharat QR' is a claim about two metrics. Drawing one of
    them is the payments form of the sub-cut defect."""
    cut = vcc.atm_pos_cut({"metric": "upi_qr", "denominator_metric": "bharat_qr"})
    assert cut["metrics"] == ["bharat_qr", "upi_qr"]


# ── the live defects this was built for ───────────────────────────────────────

def test_catches_the_defect_that_started_this():
    """Iron & Steel (children of 2.13) charted as Basic Metal (a child of 2)."""
    found = vcc.check_sibc(strict=False)
    assert any("sibc-basic-metal-sub-share-scan" in f and f.startswith("[C1") for f in found)


def test_catches_a_highlight_that_renders_nothing():
    """'Power' is code 2.18.1 and is on no chart in the dashboard."""
    found = vcc.check_sibc(strict=False)
    assert any("sibc-infra-sub-allocation" in f and "'Power'" in f for f in found)


def test_catches_a_focus_card_that_is_not_a_section():
    """gap-atm-offsite-decline points at 'atm_offsite'; AtmReadMode falls back to
    the first section of the group, so a card about offsite ATMs draws POS
    terminals. The silent fallback is why this needed a check to find."""
    found = vcc.check_atm_pos(strict=False)
    assert any("gap-atm-offsite-decline" in f for f in found)


def test_catches_a_pair_charted_one_sided():
    found = vcc.check_atm_pos(strict=False)
    assert any("pos-fleet-vs-spend-gap" in f and "pair" in f for f in found)


def test_catches_an_undeclared_cut():
    """A card that declares nothing must not read as a card that declares the
    right thing — the failure shape this project keeps meeting."""
    found = vcc.check_atm_pos(strict=False)
    assert any(f.startswith("[C4") for f in found)


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
    import csv
    rows = list(csv.DictReader(open(vcc.consolidated_csv("sibc"))))
    cuts = json.loads((ANALYSIS / "pipelines/sibc/section_cuts.json").read_text())
    secs = vcc.sibc_section_series(cuts, rows)
    assert secs["industryBySize"]["labels"]["2.3"] == "Large"
    assert secs["industryByType"]["labels"]["2.3"] == "Beverage and Tobacco"


def test_declared_section_cut_matches_what_the_chart_is_drawn_from():
    """section_cuts.json is a second description of what buildSections() renders.
    It may not drift: every declared payments metric must exist in the artifact
    the chart actually reads."""
    found = vcc.check_atm_pos(strict=False)
    assert not any("is not in atm_pos_chart_series.json" in f for f in found)
