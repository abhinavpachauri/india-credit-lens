#!/usr/bin/env python3
"""
generate_release_read.py — newsletter Post 1: the release read (L1)
--------------------------------------------------------------------
Runs within 24h of an RBI release. Fully deterministic: composes the issue from
signals.db (headline stats, status flips, new trackers) and the gate-validated
insight cards. No LLM, no hand-authored stats. Voice: plain conversational
English — short sentences, no consulting words.

Self-gating: the issue is validated for number traceability BEFORE any file is
written. A failing issue is never written.

Output: analysis/newsletter/output/release_read_{pipeline}_{period}.md + .html
Usage:  python3 analysis/newsletter/generate_release_read.py [--pipeline sibc|atm_pos] [--period YYYY-MM-DD]
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import newsletter_sources as src                      # noqa: E402
from newsletter_render import html_render, md_render  # noqa: E402
from validate_newsletter import check_doc             # noqa: E402

OUT = Path(__file__).resolve().parent / "output"

RELEASE_NAME = {"sibc": "sectoral bank credit (SIBC)", "atm_pos": "ATM/POS and card"}
DASHBOARD = {"sibc": "https://indiacreditlens.com", "atm_pos": "https://indiacreditlens.com/payments"}


def month_name(period):
    return datetime.strptime(period, "%Y-%m-%d").strftime("%B %Y")


def build_doc(pipeline, period):
    prior = src.prior_period(pipeline, period)
    stats = src.headline_stats(pipeline, period)
    flips = src.status_flips(pipeline, period, prior) if prior else []
    fresh = src.new_signals(pipeline, period)
    cards = src.insight_cards(pipeline)
    # every signal whose values the template itself renders — the traceability scope
    declared = [s["id"] for s in stats] + [f["id"] for f in flips] + [n["id"] for n in fresh]

    month = month_name(src.data_month(pipeline, period))   # the data month, not the release date
    doc = []
    lead = cards[0]["title"] if cards else f"the {month} numbers"
    doc.append({"type": "h1", "text": f"RBI {RELEASE_NAME[pipeline]} data, {month}: {lead}"})
    doc.append({"type": "p", "text":
                f"RBI has put out the {RELEASE_NAME[pipeline]} data for {month}. "
                "This issue covers what actually moved, what changed direction since last month, "
                "and the reads that matter for anyone working in lending. Every number below is "
                "machine-checked against the RBI source file before this issue is generated."})
    if cards:
        doc.append({"type": "chart", "text": f"Hero chart — {cards[0]['chart']}"})

    doc.append({"type": "h2", "text": "The headline numbers"})
    # each stat carries its own signal — the scope the gate judges that number by
    doc.append({"type": "statgrid", "items": [
        {"value": s["display"], "label": s["title"], "note": s["status_word"],
         "signal": s["id"]} for s in stats]})

    if flips:
        doc.append({"type": "h2", "text": "What changed direction since last month"})
        doc.append({"type": "p", "text":
                    "These trackers read differently this month than last. A change here is "
                    "usually the earliest sign a trend is starting or ending."})
        GAINING = {"accelerating", "growing steadily", "improving"}
        up = [f for f in flips if f["now"] in GAINING]
        down = [f for f in flips if f["now"] not in GAINING]
        cap = 6
        if up:
            doc.append({"type": "p", "text": "Picked up:"})
            for f in up[:cap]:
                doc.append({"type": "li", "signals": [f["id"]],
                            "text": f"↑ {f['title']} — now {f['now']} ({f['display']})"})
            if len(up) > cap:
                doc.append({"type": "small", "meta": True,
                            "text": f"…and {len(up) - cap} more on the dashboard."})
        if down:
            doc.append({"type": "p", "text": "Slowed down:"})
            for f in down[:cap]:
                doc.append({"type": "li", "signals": [f["id"]],
                            "text": f"↓ {f['title']} — now {f['now']} ({f['display']})"})
            if len(down) > cap:
                doc.append({"type": "small", "meta": True,
                            "text": f"…and {len(down) - cap} more on the dashboard."})

    if fresh:
        doc.append({"type": "h2", "text": "New trackers this cycle"})
        for n in fresh:
            doc.append({"type": "li", "signals": [n["id"]], "text": n["title"]})

    doc.append({"type": "h2", "text": "The reads that matter"})
    for i, c in enumerate(cards):
        if i:
            doc.append({"type": "hr"})
        doc.append({"type": "card", "title": c["title"], "body": c["body"],
                    "implication": c.get("implication", "")})
        if i and c.get("chart"):        # card 0's chart is the hero — don't repeat it
            doc.append({"type": "chart", "text": c["chart"]})

    doc.append({"type": "hr"})
    doc.append({"type": "p", "text":
                "That is the full read for this cycle. The interactive charts behind every number "
                f"are on the dashboard: {DASHBOARD[pipeline]}"})
    doc.append({"type": "small", "text":
                "How this is made: the data goes through an automated pipeline with validation "
                "gates at every step. Nothing in this issue is typed by hand — if a number here "
                "does not match the RBI source file, the issue does not generate."})
    return doc, declared


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pipeline", default="sibc", choices=["sibc", "atm_pos"])
    ap.add_argument("--period", help="default: latest in signals.db")
    a = ap.parse_args()
    period = a.period or src.latest_period(a.pipeline)
    if not period:
        print(f"✗ no periods in signals.db for {a.pipeline}", file=sys.stderr)
        return 1

    doc, declared = build_doc(a.pipeline, period)
    md = md_render(doc)

    failures = check_doc(doc, declared, label=f"release_read {a.pipeline} {period}")
    if failures:
        for f in failures:
            print(f"  ✗ {f}", file=sys.stderr)
        print(f"✗ FAIL — {len(failures)} ungrounded number(s); nothing written", file=sys.stderr)
        return 1

    OUT.mkdir(exist_ok=True)
    title = doc[0]["text"]
    md_path = OUT / f"release_read_{a.pipeline}_{period}.md"
    html_path = OUT / f"release_read_{a.pipeline}_{period}.html"
    md_path.write_text(md)
    html_path.write_text(html_render(doc, title))
    print(f"✓ traceability passed — every number traces to signals.db")
    print(f"  → {md_path.relative_to(ROOT)}")
    print(f"  → {html_path.relative_to(ROOT)}   (open in browser → select all → copy → paste into Substack)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
