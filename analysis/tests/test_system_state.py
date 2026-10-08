#!/usr/bin/env python3
"""
Unit tests for analysis/core/generate_system_state.py (stratum S3).

These cover the semantic logic the gate validators cannot catch — they would have
caught the two defects fixed in the 2026-06-13 review:
  - #2: STATUS_DIR silently mapping unknown/`reversed`-class statuses to 0
  - #3: the unreachable `"dominant"` edge-state branch (magnitude pretense)

Run: python3 -m pytest analysis/tests/test_system_state.py -q
"""
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import generate_system_state as g3  # noqa: E402


# --------------------------------------------------------------------------- #
# Fixtures: a minimal but spec-shaped model.
#   root R (own signal) -> A, B (composes_into)
#   A -> A1, A2 (leaves)   B -> B1 (leaf)
#   force F (active) --drives(+)--> A
#   loop L over the drives edge
# --------------------------------------------------------------------------- #
def _entity(eid, code, role, sids, statement="S1", dec="primary"):
    return {
        "id": eid, "urn": f"icl:test/{statement}/{code}", "tier": "entity",
        "code": code, "statement": statement, "structural_role": role,
        "decomposition": dec, "signal_ids": sids,
    }


def make_model():
    return {
        "nodes": [
            _entity("e_R", "R", "root", ["sig_R"]),
            _entity("e_A", "A", "aggregate", []),
            _entity("e_B", "B", "aggregate", []),
            _entity("e_A1", "A1", "leaf", ["sig_A1"]),
            _entity("e_A2", "A2", "leaf", ["sig_A2"]),
            _entity("e_B1", "B1", "leaf", ["sig_B1"]),
        ],
        "edges": [
            {"id": "x_A1_A", "type": "composes_into", "from": "e_A1", "to": "e_A", "polarity": "structural"},
            {"id": "x_A2_A", "type": "composes_into", "from": "e_A2", "to": "e_A", "polarity": "structural"},
            {"id": "x_B1_B", "type": "composes_into", "from": "e_B1", "to": "e_B", "polarity": "structural"},
            {"id": "x_A_R", "type": "composes_into", "from": "e_A", "to": "e_R", "polarity": "structural"},
            {"id": "x_B_R", "type": "composes_into", "from": "e_B", "to": "e_R", "polarity": "structural"},
            {"id": "ed_F_A", "type": "drives", "from": "f_F", "to": "e_A", "polarity": "+"},
        ],
        "force_instances": [
            {"id": "f_F", "instance_of": "ch_F", "signal_evidence": ["sig_A1"], "status": "active"},
        ],
        "loops": [
            {"id": "L", "type": "reinforcing", "participating_edges": ["ed_F_A"]},
        ],
    }


# --------------------------------------------------------------------------- #
# #3 regression — the edge-state branch must never emit "dominant".
# --------------------------------------------------------------------------- #
def test_no_dominant_edge_state_ever():
    """Direction is sign-only, so 'dominant' (abs(d) >= 1 branch) is unreachable."""
    model = make_model()
    for sig_A1 in (1, -1, 0):
        st = g3.compute(model, {"sig_R": 1, "sig_A1": sig_A1, "sig_A2": -1, "sig_B1": 1})
        states = {v["state"] for v in st["edge_states"].values()}
        assert "dominant" not in states


def test_edge_active_reversed_dormant():
    model = make_model()
    # force F is active (evidence sig_A1 != 0) -> drives(+) edge fires "active"
    st = g3.compute(model, {"sig_R": 1, "sig_A1": 1, "sig_A2": 1, "sig_B1": 1})
    assert st["edge_states"]["ed_F_A"]["state"] == "active"
    # force latent (evidence sig_A1 == 0) -> edge dormant
    st = g3.compute(model, {"sig_R": 1, "sig_A1": 0, "sig_A2": 1, "sig_B1": 1})
    assert st["edge_states"]["ed_F_A"]["state"] == "dormant"


# --------------------------------------------------------------------------- #
# #2 regression — STATUS_DIR contract + loud warning on unmapped statuses.
# --------------------------------------------------------------------------- #
def test_status_dir_contract():
    assert g3.STATUS_DIR == {
        "strengthening": 1, "active": 1, "weakening": -1, "declining": -1, "unknown": 0,
    }


def _tmp_db(tmp_path, rows):
    db = tmp_path / "signals.db"
    con = sqlite3.connect(db)
    con.execute("create table signals (pipeline text, period text, metric_id text, status text)")
    con.executemany("insert into signals values (?,?,?,?)",
                    [("sibc", "2026-05-29", m, s) for m, s in rows])
    con.commit()
    con.close()
    return db


