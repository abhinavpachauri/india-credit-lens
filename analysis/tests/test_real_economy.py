"""1f — a credit part measured against the real economy (signals/compute/real_economy.py).

Pins the formula, the closed list of per-period reasons, and the failures that must stay loud:
an overdue reference value, a combined series missing one component, a pipeline reading a
reference it does not declare.
"""
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

from core import absence                                         # noqa: E402
from signals.compute import csv_sector as C                      # noqa: E402
from signals.compute import real_economy as R                    # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_caches():
    """Some tests edit the cached reference to stage a gap; none may leak into the next."""
    R.invalidate_cache()
    yield
    R.invalidate_cache()


def test_real_growth_formula_is_pinned():
    """signals/README §1f: Industry Q1 FY27, g = 19.25, π = 3.85 → 14.83."""
    assert round(R.real(19.25, 3.85), 2) == 14.83


def test_the_live_industry_row_agrees_with_the_pinned_example():
    """The same number end to end, from the CSVs: Industry real growth at Jun 2026."""
    df = C._load_df("sibc")
    rows = R.csv_sector_real_growth({"cut": "sibc-main", "reference": "mospi"}, "2026-06-30", df)
    industry = [r for r in rows if r["entity_id"].startswith("Industry")]
    assert len(industry) == 1 and abs(industry[0]["value"] - 14.83) < 0.02


def _ref(monkeypatch, run_date):
    monkeypatch.setattr(R, "today", lambda: run_date)
    R.invalidate_cache()
    return R.reference("mospi")


def test_a_missing_reference_value_is_not_released_while_due_date_is_ahead(monkeypatch):
    ref = _ref(monkeypatch, date(2026, 9, 1))          # IIP Sep 2026 due 28 Oct + grace
    assert ref.value("iip/nic:10", "index", "2026-09-30") == "not_released"


def test_a_missing_reference_value_past_its_due_date_raises(monkeypatch):
    ref = _ref(monkeypatch, date(2027, 1, 1))
    with pytest.raises(R.ReferenceMissing):
        ref.value("iip/nic:10", "index", "2026-09-30")


def test_a_period_before_the_series_starts_is_a_history_gap(monkeypatch):
    ref = _ref(monkeypatch, date(2026, 10, 3))
    assert ref.value("iip/nic:10", "index", "2022-03-31") == "reference_history_gap"
    assert ref.value("cpi/cpi:all", "index", "2024-12-31") == "reference_history_gap"


def test_every_per_period_reason_used_is_in_the_closed_list():
    assert {"not_released", "credit_history_gap", "reference_history_gap"} <= set(absence.PER_PERIOD)
    assert not set(absence.STATIC) & set(absence.PER_PERIOD)


def test_a_combined_series_needs_every_component(monkeypatch):
    """One component missing → the whole is absent; the weights are never renormalised."""
    ref = _ref(monkeypatch, date(2026, 9, 1))
    spec = {"series": ["iip/nic:24", "iip/nic:25"], "combine": "weighted",
            "weights": {"iip/nic:24": 9.198, "iip/nic:25": 2.481}}
    assert R.combined(ref, spec, "index", "2026-08-31") > 0
    ref.values.pop(("iip", "nic:25", "index", "2026-08-31"))
    with pytest.raises(R.Absent) as e:
        R.combined(ref, spec, "index", "2026-08-31")
    assert e.value.reason == "not_released"


def test_a_quarterly_cut_emits_nothing_between_quarter_ends():
    df = C._load_df("sibc")
    assert R.csv_sector_output_growth({"cut": "sibc-main", "reference": "mospi"}, "2026-08-31", df) == []
    assert R.csv_sector_output_growth({"cut": "sibc-main", "reference": "mospi"}, "2026-06-30", df)


def test_every_row_has_a_value_or_a_reason_never_both():
    df = C._load_df("sibc")
    for method in R.METHODS.values():
        for r in method({"cut": "sibc-industry-type", "reference": "mospi"}, "2026-08-31", df):
            assert (r["value"] is None) != (r["reason"] is None), r
            assert (r["status"] == "absent") == (r["value"] is None), r


def test_reading_an_undeclared_reference_raises_through_compute(monkeypatch):
    """Not swallowed into _unknown(): the engine's catch-all re-raises ReferenceMissing."""
    df = C._load_df("sibc")
    params = {"method": "csv_sector_real_growth", "cut": "sibc-main", "reference": "not_declared"}
    with pytest.raises(R.ReferenceMissing):
        C.compute("x", params, "2026-06-30", df)


def test_the_parent_row_is_emitted_once_on_its_own_cut():
    """Industry is the industry-by-type total and a main-table part: computed on the main table only."""
    df = C._load_df("sibc")
    p = {"cut": "sibc-industry-type", "reference": "mospi"}
    assert all(r["entity_type"] != "aggregate" for r in R.csv_sector_real_growth(p, "2026-06-30", df))
    main = R.csv_sector_real_growth({"cut": "sibc-main", "reference": "mospi"}, "2026-06-30", df)
    assert sum(r["entity_type"] == "aggregate" for r in main) == 1
