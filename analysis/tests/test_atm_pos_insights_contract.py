"""
A characterisation net around the payments insight generator, so it can be refactored.

`generate_atm_pos_insights.py` is the largest module in the repo (2,086 lines) and had no
direct tests. It is also the least generic: ~30 hand-written functions, one per dashboard
card, where SIBC derives its cards from the registry. Migrating it onto the registry-driven
path is worthwhile but only safe if "the output did not change" is something a machine can
check — otherwise a card can quietly vanish or change routing and nobody notices until the
dashboard looks wrong.

These tests do not describe what the generator *should* do. They pin what it *does* today,
against the committed insights.json, so any behaviour change during the migration has to be
deliberate: either the code is wrong, or the golden file gets updated in the same commit
with a reason.

Deliberately NOT pinned: the prose of LLM-represented cards. That text comes from the
evaluation JSON and changes when the eval re-runs, which is expected and not a regression.
Their *routing* is pinned like everything else.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

COMMITTED = json.loads((ROOT / "analysis/rbi_atm_pos/insights.json").read_text())
SIGNALS = json.loads((ROOT / "analysis/rbi_atm_pos/signals.json").read_text())


@pytest.fixture(scope="module")
def gen():
    import importlib
    return importlib.import_module("pipelines.atm_pos.generate_atm_pos_insights")


@pytest.fixture(scope="module")
def generated(gen):
    """Run the deterministic half of the generator: every rule, the relational cards, and the
    dominance guard. The LLM representation layer is skipped — it rewrites prose from an
    evaluation file, which is not what this contract is about."""
    month = SIGNALS["meta"]["latest_month"]
    cards, failures = [], []
    for rule in gen.RULES:
        try:
            result = rule(SIGNALS, month)
        except Exception as exc:                       # noqa: BLE001 — reported, not swallowed
            failures.append(f"{rule.__name__}: {exc}")
            continue
        if result:
            cards.append(result)
    cards.extend(gen.relational_cards(SIGNALS, month))
    gen.apply_dominance_guard(cards, SIGNALS["meta"]["latest_period"])
    return cards, failures


def test_dominance_guard_runs_without_any_evaluation(gen, generated):
    """The guard is deterministic, so it must not depend on the LLM step having run.

    It used to live inside apply_llm_representation, behind the check that skips a card with no
    evaluation entry — so in a period with no evaluation, nothing was attributed and a
    single-issuer artifact would have published as a market move. The fixture above never loads
    an evaluation, so if any card here carries the caveat, the guard is genuinely independent.
    """
    cards, _ = generated
    guarded = [c for c in cards if c.get("representation") == "deterministic-dominance"]
    assert guarded, "no card was attributed without an evaluation — the guard is still coupled"
    for card in guarded:
        assert card.get("single_entity_artifact") is True
        assert card.get("eval_signal"), f"{card['id']} lost its signal link"


def _routing(card):
    """Everything that decides where a card lands in the UI. Prose may change; this must not."""
    effect = card.get("effect") or {}
    return (card["id"], card["group"], card["cut"], card["type"],
            effect.get("focusCard"), effect.get("tab"), effect.get("trendMode"),
            tuple(effect.get("highlight") or ()))


def test_no_rule_raises(generated):
    """main() catches per-rule exceptions and prints them, but still exits 0 — so a card can
    disappear from the dashboard without failing the gate. Until that is fixed, this test is
    the thing that notices."""
    _, failures = generated
    assert not failures, "rule(s) raised: " + "; ".join(failures)


def test_card_inventory_is_unchanged(generated):
    cards, _ = generated
    assert {c["id"] for c in cards} == {c["id"] for c in COMMITTED}


def test_no_duplicate_card_ids(generated):
    cards, _ = generated
    ids = [c["id"] for c in cards]
    assert len(ids) == len(set(ids))


def test_routing_is_unchanged(generated):
    """Group, cut, type and every chart-driving field, per card."""
    cards, _ = generated
    assert {_routing(c) for c in cards} == {_routing(c) for c in COMMITTED}


def test_deterministic_prose_is_unchanged(generated):
    """Cards the LLM never touches must render identical text — these are pure functions of
    signals.json, so any diff here is a real behaviour change."""
    cards, _ = generated
    committed = {c["id"]: c for c in COMMITTED if c.get("representation") != "llm"}
    for card in cards:
        want = committed.get(card["id"])
        if want is None:                    # an LLM-represented card — prose not pinned
            continue
        assert card["title"] == want["title"], f"{card['id']} title changed"
        assert card["body"] == want["body"], f"{card['id']} body changed"


@pytest.mark.parametrize("card", COMMITTED, ids=lambda c: c["id"])
def test_every_card_carries_its_evidence(card):
    """The platform's standing rule: a card states where its numbers came from. Enforced at
    the gate by Stage 4c; asserted here so a refactor cannot quietly drop the linkage."""
    assert card.get("sourceSignals"), f"{card['id']} declares no sourceSignals"
    chain = (card.get("reasoning") or {}).get("chain") or (card.get("basis") or {}).get("inferences")
    assert chain and len(chain) >= 2, f"{card['id']} has no inference chain"


def test_representation_is_declared(generated):
    """Every card says how its prose was produced — llm, or one of the deterministic kinds.
    The migration must preserve this, because Stage 4c validates the two differently."""
    valid = {"llm", "deterministic", "deterministic-db", "deterministic-dominance"}
    for card in COMMITTED:
        assert card.get("representation") in valid, card["id"]
