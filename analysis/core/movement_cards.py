#!/usr/bin/env python3
"""
movement_cards.py — one movement reading per cut, for any pipeline
───────────────────────────────────────────────────────────────────
The movement family answers where new volume went, how fast the destination is
growing, and whether that pace is picking up. Four signals produce ONE card:
emitting them separately would say one thing four times on a dashboard that
already renders too many.

The rows behind it are pipeline-shaped identically — momentum with its
`aggregate` total/gross_movement/coherence, allocation split into
alloc/contribution/weight, acceleration and a speed scan per entity — because
both pipelines compute them through the same engine. Only the naming of the
signals and the shape of the card differ. So the reading is assembled here and
each generator wraps it in its own card, rather than the SIBC builder being
copied into the payments one.

The pairing rule lives here too, in `movement_insight`: a share of new volume is
never rendered without that entity's speed and acceleration, because a falling
share published alone reads as decline when the entity may simply have grown
more slowly than its peers.
"""
from __future__ import annotations

from dataclasses import dataclass

from core.relational_insights import movement_insight


@dataclass(frozen=True)
class MovementCut:
    """One dashboard dimension's movement card.

    Adding a cut is a row in a pipeline's table plus its registry entries — no new
    code, which is the property that let this widen from one SIBC cut to seven.
    """
    slug:    str    # signal-id stem: "{pipeline-prefix}-{slug}-{momentum|acceleration|allocation}"
    section: str    # the dashboard section/group the card belongs to
    speed:   str    # the YoY scan that satisfies the pairing rule
    subject: str    # the noun the prose adds to: "…of all new {subject}"


# The row types a movement signal writes ALONGSIDE its members. `aggregate` carries
# total/gross_movement/coherence; allocation splits into alloc/contribution/weight.
_NON_MEMBER = ("aggregate", "alloc", "contribution", "weight", "pair_side", "fy_yoy")

# The compute methods this module OWNS. A signal computed by one of these is rendered as part of
# the single movement card for its cut — never on its own — so the generic annotation path must
# skip it. Stated here, beside the reader, so the two cannot drift into different opinions about
# which signals belong to the family.
#
# Why this is a list and not a substring test: `csv_sector_fy_acceleration` is a DIFFERENT family
# (the FY step-up cards) that legitimately publishes on its own, and "acceleration" in a name is
# not membership.
MOVEMENT_METHODS = (
    "csv_sector_momentum",   "csv_sector_acceleration",   "csv_sector_allocation",
    "csv_category_momentum", "csv_category_acceleration", "csv_category_allocation",
)


def _member_type(conn, pipeline: str, period: str, metric_id: str) -> str | None:
    """The entity type this signal's MEMBER rows carry — sectors, bank categories, whatever
    a future source calls its parts. Discovered, so a new pipeline needs no vocabulary here."""
    row = conn.execute(
        "SELECT entity_type FROM signals WHERE pipeline=? AND period=? AND metric_id=? "
        f"AND entity_type NOT IN ({','.join('?' * len(_NON_MEMBER))}) LIMIT 1",
        (pipeline, period, metric_id, *_NON_MEMBER)).fetchone()
    return row[0] if row else None


def reading(conn, pipeline: str, period: str, registry: dict,
            cut: MovementCut, prefix: str) -> dict | None:
    """The rendered movement reading for one cut, or None when it has nothing to say.

    None is a real answer, not a failure: a window with no movement rows (the
    12-month lookback not yet available) has no card, by construction.
    """
    def rows(metric_id: str, entity_type: str) -> dict:
        return {e: v for e, v in conn.execute(
            "SELECT entity_id, value FROM signals WHERE pipeline=? AND period=? "
            "AND metric_id=? AND entity_type=?", (pipeline, period, metric_id, entity_type))}

    mom_sid   = f"{prefix}{cut.slug}-momentum"
    acc_sid   = f"{prefix}{cut.slug}-acceleration"
    alloc_sid = f"{prefix}{cut.slug}-allocation"

    # The member entity type is read off the ROWS, not off the registry. SIBC declares
    # `compute.entity_type` and its engine uses it; the payments engine writes
    # "bank_category" directly and reads no such field, so trusting the declaration would
    # mean trusting a description that only one pipeline actually keeps true. The rows are
    # what the compute wrote — the one description that cannot drift from itself.
    entity_type = _member_type(conn, pipeline, period, mom_sid)
    if not entity_type:
        return None
    momentum = rows(mom_sid, entity_type)
    if not momentum:
        return None

    agg      = rows(mom_sid, "aggregate")
    alloc    = rows(alloc_sid, "alloc")
    contrib  = rows(alloc_sid, "contribution")
    accel    = rows(acc_sid, entity_type)
    speed    = rows(cut.speed, _member_type(conn, pipeline, period, cut.speed) or entity_type)

    ins = movement_insight(alloc, contrib, momentum, agg.get("total"),
                           agg.get("gross_movement"), agg.get("coherence"),
                           accel, speed, cut.subject)
    if ins is None:
        return None

    return {
        "insight":   ins,
        # The entity the card leads with — allocation where the cut has it, momentum
        # otherwise (a contested window withholds `alloc` but keeps contribution).
        "lead":      max(alloc or momentum, key=(alloc or momentum).get),
        "alloc_sid": alloc_sid,
        # Declared reads. The card quotes a share beside a speed and an acceleration,
        # so the traceability gate scopes to exactly these four rather than falling
        # back to period-wide — the fallback is how a traceability gate quietly dies.
        "sources":   [alloc_sid, mom_sid, acc_sid, cut.speed],
    }
