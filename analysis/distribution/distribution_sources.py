#!/usr/bin/env python3
"""
distribution_sources.py — the distribution layer's data layer
--------------------------------------------------------------
DISTRIBUTION_SPEC §1: distribution is a rendering problem over artifacts the pipelines
already compute. This module is the single read path. Every channel renderer sits on
top of it, and no renderer re-derives a number.

It absorbed `newsletter/newsletter_sources.py` on 2026-07-21 — the newsletter was never a
separate system, only the long-form channel of this one. The first half below is what that
module owned (db access, period arithmetic, value formatting, status wording); the second
half is what distribution adds:

  claims by CATEGORY   the §3 partition applied to validated feed cards
  data vintage         each pipeline's own data month, read fresh every run (§13.2)
  turns / corrections   the two categories that are computed from history, not cards
  watchlist            proximity-to-threshold, from the signal layer (signals/proximity.py)

Everything returned here is a `claim`: a title, prose that already passed a gate, the
signal ids behind it, and the numbers it states. That is the only shape the renderers see.
"""
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

from core.traceability import SIBC as POLICY, extract_numbers      # noqa: E402
from distribution import categories as cats
from distribution import slot_render                        # noqa: E402
from signals import proximity                                      # noqa: E402

PIPELINES = ("sibc", "atm_pos")

