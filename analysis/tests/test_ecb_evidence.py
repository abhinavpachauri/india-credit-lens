#!/usr/bin/env python3
"""
Controls for analysis/core/ecb_evidence.py (sources/README "ECB borrower lists").

  1 every sector label in the saved months resolves; a label nothing explains stops the read
  2 punctuation and RBI's truncation resolve to the same division; a short prefix does not
  3 a falling unexplained move gets its sector's deals, rupee-loan refinancing first
  4 a rise, an explained move, or an unmapped line gets nothing
  5 a missing month is named, never read as "no deals"
  6 the saved months reproduce the totals read when they were probed (2026-11-13)

Run: python3 -m pytest analysis/tests/test_ecb_evidence.py -q
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import ecb_evidence as ee  # noqa: E402


def test_1_unknown_sector_stops_the_read():
    with pytest.raises(ee.UnknownSector):
        ee.division_of("Manufacture of happiness")


def test_2_variants_and_truncation_resolve_but_a_short_prefix_does_not():
    assert ee.division_of(" Electricity gas steam and air conditioning supply") == "35"
    assert ee.division_of("Electricity, gas, steam and air conditioning supply") == "35"
    assert ee.division_of("Architecture and engineering activities; technical testing and analysi") == "71"
    assert ee.division_of("Manufacturing Textiles") == "13"
    with pytest.raises(ee.UnknownSector):
        ee.division_of("Manufacture of")                       # a prefix of many divisions


MOVES = [
    {"entity": "Shipping", "urn": "u:ship", "direction": "down", "gap_change_pp": -20.1, "filed_under": "unexplained"},
    {"entity": "Ports", "urn": "u:ports", "direction": "up", "gap_change_pp": 17.0, "filed_under": "unexplained"},
    {"entity": "Tourism", "urn": "u:ship", "direction": "down", "gap_change_pp": -4.4, "filed_under": "structural"},
    {"entity": "Housing", "urn": "u:housing", "direction": "down", "gap_change_pp": -3.0, "filed_under": "unexplained"},
]
PARTS = {"u:ship": ["50"], "u:ports": ["52"]}


def deal(no, nic, usd, purpose, borrower="X Ltd"):
    return {"no": no, "route": "General Permission", "kind": "ECB", "borrower": borrower, "sector": "s",
            "nic": nic, "usd": usd, "purpose": purpose, "maturity": "5 Years", "lender": "L"}


BY_MONTH = {"2026-09": [deal(1, "50", 2e6, "Working Capital"),
                        deal(2, "50", 1.004e8, "Refinancing of Rupee Loans", "The Shipping Corporation of India Limited"),
                        deal(3, "52", 5e8, "Refinancing of Rupee Loans")],
            "2026-08": [deal(4, "50", 9e7, "Import of Capital Goods")]}


def test_3_a_fall_gets_its_sector_deals_refinancing_first():
    ev = ee.evidence_for(MOVES, "2026-09", PARTS, BY_MONTH)
    assert [e["entity"] for e in ev] == ["Shipping"]
    s = ev[0]
    assert s["deals"][0]["borrower"].startswith("The Shipping Corporation")
    assert len(s["refinancing"]) == 1 and s["n_deals"] == 3          # the ports deal is not shipping's


def test_4_rises_explained_moves_and_unmapped_lines_get_nothing():
    names = [e["entity"] for e in ee.evidence_for(MOVES, "2026-09", PARTS, BY_MONTH)]
    assert "Ports" not in names and "Tourism" not in names and "Housing" not in names


def test_5_a_missing_month_is_named():
    ev = ee.evidence_for(MOVES, "2026-10", PARTS, BY_MONTH)
    assert ev[0]["months_missing"] == ["2026-10"]
    assert ev[0]["months_read"] == ["2026-09"]


def test_6_saved_months_reproduce_the_probe_totals():
    rows = ee.saved_rows()
    if not rows:
        pytest.skip("no ECB months saved")
    probe = {"2025-10": 2.21, "2026-01": 5.33, "2026-06": 6.08, "2026-09": 7.05}   # US$ bn, 2026-11-13
    for m, bn in probe.items():
        if m in rows:
            assert round(sum(r["usd"] for r in rows[m]) / 1e9, 2) == bn
