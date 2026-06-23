#!/usr/bin/env python3
"""
Golden tests for analysis/signals/compute/atm_pos.py (Layer-1 deterministic compute).

Fixture (record_type "total" rows give the aggregate; "bank" rows sum per category):
    report_date   metric  total      PSB banks (A,B)
    2025-04-30    cards   1000       350 + 300 = 650
    2026-03-31    cards   1100       -
    2026-04-30    cards   1200       400 + 320 = 720
    2025-04-30    spend    400
    2026-03-31    spend    450
    2026-04-30    spend    500

Hand-computed for period 2026-04-30:
    total_abs(cards)             = 1200          (MoM prior 1100)
    total_yoy(cards)             = (1200-1000)/1000 = 20.0%
    total_ratio(spend/cards)     = 500/1200      = 0.4167
    ratio_sum(cards/(cards+spend)) = 1200/1700   = 70.5882%
    sum_yoy([cards,spend])       = (1700-1400)/1400 = 21.4286%
    category_share(PSB,cards)    = 720/1200      = 60.0%
    category_yoy(PSB,cards)      = (720-650)/650 = 10.7692%
    streak(cards, growth)        = 2  (1200>1100>1000; 2025 has no prior → break)

Run: python3 -m pytest analysis/tests/test_compute_atm_pos.py -q
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from signals.compute import atm_pos as ap  # noqa: E402

P = "2026-04-30"


def _df():
    def tot(d, m, v):
        return {"report_date": d, "bank_name": "", "bank_category": "",
                "record_type": "total", "metric": m, "value": v,
                "unit": "count", "data_status": "actual"}

    def bank(d, name, cat, m, v):
        return {"report_date": d, "bank_name": name, "bank_category": cat,
                "record_type": "bank", "metric": m, "value": v,
                "unit": "count", "data_status": "actual"}

    rows = [
        tot("2025-04-30", "cards", 1000), tot("2026-03-31", "cards", 1100),
        tot("2026-04-30", "cards", 1200),
        tot("2025-04-30", "spend", 400), tot("2026-03-31", "spend", 450),
        tot("2026-04-30", "spend", 500),
        bank("2025-04-30", "A", "PSB", "cards", 350),
        bank("2025-04-30", "B", "PSB", "cards", 300),
        bank("2026-04-30", "A", "PSB", "cards", 400),
        bank("2026-04-30", "B", "PSB", "cards", 320),
    ]
    return pd.DataFrame(rows)


def _val(rows):
    assert len(rows) == 1
    return rows[0]


# ── helpers ───────────────────────────────────────────────────────────────────

def test_total_val_and_category_val():
    df = _df()
    assert ap._total_val(df, P, "cards") == 1200.0
    assert ap._category_val(df, P, "cards", "PSB") == 720.0   # sums A+B


def test_prior_year_and_period():
    avail = {"2025-04-30", "2026-03-31", "2026-04-30"}
    assert ap._prior_year(P, avail) == "2025-04-30"
    assert ap._prior_period(P, avail) == "2026-03-31"


# ── scalar methods ────────────────────────────────────────────────────────────

def test_total_abs():
    assert _val(ap.csv_total_abs({"metric": "cards"}, P, _df()))["value"] == pytest.approx(1200.0)


def test_total_yoy():
    assert _val(ap.csv_total_yoy({"metric": "cards"}, P, _df()))["value"] == pytest.approx(20.0)


def test_total_yoy_missing_prior_unknown():
    r = _val(ap.csv_total_yoy({"metric": "cards"}, "2025-04-30", _df()))
    assert r["value"] is None and r["status"] == "unknown"


def test_total_ratio():
    r = _val(ap.csv_total_ratio(
        {"metric": "spend", "denominator_metric": "cards"}, P, _df()))
    assert r["value"] == pytest.approx(500 / 1200, rel=1e-4)


def test_ratio_sum():
    r = _val(ap.csv_ratio_sum(
        {"metric": "cards", "denominator_metrics": ["cards", "spend"]}, P, _df()))
    assert r["value"] == pytest.approx(1200 / 1700 * 100, rel=1e-4)


def test_sum_yoy():
    r = _val(ap.csv_sum_yoy({"metrics": ["cards", "spend"]}, P, _df()))
    assert r["value"] == pytest.approx((1700 - 1400) / 1400 * 100, rel=1e-4)


def test_category_share():
    r = _val(ap.csv_category_share(
        {"metric": "cards", "category": "PSB"}, P, _df()))
    assert r["value"] == pytest.approx(60.0)
    assert r["entity_id"] == "PSB"


def test_category_yoy():
    r = _val(ap.csv_category_yoy(
        {"metric": "cards", "category": "PSB"}, P, _df()))
    assert r["value"] == pytest.approx((720 - 650) / 650 * 100, rel=1e-4)


# ── streak (MoM direction) ────────────────────────────────────────────────────

def test_streak_growth():
    r = _val(ap.csv_streak(
        {"metric": "cards", "condition": "value > prev_value"}, P, _df()))
    assert r["value"] == pytest.approx(2.0)   # 1200>1100>1000; 2025 no prior


def test_streak_contraction_is_zero_not_unknown():
    # cards grew, so a contraction streak is 0 (valid result, not unknown)
    r = _val(ap.csv_streak(
        {"metric": "cards", "condition": "value < prev_value"}, P, _df()))
    assert r["value"] == pytest.approx(0.0)


# ── dispatcher safety ─────────────────────────────────────────────────────────

def test_compute_unknown_method_is_safe():
    r = _val(ap.compute("x", {"method": "nope"}, P, _df()))
    assert r["status"] == "unknown"
