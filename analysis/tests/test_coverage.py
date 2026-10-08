#!/usr/bin/env python3
"""
Unit tests for analysis/core/coverage.py (SYSTEM_MODEL_SPEC §16 Step 6a).

The four controls the spec names come first: a step change is a move, a line in step with its
group is not, a matched working force files the move under `cause`, and the same force with
its sign flipped leaves it `unexplained`.

Run: python3 -m pytest analysis/tests/test_coverage.py -q
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import coverage as cv  # noqa: E402

PERIODS = [f"2025-{m:02d}" for m in range(1, 9)]
WOBBLE = [0.0, 0.3, -0.2, 0.25, -0.3, 0.2, -0.25]      # typical change ~0.25, bar ~0.75


def line(last_change, base=10.0):
    """Parent grows `base`; the line wobbles around it, then changes by `last_change`."""
    vals, v = {}, base + 2
    for p, w in zip(PERIODS[:-1], WOBBLE):
        v += w
        vals[p] = v
    vals[PERIODS[-1]] = v + last_change
    return vals


def _e(eid, label, role):
    return {"id": eid, "tier": "entity", "label": label, "structural_role": role, "additive": True}


def model(edges=(), forces=()):
    return {
        "nodes": [_e("R", "Root", "root"), _e("P", "Parent", "aggregate"),
                  _e("A", "Line A", "leaf"), _e("B", "Line B", "leaf")],
        "edges": [{"type": "composes_into", "from": "P", "to": "R"},
                  {"type": "composes_into", "from": "A", "to": "P"},
                  {"type": "composes_into", "from": "B", "to": "P"}, *edges],
        "force_instances": list(forces),
    }


def run(m, a_line, checked=None, real=None, output=None, artifact=None):
    flat = {p: 10.0 for p in PERIODS}
    series = {"R": flat, "P": flat, "A": a_line, "B": line(0.0)}
    return cv.compute(m, PERIODS[-1], series, PERIODS, checked or {}, real, output, artifact)


def move(res, label="Line A"):
    return next((x for x in res["moves"] if x["entity"] == label), None)


DATED = {"id": "f", "starts": "2025-01-01", "delay_months": 0, "fades_after_months": 24}
EDGE = {"id": "ed", "type": "drives", "from": "f", "to": "A", "polarity": "+"}


def working(edge_id="ed"):
    return {"f": {"edges": {edge_id: {"verdict": "working"}}}}


# ── the spec's four controls ─────────────────────────────────────────────────────────────

def test_a_step_change_is_a_move():
    r = run(model(), line(+3.0))
    assert move(r)["direction"] == "up" and move(r)["filed_under"] == "unexplained"


def test_a_line_in_step_with_its_group_is_not_a_move():
    r = run(model(), line(+0.2))
    assert move(r) is None and r["summary"]["steady"] >= 1


def test_a_matched_working_dated_force_files_the_move_under_cause():
    r = run(model([EDGE], [DATED]), line(+3.0), checked=working())
    assert move(r)["filed_under"] == "cause" and move(r)["also_holds"]["cause"] == ["f"]


def test_the_same_force_with_its_sign_flipped_leaves_it_unexplained():
    flipped = {**EDGE, "type": "suppresses", "polarity": "-"}
    r = run(model([flipped], [DATED]), line(+3.0), checked=working())
    assert move(r)["filed_under"] == "unexplained"


# ── the rest of the rule ─────────────────────────────────────────────────────────────────

def test_a_standing_force_never_explains_a_move():
    standing = {"id": "f", "standing": True}
    r = run(model([EDGE], [standing]), line(+3.0), checked=working())
    assert move(r)["filed_under"] == "unexplained"


def test_a_force_that_is_not_working_explains_nothing():
    r = run(model([EDGE], [DATED]), line(+3.0), checked={"f": {"edges": {"ed": {"verdict": "unclear"}}}})
    assert move(r)["filed_under"] == "unexplained"


def test_prices_explain_when_the_deflator_covers_half_the_nominal_change():
    a = line(+3.0)
    p, q = PERIODS[-1], PERIODS[-2]
    real = {"A": {q: {"deflator_yoy": 4.0}, p: {"deflator_yoy": 6.0}}}     # +2.0 of +3.0
    r = run(model(), a, real=real)
    assert move(r)["filed_under"] == "prices_activity" and move(r)["prices_activity"] == "holds"


def test_prices_do_not_explain_when_too_small_or_the_wrong_way():
    p, q = PERIODS[-1], PERIODS[-2]
    for d in (0.5, -2.0):
        real = {"A": {q: {"deflator_yoy": 4.0}, p: {"deflator_yoy": 4.0 + d}}}
        assert move(run(model(), line(+3.0), real=real))["prices_activity"] == "does_not_hold"


def test_no_reference_match_says_not_decomposable_not_no_effect():
    assert move(run(model(), line(+3.0)))["prices_activity"] == "not_decomposable"


def test_artifact_is_filed_first_and_the_others_still_listed():
    r = run(model([EDGE], [DATED]), line(+3.0), checked=working(), artifact=lambda n: n["id"] == "A")
    m = move(r)
    assert m["filed_under"] == "artifact" and set(m["also_holds"]) == {"artifact", "cause"}


def test_a_relationship_explains_when_its_source_moved_the_pushing_way():
    rel = {"id": "rel", "type": "drives", "from": "B", "to": "A", "polarity": "+"}
    flat = {p: 10.0 for p in PERIODS}
    series = {"R": flat, "P": flat, "A": line(+3.0), "B": line(+3.0)}
    r = cv.compute(model([rel]), PERIODS[-1], series, PERIODS, {})
    assert move(r)["filed_under"] == "relationship"
    series["B"] = line(-3.0)
    assert move(cv.compute(model([rel]), PERIODS[-1], series, PERIODS, {}))["filed_under"] == "unexplained"


def test_a_group_is_counted_so_a_force_on_it_can_explain_its_move_against_its_parent():
    grp_edge = {"id": "eg", "type": "drives", "from": "f", "to": "P", "polarity": "+"}
    flat = {p: 10.0 for p in PERIODS}
    series = {"R": flat, "P": line(+3.0), "A": line(+3.0), "B": line(+3.0)}
    r = cv.compute(model([grp_edge], [DATED]), PERIODS[-1], series, PERIODS, working("eg"))
    assert move(r, "Parent")["filed_under"] == "cause"


def test_missing_readings_are_listed_not_dropped():
    m = model()
    flat = {p: 10.0 for p in PERIODS}
    r = cv.compute(m, PERIODS[-1], {"R": flat, "P": flat, "A": line(3.0)}, PERIODS, {})
    assert {x["entity"] for x in r["no_reading"]} == {"Line B"}
    assert r["summary"]["no_reading"] == 1


def test_s4_refuses_a_state_without_coverage(tmp_path, monkeypatch):
    from core import run_inference as ri
    monkeypatch.setattr(ri, "latest_state", lambda cfg: {"_meta": {"period": "x"},
                                                         "system_observations": {}})
    with pytest.raises(RuntimeError, match="explanation_coverage"):
        ri.detect_unexplained("t", {})


def test_s4_reads_only_the_unexplained_moves():
    from core import run_inference as ri
    st = {"_meta": {"period": "x"}, "system_observations": {"authored_vs_observed_mismatches": ["f"]},
          "explanation_coverage": {"moves": [
              {"entity": "A", "urn": "u:A", "direction": "up", "filed_under": "unexplained",
               "gap_change_pp": 3.0, "threshold_pp": 1.0, "baseline_of": "P", "prices_activity": "x"},
              {"entity": "B", "urn": "u:B", "direction": "down", "filed_under": "cause",
               "gap_change_pp": -3.0, "threshold_pp": 1.0, "baseline_of": "P", "prices_activity": "x"}]}}
    ri_latest = ri.latest_state
    try:
        ri.latest_state = lambda cfg: st
        un, mm = ri.detect_unexplained("t", {})
    finally:
        ri.latest_state = ri_latest
    assert [u["entity"] for u in un] == ["A"] and un[0]["direction"] == "rising" and mm == ["f"]


def test_a_change_across_a_hole_in_the_history_is_not_a_move():
    """SIBC skipped Sep–Dec 2025: the Jan 2026 change spans five months and once made 32 lines
    look like they moved at once. Only a change from the month before can be a move."""
    holed = [p for p in PERIODS if p != "2025-07"]           # 2025-06 -> 2025-08 is a hole
    flat = {p: 10.0 for p in holed}
    a = {p: v for p, v in line(+3.0).items() if p in holed}
    r = cv.compute(model(), PERIODS[-1], {"R": flat, "P": flat, "A": a, "B": line(0.0)}, holed, {})
    assert move(r) is None
    assert any(x["entity"] == "Line A" and "month before" in x["reason"] for x in r["no_reading"])


# ── structural: not a separate event (Part A) ────────────────────────────────────────────

def test_echo_when_the_group_moved_the_other_way():
    """Non-food credit 'falls' against bank credit when food credit jumps: the group moved."""
    flat = {p: 10.0 for p in PERIODS}
    parent = {**flat, PERIODS[-1]: 13.0}                  # the group jumps +3
    a = {p: 12.0 + w for p, w in zip(PERIODS, [0, .3, .1, .35, .05, .25, 0, 0])}
    a[PERIODS[-1]] = a[PERIODS[-2]]                       # the line itself did not change
    r = cv.compute(model(), PERIODS[-1], {"R": flat, "P": parent, "A": a, "B": line(0.0)},
                   PERIODS, {})
    m = move(r)
    assert m["direction"] == "down" and m["filed_under"] == "structural"
    assert m["also_holds"]["structural"] == ["echo of Parent"]


def test_no_echo_when_the_line_itself_moved():
    r = run(model(), line(+3.0))                           # the parent is flat
    assert move(r)["filed_under"] == "unexplained"


def lens_model():
    m = model()
    m["nodes"] += [{"id": "L", "tier": "entity", "label": "Lens", "structural_role": "root",
                    "additive": False},
                   {"id": "T", "tier": "entity", "label": "Lens twin", "structural_role": "leaf",
                    "additive": False}]
    m["edges"] += [{"type": "composes_into", "from": "T", "to": "L"},
                   {"type": "reclassifies", "from": "T", "to": "A"}]
    return m


def test_twin_files_the_lens_side_and_the_main_line_keeps_the_event():
    flat = {p: 10.0 for p in PERIODS}
    series = {"R": flat, "P": flat, "A": line(+3.0), "B": line(0.0), "T": line(+3.0)}
    r = cv.compute(lens_model(), PERIODS[-1], series, PERIODS, {})
    assert move(r, "Lens twin")["also_holds"]["structural"] == ["twin of Line A"]
    assert move(r, "Line A")["filed_under"] == "unexplained"


def test_no_twin_when_the_main_line_moved_the_other_way():
    flat = {p: 10.0 for p in PERIODS}
    series = {"R": flat, "P": flat, "A": line(-3.0), "B": line(0.0), "T": line(+3.0)}
    r = cv.compute(lens_model(), PERIODS[-1], series, PERIODS, {})
    assert move(r, "Lens twin")["filed_under"] == "unexplained"


def test_carried_by_a_member_that_is_most_of_the_group():
    """The member leads (it beats its group too), and its weighted change is most of the
    group's: the event is the member's, so the group is filed as carried by it."""
    flat = {p: 10.0 for p in PERIODS}
    series = {"R": flat, "P": line(+3.0), "A": line(+5.0), "B": line(0.0)}
    r = cv.compute(model(), PERIODS[-1], series, PERIODS, {}, weights={"P": 100.0, "A": 60.0, "B": 40.0})
    assert move(r, "Parent")["also_holds"]["structural"] == ["carried by Line A"]
    assert move(r, "Line A")["filed_under"] == "unexplained"         # the event stays listed once
    r = cv.compute(model(), PERIODS[-1], series, PERIODS, {}, weights={"P": 100.0, "A": 10.0, "B": 90.0})
    assert move(r, "Parent")["filed_under"] == "unexplained"         # a sliver cannot carry it


def test_not_carried_when_the_member_merely_moved_with_its_group():
    """If the member has no move of its own, filing the group as carried would make the event
    vanish from the list. The group keeps it."""
    flat = {p: 10.0 for p in PERIODS}
    series = {"R": flat, "P": line(+3.0), "A": line(+3.0), "B": line(0.0)}
    r = cv.compute(model(), PERIODS[-1], series, PERIODS, {}, weights={"P": 100.0, "A": 90.0, "B": 10.0})
    assert move(r, "Parent")["filed_under"] == "unexplained"
