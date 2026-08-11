"""
A characterisation net around the payments insight generator, so it can be refactored.

`generate_atm_pos_insights.py` was the largest module in the repo and had no direct tests. It
was also the least generic: ~30 hand-written functions, one per dashboard card, where SIBC
derives its cards from the registry. Migrating it was only safe because "the output did not
change" is something these tests can answer — otherwise a card can quietly vanish or change
routing and nobody notices until the dashboard looks wrong.

These tests do not describe what the generator *should* do. They pin what it *does* today,
against a golden file kept OUTSIDE the generated artifact, so any behaviour change during the
migration has to be deliberate: either the code is wrong, or the golden is refreshed in the
same commit with a stated reason.

What is captured is the DETERMINISTIC output — the cards as the rules, relational builders and
dominance guard produce them, before the LLM layer rewrites the prose of anchored cards. That is
deliberate: reading the shipped insights.json would leave anchored cards' text unpinned, and those
are exactly the cards being migrated. Every deterministic sentence stays under the net; evaluation
text, which legitimately changes when an eval re-runs, never enters the golden.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

# The expectation lives in its own file, NOT in the generated artifact. Comparing generator
# output against analysis/rbi_atm_pos/insights.json would be circular — the generator rewrites
# that file, so regenerating would silently redefine what "unchanged" means. Refreshing the
# golden is a deliberate act: analysis/tests/golden/refresh_atm_pos_cards.py.
GOLDEN = json.loads((ROOT / "analysis/tests/golden/atm_pos_cards.json").read_text())
EXPECTED = GOLDEN["cards"]
SIGNALS = json.loads((ROOT / "analysis/rbi_atm_pos/signals.json").read_text())
SHIPPED = json.loads((ROOT / "analysis/rbi_atm_pos/insights.json").read_text())


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
    for spec in gen.CARDS:
        try:
            result = gen.render_card(spec, SIGNALS, month)
        except Exception as exc:                       # noqa: BLE001 — reported, not swallowed
            failures.append(f"{spec.id}: {exc}")
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
    return (card["group"], card["cut"], card["type"],
            effect.get("focusCard"), effect.get("tab"), effect.get("trendMode"),
            tuple(effect.get("highlight") or ()))


def test_no_producer_raises(generated):
    """main() catches per-rule exceptions and prints them, but still exits 0 — so a card can
    disappear from the dashboard without failing the gate. Until that is fixed, this test is
    the thing that notices."""
    _, failures = generated
    assert not failures, "rule(s) raised: " + "; ".join(failures)


def test_card_inventory_is_unchanged(generated):
    cards, _ = generated
    assert {c["id"] for c in cards} == set(EXPECTED)


def test_card_order_is_unchanged(generated):
    """Order is what the dashboard shows, so migrating a card must not reshuffle the page."""
    cards, _ = generated
    assert [c["id"] for c in cards] == GOLDEN["order"]


def test_no_duplicate_card_ids(generated):
    cards, _ = generated
    ids = [c["id"] for c in cards]
    assert len(ids) == len(set(ids))


def test_routing_is_unchanged(generated):
    """Group, cut, type and every chart-driving field, per card."""
    cards, _ = generated
    for card in cards:
        assert _routing(card) == _routing(EXPECTED[card["id"]]), f"{card['id']} routing changed"


def test_cited_evidence_is_unchanged(generated):
    """A card cites the signals it used. During the gap migration these stopped being typed out
    by hand and became derived from the paths the card reads — so this is the assertion that the
    derivation produces exactly what the hand-written list did."""
    cards, _ = generated
    for card in cards:
        want = EXPECTED[card["id"]]["sourceSignals"]
        assert card.get("sourceSignals") == want, f"{card['id']} cites different signals"


def test_deterministic_prose_is_unchanged(generated):
    """Cards the LLM never touches must render identical text — these are pure functions of
    signals.json, so any diff here is a real behaviour change."""
    cards, _ = generated
    for card in cards:
        want = EXPECTED[card["id"]]
        assert card["title"] == want["title"], f"{card['id']} title changed"
        assert card["body"] == want["body"], f"{card['id']} body changed"
        assert card.get("implication") == want["implication"], f"{card['id']} implication changed"
        assert (card.get("reasoning") or {}).get("chain") == want["chain"], f"{card['id']} chain changed"


@pytest.mark.parametrize("card", SHIPPED, ids=lambda c: c["id"])
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
    for card in SHIPPED:
        assert card.get("representation") in valid, card["id"]


# ── The branch that is not firing this month ──────────────────────────────────
# A characterisation golden can only pin cards that actually render, so a card behind a
# condition that is false today is invisible to every test above. The concentration cards are
# exactly that: they only appear in a month where no bank changed rank. They used to be the
# `else` of another card's function, which is why a stale hardcoded number survived in one of
# them unnoticed.

def _with_ranks(group: str, changes: list) -> dict:
    """This month's signals with the rank-change list forced either way. Both states have to be
    constructed: whether any bank moved rank is a property of the month, and asserting against
    whichever happened to be true in June would test the data, not the code."""
    import copy
    signals = copy.deepcopy(SIGNALS)
    signals["groups"][group]["top_n"]["rank_changes"] = changes
    return signals


A_RANK_CHANGE = [{"name": "SOME BANK LTD", "from_rank": 6, "to_rank": 5}]


@pytest.mark.parametrize("group,rank_card,quiet_card", [
    ("cc", "cc-top-bank-rank-change", "cc-top5-concentration"),
    ("dc", "dc-top-bank-rank-change", "dc-top-bank-leader"),
])
def test_rank_and_concentration_cards_are_mutually_exclusive(gen, group, rank_card, quiet_card):
    """These two were one function with a hidden fork. Splitting them is only faithful if
    exactly one can ever fire."""
    month = SIGNALS["meta"]["latest_month"]
    moved = _with_ranks(group, A_RANK_CHANGE)
    still = _with_ranks(group, [])
    fired = lambda sig: [bool(gen.render_card(gen.TOP_BANK[c], sig, month)) for c in (rank_card, quiet_card)]
    assert fired(moved) == [True, False], f"{group}: wrong card(s) fired when a bank moved rank"
    assert fired(still) == [False, True], f"{group}: wrong card(s) fired when ranks were still"


def test_concentration_prose_reads_the_real_share(gen):
    """The CC concentration card used to open with a hardcoded '74%' while the number printed
    beside it was computed — frozen prose that would drift the moment concentration moved."""
    month = SIGNALS["meta"]["latest_month"]
    quiet = _with_ranks("cc", [])
    card = gen.render_card(gen.TOP_BANK["cc-top5-concentration"], quiet, month)
    share = quiet["groups"]["cc"]["top_n"]["top5_share_pct"]
    assert f"{share:.1f}%" in card["implication"]
    assert "74%" not in card["implication"] or abs(share - 74) < 0.05


# ── The cash-trend forks ──────────────────────────────────────────────────────
# Two more functions that were each secretly two cards, split on the direction of a streak.
# Same risk as the top-bank pair: if the conditions overlap, a month could publish both halves
# of a contradiction — "cash is falling, customers are becoming visible" beside "cash is
# rising, customers are in liquidity stress".

@pytest.mark.parametrize("falling,rising,metric_path", [
    ("cc-atm-declining", "cc-atm-rising", "groups.cc.total.metrics.cc_atm_withdrawal_vol"),
    ("dc-atm-declining", "dc-atm-rising", "groups.dc.total.metrics.dc_atm_withdrawal_vol"),
])
def test_cash_trend_directions_cannot_both_fire(gen, falling, rising, metric_path):
    import copy
    month = SIGNALS["meta"]["latest_month"]
    group, metric = metric_path.split(".")[1], metric_path.split(".")[-1]

    def with_streak(direction, months, mom):
        sig = copy.deepcopy(SIGNALS)
        node = sig["groups"][group]["total"]["metrics"][metric]
        node["streak_dir"], node["streak_months"], node["mom_pct"] = direction, months, mom
        return sig

    for state in (with_streak("down", 5, -8.0), with_streak("up", 5, 9.0), with_streak("flat", 1, 0.1)):
        fired = [c for c in (falling, rising) if gen.render_card(gen.CASH[c], state, month)]
        assert len(fired) <= 1, f"both directions fired at once: {fired}"


def test_every_card_id_is_unique_in_the_declaration_list(gen):
    """CARDS is now the whole dashboard in one list, so a copy-paste that duplicates an id would
    render the same card twice."""
    ids = [c.id for c in gen.CARDS]
    assert len(ids) == len(set(ids))
