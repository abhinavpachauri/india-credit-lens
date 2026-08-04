#!/usr/bin/env python3
"""
monthly_issue.py — the 1st-of-month issue: one merged read (§11.1)
--------------------------------------------------------------------
The single email a lending subscriber gets on the 1st: what RBI's credit AND payments
data said this cycle. One masthead, two halves — a **credit** half and a **payments**
half — each shaped by its own data. There is **no forced cross-read**: the merge is in
the envelope, not manufactured in the prose (the genuine cross-system material lives on
/opportunities and in the deep read). Backward-looking only — no watch, no proximity.

The two RBI releases run on different clocks, so the issue reads BOTH pipelines' latest
periods and states the data-month gap honestly (§13.2) — it never assumes they coincide.

Every number is machine-checked against signals.db, per-block scoped, BEFORE any file is
written (`check_doc`). Fully deterministic — no LLM, no hand-authored stats. The "reads
that matter" are chosen by the deterministic is-news selector (`signals/is_news.py`), not
feed order: a card leads only if it set a record, flipped regime, or crossed a threshold
this cycle. A structural template scores zero and never surfaces.

This supersedes the per-pipeline `merged_issue.py` (now in legacy/): that produced one
issue per pipeline; this produces the one merged issue.

Output: analysis/distribution/output_longform/monthly_issue_{period}.md + .html
Usage:  python3 analysis/distribution/issues/monthly_issue.py
"""
import argparse
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

from distribution import distribution_sources as src            # noqa: E402
from distribution.longform_render import html_render, md_render  # noqa: E402
from distribution.validate_distribution import (                 # noqa: E402
    check_doc, word_number_conflicts, prose_lint)
from signals import is_news                                      # noqa: E402

OUT = ROOT / "analysis" / "distribution" / "output_longform"
DASH = {"sibc": "indiacreditlens.com", "atm_pos": "indiacreditlens.com/payments"}

# The level tiles per half — (label, level signal, YoY signal). A YoY-only tile passes
# None as the level. Level + YoY, no standalone status word (§11.1 build decision).
CREDIT_TILES = [
    ("Bank credit", "sibc-bank-credit-abs", "sibc-bank-credit-yoy"),
    ("Personal loans", None, "sibc-personal-loans-yoy"),
    ("Industry", None, "sibc-industry-yoy"),
]
PAYMENTS_TILES = [
    ("Credit cards in force", "cc-outstanding-abs", "cc-outstanding-yoy"),
    ("Debit cards in force", "dc-outstanding-abs", "dc-outstanding-yoy"),
    ("POS terminals", "pos-terminals-abs", "pos-terminals-yoy"),
]
# Top-5-banks dimensions for the payments half (label, scan signal). All three scans are
# per-bank COUNTS of stock in force — not issuance flows and not spend (there is no per-bank
# spend signal). Labels say exactly that (§11.1 revision).
BANK_DIMS = [("Credit cards in force", "cc-bank-scan"),
             ("Debit cards in force", "dc-bank-scan"),
             ("POS terminals", "pos-bank-scan")]


def _reads(cards, registry, conn, k=2):
    """The k cards that most clearly changed this cycle, is-news ranked. May be fewer."""
    return is_news.select_reads(cards, registry, k=k, conn=conn)


def _pick_reads(cards, registry, conn, picks):
    """Editor-picked reads (§11.1). `picks` = 1-based indices into the is-news shortlist,
    in the order the editor gave them. No picks → fall back to the top 2 clearing the floor,
    so an unattended run still produces an issue."""
    ranked = is_news.shortlist(cards, registry, conn)
    if picks:
        return [ranked[i - 1] for i in picks if 1 <= i <= len(ranked)]
    return [r for r in ranked if r["score"] >= is_news.READ_FLOOR][:2]


