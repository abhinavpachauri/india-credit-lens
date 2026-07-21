#!/usr/bin/env python3
"""
slot_render.py — one slate in, two artifacts out
--------------------------------------------------
DISTRIBUTION_SPEC §5: every slot emits a `design_prompt.md` and a `blurb.md`, and
neither is a finished post. Claude does not write the LinkedIn post; the design session
does not invent a number.

The design prompt is deliberately **closed**. It is the only surface on this platform
that leaves the gate — a fresh session with a browser and no ground truth is exactly
where a plausible-looking figure would come from. So the prompt hands over every number
it is allowed to use, verbatim, and forbids deriving any others. The same numbers also
go out as a machine-readable block, so the subset checker in §5.1 becomes a small job
later rather than a reformat.

The blurb is generated from templates, not written. Its numbers come from the claims,
which came from gate-validated feeds, so the traceability check has something to check.
Voice rules are §10 and `lint_blurb` enforces the parts of them a machine can see.
"""
import json
import re

from distribution import categories as cats

# §10 banned register. A blurb saying any of these has stopped sounding like a person.
BANNED = [
    "firing on all cylinders", "robust", "yield optimisation", "yield optimization",
    "unlock", "headwind", "tailwind", "poised to", "double down",
    "at an inflection point", "billion",
]

# SEBI guardrail — analytics language only, on every surface that leaves the building.
# Inherited from the retired reply desk (analysis/legacy/replydesk/), which held the
# only copy: this is a compliance control, not a style preference, and it must outlive
# whichever channel happened to introduce it. India Credit Lens publishes analysis; it
# does not give investment advice, and no generated artifact may imply otherwise.
SEBI_BANNED = [
    "buy", "sell", "target price", "price target", "accumulate", "book profit",
    "book profits", "multibagger", "go long", "go short", "stop loss", "stoploss",
    "entry price", "exit price", "upside", "downside target", "rerating", "re-rating",
    "undervalued", "overvalued", "cheap stock", "invest in", "add on dips",
]

# Openers per category — plain statements, never a rhetorical question (§10).
OPENERS = {
    "C1":  "{sibc_month} credit numbers are out.",
    "C2":  "Some shifts in who is gaining ground.",
    "C3":  "A few things that usually move together have come apart.",
    "C4":  "Looking at how widely this is spread.",
    "C5":  "A few things changed direction this month.",
    "C6":  "What this opens up, and what to watch.",
    "C7":  "Credit and payments data, read together.",
    "C8":  "{count} that could turn next month.",
    "C9":  "An earlier read of ours needs correcting.",
    "C10": "Notes from building this thing.",
}

COUNT_WORD = {1: "One", 2: "Two", 3: "Three", 4: "Four"}

CLOSERS = {
    "C1":  "Full breakdown on Substack.",
    "C6":  "Full deep read on Substack.",
    "C7":  "Full deep read on Substack.",
}
DEFAULT_CLOSER = "Charts and the full working are on indiacreditlens.com."

# What the pager should be shaped like, per category. Handed to the design session as
# the narrative arc so it composes rather than lists.
ARCS = {
    "C1":  "Open with the headline level, then the two or three numbers that qualify it. "
           "The reader should leave knowing the size and the direction, nothing more.",
    "C2":  "Show the mix moving: who gained share, who gave it up, and how much of the mix "
           "changed hands in total. A before/after of the same pie reads better than a bar chart.",
    "C3":  "Two lines that used to track each other, now apart. Show both lines and the gap "
           "between them. The gap is the subject, not either line.",
    "C4":  "Show the distribution, not the average — where the mass sits and how long the tail is.",
    "C5":  "Before and after. Each turn gets the same treatment: what it was, what it is now.",
    "C6":  "Lead with the opening or the risk itself, then the computed basis underneath it. "
           "The basis is the credibility, so give it room.",
    "C7":  "One panel per pipeline, then the join between them. The join is the whole point — "
           "neither half says this on its own.",
    "C8":  "A distance-to-the-line layout: current value, the threshold, and the gap between. "
           "Nearest first.",
    "C9":  "What we said, what it reads now, and why it moved. Plain and unhedged.",
    "C10": "One idea, one measurement, one takeaway a builder can reuse.",
}


