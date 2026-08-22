#!/usr/bin/env python3
"""
Unit tests for analysis/cross/compose_ecosystem.py (COMPOSITION_SPEC Part II).

Covers the pure state functions of the ecosystem meta-model — the semantic layer
the composition validator (reference integrity only) cannot catch:
  - §14 construct direction: role signs, weights, missing members, sign-only output
  - §15 eco-edge state: active / reversed / dormant vs polarity
  - §16 loop firing: the per-pipeline S3 step-5 rule applied to qualified refs
  - §17 constraint evaluation: corridor / pct / abs, unobservable operands

Run: python3 -m pytest analysis/tests/test_ecosystem_compose.py -q
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cross.compose_ecosystem import (      # noqa: E402
    X_STATE_AS_EDGE, agreement_word, construct_direction, eco_edge_state, eval_constraint, loop_state,
)


# ── §14 construct direction ────────────────────────────────────────────────────

def _construct(members):
    return {"id": "c", "members": members}


def test_construct_all_measures_up():
    c = _construct([{"urn": "a", "role": "measures"}, {"urn": "b", "role": "measures"}])
    d, basis = construct_direction(c, {"a": 1, "b": 1})
    assert d == 1
    assert basis["observed"] == 2 and basis["total"] == 2


def test_coherence_separates_unanimity_from_a_majority():
    """The whole point: `direction` alone cannot tell these two apart, and until
    2026-08-19 the published card called both of them "expanding (5/5 measurements
    observed)". Modelled on the live pair — unsecured_retail_appetite (5 up) versus
    card_consumption_activity (3 up, 1 down, 1 flat)."""
    five_up = {"members": [{"urn": u, "role": "measures"} for u in "abcde"]}
    d, basis = construct_direction(five_up, {u: 1 for u in "abcde"})
    assert (d, basis["coherence"], basis["agree"]) == (1, 1.0, "aligned")

    d, basis = construct_direction(five_up, {"a": 1, "b": -1, "c": 0, "d": 1, "e": 1})
    assert d == 1, "direction is unchanged — coherence qualifies it, never suppresses it"
    assert basis["coherence"] == 0.5
    assert basis["agree"] == "contested"
    assert basis["observed"] == 5, "coverage is still full — agreement is a different question"


def test_coherence_is_none_when_nothing_moved():
    """Undefined, not perfect. A construct whose members are all flat has no agreement
    to report, and claiming 1.0 would read as unanimity."""
    c = {"members": [{"urn": "a", "role": "measures"}, {"urn": "b", "role": "measures"}]}
    d, basis = construct_direction(c, {"a": 0, "b": 0})
    assert (d, basis["coherence"], basis["agree"]) == (0, None, "still")


def test_a_true_split_is_named_split_not_contested():
    c = {"members": [{"urn": "a", "role": "measures"}, {"urn": "b", "role": "measures"}]}
    d, basis = construct_direction(c, {"a": 1, "b": -1})
    assert basis["coherence"] == 0.0 and basis["agree"] == "split"


def test_agreement_word_boundaries_match_the_layer_1_router():
    assert agreement_word(1.0) == "aligned"
    assert agreement_word(0.90) == "aligned"
    assert agreement_word(0.8999) == "contested"
    assert agreement_word(0.50) == "contested"
    assert agreement_word(0.4999) == "split"
    assert agreement_word(None) == "still"


def test_contra_indicator_counts_toward_agreement_after_its_sign_flips():
    """A contra-indicator moving DOWN agrees with a construct moving up — coherence is
    measured on contributions, after role_sign, not on raw member directions."""
    c = {"members": [{"urn": "a", "role": "measures"},
                     {"urn": "b", "role": "contra_indicates"}]}
    d, basis = construct_direction(c, {"a": 1, "b": -1})
    assert (d, basis["coherence"], basis["agree"]) == (1, 1.0, "aligned")


def test_construct_contra_indicates_flips_sign():
    c = _construct([{"urn": "a", "role": "measures"}, {"urn": "b", "role": "contra_indicates"}])
    # a up (+1), b up but contra (−1) → net 0
    d, _ = construct_direction(c, {"a": 1, "b": 1})
    assert d == 0


def test_construct_weight_dominates():
    c = _construct([{"urn": "a", "role": "measures", "weight": 3},
                    {"urn": "b", "role": "measures"}])
    d, _ = construct_direction(c, {"a": -1, "b": 1})
    assert d == -1


def test_construct_missing_member_reduces_observed_not_direction():
    c = _construct([{"urn": "a", "role": "measures"}, {"urn": "zz", "role": "measures"}])
    d, basis = construct_direction(c, {"a": 1})
    assert d == 1
    assert basis["observed"] == 1 and basis["total"] == 2
    assert [m["direction"] for m in basis["members"]] == [1, None]


def test_construct_output_is_sign_only():
    c = _construct([{"urn": x, "role": "measures"} for x in "abcde"])
    d, _ = construct_direction(c, {x: 1 for x in "abcde"})
    assert d == 1  # never a magnitude


# ── §15 eco-edge state ─────────────────────────────────────────────────────────

def test_eco_edge_active_reversed_dormant():
    e = {"from": "src", "to": "dst", "polarity": "+"}
    assert eco_edge_state(e, {"src": 1}) == "active"
    assert eco_edge_state(e, {"src": -1}) == "reversed"
    assert eco_edge_state(e, {"src": 0}) == "dormant"
    assert eco_edge_state(e, {}) == "dormant"


def test_eco_edge_negative_polarity():
    e = {"from": "src", "to": "dst", "polarity": "-"}
    assert eco_edge_state(e, {"src": -1}) == "active"    # firing = the constraint binds
    assert eco_edge_state(e, {"src": 1}) == "reversed"


# ── §16 loop firing ────────────────────────────────────────────────────────────

def _resolver(mapping):
    return lambda ref: mapping.get(ref)


def test_loop_all_active_reinforcing():
    lp = {"id": "l", "type": "reinforcing", "member_edges": ["eco:a", "x:b", "sibc:c"]}
    st = loop_state(lp, _resolver({"eco:a": "active", "x:b": "active", "sibc:c": "active"}))
    assert st["state"] == "active_reinforcing"
    assert st["live_edges"] == 3 and st["total_edges"] == 3


def test_loop_partial_when_any_segment_live():
    lp = {"id": "l", "type": "balancing", "member_edges": ["eco:a", "x:b"]}
    st = loop_state(lp, _resolver({"eco:a": "reversed", "x:b": "dormant"}))
    assert st["state"] == "partial"


def test_loop_dormant_when_nothing_live():
    lp = {"id": "l", "type": "reinforcing", "member_edges": ["eco:a", "x:b"]}
    st = loop_state(lp, _resolver({"eco:a": "dormant", "x:b": "dormant"}))
    assert st["state"] == "dormant"


def test_x_edge_state_mapping_for_loops():
    # divergent cross-edge = the segment is running AGAINST its expected direction
    assert X_STATE_AS_EDGE == {"aligned": "active", "divergent": "reversed", "dormant": "dormant"}


# ── §17 constraint evaluation ──────────────────────────────────────────────────

def _cx(**kw):
    base = {"id": "cx", "operands": [{"pipeline": "sibc", "signal_id": "a"},
                                     {"pipeline": "atm_pos", "signal_id": "b"}]}
    base.update(kw)
    return base


def test_constraint_ratio_corridor_holds_and_violates():
    cx = _cx(op="ratio", tolerance={"type": "corridor", "value": [10, 50]})
    ok = eval_constraint(cx, {("sibc", "a"): 300.0, ("atm_pos", "b"): 10.0})
    assert ok["state"] == "holds" and ok["value"] == 30.0
    bad = eval_constraint(cx, {("sibc", "a"): 1000.0, ("atm_pos", "b"): 10.0})
    assert bad["state"] == "violated" and bad["value"] == 100.0


def test_constraint_operand_scale():
    cx = _cx(op="ratio", tolerance={"type": "corridor", "value": [10, 50]})
    cx["operands"][0]["scale"] = 0.1
    r = eval_constraint(cx, {("sibc", "a"): 3000.0, ("atm_pos", "b"): 10.0})
    assert r["value"] == 30.0 and r["state"] == "holds"


def test_constraint_unobservable_when_operand_missing():
    cx = _cx(tolerance={"type": "corridor", "value": [0, 1]})
    r = eval_constraint(cx, {("sibc", "a"): 1.0})   # atm_pos operand absent
    assert r["state"] == "unobservable" and r["value"] is None


def test_constraint_pct_tolerance():
    cx = _cx(op="diff", tolerance={"type": "pct", "value": 5})
    assert eval_constraint(cx, {("sibc", "a"): 104.0, ("atm_pos", "b"): 100.0})["state"] == "holds"
    assert eval_constraint(cx, {("sibc", "a"): 110.0, ("atm_pos", "b"): 100.0})["state"] == "violated"
