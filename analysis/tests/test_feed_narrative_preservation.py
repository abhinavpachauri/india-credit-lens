#!/usr/bin/env python3
"""
Unit tests for narrative preservation across an opportunities-feed rebuild
(analysis/crosssource/generate_opportunities_feed.preserve_narratives).

An LLM narrative is written against one computed state. The deterministic
(title, status) pair fingerprints that state: cross-system titles encode
direction, pipeline titles are static labels whose state signal is the status.
These tests pin the four cases from HANDOFF_NARRATIVE_STALENESS_BUG.md:
  (a) title+status unchanged  → preserved
  (b) title flipped           → dropped (the observed cc-spend bug)
  (c) status flipped, same title → dropped (the pipeline-card hole)
  (d) eco_loop                → never preserved (COMPOSITION_SPEC §23.2)

Run: python3 -m pytest analysis/tests/test_feed_narrative_preservation.py -q
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from crosssource.generate_opportunities_feed import preserve_narratives  # noqa: E402


def cross(**kw):
    item = {"id": "x1", "title": "flow softening ahead of stock", "status": "watch",
            "body": "B", "implication": "I", "chain": ["c1"],
            "driver": {"kind": "eco_edge"}}
    item.update(kw)
    return item


def feed(item, pipeline_items=None):
    return {"cross_system": [item], "pipelines": {"sibc": pipeline_items or []}}


def narrated(item):
    return {**item, "narrative": True}


def test_unchanged_state_preserves_narrative():
    prev = feed(narrated(cross()))
    new = feed(cross(body="template", implication="ti", chain=["t"]))
    assert preserve_narratives(prev, new) == 1
    got = new["cross_system"][0]
    assert (got["body"], got["implication"], got["chain"]) == ("B", "I", ["c1"])
    assert got["narrative"] is True


def test_flipped_title_drops_narrative():
    prev = feed(narrated(cross()))
    new = feed(cross(title="flow leading stock — origination headroom",
                     status="active", body="template"))
    assert preserve_narratives(prev, new) == 0
    got = new["cross_system"][0]
    assert got["body"] == "template"
    assert "narrative" not in got


def test_flipped_status_same_title_drops_narrative():
    """Pipeline cards carry static model labels — status is their only state signal."""
    prev_item = narrated({"id": "opp1", "title": "Co-lending expansion",
                          "status": "watch", "body": "B", "implication": "I",
                          "chain": ["c1"], "driver": {"kind": "force"}})
    new_item = {"id": "opp1", "title": "Co-lending expansion", "status": "active",
                "body": "template", "implication": "ti", "chain": ["t"],
                "driver": {"kind": "force"}}
    prev = {"cross_system": [], "pipelines": {"sibc": [prev_item]}}
    new = {"cross_system": [], "pipelines": {"sibc": [new_item]}}
    assert preserve_narratives(prev, new) == 0
    assert new["pipelines"]["sibc"][0]["body"] == "template"


def test_eco_loop_never_preserved():
    loop = cross(driver={"kind": "eco_loop"})
    prev = feed(narrated(loop))
    new = feed(cross(driver={"kind": "eco_loop"}, body="template"))
    assert preserve_narratives(prev, new) == 0
    assert new["cross_system"][0]["body"] == "template"


def test_moved_numbers_drop_narrative_even_when_title_and_status_hold():
    """Prose citing last period's YoY is stale even under an identical headline."""
    basis = lambda v: {"facts": [{"id": "sibc-pl-cc-yoy", "value": v}]}  # noqa: E731
    prev = feed(narrated(cross(basis=basis(1.33))))
    new = feed(cross(basis=basis(2.10), body="template"))
    assert preserve_narratives(prev, new) == 0
    assert new["cross_system"][0]["body"] == "template"

    same = feed(cross(basis=basis(1.33), body="template"))
    assert preserve_narratives(prev, same) == 1
    assert same["cross_system"][0]["body"] == "B"


def test_unnarrated_prev_item_is_not_carried():
    prev = feed(cross())  # no narrative flag
    new = feed(cross(body="template"))
    assert preserve_narratives(prev, new) == 0
    assert new["cross_system"][0]["body"] == "template"
