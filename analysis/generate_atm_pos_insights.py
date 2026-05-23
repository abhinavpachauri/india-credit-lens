#!/usr/bin/env python3
"""
Stage 4b — ATM/POS Insight Generation (deterministic, rule-based)
Reads signals.json and applies threshold-gated templates to produce structured
insight objects. No LLM involved — every claim is templated from signals.json.

Guard rail: validate_atm_pos_insights.py (Stage 4c) checks every number in
the output against signals.json before insights are used on the frontend.

Output: analysis/rbi_atm_pos/insights.json
        web/public/data/atm_pos_insights.json

Usage:
    python3 analysis/generate_atm_pos_insights.py
"""

import json
import shutil
from pathlib import Path

ROOT        = Path(__file__).parent.parent
SIGNALS_IN  = ROOT / "analysis/rbi_atm_pos/signals.json"
OUT_PATH    = ROOT / "analysis/rbi_atm_pos/insights.json"
WEB_PATH    = ROOT / "web/public/data/atm_pos_insights.json"

# ── Metric labels (human-readable) ────────────────────────────────────────────

METRIC_LABEL = {
    "credit_cards":             "credit cards outstanding",
    "debit_cards":              "debit cards outstanding",
    "cc_pos_txn_vol":           "CC POS transaction volume",
    "cc_pos_txn_val":           "CC POS transaction value",
    "cc_ecom_txn_vol":          "CC ecommerce transaction volume",
    "cc_ecom_txn_val":          "CC ecommerce transaction value",
    "cc_atm_withdrawal_vol":    "CC ATM withdrawal volume",
    "cc_atm_withdrawal_val":    "CC ATM withdrawal value",
    "cc_other_txn_vol":         "CC other transaction volume",
    "dc_atm_withdrawal_vol":    "DC ATM withdrawal volume",
    "dc_pos_txn_vol":           "DC POS transaction volume",
    "dc_ecom_txn_vol":          "DC ecommerce transaction volume",
    "dc_pos_withdrawal_vol":    "DC POS cash withdrawal volume",
    "pos_terminals":            "POS terminals",
    "upi_qr":                   "UPI QR codes",
    "atm_onsite":               "on-site ATMs",
    "atm_offsite":              "off-site ATMs",
    "micro_atms":               "Micro ATMs",
    "bharat_qr":                "Bharat QR codes",
}

METRIC_UNIT_LABEL = {
    "credit_cards":   "cards",
    "debit_cards":    "cards",
    "cc_pos_txn_vol": "transactions",
    "cc_ecom_txn_vol":"transactions",
    "pos_terminals":  "terminals",
    "upi_qr":         "codes",
    "micro_atms":     "units",
    "bharat_qr":      "codes",
}


def fmt_num(v: float, metric: str = "") -> str:
    """Format large numbers with B/M/K suffix."""
    if v >= 1e9:
        return f"{v/1e9:.2f}B"
    if v >= 1e7:
        return f"{v/1e6:.1f}M"
    if v >= 1e6:
        return f"{v/1e6:.2f}M"
    if v >= 1e3:
        return f"{v/1e3:.1f}K"
    return f"{v:,.0f}"


def streak_label(n: int, direction: str) -> str:
    if direction == "up":
        return f"{n} consecutive month{'s' if n > 1 else ''} of growth"
    if direction == "down":
        return f"{n} consecutive month{'s' if n > 1 else ''} of decline"
    return f"{n} month{'s' if n > 1 else ''} flat"


def sign(v: float) -> str:
    return f"+{v:.1f}" if v >= 0 else f"{v:.1f}"


def insight(id_, group, cut, period, title, body, effect, explore=None):
    return {
        "id":          id_,
        "group":       group,
        "cut":         cut,
        "period":      period,
        "title":       title,
        "body":        body,
        "effect":      effect,
        "exploreAction": explore,
    }


# ══════════════════════════════════════════════════════════════════════════════
# CC RULES
# ══════════════════════════════════════════════════════════════════════════════

