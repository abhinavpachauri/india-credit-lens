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


def insight(id_, group, cut, period, title, body, effect, explore=None,
            type_="insight", implication=None, source_signals=None):
    return {
        "id":            id_,
        "group":         group,
        "cut":           cut,
        "period":        period,
        "type":          type_,
        "title":         title,
        "body":          body,
        "implication":   implication,
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
        f"With ecommerce at {ecom_sh:.1f}% of CC volume, the majority of CC spend is now card-not-present (CNP). "
        f"Lenders should review fraud scoring models calibrated on POS-dominant spend patterns — "
        f"CNP transactions carry higher chargeback exposure and require digital-first decisioning."
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
            f"Rising CC ATM cash withdrawals over {streak} months signals growing cash advance "
            "dependency in credit card portfolios. Cash advances typically attract higher interest "
            "rates and no grace periods — monitor for elevated delinquency risk in segments showing "
            "this pattern."
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
            f"Consecutive months of CC card growth ({streak} months) indicates sustained acquisition momentum. "
            f"Lenders should track activation rates alongside issuance — dormant card growth inflates "
            "headline numbers without building transaction-based credit history."
        )
    else:
        implication = (
            f"Consecutive months of CC card decline ({streak} months) may signal intentional "
            "portfolio pruning (loss-making or inactive accounts) or competitive attrition. "
            "Lenders acquiring from the secondary market should verify whether this is "
            "quality-driven contraction or market share loss."
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
        f"{gainer} banks gaining {g_delta:.1f}pp CC share signals a shift in acquisition strategy or "
        f"partnership activity in that segment. For lenders benchmarking portfolio quality, "
        f"tracking which bank type is gaining share helps contextualise portfolio concentration risk "
        f"and pricing expectations in the credit card market."
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
            f"A rank change in the top-5 CC issuers reflects meaningful shifts in acquisition pace "
            f"or portfolio quality management. Lenders benchmarking competitive positioning should "
            f"track whether the move is driven by new card issuance or balance attrition."
        )
        return insight(
            "cc-top-bank-rank-change", "cc", "top_n", month, title, body,
            effect={"highlight": [rc["name"], "Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "credit_cards"},
            explore={"mode": "top_n", "topN": 10},
            implication=implication,
            source_signals=["groups.cc.top_n.rank_changes", "groups.cc.top_n.top5_share_pct"],
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
            f"With {top5sh:.1f}% concentration in the top 5 CC issuers, smaller banks have limited "
            "scale to build competitive rewards programs or co-brand partnerships. For credit strategy "
            "teams, this concentration means data from RBI's aggregate CC series is effectively "
            "proxied by a handful of banks' portfolios."
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
            "Growing comfort with digital debit payments among traditionally cash-dependent segments "
            "improves transaction data quality for underwriting. Debit-transacting customers who "
            "shift to digital payments build richer footprints — a precursor for credit product "
            "eligibility assessments."
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
        )

    if sd == "up" and streak >= 3:
        title = f"DC ATM withdrawals rising — {streak_label(streak, 'up')} ({mom:+.1f}% MoM)"
        body = f"Debit card ATM withdrawal volume grew {mom:.1f}% MoM in {month}. "
        if atm_sh:
            body += f"Cash accounts for {atm_sh:.1f}% of total DC volume."
        implication = (
            f"Sustained DC ATM growth ({streak} months) indicates cash-dependent transaction patterns "
            "remain strong. For lenders building alternate data underwriting, this signals a large "
            "segment that leaves limited digital footprints — cash-first behaviour requires "
            "bureau-plus-physical verification approaches."
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
        f"Debit card ecommerce at {ecom_sh:.1f}% of DC volume creates a digitally-traceable "
        "subpopulation of debit-only customers — higher-value prospects for credit product cross-sell. "
        "Lenders with access to debit transaction data should segment by digital vs ATM-cash "
        "behaviour to prioritise credit outreach."
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
        f"India debit card base at {fmt_num(latest)} provides a large population with formal banking "
        "access. However, card count alone overstates addressable credit opportunity — "
        "lenders should focus on the active-transacting subset, which is the realistic "
        "pool for first-credit products."
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
        f"PSB dominance at {psb_sh:.1f}% of debit cards reflects Jan Dhan linkage and rural banking "
        "penetration rather than active acquisition. For credit lenders, PSB debit portfolios skew "
        "toward low-income, low-activity accounts — transaction-based underwriting signals must be "
        "calibrated separately from urban private bank debit portfolios."
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
            "Rank changes in debit card leaders often reflect PSB account closure campaigns or "
            "private bank expansion in Tier 2/3 cities. The bank gaining rank is expanding its "
            "bankable population base — a leading indicator of future credit origination volume."
        )
        return insight(
            "dc-top-bank-rank-change", "dc", "top_n", month, title, body,
            effect={"highlight": [rc["name"], "Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "debit_cards"},
            explore={"mode": "top_n", "topN": 10},
            implication=implication,
            source_signals=["groups.dc.top_n.rank_changes", "groups.dc.top_n.top5_share_pct"],
        )

    title = f"{leader['name']} leads DC cards at {leader['share_pct']:.1f}%"
    body = (
        f"{leader['name']} holds {leader['share_pct']:.1f}% of total debit cards in {month} "
        f"({leader['mom_pct']:+.1f}% MoM). "
        f"Top 5 banks account for {top5sh:.1f}%{f' ({sign(delta)}pp vs prior month)' if delta else ''}."
    )
    implication = (
        f"The top 5 DC banks hold {top5sh:.1f}% of debit cards. For lenders using debit card "
        "transaction data in underwriting, coverage quality is largely determined by data-sharing "
        "arrangements with these top banks — gaps in coverage create blind spots for credit decisions."
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
        f"At {latest:.0f} UPI QR codes per POS terminal, QR-based merchant acceptance has decisively "
        "outpaced hardware deployment. Lenders without credit products accessible via UPI QR "
        "(credit on UPI, BNPL on QR) are structurally excluded from the long-tail merchant base "
        "that has no POS terminal — this is the majority of small merchants."
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
            f"Growing POS terminal count ({fmt_num(latest)} and rising) signals merchant "
            "formalisation — merchants deploying POS terminals generate transaction histories "
            "that can underpin MSME credit assessments. Lenders with POS-linked lending "
            "products (merchant cash advances, working capital) benefit from this infrastructure growth."
        )
    else:
        implication = (
            "Contracting POS terminal count may indicate QR-based acceptance is substituting "
            "hardware deployment. Lenders using POS transaction data for merchant underwriting "
            "should re-evaluate data sourcing strategy as merchant activity migrates to QR rails."
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
        f"UPI QR at {ratio:.0f}x Bharat QR scale means any payments or lending infrastructure "
        "built on Bharat QR rails is operating on a de facto deprecated standard. "
        "Lenders evaluating QR-linked credit products should anchor on UPI QR as the only "
        "viable acceptance network at scale."
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
        f"{gainer} banks expanding POS share signals growing merchant acquiring relationships in that "
        "segment. Banks with strong POS networks have the richest merchant transaction data — "
        "relevant for co-branded card partnerships and MSME merchant credit origination."
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
        f"Top 5 banks controlling {top5sh_val:.1f}% of POS terminals means merchant acquiring — "
        "and by extension, merchant transaction data — is concentrated in a handful of institutions. "
        "Lenders building merchant credit products outside these banks face significant data "
        "coverage gaps. Co-lending or data-sharing with top POS acquirers is a prerequisite for scale."
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
        f"Year-end CC transaction surges (avg {avg_mom:.1f}% MoM across all types) are seasonal — "
        "not reflective of structural demand growth. Underwriters should normalise Q4 spend volumes "
        "when assessing credit utilisation or limit adequacy to avoid overstating repayment capacity."
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
        f"DC ATM cash at {atm_sh:.1f}% and declining creates an expanding segment of digitally-active "
        "debit customers with improving transaction footprints. Lenders with access to debit "
        "transaction data should segment on this shift — moving-to-digital debit customers are "
        "prime candidates for first-credit product origination."
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
        "Declining POS cash-back withdrawals indicate merchants and customers are shifting toward "
        "net digital payments rather than using POS as a cash-out channel. This is a positive "
        "signal for POS-data quality — transaction records increasingly reflect actual purchases "
        "rather than cash access events, improving their value for credit underwriting."
    )
    return insight(
        "dc-pos-cash-decline", "dc", "total", month, title, body,
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "mom", "focusCard": "dc_pos_wd"},
        implication=implication,
        source_signals=[
            "groups.dc.total.metrics.dc_pos_withdrawal_vol.mom_pct",
            "groups.dc.total.metrics.dc_pos_withdrawal_vol.streak_months",
        ],
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
        f"With {atm_sh:.1f}% of DC volume still being ATM cash, the majority of debit card "
        "transactions leave no digital footprint for underwriting purposes. Lenders building "
        "alternate data credit models on debit transaction data face severe coverage gaps — "
        "bureau supplementation remains essential for the cash-dominant debit segment."
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
        f"Bharat QR's {bqr_mom:.1f}% MoM decline signals the standard is being actively abandoned "
        "by merchants. Any lending or payments product built on Bharat QR infrastructure "
        "faces accelerating merchant disengagement. Reallocate merchant acquisition "
        "and credit-linked acceptance strategy to UPI QR rails exclusively."
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
        "Declining offsite ATMs reduce repayment infrastructure for rural borrowers who remain "
        "cash-dependent. Lenders with rural loan books should assess whether offsite ATM "
        "coverage in their geographies is contracting — this can impair EMI collection "
        "in areas without digital payment penetration."
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
        f"POS concentration at {top5sh:.1f}% in 5 banks means meaningful merchant transaction data "
        "for credit underwriting is controlled by a tiny number of institutions. Lenders without "
        "data-sharing partnerships with these top POS acquirers are effectively blind to the "
        "majority of formal merchant transaction history in India."
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
        f"Foreign bank CC share at {sh:.1f}% and declining means the premium-card, high-limit "
        "borrower segment is consolidating within Indian private banks. For credit intelligence, "
        "the RBI CC data increasingly reflects domestic bank portfolios — foreign bank premium "
        "cardholder behaviour is underrepresented and requires separate data sources."
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
        f"DC ecommerce at {ecom_sh:.1f}% of volume means debit card transaction histories are "
        "predominantly cash events — not useful for digital underwriting. Lenders building "
        "first-credit products for the debit-primary mass market should rely on bureau + "
        "income-proxy signals rather than transaction-data models, which will suffer from "
        "severe data sparsity in this population."
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
