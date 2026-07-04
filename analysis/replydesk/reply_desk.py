#!/usr/bin/env python3
"""
reply_desk.py — the X reply desk (assisted distribution, v1)
-------------------------------------------------------------
Another projection over the validated engine (like the newsletter): given a
tweet's text, produce the AMMUNITION for a grounded reply — current values,
statuses, and verbatim insight lines — and gate any draft before it reaches
the human review queue.

The workflow around this module (browser reading, drafting, posting) is the
session ritual in analysis/replydesk/CLAUDE.md. Hard rules: a human posts
every reply; drafts that fail the gate are never shown for review.

Data layer is SHARED with the newsletter (newsletter_sources) — one
distribution data layer, two consumers. If a third consumer appears, lift it
to its own module then, not before.

Usage:
  python3 analysis/replydesk/reply_desk.py brief "<tweet text or topic>"
  python3 analysis/replydesk/reply_desk.py check "<draft reply>" [--topics gold_loans,credit_cards]
  python3 analysis/replydesk/reply_desk.py log --url <tweet_url> --topic <id> --text "<posted reply>"
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))
sys.path.insert(0, str(ROOT / "analysis" / "newsletter"))

import newsletter_sources as src                                   # noqa: E402
from validate_newsletter import declared_ground_truth              # noqa: E402
from core.traceability import SIBC as POLICY, extract_numbers, matches, ratio_matches  # noqa: E402

LOG = Path(__file__).resolve().parent / "reply_log.json"

# ── Topic routing (deterministic keyword → signals + insight sections) ────────

TOPICS = {
    "bank_credit": {
        "keywords": ["bank credit", "credit growth", "credit deployment", "non-food credit",
                     "sibc", "credit offtake", "loan growth"],
        "signals": ["sibc-bank-credit-abs", "sibc-bank-credit-yoy", "sibc-nonfood-credit-yoy"],
        "cards": [("sibc", "bankCredit"), ("sibc", "mainSectors")],
    },
    "gold_loans": {
        "keywords": ["gold loan", "muthoot", "manappuram", "iifl finance", "loan against gold",
                     "gold finance"],
        "signals": ["sibc-pl-gold-yoy", "sibc-pl-gold-share", "sibc-pl-gold-pos-streak"],
        "cards": [("sibc", "personalLoans")],
    },
    "credit_cards": {
        "keywords": ["credit card", "card spend", "sbi cards", "cc outstanding", "revolvers",
                     "card issuance"],
        "signals": ["sibc-pl-cc-yoy", "sibc-pl-cc-abs", "cc-outstanding-abs", "cc-outstanding-yoy"],
        "cards": [("sibc", "personalLoans"), ("atm_pos", "cc")],
    },
    "unsecured_retail": {
        "keywords": ["unsecured", "personal loan", "retail credit", "consumer credit",
                     "household debt", "retail lending"],
        "signals": ["sibc-personal-loans-yoy", "sibc-pl-other-yoy", "sibc-pl-cc-yoy"],
        "cards": [("sibc", "personalLoans")],
    },
    "msme": {
        "keywords": ["msme", "small business", "micro and small", "sme lending", "udyam"],
        "signals": ["sibc-msme-micro-small-yoy", "sibc-msme-medium-yoy", "sibc-msme-size-yoy-spread"],
        "cards": [("sibc", "industryBySize")],
    },
    "vehicle_auto": {
        "keywords": ["vehicle loan", "auto loan", "car loan", "fada", "auto retail",
                     "vehicle registration", "two-wheeler"],
        "signals": ["sibc-pl-vehicle-yoy", "sibc-pl-vehicle-share"],
        "cards": [("sibc", "personalLoans")],
    },
    "housing": {
        "keywords": ["home loan", "housing finance", "housing loan", "hfc", "mortgage"],
        "signals": ["sibc-pl-housing-yoy", "sibc-pl-housing-share"],
        "cards": [("sibc", "personalLoans"), ("sibc", "services")],
    },
    "payments_infra": {
        "keywords": ["upi", "pos terminal", "qr code", "payments infra", "acceptance",
                     "debit card", "atm"],
        "signals": ["pos-terminals-abs", "pos-terminals-yoy", "upi-qr-yoy", "dc-outstanding-yoy"],
        "cards": [("atm_pos", "infra"), ("atm_pos", "dc")],
    },
    "agriculture": {
        "keywords": ["agriculture credit", "agri loan", "farm credit", "kisan", "rural credit"],
        "signals": ["sibc-agriculture-yoy"],
        "cards": [("sibc", "mainSectors"), ("sibc", "prioritySector")],
    },
    "nbfc_services": {
        "keywords": ["nbfc", "bank lending to nbfc", "services credit", "shadow bank"],
        "signals": ["sibc-services-yoy"],
        "cards": [("sibc", "services")],
    },
}

# SEBI guardrail — analytics language only, everywhere, always. A draft with any
# of these NEVER reaches the review queue (word-boundary, case-insensitive).
SEBI_BANNED = ["buy", "sell", "target price", "price target", "accumulate", "book profit",
               "book profits", "multibagger", "go long", "go short", "stop loss", "stoploss",
               "entry price", "exit price", "upside", "downside target", "rerating", "re-rating",
               "undervalued", "overvalued", "cheap stock", "invest in", "add on dips"]


def detect_topics(text, max_topics=2):
    t = text.lower()
    scored = [(sum(1 for k in cfg["keywords"] if k in t), tid) for tid, cfg in TOPICS.items()]
    return [tid for n, tid in sorted(scored, reverse=True) if n > 0][:max_topics]


def _cards_for(pipeline, section, keywords, cap=3):
    """Verbatim validated insight lines for a section — topic-relevant first.
    A section can hold many cards (personalLoans has ~19); surface the ones whose
    text matches the topic, else fall back to the section's leads."""
    section_cards = [c for c in src.insight_cards(pipeline, max_cards=99, per_section=99)
                     if c["where"] == section]
    hit = [c for c in section_cards
           if any(k in (c["title"] + " " + c["body"]).lower() for k in keywords)]
    return (hit or section_cards[:2])[:cap]


