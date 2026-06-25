#!/usr/bin/env python3
"""
Golden tests for the ATM/POS traceability number layer (validate_atm_pos_insights):
extract_numbers / _matches / _ratio_matches. This is the deterministic core of the
payments Stage-4c gate — the analog of test_traceability.py for SIBC.

Written BEFORE the core/traceability.py de-duplication (§4 P1 batch 5) so the merge has
a regression net: these pin the ACTUAL current behavior, including the places where the
payments core genuinely diverges from SIBC's (the reason the two can't be naively unified):
  - suffix scaling: "1B" → 1e9, "5M" → 5e6, "3.2K" → 3200, while "137x"/"20%" only strip.
  - NO structural stripping: unlike SIBC, "FY26" leaks 6.0 and an ISO date leaks its
    components (incl. negative day from the "-"). Payments prose is templated so this is
    tolerated; locking it means the merge can't silently change it.
  - tighter tolerances: REL_TOL 0.5% (vs SIBC 2%), ABS_TOL 0.6 (vs 0.25).
  - ratios are plain A/B (round or rel), NO percent-of-total (no 100*A/B like SIBC).

Run: python3 -m pytest analysis/tests/test_traceability_atm_pos.py -q
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipelines.atm_pos import validate_atm_pos_insights as a  # noqa: E402

en = a.extract_numbers


# ── extract_numbers: suffix scaling ───────────────────────────────────────────

def test_magnitude_suffixes_scale():
    assert en("1B transactions") == [1_000_000_000.0]
    assert en("5M cards") == [5_000_000.0]
    assert en("3.2K terminals") == [3200.0]
    assert en("108M net codes") == [108_000_000.0]


def test_x_and_percent_strip_only():
    assert en("137x per Bharat QR") == [137.0]
    assert en("1.5x growth") == [1.5]
    assert en("8.1% YoY") == [8.1]
    assert en("share 0.5%") == [0.5]


def test_multiple_values():
    assert en("grew 20.8% vs 26.8%") == [20.8, 26.8]
    assert en("2000 to 5000") == [2000.0, 5000.0]


# ── extract_numbers: NO structural stripping (the divergence from SIBC) ────────

def test_no_structural_stripping_quirks():
    # locked intentionally: payments core does NOT strip FY/ISO/year tokens
    assert en("FY26") == [6.0]
    assert en("as of 2026-04-30") == [2026.0, -4.0, -30.0]
    assert en("in 2025") == [2025.0]


def test_alpha_glued_tokens_skipped():
    assert en("Q4") == []
    assert en("Tier2") == []
    assert en("up 0.2pp") == []          # decimal glued to letters → dropped entirely


def test_glued_unit_decimal_backtracks_to_integer():
    assert en("-12.3pp") == [-12.0]      # same backtrack quirk as SIBC
    assert en("-12.3 pp") == [-12.3]     # space preserves the decimal
    assert en("₹212.1L") == [212.0]


def test_below_min_value_ignored():
    # MIN_VALUE_TO_CHECK = 0.5
    assert en("a 0.4 value") == []
    assert en("0.3% blip") == []
    assert en("reset to 0") == []        # 0 < 0.5


def test_plain_count():
    assert en("99 banks") == [99.0]
    assert en("14-month run") == [14.0]
    assert en("16-period range") == [16.0]


# ── _matches: tolerance behaviour (REL_TOL 0.5%, ABS_TOL 0.6) ──────────────────

def test_matches_rel_then_abs():
    assert a._matches(20.04, [20.0])     # 0.2% < REL_TOL (0.5%)
    assert a._matches(20.3, [20.0])      # 1.5% > rel, but |0.3| <= ABS_TOL (0.6)
    assert not a._matches(21.0, [20.0])  # 5% rel and |1.0| > 0.6


def test_matches_zero_candidate():
    assert a._matches(0.5, [0.0])        # |0.5| < ABS_TOL 0.6
    assert not a._matches(0.6, [0.0])    # |0.6| not < 0.6


# ── _ratio_matches: plain A/B, no percent-of-total ────────────────────────────

def test_ratio_plain_quotient():
    assert a._ratio_matches(137.0, [137_000.0, 1000.0])   # 137000/1000 = 137


def test_ratio_rejects_percent_of_total():
    # SIBC would ground 99.5 = 100*211/212; payments deliberately does NOT
    assert not a._ratio_matches(99.5, [212.0, 211.0])


def test_ratio_needs_two_values():
    assert not a._ratio_matches(5.0, [10.0])