def cc_ecom_vs_pos(s, month) -> dict | None:
    """CC ecommerce share of total volume vs POS — milestone if > 50%."""
    cross = s["groups"]["cc"]["total"]["cross"]
    ecom  = cross.get("cc_ecom_txn_vol", {})
    pos   = cross.get("cc_pos_txn_vol", {})
    ecom_sh  = ecom.get("share_pct")
    pos_sh   = pos.get("share_pct")
    ecom_pr  = ecom.get("prior_share_pct")
    delta    = ecom.get("share_delta_pp")

    if ecom_sh is None or pos_sh is None:
        return None

    if ecom_sh >= 50:
        title = (
            f"CC ecommerce exceeds POS for the {'first time' if ecom_pr and ecom_pr < 50 else f'{round(ecom_sh,1)}% of total CC volume'}"
            if ecom_pr and ecom_pr < 50
            else f"CC ecommerce holds above POS at {ecom_sh:.1f}% of total CC volume"
        )
        delta_str = f" ({sign(delta)}pp vs prior month)" if delta is not None else ""
        body = (
            f"In {month}, ecommerce accounted for {ecom_sh:.1f}%{delta_str} of total CC transaction volume "
            f"vs POS at {pos_sh:.1f}%. "
            f"This structural shift — digital-first over in-store — has persisted for "
            f"{'multiple months' if (ecom_pr and ecom_pr >= 50) else 'the first time in this data series'}."
        )
    else:
        if delta is not None and delta > 0.5:
            title = f"CC ecommerce closing in on POS — now {ecom_sh:.1f}% of total volume"
            body = (
                f"In {month}, CC ecommerce is {ecom_sh:.1f}% of total CC transaction volume vs POS at {pos_sh:.1f}%. "
                f"Ecom gained {sign(delta)}pp vs prior month. The gap to POS is {pos_sh - ecom_sh:.1f}pp."
            )
        else:
            return None  # no notable move

    return insight(
        "cc-ecom-vs-pos-share", "cc", "total", month, title, body,
        effect={
            "highlight": ["Total"],
            "tab": "distribution",
            "distMode": "pct",
            "focusCard": "cc_ecom",
        },
        explore={"mode": "by_type"},
    )


def cc_atm_withdrawal_trend(s, month) -> dict | None:
    """CC ATM cash withdrawal declining = going cashless signal."""
    m = s["groups"]["cc"]["total"]["metrics"].get("cc_atm_withdrawal_vol", {})
    cross = s["groups"]["cc"]["total"]["cross"]
    atm_sh = cross.get("cc_atm_withdrawal_vol", {}).get("share_pct")
    atm_delta = cross.get("cc_atm_withdrawal_vol", {}).get("share_delta_pp")
    mom = m.get("mom_pct")
    streak = m.get("streak_months", 1)
    streak_dir = m.get("streak_dir", "flat")

    if mom is None:
        return None

    if streak_dir == "down" and streak >= 2:
        title = f"CC ATM cash withdrawals declining — {streak_label(streak, 'down')}"
        body = (
            f"CC ATM withdrawal volume fell {abs(mom):.1f}% MoM in {month}, "
            f"the {streak_label(streak, 'down')}. "
        )
        if atm_sh is not None:
            body += f"ATM cash now accounts for {atm_sh:.1f}% of total CC transaction volume"
            if atm_delta:
                body += f" ({sign(atm_delta)}pp vs prior month)"
            body += ". Credit cards are increasingly used for purchases, not cash."
        return insight(
            "cc-atm-declining", "cc", "total", month, title, body,
            effect={"highlight": ["Total"], "tab": "trend", "trendMode": "mom", "focusCard": "cc_atm"},
        )

    if streak_dir == "up" and streak >= 3 and mom > 3:
        title = f"CC ATM cash withdrawals rising — {streak_label(streak, 'up')} ({mom:+.1f}% MoM)"
        body = (
            f"CC ATM withdrawal volume grew {mom:.1f}% MoM in {month}, "
            f"the {streak_label(streak, 'up')}. "
        )
        if atm_sh:
            body += f"Cash accounts for {atm_sh:.1f}% of CC transaction volume."
        return insight(
            "cc-atm-rising", "cc", "total", month, title, body,
            effect={"highlight": ["Total"], "tab": "trend", "trendMode": "mom", "focusCard": "cc_atm"},
        )
    return None


