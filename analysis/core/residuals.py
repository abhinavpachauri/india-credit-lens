#!/usr/bin/env python3
"""
residuals.py — RBI's catch-all buckets, and what a card may say about them
──────────────────────────────────────────────────────────────────────────
RBI closes most of its cuts with a bucket for whatever it does not classify:
"Others" in chemicals, "Other Personal Loans", "Other Services". These are
residuals, not sectors. A residual has no behaviour of its own — it moves when
the named blocks are reclassified as readily as when anything real happens — so
reading one as a sector is reading noise as a signal.

The rule was already written down, in `_is_residual`'s docstring:

    "It is a residual, not a sector, so it must never headline a leaderboard
     ('Others is the biggest slice of X'). When it is large, the real signal is
     a classification gap, not a composition read."

It matched the literal words "others"/"other", so it fired on three of the nine
catch-alls in the SIBC data and not on the six with a noun after "Other" —
including the two largest, Other Personal Loans (₹17.7L Cr) and Other Services
(₹12.5L Cr). "Other Textiles is the biggest slice of textiles credit at 45.5%"
was live: the exact sentence the docstring forbids.

Detection is STRUCTURAL, not a list to maintain
───────────────────────────────────────────────
A catch-all is an entity RBI names with its catch-all convention AND never
breaks down. Measured over every entity in the consolidated CSV: 9 of 9 "Other…"
entities are leaves in all 21 periods, and no other leaf is a catch-all. So the
two conditions together identify the set exactly, and a new source inherits the
rule rather than a hand-kept list of names.

Consequence scales with what is unclassified
────────────────────────────────────────────
Binary would be wrong in both directions. Payments' "Other Transactions" is
0.62% of credit-card volume — caveating it would be noise. Engineering's
"Others" is 79.2% — the classification gap IS the story. `materiality` reports
the share so callers can say something proportionate, and `leads` answers the
one question that is never a matter of degree: may this block headline?
"""
from __future__ import annotations

import csv
import re
from functools import lru_cache

from core.manifest import consolidated_csv

# RBI's convention: "Others", "Other Personal Loans", "Other Metal and Metal Product".
# Anchored, so "Loans against gold jewellery" and "Wholesale Trade" are untouched.
_CATCH_ALL_NAME = re.compile(r"^others?\b", re.I)


def named_like_a_catch_all(name: str) -> bool:
    """Half the test — the naming convention alone. Public so the gate can report
    a name that looks like a catch-all but is broken down (which would mean RBI
    changed something, and the structural half should be trusted over the name)."""
    return bool(_CATCH_ALL_NAME.match((name or "").strip()))


@lru_cache(maxsize=None)
def catch_alls(pipeline: str = "sibc") -> frozenset[str]:
    """Every catch-all in this pipeline's data, by the name the signals use.

    Structural: named by the convention AND childless in every period. A bucket
    RBI starts breaking down stops being a residual on its own, without an edit
    here — which is the point of deriving it rather than listing it.
    """
    if pipeline != "sibc":
        return frozenset()          # payments has no hierarchy to close
    rows = list(csv.DictReader(open(consolidated_csv(pipeline))))
    parents = {r["parent_code"] for r in rows if r["parent_code"]}
    return frozenset(
        r["sector"] for r in rows
        if named_like_a_catch_all(r["sector"]) and r["code"] not in parents
    )


def is_catch_all(name: str, pipeline: str = "sibc") -> bool:
    """Is this entity a remainder rather than a sector?"""
    return (name or "").strip() in catch_alls(pipeline)


def kind(name: str, pipeline: str = "sibc") -> str | None:
    """Which sort of remainder — the distinction the prose has to respect.

    pure              named exactly "Others"/"Other". Tells you nothing about what
                      is inside it; the honest read is a classification gap.
    named_remainder   "Other Textiles", "Other Personal Loans". Still a remainder
                      RBI does not break down, but the noun says what it holds —
                      textiles that are not cotton, jute or man-made.

    Both are barred from headlining a leaderboard, because "the biggest slice" is
    a claim about blocks and neither is one. Only `pure` earns the word
    "unclassified": calling Other Textiles unclassified would be less accurate
    than what the card says today, not more.
    """
    if not is_catch_all(name, pipeline):
        return None
    return "pure" if (name or "").strip().lower() in {"others", "other"} else "named_remainder"


def materiality(dist: list[tuple], pipeline: str = "sibc") -> tuple[str, float] | None:
    """The catch-all in this distribution and the share it holds, or None.

    `dist` is the ranked [(entity, value, status)] a scan produces. For a share
    scan the value IS the share; callers with a growth scan pass the matching
    share distribution, because how fast a residual grew says nothing about how
    much of the cut is unreadable.
    """
    for entity, value, *_ in dist:
        if is_catch_all(entity, pipeline):
            return entity, value
    return None


def leads(dist: list[tuple], pipeline: str = "sibc") -> bool:
    """Would a leaderboard built from this distribution headline a residual?

    The one consequence that is not a matter of degree: "Other Textiles is the
    biggest slice of textiles credit" is a false sentence at any share, because
    it names a bucket as though it were a block.
    """
    return bool(dist) and is_catch_all(dist[0][0], pipeline)


def named_only(dist: list[tuple], pipeline: str = "sibc") -> list[tuple]:
    """The distribution with the residual removed — what can be read as sectors."""
    return [d for d in dist if not is_catch_all(d[0], pipeline)]
