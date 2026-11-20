"""
Bank-wise dashboard cuts: one per credit measure, under one dimension, `banks`.

Like NBFC, bank-wise has no card generator (BANKWISE_SPEC §8a), so its cut table lives on its
own. The measures are NOT retyped here: they are the skeleton profile's nodes
(`rbi_bankwise/skeleton_profile.json`), the same list the registry is built from
(`build_registry.py`). Each cut is that measure split by bank group; its parent rate is the
measure's all-banks growth. Only all credit (`gross`) is an ANCHOR, the line a tile shows: a
tile carrying thirteen measures' bands would be a wall, and the pane shows the one on screen.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

from core.movement_cards import MovementCut                            # noqa: E402

MOVEMENT_PREFIX = "bw-"
SECTION = "banks"
_NODES = json.loads((ROOT / "analysis/rbi_bankwise/skeleton_profile.json").read_text())["nodes"]


def _cut(n: dict) -> MovementCut:
    slug = f"{n['code'].replace('_', '-')}-category"
    lab = n["label"].lower()
    noun = "bank credit" if n["code"] == "gross" else (lab if lab.endswith("credit") else f"{lab} credit")
    return MovementCut(slug, SECTION, f"bw-{slug}-yoy-scan", noun,
                       parent_yoy=f"bw-{n['code'].replace('_', '-')}-yoy",
                       parent_label="All banks' credit" if n["code"] == "gross" else f"All banks' {noun}")


MOVEMENT_CUTS = [_cut(n) for n in _NODES]

#: How each measure is named in the dashboard's measure menu, in reading order: all credit, the
#: sectors, the retail parts, then the accounting lines. Built from the profile's labels.
_ORDER = ["gross", "agri", "industry", "services", "retail", "housing", "vehicle", "cards",
          "education", "other_retail", "other_non_food", "non_food", "food"]
_SHORT = {"gross": "All credit", "agri": "Agriculture", "retail": "Retail",
          "vehicle": "Vehicle", "cards": "Cards", "housing": "Housing", "education": "Education",
          "other_retail": "Other retail", "other_non_food": "Other non-food"}
TITLES = {f"bw-{c.replace('_', '-')}-category": _SHORT.get(c) or next(n["label"] for n in _NODES if n["code"] == c)
          for c in _ORDER}

#: The cuts a dimension TILE shows; the rest show in the pane, for the measure on screen.
ANCHORS = ["gross-category"]

#: No dimension here has a rate without a split.
STATE_RATE_ONLY: list = []

#: Each bank's own book (BANKWISE_SPEC §8b gap 2): the lines a bank row opens into, read by
#: `core/bank_tables.books`. The four sectors with retail's parts under it, then the accounting
#: lines; non-food is left out because it is the four sectors and other non-food added up.
_BOOK = [("agri", 0), ("industry", 0), ("services", 0), ("retail", 0), ("housing", 1),
         ("other_retail", 1), ("vehicle", 1), ("education", 1), ("cards", 1),
         ("food", 0), ("other_non_food", 0)]
_METRIC = {n["code"]: n["metric"] for n in _NODES}
BOOK = {"whole": _METRIC["gross"],
        "lines": [{"metric": _METRIC[c], "label": TITLES[f"bw-{c.replace('_', '-')}-category"],
                   "indent": i} for c, i in _BOOK]}
