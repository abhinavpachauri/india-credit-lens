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
    rotation_insight, divergence_insight, _majority_role)

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
