"""
compute/common.py — the parts of signal computation that no pipeline owns
--------------------------------------------------------------------------
`sibc.py` and `atm_pos.py` know their own CSV: its date column, its entity hierarchy, what a
"sector" or a "bank" is. That knowledge is properly per-pipeline and should stay there.

What is NOT per-pipeline is the arithmetic they happen to share. Two functions had been
copy-pasted between them — `_eval_status` byte-for-byte identical, and the streak-counting
loop differing only in what it compares. They agreed today and could drift tomorrow, which is
exactly the "parallel copies" the platform's first principle forbids. They live here now, so a
third pipeline inherits them instead of copying them a third time.
"""
from __future__ import annotations

import calendar
from datetime import date
from typing import Callable, Sequence


def eval_status(rules: list, value: float, prev: float) -> str:
    """Apply a registry signal's declared status_rules to a computed value.

    Rules are ordered and the first match wins; `{"if": "true"}` is the catch-all. A rule's
    condition is a tiny Python expression over `value` and `prev_value` ("value > prev_value",
    "value >= 3") evaluated with builtins stripped — status rules are configuration authored
    in the registry, not user input.

    Moved here verbatim from the two compute modules, where it was byte-identical. Behaviour
    is deliberately unchanged: this is the function that decides every signal's status, and
    every stored status in signals.db was produced by it.
    """
    if value is None:
        return "unknown"
    ctx = {"value": value, "prev_value": prev if prev is not None else value}
    for rule in rules:
        cond = rule["if"]
        if cond == "true":
            return rule["then"]
        try:
            if eval(cond, {"__builtins__": {}}, ctx):   # noqa: S307
                return rule["then"]
        except Exception:
            continue
    return "unknown"


def row(entity_type: str, entity_id: str, value, status: str, unit: str) -> dict:
    """One computed signal row, as it is stored.

    Both modules defined this identically — the 65% text similarity between them was purely
    whitespace. It is the shape every signal in signals.db takes, so it belongs in one place:
    a rounding difference between the two would be a rounding difference between the two
    dashboards.
    """
    return {
        "entity_type": entity_type,
        "entity_id":   entity_id,
        "value":       round(float(value), 4) if value is not None else None,
        "status":      status,
        "unit":        unit,
    }


def count_streak(dates: Sequence[str], end_idx: int, holds: Callable[[int], bool]) -> int:
    """How many consecutive periods, counting back from `end_idx`, satisfy `holds`.

    `holds` takes a position in `dates` and answers whether the condition held *at* that
    period. What the condition compares — a YoY rate, a month-on-month level — is the
    caller's business; the walk backwards is not.
    """
    streak = 0
    for i in range(end_idx, -1, -1):
        if not holds(i):
            break
        streak += 1
    return streak


def prior_year(period: str, available: set[str]) -> str | None:
    """The same month one year earlier, or None if that period was never ingested.

    Both pipelines walk to the year-ago month-end the same way, so they shared this by
    copy-paste. Year-on-year is the backbone of nearly every signal; the two copies agreeing
    was luck rather than design.
    """
    d = date.fromisoformat(period)
    py = d.year - 1
    last_day = calendar.monthrange(py, d.month)[1]
    target = f"{py}-{d.month:02d}-{last_day:02d}"
    return target if target in available else None


def rotation_rows(cur_shares: list[dict], prior_shares: list[dict],
                  rules: list) -> list[dict]:
    """Δshare_pp per entity between two share-scan snapshots, plus the aggregate
    "rotation mass" row (Σ|Δ|/2 — the share of the mix that actually moved).

    Entities must appear in BOTH snapshots to rotate: something that only exists in one of
    them has no Δ, it has an arrival or a departure, which is a different fact.

    This was duplicated verbatim in both compute modules — identical but for one docstring
    line. Rotation is a claim about how a mix shifted; two copies of that arithmetic is two
    chances for the credit and payments dashboards to mean different things by the same word.
    """

    prior = {r["entity_id"]: r["value"] for r in prior_shares
             if r["value"] is not None}
    out = []
    for r in cur_shares:
        eid = r["entity_id"]
        if r["value"] is None or eid not in prior:
            continue
        delta = r["value"] - prior[eid]
        out.append(row(r["entity_type"], eid, delta,
                       eval_status(rules, delta, delta), "pp"))
    if not out:
        return []
    out.sort(key=lambda r: r["value"], reverse=True)
    mass = sum(abs(r["value"]) for r in out) / 2
    out.append(row("aggregate", "total", mass, "active", "pp"))
    return out