def cc_cards_streak(s, month) -> dict | None:
    """CC cards outstanding — streak if ≥ 3 months."""
    m = s["groups"]["cc"]["total"]["metrics"].get("credit_cards", {})
    streak = m.get("streak_months", 1)
    streak_dir = m.get("streak_dir", "flat")
    latest = m.get("latest")
    mom = m.get("mom_pct")

    if streak < 3 or streak_dir == "flat":
        return None

    latest_fmt = fmt_num(latest)
    title = f"Credit cards outstanding: {streak_label(streak, streak_dir)} — {latest_fmt} cards"
    body = (
        f"Total credit cards outstanding reached {latest_fmt} in {month} ({mom:+.1f}% MoM), "
        f"marking the {streak_label(streak, streak_dir)}. "
        f"{'Issuance momentum is broad-based across bank types.' if streak_dir == 'up' else 'Card attrition or issuance slowdown is underway.'}"
    )
    return insight(
        "cc-cards-streak", "cc", "total", month, title, body,
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "credit_cards"},
        explore={"mode": "by_type"},
    )


def cc_category_share_shift(s, month) -> dict | None:
    """Category gaining/losing CC share — surface the biggest mover."""
    by_type = s["groups"]["cc"]["by_type"]
    cats    = by_type["categories"]
    gainer  = by_type.get("top_gainer")
    loser   = by_type.get("top_loser")

    if not gainer or not loser:
        return None
    g_delta = cats[gainer].get("share_delta_pp", 0) or 0
    l_delta = cats[loser].get("share_delta_pp", 0) or 0

    if abs(g_delta) < 0.05 and abs(l_delta) < 0.05:
        return None  # too small to call out

    g_sh = cats[gainer].get("share_pct", 0)
    l_sh = cats[loser].get("share_pct", 0)
    title = f"{gainer} banks gained CC card share in {month} (+{g_delta:.1f}pp)"
    body = (
        f"{gainer} banks hold {g_sh:.1f}% of total credit cards outstanding in {month} "
        f"({sign(g_delta)}pp vs prior month). "
        f"{loser} banks lost the most share at {sign(l_delta)}pp, now at {l_sh:.1f}%. "
        f"{'SFB growth in credit cards reflects increased fintech partnerships.' if gainer == 'SFB' else ''}"
        f"{'Private bank CC dominance continues to compound.' if gainer == 'Private' else ''}"
    )
    return insight(
        "cc-category-share-shift", "cc", "by_type", month, title, body,
        effect={
            "highlight": [gainer, "Total"],
            "tab": "distribution",
            "distMode": "pct",
            "focusCard": "credit_cards",
        },
        explore={"mode": "by_type"},
    )


