#!/usr/bin/env python3
"""
Unit tests for analysis/core/force_check.py (SYSTEM_MODEL_SPEC §16 Step 3, v3.1).

The check exists because its predecessor could not fail: every force read `active` every
period. So most of these tests are the failing cases — a check that cannot return
`contradicted` on a contradicting line is the defect this module replaced.

Run: python3 -m pytest analysis/tests/test_force_check.py -q
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import force_check as fc  # noqa: E402

PERIODS = ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06"]
MONTH = {p: p + "-28" for p in PERIODS}     # period key -> its data month (identity here)


def _e(eid, label, additive=True, role="leaf", dec="primary"):
    return {"id": eid, "tier": "entity", "label": label, "additive": additive,
            "structural_role": role, "decomposition": dec}


def make_model(force, edge_type="drives", target="e_A"):
    """root R -> P (parent) -> A, B (additive children); lens L (non-additive) -> M."""
    return {
        "nodes": [_e("e_R", "Root", role="root"), _e("e_P", "Parent", role="aggregate"),
                  _e("e_A", "Line A"), _e("e_B", "Line B"),
                  _e("e_L", "Lens", additive=False, role="root", dec="lens"),
                  _e("e_M", "Lens member", additive=False, dec="lens")],
        "edges": [
            {"type": "composes_into", "from": "e_P", "to": "e_R"},
            {"type": "composes_into", "from": "e_A", "to": "e_P"},
            {"type": "composes_into", "from": "e_B", "to": "e_P"},
            {"type": "composes_into", "from": "e_M", "to": "e_L"},
            {"id": "ed", "type": edge_type, "from": force["id"], "to": target},
        ],
        "force_instances": [force],
    }


STANDING = {"id": "f", "status": "active", "standing": True, "timing_rule": "trend"}
# Parent grows 10% throughout; the line's wobble around it is ~1pp.
PARENT = {p: 10.0 for p in PERIODS}


def run(force, line, edge_type="drives", target="e_A", period="2025-06", extra=None):
    series = {"e_P": PARENT, target: line, **(extra or {})}
    model = make_model(force, edge_type, target)
    return fc.check("t", model, period, series, PERIODS, data_month=MONTH.get)["f"]


# ── the two controls the spec names ──────────────────────────────────────────────────────

def test_known_bad_force_on_a_falling_line_is_contradicted():
    """A force that 'drives' a line which falls behind its parent must fail."""
    falling = {"2025-01": 10, "2025-02": 9, "2025-03": 10, "2025-04": 9, "2025-05": 5, "2025-06": 2}
    r = run(STANDING, falling)
    assert r["verdict"] == "contradicted"
    assert r["in_doubt"] is True            # contradicted at 2025-05 and 2025-06


def test_known_good_suppressing_force_on_a_lagging_line_is_working():
    """The Nov 2023 risk-weight shape: the line still grows, but far slower than its parent.
    v3.0 called this `reversed` because it compared against zero."""
    lagging = {"2025-01": 9, "2025-02": 8, "2025-03": 9, "2025-04": 8, "2025-05": 4, "2025-06": 3}
    r = run(STANDING, lagging, edge_type="suppresses")
    assert r["verdict"] == "working"
    assert r["edges"]["ed"]["gap_pp"] == -7.0


def test_flipping_the_force_sign_flips_the_verdict():
    rising = {"2025-01": 10, "2025-02": 11, "2025-03": 10, "2025-04": 11, "2025-05": 15, "2025-06": 18}
    assert run(STANDING, rising, "drives")["verdict"] == "working"
    assert run(STANDING, rising, "suppresses")["verdict"] == "contradicted"


def test_growth_in_step_with_the_parent_is_unclear_not_working():
    """Growing is not evidence. The v3.0 check counted any growth as the force firing."""
    in_step = {"2025-01": 10, "2025-02": 11, "2025-03": 9, "2025-04": 11, "2025-05": 9, "2025-06": 10.5}
    assert run(STANDING, in_step)["verdict"] == "unclear"


# ── window ───────────────────────────────────────────────────────────────────────────────

def dated(starts, delay, fade):
    return {"id": "f", "status": "active", "starts": starts, "delay_months": delay,
            "fades_after_months": fade, "timing_rule": "capital_cost"}


def test_before_its_window_the_force_is_not_yet_due():
    line = {p: 20.0 for p in PERIODS}
    assert run(dated("2025-05-01", 3, 24), line)["verdict"] == "not_yet_due"


def test_after_its_window_the_force_has_faded():
    line = {p: 20.0 for p in PERIODS}
    assert run(dated("2024-01-01", 0, 12), line)["verdict"] == "faded"


def test_window_end_is_exclusive():
    # starts Jan 2025, no delay, visible 5 months -> Jan..May in window, June faded
    line = {"2025-01": 20, "2025-02": 21, "2025-03": 20, "2025-04": 21, "2025-05": 20, "2025-06": 21}
    f = dated("2025-01-01", 0, 5)
    assert run(f, line, period="2025-05")["verdict"] == "working"
    assert run(f, line, period="2025-06")["verdict"] == "faded"


# ── baseline by place in the skeleton ────────────────────────────────────────────────────

def test_lens_member_with_a_dated_force_is_compared_with_itself_before_the_start():
    member = {"2025-01": 5, "2025-02": 6, "2025-03": 5, "2025-04": 12, "2025-05": 13, "2025-06": 14}
    r = run(dated("2025-04-01", 0, 12), member, target="e_M")
    e = r["edges"]["ed"]
    assert e["baseline_kind"] == "own_before" and e["baseline"] == 5   # the March reading
    assert r["verdict"] == "working"


def test_lens_member_with_a_standing_force_goes_to_its_tree_root():
    member = {p: 12.0 for p in PERIODS}
    r = run(STANDING, member, target="e_M")
    e = r["edges"]["ed"]
    assert e["baseline_kind"] == "root" and e["baseline_of"] == "Lens"
    assert e["verdict"] == "unassessable"       # the lens root has no reading, and says so


# ── absences stay loud ───────────────────────────────────────────────────────────────────

def test_short_history_is_unassessable_with_a_reason():
    line = {"2025-05": 20, "2025-06": 22}
    e = run(STANDING, line)["edges"]["ed"]
    assert e["verdict"] == "unassessable" and "wobble" in e["reason"]


def test_a_force_with_no_driver_edge_says_so():
    model = make_model(STANDING)
    model["edges"] = [e for e in model["edges"] if e.get("id") != "ed"]
    r = fc.check("t", model, "2025-06", {}, PERIODS, data_month=MONTH.get)["f"]
    assert r["verdict"] == "unassessable" and "which way it pushes" in r["reason"]


def test_roll_up():
    assert fc.roll_up(["working", "working", "contradicted"]) == "working"
    assert fc.roll_up(["working", "contradicted"]) == "unclear"
    assert fc.roll_up(["faded", "faded"]) == "faded"
    assert fc.roll_up(["faded", "unassessable"]) == "unassessable"
    assert fc.roll_up([]) == "unassessable"


def test_monthly_changes_skip_a_hole():
    gaps = [("2025-01", 1.0), ("2025-02", 2.0), ("2025-06", 9.0), ("2025-07", 9.5)]
    assert fc.monthly_changes(gaps, lambda p: p) == [("2025-02", 1.0), ("2025-07", 0.5)]


# ── group totals (csv_sum_yoy) — 2026-10-10 ──────────────────────────────────────────────

def test_a_missing_part_makes_a_group_total_unknown_not_smaller():
    """`or 0` once let one absent metric shrink the sum, and a partial total's growth reads as
    real. A missing part now returns unknown with a reason."""
    import pandas as pd
    from signals.compute import atm_pos
    rows = []
    for d in ("2025-08-31", "2026-08-31"):
        for m, v in (("a", 100.0), ("b", 50.0)):
            rows.append({"report_date": d, "metric": m, "record_type": "total", "value": v * (1.1 if d[:4] == "2026" else 1)})
    df = pd.DataFrame(rows)
    ok = atm_pos.csv_sum_yoy({"metrics": ["a", "b"]}, "2026-08-31", df)[0]
    assert round(ok["value"], 4) == 10.0 and '"year_ago_sum": 150.0' in ok["operands"]
    holed = df[~((df["metric"] == "b") & (df["report_date"] == "2025-08-31"))]
    bad = atm_pos.csv_sum_yoy({"metrics": ["a", "b"]}, "2026-08-31", holed)[0]
    assert bad["value"] is None and bad["status"] == "unknown" and "b" in bad["reason"]


def test_a_sum_signal_belongs_to_the_node_whose_leaves_it_adds(monkeypatch, tmp_path):
    """No hand-written mapping: the node is derived from the skeleton by its leaf set."""
    import sqlite3
    db = tmp_path / "s.db"
    con = sqlite3.connect(db)
    con.execute("create table signals (pipeline, period, metric_id, entity_type, entity_id, value)")
    con.execute("insert into signals values ('t','2026-08-31','grp-yoy','aggregate','total',4.2)")
    con.commit()
    model = {"nodes": [{"id": "G", "tier": "entity", "code": "grp", "label": "G"},
                       {"id": "A", "tier": "entity", "code": "a", "label": "A"},
                       {"id": "B", "tier": "entity", "code": "b", "label": "B"}],
             "edges": [{"type": "composes_into", "from": "A", "to": "G"},
                       {"type": "composes_into", "from": "B", "to": "G"}]}
    reg = {"signals": {"grp-yoy": {"pipeline": "t", "compute": {"method": "csv_sum_yoy", "metrics": ["b", "a"]}}}}
    monkeypatch.setattr(fc.gs, "load_json", lambda p: reg)
    assert fc.growth_series("t", model, con) == {"G": {"2026-08-31": 4.2}}