def _numbers_block(claims):
    """Every number the design session is allowed to use, with where it came from."""
    supplied = []
    seen = set()
    for c in claims:
        for token in _number_tokens(" ".join(x for x in (c["title"], c["body"],
                                                         c.get("implication", "")) if x)):
            key = (token, c["id"])
            if key in seen:
                continue
            seen.add(key)
            supplied.append({"value": token, "claim": c["id"],
                             "signals": c.get("signal_ids", [])})
    return supplied


_NUM_TOKEN = re.compile(r"[₹]?-?\d[\d,]*\.?\d*\s?(?:%|pp|L Cr|Cr|lakh|crore|×)?")


def _number_tokens(text):
    """Numeric tokens as the reader sees them — with unit attached, so the design
    session copies '₹2.95L Cr', never a bare 2.95 it might re-unit."""
    text = re.sub(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* 20\d\d\b",
                  " ", text)
    out = []
    for m in _NUM_TOKEN.finditer(text):
        tok = m.group(0).strip()
        if re.search(r"\d", tok):
            out.append(tok)
    return out


SHARED_RULE = ("Use the wording as the source of truth for what is being said; you may "
               "shorten for the page, but you may not change a number or add a "
               "qualifier that is not here.")


def _provenance_note(claims):
    """Say where these words actually came from.

    A prompt whose whole job is "invent nothing" cannot itself be loose about
    provenance. Feed cards and generated sentences are both grounded, but they are
    grounded differently, and a slot can carry either or both.
    """
    verbatim = any(c.get("verbatim") for c in claims)
    generated = any(not c.get("verbatim") for c in claims)
    if verbatim and generated:
        origin = ("Some blocks below are verbatim from a gate-validated artifact; the "
                  "rest were written deterministically from signals.db. Both are checked.")
    elif verbatim:
        origin = "Each block below is verbatim from a gate-validated artifact."
    else:
        origin = ("Each block below was written deterministically from signals.db — the "
                  "wording is the generator's, the numbers are the database's.")
    return f"{origin} {SHARED_RULE}"


def design_prompt(slate):
    """The closed prompt pasted into a separate Claude design session (§5.1)."""
    cat = slate["category"]
    lines = [
        f"# Design prompt — {slate['date']} · {cats.label(cat)} ({cat})",
        "",
        f"**Slot:** {slate['slot']} of the month"
        + ("  ·  **this is the fallback category for this slot**" if slate.get("is_fallback") else ""),
        f"**Question this answers:** {cats.question(cat)}",
        f"**Data vintage:** {slate['vintage_sentence']}",
        f"**Pages:** {slate.get('pages', 1)}",
        "",
        "## The arc",
        "",
        ARCS.get(cat, ""),
        "",
        "## The claims",
        "",
        _provenance_note(slate["claims"]),
        "",
    ]
    for c in slate["claims"]:
        lines += [f"### {c['title']}", "", c["body"]]
        if c.get("implication"):
            lines += ["", f"*So what:* {c['implication']}"]
        lines += ["", f"<sub>source: {c['source']} · signals: "
                      f"{', '.join(c.get('signal_ids', [])) or '—'}</sub>", ""]

    supplied = _numbers_block(slate["claims"])
    lines += [
        "## The numbers you may use",
        "",
        "This is the complete set. Nothing outside it may appear on the pager.",
        "",
        "```json",
        json.dumps({"supplied_numbers": supplied}, indent=1, ensure_ascii=False),
        "```",
        "",
        "## Hard constraints",
        "",
        "- Use **only** the numbers listed above. Invent nothing.",
        "- Do **not** compute new figures from these numbers — no totals, no differences, "
        "no percentages of percentages, no annualising.",
        "- Do not look anything up. This prompt is the whole world for this pager.",
        "- Do not add forecasts, targets, or attributions to any policy or event.",
        "- Keep the data vintage line on the pager exactly as given above.",
        "- If something seems missing, leave it out rather than filling the gap.",
        "",
        f"<sub>generated by analysis/distribution/generate_slot.py · category {cat} · "
        f"{slate['date']}</sub>",
        "",
    ]
    return "\n".join(lines)


