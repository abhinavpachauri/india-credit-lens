#!/usr/bin/env python3
"""
Golden tests for the traceability number layer (validate_sibc_traceability):
extract_numbers / matches / ratio_matches. These are the deterministic core of
Check 2g/4f — if extract_numbers leaks a structural token as a "number", or matches
is too loose/tight, the traceability gate either nags falsely or lets a fabricated
number through.

Pins the ACTUAL contract (probed against the code), including two real quirks worth
locking so they can't silently change:
  - FY ranges like "FY22-24" are fully stripped (no "-24" leak) — the bug this guards.
  - a decimal glued to a unit letter backtracks to its integer part:
    "₹212.1L Cr" → 212.0, "-12.3pp" → -12.0 (but "-12.3 pp" → -12.3).

Run: python3 -m pytest analysis/tests/test_traceability.py -q
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipelines.sibc import validate_sibc_traceability as v  # noqa: E402

en = v.extract_numbers


# ── extract_numbers: structural tokens stripped ───────────────────────────────

@pytest.mark.parametrize("text", [
    "FY22-24",          # the headline case: must NOT leak -24 or 22/24
    "FY25", "FY 2026", "FY22–24", "FY22/24",
    "as of 2026-04-30",  # ISO date
    "in 2025",           # standalone calendar year
    "Q1", "in Q3 results",
])
def test_structural_tokens_yield_no_numbers(text):
    assert en(text) == []


def test_fy_range_with_real_number():
    assert en("FY22-24 saw 15.5% growth") == [15.5]


# ── extract_numbers: real values ──────────────────────────────────────────────

def test_plain_decimal_and_percent():
    assert en("grew 20.0% YoY") == [20.0]
    assert en("share 0.5%") == [0.5]
    assert en("99 banks") == [99.0]


def test_below_min_check_ignored():
    # MIN_CHECK = 0.5 — trivial small values are dropped
    assert en("a 0.3% blip") == []


def test_glued_unit_decimal_backtracks_to_integer():
    # known quirk: a decimal immediately followed by a letter loses its fraction
    assert en("₹212.1L Cr") == [212.0]
    assert en("fell -12.3pp") == [-12.0]
    # but a space preserves the full decimal
    assert en("fell -12.3 pp") == [-12.3]


# ── matches: tolerance behaviour ──────────────────────────────────────────────

def test_matches_exact_and_within_rel_tol():
    assert v.matches(20.0, [20.0])
    assert v.matches(20.04, [20.0])     # 0.2% < REL_TOL (2%)
    assert v.matches(20.3, [20.0])      # 1.5% < REL_TOL


def test_matches_outside_tol():
    assert not v.matches(25.0, [27.27])   # ~8% off


def test_matches_abs_tol_for_small_values():
    assert v.matches(0.6, [0.5])          # |0.1| <= ABS_TOL (0.25)
    assert not v.matches(1.0, [0.5])      # |0.5| > ABS_TOL and >2% rel


def test_matches_zero_candidate():
    assert v.matches(0.1, [0.0])          # near-zero within ABS_TOL
    assert not v.matches(0.4, [0.0])      # 0.4 > ABS_TOL


# ── ratio_matches: percentage-of-total grounding ──────────────────────────────

def test_ratio_matches_percent_of_total():
    # 100 * 211 / 212 = 99.528 — a share derivable from two grounded levels
    assert v.ratio_matches(99.5, [212.0, 211.0])


def test_ratio_matches_rejects_ungrounded():
    assert not v.ratio_matches(50.0, [212.0, 211.0])