def brief(text):
    topics = detect_topics(text)
    if not topics:
        print("No topic match — reply desk covers: " + ", ".join(TOPICS))
        return 1
    registry = src.load_registry()
    for tid in topics:
        cfg = TOPICS[tid]
        print(f"\n═══ {tid} ═══")
        print("  Signals (signals.db, latest period — quote these values exactly):")
        by_pipe = {}
        for sid in cfg["signals"]:
            sig = registry.get(sid)
            if not sig:
                continue
            pl = sig["pipeline"]
            vals = by_pipe.setdefault(pl, src.total_values(pl, src.latest_period(pl)))
            if sid in vals:
                v, u, s = vals[sid]
                print(f"    {sid}: {src.fmt_value(v, u)}  [{s}]  ({sig['title']})")
        print("  Validated card lines (verbatim ammunition):")
        for pl, section in cfg["cards"]:
            for c in _cards_for(pl, section, cfg["keywords"]):
                print(f"    · {c['title']}")
        print(f"  Declared scope for `check`: --topics {tid}")
    print("\nDraft rules: ≤280 chars, ONE number carried exactly as printed above, no links, "
          "no advice language. Then run `check` before review.")
    return 0


def check(draft, topics):
    """Gate a draft: SEBI lint + every number traces to the declared topics' signals."""
    failures = []
    low = draft.lower()
    for term in SEBI_BANNED:
        if re.search(rf"\b{re.escape(term)}\b", low):
            failures.append(f"SEBI lint: banned term {term!r}")
    sids = [s for t in topics for s in TOPICS.get(t, {}).get("signals", [])]
    legit = declared_ground_truth(sids)
    clean = re.sub(r"\b(?:19|20)\d\d\b", " ", draft)          # years are not data claims
    for num in extract_numbers(clean, POLICY):
        if not matches(num, legit, POLICY) and not ratio_matches(num, legit, POLICY):
            failures.append(f"ungrounded number {num} (scope: {', '.join(sids) or 'none declared'})")
    if failures:
        for f in failures:
            print(f"  ✗ {f}")
        print("✗ BLOCKED — fix the draft; it must not reach the review queue")
        return 1
    print("✓ draft clean — grounded and SEBI-safe; ready for human review")
    return 0


def log_reply(url, topic, text):
    entries = json.loads(LOG.read_text()) if LOG.exists() else []
    entries.append({"date": date.today().isoformat(), "url": url, "topic": topic, "text": text})
    LOG.write_text(json.dumps(entries, indent=2, ensure_ascii=False))
    print(f"logged ({len(entries)} replies on record)")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("brief");  b.add_argument("text")
    c = sub.add_parser("check");  c.add_argument("draft"); c.add_argument("--topics", default="")
    l = sub.add_parser("log");    l.add_argument("--url", required=True)
    l.add_argument("--topic", required=True); l.add_argument("--text", required=True)
    a = ap.parse_args()
    if a.cmd == "brief":
        return brief(a.text)
    if a.cmd == "check":
        topics = [t for t in a.topics.split(",") if t] or detect_topics(a.draft)
        return check(a.draft, topics)
    return log_reply(a.url, a.topic, a.text)


if __name__ == "__main__":
    sys.exit(main())
