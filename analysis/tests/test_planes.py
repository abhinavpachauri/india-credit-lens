#!/usr/bin/env python3
"""Unit tests for the read/composition/subject plane classifier (signals/planes.py).

The stillness rule is tested against a synthetic in-memory signals table so the exact
band/priority behaviour is pinned; the partition + measurement are smoke-tested against
the live signals.db so a schema drift shows up here rather than in a silent dashboard.

Run: python3 -m pytest analysis/tests/test_planes.py -q
"""
import sqlite3
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

from signals import planes                                        # noqa: E402


# ── a synthetic signals table, one signal's total-level history ───────────────

def _db(rows):
    """rows = list of (period, value, status). Builds the minimal table the classifier reads."""
    conn = sqlite3.connect(":memory:")
    conn.execute("create table signals (pipeline text, metric_id text, period text, "
                 "entity_type text, entity_id text, value real, status text)")
    for period, value, status in rows:
        conn.execute("insert into signals values ('t','S',?,?,?,?,?)",
                     (period, "total", "total", value, status))
    conn.commit()
    return conn


def _sig(method="csv_sector_share", unit=None, status="stable"):
    return {"pipeline": "t", "layer": 1, "unit": unit, "current_status": status,
            "compute": {"method": method}}


def _months(vals, status="stable"):
    return [(f"2025-{i + 1:02d}-01", v, status) for i, v in enumerate(vals)]


# ── _band: shares and rates are absolute points; everything else relative ─────

def test_band_share_is_absolute_even_with_blank_unit():
    # a share carries unit=None but is pp-scale — must not get the (tiny) relative band
    assert planes._band(None, "csv_sector_share", [0.15, 0.16, 0.15]) == planes.BAND_ABS


def test_band_pct_unit_is_absolute():
    assert planes._band("pct", "csv_total_yoy", [8.0, 8.1, 7.9]) == planes.BAND_ABS


def test_band_count_is_relative_to_level():
    assert planes._band("count", "csv_total_abs", [100.0, 100.0]) == planes.BAND_REL * 100.0


def test_band_zero_level_is_undefined():
    assert planes._band("count", "csv_total_abs", [0.0, 0.0]) is None


def test_is_share():
    assert planes._is_share("csv_sector_share")
    assert not planes._is_share("csv_total_yoy")


# ── _one_regime: label wobble across regimes vs a held regime ─────────────────

def test_one_regime_holds_through_accel_decel_wobble():
    # strengthening ↔ active both collapse to 'grow' — a held regime
    assert planes._one_regime(["strengthening", "active", "strengthening"])


def test_one_regime_broken_by_grow_shrink():
    assert not planes._one_regime(["active", "declining"])


def test_one_regime_ignores_unknowns():
    assert planes._one_regime(["active", "unknown", "strengthening"])


# ── is_structural: the core judgement ─────────────────────────────────────────

def test_flat_share_is_structural():
    """A share sitting at ~33% all year is structure, whatever its status label does."""
    conn = _db(_months([33.0, 33.1, 32.9, 33.2, 33.0, 33.1, 32.8, 33.0], status="active"))
    out = planes.is_structural(conn, "S", _sig())
    assert out["structural"] is True and out["still"] is True


def test_flat_share_structural_despite_status_wobble():
    """The regime_held=False case that the measurement retired: value still, label churning."""
    rows = _months([33.0, 33.1, 32.9, 33.2], status="active")
    rows[1] = (rows[1][0], rows[1][1], "stable")      # a grow↔flat wobble on noise
    conn = _db(rows)
    out = planes.is_structural(conn, "S", _sig())
    assert out["structural"] is True and out["regime_held"] is False


def test_rotating_share_is_not_structural():
    """A share that moved 10 pp over the year is rotation — news, not structure."""
    conn = _db(_months([20.0, 22.0, 24.0, 26.0, 28.0, 30.0]))
    assert planes.is_structural(conn, "S", _sig())["structural"] is False


def test_streak_is_never_structural():
    conn = _db(_months([1.0, 2.0, 3.0, 4.0]))
    out = planes.is_structural(conn, "S-streak", _sig(method="csv_mom_streak", unit="periods"))
    assert out["structural"] is False and "momentum" in out["reason"]


def test_flat_count_is_structural_by_relative_band():
    conn = _db(_months([1000.0, 1010.0, 990.0, 1005.0, 1002.0]))
    assert planes.is_structural(conn, "S", _sig(method="csv_total_abs", unit="count"))["structural"]


def test_growing_count_is_not_structural():
    conn = _db(_months([1000.0, 1100.0, 1200.0, 1400.0, 1700.0]))
    assert not planes.is_structural(conn, "S", _sig(method="csv_total_abs", unit="count"))["structural"]


def test_too_short_history_is_unjudged():
    conn = _db(_months([33.0, 33.1]))
    assert planes.is_structural(conn, "S", _sig()) is None


def test_retired_signal_is_unjudged():
    conn = _db(_months([33.0, 33.1, 32.9, 33.0]))
    assert planes.is_structural(conn, "S", _sig(status="active") | {"current_status": "retired"}) is None


# ── live smoke: partition + measurement against real signals.db ───────────────

def test_classify_partitions_cleanly():
    rows = planes.classify("sibc")
    assert rows, "no signals classified — schema drift?"
    assert all(r["plane"] in (planes.READ, planes.COMPOSITION, planes.SUBJECT) for r in rows)


def test_reads_sort_before_composition_before_subjects():
    order = {planes.READ: 0, planes.COMPOSITION: 1, planes.SUBJECT: 2}
    seen = [order[r["plane"]] for r in planes.classify("sibc")]
    assert seen == sorted(seen)


def test_measure_catches_structure_and_rejects_movers():
    """The property the classifier exists for, measured non-circularly on the live registry:
    every truly-still non-news share lands in composition, and no magnitude outlier does."""
    m = planes.measure()
    caught, total = m["catch"]
    wrong, movers = m["false_reject"]
    assert total > 0 and caught == total          # 100% catch
    assert movers > 0 and wrong == 0              # 0% false-reject
    assert m["partition"].get(planes.COMPOSITION, 0) > 0
