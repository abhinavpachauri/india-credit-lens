#!/usr/bin/env python3
"""
Rewrite the payments card golden from the generator's DETERMINISTIC output.

Run this ONLY when a change to the cards is intended, and say why in the commit. The golden
exists so that "the output changed" is a question someone has to answer, rather than something
that happens quietly during a refactor.

    python3 analysis/tests/golden/refresh_atm_pos_cards.py

Note what is captured: the cards as the rules, relational builders and dominance guard produce
them — BEFORE the LLM representation layer rewrites the prose of anchored cards. Reading the
shipped insights.json instead would leave the anchored cards' text unpinned (it is replaced by
evaluation text), and those are precisely the cards being migrated. Generating the same way the
test does keeps every deterministic sentence under the net.
"""
import json
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))
GOLDEN = Path(__file__).with_name("atm_pos_cards.json")


def deterministic_cards() -> list[dict]:
    """Exactly what analysis/tests/test_atm_pos_insights_contract.py builds."""
    from pipelines.atm_pos import generate_atm_pos_insights as gen

    signals = json.loads((ROOT / "analysis/rbi_atm_pos/signals.json").read_text())
    month = signals["meta"]["latest_month"]
    cards = [c for c in (gen.produce(p, signals, month) for p in gen.RULES) if c]
    cards.extend(gen.relational_cards(signals, month))
    gen.apply_dominance_guard(cards, signals["meta"]["latest_period"])
    return cards


def main() -> int:
    cards = deterministic_cards()
    previous = json.loads(GOLDEN.read_text()) if GOLDEN.exists() else {"cards": {}}
    golden = {
        "_meta": previous.get("_meta", {}) | {
            "period": cards[0]["period"],
            "captured": "pre-LLM deterministic output (rules + relational + dominance guard)",
        },
        "cards": {
            c["id"]: {
                "group": c["group"], "cut": c["cut"], "type": c["type"],
                "representation": c.get("representation"),
                "effect": c.get("effect"),
                "sourceSignals": c.get("sourceSignals"),
                "title": c["title"],
                "body": c["body"],
                "implication": c.get("implication"),
                "chain": (c.get("reasoning") or {}).get("chain"),
            }
            for c in cards
        },
        "order": [c["id"] for c in cards],
    }
    GOLDEN.write_text(json.dumps(golden, indent=2, ensure_ascii=False) + "\n")
    added = set(golden["cards"]) - set(previous.get("cards", {}))
    dropped = set(previous.get("cards", {})) - set(golden["cards"])
    print(f"golden refreshed: {len(golden['cards'])} cards")
    if added:
        print("  added:   " + ", ".join(sorted(added)))
    if dropped:
        print("  DROPPED: " + ", ".join(sorted(dropped)) + "  ← is that intended?")
    return 0


if __name__ == "__main__":
    sys.exit(main())