def _sector_table(doc, period, prior):
    """The full sector growth table, grouped by parent — every sector's YoY, movers flagged."""
    groups = src.sector_growth_table(period, prior)
    if not groups:
        doc.append({"type": "p", "text": "No sector data this cycle."})
        return []
    rows, declared = [], []
    for section, secs in groups:
        rows.append({"cells": [section, "", ""], "header": True})
        for s in secs:
            rows.append({"cells": [s["name"], s["yoy"], s["mark"]], "signals": s["signals"]})
            declared += s["signals"]
    doc.append({"type": "table", "columns": ["Sector", "YoY growth", "Trend"], "rows": rows,
                "caption": "Trend shows momentum in the growth rate: ↗ accelerating (rate rose "
                           "vs last month), ↘ decelerating (rate fell), → steady. 'turned' marks "
                           "the rarer event — a sector that flipped between growing and shrinking."})
    return declared


def _reads_block(doc, reads):
    """Reads = card title + body only. The prescriptive 'So what' implication is dropped
    for the monthly issue (§11.1 revision) — it is descriptive, not advisory."""
    for r in reads:
        c = r["card"]
        doc.append({"type": "card", "title": c["title"], "body": c["body"]})
        if c.get("chart"):
            doc.append({"type": "chart", "text": c["chart"]})


def build_doc(credit_picks=None, payments_picks=None):
    from signals import proximity
    registry = src.load_registry()
    conn = proximity._con()

    vintage = src.data_vintage()
    sp = vintage.get("sibc", {}).get("period")
    ap = vintage.get("atm_pos", {}).get("period")
    smonth = vintage.get("sibc", {}).get("label", "")
    amonth = vintage.get("atm_pos", {}).get("label", "")

    declared = []
    doc = []

    # ── Masthead ──────────────────────────────────────────────────────────────
    doc.append({"type": "h1", "text": f"India Credit Lens — credit and payments"})
    doc.append({"type": "p", "text": src.vintage_sentence(vintage)})

    # The month in one line — the single strongest read across both halves.
    credit_cards = src.insight_cards("sibc", max_cards=8)
    pay_cards = src.insight_cards("atm_pos", max_cards=8)
    lead = _reads(credit_cards + pay_cards, registry, conn, k=1)
    if lead:
        doc.append({"type": "p", "signals": lead[0]["card"].get("signal_ids", []),
                    "text": lead[0]["card"]["body"], "verbatim": True})   # quoted eval prose

    # ── Credit half ───────────────────────────────────────────────────────────
    doc.append({"type": "h2", "text": f"Credit — {smonth}"})
    ctiles = src.tiles(sp, CREDIT_TILES)
    doc.append({"type": "statgrid", "items": ctiles})
    for it in ctiles:
        declared += it["signals"]

    doc.append({"type": "h2", "text": "How each sector is growing"})
    prior_s = src.prior_period("sibc", sp)
    declared += _sector_table(doc, sp, prior_s)

    rot = src.rotation_line("sibc", sp)
    if rot:
        doc.append({"type": "h2", "text": "Where the mix is shifting"})
        doc.append({"type": "p", "signals": rot["signals"], "text": rot["text"]})
        declared += rot["signals"]

    doc.append({"type": "h2", "text": "The reads that matter"})
    creads = _pick_reads(credit_cards, registry, conn, credit_picks)
    if creads:
        _reads_block(doc, creads)
    else:
        doc.append({"type": "p", "text": "Nothing in the credit data cleared the news bar "
                                         "this cycle — a quiet month."})

    # ── Payments half ─────────────────────────────────────────────────────────
    doc.append({"type": "h2", "text": f"Payments — {amonth}"})
    ptiles = src.tiles(ap, PAYMENTS_TILES)
    doc.append({"type": "statgrid", "items": ptiles})
    for it in ptiles:
        declared += it["signals"]

    lines = src.pair_lines("atm_pos", ap)
    if lines:
        doc.append({"type": "h2", "text": "Fleet vs usage"})
        doc.append({"type": "p", "text": "A few things that usually move together have come apart "
                                         "this year:"})
        for ln in lines:
            doc.append({"type": "p", "signals": ln["signals"], "text": ln["text"]})
            declared += ln["signals"]

    doc.append({"type": "h2", "text": "The biggest banks this month"})
    for label, scan in BANK_DIMS:
        tb = src.top_banks(scan, ap)
        if not tb["banks"]:
            continue
        rows = [{"cells": [b["name"], b["value"]], "signals": [scan]} for b in tb["banks"]]
        doc.append({"type": "table", "columns": ["Bank", label], "rows": rows})
        declared.append(scan)

    doc.append({"type": "h2", "text": "The reads that matter"})
    preads = _pick_reads(pay_cards, registry, conn, payments_picks)
    if preads:
        _reads_block(doc, preads)
    else:
        doc.append({"type": "p", "text": "Nothing in the payments data cleared the news bar "
                                         "this cycle."})

    conn.close()

    # ── Closing ───────────────────────────────────────────────────────────────
    doc.append({"type": "hr"})
    doc.append({"type": "p", "text":
                f"The interactive charts behind every number are on the dashboards: "
                f"{DASH['sibc']} for credit, {DASH['atm_pos']} for payments."})
    doc.append({"type": "small", "text":
                "How this is made: the data goes through an automated pipeline with validation "
                "gates at every step. Every number is machine-checked against the RBI source file; "
                "the two reads in each half are chosen by an editor from a shortlist the pipeline "
                "ranks by how much each moved."})

    period = sp or ap
    return doc, declared, period


