#!/usr/bin/env python3
"""Unit tests for the is-news reads selector (signals/is_news.py).

The pure factor logic is testable without the DB; the ranking is smoke-tested against
live signals.db so a schema drift shows up here rather than in a silent empty issue.
"""
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

from signals import is_news                                       # noqa: E402


# ── _extreme: the reversal test is the whole point ────────────────────────────

def test_monotonic_new_high_is_not_a_record():
    """A series that only ever rises (outstanding credit) hits a new high every month —
    that is arithmetic, not news, and must not score as a record."""
    assert is_news._extreme([1, 2, 3, 4, 5]) == (False, None)


def test_reversal_new_high_is_a_record():
    """A series that has gone both ways and now sets a fresh high IS news."""
    is_record, kind = is_news._extreme([5, 3, 4, 2, 6])
    assert is_record and kind == "record high"


def test_reversal_new_low_is_a_record():
    is_record, kind = is_news._extreme([2, 5, 3, 6, 1])
    assert is_record and kind == "record low"


def test_interior_value_is_not_a_record():
    assert is_news._extreme([1, 9, 3, 5, 4]) == (False, None)


def test_too_short_series_is_not_a_record():
    assert is_news._extreme([1, 2]) == (False, None)


# ── regime map: the wobble must not count as a flip ───────────────────────────

def test_accelerating_to_decelerating_is_same_regime():
    """strengthening ↔ active is the accelerating/decelerating wobble, still growing —
    it is NOT a regime flip and must not fire the flip factor."""
    assert is_news.REGIME["strengthening"] == is_news.REGIME["active"] == "grow"


def test_growing_to_shrinking_changes_regime():
    assert is_news.REGIME["active"] != is_news.REGIME["declining"]


# ── ranking + selection smoke tests (live registry + db) ──────────────────────

def test_ranked_runs_and_orders_by_score():
    rows = is_news.ranked("sibc")
    assert rows, "no signals scored — schema drift?"
    scores = [r["score"] for r in rows]
    assert scores == sorted(scores, reverse=True)


def test_select_reads_respects_k_and_floor():
    from distribution import distribution_sources as src
    cards = src.insight_cards("sibc", max_cards=8)
    reads = is_news.select_reads(cards, is_news.proximity.load_registry(), k=2)
    assert len(reads) <= 2
    for r in reads:
        assert r["news"]["score"] >= is_news.READ_FLOOR


def test_a_static_share_is_never_a_read():
    """The property the whole selector exists for: a structural, unmoving share scores
    below the read floor. Measured across the live registry — at least one such signal
    exists, and none of them clears the floor."""
    m = is_news.measure()
    reject, total = m["template_reject"]
    assert total > 0 and reject == total
