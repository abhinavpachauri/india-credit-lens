#!/usr/bin/env python3
"""S4 triage — taking a proposal off the queue without promoting it.

S4 converts at roughly one in forty, so most proposals are meant to die. Until
triage existed the verdict vocabulary was entirely about SOURCING, so "we already
model this" and "this is not a force at all" had nowhere to go and every proposal
stayed on the worklist forever — an unworked proposal and a rejected one looked
identical.

Two properties matter and are pinned here:
  1. triage NEVER promotes — sourcing stays the only route into the model;
  2. a ruled-out proposal is REPORTED, not merely absent, because a queue that
     shrinks silently turns a decision into an omission.

Run: python3 -m pytest analysis/tests/test_s4_triage.py -q
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.run_inference import TRIAGE_VERDICTS, triaged, worklist  # noqa: E402


def _file(tmp_path, proposals):
    import json
    p = tmp_path / "props.json"
    p.write_text(json.dumps({"proposals": proposals}))
    return p


def test_a_triaged_proposal_leaves_the_queue_but_is_still_reported(tmp_path):
    f = _file(tmp_path, [
        {"label": "kept", "required_source": "RBI circular"},
        {"label": "ruled", "triage": {"verdict": "duplicate",
                                      "note": "already force_pli_manufacturing"}},
    ])
    rows, ruled = worklist(f)
    assert [r[4] for r in rows] == ["kept"]
    assert [r[3] for r in ruled] == ["ruled"]
    assert ruled[0][1] == "duplicate"


def test_triage_never_makes_a_proposal_promotable(tmp_path):
    """The whole safety property: an editorial ruling removes, it never admits."""
    f = _file(tmp_path, [
        {"label": "x", "triage": {"verdict": "not_a_force", "note": "a published series"}},
    ])
    import json
    doc = json.loads(Path(f).read_text())
    assert not doc["proposals"][0].get("promotable")
    rows, ruled = worklist(f)
    assert rows == [] and len(ruled) == 1


def test_an_unknown_verdict_is_not_a_ruling(tmp_path):
    """A typo must leave the proposal ON the queue rather than silently dropping it."""
    assert triaged({"triage": {"verdict": "looks_wrong", "note": "n"}}) is None
    f = _file(tmp_path, [{"label": "x", "triage": {"verdict": "looks_wrong", "note": "n"}}])
    rows, ruled = worklist(f)
    assert len(rows) == 1 and ruled == []


def test_every_verdict_carries_a_written_meaning():
    """The vocabulary is the contract; a verdict nobody can define is not usable."""
    assert set(TRIAGE_VERDICTS) == {"duplicate", "not_a_force", "unsourceable", "expired"}
    assert all(isinstance(v, str) and v for v in TRIAGE_VERDICTS.values())


def test_the_live_file_rules_nothing_in_by_triage():
    """Live-clean companion to the synthetic tests above."""
    import json
    p = Path(__file__).resolve().parents[1] / "s4_proposals/2026-08-31.json"
    if not p.exists():
        pytest.skip("proposal file absent")
    for prop in json.loads(p.read_text())["proposals"]:
        if triaged(prop):
            assert not prop.get("promotable"), prop.get("label")
