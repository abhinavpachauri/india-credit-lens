#!/usr/bin/env python3
"""
Golden tests for analysis/signals/compute/sibc.py (Layer-1 deterministic compute).

The platform's whole value is "deterministic + traceable", yet the compute methods
were verified only by consistency-gates (which catch drift, not wrong-from-the-start
logic). These pin the math against a tiny fixture with hand-computed expected values.

Fixture (statement "Statement 1", three FY-end dates so YoY resolves):
    date         S    C(parent S)   T     D
    2024-03-31   100      -         -     -
    2025-03-31   110      30        100   100
    2026-03-31   132      33        105    90

Hand-computed for period 2026-03-31:
    S YoY   = (132-110)/110 = 20.0%   (prev-yr YoY = (110-100)/100 = 10.0%)
    T YoY   = (105-100)/100 =  5.0%
    D YoY   = (90-100)/100  = -10.0%
    C share = 33/132 = 25.0%          (prior 30/110 = 27.27% → declining)
    spread(S,T) = 20.0 - 5.0 = 15.0pp
    count positive YoY [S,T,D] = 2
    streak(S, positive) = 2  (2026✓ 2025✓; 2024 has no prior-yr → break)

Run: python3 -m pytest analysis/tests/test_compute_sibc.py -q
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from signals.compute import sibc  # noqa: E402

P = "2026-03-31"


def _df():
    rows = [
        # date, code, parent_code, outstanding_cr
        ("2024-03-31", "S", "",  100.0),
        ("2025-03-31", "S", "",  110.0),
        ("2026-03-31", "S", "",  132.0),
        ("2025-03-31", "C", "S",  30.0),
        ("2026-03-31", "C", "S",  33.0),
        ("2025-03-31", "T", "",  100.0),
        ("2026-03-31", "T", "",  105.0),
        ("2025-03-31", "D", "",  100.0),
        ("2026-03-31", "D", "",   90.0),
    ]
    return pd.DataFrame(
        [{"date": d, "code": c, "parent_code": p, "statement": "Statement 1",
          "outstanding_cr": v, "is_priority_sector_memo": False} for d, c, p, v in rows]
    )


def _val(rows):
    """Single scalar result helper."""
    assert len(rows) == 1
    return rows[0]


# ── date helpers ──────────────────────────────────────────────────────────────

def test_prior_year():
    avail = {"2024-03-31", "2025-03-31", "2026-03-31"}
    assert sibc._prior_year("2026-03-31", avail) == "2025-03-31"
    assert sibc._prior_year("2025-03-31", avail) == "2024-03-31"
    assert sibc._prior_year("2024-03-31", avail) is None  # 2023 absent


def test_prior_period():
    avail = {"2024-03-31", "2025-03-31", "2026-03-31"}
    assert sibc._prior_period("2026-03-31", avail) == "2025-03-31"
    assert sibc._prior_period("2024-03-31", avail) is None
    assert sibc._prior_period("2099-01-01", avail) is None  # not present


# ── status rule evaluation ────────────────────────────────────────────────────

def test_eval_status_first_match_wins():
    rules = [{"if": "value > 10", "then": "high"}, {"if": "true", "then": "low"}]
    assert sibc._eval_status(rules, 20, 10) == "high"
    assert sibc._eval_status(rules, 5, 10) == "low"


def test_eval_status_none_is_unknown():
    rules = [{"if": "true", "then": "x"}]
    assert sibc._eval_status(rules, None, 1) == "unknown"


def test_eval_status_uses_prev_value():
    rules = [{"if": "value > prev_value", "then": "accelerating"},
             {"if": "true", "then": "steady"}]
    assert sibc._eval_status(rules, 20, 10) == "accelerating"
    assert sibc._eval_status(rules, 10, 20) == "steady"


# ── scalar compute methods ────────────────────────────────────────────────────

def test_csv_sector_yoy():
    r = _val(sibc.csv_sector_yoy({"code": "S"}, P, _df()))
    assert r["value"] == pytest.approx(20.0)
    assert r["unit"] == "pct"


def test_csv_sector_yoy_acceleration_status():
    r = _val(sibc.csv_sector_yoy(
        {"code": "S", "status_rules":
            [{"if": "value > prev_value", "then": "accelerating"},
             {"if": "true", "then": "steady"}]}, P, _df()))
    assert r["status"] == "accelerating"   # 20% now vs 10% prior year


def test_csv_sector_yoy_missing_prior_is_unknown():
    # 2024-03-31 has no 2023 prior year → unknown
    r = _val(sibc.csv_sector_yoy({"code": "S"}, "2024-03-31", _df()))
    assert r["value"] is None and r["status"] == "unknown"


def test_csv_sector_abs():
    r = _val(sibc.csv_sector_abs({"code": "S"}, P, _df()))
    assert r["value"] == pytest.approx(132.0)


def test_csv_sector_share():
    r = _val(sibc.csv_sector_share({"code": "C", "parent_code": "S"}, P, _df()))
    assert r["value"] == pytest.approx(25.0)


def test_csv_sector_share_declining_vs_prior():
    r = _val(sibc.csv_sector_share(
        {"code": "C", "parent_code": "S", "status_rules":
            [{"if": "value < prev_value", "then": "declining"},
             {"if": "true", "then": "rising"}]}, P, _df()))
    assert r["status"] == "declining"   # 25.0% now vs 27.27% prior period


def test_csv_sector_yoy_spread():
    r = _val(sibc.csv_sector_yoy_spread({"code_a": "S", "code_b": "T"}, P, _df()))
    assert r["value"] == pytest.approx(15.0)
    assert r["unit"] == "pp"


def test_csv_sector_count_positive_yoy():
    r = _val(sibc.csv_sector_count_positive_yoy(
        {"child_codes": ["S", "T", "D"]}, P, _df()))
    assert r["value"] == pytest.approx(2.0)   # S,T positive; D negative


# ── multi-period: streak ──────────────────────────────────────────────────────

def test_csv_streak_positive():
    r = _val(sibc.csv_streak({"code": "S", "condition": "positive"}, P, _df()))
    assert r["value"] == pytest.approx(2.0)   # 2026✓ 2025✓; 2024 no prior-yr
    assert r["unit"] == "periods"


def test_csv_streak_breaks_on_negative():
    # D declined in 2026 → positive streak is 0 → unknown
    r = _val(sibc.csv_streak({"code": "D", "condition": "positive"}, P, _df()))
    assert r["value"] is None and r["status"] == "unknown"


def test_csv_streak_threshold_condition():
    # S YoY: 2026=20, 2025=10. condition above:15 → only 2026 qualifies → 1
    r = _val(sibc.csv_streak({"code": "S", "condition": "above:15"}, P, _df()))
    assert r["value"] == pytest.approx(1.0)


# ── dispatcher swallows unknown method → _unknown, never raises ────────────────

def test_compute_unknown_method_is_safe():
    r = _val(sibc.compute("x", {"method": "no_such_method"}, P, _df()))
    assert r["status"] == "unknown"