def cc_top_bank_concentration(s, month) -> dict | None:
    """Top 5 CC concentration or notable rank change."""
    topn   = s["groups"]["cc"]["top_n"]
    banks  = topn["banks"]
    top5sh = topn.get("top5_share_pct")
    delta  = topn.get("top5_share_delta_pp")
    rank_changes = topn.get("rank_changes", [])
    leader = banks[0] if banks else None

    if not leader:
        return None

    if rank_changes:
        rc = rank_changes[0]
        direction = "up" if rc["to_rank"] < rc["from_rank"] else "down"
        title = f"{rc['name']} moves {'up' if direction == 'up' else 'down'} to #{rc['to_rank']} in CC cards"
        body = (
            f"{rc['name']} moved from #{rc['from_rank']} to #{rc['to_rank']} in credit cards outstanding "
            f"in {month}. "
        )
        if top5sh:
            body += f"Top 5 banks collectively hold {top5sh:.1f}% of total CC cards"
            if delta:
                body += f" ({sign(delta)}pp vs prior month)"
            body += "."
        return insight(
            "cc-top-bank-rank-change", "cc", "top_n", month, title, body,
            effect={"highlight": [rc["name"], "Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "credit_cards"},
            explore={"mode": "top_n", "topN": 10},
        )
    else:
        if top5sh is None:
            return None
        title = f"Top 5 banks hold {top5sh:.1f}% of CC cards — {leader['name']} leads at {leader['share_pct']:.1f}%"
        body = (
            f"In {month}, the top 5 banks account for {top5sh:.1f}% of total credit cards outstanding"
            f"{f' ({sign(delta)}pp vs prior month)' if delta else ''}. "
            f"{leader['name']} leads with {leader['share_pct']:.1f}% share "
            f"({leader['mom_pct']:+.1f}% MoM)."
        )
        return insight(
            "cc-top5-concentration", "cc", "top_n", month, title, body,
            effect={"highlight": [leader["name"], "Total"], "tab": "distribution", "distMode": "pct", "focusCard": "credit_cards"},
            explore={"mode": "top_n", "topN": 10},
        )


# ══════════════════════════════════════════════════════════════════════════════
# DC RULES
# ══════════════════════════════════════════════════════════════════════════════

def dc_atm_trend(s, month) -> dict | None:
    """DC ATM withdrawal trend — cash usage signal."""
    m      = s["groups"]["dc"]["total"]["metrics"].get("dc_atm_withdrawal_vol", {})
    cross  = s["groups"]["dc"]["total"]["cross"]
    atm_sh = cross.get("dc_atm_withdrawal_vol", {}).get("share_pct")
    atm_dt = cross.get("dc_atm_withdrawal_vol", {}).get("share_delta_pp")
    mom    = m.get("mom_pct")
    streak = m.get("streak_months", 1)
    sd     = m.get("streak_dir", "flat")

    if mom is None:
        return None

    if sd == "down" and streak >= 2:
        title = f"DC ATM cash withdrawals: {streak_label(streak, 'down')} — cash usage shifting"
        body = f"Debit card ATM withdrawal volume fell {abs(mom):.1f}% MoM in {month}, "
        body += f"the {streak_label(streak, 'down')}. "
        if atm_sh:
            body += f"ATM cash is {atm_sh:.1f}% of total DC transaction volume"
            if atm_dt:
                body += f" ({sign(atm_dt)}pp)"
            body += ". Debit cards are increasingly used for digital payments, not just ATM cash."
        return insight(
            "dc-atm-declining", "dc", "total", month, title, body,
            effect={"highlight": ["Total"], "tab": "trend", "trendMode": "mom", "focusCard": "dc_atm"},
        )

    if sd == "up" and streak >= 3:
        title = f"DC ATM withdrawals rising — {streak_label(streak, 'up')} ({mom:+.1f}% MoM)"
        body = f"Debit card ATM withdrawal volume grew {mom:.1f}% MoM in {month}. "
        if atm_sh:
            body += f"Cash accounts for {atm_sh:.1f}% of total DC volume."
        return insight(
            "dc-atm-rising", "dc", "total", month, title, body,
            effect={"highlight": ["Total"], "tab": "trend", "trendMode": "mom", "focusCard": "dc_atm"},
        )
    return None


def dc_ecom_share(s, month) -> dict | None:
    """DC ecom share of total DC vol — digital shift in debit."""
    cross  = s["groups"]["dc"]["total"]["cross"]
    ecom   = cross.get("dc_ecom_txn_vol", {})
    ecom_sh  = ecom.get("share_pct")
    ecom_pr  = ecom.get("prior_share_pct")
    delta    = ecom.get("share_delta_pp")

    if ecom_sh is None:
        return None
    if ecom_sh < 2 and (delta is None or abs(delta) < 0.3):
        return None  # too small

    atm_sh = cross.get("dc_atm_withdrawal_vol", {}).get("share_pct")

    title = f"DC ecommerce is {ecom_sh:.1f}% of total DC transaction volume in {month}"
    body = (
        f"Debit card ecommerce accounted for {ecom_sh:.1f}% of total DC transaction volume in {month}"
        f"{f' ({sign(delta)}pp vs prior month)' if delta else ''}. "
    )
    if atm_sh:
        body += f"ATM cash still dominates at {atm_sh:.1f}%. "
    body += "The structural shift away from cash toward digital payments is ongoing."

    return insight(
        "dc-ecom-share", "dc", "total", month, title, body,
        effect={"highlight": ["Total"], "tab": "distribution", "distMode": "pct", "focusCard": "dc_ecom"},
        explore={"mode": "by_type"},
    )


def dc_cards_streak(s, month) -> dict | None:
    """DC cards outstanding streak."""
    m      = s["groups"]["dc"]["total"]["metrics"].get("debit_cards", {})
    streak = m.get("streak_months", 1)
    sd     = m.get("streak_dir", "flat")
    latest = m.get("latest")
    mom    = m.get("mom_pct")

    if streak < 4 or sd == "flat":
        return None  # higher bar for DC (slower moving)

    title = f"Debit cards: {streak_label(streak, sd)} — {fmt_num(latest)} outstanding"
    body = (
        f"Total debit cards outstanding reached {fmt_num(latest)} in {month} ({mom:+.1f}% MoM), "
        f"the {streak_label(streak, sd)}. "
        f"{'With over 1B cards, India debit base continues to expand.' if latest > 1e9 else ''}"
    )
    return insight(
        "dc-cards-streak", "dc", "total", month, title, body,
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "debit_cards"},
        explore={"mode": "by_type"},
    )


def dc_category_dominance(s, month) -> dict | None:
    """PSB dominance in debit cards — structural story."""
    by_type = s["groups"]["dc"]["by_type"]
    cats    = by_type["categories"]
    psb     = cats.get("PSB", {})
    private = cats.get("Private", {})
    gainer  = by_type.get("top_gainer")
    loser   = by_type.get("top_loser")

    psb_sh    = psb.get("share_pct")
    psb_delta = psb.get("share_delta_pp")
    priv_sh   = private.get("share_pct")

    if psb_sh is None:
        return None

    title = f"PSB banks hold {psb_sh:.1f}% of debit cards — {gainer} gaining share in {month}"
    body = (
        f"Public sector banks account for {psb_sh:.1f}% of total debit cards outstanding in {month}"
        f"{f' ({sign(psb_delta)}pp vs prior month)' if psb_delta else ''}. "
        f"Private banks hold {priv_sh:.1f}%. "
        f"{(gainer + ' banks are the fastest-growing category (' + sign(cats[gainer].get('share_delta_pp',0)) + 'pp share gain).') if gainer else ''}"
    )
    return insight(
        "dc-psb-dominance", "dc", "by_type", month, title, body,
        effect={
            "highlight": ["PSB", gainer, "Total"] if gainer and gainer != "PSB" else ["PSB", "Total"],
            "tab": "distribution",
            "distMode": "pct",
            "focusCard": "debit_cards",
        },
        explore={"mode": "by_type"},
    )


def dc_top_bank(s, month) -> dict | None:
    """Top DC bank + concentration."""
    topn   = s["groups"]["dc"]["top_n"]
    banks  = topn["banks"]
    top5sh = topn.get("top5_share_pct")
    delta  = topn.get("top5_share_delta_pp")
    leader = banks[0] if banks else None
    rank_changes = topn.get("rank_changes", [])

    if not leader:
        return None

    if rank_changes:
        rc = rank_changes[0]
        title = f"{rc['name']} moves to #{rc['to_rank']} in debit cards (from #{rc['from_rank']})"
        body = f"{rc['name']} shifted from #{rc['from_rank']} to #{rc['to_rank']} in {month}. "
        if top5sh:
            body += f"Top 5 banks: {top5sh:.1f}% of total DC cards{f' ({sign(delta)}pp)' if delta else ''}."
        return insight(
            "dc-top-bank-rank-change", "dc", "top_n", month, title, body,
            effect={"highlight": [rc["name"], "Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "debit_cards"},
            explore={"mode": "top_n", "topN": 10},
        )

    title = f"{leader['name']} leads DC cards at {leader['share_pct']:.1f}%"
    body = (
        f"{leader['name']} holds {leader['share_pct']:.1f}% of total debit cards in {month} "
        f"({leader['mom_pct']:+.1f}% MoM). "
        f"Top 5 banks account for {top5sh:.1f}%{f' ({sign(delta)}pp vs prior month)' if delta else ''}."
    )
    return insight(
        "dc-top-bank-leader", "dc", "top_n", month, title, body,
        effect={"highlight": [leader["name"], "Total"], "tab": "distribution", "distMode": "pct", "focusCard": "debit_cards"},
        explore={"mode": "top_n", "topN": 10},
    )


# ══════════════════════════════════════════════════════════════════════════════
# INFRA RULES
# ══════════════════════════════════════════════════════════════════════════════

def infra_qr_per_pos(s, month) -> dict | None:
    """UPI QR codes per POS terminal — infrastructure tipping point."""
    metrics = s["groups"]["infra"]["total"]["metrics"]
    upi_sig = metrics.get("upi_qr", {})
    pos_sig = metrics.get("pos_terminals", {})
    upi_v   = upi_sig.get("latest")
    pos_v   = pos_sig.get("latest")
    upi_pr  = upi_sig.get("prior")
    pos_pr  = pos_sig.get("prior")
    upi_mom = upi_sig.get("mom_pct")
    pos_mom = pos_sig.get("mom_pct")

    if upi_v is None or pos_v is None or pos_v == 0:
        return None

    latest = round(upi_v / pos_v)
    prior  = round(upi_pr / pos_pr) if (upi_pr and pos_pr and pos_pr > 0) else None

    title = f"India now has {latest:.0f} UPI QR codes per POS terminal"
    body = (
        f"As of {month}, there are {latest:.0f} UPI QR codes ({fmt_num(upi_sig.get('latest',0))}) "
        f"for every POS terminal ({fmt_num(pos_sig.get('latest',0))}). "
    )
    if prior:
        body += f"This ratio was {prior:.0f} in the prior month. "
    if upi_mom is not None and pos_mom is not None:
        body += (
            f"UPI QR grew {upi_mom:+.1f}% MoM vs POS terminals at {pos_mom:+.1f}% MoM — "
            f"digital acceptance infrastructure is {'outpacing' if upi_mom > pos_mom else 'growing in line with'} hardware deployment."
        )
    return insight(
        "infra-qr-per-pos", "infra", "total", month, title, body,
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "upi_qr"},
        explore={"mode": "by_type"},
    )


def infra_pos_streak(s, month) -> dict | None:
    """POS terminal growth streak."""
    m      = s["groups"]["infra"]["total"]["metrics"].get("pos_terminals", {})
    streak = m.get("streak_months", 1)
    sd     = m.get("streak_dir", "flat")
    latest = m.get("latest")
    mom    = m.get("mom_pct")

    if streak < 3 or sd == "flat":
        return None

    title = f"POS terminals: {streak_label(streak, sd)} — {fmt_num(latest)} deployed"
    body = (
        f"POS terminals reached {fmt_num(latest)} in {month} ({mom:+.1f}% MoM), "
        f"the {streak_label(streak, sd)}. "
        f"{'Physical acceptance infrastructure continues to expand.' if sd == 'up' else 'POS terminal count is contracting — QR-first acceptance may be replacing hardware.'}"
    )
    return insight(
        "infra-pos-streak", "infra", "total", month, title, body,
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "pos_terminals"},
        explore={"mode": "by_type"},
    )


def infra_upi_vs_bharat_qr(s, month) -> dict | None:
    """UPI QR vs Bharat QR divergence."""
    m_upi   = s["groups"]["infra"]["total"]["metrics"].get("upi_qr", {})
    m_bqr   = s["groups"]["infra"]["total"]["metrics"].get("bharat_qr", {})
    upi_v   = m_upi.get("latest")
    bqr_v   = m_bqr.get("latest")
    upi_mom = m_upi.get("mom_pct")
    bqr_mom = m_bqr.get("mom_pct")

    if upi_v is None or bqr_v is None or upi_v == 0:
        return None

    ratio = upi_v / bqr_v if bqr_v > 0 else None
    if ratio is None:
        return None

    title = f"UPI QR codes are {ratio:.0f}x Bharat QR in scale — {fmt_num(upi_v)} vs {fmt_num(bqr_v)}"
    body = (
        f"As of {month}, there are {fmt_num(upi_v)} UPI QR codes deployed vs {fmt_num(bqr_v)} Bharat QR codes — "
        f"a {ratio:.0f}x gap. "
    )
    if upi_mom is not None and bqr_mom is not None:
        body += f"UPI QR grew {upi_mom:+.1f}% MoM vs Bharat QR at {bqr_mom:+.1f}% MoM. "
    body += "UPI has decisively won the QR standard battle in India."
    return insight(
        "infra-upi-vs-bharat-qr", "infra", "total", month, title, body,
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "upi_qr"},
    )