def test_load_signal_dirs_warns_on_unmapped(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(g3, "DB", _tmp_db(tmp_path, [("a", "active"), ("b", "reversed")]))
    dirs, _ = g3.load_signal_dirs("sibc", "2026-05-29")
    assert dirs == {"a": 1, "b": 0}          # unmapped -> 0 ...
    err = capsys.readouterr().err
    assert "reversed" in err and "unmapped" in err  # ... but never silently


def test_load_signal_dirs_unknown_is_silent_zero(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(g3, "DB", _tmp_db(tmp_path, [("a", "unknown"), ("b", "weakening")]))
    dirs, _ = g3.load_signal_dirs("sibc", "2026-05-29")
    assert dirs == {"a": 0, "b": -1}
    assert capsys.readouterr().err == ""      # unknown is a defined zero, no warning


# --------------------------------------------------------------------------- #
# Propagation semantics.
# --------------------------------------------------------------------------- #
def test_aggregate_own_signal_overrides_children():
    """e_R has its own signal; it must win over rolled-up child directions."""
    model = make_model()
    st = g3.compute(model, {"sig_R": -1, "sig_A1": 1, "sig_A2": 1, "sig_B1": 1})
    assert st["entity_states"]["icl:test/S1/R"]["direction"] == -1


def test_aggregate_without_signal_rolls_up_share_weighted():
    """e_A has no own signal; the larger-weight child sets its decomposition sign."""
    model = make_model()
    # A1 up, A2 down; A1 weighted heavier -> A resolves positive
    st = g3.compute(model, {"sig_A1": 1, "sig_A2": -1},
                    weights={"e_A1": 10.0, "e_A2": 1.0})
    assert st["entity_states"]["icl:test/S1/A"]["direction"] == 1


def test_force_instance_state_and_mismatch():
    model = make_model()
    # evidence sig_A1 fires -> active, authored 'active' -> no mismatch
    st = g3.compute(model, {"sig_A1": 1})
    assert st["force_states"]["f_F"]["state"] == "active"
    assert st["force_states"]["f_F"]["mismatch"] is False
    # evidence does not fire -> latent, but authored 'active' -> mismatch flagged
    st = g3.compute(model, {"sig_A1": 0})
    assert st["force_states"]["f_F"]["state"] == "latent"
    assert st["force_states"]["f_F"]["mismatch"] is True


def test_loop_active_vs_partial():
    model = make_model()
    st = g3.compute(model, {"sig_A1": 1})       # drives edge active -> loop active_reinforcing
    assert st["loop_states"]["L"]["state"] == "active_reinforcing"
    st = g3.compute(model, {"sig_A1": 0})       # edge dormant -> loop dormant
    assert st["loop_states"]["L"]["state"] == "dormant"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))


# --------------------------------------------------------------------------- #
# v3.1 switch (SYSTEM_MODEL_SPEC §16 Step 3): when the manifest declares it, the force
# check's verdict replaces "any evidence signal moved". These are the cases where the two
# rules disagree, which is the whole reason for the switch.
# --------------------------------------------------------------------------- #
def _checked(verdict, in_doubt=False):
    return {"f_F": {"verdict": verdict, "window": "in_window", "in_doubt": in_doubt,
                    "edges": {"ed_F_A": {"verdict": verdict}}}}


def test_v31_contradicted_force_is_not_active_even_when_its_signal_moves():
    model = make_model()
    st = g3.compute(model, {"sig_A1": 1}, checked=_checked("contradicted", in_doubt=True))
    f = st["force_states"]["f_F"]
    assert f["state"] == "contradicted" and f["rule"] == "v3.1"
    assert f["mismatch"] is True                                   # in_doubt -> S4's input
    assert st["edge_states"]["ed_F_A"]["state"] == "reversed"
    assert "f_F" not in st["system_observations"]["dominant_forces"]
    assert st["loop_states"]["L"]["state"] != "active_reinforcing"


def test_v31_working_force_is_active_even_when_v30_would_call_it_latent():
    model = make_model()
    st = g3.compute(model, {"sig_A1": 0}, checked=_checked("working"))
    assert st["force_states"]["f_F"]["state"] == "active"
    assert st["edge_states"]["ed_F_A"]["state"] == "active"
    assert st["system_observations"]["dominant_forces"] == ["f_F"]


def test_v31_window_and_unassessable_verdicts_make_the_edge_dormant():
    model = make_model()
    for v in ("faded", "not_yet_due", "unclear", "unassessable"):
        st = g3.compute(model, {"sig_A1": 1}, checked=_checked(v))
        assert st["edge_states"]["ed_F_A"]["state"] == "dormant", v
        assert st["force_states"]["f_F"]["state"] == v


def test_without_checked_the_v30_rule_is_unchanged():
    st = g3.compute(make_model(), {"sig_A1": 1})
    assert st["force_states"]["f_F"]["rule"] == "v3.0"
    assert st["force_states"]["f_F"]["state"] == "active"


def test_manifest_force_check_defaults_and_rejects_unknown(monkeypatch):
    from core import manifest
    monkeypatch.setattr(manifest, "load", lambda p: {})
    assert manifest.force_check("x") == "v3.0"
    monkeypatch.setattr(manifest, "load", lambda p: {"force_check": "v9"})
    with pytest.raises(KeyError):
        manifest.force_check("x")
    assert manifest.force_check.__module__ == "core.manifest"


def test_sibc_declares_v31_and_payments_does_not():
    from core import manifest
    assert manifest.force_check("sibc") == "v3.1"
    assert manifest.force_check("atm_pos") == "v3.0"
