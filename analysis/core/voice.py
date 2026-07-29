#!/usr/bin/env python3
"""
voice.py — the platform's reader-facing voice, defined once (DISTRIBUTION_SPEC §11.2-R1)
------------------------------------------------------------------------------------------
Every surface that speaks to a reader — the two monthly issues, the LinkedIn blurbs, the
deep read, and the LLM-sourced bank "why" — has to sound like the same person: plain Indian
conversational English, short sentences, lakh/crore never million/billion, no consulting
register, no advice or forecast in the machine's own words, and understandable by someone
with basic lending experience and no analyst jargon.

Before this, those rules lived in three places (`slot_render`, `validate_distribution`,
`relational_insights`) and drifted. This is the single home. Two things live here:

  1. `lint(text)` / `direction_conflict(text)` — the checks, so every generator and gate
     asks the same questions of its prose. `validate_distribution` and the slot renderer
     call these; they no longer keep their own copies.
  2. A small kit of conversational builders — `observed_dir`, `moved`, `pp_gap`, `oxford`
     — so a *gated fact* becomes a plain sentence the same way everywhere. The numbers stay
     the caller's (scoped, traceable); the voice is shared.

The voice does NOT ground numbers (that stays `core.traceability`) and does NOT measure
itself (that stays `measure_groundedness`). It sits beside them.
"""
import re
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

from distribution import slot_render   # SEBI/compliance lint + the BANNED register  # noqa: E402

# The consulting register the reader voice avoids. Owned by slot_render historically; kept
# there so the LinkedIn path is untouched, imported here so there is one list, not two.
BANNED = slot_render.BANNED

# Advice — telling the reader what to DO. Analysis states what is; the prescriptive call is
# the editor's (the handwritten layer), never the machine's own words.
_ADVICE = re.compile(r"\b(?:should(?:\s+not)?|must(?:\s+not)?|need to|ought to|"
                     r"focus on|prepare for|watch for|allocate|treat this as)\b", re.I)
# Forecast — a claim about the future. The reads are backward-looking; the machine does not
# predict.
_FORECAST = re.compile(r"\b(?:will\s+(?:continue|keep|likely|remain|widen|persist)|"
                       r"on track to|set to|poised to|expected to|going to|"
                       r"through fy\d{2}|next (?:quarter|few quarters|year)|coming months)\b", re.I)
# Millions/billions or M/K/B — this platform speaks lakh and crore. "L"/"L Cr" (lakh crore)
# is what we want, so it is excluded.
_BIGUNIT = re.compile(r"\b\d+(?:\.\d+)?\s?(?:million|billion|mn|bn)\b|"
                      r"(?<![A-Za-z])\d+(?:\.\d+)?[MKB]\b")


def lint(text):
    """Every §10 voice problem in one string: SEBI/compliance + banned register + advice +
    forecast + unit voice. Returns a list of human-readable problems ([] = clean). Callers
    decide whether a hit hard-fails (our own words) or warns (verbatim card/quoted prose)."""
    problems = list(slot_render.lint_compliance(text))
    low = text.lower()
    for phrase in BANNED:
        if phrase in low:
            problems.append(f"banned register {phrase!r}")
    if _ADVICE.search(text):
        problems.append(f"advice voice: {_ADVICE.search(text).group(0)!r}")
    if _FORECAST.search(text):
        problems.append(f"forecast: {_FORECAST.search(text).group(0)!r}")
    for m in _BIGUNIT.finditer(text):
        problems.append(f"millions/M-K units — say it in lakh/crore: {m.group(0)!r}")
    return problems


# ── Word-vs-number agreement (a rate shown WITH its sign must not fight the word) ─────────
# Word-boundaried so bare "up"/"down" fire without tripping on "group"/"update"/"download".
_UP_RE = re.compile(r"↑|\b(?:accelerat\w*|strengthen\w*|gained|picked up|rose|higher|"
                    r"faster|up)\b", re.I)
_DOWN_RE = re.compile(r"↓|\b(?:slow\w*|declin\w*|fell|falling|gave up|lower|shrank|"
                      r"shrink\w*|down)\b", re.I)
# ONLY explicitly-signed rates: "fell 4.3%" is correct (the word carries the sign); the bug
# is a rate shown WITH its sign ("up, −2.6%") where the value itself contradicts the word.
_RATE = re.compile(r"(?<![A-Za-z\d])([-+])(\d+(?:\.\d+)?)\s?(?:%|pp)(?![A-Za-z])")


def _rate_signs(text):
    return [(-1 if m.group(1) == "-" else 1) for m in _RATE.finditer(text)
            if abs(float(m.group(2))) >= 0.05]


def direction_conflict(text):
    """A one-line description if this text's direction cue disagrees with its own signed
    rate, else None. E.g. 'up … −2.6%'."""
    up = bool(_UP_RE.search(text))
    down = bool(_DOWN_RE.search(text))
    if up == down:                                 # neither, or ambiguous both → no verdict
        return None
    signs = _rate_signs(text)
    if not signs:
        return None
    cue = 1 if up else -1
    if all(s != cue for s in signs):
        return (f"direction says {'up' if up else 'down'} but rate is "
                f"{'negative' if cue > 0 else 'positive'}: {text.strip()[:90]!r}")
    return None


# ── Conversational builders — a gated fact → a plain fragment, the same way everywhere ────

_WORD_DIR = {"rising": 1, "running": 1, "growing": 1, "expanding": 1, "up": 1,
             "falling": -1, "shrinking": -1, "contracting": -1, "unwinding": -1,
             "reversed": -1, "down": -1}


def observed_dir(value):
    """The direction the VALUE itself shows: +1/-1 from a single-signed number or a
    direction word, None when mixed (both signs) or directionless."""
    v = (value or "").strip().lower()
    if v in _WORD_DIR:
        return _WORD_DIR[v]
    signs = {(-1 if m.group(1) == "-" else 1) for m in re.finditer(r"([-+])\d", value or "")}
    return next(iter(signs)) if len(signs) == 1 else None


def moved(value_word_up="grew", value_word_down="fell", value_word_flat="held steady",
          *, direction):
    """The past-tense verb for a direction (+1/-1/0/None) — one place, so 'grew/fell/held'
    never drifts to 'increased/decreased' in one surface and not another."""
    return {1: value_word_up, -1: value_word_down}.get(direction, value_word_flat)


def oxford(items, conj="and"):
    """A plain list: 'a', 'a and b', 'a, b and c' — no serial comma, the way people write."""
    items = [str(i) for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return f"{', '.join(items[:-1])} {conj} {items[-1]}"


def plainly(sentence):
    """Prefix a restatement the way the reads do ('Put simply — …'), used when a line needs
    a second, simplest pass for a reader who skipped the detail."""
    return f"Put simply — {sentence}"