def infra_category_pos(s, month) -> dict | None:
    """Category gaining POS share."""
    by_type = s["groups"]["infra"]["by_type"]
    cats    = by_type["categories"]
    gainer  = by_type.get("top_gainer")
    loser   = by_type.get("top_loser")

    if not gainer:
        return None
    g_delta = (cats[gainer].get("share_delta_pp") or 0)
    if abs(g_delta) < 0.2:
        return None

    g_sh = cats[gainer].get("share_pct", 0)
    title = f"{gainer} banks fastest-growing in POS terminal deployment in {month} ({sign(g_delta)}pp share)"
    body = (
        f"{gainer} banks hold {g_sh:.1f}% of total POS terminals in {month}, "
        f"gaining {sign(g_delta)}pp vs prior month. "
        f"{loser + ' banks lost the most share.' if loser and loser != gainer else ''}"
    )
    return insight(
        "infra-category-pos-share", "infra", "by_type", month, title, body,
        effect={"highlight": [gainer, "Total"], "tab": "distribution", "distMode": "pct", "focusCard": "pos_terminals"},
        explore={"mode": "by_type"},
    )


def infra_top_bank_pos(s, month) -> dict | None:
    """Top bank in POS deployment — often counterintuitive (RBL)."""
    topn   = s["groups"]["infra"]["top_n"]
    banks  = topn["banks"]
    top5sh = topn.get("top5_share_pct")
    delta  = topn.get("top5_share_delta_pp")
    leader = banks[0] if banks else None
    rank_changes = topn.get("rank_changes", [])

    if not leader:
        return None

    title = f"{leader['name']} leads POS terminal deployment at {leader['share_pct']:.1f}% market share"
    body = (
        f"{leader['name']} has deployed {fmt_num(leader['value'])} POS terminals in {month}, "
        f"accounting for {leader['share_pct']:.1f}% of total ({leader['mom_pct']:+.1f}% MoM). "
    )
    if top5sh:
        body += f"Top 5 banks hold {top5sh:.1f}% of all POS terminals{f' ({sign(delta)}pp vs prior month)' if delta else ''}."
    if rank_changes:
        rc = rank_changes[0]
        body += f" Notable: {rc['name']} moved from #{rc['from_rank']} to #{rc['to_rank']}."

    return insight(
        "infra-top-bank-pos", "infra", "top_n", month, title, body,
        effect={"highlight": [leader["name"], "Total"], "tab": "distribution", "distMode": "pct", "focusCard": "pos_terminals"},
        explore={"mode": "top_n", "topN": 10},
    )


