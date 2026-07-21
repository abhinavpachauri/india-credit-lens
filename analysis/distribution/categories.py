#!/usr/bin/env python3
"""
categories.py — the editorial partition, in code
-------------------------------------------------
DISTRIBUTION_SPEC §2 says repetition is prevented at design time by partitioning the
signal space into non-overlapping categories, and that the ledger only *verifies* the
partition held. This module is that partition.

The assignment is deterministic and derived from the registry, not from a hand-listed
set of card ids: a claim's category follows from the compute method that produced its
signal. Add a compute method and it must be classified here — an unclassified method
raises rather than silently landing in C1, because a silent default is how two slots
start telling the same story.

Boundary rules from §3, encoded:

  - a claim belongs to exactly ONE category
  - when a card's signals span categories, the most specific wins (see PRECEDENCE) —
    a rotation card that also quotes a level is still a rotation card
  - C1 states levels; the moment the framing is "and that changed direction", it is C5
  - C6/C7 are model-driven and never derived from L1 methods, so they are assigned by
    the source artifact (the opportunities feed), not by compute method
"""

# Category id → (short label, the question it answers). §3.
CATEGORIES = {
    "C1":  ("Headline levels", "What are the numbers"),
    "C2":  ("Rotation", "What's gaining ground, at whose expense"),
    "C3":  ("Divergence", "What used to move together and no longer does"),
    "C4":  ("Spread", "Broad-based, or a few names carrying it"),
    "C5":  ("Turns", "What changed direction"),
    "C6":  ("Openings & risks", "So what, and for whom"),
    "C7":  ("Cross-system", "What credit and payments say together"),
    "C8":  ("Watchlist", "What could flip next month"),
    "C9":  ("Corrections", "Where our earlier read was wrong"),
    "C10": ("Method", "How this thing is built"),
}

# Layer-1 compute method → category. The registry is the source of truth for which
# methods exist; `unclassified_methods()` fails loudly when the two drift apart.
METHOD_CATEGORY = {
    # C1 — levels and the rates that describe them
    "csv_sector_abs":                "C1",
    "csv_total_abs":                 "C1",
    "csv_sector_yoy":                "C1",
    "csv_total_yoy":                 "C1",
    "csv_sector_share":              "C1",
    "csv_category_share":            "C1",
    "csv_total_ratio":               "C1",
    "csv_ratio_sum":                 "C1",
    # C2 — share of the mix moving between entities
    "csv_sector_rotation":           "C2",
    "csv_category_rotation":         "C2",
    # C3 — declared co-movement breaking (hierarchy axis and metric axis)
    "csv_sector_divergence":         "C3",
    "csv_bank_divergence":           "C3",
    "csv_pair_divergence":           "C3",
    # C4 — distribution across an entity set: breadth, concentration, leaders/laggards
    "csv_sector_scan_yoy":           "C4",
    "csv_sector_scan_share":         "C4",
    "csv_psl_scan_yoy":              "C4",
    "csv_bank_scan":                 "C4",
    "csv_category_scan_share":       "C4",
    "csv_sector_count_positive_yoy": "C4",
    "csv_sector_yoy_spread":         "C4",
    # C5 — direction changing: runs, and growth measured against its own past growth
    "csv_streak":                    "C5",
    "csv_sector_fy_acceleration":    "C5",
    "csv_sector_fy_delta":           "C5",
}

# Most specific wins when one card's signals span categories (§3 boundary rules).
PRECEDENCE = ["C3", "C2", "C5", "C4", "C1"]

# Categories that are not derived from L1 methods at all.
ARTIFACT_CATEGORIES = {
    "C6":  "opportunities_feed.json — pipeline openings and risks (S3-driven)",
    "C7":  "opportunities_feed.json — cross_system items (constructs, eco-edges, loops, constraints)",
    "C8":  "signals/proximity.py — distance to the next status flip",
    "C9":  "distribution_ledger.json + registry retirements — where an earlier read was wrong",
    "C10": "ai_pm_register.json — the AI PM track",
}


def label(category):
    return CATEGORIES[category][0]


def question(category):
    return CATEGORIES[category][1]


def category_of_method(method):
    """The category a compute method's claims belong to. None if the method is unknown."""
    return METHOD_CATEGORY.get(method)


def category_of_signals(signal_ids, registry):
    """The single category a card belongs to, given the signals it cites.

    Precedence resolves the multi-signal case: a card citing both a rotation signal and
    a level is a rotation card, because rotation is the question it answers.
    """
    found = set()
    for sid in signal_ids:
        sig = registry.get(sid)
        if not sig:
            continue
        cat = category_of_method((sig.get("compute") or {}).get("method"))
        if cat:
            found.add(cat)
    for cat in PRECEDENCE:
        if cat in found:
            return cat
    return None


def unclassified_methods(registry):
    """Layer-1 compute methods the partition does not cover — a gate, not a report."""
    return sorted({
        (s.get("compute") or {}).get("method")
        for s in registry.values()
        if s.get("layer") == 1 and (s.get("compute") or {}).get("method")
    } - set(METHOD_CATEGORY))
