"""Restated basis: a comparison between a reprinted month and one on the old basis is absent.

Spec: signals/README.md, "Series breaks". Transport Operators read 2.93 (Aug 2026, old basis) and
2.50 lakh crore (Sep 2026, new basis): the fall is the relabelling. Sep against Sep still holds.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import absence, coverage as cv, force_check as fc, series_breaks as SB  # noqa: E402
from signals.compute import csv_sector as S                                       # noqa: E402

ST = "Statement 1"
PRINTED = {"2024-09-30", "2025-03-31", "2025-09-30", "2026-03-31", "2026-09-30"}


def test_the_new_basis_is_the_months_the_release_printed():
    assert PRINTED <= SB.restated_months("sibc", ST, "3.1")
    assert "2026-08-31" not in SB.restated_months("sibc", ST, "3.1")


@pytest.mark.parametrize("a, b, crosses", [
    ("2026-08-31", "2026-09-30", True),      # old basis vs new
    ("2025-09-30", "2026-09-30", False),     # both reprinted: RBI's own growth
    ("2025-08-31", "2026-08-31", False),     # both old
    ("2026-03-31", "2026-09-30", False),     # RBI's own financial-year variation
])
def test_a_comparison_crosses_only_between_bases(a, b, crosses):
    assert bool(SB.spans("sibc", ST, "3.1", a, b)) is crosses
    assert bool(SB.spans("sibc", ST, "4.7", a, b)) is crosses


def test_a_line_not_declared_is_read_as_published():
    assert SB.spans("sibc", ST, "3.8", "2026-08-31", "2026-09-30") is None
    assert SB.restated_months("sibc", ST, "3.8") == frozenset()


def test_a_pipeline_without_a_breaks_file_has_none():
    assert SB.restated_months("nbfc", ST, "3.1") == frozenset()


def test_the_reason_is_a_declared_absence_code():
    assert "restated_basis" in absence.PER_PERIOD


def _yoy(code, period):
    return S.compute("t", {"method": "csv_sector_yoy", "code": code, "statement": ST},
                     period, S._load_df("sibc"))


def test_growth_on_one_basis_is_rbis_printed_figure():
    [row] = _yoy("3.1", "2026-09-30")
    assert row["value"] == pytest.approx(24.58, abs=0.05)      # 250471 / 201046
    assert row.get("reason") is None


def test_the_change_in_growth_across_bases_is_absent():
    rows = S.compute("t", {"method": "csv_sector_acceleration", "parent_code": "3", "statement": ST,
                           "child_level": 2, "entity_type": "sector"},
                     "2026-09-30", S._load_df("sibc"))
    transport = [r for r in rows if r["entity_id"] == "Transport Operators"]
    other = [r for r in rows if r["entity_id"] == "Trade"]
    assert transport and (transport[0]["value"], transport[0]["reason"]) == (None, "restated_basis")
    assert other and other[0]["value"] is not None


def test_a_monthly_change_across_bases_is_not_counted():
    gaps = [("2026-07-31", 1.0), ("2026-08-31", 2.0), ("2026-09-30", 18.0)]
    assert fc.monthly_changes(gaps, lambda p: p) == [("2026-08-31", 1.0), ("2026-09-30", 16.0)]
    assert fc.monthly_changes(gaps, lambda p: p, frozenset({"2026-09-30"})) == [("2026-08-31", 1.0)]


def test_a_move_across_bases_says_why_it_has_no_reading():
    months = [f"2025-{m:02d}-28" for m in range(1, 13)] + ["2026-01-28"]
    growth = {p: float(i % 2) for i, p in enumerate(months)}
    out = cv.move_of(growth, {}, "none", months, months[-1], lambda p: p, frozenset({months[-1]}))
    assert out["status"] == "no_reading" and out["reason"].startswith("restated_basis")


@pytest.mark.parametrize("reprints, typical, flagged", [
    ([-26.4, -26.1, -24.8, -18.6], 1.53, True),     # Transport Operators, 30 Oct 2026
    ([10.1, 9.4, 8.8, 4.5], 1.30, True),            # Vehicle Loans
    ([3.9, 0.2, 9.8, 0.8], 1.40, False),            # Roads: revisions, one month small
    ([-1.2, 5.0], 1.0, False),                      # moved both ways
    ([-20.0], 1.0, False),                          # one month is a revision
    ([-20.0, -20.0], None, False),                  # no history to judge by
    ([-3.0, -3.0], 1.0, False),                     # exactly at the bar, not over it
])
def test_what_counts_as_a_restatement(reprints, typical, flagged):
    assert SB.is_restatement(reprints, typical) is flagged