def cc_transaction_surge(s, month) -> dict | None:
    """All CC transaction types up strongly in same month — year-end / seasonal signal."""
    metrics   = s["groups"]["cc"]["total"]["metrics"]
    txn_keys  = ["cc_pos_txn_vol", "cc_ecom_txn_vol", "cc_atm_withdrawal_vol", "cc_other_txn_vol"]
    moms      = {k: metrics.get(k, {}).get("mom_pct") for k in txn_keys}
    valid     = {k: v for k, v in moms.items() if v is not None}
    if not valid:
        return None
    avg_mom = sum(valid.values()) / len(valid)
    if not all(v > 10 for v in valid.values()) or avg_mom < 12:
        return None  # only fire when all types surge together

    title = f"All CC transaction types surged in {month} — avg {avg_mom:.1f}% MoM"
    body = (
        f"All four CC transaction types grew strongly in {month}: "
        f"POS +{moms['cc_pos_txn_vol']:.1f}%, "
        f"eCommerce +{moms['cc_ecom_txn_vol']:.1f}%, "
        f"ATM +{moms['cc_atm_withdrawal_vol']:.1f}%, "
        f"Other +{moms['cc_other_txn_vol']:.1f}%. "
        f"March year-end spending typically drives broad-based CC transaction growth."
    )
    return insight(
        "cc-txn-surge", "cc", "total", month, title, body,
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "mom", "focusCard": "cc_pos"},
    )