MONTH_NAME = ["", "January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]


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


def data_month(pipeline, period):
    """The month the DATA is about — not the release date. SIBC periods are keyed by
    dataDate (release day, e.g. 2026-06-30 for May data); the true data month is the
    timeline's csv_date. Payments periods already are the data month."""
    if pipeline == "sibc":
        timeline = json.loads((ROOT / "analysis/rbi_sibc/timeline.json").read_text())
        for e in timeline.get("periods", []):
            if e.get("dataDate") == period:
                return e.get("csv_date", period)
    return period


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


SECTION_NAME = {  # feed section/group key → the label the reader sees on the dashboard
    "bankCredit": "Bank Credit", "mainSectors": "Main Sectors", "industryBySize": "Industry by Size",
    "services": "Services", "personalLoans": "Personal Loans", "prioritySector": "Priority Sector",
    "industryByType": "Industry by Type",
    "cc": "Credit Cards", "dc": "Debit Cards", "infra": "Infrastructure",
}
MODE_NAME = {"absolute": "Absolute", "yoy": "YoY %", "fy": "FY Cumul.", "mom": "MoM %",
             "share": "% Share (Distribution tab)", "pct": "% Share (Distribution tab)"}


def _chart_recipe(pipeline, section_key, highlight, mode):
    """The exact screenshot instruction for a card — dashboard → section → mode → series."""
    dash = "indiacreditlens.com" if pipeline == "sibc" else "indiacreditlens.com/payments"
    parts = [f"{dash} → {SECTION_NAME.get(section_key, section_key)}"]
    if mode:
        parts.append(f"{MODE_NAME.get(mode, mode)} view")
    if highlight:
        parts.append("highlight: " + ", ".join(highlight[:3]))
    return " → ".join(parts)


def insight_cards(pipeline, max_cards=6, per_section=1):
    """Validated insight cards in fixed section order — deterministic pick.
    The newsletter takes 1 per section (default); the reply desk asks for all
    (per_section high) and filters by topic. Each card carries its chart recipe."""
    cards = []
    if pipeline == "sibc":
        feed = json.loads((DATA / "sibc_l1_annotations.json").read_text())
        for section, bucket in feed["sections"].items():
            for it in bucket.get("insights", [])[:per_section]:
                cards.append({"where": section, "title": it["title"], "body": it["body"],
                              "implication": it.get("implication", ""),
                              "chart": _chart_recipe(pipeline, section,
                                                     (it.get("effect") or {}).get("highlight"),
                                                     it.get("preferredMode"))})
    else:
        feed = json.loads((DATA / "atm_pos_insights.json").read_text())
        count = {}
        for it in feed:
            g = it.get("group", "")
            if it.get("type") != "insight" or count.get(g, 0) >= per_section:
                continue
            count[g] = count.get(g, 0) + 1
            eff = it.get("effect") or {}
            cards.append({"where": g, "title": it["title"], "body": it["body"],
                          "implication": it.get("implication", ""),
                          "chart": _chart_recipe(pipeline, g,
                                                 eff.get("highlight"), eff.get("trendMode"))})
    return cards[:max_cards]


def opportunities_feed():
    return json.loads((DATA / "opportunities_feed.json").read_text())


# ── Vintage ───────────────────────────────────────────────────────────────────
# Never assume the two pipelines are on the same data month (§13.2). Read it.

def _month_label(iso):
    y, m, _ = iso.split("-")
    return f"{MONTH_NAME[int(m)]} {y}"


def data_vintage():
    """Each pipeline's latest period, the month its DATA is about, and the gap between them."""
    out = {}
    for pl in PIPELINES:
        period = latest_period(pl)
        if not period:
            continue
        month = data_month(pl, period)
        out[pl] = {"period": period, "data_month": month, "label": _month_label(month)}
    if len(out) == 2:
        a, b = (out[p]["data_month"] for p in PIPELINES)
        ay, am = int(a[:4]), int(a[5:7])
        by, bm = int(b[:4]), int(b[5:7])
        out["gap_months"] = (ay * 12 + am) - (by * 12 + bm)
    return out


def vintage_sentence(vintage):
    """The honest one-liner the merged issue opens with (§11.1). Never smoothed over."""
    sibc, atm = vintage.get("sibc"), vintage.get("atm_pos")
    if not (sibc and atm):
        return ""
    gap = vintage.get("gap_months", 0)
    if gap == 0:
        return (f"Both halves are on the same data month: {sibc['label']} credit data and "
                f"{atm['label']} payments data.")
    months = "month" if abs(gap) == 1 else "months"
    ahead, behind = ("credit", "payments") if gap > 0 else ("payments", "credit")
    return (f"{sibc['label']} credit data, {atm['label']} payments data — the two RBI releases "
            f"run on different clocks, so the {ahead} half is {abs(gap)} {months} ahead of the "
            f"{behind} half.")


# ── Claims from validated feed cards ──────────────────────────────────────────

def _claim(pipeline, cid, title, body, implication, signal_ids, source):
    text = " ".join(x for x in (title, body, implication) if x)
    return {
        "id": cid,
        "pipeline": pipeline,
        "title": title,
        "body": body,
        "implication": implication or "",
        "signal_ids": sorted(set(signal_ids)),
        "numbers": extract_numbers(text, POLICY),
        "source": source,
        "verbatim": True,          # prose came from a gate-validated feed; never reword it
    }


def _atm_signal_ids(card):
    """Registry signal ids an ATM/POS card cites.

    Two shapes coexist by design: LLM-represented cards name their anchor in
    `eval_signal`, relational cards key their reasoning rows as `{signal_id}:{entity}`.
    Deterministic cards built from signals.json paths cite no registry id — those fall
    through to the artifact-level category assignment in `cards()`.
    """
    ids = []
    if card.get("eval_signal"):
        ids.append(card["eval_signal"])
    for row in (card.get("reasoning") or {}).get("signals", []):
        key = row.get("key", "")
        if ":" in key and not key.startswith("groups."):
            ids.append(key.split(":", 1)[0])
    return ids


# Deterministic ATM/POS cards cite signals.json paths rather than registry ids. Their
# `cut` says which question they answer, which is enough for the partition.
CUT_CATEGORY = {"top_n": "C4", "by_type": "C4", "distribution": "C4", "total": "C1"}


def cards(pipeline, registry=None):
    """Every validated insight card for a pipeline, each tagged with its category."""
    registry = registry or load_registry()
    out = []
    if pipeline == "sibc":
        feed = json.loads((DATA / "sibc_l1_annotations.json").read_text())
        for section, bucket in feed["sections"].items():
            for it in bucket.get("insights", []):
                # SIBC card ids ARE registry signal ids — the feed is one card per signal.
                c = _claim("sibc", it["id"], it["title"], it["body"], it.get("implication"),
                           [it["id"]], f"sibc_l1_annotations.json → {section}")
                c["category"] = cats.category_of_signals([it["id"]], registry)
                c["where"] = section
                out.append(c)
    else:
        feed = json.loads((DATA / "atm_pos_insights.json").read_text())
        for it in feed:
            if it.get("type") != "insight":
                continue
            sids = _atm_signal_ids(it)
            c = _claim("atm_pos", it["id"], it["title"], it["body"], it.get("implication"),
                       sids, f"atm_pos_insights.json → {it.get('group', '')}")
            c["category"] = (cats.category_of_signals(sids, registry)
                             or CUT_CATEGORY.get(it.get("cut")))
            c["where"] = it.get("group", "")
            out.append(c)
    return out


def cards_for_category(category, registry=None):
    """All validated cards belonging to one category, both pipelines, credit first."""
    registry = registry or load_registry()
    return [c for pl in PIPELINES for c in cards(pl, registry) if c.get("category") == category]


def diversify(claims, limit):
    """Pick `limit` claims spread across pipelines and sections, best-first within each.

    Taking the first N in feed order looks fine until you read the result: the credit
    feed lists bank credit first, so a merged monthly summary comes out as four bank
    credit lines and no payments at all. Round-robin over (pipeline, section) buckets
    keeps the order the feed chose *within* a bucket while guaranteeing the slot spans
    what it claims to span.
    """
    buckets = {}
    for c in claims:
        buckets.setdefault((c.get("category"), c.get("pipeline"), c.get("where")), []).append(c)
    out = []
    while len(out) < limit and any(buckets.values()):
        for key in list(buckets):
            if not buckets[key]:
                continue
            out.append(buckets[key].pop(0))
            if len(out) >= limit:
                break
    return out


def prioritise(claims, preferred_ids):
    """Float the signals a category leads with to the front; leave the rest in order."""
    rank = {sid: i for i, sid in enumerate(preferred_ids)}
    return sorted(claims, key=lambda c: min((rank.get(s, 999) for s in c["signal_ids"]),
                                            default=999))


def headline_ids():
    """The signals a monthly summary opens with — the newsletter already decided these,
    and a second list that drifts from it is exactly the parallel copy we don't allow."""
    return [sid for pl in PIPELINES for sid in HEADLINE_SIGNALS.get(pl, [])]


# ── C5 Turns — computed from history, not from cards ──────────────────────────

def turns():
    """Status flips since the prior period, both pipelines. The 'what changed direction' list."""
    out = []
    for pl in PIPELINES:
        period = latest_period(pl)
        prior = prior_period(pl, period) if period else None
        if not prior:
            continue
        for f in status_flips(pl, period, prior):
            out.append({
                "id": f["id"], "pipeline": pl, "category": "C5",
                "title": f["title"],
                "body": f"{f['title']} — was {f['was']}, now {f['now']} at {f['display']}.",
                "implication": "", "signal_ids": [f["id"]],
                "numbers": extract_numbers(f["display"], POLICY),
                "source": "signals.db — status change vs prior period",
                "verbatim": False,      # our own words over db values; the gate checks them
            })
    return out


# ── C6 / C7 — model-driven, straight off the opportunities feed ───────────────

def _lede(title, body):
    """Title plus a quotable sentence — an opportunity's title alone is only a label.

    Takes the first sentence that is fit to quote as-is. Some upstream narrative
    sentences carry machine formatting ("120454115.0 credit cards"); this layer curates
    validated prose and never rewords it, so the honest move is to quote a different
    sentence — and if none qualifies, to say only the title rather than tidy one up.
    """
    for sentence in re.split(r"(?<=[.!?])\s+", (body or "").strip()):
        if sentence and slot_render.is_presentable(sentence):
            return f"{title} — {sentence}"
    return title

def opportunity_claims(cross_system):
    """C7 when cross_system, else C6. Openings and risks are model output, never inference."""
    feed = opportunities_feed()
    items = (feed.get("cross_system", []) if cross_system
             else [x for v in feed.get("pipelines", {}).values() for x in v])
    out = []
    for it in items:
        if it.get("status") in ("closed", "retired"):
            continue
        evidence = it.get("evidence_all") or it.get("evidence") or []
        sids = [e.get("signal_id", e) if isinstance(e, dict) else e for e in evidence]
        c = _claim(it.get("pipeline", "cross"), it.get("id", ""), it.get("title", ""),
                   it.get("body", "") or it.get("narrative", ""), it.get("implication"),
                   [s for s in sids if isinstance(s, str)],
                   "opportunities_feed.json")
        c["category"] = "C7" if cross_system else "C6"
        c["where"] = it.get("driver_kind", "")
        c["lede"] = _lede(c["title"], c["body"])
        c["opportunity_status"] = it.get("status", "")
        c["basis"] = it.get("basis")
        out.append(c)
    return out


# ── C8 Watchlist — the one net-new computation (§6) ───────────────────────────

def watchlist(top_n=3):
    """Signals closest to flipping status, ranked by how many typical monthly moves away."""
    out = []
    for row in proximity.ranked(limit=top_n):
        out.append({
            "id": row["signal_id"], "pipeline": row["pipeline"], "category": "C8",
            "title": row["title"],
            "body": proximity.sentence(row),
            "implication": "", "signal_ids": [row["signal_id"]],
            "numbers": extract_numbers(proximity.sentence(row), POLICY),
            "source": "signals/proximity.py — distance to the next status flip",
            "verbatim": False,
            "lede": proximity.short_sentence(row),
            "proximity": row,
        })
    return out


# ── C9 Corrections — where an earlier read was wrong ──────────────────────────

def corrections(ledger_entries):
    """Two honest sources: a published claim whose signal has since flipped, and a
    tracker we retired. Both are facts about our own record, so the ledger is an input
    here — the one place it feeds generation rather than only verifying it."""
    registry = load_registry()
    out, seen = [], set()

    published = {}
    for e in ledger_entries:
        for sid in e.get("signal_ids", []):
            published.setdefault(sid, e)

    for sid, entry in published.items():
        sig = registry.get(sid)
        if not sig or sid in seen:
            continue
        was = entry.get("statuses", {}).get(sid)
        now = sig.get("current_status")
        if was and now and was != now:
            seen.add(sid)
            out.append({
                "id": sid, "pipeline": sig.get("pipeline", ""), "category": "C9",
                "title": sig.get("title", sid),
                "body": (f"On {entry.get('date')} we published this as "
                         f"{STATUS_WORD.get(was, was)}. It now reads "
                         f"{STATUS_WORD.get(now, now)}."),
                "implication": "", "signal_ids": [sid], "numbers": [],
                "source": f"distribution_ledger.json → {entry.get('date')}",
                "verbatim": False,
            })

    for sid, sig in registry.items():
        if sig.get("current_status") == "retired" and sig.get("retire_period") and sid not in seen:
            out.append({
                "id": sid, "pipeline": sig.get("pipeline", ""), "category": "C9",
                "title": sig.get("title", sid),
                "body": (f"We stopped tracking this in {_month_label(sig['retire_period'])}. "
                         f"{sig.get('retire_reason', '')}").strip(),
                "implication": "", "signal_ids": [], "numbers": [],
                "source": "registry.json — retired tracker",
                "verbatim": False,
            })
    return out


def current_statuses(signal_ids):
    """Status snapshot to record in the ledger, so C9 can later detect our own reversals."""
    registry = load_registry()
    return {sid: registry[sid].get("current_status") for sid in signal_ids if sid in registry}
