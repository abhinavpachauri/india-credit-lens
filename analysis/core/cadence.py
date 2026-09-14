#!/usr/bin/env python3
"""
cadence.py — how often a signal's value can change

Every signal in the registry has assumed MONTHLY since the first one was written. Nothing
said so; it was simply true of both sources, so the assumption spread into prose ("16-period
range" meaning sixteen months), into streak counting (periods-as-months), and into the way a
window is described. The next sources are not monthly — the price-of-credit cluster is
fortnightly and quarterly, BSR-1 is quarterly, STRBI is annual — and an assumption that was
never written down cannot be found and corrected when it stops holding.

  **Cadence is how often the VALUE can change, not how often the source publishes.**

That distinction is the whole point, and it is why `compute.annual` already existed on the
FY-acceleration signals: RBI publishes them inside a monthly file, but the number is set once
a year at the March year-end, so describing a month-to-month move in it is describing noise.
An annual signal inside a monthly source is a real thing, and a field keyed to the publication
schedule would get it wrong.

`compute.annual` is kept as the compute spec's own input and this module derives from it, so
there is one name in the code and no second place to keep in step.
"""
from __future__ import annotations

# Ordered coarsest-last, so a comparison reads the way a reader expects.
CADENCES = ("fortnightly", "monthly", "quarterly", "half_yearly", "annual")

#: What one period IS, in months. Fortnightly is the exception the whole table exists for:
#: it is the only cadence finer than a month, and its window arithmetic cannot use months.
MONTHS_PER_PERIOD = {"fortnightly": 0.5, "monthly": 1, "quarterly": 3,
                     "half_yearly": 6, "annual": 12}

#: The word for one period, singular and plural — for prose that today says "month" because
#: every signal happened to be monthly.
PERIOD_WORD = {"fortnightly": ("fortnight", "fortnights"), "monthly": ("month", "months"),
               "quarterly": ("quarter", "quarters"), "half_yearly": ("half-year", "half-years"),
               "annual": ("year", "years")}


def of(signal: dict) -> str:
    """The cadence a signal declares, or the one its compute spec implies.

    A signal that declares nothing is monthly — which is what every signal written before this
    field existed actually is, verified rather than assumed when the field was backfilled.
    """
    declared = signal.get("cadence")
    if declared:
        return declared
    return "annual" if (signal.get("compute") or {}).get("annual") else "monthly"


def is_valid(cadence: str) -> bool:
    return cadence in CADENCES


def periods_in_a_year(cadence: str) -> float:
    """How many readings a year holds — the divisor a per-year rate needs."""
    return 12 / MONTHS_PER_PERIOD[cadence]


def window_months(periods: int, cadence: str) -> float:
    """The calendar span of N readings. A 12-period window is a year of monthly data and
    three years of quarterly data, and code that compares them without this is comparing two
    different questions."""
    return periods * MONTHS_PER_PERIOD[cadence]


def describe(n: int, cadence: str) -> str:
    """"16 months", "8 quarters" — a run of readings named in the reader's units rather than
    in "periods", which is the word a dashboard uses when it does not know."""
    one, many = PERIOD_WORD[cadence]
    return f"{n} {one if n == 1 else many}"
