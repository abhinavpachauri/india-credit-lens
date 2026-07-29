#!/usr/bin/env python3
"""
deep_read.py — the 14th-of-month issue: the deep read (§11.2)
-----------------------------------------------------------------
The companion to the 1st. The monthly issue says what moved; this says why it matters —
one or more questions that have been building across the data, each answered with the
model's own computed basis and, where verified, a sourced why. ~7 minutes.

It is a computed floor plus an editorial spine (§11.2):

  Part A — Banks this month   fully computed from the payments bank signals the monthly
                              issue deliberately drops (rotation + divergence). No judgement:
                              the only input is which banks to feature, ranked by move size.
  Part B — the spine(s)       the editor's call. `--shortlist` ranks the candidate questions
                              (loops, constructs, cross-edges, openings, risks, constraints)
                              from the composed model; `--spine 1,3` picks one or more; the
                              machine builds the issue around the pick. No pick → the top
                              candidate, so an unattended run still produces an issue.

Every number is machine-checked against signals.db BEFORE any file is written, per block,
scoped to that block's own signals — a basis line scopes to its member's own signal, never
the driver's whole evidence set (§11.2 D1). A spine that rests on a loop or a constraint
gets an inline mermaid diagram. A featured bank's "why" is sourced and verified or it is not
shown — the computed basis is the honest fallback.

    python3 analysis/distribution/issues/deep_read.py --shortlist     # ranked spine options
    python3 analysis/distribution/issues/deep_read.py --spine 1,3      # editor picks
    python3 analysis/distribution/issues/deep_read.py                  # top spine, unattended

Output: analysis/distribution/output_longform/deep_read_{period}.md + .html
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

from core import voice                                            # noqa: E402
from distribution import bank_sourcing                             # noqa: E402
from distribution import distribution_sources as src              # noqa: E402
from distribution import ledger                                   # noqa: E402
from distribution import mermaid                                  # noqa: E402
from distribution import model_graph                              # noqa: E402
from distribution.longform_render import html_render, md_render   # noqa: E402
from distribution.validate_distribution import (                  # noqa: E402
    check_doc, prose_lint, word_number_conflicts)

OUT = ROOT / "analysis" / "distribution" / "output_longform"
OPPS_URL = "https://indiacreditlens.com/opportunities"

# How many banks Part A features per dimension, and which spine gets the top billing.
FEATURE_N = 3


def month_name(period):
    return datetime.strptime(period, "%Y-%m-%d").strftime("%B %Y")


def chart_recipe(item):
    caps = [ch.get("caption") for ch in item.get("charts", []) if ch.get("caption")]
    if not caps:
        return None
    return ("indiacreditlens.com/opportunities → this card → screenshot its chart panel "
            f"({' + '.join(caps[:3])})")


# ── Part B: render one chosen spine (§11.2-R) ─────────────────────────────────
# The machine's own words are plain and grounded (voice-rendered over gated facts); the
# validated body stays verbatim for its substance; the prescriptive take is the editor's.

def _yoy_move(node, pipeline, period):
    """A plain, sign-safe sentence for a node's own year-on-year move, scoped to its -yoy
    signal — or None. The word agrees with the sign, so nothing reads 'up, −0.5%'."""
    vals = src.total_values(pipeline, period)
    sid = next((s for s in node.get("signals", []) if s.endswith("-yoy") and s in vals), None)
    if not sid:
        return None
    v, u, _ = vals[sid]
    disp = src.fmt_value(v, u)                       # "16.4%" / "-0.5%"
    label = node["label"]
    # Direction from the raw value's sign — fmt_value drops the '+' on a positive rate, so the
    # rendered string alone would read a genuine gain as directionless (§11.2-R1). The word
    # agrees with the sign, so a negative rate keeps its minus and reads 'shrank … -0.5%'.
    if v > 0.05:
        text = f"{label} grew {disp} over the past year."
    elif v < -0.05:
        text = f"{label} shrank over the past year, its rate at {disp}."
    else:
        text = f"{label} was flat over the year, at {disp}."
    return {"type": "p", "signals": [sid], "text": text}


def _force_split(cand, sub):
    """(force, up_target, down_target) from the spine's model subgraph — the +/- split of a
    sourced force. Any missing → None, and the caller falls back to a plainer read."""
    force = next((n for n in sub["nodes"] if n["kind"] == "force"), None)
    if not force:
        return None
    up = down = None
    for e in sub["edges"]:
        if e["from"] != force["id"]:
            continue
        tgt = next((n for n in sub["nodes"] if n["id"] == e["to"]), None)
        if not tgt or tgt["kind"] == "risk":
            continue
        if e.get("against"):
            down = down or tgt
        else:
            up = up or tgt
    return (force, up, down) if (up and down) else None


def _risk_read(doc, cand, sub, pipeline, period):
    """The 'how we know' for a risk/opening whose model carries a sourced force splitting two
    ways (e.g. #8: Zero MDR lifts QR, weighs on POS). Plain words, grounded numbers scoped to
    each side's own signal. Returns declared signal ids, or None if the shape doesn't fit."""
    split = _force_split(cand, sub) if sub else None
    if not split:
        return None
    force, up, down = split
    declared = []
    source = model_graph.force_source(pipeline, force["id"]).split("—")[0].strip()
    on_record = f" It is on the record — {source}." if source else ""
    doc.append({"type": "p", "text":
                f"The reason is a policy one: {force['label']}. It pushes two ways at once — it "
                f"lifts {up['label']} and it weighs on {down['label']}.{on_record}"})
    doc.append({"type": "p", "text": "You can see both sides in the data — the same force, "
                                     "pushing them opposite ways:"})
    for node in (up, down):
        move = _yoy_move(node, pipeline, period)
        if move:
            doc.append(move)
            declared += move["signals"]
    return declared


def _basis_read(doc, basis):
    """The 'how we know' for a composed cross-system spine — one plain sentence per member,
    each scoped to its own signal (D1), the one moving against the read flagged. Returns
    declared signal ids."""
    declared = []
    doc.append({"type": "p", "text": "How we can tell — the pieces this read rests on:"})
    for m in basis.get("members", [])[:6]:
        value = (m.get("value") or "").strip()
        if not value:
            continue
        obs = voice.observed_dir(value)
        authored = m.get("direction")
        against = obs is not None and authored not in (None, 0) and obs != authored
        tail = " — the one to watch, moving against the rest" if against else ""
        doc.append({"type": "p", "signals": m.get("signals") or [],
                    "text": f"{m['label']} is running at {value}{tail}."})
        declared += m.get("signals") or []
    return declared


def _so_what(doc, kind):
    """A plain observation — never advice, never a forecast (voice-linted). The sharp,
    prescriptive take is the editor's, added by hand; the machine only says where the lines
    are now."""
    text = {
        "risk": "What it means for a lender, plainly: the two sides are drifting apart, and "
                "whatever only the shrinking side provided drifts out of reach for those who "
                "follow the growing one. That gap is the read as it stands today.",
        "constraint": "What it means, plainly: this is a data check, not a market move. As long as "
                      "the two sources reconcile, the numbers downstream can be trusted; when they "
                      "don't, it is a source to fix.",
    }.get(kind,
          "What it means, plainly: the pieces are lining up the same way across credit and "
          "payments right now — which is what makes this one read rather than noise.")
    doc.append({"type": "p", "text": text})


def render_spine(doc, cand, heading):
    """Append one spine's section under `heading` (§11.2-R published shape):
    heading → the read (plain) → model diagram → how we know (grounded) → so what → Bank angle."""
    declared = []
    item = cand.get("item", {})
    kind = cand["kind"]
    pipeline = item.get("pipeline", "atm_pos")
    period = src.latest_period(pipeline)
    sub = model_graph.subgraph_for(cand)
    doc.append({"type": "h2", "text": heading})

    # The read — the validated body carries the substance verbatim (its numbers are gate-safe);
    # a constraint has no card, so it is described in neutral words. The boilerplate implication
    # is dropped — the machine's take is the voice-rendered "so what" below.
    if cand.get("verbatim_prose", True) and item.get("body"):
        doc.append({"type": "card", "title": "",
                    "body": item.get("body", "") or item.get("narrative", "")})
    elif kind == "constraint":
        doc.append({"type": "p", "text":
                    "This is a cross-check, not a trend. Two independent RBI sources — one on the "
                    "credit side, one on the payments side — are compared to see whether they "
                    "still tell a consistent story. When they drift apart, it usually means a data "
                    "problem to fix, not a real economic move."})

    # The diagram is the model's own subgraph, drawn inline — never synthesised (§11.2-R2).
    if sub:
        doc.append(mermaid.block(
            mermaid.render(sub["nodes"], sub["edges"]),
            caption="Every box and arrow here is from the causal model — a solid arrow pushes "
                    "the same way, a dashed one pushes against."))

    # How we know — grounded and plain. A sourced-force split reads one way; a composed basis
    # reads another; a bare risk falls back to naming its driver.
    grounded = _risk_read(doc, cand, sub, pipeline, period)
    if grounded is not None:
        declared += grounded
    elif item.get("basis"):
        declared += _basis_read(doc, item["basis"])
    elif cand.get("_driver"):
        via = f" — {item.get('_via')}" if item.get("_via") else ""
        doc.append({"type": "p", "text":
                    f"How we can tell: the driver behind this read is {cand['_driver']}{via}."})

    _so_what(doc, kind)

    # Corroboration — verified second sources (§11.2 R3). Show at most one that grounds the read
    # on the record (official/report) and one that triangulates it (independent press).
    corrs = bank_sourcing.corroborations(cand.get("id"))
    shown = set()
    for corr in corrs:
        is_press = corr.get("tier") == "press"
        bucket = "press" if is_press else "record"
        if bucket in shown:
            continue
        shown.add(bucket)
        lead = "Others are seeing it too" if is_press else "On the official record"
        doc.append({"type": "p", "signals": [], "text":
                    f"{lead} — {corr.get('source')}: “{corr.get('excerpt')}” "
                    f"({bank_sourcing.TIER_LABEL.get(corr.get('tier'), '')}, {corr.get('url')})"})

    recipe = chart_recipe(item)
    if recipe:
        doc.append({"type": "chart", "text": recipe})

    # Bank angle — the sourced 'why' for the featured banks (Part 2 S4a fills this). Verified
    # claims only; with none, the honest note that it is added when sourced.
    doc.append({"type": "h3", "text": "Bank angle"})
    whys = bank_sourcing._publishable(bank_sourcing.load().get("bank_claims", []))
    if whys:
        for w in whys[:6]:
            tier = bank_sourcing.TIER_LABEL.get(w.get("tier"), w.get("tier", ""))
            doc.append({"type": "p", "signals": [], "text":
                        f"{w.get('bank')} — {w.get('why')} “{w.get('excerpt')}” "
                        f"({tier}: {w.get('url')})"})
    else:
        doc.append({"type": "p", "text":
                    "We don't yet publish a sourced, bank-by-bank why for this question — a "
                    "bank-level reason appears here only once it is found, quoted, and verified "
                    "against a public source. Until then, the computed read above and the bank "
                    "movements in “Banks this month” below are what we can stand behind."})
    return declared


# ── Part A: banks this month (computed floor) ─────────────────────────────────

def render_banks(doc, period):
    """Append Part A. Returns declared signal ids. Honest-null when a section is empty."""
    declared = []
    doc.append({"type": "hr"})
    doc.append({"type": "h2", "text": "Banks this month"})
    doc.append({"type": "p", "text":
                "This part is fully computed — who is gaining ground on their peers, and who is "
                "pulling away from their own category. No editorial pick beyond which banks to show."})

    rot = src.bank_rotation(period)
    if rot:
        doc.append({"type": "h3", "text": "Who's rotating"})
        for r in rot:
            # lower-case the dimension for mid-sentence flow, but keep POS/ATM upper.
            dim = r["dimension"]
            dim = dim if dim.split()[0] in ("POS", "ATM") else dim.lower()
            doc.append({"type": "p", "signals": r["signals"], "text":
                        f"In {dim}, {r['gain']['category']} gained the most "
                        f"share ({r['gain']['delta']}) while {r['give']['category']} gave up the "
                        f"most ({r['give']['delta']})."})
            declared += r["signals"]
    else:
        doc.append({"type": "p", "text": "No category rotated meaningfully this cycle — the mix "
                                         "held steady across bank groups."})

    div = src.bank_divergence(period, n=FEATURE_N)
    flagged = [d for d in div if d["pulling_away"] or d["falling_behind"]]
    if flagged:
        doc.append({"type": "h3", "text": "Who's diverging"})
        doc.append({"type": "p", "text": "Banks whose own growth pulled furthest away from their "
                                         "category's — ahead of it, or behind it (year-on-year)."})
        for d in flagged:
            rows = []
            for b in d["pulling_away"]:
                rows.append({"cells": [b["bank"], b["gap"], "▲ ahead of its group"],
                             "signals": d["signals"]})
            for b in d["falling_behind"]:
                rows.append({"cells": [b["bank"], b["gap"], "▼ behind its group"],
                             "signals": d["signals"]})
            doc.append({"type": "table",
                        "columns": [d["dimension"], "vs its category (pp)", ""], "rows": rows})
            declared += d["signals"]
            # A per-dimension chart of the featured banks against their group — a screenshot
            # placeholder the editor fills from the payments dashboard (§11.2 charts convention).
            names = [b["bank"] for b in (d["pulling_away"] + d["falling_behind"])]
            doc.append({"type": "chart", "text":
                        f"indiacreditlens.com/payments → {d['dimension']} → per-bank YoY view → "
                        f"highlight: {', '.join(names[:6])}"})
    else:
        doc.append({"type": "p", "text": "No bank pulled far enough from its category to flag "
                                         "this cycle — movement stayed within the pack."})
    return declared


# ── Assembly ──────────────────────────────────────────────────────────────────

def build_doc(spine_picks=None):
    cands = src.spine_candidates()
    if spine_picks:
        chosen = [cands[i - 1] for i in spine_picks if 1 <= i <= len(cands)]
    else:
        chosen = cands[:1]                        # unattended: the top-ranked spine
    for c in chosen:
        c.setdefault("verbatim_prose", c["kind"] != "constraint")

    vintage = src.data_vintage()
    periods = vintage
    data_months = [v["data_month"] for k, v in vintage.items() if isinstance(v, dict)]
    display = month_name(max(data_months)) if data_months else ""
    atm_period = vintage.get("atm_pos", {}).get("period")

    declared = []
    doc = []

    # ── Masthead: a generic title + the chosen question(s), stated once ────────────
    doc.append({"type": "h1", "text": f"The deep read — {display}"})
    if len(chosen) == 1:
        doc.append({"type": "p", "text": f"This month's question: {chosen[0]['question']}"})
    elif len(chosen) > 1:
        qs = "  ·  ".join(c["question"] for c in chosen)
        doc.append({"type": "p", "text": f"This month's questions —  {qs}"})
    doc.append({"type": "p", "text":
                "The monthly issue covered what moved. This one takes a question that has been "
                "building across the credit and payments data and follows it down — with the "
                "model's own computed basis, and a sourced why wherever one is verified. It ends "
                "with the banks: who is gaining ground, and who is drifting from their peers."})

    if not chosen:
        doc.append({"type": "p", "text":
                    "No question was fresh enough to lead this cycle — every angle we would open "
                    "ran recently. Rather than repeat one, the deep read is the bank section alone "
                    "this month."})
    # One spine → the generic "Why this question now"; several → each headed by its question.
    for cand in chosen:
        heading = "Why this question now" if len(chosen) == 1 else cand["question"]
        declared += render_spine(doc, cand, heading)

    if atm_period:
        declared += render_banks(doc, atm_period)

    # What we're watching — one C8 level edge (not a momentum knife edge).
    watch = src.watchlist(top_n=1)
    if watch:
        w = watch[0]
        p = w["proximity"]
        doc.append({"type": "h2", "text": "What we're watching"})
        # A proximity threshold is derived from the signal's own status rules, not stored —
        # so the line carries its four derived numbers as `extra`, scoped to this block only.
        doc.append({"type": "p", "signals": w["signal_ids"], "text": w["body"],
                    "extra": [p["value"], p["threshold_value"], p["distance"],
                              p["typical_move"], p["prev_value"]]})
        declared += w["signal_ids"]

    doc.append({"type": "hr"})
    doc.append({"type": "p", "text":
                "Every read here updates automatically when new RBI data lands. The live version, "
                f"with charts and the full computed basis, is here: {OPPS_URL}"})
    doc.append({"type": "small", "text":
                "How this is made: Part A is computed straight from the bank data. The spine is "
                "chosen by an editor from a ranked shortlist the pipeline builds, then answered "
                "with the model's computed basis. A bank-level 'why' or an outside corroborating "
                "source appears only once it has been found, quoted, and verified with a link — "
                "never inferred. Until then, the computed basis is the read."})

    period = atm_period or (vintage.get("sibc") or {}).get("period")
    spine_kinds = [c["kind"] for c in chosen]
    return doc, period, declared, spine_kinds


# ── Shortlist (the editor's menu) ─────────────────────────────────────────────

def _print_shortlist():
    cands = src.spine_candidates()
    print("\nSPINE OPTIONS — deep read (ranked)\n")
    for i, c in enumerate(cands, 1):
        diagram = "diagram: YES" if c.get("diagram") else "diagram: no "
        print(f"{i:>2}. [{c['kind']:<10}] {c['question']}")
        sup = " · ".join(s for s in c.get("supports", []) if s)[:96]
        if sup:
            print(f"    supports: {sup}")
        print(f"    {diagram}   fresh: {c['fresh']}   score: {c['score']:.1f}")
    print("\nPick with:  --spine 1        or several:  --spine 1,3")


def _picks(arg):
    return [int(x) for x in arg.split(",") if x.strip()] if arg else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shortlist", action="store_true",
                    help="list the ranked spine candidates, then exit")
    ap.add_argument("--spine", help="comma indices into the shortlist, e.g. 1,3")
    ap.add_argument("--dry-run", action="store_true", help="gate + print, write nothing")
    a = ap.parse_args()

    if a.shortlist:
        _print_shortlist()
        return 0

    doc, period, declared, spine_kinds = build_doc(_picks(a.spine))
    md = md_render(doc)

    # Gate 1 — numbers trace, per block (basis lines scoped to their own member signal).
    failures = check_doc(doc, declared, label=f"deep_read {period}")
    # Gate 2 — word/number agreement + prose register in OUR text; verbatim card prose warns.
    wn_hard, wn_warn = word_number_conflicts(doc)
    pr_hard, pr_warn = prose_lint(doc)
    # Gate 3 — nothing marked verified in the sourcing store may be missing its link/excerpt.
    failures += bank_sourcing.validate_store()
    failures += wn_hard + pr_hard

    if failures:
        for f in failures:
            print(f"  ✗ {f}", file=sys.stderr)
        print(f"✗ FAIL — {len(failures)} issue(s); nothing written", file=sys.stderr)
        return 1

    print("✓ traceability passed — every number traces to signals.db (per-block scoped)")
    print("✓ word-vs-number agreement — no direction/rate conflicts in generated text")
    warnings = wn_warn + pr_warn
    if warnings:
        print(f"⚠ {len(warnings)} warning(s) in verbatim card prose — fix upstream at eval "
              f"prompt v1.12, not here:")
        for w in warnings[:12]:
            print(f"    ⚠ {w}")
    if a.dry_run:
        print("\n" + md)
        return 0

    OUT.mkdir(exist_ok=True)
    (OUT / f"deep_read_{period}.md").write_text(md)
    (OUT / f"deep_read_{period}.html").write_text(html_render(doc, doc[0]["text"]))
    ledger.record_spines(spine_kinds)
    print(f"  spines: {', '.join(spine_kinds) or '(bank section only)'} — recorded to ledger")
    print(f"  → {(OUT / f'deep_read_{period}.md').relative_to(ROOT)}")
    print(f"  → {(OUT / f'deep_read_{period}.html').relative_to(ROOT)}   "
          "(open → select all → copy → paste into Substack)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
