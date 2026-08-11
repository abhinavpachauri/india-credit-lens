#!/usr/bin/env python3
"""
Rewrite the payments card golden from the current generator output.

Run this ONLY when a change to the cards is intended, and say why in the commit. The golden
exists so that "the output changed" is a question someone has to answer, rather than something
that happens quietly during a refactor.

    python3 analysis/tests/golden/refresh_atm_pos_cards.py
"""
import json
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
CARDS = ROOT / "analysis/rbi_atm_pos/insights.json"
GOLDEN = Path(__file__).with_name("atm_pos_cards.json")


def main() -> int:
    cards = json.loads(CARDS.read_text())
    previous = json.loads(GOLDEN.read_text()) if GOLDEN.exists() else {"cards": {}}
    golden = {
        "_meta": previous.get("_meta", {}) | {"period": cards[0]["period"]},
        "cards": {
            c["id"]: {
                "group": c["group"], "cut": c["cut"], "type": c["type"],
                "representation": c.get("representation"),
                "effect": c.get("effect"),
                "sourceSignals": c.get("sourceSignals"),
                "title": None if c.get("representation") == "llm" else c["title"],
                "body": None if c.get("representation") == "llm" else c["body"],
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
