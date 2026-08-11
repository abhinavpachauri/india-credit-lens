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
