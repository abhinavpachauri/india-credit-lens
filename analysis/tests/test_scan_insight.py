#!/usr/bin/env python3
"""
Unit tests for deterministic_scan_insight (generate_analysis_report).

Locks the spec-driven semantics that fixed the unreadable NBFC card:
  - kind comes from the SPEC, never from the values — an all-positive growth
    scan must never be rendered as a share distribution ("top three hold X%
    of the total" over summed growth rates was the bug)
  - share cards name the denominator (share_of) and say "size shares"
  - N=2 renders a comparison, not a leaderboard (no duplicate entity, no
    "top three" over two break-outs)

Run: python3 -m pytest analysis/tests/test_scan_insight.py -q
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipelines.sibc.generate_analysis_report import deterministic_scan_insight  # noqa: E402


def _all(parts):
    return " ".join([parts[0], parts[1], " ".join(parts[2]), parts[3]])


def test_share_n2_is_comparison_not_leaderboard():
    dist = [("Housing Finance Companies (HFCs)", 17.7, "x"),
            ("Public Financial Institutions (PFIs)", 17.0, "y")]
    title, body, chain, imp = deterministic_scan_insight(dist, "pct", kind="share",
                                                         share_of="NBFC credit")
    text = _all((title, body, chain, imp))
    assert "of NBFC credit" in text
    assert "size shares, not growth rates" in body
    assert "Top three" not in text and "top three" not in text
    # the lowest entity appears as the comparison, never listed twice as
    # runner-up AND lowest
    assert body.count("Public Financial Institutions") == 1


def test_share_n3_keeps_leaderboard_with_labels():
    dist = [("A", 50.0, ""), ("B", 30.0, ""), ("C", 10.0, "")]
    title, body, chain, imp = deterministic_scan_insight(dist, "pct", kind="share",
                                                         share_of="trade credit")
    assert "biggest slice of trade credit" in title
    assert "Top three hold 90.0% of trade credit" in body
    assert "concentrated" in " ".join(chain)


def test_yoy_all_positive_never_summed_as_total():
    """The old any-negative heuristic summed growth rates into 'X% of the total'."""
    dist = [("PFIs", 71.8, ""), ("HFCs", 19.7, "")]
    title, body, chain, imp = deterministic_scan_insight(dist, "pct", kind="yoy")
    text = _all((title, body, chain, imp))
    assert "of the total" not in text
    assert "YoY" in title
    # spread rendered as "N.N percentage points" — the extractor-safe form the
    # 2g number parser handles (a glued "52.1pp" mis-extracts as the integer part)
    assert "52.1 percentage points" in body or "52.0 percentage points" in body


def test_yoy_n2_direction_split_wording():
    dist = [("A", 5.0, ""), ("B", -2.0, "")]
    _, _, chain, _ = deterministic_scan_insight(dist, "pct", kind="yoy")
    assert any("direction split" in c for c in chain)


def test_yoy_n4_counts_growing_categories():
    dist = [("A", 20.0, ""), ("B", 10.0, ""), ("C", 5.0, ""), ("D", -1.0, "")]
    _, body, chain, _ = deterministic_scan_insight(dist, "pct", kind="yoy")
    assert "3 of 4 categories growing" in body
    assert "broad-based" in " ".join(chain)