def dc_atm_share_structural(s, month) -> dict | None:
    """DC ATM cash losing share to digital — structural shift signal."""
    cross     = s["groups"]["dc"]["total"]["cross"]
    atm       = cross.get("dc_atm_withdrawal_vol", {})
    ecom      = cross.get("dc_ecom_txn_vol", {})
    atm_sh    = atm.get("share_pct")
    atm_delta = atm.get("share_delta_pp")
    ecom_sh   = ecom.get("share_pct")
    ecom_delta= ecom.get("share_delta_pp")

    if atm_sh is None or atm_delta is None or atm_delta >= 0:
        return None  # only fire when ATM share declining

    title = f"DC ATM cash losing share — {atm_sh:.1f}% of DC volume ({sign(atm_delta)}pp) as digital grows"
    body  = (
        f"Debit card ATM withdrawals account for {atm_sh:.1f}% of total DC transaction volume in {month} "
        f"({sign(atm_delta)}pp vs prior month). "
    )
    if ecom_sh and ecom_delta:
        body += f"DC ecommerce has grown to {ecom_sh:.1f}% ({sign(ecom_delta)}pp). "
    body += "The structural shift from cash to digital payments is underway in the debit segment."
    return insight(
        "dc-atm-share-structural", "dc", "total", month, title, body,
        effect={"highlight": ["Total"], "tab": "distribution", "distMode": "pct", "focusCard": "dc_atm"},
    )


