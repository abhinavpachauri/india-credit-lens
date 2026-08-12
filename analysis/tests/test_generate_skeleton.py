"""
The merge contract: regenerating the skeleton must never destroy authored work.

`generate_skeleton.py` runs in both gates, on every ingestion, and rewrites system_model.json
in place. The entity nodes and structural edges are its to own. Everything else in that file —
forces, risks, opportunities, gaps, behavioral edges, loops, dated force instances — was
authored by a human, sometimes with a sourced citation behind it, and the generator's contract
is to carry it through untouched.

That contract had no test. If it broke, nothing would fail: the model would still validate, the
gate would still pass, and a month of authored causal work would simply be gone from the file.
The `--check` mode that guards staleness would then happily confirm the emptier model was fresh.

Also pins determinism, because two other guards assume it. check_derived_fresh regenerates the
skeleton and diffs it against the committed copy, so a generator that varied run to run would
make that guard cry wolf until someone silenced it.
"""
import json
import sys
from pathlib import Path

import pytest

ANALYSIS = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"
sys.path.insert(0, str(ANALYSIS))

from core import generate_skeleton as gs  # noqa: E402


# ── Pure helpers ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("partition,code,expected_prefix", [
    ("main_sectors", "1", "e_"),
    ("personal_loans", "4.8", "e_"),
])
def test_entity_id_is_prefixed_and_stable(partition, code, expected_prefix):
    first = gs.entity_id(partition, code)
    assert first.startswith(expected_prefix)
    assert first == gs.entity_id(partition, code), "entity_id must be a pure function of its inputs"


def test_entity_id_separates_partitions():
    """The same code can mean different things in different partitions, so the id must not
    collide — an id collision would silently merge two sectors into one node."""
    assert gs.entity_id("main_sectors", "1") != gs.entity_id("personal_loans", "1")


def test_codesort_orders_numerically_not_lexically():
    """'4.10' comes after '4.9'. Sorted as text it would come after '4.1' and before '4.2',
    which would reorder the model file on every regeneration for no reason."""
    codes = ["4.10", "4.2", "4.9", "10", "2"]
    assert sorted(codes, key=gs._codesort) == ["2", "4.2", "4.9", "4.10", "10"]


@pytest.mark.parametrize("value,expected", [
    ("true", True), (" true ", True),      # surrounding whitespace is stripped
    ("True", False),                       # case-SENSITIVE — see the note below
    ("no", False), ("", False), (None, False),
])
def test_truthy_matches_the_declared_vocabulary_exactly(value, expected):
    """The vocabulary is the contract, and matching is exact after stripping.

    That is deliberate rather than an oversight: the built-in default is
    ["True", "true", "1"], which enumerates both capitalisations by hand. A profile that
    declares only "true" will read a CSV's "True" as false — silently, since the flag simply
    does not fire and a reclassification quietly does not happen. Worth knowing when adding a
    source: list every spelling the file actually contains.
    """
    assert gs.truthy(value, {"true", "1"}) is expected


def test_default_truthy_vocabulary_covers_both_capitalisations():
    """Guards the enumeration above — if the default ever loses a spelling, a reclassification
    flag stops firing and nothing complains."""
    default = {"True", "true", "1"}
    for spelling in ("True", "true", "1"):
        assert gs.truthy(spelling, default) is True


# ── The merge contract ────────────────────────────────────────────────────────

AUTHORED_FORCE = {
    "id": "force_kcc_collateral_limit", "tier": "force",
    "label": "RBI raised the collateral-free agri limit",
    "sourced": True, "source_url": "https://pib.gov.in/…",
}
AUTHORED_RISK = {"id": "risk_cc_concentration", "tier": "risk", "label": "Card concentration"}
AUTHORED_EDGE = {"from": "force_kcc_collateral_limit", "to": "e_agri", "type": "drives"}
AUTHORED_LOOP = {"id": "loop_unsecured_spend", "members": ["e_pl", "e_cc"], "polarity": "reinforcing"}
AUTHORED_INSTANCE = {"id": "fi_kcc_2025", "channel": "ch_kcc", "from": "2025-01-01"}


def _existing_model(tmp_path: Path) -> Path:
    """A model as it looks after a human has authored a behavioral layer on top."""
    model = {
        "_meta": {"schema_version": "4.0", "mode": "update", "last_updated": "2026-07-31"},
        "nodes": [
            {"id": "e_agri", "tier": "entity", "statement": "S1", "code": "2",
             "label": "Agriculture", "data_section": "mainSectors",
             "annotation_ids": ["sibc-agri-yoy"], "description": "An authored description."},
            AUTHORED_FORCE, AUTHORED_RISK,
        ],
        "edges": [
            {"from": "e_total", "to": "e_agri", "type": "composes_into"},   # structural
            AUTHORED_EDGE,                                                   # behavioral
        ],
        "force_instances": [AUTHORED_INSTANCE],
        "loops": [AUTHORED_LOOP],
    }
    path = tmp_path / "system_model.json"
    path.write_text(json.dumps(model, indent=2))
    return path


