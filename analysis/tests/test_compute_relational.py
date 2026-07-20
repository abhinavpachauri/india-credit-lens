#!/usr/bin/env python3
"""
Golden tests for the relational compute methods (rotation + divergence),
spec: analysis/signals/README.md — "Relational signal methods".

SIBC fixture (Statement 1, parent P with children X/Y/Z; two annual dates):
    date         P     X     Y     Z      shares:  X      Y      Z
    2025-03-31   200   100   60    40              50.0%  30.0%  20.0%
    2026-03-31   250   150   64    36              60.0%  25.6%  14.4%

Hand-computed for period 2026-03-31:
    rotation Δshare:  X +10.0pp  Y −4.4pp  Z −5.6pp
    rotation mass  =  (10.0 + 4.4 + 5.6) / 2 = 10.0pp
    YoY:  P +25%   X +50%   Y +6.667%   Z −10%
    divergence: only Z flagged (opposite sign, |−10| ≥ 2, |−10−25| = 35 ≥ 5)
                value = −35.0pp

ATM/POS fixture (metric "cards"; PSB = A+B+D, PVT = C):
    date         total   A(PSB)  B(PSB)  D(PSB)  C(PVT)   PSB      PVT
    2025-04-30   1100    350     300     100     350      750      350
    2026-04-30   1280    400     320     80      480      800      480

Hand-computed for period 2026-04-30:
    shares 2025: PSB 68.18%  PVT 31.82%   (of 1100)
    shares 2026: PSB 62.50%  PVT 37.50%   (of 1280)
    rotation Δshare:  PVT +5.6818pp  PSB −5.6818pp   mass = 5.6818pp
    YoY:  PSB (800−750)/750 = +6.6667%   D (80−100)/100 = −20%
    divergence: only D flagged, value = −20 − 6.6667 = −26.6667pp

Run: python3 -m pytest analysis/tests/test_compute_relational.py -q
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from signals.compute import sibc      # noqa: E402
from signals.compute import atm_pos as ap  # noqa: E402


# ── SIBC fixture ──────────────────────────────────────────────────────────────

SIBC_P = "2026-03-31"


def _sibc_df():
    rows = [
        # date, code, parent_code, level, sector, value
        ("2025-03-31", "P", "",  1, "Parent", 200.0),
        ("2026-03-31", "P", "",  1, "Parent", 250.0),
        ("2025-03-31", "X", "P", 2, "Xray",   100.0),
        ("2026-03-31", "X", "P", 2, "Xray",   150.0),
        ("2025-03-31", "Y", "P", 2, "Yankee",  60.0),
        ("2026-03-31", "Y", "P", 2, "Yankee",  64.0),
        ("2025-03-31", "Z", "P", 2, "Zulu",    40.0),
        ("2026-03-31", "Z", "P", 2, "Zulu",    36.0),
    ]
    return pd.DataFrame(
        [{"date": d, "code": c, "parent_code": p, "level": lv, "sector": s,
          "statement": "Statement 1", "outstanding_cr": v,
          "is_priority_sector_memo": False}
         for d, c, p, lv, s, v in rows]
    )


SIBC_ROT = {"method": "csv_sector_rotation", "parent_code": "P",
            "child_level": 2, "entity_type": "sector"}
SIBC_DIV = {"method": "csv_sector_divergence", "parent_code": "P",
            "child_level": 2, "entity_type": "sector"}


# ── SIBC rotation ─────────────────────────────────────────────────────────────

def test_sibc_rotation_deltas_and_mass():
    rows = sibc.csv_sector_rotation(SIBC_ROT, SIBC_P, _sibc_df())
    by_id = {r["entity_id"]: r for r in rows}
    assert by_id["Xray"]["value"] == pytest.approx(10.0, abs=1e-3)
    assert by_id["Yankee"]["value"] == pytest.approx(-4.4, abs=1e-3)
    assert by_id["Zulu"]["value"] == pytest.approx(-5.6, abs=1e-3)
    assert by_id["total"]["value"] == pytest.approx(10.0, abs=1e-3)
    assert by_id["total"]["entity_type"] == "aggregate"
    assert all(r["unit"] == "pp" for r in rows)


def test_sibc_rotation_default_statuses():
    rows = sibc.csv_sector_rotation(SIBC_ROT, SIBC_P, _sibc_df())
    by_id = {r["entity_id"]: r for r in rows}
    assert by_id["Xray"]["status"] == "strengthening"
    assert by_id["Yankee"]["status"] == "weakening"
    assert by_id["Zulu"]["status"] == "weakening"
    assert by_id["total"]["status"] == "active"


def test_sibc_rotation_sorted_desc_entities_then_mass():
    rows = sibc.csv_sector_rotation(SIBC_ROT, SIBC_P, _sibc_df())
    entities = rows[:-1]
    assert [r["entity_id"] for r in entities] == ["Xray", "Yankee", "Zulu"]
    assert rows[-1]["entity_id"] == "total"


def test_sibc_rotation_no_window_no_rows():
    # 2025-03-31 has no 2024 comparison date → the first window emits nothing.
    assert sibc.csv_sector_rotation(SIBC_ROT, "2025-03-31", _sibc_df()) == []


def test_sibc_rotation_window_is_calendar_not_positional():
    # Insert an extra date between the two annual endpoints: a positional
    # 12-back would miss; the calendar window must still find 2025-03-31.
    df = _sibc_df()
    extra = df[df["date"] == "2025-03-31"].copy()
    extra["date"] = "2025-09-30"
    rows = sibc.csv_sector_rotation(SIBC_ROT, SIBC_P, pd.concat([df, extra]))
    by_id = {r["entity_id"]: r for r in rows}
    assert by_id["Xray"]["value"] == pytest.approx(10.0, abs=1e-3)


# ── SIBC divergence ───────────────────────────────────────────────────────────

def test_sibc_divergence_flags_only_contradicting_child():
    rows = sibc.csv_sector_divergence(SIBC_DIV, SIBC_P, _sibc_df())
    assert len(rows) == 1
    r = rows[0]
    assert r["entity_id"] == "Zulu"
    assert r["value"] == pytest.approx(-35.0, abs=1e-3)   # −10 − (+25)
    assert r["unit"] == "pp"
    assert r["status"] == "active"


def test_sibc_divergence_min_gap_suppresses():
    rows = sibc.csv_sector_divergence({**SIBC_DIV, "min_gap": 40},
                                      SIBC_P, _sibc_df())
    assert rows == []


def test_sibc_divergence_min_abs_suppresses():
    rows = sibc.csv_sector_divergence({**SIBC_DIV, "min_abs": 15},
                                      SIBC_P, _sibc_df())
    assert rows == []


def test_sibc_divergence_no_prior_year_no_rows():
    assert sibc.csv_sector_divergence(SIBC_DIV, "2025-03-31", _sibc_df()) == []


# ── ATM/POS fixture ───────────────────────────────────────────────────────────

AP_P = "2026-04-30"


def _ap_df():
    def tot(d, v):
        return {"report_date": d, "bank_name": "", "bank_category": "",
                "record_type": "total", "metric": "cards", "value": v,
                "unit": "count", "data_status": "actual"}

    def bank(d, name, cat, v):
        return {"report_date": d, "bank_name": name, "bank_category": cat,
                "record_type": "bank", "metric": "cards", "value": v,
                "unit": "count", "data_status": "actual"}

    return pd.DataFrame([
        tot("2025-04-30", 1100), tot("2026-04-30", 1280),
        bank("2025-04-30", "A", "PSB", 350), bank("2026-04-30", "A", "PSB", 400),
        bank("2025-04-30", "B", "PSB", 300), bank("2026-04-30", "B", "PSB", 320),
        bank("2025-04-30", "D", "PSB", 100), bank("2026-04-30", "D", "PSB", 80),
        bank("2025-04-30", "C", "PVT", 350), bank("2026-04-30", "C", "PVT", 480),
    ])


AP_ROT = {"method": "csv_category_rotation", "metric": "cards"}
AP_DIV = {"method": "csv_bank_divergence", "metric": "cards"}


# ── ATM/POS rotation ──────────────────────────────────────────────────────────

def test_ap_rotation_deltas_and_mass():
    rows = ap.csv_category_rotation(AP_ROT, AP_P, _ap_df())
    by_id = {r["entity_id"]: r for r in rows}
    assert by_id["PVT"]["value"] == pytest.approx(5.6818, abs=1e-3)
    assert by_id["PSB"]["value"] == pytest.approx(-5.6818, abs=1e-3)
    assert by_id["total"]["value"] == pytest.approx(5.6818, abs=1e-3)
    assert by_id["total"]["entity_type"] == "aggregate"
    assert by_id["PVT"]["status"] == "strengthening"
    assert by_id["PSB"]["status"] == "weakening"


def test_ap_rotation_no_window_no_rows():
    assert ap.csv_category_rotation(AP_ROT, "2025-04-30", _ap_df()) == []


# ── ATM/POS bank divergence ───────────────────────────────────────────────────

def test_ap_divergence_flags_only_contradicting_bank():
    rows = ap.csv_bank_divergence(AP_DIV, AP_P, _ap_df())
    assert len(rows) == 1
    r = rows[0]
    assert r["entity_id"] == "D"
    assert r["entity_type"] == "bank"
    assert r["value"] == pytest.approx(-26.6667, abs=1e-3)   # −20 − (+6.667)
    assert r["status"] == "active"


def test_ap_divergence_min_base_excludes_structural_zero():
    # Bank E: zero base last year, huge base now — structure (new entrant /
    # issuer ramp), never an anomaly. min_base must exclude it by construction.
    df = pd.concat([_ap_df(), pd.DataFrame([
        {"report_date": "2025-04-30", "bank_name": "E", "bank_category": "PSB",
         "record_type": "bank", "metric": "cards", "value": 0.0,
         "unit": "count", "data_status": "actual"},
        {"report_date": "2026-04-30", "bank_name": "E", "bank_category": "PSB",
         "record_type": "bank", "metric": "cards", "value": 500.0,
         "unit": "count", "data_status": "actual"},
    ])])
    flagged = {r["entity_id"] for r in ap.csv_bank_divergence(AP_DIV, AP_P, df)}
    assert "E" not in flagged
    assert "D" in flagged


def test_ap_divergence_no_prior_year_no_rows():
    assert ap.csv_bank_divergence(AP_DIV, "2025-04-30", _ap_df()) == []
