"""
The rule that decides whether an opportunity is live.

`derive_opportunities.py` runs in both gates every period and had no tests. Its whole job is
one decision — given whether a driver fired now and last period, is this opportunity active,
watched, or closed — and that decision reaches the reader directly: an "active" badge on
/opportunities is the platform asserting something is happening right now.

Two properties are worth pinning beyond the truth table. Two periods rather than one is a
deliberate noise filter, so a single firing month must never reach `active`. And `retired` is a
lifecycle decision a human made in the model, so data must never resurrect it — that one is the
difference between a machine that reports and a machine that overrules its editor.
"""
import sqlite3
import sys
from pathlib import Path

import pytest

ANALYSIS = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"
sys.path.insert(0, str(ANALYSIS))

from core import derive_opportunities as do  # noqa: E402


@pytest.mark.parametrize("now,prior,expected", [
    (True,  True,  "active"),
    (True,  False, "watch"),
    (False, True,  "watch"),
    (False, False, "closed"),
])
def test_status_truth_table(now, prior, expected):
    assert do.opportunity_status(now, prior) == expected


def test_one_period_of_firing_is_never_active():
    """The two-period rule is the noise filter. A driver that fires once has not established
    anything — if this ever collapses to one period, every transient move becomes an opportunity."""
    assert do.opportunity_status(True, False) != "active"
    assert do.opportunity_status(False, True) != "active"


@pytest.mark.parametrize("now,prior", [(True, True), (True, False), (False, True), (False, False)])
def test_retired_is_never_resurrected_by_data(now, prior):
    """Retirement is a human decision recorded in the model. No combination of firing signals
    may override it."""
    assert do.opportunity_status(now, prior, "retired") == "retired"


@pytest.mark.parametrize("node_status", [None, "", "active", "watch", "closed", "proposed"])
def test_any_other_node_status_is_decided_by_the_data(node_status):
    """Only `retired` is special. A node carrying a stale status from a previous run must be
    recomputed, not trusted — that staleness is what this whole script exists to remove."""
    assert do.opportunity_status(True, True, node_status) == "active"
    assert do.opportunity_status(False, False, node_status) == "closed"


# ── The two database reads ────────────────────────────────────────────────────

@pytest.fixture
def db(tmp_path, monkeypatch):
    """A signals.db with three periods and a mix of firing and flat statuses."""
    path = tmp_path / "signals.db"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE signals (pipeline TEXT, period TEXT, metric_id TEXT, status TEXT)")
    rows = [
        ("sibc", "2026-04-30", "a", "strengthening"),
        ("sibc", "2026-04-30", "b", "stable"),
        ("sibc", "2026-05-31", "a", "weakening"),
        ("sibc", "2026-05-31", "b", "stable"),
        ("sibc", "2026-06-30", "a", "stable"),
        ("sibc", "2026-06-30", "b", "declining"),
        ("atm_pos", "2026-06-30", "a", "strengthening"),   # a different pipeline, must not leak
    ]
    con.executemany("INSERT INTO signals VALUES (?,?,?,?)", rows)
    con.commit(); con.close()
    monkeypatch.setattr(do, "DB", path)
    return path


def test_periods_before_walks_backwards_from_the_asked_period(db):
    assert do.periods_before("sibc", "2026-06-30", 2) == ["2026-06-30", "2026-05-31"]
    assert do.periods_before("sibc", "2026-05-31", 2) == ["2026-05-31", "2026-04-30"]


def test_periods_before_never_looks_into_the_future(db):
    """Re-deriving an older period must see only what was known then — otherwise a backfill
    would answer with data that did not exist at the time."""
    assert "2026-06-30" not in do.periods_before("sibc", "2026-05-31", 2)


def test_periods_before_tolerates_a_short_history(db):
    assert do.periods_before("sibc", "2026-04-30", 2) == ["2026-04-30"]


def test_firing_signals_excludes_flat_statuses(db):
    assert do.firing_signals("sibc", "2026-04-30") == {"a"}
    assert do.firing_signals("sibc", "2026-06-30") == {"b"}


def test_firing_signals_does_not_leak_across_pipelines(db):
    """Both pipelines share one store, so every read is scoped — a payments signal must never
    make a credit opportunity look live."""
    assert do.firing_signals("sibc", "2026-06-30") == {"b"}
    assert do.firing_signals("atm_pos", "2026-06-30") == {"a"}