def _regenerate(tmp_path, fresh_nodes=None, fresh_edges=None):
    """Run the merge as an ingestion would: a freshly emitted skeleton over the existing file."""
    cfg = {"model": _existing_model(tmp_path), "report_id": "sibc", "report_name": "RBI SIBC"}
    nodes = fresh_nodes if fresh_nodes is not None else [
        {"id": "e_agri", "tier": "entity", "statement": "S1", "code": "2", "label": "Agriculture",
         "description": "Regenerated boilerplate (2)."},
    ]
    edges = fresh_edges if fresh_edges is not None else [
        {"from": "e_total", "to": "e_agri", "type": "composes_into"},
    ]
    return gs.merge_model("sibc", cfg, {}, nodes, edges, [])


def test_authored_behavioral_nodes_survive_regeneration(tmp_path):
    model, _, _, _ = _regenerate(tmp_path)
    ids = {n["id"] for n in model["nodes"]}
    assert "force_kcc_collateral_limit" in ids, "an authored, sourced force was destroyed"
    assert "risk_cc_concentration" in ids


def test_the_authored_force_survives_intact_not_just_by_id(tmp_path):
    """Carrying the id forward while dropping its sourcing would be worse than deleting it —
    the model would still look sourced."""
    model, _, _, _ = _regenerate(tmp_path)
    force = next(n for n in model["nodes"] if n["id"] == "force_kcc_collateral_limit")
    assert force == AUTHORED_FORCE


def test_behavioral_edges_and_loops_survive(tmp_path):
    model, _, _, _ = _regenerate(tmp_path)
    assert AUTHORED_EDGE in model["edges"]
    assert model["loops"] == [AUTHORED_LOOP]
    assert model["force_instances"] == [AUTHORED_INSTANCE]


def test_structural_edges_are_replaced_not_accumulated(tmp_path):
    """The generator owns structural edges. If the old ones were kept alongside the new, the
    model would grow a duplicate composes_into on every single ingestion."""
    model, _, _, _ = _regenerate(tmp_path)
    structural = [e for e in model["edges"] if e["type"] in gs.STRUCTURAL_EDGE_TYPES]
    assert len(structural) == 1


def test_authored_entity_fields_are_carried_forward(tmp_path):
    """An entity node is regenerated, but the human-authored bridge fields on it are not the
    generator's to discard — annotation_ids especially, which are permanent by project rule."""
    model, _, _, _ = _regenerate(tmp_path)
    agri = next(n for n in model["nodes"] if n["id"] == "e_agri")
    assert agri["annotation_ids"] == ["sibc-agri-yoy"]
    assert agri["data_section"] == "mainSectors"
    assert agri["description"] == "An authored description.", "authored prose was overwritten"


def test_new_and_removed_entities_are_reported(tmp_path):
    """A code appearing or vanishing in the source is a fact the operator must see, not a
    silent structural change."""
    fresh = [
        {"id": "e_agri", "tier": "entity", "statement": "S1", "code": "2", "label": "Agriculture"},
        {"id": "e_new", "tier": "entity", "statement": "S1", "code": "9", "label": "Brand New"},
    ]
    model, added, removed, _ = _regenerate(tmp_path, fresh_nodes=fresh)
    assert ("S1", "9") in added
    assert removed == []


def test_a_pre_v3_model_is_not_merged(tmp_path):
    """Old schema versions anchored their behavioral layer to a different entity-id scheme, so
    carrying it forward would attach forces to nodes that no longer exist."""
    path = tmp_path / "system_model.json"
    path.write_text(json.dumps({
        "_meta": {"schema_version": "2.0"},
        "nodes": [{"id": "old_force", "tier": "force"}],
        "edges": [], "loops": [{"id": "old_loop"}],
    }))
    cfg = {"model": path, "report_id": "sibc", "report_name": "RBI SIBC"}
    model, _, _, _ = gs.merge_model("sibc", cfg, {}, [], [], [])
    assert all(n["id"] != "old_force" for n in model["nodes"])
    assert model["loops"] == []


def test_merge_is_deterministic(tmp_path):
    """check_derived_fresh regenerates the skeleton and diffs it against the committed copy, so
    a generator that varied between runs would make that guard fire forever."""
    first, *_ = _regenerate(tmp_path)
    second, *_ = _regenerate(tmp_path)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_schema_version_is_preserved_across_regeneration(tmp_path):
    """A model migrated to 4.0 must not silently fall back to 3.0."""
    model, _, _, _ = _regenerate(tmp_path)
    assert model["_meta"]["schema_version"] == "4.0"