def dc_pos_cash_decline(s, month) -> dict | None:
    """DC POS cash withdrawals declining — distinct from ATM cash trend."""
    m      = s["groups"]["dc"]["total"]["metrics"].get("dc_pos_withdrawal_vol", {})
    streak = m.get("streak_months", 1)
    sd     = m.get("streak_dir", "flat")
    mom    = m.get("mom_pct")

    if sd != "down" or streak < 2 or mom is None:
        return None

    title = f"DC POS cash withdrawals: {streak_label(streak, 'down')} ({mom:.1f}% MoM)"
    body  = (
        f"Debit card POS cash-back withdrawal volume fell {abs(mom):.1f}% MoM in {month}, "
        f"the {streak_label(streak, 'down')}. "
        f"This is a separate channel from ATM cash — POS cash-back usage is contracting "
        f"while digital POS payments continue to grow."
    )
    return insight(
        "dc-pos-cash-decline", "dc", "total", month, title, body,
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "mom", "focusCard": "dc_pos_wd"},
    )


# ══════════════════════════════════════════════════════════════════════════════
# Orchestrate
# ══════════════════════════════════════════════════════════════════════════════

RULES = [
    # CC
    cc_ecom_vs_pos,
    cc_atm_withdrawal_trend,
    cc_cards_streak,
    cc_transaction_surge,
    cc_category_share_shift,
    cc_top_bank_concentration,
    # DC
    dc_atm_trend,
    dc_atm_share_structural,
    dc_pos_cash_decline,
    dc_ecom_share,
    dc_cards_streak,
    dc_category_dominance,
    dc_top_bank,
    # Infra
    infra_qr_per_pos,
    infra_pos_streak,
    infra_upi_vs_bharat_qr,
    infra_category_pos,
    infra_top_bank_pos,
]


def main():
    with open(SIGNALS_IN) as f:
        signals = json.load(f)

    month = signals["meta"]["latest_month"]
    print(f"Generating insights for {month}…")

    insights = []
    for rule in RULES:
        try:
            result = rule(signals, month)
            if result:
                insights.append(result)
                print(f"  ✓ {result['id']} [{result['group']} / {result['cut']}]")
        except Exception as e:
            print(f"  ✗ {rule.__name__}: {e}")

    print(f"\n{len(insights)} insights generated.")

    # Write
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(insights, f, indent=2)
    shutil.copy(OUT_PATH, WEB_PATH)

    print(f"✓ insights.json → {OUT_PATH}")
    print(f"✓ copied        → {WEB_PATH}")

    # Summary by group/cut
    from collections import Counter
    counts = Counter(f"{i['group']}/{i['cut']}" for i in insights)
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
