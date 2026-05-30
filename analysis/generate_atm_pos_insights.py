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


def get_signal_value(s: dict, key: str) -> float | None:
    """Traverse a dot-path key in the signals dict, return float or None."""
    node = s
    for part in key.split("."):
        if isinstance(node, dict):
            node = node.get(part)
        elif isinstance(node, list):
            try:
                node = node[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
        if node is None:
            return None
    return float(node) if isinstance(node, (int, float)) and not isinstance(node, bool) else None


def build_reasoning(s: dict, keys: list, chain: list) -> dict:
    """Build a reasoning object with live signal values for Stage 4d validation."""
    signals = []
    for key in keys:
        val = get_signal_value(s, key)
        if val is not None:
            signals.append({"key": key, "value": round(val, 4)})
    return {"signals": signals, "chain": chain}


def insight(id_, group, cut, period, title, body, effect, explore=None,
            type_="insight", implication=None, source_signals=None,
            chain=None, signals_dict=None):
    reasoning = (
        build_reasoning(signals_dict, source_signals or [], chain)
        if chain and signals_dict and source_signals
        else None
    )
    return {
        "id":            id_,
        "group":         group,
        "cut":           cut,
        "period":        period,
        "type":          type_,
        "title":         title,
        "body":          body,
        "implication":   implication,
        "reasoning":     reasoning,
        "sourceSignals": source_signals or [],
        "effect":        effect,
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

    implication = (
        f"More than half of credit card spending is now online — not at physical stores. "
        f"Online transactions (called CNP, or card-not-present, because the card isn't physically swiped) carry higher fraud risk. "
        f"If your fraud detection was built around in-store spending patterns, it needs to be updated for an online-first customer base."
    )
    return insight(
        "cc-ecom-vs-pos-share", "cc", "total", month, title, body,
        effect={
            "highlight": ["Total"],
            "tab": "trend",
            "trendMode": "absolute",
            "focusCard": "cc_ecom",
        },
        explore={"mode": "by_type"},
        implication=implication,
        source_signals=[
            "groups.cc.total.cross.cc_ecom_txn_vol.share_pct",
            "groups.cc.total.cross.cc_pos_txn_vol.share_pct",
            "groups.cc.total.cross.cc_ecom_txn_vol.share_delta_pp",
        ],
        chain=[
            f"CC ecommerce at {ecom_sh:.1f}% of volume — majority of CC spend is now online, not at physical stores",
            "Online transactions (card-not-present / CNP) carry higher fraud risk since the card is never physically verified",
            "Fraud detection built for in-store patterns needs recalibration for an online-first customer base",
        ],
        signals_dict=s,
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
        implication = (
            "Declining CC ATM cash advances reduce high-rate revolving exposure in CC portfolios. "
            "Lenders benefit from a cleaner credit mix; however, the shift also signals growing "
            "customer preference for digital payments over liquidity access — a proxy for financial literacy improvement."
        )
        return insight(
            "cc-atm-declining", "cc", "total", month, title, body,
            effect={"highlight": ["Total"], "tab": "trend", "trendMode": "mom", "focusCard": "cc_atm"},
            implication=implication,
            source_signals=[
                "groups.cc.total.metrics.cc_atm_withdrawal_vol.mom_pct",
                "groups.cc.total.metrics.cc_atm_withdrawal_vol.streak_months",
                "groups.cc.total.cross.cc_atm_withdrawal_vol.share_pct",
            ],
            chain=[
                f"CC ATM cash declining for {streak} months — customers using credit cards for purchases, not cash",
                "Lower cash advance usage reduces high-interest revolving exposure in CC portfolios",
                "Shift signals growing digital payment preference — proxy for improving financial literacy in the base",
            ],
            signals_dict=s,
        )

    if streak_dir == "up" and streak >= 3 and mom > 3:
        title = f"CC ATM cash withdrawals rising — {streak_label(streak, 'up')} ({mom:+.1f}% MoM)"
        body = (
            f"CC ATM withdrawal volume grew {mom:.1f}% MoM in {month}, "
            f"the {streak_label(streak, 'up')}. "
        )
        if atm_sh:
            body += f"Cash accounts for {atm_sh:.1f}% of CC transaction volume."
        implication = (
            f"When credit card holders keep withdrawing cash from ATMs over {streak} months, it usually means they're struggling with liquidity — using credit cards as a cash loan. "
            "Cash advances on credit cards are expensive (higher interest, no interest-free period). "
            "Watch for higher default risk in customer segments where this pattern shows up."
        )
        return insight(
            "cc-atm-rising", "cc", "total", month, title, body,
            effect={"highlight": ["Total"], "tab": "trend", "trendMode": "mom", "focusCard": "cc_atm"},
            implication=implication,
            source_signals=[
                "groups.cc.total.metrics.cc_atm_withdrawal_vol.mom_pct",
                "groups.cc.total.metrics.cc_atm_withdrawal_vol.streak_months",
                "groups.cc.total.cross.cc_atm_withdrawal_vol.share_pct",
            ],
            chain=[
                f"CC ATM cash growing for {streak} months — customers using credit cards as liquidity access, not for purchases",
                "Cash advances carry higher interest and no interest-free period — expensive revolving behaviour",
                "Sustained cash advance growth signals liquidity stress; monitor for elevated default risk in these segments",
            ],
            signals_dict=s,
        )
    return None


def cc_cards_streak(s, month) -> dict | None:
    """CC cards outstanding — streak if ≥ 3 months."""
    m          = s["groups"]["cc"]["total"]["metrics"].get("credit_cards", {})
    streak     = m.get("streak_months", 1)
    streak_dir = m.get("streak_dir", "flat")
    latest     = m.get("latest")
    qoq        = m.get("qoq_pct")
    curr_q     = s["meta"].get("curr_quarter", "latest quarter")
    prev_q     = s["meta"].get("prev_quarter", "prior quarter")

    if streak < 3 or streak_dir == "flat":
        return None

    latest_fmt = fmt_num(latest)
    qoq_str    = f" ({sign(qoq)}% QoQ vs {prev_q})" if qoq is not None else ""
    title = f"Credit cards outstanding: {streak_label(streak, streak_dir)} — {latest_fmt} cards"
    body = (
        f"Total credit cards outstanding reached {latest_fmt} in {month}{qoq_str}, "
        f"marking the {streak_label(streak, streak_dir)}. "
        f"{'Issuance momentum is broad-based across bank types.' if streak_dir == 'up' else 'Card attrition or issuance slowdown is underway.'}"
    )
    if streak_dir == "up":
        implication = (
            f"{streak} straight months of card growth looks good, but card count alone can mislead. "
            "Many new cards never get used — they sit inactive. "
            "What matters for lending is how many cards are actually being transacted on. "
            "Track activation rate (what percentage of issued cards have any spend in the last few months) alongside the headline number."
        )
    else:
        implication = (
            f"{streak} straight months of card decline could mean two things: banks are intentionally closing inactive or loss-making accounts (which is healthy), "
            "or they're losing customers to competitors (which is a red flag). "
            "Before drawing conclusions, check whether the decline is coming from one bank type or spread across all."
        )
    return insight(
        "cc-cards-streak", "cc", "total", month, title, body,
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "credit_cards"},
        explore={"mode": "by_type"},
        implication=implication,
        source_signals=[
            "groups.cc.total.metrics.credit_cards.latest",
            "groups.cc.total.metrics.credit_cards.streak_months",
            "groups.cc.total.metrics.credit_cards.streak_dir",
            "groups.cc.total.metrics.credit_cards.qoq_pct",
        ],
        chain=[
            f"CC cards outstanding {'growing' if streak_dir == 'up' else 'declining'} for {streak} consecutive months",
            "Card count includes dormant cards that were issued but never activated or used",
            "Activation rate (cards with any spend in recent months) is the real signal for credit origination potential",
        ],
        signals_dict=s,
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
    implication = (
        f"{gainer} banks picking up credit card share — even by {g_delta:.1f}pp — signals a change in who's acquiring customers. "
        f"{'SFBs (Small Finance Banks — banks that focus on underserved segments like AU or Equitas) growing in credit cards usually means fintech partnerships or co-branded products are kicking in.' if gainer == 'SFB' else ''}"
        f"{'Private banks compounding their lead means the premium card market is further consolidating.' if gainer == 'Private' else ''}"
        "For anyone benchmarking credit card portfolio quality, knowing which bank type is gaining share matters — their customer profiles and risk behaviour can be very different."
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
        implication=implication,
        source_signals=[
            f"groups.cc.by_type.categories.{gainer}.share_pct",
            f"groups.cc.by_type.categories.{gainer}.share_delta_pp",
            f"groups.cc.by_type.categories.{loser}.share_pct",
            f"groups.cc.by_type.categories.{loser}.share_delta_pp",
        ],
        chain=[
            f"{gainer} banks gained {g_delta:.1f}pp CC share — {loser} banks lost {abs(l_delta):.1f}pp",
            f"{'SFB growth signals fintech partnerships or co-branded card activity in underserved segments' if gainer == 'SFB' else 'Private bank lead compounding as premium card market consolidates further'}",
            "Customer risk profiles differ significantly across bank types — portfolio benchmarking must account for this mix shift",
        ],
        signals_dict=s,
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
        implication = (
            f"A rank change among the top CC issuers means one bank is either issuing cards faster "
            f"or closing inactive accounts more aggressively. For anyone watching the credit card market, "
            f"it's worth understanding the reason — growing rank means gaining customers, falling rank "
            f"could mean pruning a portfolio or losing share to a competitor."
        )
        return insight(
            "cc-top-bank-rank-change", "cc", "top_n", month, title, body,
            effect={"highlight": [rc["name"], "Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "credit_cards"},
            explore={"mode": "top_n", "topN": 10},
            implication=implication,
            source_signals=["groups.cc.top_n.top5_share_pct"],
            chain=[
                f"{rc['name']} moved from #{rc['from_rank']} to #{rc['to_rank']} in CC cards outstanding",
                f"{'Rising rank means faster card issuance or competitor attrition in that bank' if direction == 'up' else 'Falling rank suggests portfolio pruning or losing acquisition pace to competitors'}",
                "Track whether the move reflects new card issuance (gaining customers) or balance attrition (losing them)",
            ],
            signals_dict=s,
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
        implication = (
            f"74% of all credit cards in India are with just 5 banks. "
            "In practice, this means the national credit card data from RBI tells you largely "
            "what HDFC, SBI, ICICI, Axis, and Kotak are doing — not the market as a whole. "
            "If your strategy relies on industry-level CC data, keep this concentration in mind."
        )
        return insight(
            "cc-top5-concentration", "cc", "top_n", month, title, body,
            effect={"highlight": [leader["name"]], "tab": "distribution", "distMode": "pct", "focusCard": "credit_cards"},
            explore={"mode": "top_n", "topN": 10},
            implication=implication,
            source_signals=[
                "groups.cc.top_n.top5_share_pct",
                "groups.cc.top_n.top5_share_delta_pp",
                "groups.cc.top_n.banks.0.share_pct",
                "groups.cc.top_n.banks.0.mom_pct",
            ],
            chain=[
                f"Top 5 banks hold {top5sh:.1f}% of all CC cards — {leader['name']} alone accounts for {leader['share_pct']:.1f}%",
                "RBI aggregate CC data is effectively proxied by these 5 institutions — smaller banks are statistically marginal",
                "Industry-level CC strategy analysis must account for this concentration — it reflects large-bank dynamics, not the full market",
            ],
            signals_dict=s,
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
        implication = (
            "Debit card holders who are shifting from ATM cash to digital payments (POS or online) "
            "start leaving a traceable spending history. That history is exactly what lenders need "
            "to assess someone's first credit application. So fewer ATM withdrawals is actually "
            "good news for expanding the pool of underwritable debit customers."
        )
        return insight(
            "dc-atm-declining", "dc", "total", month, title, body,
            effect={"highlight": ["Total"], "tab": "trend", "trendMode": "mom", "focusCard": "dc_atm"},
            implication=implication,
            source_signals=[
                "groups.dc.total.metrics.dc_atm_withdrawal_vol.mom_pct",
                "groups.dc.total.metrics.dc_atm_withdrawal_vol.streak_months",
                "groups.dc.total.cross.dc_atm_withdrawal_vol.share_pct",
            ],
            chain=[
                f"DC ATM cash withdrawals declining for {streak} months — customers shifting to digital debit payments",
                "Digital debit transactions (POS, ecommerce) leave structured spending records vs cash which leaves none",
                "Debit customers moving to digital build a transaction history lenders can use to assess first credit applications",
            ],
            signals_dict=s,
        )

    if sd == "up" and streak >= 3:
        title = f"DC ATM withdrawals rising — {streak_label(streak, 'up')} ({mom:+.1f}% MoM)"
        body = f"Debit card ATM withdrawal volume grew {mom:.1f}% MoM in {month}. "
        if atm_sh:
            body += f"Cash accounts for {atm_sh:.1f}% of total DC volume."
        implication = (
            f"Debit card ATM cash growing for {streak} straight months means a large part of "
            "the debit base is still cash-first — their spending leaves no digital trail. "
            "For lenders using transaction data to underwrite, this segment is essentially invisible. "
            "Bureau scores (CIBIL, Experian) and physical income verification remain the only reliable tools here."
        )
        return insight(
            "dc-atm-rising", "dc", "total", month, title, body,
            effect={"highlight": ["Total"], "tab": "trend", "trendMode": "mom", "focusCard": "dc_atm"},
            implication=implication,
            source_signals=[
                "groups.dc.total.metrics.dc_atm_withdrawal_vol.mom_pct",
                "groups.dc.total.metrics.dc_atm_withdrawal_vol.streak_months",
                "groups.dc.total.cross.dc_atm_withdrawal_vol.share_pct",
            ],
            chain=[
                f"DC ATM cash growing for {streak} months — debit base is cash-first, not digitally active",
                "Cash transactions leave no digital record — financial behaviour is opaque to transaction-data models",
                "Bureau scores (CIBIL, Experian) and physical income verification are the primary underwriting tools for this segment",
            ],
            signals_dict=s,
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

    implication = (
        f"Only {ecom_sh:.1f}% of debit card spending is online, but that group is valuable. "
        "These are debit-only customers who already shop digitally — which means their spending "
        "leaves a traceable record. For cross-selling a first credit card or personal loan, "
        "debit customers with online spending history are much easier to assess than pure ATM-cash users."
    )
    return insight(
        "dc-ecom-share", "dc", "total", month, title, body,
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "dc_ecom"},
        explore={"mode": "by_type"},
        implication=implication,
        source_signals=[
            "groups.dc.total.cross.dc_ecom_txn_vol.share_pct",
            "groups.dc.total.cross.dc_ecom_txn_vol.share_delta_pp",
            "groups.dc.total.cross.dc_atm_withdrawal_vol.share_pct",
        ],
        chain=[
            f"DC ecommerce is {ecom_sh:.1f}% of DC volume — small but digitally traceable subgroup within a cash-dominant base",
            "Online debit customers leave structured purchase records; ATM-cash users leave none",
            "Digital-active debit customers are higher-value cross-sell targets for first credit products — traceable history enables underwriting",
        ],
        signals_dict=s,
    )


def dc_cards_streak(s, month) -> dict | None:
    """DC cards outstanding streak."""
    m      = s["groups"]["dc"]["total"]["metrics"].get("debit_cards", {})
    streak = m.get("streak_months", 1)
    sd     = m.get("streak_dir", "flat")
    latest = m.get("latest")
    qoq    = m.get("qoq_pct")
    curr_q = s["meta"].get("curr_quarter", "latest quarter")
    prev_q = s["meta"].get("prev_quarter", "prior quarter")

    if streak < 4 or sd == "flat":
        return None  # higher bar for DC (slower moving)

    qoq_str = f" ({sign(qoq)}% QoQ vs {prev_q})" if qoq is not None else ""
    title = f"Debit cards: {streak_label(streak, sd)} — {fmt_num(latest)} outstanding"
    body = (
        f"Total debit cards outstanding reached {fmt_num(latest)} in {month}{qoq_str}, "
        f"the {streak_label(streak, sd)}. "
        f"{'India debit base continues to expand.' if latest > 1e9 else ''}"
    )
    implication = (
        f"India has {fmt_num(latest)} debit cards — but that number is misleading as a credit opportunity. "
        "A large chunk are Jan Dhan accounts (zero-balance accounts opened under the government's "
        "financial inclusion scheme) that see very little activity. "
        "The real pool for first-time credit products is much smaller — focus on debit card holders "
        "who are actually transacting, not just account holders."
    )
    return insight(
        "dc-cards-streak", "dc", "total", month, title, body,
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "debit_cards"},
        explore={"mode": "by_type"},
        implication=implication,
        source_signals=[
            "groups.dc.total.metrics.debit_cards.latest",
            "groups.dc.total.metrics.debit_cards.streak_months",
            "groups.dc.total.metrics.debit_cards.qoq_pct",
        ],
        chain=[
            f"Debit card base at {fmt_num(latest)} — large headline number includes substantial Jan Dhan zero-balance accounts",
            "Jan Dhan accounts (government financial inclusion scheme) skew toward low-income, low-activity customers",
            "Addressable credit opportunity is a fraction of total card count — active-transacting subset is the real pool",
        ],
        signals_dict=s,
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
    implication = (
        f"PSBs (government-owned banks like SBI, PNB, Bank of Baroda) hold {psb_sh:.1f}% of debit cards, "
        "largely because of Jan Dhan — the government scheme that opened basic bank accounts "
        "for millions of low-income households. Many of these accounts have little activity. "
        "If you're using debit transaction data for credit assessment, PSB debit data needs to be "
        "treated very differently from, say, HDFC or Kotak debit customers."
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
        implication=implication,
        source_signals=[
            "groups.dc.by_type.categories.PSB.share_pct",
            "groups.dc.by_type.categories.PSB.share_delta_pp",
            "groups.dc.by_type.categories.Private.share_pct",
        ],
        chain=[
            f"PSBs hold {psb_sh:.1f}% of debit cards — primarily through Jan Dhan scheme linkage, not active acquisition",
            "Jan Dhan portfolios skew toward low-income, low-activity accounts with thin or no transaction histories",
            "PSB and private bank debit data require separate calibration for transaction-based credit underwriting",
        ],
        signals_dict=s,
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
        implication = (
            "Rank changes in debit cards usually mean one of two things: a PSB is closing "
            "dormant Jan Dhan accounts (drops in rank), or a private bank is pushing into "
            "smaller towns and cities (rises in rank). "
            "The bank moving up is reaching new customers — which often translates to more "
            "credit origination potential over the next few quarters."
        )
        return insight(
            "dc-top-bank-rank-change", "dc", "top_n", month, title, body,
            effect={"highlight": [rc["name"], "Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "debit_cards"},
            explore={"mode": "top_n", "topN": 10},
            implication=implication,
            source_signals=["groups.dc.top_n.top5_share_pct"],
            chain=[
                f"{rc['name']} shifted from #{rc['from_rank']} to #{rc['to_rank']} in debit cards",
                "PSB rank drops often reflect Jan Dhan dormant account closures; private bank rises reflect geographic expansion",
                "Bank moving up is reaching new customers — leading indicator of future credit origination volume in that segment",
            ],
            signals_dict=s,
        )

    title = f"{leader['name']} leads DC cards at {leader['share_pct']:.1f}%"
    body = (
        f"{leader['name']} holds {leader['share_pct']:.1f}% of total debit cards in {month} "
        f"({leader['mom_pct']:+.1f}% MoM). "
        f"Top 5 banks account for {top5sh:.1f}%{f' ({sign(delta)}pp vs prior month)' if delta else ''}."
    )
    implication = (
        f"Top 5 banks hold {top5sh:.1f}% of debit cards. If you're using debit transaction data "
        "for credit underwriting (assessing someone's spending behaviour before giving them a loan), "
        "the quality of that data depends heavily on whether these top banks are sharing data with you. "
        "Without coverage from at least 2-3 of them, you're missing nearly half the market."
    )
    return insight(
        "dc-top-bank-leader", "dc", "top_n", month, title, body,
        effect={"highlight": [leader["name"]], "tab": "distribution", "distMode": "pct", "focusCard": "debit_cards"},
        explore={"mode": "top_n", "topN": 10},
        implication=implication,
        source_signals=[
            "groups.dc.top_n.top5_share_pct",
            "groups.dc.top_n.top5_share_delta_pp",
            "groups.dc.top_n.banks.0.share_pct",
            "groups.dc.top_n.banks.0.mom_pct",
        ],
        chain=[
            f"Top 5 banks hold {top5sh:.1f}% of debit cards — {leader['name']} alone accounts for {leader['share_pct']:.1f}%",
            "Debit transaction data coverage for underwriting depends on data-sharing with these top institutions",
            "Without data from 2-3 of these banks, nearly half the debit market is invisible for credit decisions",
        ],
        signals_dict=s,
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
    implication = (
        f"There are {latest:.0f} UPI QR codes for every POS (card swipe) machine in India. "
        "This means the typical small merchant — kirana store, auto driver, vegetable vendor — "
        "accepts payments through a QR code on their phone, not a card machine. "
        "Any credit product designed for small merchants (small business loans, BNPL for vendors) "
        "needs to work over UPI QR, not just over POS terminals."
    )
    return insight(
        "infra-qr-per-pos", "infra", "total", month, title, body,
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "upi_qr"},
        explore={"mode": "by_type"},
        implication=implication,
        source_signals=[
            "groups.infra.total.metrics.upi_qr.latest",
            "groups.infra.total.metrics.pos_terminals.latest",
            "groups.infra.total.metrics.upi_qr.mom_pct",
            "groups.infra.total.metrics.pos_terminals.mom_pct",
        ],
        chain=[
            f"{latest:.0f} UPI QR codes per POS terminal — QR acceptance vastly outnumbers hardware deployment",
            "Typical small merchant (kirana, auto, vendor) accepts via QR only — no POS terminal",
            "Credit products for small merchants (BNPL, business loans) must work over UPI QR to reach this majority",
        ],
        signals_dict=s,
    )


def infra_pos_streak(s, month) -> dict | None:
    """POS terminal growth streak."""
    m      = s["groups"]["infra"]["total"]["metrics"].get("pos_terminals", {})
    streak = m.get("streak_months", 1)
    sd     = m.get("streak_dir", "flat")
    latest = m.get("latest")
    qoq    = m.get("qoq_pct")
    prev_q = s["meta"].get("prev_quarter", "prior quarter")

    if streak < 3 or sd == "flat":
        return None

    qoq_str = f" ({sign(qoq)}% QoQ vs {prev_q})" if qoq is not None else ""
    title = f"POS terminals: {streak_label(streak, sd)} — {fmt_num(latest)} deployed"
    body = (
        f"POS terminals reached {fmt_num(latest)} in {month}{qoq_str}, "
        f"the {streak_label(streak, sd)}. "
        f"{'Physical acceptance infrastructure continues to expand.' if sd == 'up' else 'POS terminal count is contracting — QR-first acceptance may be replacing hardware.'}"
    )
    if sd == "up":
        implication = (
            f"Every new POS machine deployed ({fmt_num(latest)} and growing) is a merchant "
            "who starts building a transaction history — how much they sell, how often, which days. "
            "That data is exactly what lenders use to assess working capital loans (short-term "
            "business credit based on daily sales). More POS terminals means more merchants "
            "who can be lent to based on their actual business performance."
        )
    else:
        implication = (
            "POS terminal count falling likely means merchants are switching to UPI QR codes "
            "instead — cheaper, no hardware needed. If you use POS transaction data to assess "
            "merchant creditworthiness, your data coverage may be quietly shrinking as merchant "
            "activity shifts to QR rails where you may not have visibility."
        )
    return insight(
        "infra-pos-streak", "infra", "total", month, title, body,
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "pos_terminals"},
        explore={"mode": "by_type"},
        implication=implication,
        source_signals=[
            "groups.infra.total.metrics.pos_terminals.latest",
            "groups.infra.total.metrics.pos_terminals.streak_months",
            "groups.infra.total.metrics.pos_terminals.qoq_pct",
        ],
        chain=[
            f"POS terminals {'growing' if sd == 'up' else 'declining'} for {streak} months — now at {fmt_num(latest)}",
            f"{'Each new POS terminal generates merchant transaction history (sales volume, frequency, ticket size)' if sd == 'up' else 'Declining POS likely means merchant migration to UPI QR — cheaper and no hardware needed'}",
            f"{'Growing POS base expands pool of merchants underwritable for working capital or merchant cash advances' if sd == 'up' else 'POS-based merchant credit data coverage may be quietly shrinking as activity migrates to QR rails'}",
        ],
        signals_dict=s,
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
    implication = (
        f"Bharat QR was an earlier QR code standard that lost out to UPI QR — which is now {ratio:.0f} times bigger. "
        "Building any credit product (credit on UPI, BNPL) on Bharat QR today would be like "
        "building on a platform that merchants have already abandoned. "
        "UPI QR is the only QR standard worth designing for."
    )
    return insight(
        "infra-upi-vs-bharat-qr", "infra", "total", month, title, body,
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "upi_qr"},
        implication=implication,
        source_signals=[
            "groups.infra.total.metrics.upi_qr.latest",
            "groups.infra.total.metrics.bharat_qr.latest",
            "groups.infra.total.metrics.upi_qr.mom_pct",
            "groups.infra.total.metrics.bharat_qr.mom_pct",
        ],
        chain=[
            f"UPI QR at {fmt_num(upi_v)} vs Bharat QR at {fmt_num(bqr_v)} — a {ratio:.0f}x gap",
            "Bharat QR was an earlier standard; merchants have consolidated on UPI QR as the accepted norm",
            "Building payments or lending infrastructure on Bharat QR rails is operationally unviable at any meaningful merchant scale",
        ],
        signals_dict=s,
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
    implication = (
        f"{gainer} banks gaining POS share means they're building more merchant relationships in that segment. "
        "Banks that own the POS network also own the merchant's transaction data — daily sales, "
        "busy periods, average ticket size. "
        "That data is the foundation for merchant lending (small business loans based on sales history). "
        "Watch which bank type is expanding POS — they're positioning for merchant credit."
    )
    return insight(
        "infra-category-pos-share", "infra", "by_type", month, title, body,
        effect={"highlight": [gainer, "Total"], "tab": "distribution", "distMode": "pct", "focusCard": "pos_terminals"},
        explore={"mode": "by_type"},
        implication=implication,
        source_signals=[
            f"groups.infra.by_type.categories.{gainer}.share_pct",
            f"groups.infra.by_type.categories.{gainer}.share_delta_pp",
        ],
        chain=[
            f"{gainer} banks gained {g_delta:.1f}pp POS share — building more merchant acquiring relationships",
            "Banks owning the POS network own the merchant's transaction data (daily sales, ticket size, frequency)",
            "POS share expansion is a leading indicator of positioning for merchant credit (working capital, cash advances)",
        ],
        signals_dict=s,
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

    top5sh_val = top5sh or 0
    implication = (
        f"5 banks own {top5sh_val:.1f}% of all POS machines in India. "
        "That also means merchant sales data — what shopkeepers sell, how much, how often — "
        "sits largely with those same 5 banks. "
        "If you want to lend to merchants and need their sales history to decide how much credit to give, "
        "you either need a data partnership with one of these banks or an alternate source "
        "like GST returns or UPI transaction feeds."
    )
    return insight(
        "infra-top-bank-pos", "infra", "top_n", month, title, body,
        effect={"highlight": [leader["name"]], "tab": "distribution", "distMode": "pct", "focusCard": "pos_terminals"},
        explore={"mode": "top_n", "topN": 10},
        implication=implication,
        source_signals=[
            "groups.infra.top_n.top5_share_pct",
            "groups.infra.top_n.banks.0.share_pct",
            "groups.infra.top_n.banks.0.mom_pct",
        ],
        chain=[
            f"Top 5 banks own {top5sh_val:.1f}% of POS terminals — merchant acquiring infrastructure is highly concentrated",
            "Merchant transaction data (sales history for credit underwriting) sits with the same institutions",
            "Merchant credit without data partnerships with these banks requires alternate sources — GST returns, UPI transaction feeds",
        ],
        signals_dict=s,
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
    implication = (
        f"March always spikes — it's financial year-end and people tend to spend more. "
        f"An average {avg_mom:.1f}% jump this month is seasonal, not a sign customers suddenly have more money. "
        "If you're assessing how much credit a customer can repay, don't use March spend as your baseline — "
        "it will make their repayment capacity look higher than it actually is."
    )
    return insight(
        "cc-txn-surge", "cc", "total", month, title, body,
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "mom", "focusCard": "cc_pos"},
        implication=implication,
        source_signals=[
            "groups.cc.total.metrics.cc_pos_txn_vol.mom_pct",
            "groups.cc.total.metrics.cc_ecom_txn_vol.mom_pct",
            "groups.cc.total.metrics.cc_atm_withdrawal_vol.mom_pct",
            "groups.cc.total.metrics.cc_other_txn_vol.mom_pct",
        ],
        chain=[
            f"All 4 CC transaction types grew simultaneously — avg {avg_mom:.1f}% MoM in March",
            "March is financial year-end in India — broad-based spending surge is a recurring seasonal pattern",
            "Seasonal spike overstates true credit utilisation; normalise March volumes before assessing repayment capacity",
        ],
        signals_dict=s,
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
    implication = (
        f"Debit card ATM cash is at {atm_sh:.1f}% and falling — which means a growing group of "
        "debit card holders is switching to digital payments (online or at stores). "
        "Those customers start leaving a spending history that lenders can actually use. "
        "Debit customers who are moving to digital are among the best targets for a first credit card "
        "or personal loan — they have a track record, just not a credit one yet."
    )
    return insight(
        "dc-atm-share-structural", "dc", "total", month, title, body,
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "dc_atm"},
        implication=implication,
        source_signals=[
            "groups.dc.total.cross.dc_atm_withdrawal_vol.share_pct",
            "groups.dc.total.cross.dc_atm_withdrawal_vol.share_delta_pp",
            "groups.dc.total.cross.dc_ecom_txn_vol.share_pct",
            "groups.dc.total.cross.dc_ecom_txn_vol.share_delta_pp",
        ],
        chain=[
            f"DC ATM cash share fell {abs(atm_delta):.1f}pp to {atm_sh:.1f}% — customers shifting away from cash",
            "Digital debit transactions (POS, ecommerce) create structured spending records; cash leaves none",
            "Debit customers moving to digital build a usable credit history — prime candidates for first credit origination",
        ],
        signals_dict=s,
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
    implication = (
        "Some merchants used to let customers withdraw cash at their POS machine — called cash-back at POS. "
        "This is declining. That's actually good for data quality: POS transaction records now reflect "
        "real purchases, not cash withdrawals disguised as purchases. "
        "Better purchase data means more accurate signals when assessing credit for small businesses or retail customers."
    )
    return insight(
        "dc-pos-cash-decline", "dc", "total", month, title, body,
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "mom", "focusCard": "dc_pos_wd"},
        implication=implication,
        source_signals=[
            "groups.dc.total.metrics.dc_pos_withdrawal_vol.mom_pct",
            "groups.dc.total.metrics.dc_pos_withdrawal_vol.streak_months",
        ],
        chain=[
            f"DC POS cash-back withdrawals fell {abs(mom):.1f}% MoM for {streak} months — merchants reducing cash-out via POS",
            "POS records now reflect real purchases rather than cash access events disguised as transactions",
            "Cleaner purchase data improves signal quality for credit underwriting of MSME and retail customers",
        ],
        signals_dict=s,
    )


# ══════════════════════════════════════════════════════════════════════════════
# GAP RULES  (type_="gap" — structural blind spots or underserved areas)
# ══════════════════════════════════════════════════════════════════════════════

def gap_dc_cash_dominance(s, month) -> dict | None:
    """DC ATM cash still >75% of DC vol — digital transition is incomplete."""
    cross  = s["groups"]["dc"]["total"]["cross"]
    atm_sh = cross.get("dc_atm_withdrawal_vol", {}).get("share_pct")
    atm_dt = cross.get("dc_atm_withdrawal_vol", {}).get("share_delta_pp")
    if atm_sh is None or atm_sh < 75:
        return None
    ecom_sh = cross.get("dc_ecom_txn_vol", {}).get("share_pct")
    title = f"Gap: DC ATM cash at {atm_sh:.1f}% of DC volume — digital transition is incomplete"
    body = (
        f"Despite growth in digital payments, ATM cash withdrawals still account for {atm_sh:.1f}% "
        f"of total debit card transaction volume in {month}"
        f"{f' ({sign(atm_dt)}pp vs prior month)' if atm_dt else ''}. "
        f"DC ecommerce is only {ecom_sh:.1f}% of DC volume. "
        f"India's debit card base remains overwhelmingly cash-dependent."
    )
    implication = (
        f"{atm_sh:.1f}% of debit card spending is ATM cash. Cash leaves no digital record — "
        "you can't tell where it was spent or on what. "
        "For lenders trying to assess a debit card holder's financial behaviour, the transaction "
        "history is mostly blank. Bureau scores (CIBIL, Experian) remain the primary tool "
        "for this segment — debit transaction data alone isn't enough yet."
    )
    return insight(
        "gap-dc-cash-dominance", "dc", "total", month, title, body,
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "dc_atm"},
        type_="gap",
        implication=implication,
        source_signals=[
            "groups.dc.total.cross.dc_atm_withdrawal_vol.share_pct",
            "groups.dc.total.cross.dc_atm_withdrawal_vol.share_delta_pp",
            "groups.dc.total.cross.dc_ecom_txn_vol.share_pct",
        ],
        chain=[
            f"{atm_sh:.1f}% of DC volume is ATM cash — transactions that leave no digital record",
            "Cash-dominant customers' financial behaviour is opaque — spending categories, frequency, merchants all unknown",
            "Bureau scores (CIBIL, Experian) remain essential for this segment; debit transaction data alone is insufficient",
        ],
        signals_dict=s,
    )


def gap_bharat_qr_contraction(s, month) -> dict | None:
    """Bharat QR declining MoM — infrastructure investment at risk."""
    m_bqr   = s["groups"]["infra"]["total"]["metrics"].get("bharat_qr", {})
    m_upi   = s["groups"]["infra"]["total"]["metrics"].get("upi_qr", {})
    bqr_mom = m_bqr.get("mom_pct")
    bqr_v   = m_bqr.get("latest")
    upi_v   = m_upi.get("latest")
    if bqr_mom is None or bqr_mom > -1:
        return None  # only flag meaningful decline
    ratio = round(upi_v / bqr_v) if (upi_v and bqr_v and bqr_v > 0) else None
    title = f"Gap: Bharat QR contracting {bqr_mom:.1f}% MoM — {fmt_num(bqr_v)} vs {fmt_num(upi_v)} UPI QR"
    body = (
        f"Bharat QR codes fell {abs(bqr_mom):.1f}% MoM in {month}, now at {fmt_num(bqr_v)} — "
        f"compared to {fmt_num(upi_v)} UPI QR codes"
        f"{f' ({ratio}x gap)' if ratio else ''}. "
        f"Merchant preference has consolidated on UPI QR as the dominant QR acceptance standard."
    )
    implication = (
        f"Bharat QR is shrinking {abs(bqr_mom):.1f}% every month — merchants are removing it. "
        "If any part of your lending or payments product depends on Bharat QR acceptance, "
        "that's a real problem. Move everything to UPI QR. "
        "There is no viable future for Bharat QR as a payments or credit infrastructure."
    )
    return insight(
        "gap-bharat-qr-contraction", "infra", "total", month, title, body,
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "mom", "focusCard": "bharat_qr"},
        type_="gap",
        implication=implication,
        source_signals=[
            "groups.infra.total.metrics.bharat_qr.mom_pct",
            "groups.infra.total.metrics.bharat_qr.latest",
            "groups.infra.total.metrics.upi_qr.latest",
        ],
        chain=[
            f"Bharat QR declining {abs(bqr_mom):.1f}% MoM — merchants are actively removing it, not seasonal dip",
            f"UPI QR at {fmt_num(upi_v)} vs Bharat QR at {fmt_num(bqr_v)} — gap structural and widening",
            "Any payments or lending product built on Bharat QR infrastructure faces accelerating merchant disengagement",
        ],
        signals_dict=s,
    )


def gap_atm_offsite_decline(s, month) -> dict | None:
    """Offsite ATMs declining — rural cash access concern."""
    m_off = s["groups"]["infra"]["total"]["metrics"].get("atm_offsite", {})
    m_on  = s["groups"]["infra"]["total"]["metrics"].get("atm_onsite", {})
    off_mom = m_off.get("mom_pct")
    on_mom  = m_on.get("mom_pct")
    off_v   = m_off.get("latest")
    if off_mom is None or off_mom >= 0:
        return None  # only fire when offsite is declining
    title = f"Gap: Offsite ATMs declining {off_mom:.1f}% MoM — rural cash access contracting"
    body = (
        f"Offsite ATMs fell {abs(off_mom):.1f}% MoM in {month} (now {fmt_num(off_v)})"
        f"{f', while onsite ATMs grew {on_mom:+.1f}% MoM' if on_mom and on_mom > 0 else ''}. "
        f"Offsite ATMs serve rural and semi-urban populations where branch presence is limited — "
        f"their decline reduces physical cash access for underserved geographies."
    )
    implication = (
        "Offsite ATMs are standalone machines in villages, petrol pumps, small towns — "
        "placed away from bank branches specifically to serve rural areas. "
        "When these decline and digital payments haven't reached those areas yet, "
        "rural borrowers lose their easiest way to access cash for repayment. "
        "If you have loans in rural geographies, check whether ATM coverage in those areas is shrinking — "
        "it can make EMI collection harder."
    )
    return insight(
        "gap-atm-offsite-decline", "infra", "total", month, title, body,
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "mom", "focusCard": "atm_offsite"},
        type_="gap",
        implication=implication,
        source_signals=[
            "groups.infra.total.metrics.atm_offsite.mom_pct",
            "groups.infra.total.metrics.atm_offsite.latest",
            "groups.infra.total.metrics.atm_onsite.mom_pct",
        ],
        chain=[
            f"Offsite ATMs (standalone machines in rural/semi-urban areas away from branches) fell {abs(off_mom):.1f}% MoM",
            "Rural borrowers without digital payment access rely on offsite ATMs as primary cash access point for loan repayment",
            "Declining offsite ATM coverage can impair EMI collection in areas where digital payment penetration is still low",
        ],
        signals_dict=s,
    )


def gap_pos_concentration(s, month) -> dict | None:
    """Top 5 banks hold >85% of POS — structural exclusion for smaller banks."""
    topn   = s["groups"]["infra"]["top_n"]
    top5sh = topn.get("top5_share_pct")
    if top5sh is None or top5sh < 85:
        return None
    leader = topn["banks"][0] if topn["banks"] else None
    title = f"Gap: Top 5 banks hold {top5sh:.1f}% of POS terminals — acquiring market is highly concentrated"
    leader_str = f"{leader['name']} leads at {leader['share_pct']:.1f}% market share. " if leader else ""
    body = (
        f"In {month}, the top 5 banks account for {top5sh:.1f}% of all deployed POS terminals in India. "
        f"{leader_str}"
        f"All remaining banks combined share less than {100 - top5sh:.1f}% of merchant acquiring infrastructure."
    )
    implication = (
        f"{top5sh:.1f}% of all POS machines in India are owned by just 5 banks — "
        "and so is most of the merchant transaction data that comes with them. "
        "If you're building merchant credit products (loans to shopkeepers or small businesses) "
        "and don't have data partnerships with these top banks, you're working with an incomplete picture. "
        "Alternate sources — GST filings, UPI transaction data — can partially fill this gap."
    )
    return insight(
        "gap-pos-concentration", "infra", "top_n", month, title, body,
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "pos_terminals"},
        explore={"mode": "top_n", "topN": 5},
        type_="gap",
        implication=implication,
        source_signals=[
            "groups.infra.top_n.top5_share_pct",
            "groups.infra.top_n.banks.0.share_pct",
        ],
        chain=[
            f"Top 5 banks own {top5sh:.1f}% of POS terminals — merchant acquiring infrastructure highly concentrated",
            "Merchant transaction data (sales history needed for credit underwriting) controlled by the same 5 institutions",
            "Merchant credit underwriting without data partnerships with these banks requires alternates — GST filings, UPI feeds",
        ],
        signals_dict=s,
    )


def gap_foreign_cc_decline(s, month) -> dict | None:
    """Foreign bank CC share small and declining — premium segment thinning."""
    by_type = s["groups"]["cc"]["by_type"]
    cats    = by_type.get("categories", {})
    foreign = cats.get("Foreign", {})
    sh      = foreign.get("share_pct")
    delta   = foreign.get("share_delta_pp")
    if sh is None:
        return None
    if sh >= 5 and (delta is None or delta >= -0.1):
        return None  # only flag when small or declining
    title = f"Gap: Foreign bank CC share at {sh:.1f}%{f' ({sign(delta)}pp MoM)' if delta else ''} — premium segment shrinking"
    body = (
        f"Foreign banks hold only {sh:.1f}% of total credit cards outstanding in {month}"
        f"{f', down {abs(delta):.2f}pp vs prior month' if delta and delta < 0 else ''}. "
        f"Foreign banks traditionally serve the high-income, high-spend segment — their declining "
        f"share signals continued loss of the premium CC market to private Indian banks."
    )
    implication = (
        f"Foreign banks (Amex, Standard Chartered, etc.) traditionally served high-income customers — "
        "high credit limits, frequent international travel, premium cards. "
        "With their share at just {sh:.1f}% and still falling, those customers are now largely "
        "being served by Indian private banks instead. "
        "For anyone analysing RBI's credit card data, this means the premium borrower segment "
        "is now in the domestic bank numbers — not in a separate foreign bank bucket."
    )
    return insight(
        "gap-foreign-cc-decline", "cc", "by_type", month, title, body,
        effect={"highlight": ["Foreign", "Total"], "tab": "distribution", "distMode": "pct", "focusCard": "credit_cards"},
        explore={"mode": "by_type"},
        type_="gap",
        implication=implication,
        source_signals=[
            "groups.cc.by_type.categories.Foreign.share_pct",
            "groups.cc.by_type.categories.Foreign.share_delta_pp",
        ],
        chain=[
            f"Foreign banks hold only {sh:.1f}% of CC cards and declining — premium card segment exiting to Indian private banks",
            "Foreign banks (Amex, Standard Chartered) traditionally served high-income, high-limit, internationally-active customers",
            "Premium cardholder behaviour is under-represented in RBI aggregate CC data — now consolidated into private bank numbers",
        ],
        signals_dict=s,
    )


def gap_dc_ecom_low(s, month) -> dict | None:
    """DC ecom <10% of DC vol — debit card digital footprint is thin."""
    cross   = s["groups"]["dc"]["total"]["cross"]
    ecom    = cross.get("dc_ecom_txn_vol", {})
    ecom_sh = ecom.get("share_pct")
    atm_sh  = cross.get("dc_atm_withdrawal_vol", {}).get("share_pct")
    if ecom_sh is None or ecom_sh >= 10:
        return None
    title = f"Gap: DC ecommerce at {ecom_sh:.1f}% of DC volume — debit cards leave thin digital footprints"
    body = (
        f"Debit card ecommerce transactions account for only {ecom_sh:.1f}% of total DC transaction "
        f"volume in {month}. "
        f"{f'ATM cash dominates at {atm_sh:.1f}%. ' if atm_sh else ''}"
        f"The vast majority of debit card holders transact primarily via ATM cash withdrawal, "
        f"with minimal digital payment activity."
    )
    implication = (
        f"Only {ecom_sh:.1f}% of debit card volume is online spending — the rest is mostly ATM cash. "
        "For the typical debit card holder, their transaction history is largely cash withdrawals, "
        "which tells you very little about their financial behaviour. "
        "To lend to this segment, bureau scores (CIBIL, Experian) and income proxies "
        "(salary credits, GST filings) will be far more reliable than transaction data models."
    )
    return insight(
        "gap-dc-ecom-low", "dc", "total", month, title, body,
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "dc_ecom"},
        type_="gap",
        implication=implication,
        source_signals=[
            "groups.dc.total.cross.dc_ecom_txn_vol.share_pct",
            "groups.dc.total.cross.dc_atm_withdrawal_vol.share_pct",
        ],
        chain=[
            f"DC ecommerce at only {ecom_sh:.1f}% of DC volume — debit history is predominantly ATM cash withdrawals",
            "Cash withdrawal records reveal nothing about spending behaviour — categories, merchants, frequency unknown",
            "Income proxies (salary credits, GST filings) and bureau scores are more reliable than transaction models for this segment",
        ],
        signals_dict=s,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Orchestrate
# ══════════════════════════════════════════════════════════════════════════════

RULES = [
    # CC — insights
    cc_ecom_vs_pos,
    cc_atm_withdrawal_trend,
    cc_cards_streak,
    cc_transaction_surge,
    cc_category_share_shift,
    cc_top_bank_concentration,
    # CC — gaps
    gap_foreign_cc_decline,
    # DC — insights
    dc_atm_trend,
    dc_atm_share_structural,
    dc_pos_cash_decline,
    dc_ecom_share,
    dc_cards_streak,
    dc_category_dominance,
    dc_top_bank,
    # DC — gaps
    gap_dc_cash_dominance,
    gap_dc_ecom_low,
    # Infra — insights
    infra_qr_per_pos,
    infra_pos_streak,
    infra_upi_vs_bharat_qr,
    infra_category_pos,
    infra_top_bank_pos,
    # Infra — gaps
    gap_bharat_qr_contraction,
    gap_atm_offsite_decline,
    gap_pos_concentration,
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
