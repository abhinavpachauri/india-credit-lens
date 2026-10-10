#!/usr/bin/env python3
"""
Unit tests for analysis/core/relationship_test.py (SYSTEM_MODEL_SPEC §16 Step 6b).

The control that matters most is the first: two lines that only share a tide must NOT pass.
That is exactly how the first real candidate (HFC lending vs direct housing) looked like a
relationship before the tide was removed.

Run: python3 -m pytest analysis/tests/test_relationship_test.py -q
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import relationship_test as rt  # noqa: E402

N = 24
rng = random.Random(11)
TIDE = {k: rng.gauss(0, 2) for k in range(N)}


def noise(seed):
    r = random.Random(seed)
    return {k: r.gauss(0, 1) for k in range(N)}


def test_two_lines_that_only_share_a_tide_are_not_supported():
    a = {k: TIDE[k] + v for k, v in noise(1).items()}
    b = {k: TIDE[k] + v for k, v in noise(2).items()}
    res = rt.test(a, b, TIDE, sign=1, lag=0)
    assert res["verdict"] == "not_supported"


def test_a_real_push_beyond_the_tide_is_supported():
    a = {k: TIDE[k] + v for k, v in noise(3).items()}
    own = {k: a[k] - TIDE[k] for k in a}                    # a's own part, beyond the tide
    b = {k: TIDE[k] + 1.5 * own[k] + 0.3 * v for k, v in noise(4).items()}
    assert rt.test(a, b, TIDE, sign=1, lag=0)["verdict"] == "supported"
    assert rt.test(a, b, TIDE, sign=-1, lag=0)["verdict"] == "opposite"


def test_a_lagged_push_is_found_only_at_its_declared_lag():
    a = {k: TIDE[k] + v for k, v in noise(5).items()}
    own = {k: a[k] - TIDE[k] for k in a}
    b = {k: TIDE[k] + (1.5 * own[k - 2] if k >= 2 else 0) + 0.3 * v for k, v in noise(6).items()}
    assert rt.test(a, b, TIDE, sign=1, lag=2)["verdict"] == "supported"
    assert rt.test(a, b, TIDE, sign=1, lag=0)["verdict"] == "not_supported"   # no rescue by lag


def test_too_few_months_says_so():
    short = {k: v for k, v in noise(7).items() if k < 6}
    assert rt.test(short, short, TIDE, sign=1, lag=0)["verdict"] == "too_few"


def test_a_family_of_tests_raises_the_bar(monkeypatch):
    """p = 0.03 passes alone and fails as one of four (bar 0.0125). The p-value is fixed so the
    bar, not the luck of a synthetic series, is what is tested."""
    monkeypatch.setattr(rt, "shuffle_p", lambda x, y, seed=rt.SEED: (0.5, 0.03))
    a = {k: TIDE[k] + v for k, v in noise(8).items()}
    one, four = rt.test(a, a, TIDE, sign=1, lag=0), rt.test(a, a, TIDE, sign=1, lag=0, family=4)
    assert (one["alpha"], one["verdict"]) == (0.05, "supported")
    assert (four["alpha"], four["verdict"]) == (0.0125, "not_supported")


def test_a_reference_series_is_read_as_monthly_changes_in_its_yoy(monkeypatch):
    """reference_changes reads through real_economy.reference (the 1f reader), takes YoY of the
    index, and keeps only changes one data month apart."""
    import types
    vals = {}
    for i, p in enumerate(["2024-01-31", "2024-02-29", "2024-03-31",
                           "2025-01-31", "2025-02-28", "2025-03-31"]):
        vals[("wpi", "x", "index", p)] = [100, 100, 100, 110, 121, 100][i]
    fake = types.SimpleNamespace(values=vals)
    monkeypatch.setattr("signals.compute.real_economy.reference", lambda pipeline: fake)
    ch = rt.reference_changes("mospi", "wpi/x")
    jan25 = 2025 * 12
    assert set(ch) == {jan25 + 1, jan25 + 2}               # YoY 10 → 21 → 0
    assert round(ch[jan25 + 1], 6) == 11.0 and round(ch[jan25 + 2], 6) == -21.0
