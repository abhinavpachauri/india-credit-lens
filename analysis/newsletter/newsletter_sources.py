#!/usr/bin/env python3
"""
newsletter_sources.py — the newsletter's data layer (v2)
--------------------------------------------------------
Everything a newsletter issue can say comes from here, and everything here comes
from artifacts the ingestion gates already validated:

  signals.db                          → headline stats, status flips, new trackers
  web/public/data/sibc_l1_annotations.json   → SIBC insight cards (Check 2g validated)
  web/public/data/atm_pos_insights.json      → payments insight cards (Stage 4c validated)
  web/public/data/opportunities_feed.json    → L2/L3 cards incl. ecosystem basis (Check 4f validated)

No hand-authored stats, no LLM calls, no retired artifacts (subsystems/mermaid).
The generators compose; this module only reads and computes.
"""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

DB = ROOT / "analysis" / "signals" / "signals.db"
REGISTRY = ROOT / "analysis" / "signals" / "registry.json"
DATA = ROOT / "web" / "public" / "data"

PIPE_LABEL = {"sibc": "Credit", "atm_pos": "Payments"}

# What leads each release read, per pipeline. Order matters; missing signals are skipped.
HEADLINE_SIGNALS = {
    "sibc": ["sibc-bank-credit-abs", "sibc-bank-credit-yoy", "sibc-nonfood-credit-yoy",
             "sibc-personal-loans-yoy"],
    "atm_pos": ["cc-outstanding-abs", "cc-outstanding-yoy", "dc-outstanding-abs",
                "pos-terminals-abs", "pos-terminals-yoy"],
}

# Plain words for signal statuses — no analyst jargon on the reader's side.
STATUS_WORD = {
    "strengthening": "accelerating", "active": "growing steadily", "weakening": "slowing",
    "declining": "falling", "stable": "steady", "improving": "improving",
    "unknown": "no clear read",
}


def load_registry():
    return json.loads(REGISTRY.read_text())["signals"]


def _con():
    return sqlite3.connect(f"file:{DB}?mode=ro", uri=True)


def latest_period(pipeline):
    con = _con()
    row = con.execute("select max(period) from signals where pipeline=?", (pipeline,)).fetchone()
    con.close()
    return row[0] if row else None


def prior_period(pipeline, period):
    con = _con()
    row = con.execute("select max(period) from signals where pipeline=? and period<?",
                      (pipeline, period)).fetchone()
    con.close()
    return row[0] if row else None


def total_values(pipeline, period):
    """metric_id → (value, unit, status) at total level for one period."""
    con = _con()
    out = {m: (v, u, s) for m, v, u, s in con.execute(
        "select metric_id, value, unit, status from signals "
        "where pipeline=? and period=? and (entity_type='total' or entity_id='total')",
        (pipeline, period))}
    con.close()
    return out


def fmt_value(value, unit):
    """Render a db value the way the dashboards do — same rounding the checks accept."""
    if value is None:
        return ""
    if unit == "pct":
        return f"{value:.1f}%"
    if unit == "pp":
        return f"{value:.1f}pp"
    if unit == "lcr_cr":                       # stored in ₹ crore → shown in lakh crore
        return f"₹{value / 1e5:.1f}L Cr"
    if unit == "count":
        if abs(value) >= 1e7:
            return f"{value / 1e7:.1f} crore"
        if abs(value) >= 1e5:
            return f"{value / 1e5:.1f} lakh"
        return f"{value:,.0f}"
    return f"{value:,.1f}"


def headline_stats(pipeline, period):
    """The 3-5 numbers the issue opens with."""
    registry = load_registry()
    vals = total_values(pipeline, period)
    out = []
    for sid in HEADLINE_SIGNALS.get(pipeline, []):
        if sid in vals and sid in registry:
            v, u, s = vals[sid]
            out.append({"id": sid, "title": registry[sid]["title"],
                        "display": fmt_value(v, u), "status": s,
                        "status_word": STATUS_WORD.get(s, s)})
    return out


def status_flips(pipeline, period, prior):
    """Signals whose status changed between the two periods — the 'what changed' list."""
    registry = load_registry()
    con = _con()
    rows = con.execute(
        "select a.metric_id, b.status, a.status, a.value, a.unit from signals a "
        "join signals b on a.metric_id=b.metric_id and a.pipeline=b.pipeline "
        "  and a.entity_type=b.entity_type and a.entity_id=b.entity_id "
        "where a.pipeline=? and a.period=? and b.period=? "
        "  and (a.entity_type='total' or a.entity_id='total') and a.status != b.status "
        "order by a.metric_id", (pipeline, period, prior)).fetchall()
    con.close()
    out = []
    for mid, was, now, value, unit in rows:
        sig = registry.get(mid)
        if not sig or sig.get("current_status") == "retired":
            continue
        out.append({"id": mid, "title": sig["title"],
                    "was": STATUS_WORD.get(was, was), "now": STATUS_WORD.get(now, now),
                    "display": fmt_value(value, unit)})
    return out


def new_signals(pipeline, period):
    """Trackers added to the registry this cycle (first_seen == period)."""
    return [{"id": sid, "title": s["title"]}
            for sid, s in load_registry().items()
            if s.get("pipeline") == pipeline and s.get("first_seen") == period]


def insight_cards(pipeline, max_cards=6):
    """One validated insight card per section/group, in fixed order — deterministic pick."""
    cards = []
    if pipeline == "sibc":
        feed = json.loads((DATA / "sibc_l1_annotations.json").read_text())
        for section, bucket in feed["sections"].items():
            for it in bucket.get("insights", []):
                cards.append({"where": section, "title": it["title"], "body": it["body"],
                              "implication": it.get("implication", "")})
                break                                   # first per section
    else:
        feed = json.loads((DATA / "atm_pos_insights.json").read_text())
        seen = set()
        for it in feed:
            if it.get("type") != "insight" or it.get("group") in seen:
                continue
            seen.add(it.get("group"))
            cards.append({"where": it.get("group", ""), "title": it["title"], "body": it["body"],
                          "implication": it.get("implication", "")})
    return cards[:max_cards]


def opportunities_feed():
    return json.loads((DATA / "opportunities_feed.json").read_text())