_GLYPH = {"record": "record", "flip": "regime-flip", "magnitude": "big-move", "crossed": "crossed",
          "artifact": "single-issuer"}


def _print_shortlist():
    """List the ranked read candidates per half so the editor can pick (§11.1)."""
    from signals import proximity
    registry = src.load_registry()
    conn = proximity._con()
    for half, pipeline in (("CREDIT", "sibc"), ("PAYMENTS", "atm_pos")):
        cards = src.insight_cards(pipeline, max_cards=8)
        ranked = is_news.shortlist(cards, registry, conn)
        print(f"\n══ {half} — read candidates (is-news ranked) ══")
        print(f"  {'#':>2}  {'score':>5}  factors                     title")
        for i, r in enumerate(ranked, 1):
            f = (r["news"] or {}).get("factors", {})
            fac = ", ".join(_GLYPH[k] for k, v in f.items() if v) or "—"
            print(f"  {i:>2}  {r['score']:>5.1f}  {fac:<26}  {r['card']['title'][:60]}")
    conn.close()
    print("\nPick with:  --credit 1,3  --payments 2,4   (numbers are the # column above)")


def _picks(arg):
    return [int(x) for x in arg.split(",") if x.strip()] if arg else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="gate + print, write nothing")
    ap.add_argument("--shortlist", action="store_true",
                    help="list the ranked read candidates per half, then exit")
    ap.add_argument("--credit", help="comma indices into the credit shortlist, e.g. 1,3")
    ap.add_argument("--payments", help="comma indices into the payments shortlist, e.g. 2,4")
    a = ap.parse_args()

    if a.shortlist:
        _print_shortlist()
        return 0

    doc, declared, period = build_doc(_picks(a.credit), _picks(a.payments))
    md = md_render(doc)

    # Gate 1 — numbers trace (per-block scoped). Hard.
    failures = check_doc(doc, declared, label=f"monthly_issue {period}")
    # Gate 2 — word-vs-number agreement + prose register. Conflicts/register in OUR text
    # hard-fail; the same in verbatim card prose warns and feeds the eval v1.12 fix list.
    wn_hard, wn_warn = word_number_conflicts(doc)
    pr_hard, pr_warn = prose_lint(doc)
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
              f"prompt v1.12, not here (§11.1):")
        for w in warnings[:12]:
            print(f"    ⚠ {w}")
    if a.dry_run:
        print("\n" + md)
        return 0

    OUT.mkdir(exist_ok=True)
    (OUT / f"monthly_issue_{period}.md").write_text(md)
    (OUT / f"monthly_issue_{period}.html").write_text(html_render(doc, doc[0]["text"]))
    print(f"  → {(OUT / f'monthly_issue_{period}.md').relative_to(ROOT)}")
    print(f"  → {(OUT / f'monthly_issue_{period}.html').relative_to(ROOT)}   "
          "(open → select all → copy → paste into Substack)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
