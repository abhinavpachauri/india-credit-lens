#!/usr/bin/env python3
"""
state_lines.py — the standing state of a dashboard dimension, in two sentences
──────────────────────────────────────────────────────────────────────────────
`DASHBOARD_SPEC.md` §16. The read tier answers *what is news*; this answers
*what is happening*, which is a different question and has no answer on the
dashboard today. Twenty-nine of ninety-six SIBC cards score as reads in a good
month, and none at all in a quiet one — so a reader arriving between events is
handed a directory.

Two sentences per cut, rendered every period whether or not anything moved:

    speed   Industry credit growing 20.0% YoY, accelerating.
    mix     Drifting toward Medium — it took 14.0% of the new industry credit
            while holding 9.2% of the total. Away from Large.

The pair is the point. **speed is Layer 1** — how fast the parent is growing,
straight off its own registered YoY signal. **mix is Layer 2** — the mix state
`generate_system_state` has computed every ingestion since August and which has
never reached a browser. Read together they separate *where the money went* from
*whether that changed the shape of the book*, and that distinction is invisible
in any single card: "Large took 60.8% of all new industry credit" is a record,
and the same window is drifting AWAY from Large, because 60.8% of the flow is
less than its 68.6% of the stock.

Three rules this module exists to keep:

* **Every number is a stored row.** The tilt is never printed as a pp figure —
  it is a subtraction, and no gate can ground a subtraction. Its two operands
  are stored, so the sentence quotes those instead, which is both checkable and
  plainer English. Coherence is never printed at all (the regime word carries
  it); it lives in a state file, not signals.db, and invented values have passed
  the gate before.
* **An absent input renders nothing.** Priority Sector is a memo lens with no
  total, so it has no speed line. A missing input never becomes a placeholder,
  a zero, or a neighbour's number.
* **A dominated aggregate is attributed, not published bare.** POS terminals
  reads -15.8% YoY, ~98% of it one issuer's reclassification. A card publishes
  that once; a STANDING line would publish it every month forever, so the speed
  clause routes through the same `signals/dominance.py` guard the cards use.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, asdict

from core.relational_insights import _pct, _short
from signals.dominance import RATIO_DENOMINATOR, SCAN_FOR, move_dominance, short_entity

# The band that counts as "the pace changed", in percentage points of YoY. Deliberately the
# same 0.5 pp the movement family's ACCEL_DEFAULT_RULES uses to call a sector strengthening or
# weakening — one definition of a changed pace across the platform, not two that agree today.
PACE_BAND_PP = 0.5


@dataclass(frozen=True)
class RateOnlyCut:
    """A dashboard dimension that has a parent RATE but no mix to state.

    Bank Credit is the whole book: the only split at that level is food vs non-food, which is
    an accounting distinction rather than a mix anyone steers. It still has the most-quoted
    growth rate on the site, and leaving the dimension with no band at all made the band look
    like a feature of some sections — which is the opposite of standing furniture.
    """
    section: str
    parent_yoy: str
    parent_label: str
    no_mix_note: str
    subject: str = ""
    slug: str = ""
    no_speed_note: str | None = None


@dataclass(frozen=True)
class StateBlock:
    """One cut's standing state, ready to render. `speed`/`mix` are None where the
    cut has no such input — the band drops the line rather than inventing one."""
    dimension: str            # the dashboard section/group id this belongs to
    cut: str                  # the cut slug, so a dimension carrying two can tell them apart
    subject: str              # "Industry credit" — the block heading when a dimension has >1 cut
    speed: str | None
    # The tile form of the same reading: "20.0% YoY · accelerating". Rendered HERE and not
    # parsed out of `speed` in the browser — it carries a number, so it has to be a string
    # the gate scans, and a regex over our own prose is a formatter wearing a disguise.
    speed_short: str | None
    speed_dir: str | None     # "up" | "down" — the tile glyph, from the SIGN of the rate
    mix: str | None
    # Why a line is absent, when it is. The band always renders both rows; an empty one carries
    # the reason instead of a number, so a reader never has to wonder whether it broke.
    no_speed_note: str | None
    no_mix_note: str | None
    mix_state: str | None     # the regime word, for the compact tile form
    toward: str | None        # the destination, shortened for display
    # The destination's RAW signals.db entity id. Display trims RBI's parenthetical
    # qualifiers, and the gate needs the name the rows are actually keyed on so it can
    # scope this block's ground truth to the one entity the sentence names.
    toward_entity: str | None
    source_signals: list[str] # what the gate scopes this block's numbers to

    def as_dict(self) -> dict:
        return asdict(self)


# ── speed · Layer 1 ───────────────────────────────────────────────────────────

def _yoy_series(conn, pipeline: str, sid: str) -> list[tuple[str, float]]:
    """The signal's own scalar series, oldest first. A YoY signal writes one
    aggregate/total row per period, which is the convention every roll-up in
    this codebase keys on."""
    return list(conn.execute(
        "SELECT period, value FROM signals WHERE pipeline=? AND metric_id=? "
        "AND entity_type='aggregate' AND entity_id='total' ORDER BY period",
        (pipeline, sid)))


def _pace(series: list[tuple[str, float]]) -> str | None:
    """Whether the growth rate itself is moving, from the signal's own last two
    readings. Derived here rather than read off the movement family's acceleration
    row because that row is keyed to the momentum signal's parent code, which is
    absent for two cuts — and a clause that appears for one industry cut and not
    the other reads as a finding when it is a lookup gap."""
    if len(series) < 2:
        return None
    delta = series[-1][1] - series[-2][1]
    if delta > PACE_BAND_PP:
        return "accelerating"
    if delta < -PACE_BAND_PP:
        return "slowing"
    return "steady"


def speed_line(conn, pipeline: str, period: str, parent_yoy: str | None,
               parent_label: str) -> tuple[str, str, str, list[str]] | None:
    """`{Parent} growing 20.0% YoY, accelerating.`, its tile form, and the direction of the
    rate — or None when the cut has no parent-level signal to speak for it.

    The direction is returned rather than left to the renderer because the tile marks it with
    a glyph, and a glyph inferred from a sentence is a glyph that says ▲ next to -15.8%."""
    if not parent_yoy:
        return None
    series = [(p, v) for p, v in _yoy_series(conn, pipeline, parent_yoy) if p <= period]
    if not series or series[-1][0] != period:
        return None
    value = series[-1][1]

    # A single entity's reporting change can own the whole aggregate move. Attribute it in
    # the sentence rather than suppressing the number — the figure is real, the market
    # reading is not. Same wording as the card-level guard, so the two cannot drift apart.
    if parent_yoy in SCAN_FOR or parent_yoy in RATIO_DENOMINATOR:
        dom = move_dominance(pipeline, parent_yoy, period, conn=conn)
        if dom and dom.dominant:
            entity = short_entity(dom.top_entity) or "one issuer"
            return (f"{parent_label} at {_pct(value)} YoY — but it's {entity}, "
                    f"not the market.",
                    f"{_pct(value)} YoY · {entity}, not the market",
                    "down" if value < 0 else "up", [parent_yoy])

    # SIGNED, always. "shrinking 15.8%" reads more naturally than "at -15.8%", and it is
    # exactly what the traceability stage rejected on its first run: the stored row is
    # -15.8269, so the unsigned figure traces to nothing. Direction lives in the verb AND
    # in the number, which is the only version a gate can check.
    if value < 0:
        return (f"{parent_label} at {_pct(value)} YoY, contracting.",
                f"{_pct(value)} YoY · contracting", "down", [parent_yoy])
    pace = _pace(series)
    # Phrased to work for a plural subject too: "Personal loans ... holding ITS pace" is
    # the kind of error a template written against one example ships.
    tail = {"accelerating": ", accelerating", "slowing": ", but slowing",
            "steady": ", at a steady pace"}.get(pace, "")
    return (f"{parent_label} growing {_pct(value)} YoY{tail}.",
            f"{_pct(value)} YoY" + (f" · {pace}" if pace and pace != "steady" else ""),
            "up", [parent_yoy])


# ── mix · Layer 2 ─────────────────────────────────────────────────────────────

def mix_line(conn, pipeline: str, period: str, alloc_sid: str, mom_sid: str,
             mix: dict) -> tuple[str, list[str]] | None:
    """The mix state as a sentence. `steered` and `drifting` name the destination and
    quote the two stored rows whose DIFFERENCE is the tilt — the tilt itself is never
    printed, because a subtraction traces to nothing.

    The sentence names no subject at all. It used to, and a band then carried two names
    for one parent four lines apart ("non-food credit" in the speed line, "bank credit"
    here) — which for the main cut are not even synonyms. Saying "of the growth" instead
    is shorter, unambiguous, and leaves exactly one name per band.
    """
    state = (mix or {}).get("mix_state")
    if not state:
        return None
    if state == "contested":
        return ("Contested — parts are moving in opposite directions, with no single "
                "destination."), []
    if state == "reallocating":
        return "Reallocating — gains and losses very nearly cancel.", []

    toward, away = mix.get("toward"), mix.get("away_from")
    if not toward:
        return None
    rows = {et: {e: v for e, v in conn.execute(
        "SELECT entity_id, value FROM signals WHERE pipeline=? AND period=? "
        "AND metric_id=? AND entity_type=?", (pipeline, period, alloc_sid, et))}
        for et in ("alloc", "weight")}
    a, w = rows["alloc"].get(toward), rows["weight"].get(toward)
    if a is None or w is None:
        return None
    # Growth or contraction is read off the stored net, never assumed — a coherent cut can
    # be one in which every part is shrinking, and "took 25% of the growth" would then be
    # the exact inversion of what happened. The contested branch of the movement family
    # learned this the hard way on POS terminals.
    net = next((v for (v,) in conn.execute(
        "SELECT value FROM signals WHERE pipeline=? AND period=? AND metric_id=? "
        "AND entity_type='aggregate' AND entity_id='total'", (pipeline, period, mom_sid))), None)
    noun = "contraction" if (net is not None and net < 0) else "growth"
    verb = "Steered" if state == "steered" else "Drifting"
    # "a year ago" is NOT decoration. `weight` is the share at the START of the window, and
    # the §17 table beside this line shows the share TODAY (`weight_now`). Unqualified, the
    # band said NBFCs hold 31.1% while the table under it said 34.3% — both true, and read
    # together a contradiction. A number whose date is implicit is a number that will be
    # read against the wrong one.
    line = (f"{verb} toward {_short(toward)} — it took {_pct(a)} of the {noun} "
            f"while holding {_pct(w)} of the total a year ago.")
    if away:
        line += f" Away from {_short(away)}."
    return line, [alloc_sid, mom_sid]


# ── the band ──────────────────────────────────────────────────────────────────

def blocks(conn, pipeline: str, period: str, cuts, prefix,
           mix_states: dict, rate_only=()) -> list[StateBlock]:
    """Every cut's state block for one pipeline, in the cut table's own order.

    `cuts` is the pipeline's `MOVEMENT_CUTS` — the same table that already decides
    which movement cards exist, so a new cut gains a state block by being declared
    once and nothing else. A cut with neither a speed nor a mix produces no block:
    an empty band is worse than no band.

    `prefix` is a string where a pipeline's signal ids share one stem (SIBC: "sibc-")
    or a section→stem mapping where they do not (payments names its three cuts
    "cc-"/"dc-"/"pos-"). Both forms are what the generators already hold, so neither
    pipeline has to keep a second copy of the same fact.
    """
    stem = (lambda c: prefix) if isinstance(prefix, str) else (lambda c: prefix[c.section])
    out: list[StateBlock] = []
    for cut in [*cuts, *rate_only]:
        if isinstance(cut, RateOnlyCut):
            sp = speed_line(conn, pipeline, period, cut.parent_yoy, cut.parent_label)
            if sp is None:
                continue
            out.append(StateBlock(
                dimension=cut.section, cut=cut.section, subject=cut.parent_label,
                speed=sp[0], speed_short=sp[1], speed_dir=sp[2],
                mix=None, no_speed_note=None, no_mix_note=cut.no_mix_note,
                mix_state=None, toward=None, toward_entity=None, source_signals=sp[3]))
            continue
        mom_sid = f"{stem(cut)}{cut.slug}-momentum"
        alloc_sid = f"{stem(cut)}{cut.slug}-allocation"
        sp = speed_line(conn, pipeline, period, cut.parent_yoy, cut.parent_label or cut.subject)
        mx = mix_line(conn, pipeline, period, alloc_sid, mom_sid, mix_states.get(mom_sid, {}))
        if sp is None and mx is None:
            continue
        mix = mix_states.get(mom_sid, {})
        out.append(StateBlock(
            dimension=cut.section,
            cut=cut.slug,
            subject=(cut.parent_label or cut.subject)[0].upper() + (cut.parent_label or cut.subject)[1:],
            speed=sp[0] if sp else None,
            speed_short=sp[1] if sp else None,
            speed_dir=sp[2] if sp else None,
            mix=mx[0] if mx else None,
            no_speed_note=None if sp else cut.no_speed_note,
            no_mix_note=None if mx else cut.no_mix_note,
            mix_state=mix.get("mix_state"),
            toward=_short(mix["toward"]) if mix.get("toward") else None,
            toward_entity=mix.get("toward") if mx else None,
            source_signals=sorted({*(sp[3] if sp else []), *(mx[1] if mx else [])}),
        ))
    return out
