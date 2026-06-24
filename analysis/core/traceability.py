#!/usr/bin/env python3
"""
core/traceability.py — the shared number-core for insight traceability (§4 P1 batch 5).

Both pipelines enforce the same rule: every number a card states must trace to a value the
signals actually produced. The *mechanics* of pulling numbers out of prose and deciding
whether a number "matches" a grounded value were DUPLICATED in two validators
(validate_sibc_traceability, validate_atm_pos_insights) with small but real divergences.
This module de-duplicates that core and makes the divergences explicit as a `NumberPolicy`,
rather than two drifting copies.

The two policies are NOT interchangeable — they encode genuinely different choices that the
golden tests (tests/test_traceability.py, tests/test_traceability_atm_pos.py) pin:

  • SIBC: strips structural tokens (ISO dates / FY labels / quarters / calendar years) before
    matching; no magnitude suffixes; looser tolerances (2% / 0.25); ratio grounding includes
    percent-of-total (100*A/B) over de-duplicated levels > 1.
  • ATM/POS: no structural stripping (templated prose); scales B/M/K and strips x/%; tighter
    tolerances (0.5% / 0.6); ratio grounding is plain A/B (round or rel) over the raw value
    list, no percent-of-total.

`matches` is identical logic across both — only the tolerances differ.
"""
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class NumberPolicy:
    rel_tol: float            # relative tolerance for matches() (formatted text rounds)
    abs_tol: float            # absolute fallback tolerance (small values / shares / near-0)
    min_check: float          # ignore |value| below this (trivial small integers)
    strip_structural: bool    # pre-strip ISO dates / FY / quarters / years (SIBC)
    handle_suffixes: bool     # scale B/M/K, strip x/% (ATM/POS)
    forbid_digit_prefix: bool # lookbehind excludes a preceding digit too (SIBC), not just letters
    ratio_percent_of_total: bool  # ratio grounding tries 100*A/B over de-duped levels>1 (SIBC)


SIBC = NumberPolicy(
    rel_tol=0.02, abs_tol=0.25, min_check=0.5,
    strip_structural=True, handle_suffixes=False,
    forbid_digit_prefix=True, ratio_percent_of_total=True,
)

ATM_POS = NumberPolicy(
    rel_tol=0.005, abs_tol=0.6, min_check=0.5,
    strip_structural=False, handle_suffixes=True,
    forbid_digit_prefix=False, ratio_percent_of_total=False,
)


def _pattern(policy: NumberPolicy) -> str:
    lookbehind = r"(?<![A-Za-z\d])" if policy.forbid_digit_prefix else r"(?<![A-Za-z])"
    suffix = r"(?:[BMKx%])?" if policy.handle_suffixes else r""
    return lookbehind + r"[-+]?\d+(?:\.\d+)?" + suffix + r"(?![A-Za-z\d])"


def extract_numbers(text: str, policy: NumberPolicy) -> list[float]:
    """Standalone numeric values from prose, per the pipeline's policy.

    SIBC strips structural tokens (ISO dates / FY / quarters / years) that are not data
    claims; ATM/POS scales magnitude suffixes (B/M/K) and strips x/%. A decimal glued to a
    trailing letter backtracks to its integer part (a quirk both pipelines share and pin)."""
    t = text
    if policy.strip_structural:
        t = re.sub(r"\b20\d\d-\d\d-\d\d\b", " ", t)                              # ISO dates
        t = re.sub(r"\bFY\s?\d{2,4}(?:\s?[-/–]\s?\d{2,4})?\b", " ", t, flags=re.I)  # FY25 / FY22-24
        t = re.sub(r"\b[Qq][1-4]\b", " ", t)                                    # quarters
        t = re.sub(r"\b(?:19|20|21)\d{2}\b", " ", t)                            # calendar years

    out: list[float] = []
    for m in re.finditer(_pattern(policy), t):
        g = m.group()
        if policy.handle_suffixes:
            raw = g.rstrip("BMKx%+")
            try:
                v = float(raw)
            except ValueError:
                continue
            if g.endswith("B"):
                v *= 1e9
            elif g.endswith("M"):
                v *= 1e6
            elif g.endswith("K"):
                v *= 1e3
        else:
            try:
                v = float(g)
            except ValueError:
                continue
        if abs(v) >= policy.min_check:
            out.append(v)
    return out


def matches(num: float, cands, policy: NumberPolicy) -> bool:
    """True if num equals a grounded candidate within the policy's tolerances. Identical
    logic across pipelines — only rel_tol/abs_tol differ."""
    for v in cands:
        if v == 0:
            if abs(num) < policy.abs_tol:
                return True
        else:
            if abs(num - v) / max(abs(v), 1e-9) <= policy.rel_tol:
                return True
            if abs(num - v) <= policy.abs_tol:
                return True
    return False


def ratio_matches(num: float, cands, policy: NumberPolicy) -> bool:
    """True if num is a ratio of two grounded values.

    SIBC (ratio_percent_of_total): a share or quotient — 100*A/B or A/B — over the distinct
    level set (|v|>1), bounded to avoid spurious matches.
    ATM/POS: a plain quotient A/B (matched rounded-by-abs or by rel) over the raw value list,
    requiring at least two values."""
    if policy.ratio_percent_of_total:
        levels = sorted({round(v, 4) for v in cands if abs(v) > 1})
        for a in levels:
            for b in levels:
                if b and a != b:
                    for c in (100 * a / b, a / b):
                        if abs(num - c) <= policy.abs_tol or \
                           abs(num - c) / max(abs(c), 1e-9) <= policy.rel_tol:
                            return True
        return False

    if len(cands) < 2:
        return False
    for a in cands:
        for b in cands:
            if b != 0 and a != b:
                ratio = a / b
                if abs(num - round(ratio)) <= policy.abs_tol:
                    return True
                if abs(num - ratio) / max(abs(ratio), 1e-9) <= policy.rel_tol:
                    return True
    return False