def _blurb_line(claim):
    """One claim, one line.

    A feed card's title is a written headline and stands alone. A generated claim's
    "title" is only the registry's name for the signal — "POS terminals YoY growth (%)"
    says nothing — so those use the sentence the generator wrote instead. A claim that
    knows better than either supplies its own `lede`: an opportunity's title is a label
    ("Gold loan market entry") that needs its first line of body to mean anything.
    """
    text = claim.get("lede") or (claim["title"] if claim.get("verbatim")
                                 else (claim["body"] or claim["title"]))
    return text.rstrip(". ") + "."


def blurb(slate):
    """The LinkedIn copy that goes with the pager (§5.2). Generated, per §10 voice."""
    cat = slate["category"]
    vintage = slate.get("vintage", {})
    sibc_month = (vintage.get("sibc") or {}).get("label", "")
    # The opener counts what is actually in the slate. Promising three things and
    # listing one is the sort of small dishonesty that costs more than the slot is worth.
    n = len(slate["claims"])
    opener = OPENERS.get(cat, "").format(
        sibc_month=f"RBI's {sibc_month}" if sibc_month else "The latest",
        count=f"{COUNT_WORD.get(n, str(n))} thing{'' if n == 1 else 's'}")

    parts = [opener, ""]
    for c in slate["claims"]:
        parts += [_blurb_line(c), ""]
    if slate.get("vintage_note"):
        parts += [slate["vintage_note"], ""]
    parts.append(CLOSERS.get(cat, DEFAULT_CLOSER))
    return "\n".join(parts).strip() + "\n"


# A number a machine printed rather than a person: a bare 7+ digit integer where §10
# asks for lakh/crore, or a float that kept its ".0" outside a percentage. Upstream
# narrative text carries a few of these, and they must never reach a published blurb.
UNFORMATTED = re.compile(r"\b\d{7,}\b|\b\d+\.0\b(?!\s*(?:%|pp))")


def is_presentable(text):
    """Whether a sentence is fit to quote as social copy without altering it."""
    return not UNFORMATTED.search(text or "")


def lint_compliance(text):
    """SEBI guardrail. Applies to every artifact that leaves the gate, not just blurbs —
    a design prompt carries card prose into a session that turns it into a public pager."""
    low = text.lower()
    return [f"SEBI lint: banned term {term!r}" for term in SEBI_BANNED
            if re.search(rf"\b{re.escape(term)}\b", low)]


def lint_blurb(text):
    """The machine-checkable half of §10. Returns a list of complaints; empty is clean."""
    problems = lint_compliance(text)
    low = text.lower()
    for m in UNFORMATTED.findall(text):
        problems.append(f"unformatted number {m!r} — say it in lakh/crore, or fix upstream")
    for phrase in BANNED:
        if phrase in low:
            problems.append(f"banned register: {phrase!r}")
    first = next((ln for ln in text.splitlines() if ln.strip()), "")
    if first.rstrip().endswith("?"):
        problems.append("opens with a rhetorical question")
    if "here's why that matters" in low or "here is why that matters" in low:
        problems.append("uses 'here's why that matters'")
    return problems


def blurb_doc(slate):
    """The blurb as validator blocks — plain paragraphs, so every number is in scope."""
    return [{"type": "p", "text": ln} for ln in blurb(slate).split("\n\n") if ln.strip()]


def claims_doc(slate):
    """The claims as validator blocks — card blocks, so they must match a feed verbatim."""
    doc = []
    for c in slate["claims"]:
        if c.get("verbatim"):
            doc.append({"type": "card", "title": c["title"], "body": c["body"],
                        "implication": c.get("implication", "")})
        else:
            doc.append({"type": "p", "text": " ".join(
                x for x in (c["title"], c["body"], c.get("implication", "")) if x)})
    return doc
