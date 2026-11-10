#!/usr/bin/env python3
"""
Controls for analysis/core/pooled_test.py (SYSTEM_MODEL_SPEC §16 Step 6d), run before any real
result is read. Synthetic lines are the gap changes the test reads; the driver is independent of
everything unless a link is planted.

  1 a planted differential link (half +, half −, delay 4) → linked, delay 4 found and confirmed
  2 a link planted on one line only → attributed to that line, not a group link
  3 an unrelated driver → `linked` at about the nominal rate (false rejection)
  4 lines sharing a monthly shock, unrelated driver → still about the nominal rate (month as unit)
  5 a uniform response across a sibling set → cancels in the gaps, the limit is stated
  6 a short history → too_short with months_needed, and at that many months about half pass
  7 direction refused when every line of a sibling set carries one sign

Run: python3 -m pytest analysis/tests/test_pooled_test.py -q
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import pooled_test as pt  # noqa: E402

FAST = dict(shuffles=500, bootstraps=300)


def world(T=60, lines=20, seed=0, beta=0.0, signs=None, lag=0, shock=0.0, only=None, uniform=0.0):
    """Driver a, its tide, line gap changes and the credit tide over T months."""
    g = np.random.default_rng(seed)
    t_a, t_b = g.normal(0, 1, T + 12), g.normal(0, 1, T + 12)
    x = g.normal(0, 1, T + 12)
    a = x + 0.8 * t_a                                   # the driver carries its own tide
    common = g.normal(0, 1, T + 12) * shock             # a monthly shock shared by every line
    signs = signs or [1 if i % 2 == 0 else -1 for i in range(lines)]
    raw = {}
    for i in range(lines):
        y = g.normal(0, 1, T + 12) + common + 0.5 * t_b
        if only is None or only == i:
            y[lag:] += beta * signs[i] * x[:T + 12 - lag]
        y[lag:] += uniform * x[:T + 12 - lag]           # the same push on every part
        raw[f"L{i:02d}"] = y
    if uniform:                                          # gaps to the group: the shared push cancels
        mean = np.mean(list(raw.values()), axis=0)
        raw = {k: v - mean + 0.5 * t_b for k, v in raw.items()}
    months = range(T + 12)
    lines_d = {k: {m: float(v[m]) for m in months} for k, v in raw.items()}
    return ({m: float(a[m]) for m in months}, {m: float(t_a[m]) for m in months},
            lines_d, {m: float(t_b[m]) for m in months}, dict(zip(sorted(raw), signs)))


def rate(make, runs=200):
    hits = 0
    for s in range(runs):
        a, t_a, lines, t_b, _ = make(s)
        K, D, design = pt.prepare(a, t_a, lines, t_b, 0)
        hits += pt.evaluate(K, D, design, shuffles=400, bootstraps=0, seed=s, attribute=False)["verdict"] == "linked"
    return hits / runs


def test_1_a_planted_differential_link_is_found_at_its_delay_and_confirmed():
    a, t_a, lines, t_b, _ = world(beta=0.35, lag=4, seed=1)
    res = pt.pooled(a, t_a, lines, t_b, **FAST)
    assert res["discovery"]["lag"] == 4
    assert res["verdict"] == "linked"
    assert res["effect"]["range"][0] > 0


def test_2_a_link_on_one_line_is_that_lines_finding():
    a, t_a, lines, t_b, _ = world(beta=2.0, only=3, seed=2)
    K, D, design = pt.prepare(a, t_a, lines, t_b, 0)
    res = pt.evaluate(K, D, design, **FAST)
    assert res["verdict"] == "one_line"
    assert res["leave_one_out"]["line"] == "L03"


def test_3_an_unrelated_driver_passes_at_about_the_nominal_rate():
    assert rate(lambda s: world(T=30, seed=1000 + s)) <= 0.09


def test_4_a_shared_monthly_shock_does_not_inflate_the_rate():
    assert rate(lambda s: world(T=30, seed=2000 + s, shock=2.0)) <= 0.09


def test_5_a_uniform_response_cancels_in_the_gaps_and_says_so():
    a, t_a, lines, t_b, _ = world(uniform=1.0, seed=5)
    K, D, design = pt.prepare(a, t_a, lines, t_b, 0)
    res = pt.evaluate(K, D, design, **FAST)
    assert res["verdict"] != "linked"
    assert "cancels" in res["limit"]


def test_6_months_needed_is_where_about_half_the_runs_pass():
    beta, n0 = 0.15, 24
    needed = []
    for s in range(30):
        a, t_a, lines, t_b, _ = world(T=n0, beta=beta, seed=3000 + s)
        K, D, design = pt.prepare(a, t_a, lines, t_b, 0, keep=lambda m: m < n0)
        res = pt.evaluate(K, D, design, shuffles=400, bootstraps=0, seed=s, attribute=False)
        if res["verdict"] == "too_short" and res["months_needed"]:
            needed.append(res["months_needed"])
    assert len(needed) >= 10
    n_at = n0 + int(np.median(needed))
    passed = 0
    for s in range(30):
        a, t_a, lines, t_b, _ = world(T=n_at, beta=beta, seed=4000 + s)
        K, D, design = pt.prepare(a, t_a, lines, t_b, 0, keep=lambda m: m < n_at)
        passed += pt.evaluate(K, D, design, shuffles=400, bootstraps=0, seed=s,
                              attribute=False)["verdict"] == "linked"
    assert 0.25 <= passed / 30 <= 0.9, (n_at, passed)


def test_6b_too_few_lines_or_months_is_too_short():
    a, t_a, lines, t_b, _ = world(T=12, lines=2, seed=6)
    res = pt.pooled(a, t_a, lines, t_b, **FAST)
    assert res["verdict"] == "too_short"


def test_7_direction_is_refused_for_one_sign_across_a_sibling_set():
    a, t_a, lines, t_b, _ = world(seed=7)
    signs = {k: -1 for k in lines}
    groups = {k: "Industry" for k in lines}
    with pytest.raises(pt.Refused):
        pt.pooled(a, t_a, lines, t_b, signs=signs, groups=groups, **FAST)


def test_7b_direction_with_differential_signs_reads_the_planted_way():
    a, t_a, lines, t_b, signs = world(beta=0.35, seed=8)
    groups = {k: "Industry" for k in lines}
    K, D, design = pt.prepare(a, t_a, lines, t_b, 0)
    pt.check_direction(signs, groups)
    assert pt.evaluate(K, D, design, signs=signs, **FAST)["verdict"] == "linked"
    flipped = {k: -v for k, v in signs.items()}
    assert pt.evaluate(K, D, design, signs=flipped, **FAST)["verdict"] == "opposite"


def test_8_the_range_holds_zero_when_there_is_no_link():
    """The separation range is corrected for repeated months in the resample; uncorrected, it sat
    above zero beside p = 0.065 on SIBC (2026-11-10)."""
    holds = 0
    for s in range(40):
        a, t_a, lines, t_b, _ = world(T=17, seed=5000 + s)
        K, D, design = pt.prepare(a, t_a, lines, t_b, 0)
        holds += pt.evaluate(K, D, design, shuffles=300, bootstraps=300, seed=s,
                             attribute=False)["effect"]["range"][0] == 0
    assert holds / 40 >= 0.85, holds


def test_8b_the_range_covers_a_planted_effect():
    covered = 0
    for s in range(40):
        a, t_a, lines, t_b, _ = world(T=40, beta=0.35, seed=6000 + s)
        K, D, design = pt.prepare(a, t_a, lines, t_b, 0)
        lo, hi = pt.evaluate(K, D, design, shuffles=300, bootstraps=300, seed=s,
                             attribute=False)["effect"]["range"]
        true_r = 0.35 / np.sqrt(1 + 0.35 ** 2)              # the planted push against unit noise
        covered += lo <= true_r <= hi
    assert covered / 40 >= 0.8, covered
