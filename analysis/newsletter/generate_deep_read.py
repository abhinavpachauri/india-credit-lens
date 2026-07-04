#!/usr/bin/env python3
"""
generate_deep_read.py — newsletter Post 2: the deep read (L2/L3)
-----------------------------------------------------------------
Prepared the same day as the release read, published mid-cycle. Composes the
cross-system view from opportunities_feed.json — the ecosystem cards (constructs,
loops, data checks) with their computed basis, plus the openings and risks that
are live this cycle. This is the content only the composed model can produce.

The card prose was already validated by Check 4f when the feed was built; the
self-gating traceability check here guards the template's own words.

Output: analysis/newsletter/output/deep_read_{period}.md + .html
Usage:  python3 analysis/newsletter/generate_deep_read.py
"""
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
OPPS_URL = "https://indiacreditlens.com/opportunities"


def month_name(period):
    return datetime.strptime(period, "%Y-%m-%d").strftime("%B %Y")


def basis_lines(basis):
    """Condense a card's computed basis into 2-3 plain lines for the letter."""
    lines = []
    if basis.get("headline"):
        lines.append(basis["headline"])
    for m in basis.get("members", [])[:6]:
        arrow = "up" if m.get("direction") == 1 else "down" if m.get("direction") == -1 else "flat"
        lines.append(f"{m['label']}: {arrow}" + (f", {m['value']}" if m.get("value") else ""))
    return lines


def build_doc():
    feed = src.opportunities_feed()
    periods = feed["_meta"]["periods"]
    period = max(p for p in periods.values() if p)
    cross = [c for c in feed.get("cross_system", []) if c["status"] in ("active", "watch")]
    live = {pl: [o for o in items if o["tier"] == "opportunity" and o["status"] == "active"]
            for pl, items in feed.get("pipelines", {}).items()}
    risks = [o for items in feed.get("pipelines", {}).values() for o in items
             if o["tier"] == "risk" and o["status"] in ("active", "watch")]
    risks += [c for c in feed.get("cross_system", []) if c["tier"] == "risk"
              and c["status"] in ("active", "watch")]

    # traceability scope = the declared evidence of every item this issue includes
    included = cross + [o for items in live.values() for o in items[:3]] + risks[:3]
    declared = list(dict.fromkeys(
        s for it in included for s in (it.get("evidence_all") or it.get("evidence") or [])))

    # label by the latest DATA month across pipelines, not the release date
    data_months = [src.data_month(pl, p) for pl, p in periods.items() if p]
    display = month_name(max(data_months)) if data_months else month_name(period)
    doc = []
    doc.append({"type": "h1", "text":
                f"The deep read, {display}: what credit and payments data "
                "say when you read them together"})
    doc.append({"type": "p", "text":
                "The release notes cover what each dataset says on its own. This one is "
                "different: it reads the credit data and the payments data as one system — "
                "where they agree, where they disagree, and what that means for lending. "
                "The disagreements are usually the most useful part."})

    if cross:
        doc.append({"type": "h2", "text": "The cross-system reads"})
        for c in cross:
            if c["tier"] == "risk":
                continue
            doc.append({"type": "card", "title": c["title"], "body": c["body"],
                        "implication": c.get("implication", "")})
            basis = c.get("basis")
            if basis:
                doc.append({"type": "p", "text": "How this read is computed:"})
                for line in basis_lines(basis):
                    doc.append({"type": "li", "text": line})

    for pl, items in live.items():
        if not items:
            continue
        doc.append({"type": "h2", "text": f"Live openings — {src.PIPE_LABEL.get(pl, pl)}"})
        for o in items[:3]:
            doc.append({"type": "card", "title": o["title"], "body": o["body"],
                        "implication": o.get("implication", "")})

    if risks:
        doc.append({"type": "h2", "text": "Watch-outs"})
        for r in risks[:3]:
            doc.append({"type": "card", "title": r["title"], "body": r["body"],
                        "implication": r.get("implication", "")})

    doc.append({"type": "hr"})
    doc.append({"type": "p", "text":
                "All of these update automatically every time new RBI data lands. The live "
                f"version, with charts and the full computed basis for each read, is here: {OPPS_URL}"})
    doc.append({"type": "small", "text":
                "How this is made: each read above is computed from the data, not written by "
                "hand. The 'how this is computed' lines show the actual inputs. If the data "
                "stops supporting a read, the read is withdrawn in the next issue — that record "
                "is public."})
    return doc, period, declared


def main():
    doc, period, declared = build_doc()
    md = md_render(doc)
    failures = check_doc(doc, declared, label=f"deep_read {period}")
    if failures:
        for f in failures:
            print(f"  ✗ {f}", file=sys.stderr)
        print(f"✗ FAIL — {len(failures)} ungrounded number(s); nothing written", file=sys.stderr)
        return 1

    OUT.mkdir(exist_ok=True)
    title = doc[0]["text"]
    md_path = OUT / f"deep_read_{period}.md"
    html_path = OUT / f"deep_read_{period}.html"
    md_path.write_text(md)
    html_path.write_text(html_render(doc, title))
    print("✓ traceability passed — every number traces to signals.db")
    print(f"  → {md_path.relative_to(ROOT)}")
    print(f"  → {html_path.relative_to(ROOT)}   (open in browser → select all → copy → paste into Substack)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
