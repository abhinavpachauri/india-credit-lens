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
