"""The single-entity dominance guard — the fix for a reporting artifact reading as a market signal.

June 2026 is the live case: POS terminals printed -15.8% YoY, but ~98% of it was one issuer (ICICI)
dropping ~1.5M terminals in a single month; ex that issuer the fleet edged up. These tests pin the
guard to that ground truth and to the property that only a truly dominated move trips it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))

from signals import is_news, proximity                       # noqa: E402
from signals.dominance import move_dominance                 # noqa: E402

PERIOD = "2026-06-30"


def test_pos_terminals_is_flagged_as_single_issuer():
    d = move_dominance("atm_pos", "pos-terminals-yoy", PERIOD)
    assert d is not None and d.dominant
    assert d.top_entity and "ICICI" in d.top_entity
    assert d.top_move_share > 0.9                 # one issuer is nearly the whole move
    assert d.ex_top_yoy_pct is not None and abs(d.ex_top_yoy_pct) < 3   # the rest of the fleet is ~flat


def test_healthy_aggregates_are_not_flagged():
    # cc / dc outstanding moved broadly, not from one entity — must NOT trip the guard.
    for m in ("cc-outstanding-yoy", "dc-outstanding-yoy"):
        d = move_dominance("atm_pos", m, PERIOD)
        assert d is not None and not d.dominant, m


def test_ratio_inherits_its_denominator_artifact():
    d = move_dominance("atm_pos", "upi-qr-per-pos", PERIOD)
    assert d is not None and d.dominant and d.via_denominator


def test_unmapped_metric_returns_none():
    assert move_dominance("atm_pos", "upi-qr-yoy", PERIOD) is None      # no per-entity count to decompose


def test_is_news_keeps_raw_metric_but_zeroes_the_corrupted_ratio():
    """A raw aggregate driven by one issuer stays a read (attributed, not hidden); a derived ratio
    riding that denominator has a spurious record and is zeroed."""
    conn = proximity._con()
    reg = proximity.load_registry()
    try:
        raw = is_news.score(conn, "pos-terminals-yoy", reg["pos-terminals-yoy"])
        assert raw["factors"]["artifact"] is True          # flagged so the insight can attribute it
        assert raw["score"] > 0                             # but still surfaces as an (explained) read

        ratio = is_news.score(conn, "upi-qr-per-pos", reg["upi-qr-per-pos"])
        assert ratio["factors"]["artifact"] is True
        assert ratio["factors"]["record"] is False and ratio["factors"]["magnitude"] is False
        assert ratio["score"] == 0.0                        # its "record" is arithmetically spurious

        # a genuine record is untouched by the guard
        assert is_news.score(conn, "cc-outstanding-yoy", reg["cc-outstanding-yoy"])["factors"]["record"] is True
    finally:
        conn.close()


def test_the_guard_covers_the_window_the_metric_spans():
    """A guard only protects the window it measures.

    The MoM check flags the month a single issuer lurches; a YoY metric then carries that lurch
    for another eleven months. Jun 2026 is the lurch (ICICI, 97.7% of that month's move); by
    Jul 2026 the MoM move is an ordinary +1.1% while the headline still reads -15.8% YoY. Before
    the year window was tested, Jul went unflagged and the card published the artifact as a market
    trend. Both months are asserted so neither window can lapse unnoticed.
    """
    lurch = move_dominance("atm_pos", "pos-terminals-yoy", "2026-06-30")
    assert lurch.dominant and lurch.window == "mom"
    assert "ICICI" in lurch.top_entity

    after = move_dominance("atm_pos", "pos-terminals-yoy", "2026-07-31")
    assert after.dominant, "the artifact is still in the YoY headline a month later"
    assert after.window == "yoy"
    assert "ICICI" in after.top_entity
    # the honest market read: excluding that issuer, the fleet GREW over the year
    assert after.ex_top_yoy_pct > 0


def test_an_ordinary_month_is_not_flagged():
    """The guard must stay quiet when no single entity drives the move — otherwise every card
    acquires a caveat and the caveat stops meaning anything."""
    calm = move_dominance("atm_pos", "pos-terminals-yoy", "2026-05-31")
    assert calm is not None and not calm.dominant and calm.top_entity is None
