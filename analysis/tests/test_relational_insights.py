#!/usr/bin/env python3
"""
Tests for core/relational_insights.rotation_insight — the deterministic
rotation prose builder (spec: analysis/signals/README.md).

Run: python3 -m pytest analysis/tests/test_relational_insights.py -q
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.relational_insights import (  # noqa: E402
    rotation_insight, divergence_insight, pair_divergence_insight, _majority_role)

ROLES = {
    "Power":       "energy_logistics_capex",
    "Ports":       "energy_logistics_capex",
    "Engineering": "capital_goods",
    "Textiles":    "consumer_traditional",
    "Leather":     "consumer_traditional",
}


def _dist(*pairs):
    return [(e, v, "active") for e, v in pairs]


# ── majority role ─────────────────────────────────────────────────────────────

def test_majority_of_tagged_material_movers():
    assert _majority_role([("Power", 1.0), ("Ports", 0.8), ("Engineering", 0.3)],
                          ROLES) == "energy_logistics_capex"


def test_immaterial_mover_excluded():
    # Engineering's +0.04 is below the 0.15 materiality bar — Power decides alone.
    assert _majority_role([("Power", 1.0), ("Engineering", 0.04)],
                          ROLES) == "energy_logistics_capex"


def test_mixed_roles_no_majority():
    assert _majority_role([("Power", 1.0), ("Engineering", 0.9)], ROLES) is None


def test_untagged_entities_abstain():
    assert _majority_role([("Power", 1.0), ("Mystery", 0.9)],
                          ROLES) == "energy_logistics_capex"


def test_no_tagged_movers_none():
    assert _majority_role([("Mystery", 1.0)], ROLES) is None


# ── rotation_insight ──────────────────────────────────────────────────────────

def test_theme_when_gainers_share_a_role():
    ins = rotation_insight(
        _dist(("Power", 1.2), ("Ports", 0.8), ("Textiles", -1.0), ("Leather", -1.0)),
        mass=2.0, roles=ROLES, subject="industry credit")
    assert ins["insight_kind"] == "rotation"
    assert "energy & logistics capex" in ins["body"]
    assert "tilting toward energy & logistics capex" in ins["body"]
    assert "traditional consumer sectors" in ins["body"]
    # Spaced unit + signed values — the traceability extractors backtrack glued
    # "1.20pp" to a bare "1", so the format is part of the contract.
    assert "+1.20 pp" in ins["body"] and "-1.00 pp" in ins["body"]
    assert "2.00 pp of the mix changed hands" in ins["body"]
    assert "composition read" in ins["implication"]


def test_honest_fallback_on_mixed_roles():
    ins = rotation_insight(
        _dist(("Power", 1.0), ("Engineering", 0.9), ("Mystery", -1.9)),
        mass=1.9, roles=ROLES, subject="industry credit")
    assert "No single economic theme" in ins["body"]


def test_no_theme_sentence_for_untagged_universe():
    # Bank categories carry no economic_role — the theme line must be absent,
    # not an assertion that "no economic theme" exists.
    ins = rotation_insight(
        _dist(("Private Sector Banks", 1.0), ("Public Sector Banks", -1.0)),
        mass=1.0, roles=ROLES, subject="credit cards")
    assert "economic theme" not in ins["body"]
    assert "changed hands." in ins["body"]


def test_steady_mix_is_the_finding():
    ins = rotation_insight(
        _dist(("Power", 0.1), ("Textiles", -0.1)),
        mass=0.1, roles=ROLES, subject="industry credit")
    assert "steady" in ins["title"]
    assert "essentially unchanged" in ins["body"]


def test_empty_distribution_suppressed():
    assert rotation_insight([], mass=None, roles=ROLES, subject="x") is None


# ── divergence_insight ────────────────────────────────────────────────────────

def test_divergence_single_flag():
    ins = divergence_insight([("Consumer Durables", -18.01, "active")],
                             subject="personal loans")
    assert ins["insight_kind"] == "divergence_hierarchy"
    assert "Consumer Durables" in ins["title"]
    assert "-18.01 pp" in ins["body"]          # signed, spaced — the row value
    assert "only" in ins["body"]               # single-flag phrasing
    assert "contracting while the rest grows" in ins["body"]


def test_divergence_multi_flag_both_directions():
    dist = [("SBM BANK INDIA LTD", 24.69, "active"),
            ("CITI BANK", 20.65, "active"),
            ("TAMILNAD MERCANTILE BANK LTD", -45.82, "active")]
    ins = divergence_insight(dist, subject="credit cards", member_noun="bank",
                             parent_is_per_entity=True)
    assert "TAMILNAD MERCANTILE BANK" in ins["title"]   # widest |gap| leads
    assert "-45.82 pp" in ins["title"]
    assert "+24.69 pp" in ins["body"]
    assert "3 banks are flagged" in ins["body"]
    assert "its category" in ins["body"]


def test_divergence_no_flags_suppressed():
    assert divergence_insight([], subject="services credit") is None


def test_no_lead_lag_language():
    # Composition reads only (COMPOSITION_SPEC §4) — transmission verbs are
    # channel territory and must never appear in rotation prose.
    ins = rotation_insight(
        _dist(("Power", 1.2), ("Ports", 0.8), ("Textiles", -2.0)),
        mass=2.0, roles=ROLES, subject="industry credit")
    text = " ".join([ins["title"], ins["body"], ins["implication"]] + ins["chain"]).lower()
    for verb in ("leads", "lags", "will grow", "predicts", "drives", "causes"):
        assert verb not in text


# ── pair divergence (metric axis) ─────────────────────────────────────────────

A, B = "cards in force", "card spend"


def _pair(gap, status, ya, yb, flagged=None):
    return pair_divergence_insight(gap, status, A, B, ya, yb, flagged)


def test_pair_stable_gap_is_suppressed():
    # Two sides still moving together is the null result — no card.
    assert _pair(1.2, "stable", 8.0, 6.8) is None
    assert _pair(None, "strengthening", None, None) is None


def test_pair_both_growing_names_the_faster_side():
    ins = _pair(5.0, "strengthening", 9.0, 4.0)
    assert "Both grew" in ins["body"]
    assert ins["title"].startswith("Cards in force grew faster than card spend")
    assert ins["insight_kind"] == "divergence_pair"


def test_pair_both_shrinking_never_called_growth():
    # The higher rate is still negative: "ahead" here means shrinking slower.
    ins = _pair(3.35, "strengthening", -2.71, -6.06)
    assert "Both shrank" in ins["body"]
    assert "grew" not in ins["title"]
    assert ins["title"].startswith("Card spend shrank faster than cards in force")


def test_pair_split_directions():
    ins = _pair(7.08, "strengthening", 2.75, -4.33)
    assert ins["title"].startswith("Cards in force grew while card spend fell")


def test_pair_negative_gap_flips_which_side_leads():
    # Gap sign is a minus b; the prose must name the actually-faster side.
    ins = _pair(-4.66, "weakening", -0.48, 4.18)
    assert ins["title"].startswith("Card spend grew while cards in force fell")
    assert "-4.66 pp" in ins["title"]


def test_pair_gap_is_signed_and_spaced_for_the_extractors():
    ins = _pair(7.08, "strengthening", 2.75, -4.33)
    assert "+7.08 pp" in ins["body"]
    assert all("7.08 pp" in step or "7.08" not in step for step in ins["chain"])


def test_pair_only_the_gap_is_stated_as_a_number():
    # The side rates inform the wording but must not appear as figures — the
    # card cites only its own signal's gap row.
    ins = _pair(7.08, "strengthening", 2.75, -4.33)
    text = " ".join([ins["title"], ins["body"], *ins["chain"], ins["implication"]])
    assert "2.75" not in text and "4.33" not in text


def test_pair_bank_rows_named_when_present():
    ins = _pair(7.08, "strengthening", 2.75, -4.33,
                [("SBM BANK INDIA LTD", 30.86, "active"), ("CITI BANK", 20.05, "active")])
    assert "2 banks are flagged" in ins["body"]
    assert "SBM BANK INDIA LTD +30.86 pp" in ins["body"]


def test_pair_unknown_side_rates_falls_back_without_direction_claim():
    ins = _pair(7.08, "strengthening", None, None)
    assert "outpaced" in ins["title"]
    assert "grew" not in ins["title"] and "shrank" not in ins["title"]
