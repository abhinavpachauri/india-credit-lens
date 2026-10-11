"""Series breaks: a comparison across the 2023 HDFC merger is absent with its reason, never growth.

Spec: signals/README.md, "Series breaks". The live SIBC CSV is read only at periods fixed in the
past (Jan–Aug 2024), which RBI does not revise; nothing here depends on the latest month.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import absence, series_breaks as SB          # noqa: E402
from signals.compute import csv_sector as S             # noqa: E402

ST = "Statement 1"


# ── the one question ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("a, b, spans", [
    ("2023-06-30", "2024-06-30", True),     # before vs after the merger month
    ("2023-07-31", "2024-07-31", False),    # both ends include the merger
    ("2022-07-31", "2023-07-31", True),     # the effective month itself is "after"
    ("2024-01-31", "2025-01-31", False),
])
def test_a_comparison_spans_the_break_only_when_it_crosses_the_effective_month(a, b, spans):
    assert bool(SB.spans("sibc", ST, "4.2", a, b)) is spans


def test_a_line_rbi_did_not_mark_is_read_as_published():
    assert SB.spans("sibc", ST, "1", "2023-06-30", "2024-06-30") is None     # agriculture


def test_a_pipeline_without_a_breaks_file_has_none():
    assert SB.spans("nbfc", ST, "4.2", "2023-06-30", "2024-06-30") is None


def test_the_reason_is_a_declared_absence_code():
    assert "merger_break" in absence.PER_PERIOD


# ── what it does to the readings ──────────────────────────────────────────────

def _yoy(code, period):
    return S.compute("t", {"method": "csv_sector_yoy", "code": code, "statement": ST},
                     period, S._load_df("sibc"))


def test_growth_across_the_merger_on_a_marked_line_is_absent_with_the_reason():
    [row] = _yoy("4.2", "2024-03-31")                       # housing, Mar 2024 vs Mar 2023
    assert (row["value"], row["status"], row["reason"]) == (None, "absent", "merger_break")


def test_growth_once_both_ends_include_the_merger_is_ordinary():
    [row] = _yoy("4.2", "2024-08-31")
    assert row["value"] is not None and row.get("reason") is None


def test_a_scan_marks_only_the_affected_rows():
    rows = S.compute("t", {"method": "csv_sector_scan_yoy", "parent_code": "4", "statement": ST,
                           "child_level": 2}, "2024-03-31", S._load_df("sibc"))
    by = {r["entity_id"]: r for r in rows}
    assert by["Housing (Including Priority Sector Housing)"]["reason"] == "merger_break"
    assert by["Loans against gold jewellery"]["value"] is not None


def test_movement_over_a_cut_with_a_marked_part_is_absent_as_a_whole():
    rows = S.compute("t", {"method": "csv_sector_momentum", "parent_code": "III", "statement": ST,
                           "child_level": 1, "window": 12}, "2024-03-31", S._load_df("sibc"))
    assert [(r["status"], r["reason"]) for r in rows] == [("absent", "merger_break")]


def test_no_year_ago_reading_is_the_deeper_absence_than_the_merger():
    """Jul 2023 has no Jul 2022 to compare with: that is a history gap, not the merger."""
    from signals.compute import real_economy as R
    cred = R.credit(S._load_df("sibc"))
    u = R.urn("sibc", ST, "4.2")
    with pytest.raises(R.Absent) as e:
        cred.yoy(u, "2023-07-31")
    assert e.value.reason == "credit_history_gap"
