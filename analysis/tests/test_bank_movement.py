"""Story readings: the movement family one level down, and the break flag.

Spec: signals/README.md, "Story readings — per-bank movement and the break flag". The rules
that matter are driven with small frames built here, so a branch the live month does not meet
(a leaver, a non-additive month, a flag that later data could move) is still exercised. The
live data is read only for the enumerated property (every metric) and the two known breaks.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from signals.compute import atm_pos as A          # noqa: E402


def _frame(series: dict[str, list[float]], start="2025-01-31", total=None) -> pd.DataFrame:
    """A one-metric payments frame: {bank: monthly values}, consecutive month-ends from start.
    The published total is the banks' sum unless `total` (one value per month) overrides it."""
    dates = pd.date_range(start, periods=len(next(iter(series.values()))), freq="ME")
    rows = []
    for i, d in enumerate(dates):
        ds = d.strftime("%Y-%m-%d")
        vals = {b: v[i] for b, v in series.items() if v[i] is not None}
        for b, v in vals.items():
            rows.append(dict(report_date=ds, bank_name=b, bank_category="Private Sector Banks",
                             record_type="bank", metric="m", value=v, unit="count"))
        rows.append(dict(report_date=ds, bank_name=None, bank_category=None, record_type="total",
                         metric="m", value=(total[i] if total else sum(vals.values())), unit="count"))
    return pd.DataFrame(rows)


def _by(rows, entity_type):
    return {r["entity_id"]: r["value"] for r in rows if r["entity_type"] == entity_type}


P = {"metric": "m", "window": 12}


# ── momentum and allocation ───────────────────────────────────────────────────

def test_a_bank_that_left_counts_its_whole_book_as_its_move():
    """The category code keeps only members present at both ends; for banks that would drop a
    leaver's book and the deltas would stop adding up to the market's move."""
    df = _frame({"A": [100.0] * 13, "B": [50.0] * 12 + [None]})
    mom = A.csv_bank_momentum(P, "2026-01-31", df)
    assert _by(mom, "bank")["B"] == -50.0
    assert _by(mom, "aggregate")["total"] == -50.0          # the published total's move


def test_a_bank_with_nothing_at_either_end_is_not_a_member():
    df = _frame({"A": [10.0] * 12 + [20.0], "Z": [0.0] * 13})
    assert "Z" not in _by(A.csv_bank_momentum(P, "2026-01-31", df), "bank")


def test_bank_allocation_carries_no_weights_the_share_scan_already_stores():
    df = _frame({"A": [10.0] * 12 + [20.0], "B": [10.0] * 12 + [15.0]})
    kinds = {r["entity_type"] for r in A.csv_bank_allocation(P, "2026-01-31", df)}
    assert kinds == {"contribution", "aggregate", "alloc"}


def test_a_non_additive_month_divides_by_the_published_total_and_says_so():
    """Branch 2. No payments month is non-additive today (832 of 832 measured), which is
    exactly why the branch is driven here rather than trusted to the live data."""
    df = _frame({"A": [10.0] * 12 + [20.0]}, total=[20.0] * 12 + [40.0])
    rows = A.csv_bank_allocation(P, "2026-01-31", df)
    assert _by(rows, "coverage")["total"] == 50.0           # A is half the published market
    assert _by(rows, "alloc")["A"] == 50.0                  # +10 of the market's +20


def test_a_missing_published_total_is_loud_not_a_fallback_to_the_banks():
    df = _frame({"A": [10.0] * 13})
    df = df[~((df.record_type == "total") & (df.report_date == "2026-01-31"))]
    rows = A.compute("x", {**P, "method": "csv_bank_allocation"}, "2026-01-31", df)
    assert [r["status"] for r in rows] == ["unknown"]


def test_every_metric_s_bank_moves_add_up_to_its_published_total_s_move():
    """Enumerated over all 26 metrics at the latest month, not sampled. Tolerance 1e-6
    relative: the published totals carry their own rounding (dc_pos_withdrawal_val differs from
    its banks' sum by 6e-9), and 1e-6 is still a hundred times tighter than ADDITIVE_EPS."""
    df = A._load_df()
    latest = max(map(str, df["report_date"].unique()))
    back = A._month_back(latest, 12, set(map(str, df["report_date"].unique())))
    metrics = sorted(map(str, df["metric"].unique()))
    assert len(metrics) == 26
    for m in metrics:
        net = _by(A.csv_bank_momentum({"metric": m}, latest, df), "aggregate")["total"]
        published = A._total_val(df, latest, m) - A._total_val(df, back, m)
        assert net == pytest.approx(published, rel=1e-6), m


# ── the break flag ────────────────────────────────────────────────────────────

STEADY = [10.0, 10.2, 10.1, 10.3, 10.2, 10.4, 10.3, 10.5]   # moves ~0.2 pp a month


def _shares(bank_a: list[float]) -> pd.DataFrame:
    """Bank A's share is the given list (the market is always 100)."""
    return _frame({"A": bank_a, "B": [100.0 - v for v in bank_a]})


def test_a_one_month_jump_far_beyond_the_bank_s_usual_move_is_flagged():
    df = _shares(STEADY + [14.0])
    rows = A.csv_bank_step({"metric": "m"}, "2025-09-30", df)
    assert _by(rows, "bank")["A"] == pytest.approx(3.5)


def test_a_jump_under_the_one_point_floor_is_not_flagged_however_quiet_the_bank():
    df = _shares([10.0] * 8 + [10.9])
    assert A.csv_bank_step({"metric": "m"}, "2025-09-30", df) == []


def test_a_gap_in_the_file_is_not_a_one_month_step():
    df = _shares(STEADY + [14.0])
    df = df[df.report_date != "2025-08-31"]
    assert A.csv_bank_step({"metric": "m"}, "2025-09-30", df) == []


def test_too_little_history_flags_nothing():
    df = _shares([10.0, 10.1, 10.2, 15.0])
    assert A.csv_bank_step({"metric": "m"}, "2025-04-30", df) == []


def test_a_stored_flag_does_not_move_when_later_months_arrive():
    """The usual move is read from changes BEFORE t only. Later volatility must not un-flag
    (or flag) a month already stored, or freshness would chase its own history."""
    early = A.csv_bank_step({"metric": "m"}, "2025-09-30", _shares(STEADY + [14.0]))
    later = A.csv_bank_step({"metric": "m"}, "2025-09-30",
                            _shares(STEADY + [14.0, 2.0, 20.0, 5.0]))
    assert early == later


@pytest.mark.parametrize("metric, bank, period, sign", [
    ("cc_pos_txn_val", "HDFC BANK LTD", "2025-12-31", -1),    # share −4.2 pp in one month
    ("pos_terminals",  "ICICI BANK LTD", "2026-06-30", -1),   # the POS reclassification
])
def test_the_two_known_breaks_are_caught(metric, bank, period, sign):
    rows = A.csv_bank_step({"metric": metric}, period, A._load_df())
    v = _by(rows, "bank").get(bank)
    assert v is not None and v * sign > 0
