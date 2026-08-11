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
import re
import shutil
from pathlib import Path

import sys
from dataclasses import dataclass, field
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core.paths import ROOT
from signals.dominance import move_dominance, short_entity
SIGNALS_IN  = ROOT / "analysis/rbi_atm_pos/signals.json"
OUT_PATH    = ROOT / "analysis/rbi_atm_pos/insights.json"
WEB_PATH    = ROOT / "web/public/data/atm_pos_insights.json"
EVAL_DIR    = ROOT / "analysis/signals/evaluations/atm_pos"

# ── LLM representation layer ──────────────────────────────────────────────────
# Same architecture as SIBC: deterministic selection + UI routing + traceable
# facts (everything below), but the annotation PROSE for scalar insights comes
# from the LLM evaluation (signals.db → evaluate.py → evaluations/atm_pos/{period}.json,
# prompt v1.11, via the API). The LLM interprets the computed signals; Stage 4c
# then hard-checks every number it wrote against signals.db. Scan / share /
# concentration / composed insights stay deterministic — the SIBC scalar=LLM,
# scan=deterministic split.
#
# Each entry maps a deterministic insight id → the registered signal_id whose LLM
# narrative becomes its representation. Only 1:1 anchors with a registered signal
# qualify; composed/ratio/scan insights are intentionally absent (stay deterministic).
EVAL_ANCHOR = {
    # YoY scalar trajectory
    "cc-cards-yoy":            "cc-outstanding-yoy",
    "dc-cards-yoy":            "dc-outstanding-yoy",
    "infra-pos-yoy":           "pos-terminals-yoy",
    "infra-upi-yoy":           "upi-qr-yoy",
    # streaks (consecutive-month runs) — registered csv_streak signals
    "cc-cards-streak":         "cc-outstanding-streak",
    "dc-cards-streak":         "dc-outstanding-streak",
    "infra-pos-streak":        "pos-terminals-pos-streak",
    "cc-atm-declining":        "cc-atm-vol-streak",
    "dc-atm-declining":        "dc-atm-vol-streak",
    "dc-pos-cash-decline":     "dc-pos-withdrawal-vol-streak",
    # cross-metric ratios
    "infra-qr-per-pos":        "upi-qr-per-pos",
    "infra-upi-vs-bharat-qr":  "upi-bharat-qr-ratio",
    # cross-metric volume shares (registered csv_ratio_sum signals)
    "cc-ecom-vs-pos-share":    "cc-ecom-vol-share",
    "dc-ecom-share":           "dc-ecom-vol-share",
    "dc-atm-share-structural": "dc-atm-vol-share",
}


def load_eval_signals(period: str) -> tuple[dict, str | None]:
    """Flatten the latest atm_pos LLM evaluation → {signal_id: entry}, plus its
    prompt_version. Returns ({}, None) if no eval exists for the period (the
    dashboard then falls back to deterministic prose — gate never breaks)."""
    path = EVAL_DIR / f"{period}.json"
    if not path.exists():
        return {}, None
    with open(path) as f:
        ev = json.load(f)
    flat = {}
    for _dom, dd in ev.get("domains", {}).items():
        for sid, se in dd.get("signals", {}).items():
            flat[sid] = se
    return flat, ev.get("prompt_version")


def _dominance_caveat(ins: dict, dom) -> None:
    """Rewrite an anchored insight whose aggregate move is a single-entity artifact. The headline
    number is real and kept; the narrative that would call it a market signal is replaced with a
    grounded, number-free caveat (the concentration facts land in basis.facts, which trace to the
    bank scan). This is why-over-what: the aggregate fell, but the *why* is one issuer's reporting,
    not the market — so we do not let the LLM narrate a 'collapse'."""
    entity = short_entity(dom.top_entity) or "one issuer"
    rose = dom.ex_top_yoy_pct is not None and dom.ex_top_yoy_pct > 0.5
    rest = ("edged up over the year" if rose else
            "was essentially flat over the year" if dom.ex_top_yoy_pct is not None and abs(dom.ex_top_yoy_pct) <= 0.5
            else "barely moved over the year")
    base = re.sub(r"[-+]?\d[\d.,]*\s*%?\s*(YoY|×|x)?", "", ins.get("title", "").split(" — ")[0]).strip(" —")
    if dom.via_denominator:
        # A ratio: the jump is the denominator (a per-entity count) lurching at one issuer, not the
        # numerator outpacing the market — the "record" is arithmetically spurious.
        ins["title"] = f"{base} — the jump is {entity}'s count, not a real shift"
        ins["body"] = (
            f"This ratio looks like it hit a record, but the move is almost entirely its denominator: "
            f"{entity}'s reported count fell sharply in a single month while the numerator barely "
            f"changed. Across every other bank the denominator held steady, so the ratio's jump is a "
            f"reporting artifact, not the market pulling apart.")
        ins["implication"] = (f"Discount the record — the ratio moved because {entity}'s reported count "
                              f"changed, not because the two sides really diverged.")
    else:
        # A raw aggregate: keep it as a real read, but attribute it — this is the issuer story, and
        # the market-level reading is what the rest of the banks did. We name the driver (a fact from
        # the bank scan); we hedge the cause, which we have not sourced.
        pct = f"{dom.agg_value:+.1f}%" if dom.agg_value is not None else "sharply"
        ins["title"] = f"{base} {pct} YoY — but it's {entity}, not the market"
        ins["body"] = (
            f"The headline {pct} year-on-year move is almost entirely {entity}: its reported count fell "
            f"sharply in a single month and accounts for nearly all of the change, while across every "
            f"other bank the fleet {rest}. This looks like a base or reporting change at {entity} — most "
            f"likely a reclassification of how terminals are counted — not a market-wide shift. (The "
            f"specific reason is not yet sourced; the concentration is straight from the bank-level data.)")
        ins["implication"] = (f"Read the market signal off the other banks — flat-to-steady — not the "
                              f"headline, which is {entity}'s reporting change.")
    ins.setdefault("basis", {}).setdefault("facts", [])
    ins["basis"]["facts"] = [f for f in ins["basis"].get("facts", [])] + [dom.as_facts()]
    ins.setdefault("reasoning", {"signals": []})["chain"] = [ins["body"], ins["implication"]]
    if ins.get("basis"):
        ins["basis"]["inferences"] = ins["reasoning"]["chain"]
    ins["representation"] = "deterministic-dominance"
    ins["single_entity_artifact"] = True
    ins["eval_signal"] = dom.metric   # keep the signal link so the card can still be ranked/traced


def apply_dominance_guard(insights: list, period: str | None) -> int:
    """Rewrite any anchored insight whose aggregate move is one entity's artifact. Returns the
    count guarded.

    This runs on its OWN, before and independent of the LLM layer, and that independence is the
    point. The guard used to live inside apply_llm_representation, after the `if not se: continue`
    that skips a card with no evaluation entry — so it only fired when the LLM had something to
    say. A period with no evaluation got no guard at all, and the POS "−15.8% collapse" that was
    98% one issuer would have published unattributed. A deterministic guard must not be
    conditional on a non-deterministic step having run.
    """
    if not period:
        return 0
    guarded = 0
    for ins in insights:
        if ins.get("representation") == "deterministic-db":
            continue   # relational cards carry their own grounded prose
        anchor = EVAL_ANCHOR.get(ins["id"])
        if not anchor:
            continue
        dom = move_dominance("atm_pos", anchor, period)
        if dom and dom.dominant:
            _dominance_caveat(ins, dom)
            guarded += 1
    return guarded


def apply_llm_representation(insights: list, eval_signals: dict, prompt_version, period=None) -> int:
    """Override the prose (title/body/implication/chain) of anchored scalar
    insights with the LLM narrative; keep deterministic selection, UI routing
    (effect/exploreAction), sourceSignals and basis.facts. Returns the count
    converted to LLM representation.

    Cards already rewritten by the dominance guard keep that grounded caveat — an aggregate that
    isn't a real market move must never be narrated as one."""
    converted = 0
    for ins in insights:
        if ins.get("representation") in ("deterministic-db", "deterministic-dominance"):
            continue   # prose already settled: relational, or a single-entity artifact
        ins["representation"] = "deterministic"
        anchor = EVAL_ANCHOR.get(ins["id"])
        se = eval_signals.get(anchor) if anchor else None
        if not se:
            continue
        body  = " ".join(x for x in [se.get("observation", ""), se.get("direction", "")] if x).strip()
        chain = se.get("chain") or []
        impl  = se.get("inference") or ins.get("implication")
        title = se.get("title") or ins["title"]
        if not (body and chain):
            continue  # incomplete eval entry → keep deterministic
        ins["title"]       = title
        ins["body"]        = body
        ins["implication"] = impl
        # chain feeds both the card back-compat path (reasoning.chain) and the
        # shared schema (basis.inferences) — keep them in sync.
        ins.setdefault("reasoning", {"signals": []})
        ins["reasoning"]["chain"] = chain
        if ins.get("basis"):
            ins["basis"]["inferences"] = chain
        ins["representation"] = "llm"
        ins["eval_signal"]    = anchor
        ins["prompt_version"] = prompt_version
        converted += 1
    return converted

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


def yoy_phrase(accel_pp: float | None) -> str:
    """Describe the trajectory of a YoY growth rate vs the prior month's YoY rate."""
    if accel_pp is None:
        return "holding steady"
    if accel_pp >= 0.5:
        return "accelerating"
    if accel_pp <= -0.5:
        return "decelerating"
    return "holding steady"


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


def build_basis(s: dict, keys: list, chain: list) -> dict:
    """Shared insight schema (same shape as SIBC): basis.facts = the traceable
    data points this rests on, basis.inferences = the reasoning chain the card
    renders. One contract across both pipelines, one traceability validator."""
    facts = []
    for key in keys:
        val = get_signal_value(s, key)
        if val is not None:
            label = ".".join(key.split(".")[-2:])    # short, readable
            facts.append(f"{label}: {round(val, 2)}")
    facts.append("Source: web/public/data/atm_pos_consolidated.csv")
    return {"facts": facts, "inferences": chain}


# ── Gap cards, declared rather than hand-written ──────────────────────────────
# A "gap" is the platform saying what the data cannot tell you: cash that leaves no digital
# record, a premium segment that has migrated out of view, acquiring infrastructure held by
# five banks. Each one used to be its own ~45-line function, and all six repeated the same
# four steps — walk a dot-path, test a threshold, interpolate the numbers, assemble the card.
#
# Only two of those steps carry any judgment: WHEN a gap is worth raising, and WHAT it means
# for someone lending money. Those stay as authored Python, because they are authored: the
# "so what" on cash dominance is a claim about bureau scores, not something a template could
# derive. Everything mechanical is now done once, below.
#
# The reason this is worth doing beyond line count: `sourceSignals` used to be typed out a
# second time, by hand, next to the paths the function had already read. Two lists that must
# agree and nothing checking that they do. Here a card reads its values THROUGH its
# declaration, so what it cites is what it used, by construction.

@dataclass(frozen=True)
class Card:
    """One dashboard card, as data.

    reads       — local name → dot-path into signals.json. Doubles as the card's sourceSignals,
                  so what a card cites is what it used.
    metric      — shorthand for the commonest case: a single metric's YoY block. Expands to the
                  four paths every trajectory card reads (yoy, yoy_prior, yoy_accel, latest)
                  under groups.{group}.total.metrics.{metric}, and merges with `reads`.
    fires_when  — given the read values, is this card worth showing this month? Returns False to
                  stay silent. A card that is not currently true must not be published.
    title/body/implication/chain — authored prose, handed the same values. These stay authored
                  because they are claims about lending, not formattings of a number.
    """
    id: str
    group: str
    cut: str
    reads: dict
    fires_when: object
    title: object
    body: object
    implication: object
    chain: object
    effect: dict
    explore: dict | None = None
    type: str = "insight"
    metric: str | None = None
    streak: str | None = None
    # Display-only, non-numeric reads (a bank name). Deliberately separate from `reads`: these
    # are prose, and a card's cited sourceSignals must all be traceable numbers.
    labels: dict = field(default_factory=dict)

    def _base(self) -> str:
        return f"groups.{self.group}.total.metrics.{self.metric or self.streak}"

    def paths(self) -> dict:
        """Every numeric path this card reads, shorthand expanded."""
        if self.metric:
            base = self._base()
            return {
                "yoy": f"{base}.yoy_pct",
                "prior_yoy": f"{base}.yoy_prior_pct",
                "accel": f"{base}.yoy_accel_pp",
                "latest": f"{base}.latest",
            } | dict(self.reads)
        if self.streak:
            base = self._base()
            return {
                "latest": f"{base}.latest",
                "streak": f"{base}.streak_months",
                "qoq": f"{base}.qoq_pct",
            } | dict(self.reads)
        return dict(self.reads)

    def label_paths(self) -> dict:
        """Non-numeric reads — a direction word, a quarter name. Never cited as evidence.

        `streak_dir` belongs here and not in `reads`: it is the string "up"/"down", and a
        card's sourceSignals are supposed to be numbers a reader could check.
        """
        out = dict(self.labels)
        if self.streak:
            out = {
                "streak_dir": f"{self._base()}.streak_dir",
                "prev_q": "meta.prev_quarter",
                "curr_q": "meta.curr_quarter",
            } | out
        return out


def read_raw(s: dict, key: str):
    """Traverse a dot-path and return whatever is there — a bank name, a label, anything.
    `get_signal_value` deliberately returns None for non-numbers, because a card's cited
    sourceSignals must all be traceable numbers; a name is prose, not evidence."""
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
    return node


def render_card(spec: Card, s: dict, month: str) -> dict | None:
    """Resolve a declaration against this month's signals — or return None if it stays silent."""
    paths = spec.paths()
    v = {name: get_signal_value(s, path) for name, path in paths.items()}
    v.update({name: read_raw(s, path) for name, path in spec.label_paths().items()})
    if not spec.fires_when(v):
        return None
    return insight(
        spec.id, spec.group, spec.cut, month,
        spec.title(v, month), spec.body(v, month),
        effect=spec.effect, explore=spec.explore, type_=spec.type,
        implication=spec.implication(v, month),
        source_signals=list(paths.values()),   # derived from what it reads — cannot drift
        chain=spec.chain(v, month),
        signals_dict=s,
    )


def produce(producer, s: dict, month: str) -> dict | None:
    """Run one card producer, whichever kind it is. Functions are the cards not yet migrated;
    GapCard declarations are the ones that are."""
    if isinstance(producer, Card):
        return render_card(producer, s, month)
    return producer(s, month)


def producer_name(producer) -> str:
    return producer.id if isinstance(producer, Card) else producer.__name__


def _pp(delta) -> str:
    """A parenthetical month-on-month move, or nothing at all when there is no prior value."""
    return f" ({sign(delta)}pp vs prior month)" if delta else ""


def _qoq(v) -> str:
    """" (+1.2% QoQ vs Q1 FY26)" — omitted when there is no quarter-on-quarter figure."""
    if v.get("qoq") is None:
        return ""
    return f" ({sign(v['qoq'])}% QoQ vs {v.get('prev_q') or 'prior quarter'})"


def _mom_pp(delta) -> str:
    """" (-0.12pp MoM)" — or nothing when there is no prior month to compare."""
    return f" ({sign(delta)}pp MoM)" if delta else ""


def _fell_pp(delta) -> str:
    """", down 0.12pp vs prior month" — only when it actually fell."""
    return f", down {abs(delta):.2f}pp vs prior month" if delta and delta < 0 else ""


def _ratio_gap(numerator, denominator) -> str:
    """" (150x gap)" — omitted when either side is missing or the denominator is zero."""
    if not (numerator and denominator and denominator > 0):
        return ""
    return f" ({round(numerator / denominator)}x gap)"


def _leader_line(name, share) -> str:
    """"HDFC Bank leads at 31.2% market share. " — omitted when there is no leader to name."""
    if not name or share is None:
        return ""
    return f"{name} leads at {share:.1f}% market share. "


def insight(id_, group, cut, period, title, body, effect, explore=None,
            type_="insight", implication=None, source_signals=None,
            chain=None, signals_dict=None):
    has_reasoning = bool(chain and signals_dict and source_signals)
    reasoning = build_reasoning(signals_dict, source_signals or [], chain) if has_reasoning else None
    basis     = build_basis(signals_dict, source_signals or [], chain) if has_reasoning else None
    return {
        "id":            id_,
        "group":         group,
        "cut":           cut,
        "period":        period,
        "type":          type_,
        "title":         title,
        "body":          body,
        "implication":   implication,
        "reasoning":     reasoning,   # kept for card back-compat (reasoning.chain)
        "basis":         basis,       # shared schema (basis.facts / basis.inferences)
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

# ══════════════════════════════════════════════════════════════════════════════
# YoY TRAJECTORY RULES  (seasonally-clean — unlocked by the 2024 backfill)
# Year-on-year strips the seasonal swings (March FY-end, festive spikes) that
# dominate MoM. These rules report the YoY rate AND whether it is accelerating or
# decelerating vs the prior month's YoY rate — a trajectory MoM/streak can't show.
# ══════════════════════════════════════════════════════════════════════════════

def cc_spend_yoy(s, month) -> dict | None:
    """CC ecommerce vs POS spend — YoY growth, seasonally clean."""
    metrics = s["groups"]["cc"]["total"]["metrics"]
    ecom    = metrics.get("cc_ecom_txn_vol", {})
    pos     = metrics.get("cc_pos_txn_vol", {})
    e_yoy   = ecom.get("yoy_pct")
    p_yoy   = pos.get("yoy_pct")
    if e_yoy is None or p_yoy is None:
        return None
    if abs(e_yoy) < 5 and abs(p_yoy) < 5:
        return None  # nothing notable

    online_leads = e_yoy > p_yoy
    title = f"CC spend YoY — ecommerce {e_yoy:.1f}% vs in-store POS {p_yoy:.1f}%"
    body  = (
        f"On a year-on-year basis, credit card ecommerce transaction volume grew {e_yoy:.1f}% "
        f"and in-store POS volume grew {p_yoy:.1f}% as of {month}. "
        f"Year-on-year removes the heavy seasonality in the monthly numbers — "
        f"{'online is outpacing in-store' if online_leads else 'in-store is outpacing online'} on a clean comparison."
    )
    implication = (
        f"Credit card spend is growing across both channels year-on-year "
        f"({'ecom faster' if online_leads else 'POS faster'}). "
        "For credit-risk teams this matters: a spend mix tilting online means more "
        "card-not-present volume, where fraud and dispute rates run higher — provisioning "
        "and fraud models should track the channel mix, not just the headline spend growth."
    )
    return insight(
        "cc-spend-yoy", "cc", "total", month, title, body,
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "yoy", "focusCard": "cc_ecom"},
        explore={"mode": "by_type"},
        implication=implication,
        source_signals=[
            "groups.cc.total.metrics.cc_ecom_txn_vol.yoy_pct",
            "groups.cc.total.metrics.cc_pos_txn_vol.yoy_pct",
        ],
        chain=[
            f"CC ecommerce volume up {e_yoy:.1f}% YoY vs POS up {p_yoy:.1f}% YoY — both growing, seasonally clean",
            f"{'Online (CNP) is the faster-growing channel' if online_leads else 'In-store POS is the faster-growing channel'} on a year-on-year basis",
            "Channel mix shift changes the fraud and dispute profile — risk models must track mix, not just total spend",
        ],
        signals_dict=s,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Orchestrate
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# RELATIONAL CARDS (rotation + divergence — signals.db-sourced)
# ══════════════════════════════════════════════════════════════════════════════
# These read the registered relational signals from signals.db (kept honest by
# Check 2f) rather than signals.json — deterministic prose is the product
# (signals/README.md), built by core/relational_insights. Stage 4c validates
# them against their own db rows (representation "deterministic-db").

import sqlite3
from core.relational_insights import (
    rotation_insight, divergence_insight, pair_divergence_insight,
    rotation_distribution, entity_roles, _subject as relational_subject)
from signals.query import scan_distribution

DB_PATH = ROOT / "analysis/signals/signals.db"
REG_PATH = ROOT / "analysis/signals/registry.json"

# UI category names (charts) for the db's full bank_category labels.
CATEGORY_SHORT = {
    "Public Sector Banks":  "PSB",
    "Private Sector Banks": "Private",
    "Foreign Banks":        "Foreign",
    "Small Finance Banks":  "SFB",
    "Payment Banks":        "Payments",
}

ROTATION_CARDS = [
    # (signal_id, group, focusCard metric)
    ("cc-category-rotation",  "cc",    "credit_cards"),
    ("dc-category-rotation",  "dc",    "debit_cards"),
    ("pos-category-rotation", "infra", "pos_terminals"),
]
DIVERGENCE_CARDS = [
    ("cc-bank-divergence",  "cc",    "credit_cards"),
    ("dc-bank-divergence",  "dc",    "debit_cards"),
    ("pos-bank-divergence", "infra", "pos_terminals"),
]
# Declared co-movement pairs: (total-gap signal, bank-level signal | None,
# group, focusCard section). The bank-level signal, where one is registered,
# names where the total gap actually lives.
PAIR_CARDS = [
    ("cc-issuance-vs-spend-gap",    "cc-issuance-vs-spend-bank-gap", "cc",    "credit_cards"),
    ("dc-issuance-vs-spend-gap",    None,                            "dc",    "debit_cards"),
    ("pos-fleet-vs-spend-gap",      None,                            "infra", "pos_terminals"),
    ("atm-fleet-vs-withdrawal-gap", None,                            "infra", "atms"),
]


def _relational_card(sid, group, cut, month, rel, effect, facts, sources):
    # sources — [(signal_id, rows)]: every db signal the card rests on. Usually
    # one; a pair card rests on its total gap AND the bank-level rows behind it.
    # reasoning.signals carries those rows keyed "{signal_id}:{entity_id}" —
    # Stage 4d resolves these against signals.db (the deterministic-db analog
    # of its signals.json key check).
    reasoning_signals = [{"key": f"{s}:{e}", "value": round(v, 4)}
                         for s, rows in sources for e, v, _ in rows]
    card = insight(sid, group, cut, month, rel["title"], rel["body"], effect,
                   implication=rel["implication"])
    card["basis"]          = {"facts": facts, "inferences": rel["chain"]}
    card["reasoning"]      = {"signals": reasoning_signals, "chain": rel["chain"]}
    card["sourceSignals"]  = [s for s, _ in sources]
    card["representation"] = "deterministic-db"
    card["insight_kind"]   = rel["insight_kind"]
    return card


def relational_cards(s, month) -> list[dict]:
    """Rotation + divergence cards for the current period. No rows (window
    unavailable / nothing diverges) → no card, by construction."""
    period   = s["meta"]["latest_period"]
    registry = json.loads(REG_PATH.read_text())["signals"]
    roles    = entity_roles("atm_pos")
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    out: list[dict] = []

    for sid, group, metric in ROTATION_CARDS:
        dist, mass = rotation_distribution(conn, sid, "atm_pos", period)
        rel = rotation_insight(dist, mass, roles, relational_subject(registry[sid]))
        if rel is None:
            continue
        top = CATEGORY_SHORT.get(dist[0][0], dist[0][0])
        facts = [f"{e}: {v:+.2f} pp share vs a year ago" for e, v, _ in dist]
        if mass is not None:
            facts.append(f"Rotation mass: {mass:.2f} pp")
        facts.append(f"Source: signals.db ({sid})")
        out.append(_relational_card(
            sid, group, "by_type", month, rel,
            effect={"highlight": [top, "Total"], "tab": "distribution",
                    "distMode": "pct", "focusCard": metric},
            facts=facts, sources=[(sid, dist)]))

    for sid, group, metric in DIVERGENCE_CARDS:
        dist = scan_distribution(conn, sid, "atm_pos", period)
        rel = divergence_insight(dist, relational_subject(registry[sid]),
                                 member_noun="bank", parent_is_per_entity=True)
        if rel is None:
            continue
        lead = max(dist, key=lambda r: abs(r[1]))[0]
        facts = [f"{e}: {v:+.2f} pp vs its category's YoY pace" for e, v, _ in dist]
        facts.append(f"Source: signals.db ({sid})")
        out.append(_relational_card(
            sid, group, "by_bank", month, rel,
            effect={"highlight": [lead, "Total"], "tab": "trend",
                    "trendMode": "yoy", "focusCard": metric},
            facts=facts, sources=[(sid, dist)]))

    out += pair_cards(conn, registry, period, month)
    conn.close()
    return out


def pair_cards(conn, registry, period, month) -> list[dict]:
    """Declared co-movement pairs (metric axis of divergence). A pair earns a
    card only when its two sides have come apart — a 'stable' gap means they
    are still moving together, and the insight builder suppresses it."""
    out: list[dict] = []
    for total_sid, bank_sid, group, metric in PAIR_CARDS:
        rows = dict(conn.execute(
            "SELECT entity_id, value FROM signals WHERE pipeline='atm_pos' "
            "AND period=? AND metric_id=? AND entity_type IN ('aggregate','pair_side')",
            (period, total_sid)).fetchall())
        status_row = conn.execute(
            "SELECT status FROM signals WHERE pipeline='atm_pos' AND period=? "
            "AND metric_id=? AND entity_type='aggregate'",
            (period, total_sid)).fetchone()
        if "total" not in rows or status_row is None:
            continue
        gap, status = rows["total"], status_row[0]
        flagged = scan_distribution(conn, bank_sid, "atm_pos", period) if bank_sid else []
        comp = registry[total_sid]["compute"]
        rel = pair_divergence_insight(gap, status, comp["a"]["label"],
                                      comp["b"]["label"],
                                      rows.get("a"), rows.get("b"), flagged)
        if rel is None:
            continue
        facts = [f"{comp['a']['label']} vs {comp['b']['label']}: "
                 f"{gap:+.2f} pp apart year on year",
                 f"{comp['a']['label']}: {rows.get('a', float('nan')):+.2f}% YoY",
                 f"{comp['b']['label']}: {rows.get('b', float('nan')):+.2f}% YoY"]
        facts += [f"{e}: {v:+.2f} pp — issuance ahead of spend on its own book"
                  for e, v, _ in flagged]
        facts.append(f"Source: signals.db ({total_sid}"
                     + (f", {bank_sid})" if bank_sid else ")"))
        sources = [(total_sid, [(e, v, status) for e, v in rows.items()])]
        if flagged:
            sources.append((bank_sid, flagged))
        out.append(_relational_card(
            total_sid, group, "total", month, rel,
            effect={"highlight": ["Total"], "tab": "trend",
                    "trendMode": "yoy", "focusCard": metric},
            facts=facts, sources=sources))
    return out


# ══════════════════════════════════════════════════════════════════════════════
# YoY TRAJECTORY CARDS — declared (see Card / render_card above)
# ══════════════════════════════════════════════════════════════════════════════
# One metric, read year-on-year: where it stands, whether the rate itself is speeding up or
# slowing down, and what that means for someone lending against it. Four cards, one shape —
# `metric=` expands to the four paths each of them reads, so the paths appear once instead of
# eight times (read, then cited).
#
# The prose stays authored per card and stays verbatim. These read as different sentences
# because they ARE different claims: decelerating card issuance is a tightening story,
# decelerating POS deployment is a QR-substitution story. A shared template would have had to
# flatten that, and the flattening is the part worth keeping.

YOY_CARDS = [
    Card(
        id="cc-cards-yoy", group="cc", cut="total", metric="credit_cards", reads={},
        fires_when=lambda v: v["yoy"] is not None and abs(v["yoy"]) >= 2,
        title=lambda v, m: f"Credit cards growing {v['yoy']:.1f}% YoY — issuance {yoy_phrase(v['accel'])}",
        body=lambda v, m:
            f"Total credit cards outstanding reached {fmt_num(v['latest'])} in {m}, "
            f"up {v['yoy']:.1f}% year-on-year. "
            + (f"The YoY growth rate was {v['prior_yoy']:.1f}% a month ago, so issuance is "
               f"{yoy_phrase(v['accel'])} ({sign(v['accel'])}pp). "
               if v["prior_yoy"] is not None and v["accel"] is not None else "")
            + "Year-on-year strips out the seasonal swings — March year-end and festive spikes — that distort month-on-month.",
        implication=lambda v, m:
            f"Credit card issuance is running at {v['yoy']:.1f}% a year — a cleaner read on portfolio "
            f"growth than any single month, which is skewed by seasonality. "
            + ("A decelerating YoY rate is an early sign issuers are tightening acquisition — watch new-account approval rates next quarter."
               if yoy_phrase(v["accel"]) == "decelerating" else
               "A steady-to-accelerating YoY rate signals issuers are still leaning into acquisition; track activation, not just card count."),
        chain=lambda v, m: [
            f"Credit cards outstanding up {v['yoy']:.1f}% YoY — issuance momentum on a seasonally-clean basis",
            (f"YoY rate moved from {v['prior_yoy']:.1f}% to {v['yoy']:.1f}% — issuance is {yoy_phrase(v['accel'])}"
             if v["prior_yoy"] is not None else "Year-on-year removes seasonal distortion from the headline"),
            "YoY trajectory is the leading read on acquisition intensity — track activation rate alongside card count",
        ],
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "yoy", "focusCard": "credit_cards"},
        explore={"mode": "by_type"},
    ),

    Card(
        id="dc-cards-yoy", group="dc", cut="total", metric="debit_cards", reads={},
        # Debit moves slowly, so a small level change still matters if the RATE turned.
        fires_when=lambda v: v["yoy"] is not None and not (
            abs(v["yoy"]) < 2 and (v["accel"] is None or abs(v["accel"]) < 1)),
        title=lambda v, m: f"Debit card base {v['yoy']:+.1f}% YoY — growth {yoy_phrase(v['accel'])}",
        body=lambda v, m:
            f"Total debit cards outstanding stand at {fmt_num(v['latest'])} in {m}, "
            f"{v['yoy']:+.1f}% year-on-year. "
            + (f"The YoY rate was {v['prior_yoy']:+.1f}% a month ago — the base is "
               f"{yoy_phrase(v['accel'])} ({sign(v['accel'])}pp). "
               if v["prior_yoy"] is not None and v["accel"] is not None else "")
            + "Year-on-year smooths the month-to-month volatility from card reissuance and account closures.",
        implication=lambda v, m:
            f"The debit base is growing {v['yoy']:.1f}% a year — far slower than credit cards. "
            + ("A decelerating debit YoY often reflects PSBs pruning dormant Jan Dhan accounts — healthy, but it shrinks the headline pool, not the active one."
               if yoy_phrase(v["accel"]) == "decelerating" else
               "Debit growth is structurally slow; the active-transacting subset, not the headline count, is the real first-credit pool."),
        chain=lambda v, m: [
            f"Debit cards outstanding {v['yoy']:+.1f}% YoY — structurally slower than credit card growth",
            (f"YoY rate moved from {v['prior_yoy']:+.1f}% to {v['yoy']:+.1f}% — base is {yoy_phrase(v['accel'])}"
             if v["prior_yoy"] is not None else "Year-on-year smooths reissuance and closure volatility"),
            "Headline debit count is inflated by low-activity accounts — the active subset is the real credit opportunity",
        ],
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "yoy", "focusCard": "debit_cards"},
        explore={"mode": "by_type"},
    ),

    Card(
        id="infra-pos-yoy", group="infra", cut="total", metric="pos_terminals", reads={},
        # Fire on a clear deceleration story or material growth.
        fires_when=lambda v: v["yoy"] is not None and not (
            abs(v["yoy"]) < 2 and (v["accel"] is None or abs(v["accel"]) < 1.5)),
        title=lambda v, m: f"POS terminal growth {v['yoy']:+.1f}% YoY — deployment {yoy_phrase(v['accel'])}",
        body=lambda v, m:
            f"POS terminals reached {fmt_num(v['latest'])} in {m}, {v['yoy']:+.1f}% year-on-year. "
            + (f"A year-on-year basis a month ago showed {v['prior_yoy']:+.1f}% — deployment is "
               f"{yoy_phrase(v['accel'])} ({sign(v['accel'])}pp). "
               if v["prior_yoy"] is not None and v["accel"] is not None else "")
            + "Year-on-year is the honest read on hardware expansion; monthly figures bounce on bank deployment cycles.",
        implication=lambda v, m:
            f"POS terminal growth has slowed to {v['yoy']:.1f}% a year. "
            + ("Decelerating POS deployment alongside fast UPI QR growth is the merchant acceptance shift in one number — card-terminal hardware is being replaced by QR."
               if yoy_phrase(v["accel"]) == "decelerating" else
               "Steady POS growth means the card-acceptance footprint is still expanding — merchant transaction data for working-capital lending keeps widening.")
            + " If you underwrite merchants on POS data, watch whether your coverage is migrating to QR rails you can't see.",
        chain=lambda v, m: [
            f"POS terminals {v['yoy']:+.1f}% YoY — hardware acceptance growth on a seasonally-clean basis",
            (f"YoY rate moved from {v['prior_yoy']:+.1f}% to {v['yoy']:+.1f}% — deployment is {yoy_phrase(v['accel'])}"
             if v["prior_yoy"] is not None else "Year-on-year removes bank deployment-cycle noise"),
            "Decelerating POS growth signals merchant migration to UPI QR — POS-based merchant credit data coverage may be narrowing",
        ],
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "yoy", "focusCard": "pos_terminals"},
        explore={"mode": "by_type"},
    ),

    Card(
        id="infra-upi-yoy", group="infra", cut="total", metric="upi_qr", reads={},
        fires_when=lambda v: v["yoy"] is not None and abs(v["yoy"]) >= 3,
        title=lambda v, m: f"UPI QR acceptance up {v['yoy']:.1f}% YoY — expansion {yoy_phrase(v['accel'])}",
        body=lambda v, m:
            f"UPI QR codes deployed reached {fmt_num(v['latest'])} in {m}, up {v['yoy']:.1f}% year-on-year. "
            + (f"The YoY rate was {v['prior_yoy']:.1f}% a month ago — QR acceptance expansion is "
               f"{yoy_phrase(v['accel'])} ({sign(v['accel'])}pp). "
               if v["prior_yoy"] is not None and v["accel"] is not None else "")
            + "Year-on-year cuts through the monthly registration noise to show the true acceptance build-out.",
        implication=lambda v, m:
            f"QR acceptance is expanding {v['yoy']:.1f}% a year — far faster than POS hardware. "
            "Every new QR is a merchant who becomes reachable for credit-on-UPI and merchant BNPL. "
            "Any small-merchant lending product needs a QR-native distribution path; POS-only reach is shrinking by comparison.",
        chain=lambda v, m: [
            f"UPI QR codes up {v['yoy']:.1f}% YoY — acceptance footprint expanding far faster than POS hardware",
            (f"YoY rate moved from {v['prior_yoy']:.1f}% to {v['yoy']:.1f}% — expansion is {yoy_phrase(v['accel'])}"
             if v["prior_yoy"] is not None else "Year-on-year shows the true acceptance build-out beneath monthly noise"),
            "Each new QR is a reachable merchant for credit-on-UPI and BNPL — QR-native distribution is now the larger channel",
        ],
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "yoy", "focusCard": "upi_qr"},
        explore={"mode": "by_type"},
    ),
]

YOY = {c.id: c for c in YOY_CARDS}


# ══════════════════════════════════════════════════════════════════════════════
# STREAK CARDS — declared (see Card / render_card above)
# ══════════════════════════════════════════════════════════════════════════════
# A run of consecutive months moving the same way. The bar differs by metric — debit cards move
# slowly, so four months means what three means for credit cards — and so does the reading: a
# growing card base is an activation question, a shrinking POS fleet is a QR-migration question.

STREAK_CARDS = [
    Card(
        id="cc-cards-streak", group="cc", cut="total", streak="credit_cards", reads={},
        fires_when=lambda v: v["streak"] is not None and v["streak"] >= 3 and v["streak_dir"] != "flat",
        title=lambda v, m:
            f"Credit cards outstanding: {streak_label(int(v['streak']), v['streak_dir'])} — "
            f"{fmt_num(v['latest'])} cards",
        body=lambda v, m:
            f"Total credit cards outstanding reached {fmt_num(v['latest'])} in {m}{_qoq(v)}, "
            f"marking the {streak_label(int(v['streak']), v['streak_dir'])}. "
            + ("Issuance momentum is broad-based across bank types." if v["streak_dir"] == "up"
               else "Card attrition or issuance slowdown is underway."),
        implication=lambda v, m:
            (f"{int(v['streak'])} straight months of card growth looks good, but card count alone can mislead. "
             "Many new cards never get used — they sit inactive. "
             "What matters for lending is how many cards are actually being transacted on. "
             "Track activation rate (what percentage of issued cards have any spend in the last few months) alongside the headline number.")
            if v["streak_dir"] == "up" else
            (f"{int(v['streak'])} straight months of card decline could mean two things: banks are intentionally closing inactive or loss-making accounts (which is healthy), "
             "or they're losing customers to competitors (which is a red flag). "
             "Before drawing conclusions, check whether the decline is coming from one bank type or spread across all."),
        chain=lambda v, m: [
            f"CC cards outstanding {'growing' if v['streak_dir'] == 'up' else 'declining'} for {int(v['streak'])} consecutive months",
            "Card count includes dormant cards that were issued but never activated or used",
            "Activation rate (cards with any spend in recent months) is the real signal for credit origination potential",
        ],
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "credit_cards"},
        explore={"mode": "by_type"},
    ),

    Card(
        id="dc-cards-streak", group="dc", cut="total", streak="debit_cards", reads={},
        # A higher bar than credit cards: the debit base moves slowly, so three months is noise.
        fires_when=lambda v: v["streak"] is not None and v["streak"] >= 4 and v["streak_dir"] != "flat",
        title=lambda v, m:
            f"Debit cards: {streak_label(int(v['streak']), v['streak_dir'])} — {fmt_num(v['latest'])} outstanding",
        body=lambda v, m:
            f"Total debit cards outstanding reached {fmt_num(v['latest'])} in {m}{_qoq(v)}, "
            f"the {streak_label(int(v['streak']), v['streak_dir'])}. "
            + ("India debit base continues to expand." if v["latest"] and v["latest"] > 1e9 else ""),
        implication=lambda v, m:
            f"India has {fmt_num(v['latest'])} debit cards — but that number is misleading as a credit opportunity. "
            "A large chunk are Jan Dhan accounts (zero-balance accounts opened under the government's "
            "financial inclusion scheme) that see very little activity. "
            "The real pool for first-time credit products is much smaller — focus on debit card holders "
            "who are actually transacting, not just account holders.",
        chain=lambda v, m: [
            f"Debit card base at {fmt_num(v['latest'])} — large headline number includes substantial Jan Dhan zero-balance accounts",
            "Jan Dhan accounts (government financial inclusion scheme) skew toward low-income, low-activity customers",
            "Addressable credit opportunity is a fraction of total card count — active-transacting subset is the real pool",
        ],
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "debit_cards"},
        explore={"mode": "by_type"},
    ),

    Card(
        id="infra-pos-streak", group="infra", cut="total", streak="pos_terminals", reads={},
        fires_when=lambda v: v["streak"] is not None and v["streak"] >= 3 and v["streak_dir"] != "flat",
        title=lambda v, m:
            f"POS terminals: {streak_label(int(v['streak']), v['streak_dir'])} — {fmt_num(v['latest'])} deployed",
        body=lambda v, m:
            f"POS terminals reached {fmt_num(v['latest'])} in {m}{_qoq(v)}, "
            f"the {streak_label(int(v['streak']), v['streak_dir'])}. "
            + ("Physical acceptance infrastructure continues to expand." if v["streak_dir"] == "up"
               else "POS terminal count is contracting — QR-first acceptance may be replacing hardware."),
        implication=lambda v, m:
            (f"Every new POS machine deployed ({fmt_num(v['latest'])} and growing) is a merchant "
             "who starts building a transaction history — how much they sell, how often, which days. "
             "That data is exactly what lenders use to assess working capital loans (short-term "
             "business credit based on daily sales). More POS terminals means more merchants "
             "who can be lent to based on their actual business performance.")
            if v["streak_dir"] == "up" else
            ("POS terminal count falling likely means merchants are switching to UPI QR codes "
             "instead — cheaper, no hardware needed. If you use POS transaction data to assess "
             "merchant creditworthiness, your data coverage may be quietly shrinking as merchant "
             "activity shifts to QR rails where you may not have visibility."),
        chain=lambda v, m: [
            f"POS terminals {'growing' if v['streak_dir'] == 'up' else 'declining'} for {int(v['streak'])} months — now at {fmt_num(v['latest'])}",
            ("Each new POS terminal generates merchant transaction history (sales volume, frequency, ticket size)"
             if v["streak_dir"] == "up" else
             "Declining POS likely means merchant migration to UPI QR — cheaper and no hardware needed"),
            ("Growing POS base expands pool of merchants underwritable for working capital or merchant cash advances"
             if v["streak_dir"] == "up" else
             "POS-based merchant credit data coverage may be quietly shrinking as activity migrates to QR rails"),
        ],
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "pos_terminals"},
        explore={"mode": "by_type"},
    ),
]

STREAK = {c.id: c for c in STREAK_CARDS}


# ══════════════════════════════════════════════════════════════════════════════
# GAP CARDS — declared, not hand-written (see GapCard / render_gap above)
# ══════════════════════════════════════════════════════════════════════════════
# Read these as a list of standing questions the data cannot answer, each with the condition
# that makes it worth raising this month. The prose stays authored because it is a claim about
# lending, not a formatting of numbers.

GAPS = [
    Card(
        id="gap-foreign-cc-decline", group="cc", cut="by_type",
        reads={
            "share": "groups.cc.by_type.categories.Foreign.share_pct",
            "delta": "groups.cc.by_type.categories.Foreign.share_delta_pp",
        },
        # Small OR shrinking. A foreign-bank share that is both sizeable and steady is not a gap
        # in the data — it is just a fact about the market.
        fires_when=lambda v: v["share"] is not None and (
            v["share"] < 5 or (v["delta"] is not None and v["delta"] < -0.1)),
        title=lambda v, m:
            f"Gap: Foreign bank CC share at {v['share']:.1f}%{_mom_pp(v['delta'])}"
            f" — premium segment shrinking",
        body=lambda v, m:
            f"Foreign banks hold only {v['share']:.1f}% of total credit cards outstanding in {m}"
            f"{_fell_pp(v['delta'])}. "
            f"Foreign banks traditionally serve the high-income, high-spend segment — their declining "
            f"share signals continued loss of the premium CC market to private Indian banks.",
        implication=lambda v, m:
            f"Foreign banks (Amex, Standard Chartered, etc.) traditionally served high-income customers — "
            f"high credit limits, frequent international travel, premium cards. "
            f"With their share at just {v['share']:.1f}% and still falling, those customers are now largely "
            f"being served by Indian private banks instead. "
            f"For anyone analysing RBI's credit card data, this means the premium borrower segment "
            f"is now in the domestic bank numbers — not in a separate foreign bank bucket.",
        chain=lambda v, m: [
            f"Foreign banks hold only {v['share']:.1f}% of CC cards and declining — premium card segment exiting to Indian private banks",
            "Foreign banks (Amex, Standard Chartered) traditionally served high-income, high-limit, internationally-active customers",
            "Premium cardholder behaviour is under-represented in RBI aggregate CC data — now consolidated into private bank numbers",
        ],
        effect={"highlight": ["Foreign", "Total"], "tab": "distribution", "distMode": "pct",
                "focusCard": "credit_cards"},
        explore={"mode": "by_type"},
        type="gap",
    ),

    Card(
        id="gap-dc-cash-dominance", group="dc", cut="total",
        reads={
            "atm_share": "groups.dc.total.cross.dc_atm_withdrawal_vol.share_pct",
            "atm_delta": "groups.dc.total.cross.dc_atm_withdrawal_vol.share_delta_pp",
            "ecom_share": "groups.dc.total.cross.dc_ecom_txn_vol.share_pct",
        },
        fires_when=lambda v: v["atm_share"] is not None and v["atm_share"] >= 75,
        title=lambda v, m:
            f"Gap: DC ATM cash at {v['atm_share']:.1f}% of DC volume — digital transition is incomplete",
        body=lambda v, m:
            f"Despite growth in digital payments, ATM cash withdrawals still account for {v['atm_share']:.1f}% "
            f"of total debit card transaction volume in {m}{_pp(v['atm_delta'])}. "
            f"DC ecommerce is only {v['ecom_share']:.1f}% of DC volume. "
            f"India's debit card base remains overwhelmingly cash-dependent.",
        implication=lambda v, m:
            f"{v['atm_share']:.1f}% of debit card spending is ATM cash. Cash leaves no digital record — "
            "you can't tell where it was spent or on what. "
            "For lenders trying to assess a debit card holder's financial behaviour, the transaction "
            "history is mostly blank. Bureau scores (CIBIL, Experian) remain the primary tool "
            "for this segment — debit transaction data alone isn't enough yet.",
        chain=lambda v, m: [
            f"{v['atm_share']:.1f}% of DC volume is ATM cash — transactions that leave no digital record",
            "Cash-dominant customers' financial behaviour is opaque — spending categories, frequency, merchants all unknown",
            "Bureau scores (CIBIL, Experian) remain essential for this segment; debit transaction data alone is insufficient",
        ],
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "dc_atm"},
        type="gap",
    ),

    Card(
        id="gap-dc-ecom-low", group="dc", cut="total",
        reads={
            "ecom_share": "groups.dc.total.cross.dc_ecom_txn_vol.share_pct",
            "atm_share": "groups.dc.total.cross.dc_atm_withdrawal_vol.share_pct",
        },
        fires_when=lambda v: v["ecom_share"] is not None and v["ecom_share"] < 10,
        title=lambda v, m:
            f"Gap: DC ecommerce at {v['ecom_share']:.1f}% of DC volume — debit cards leave thin digital footprints",
        body=lambda v, m:
            f"Debit card ecommerce transactions account for only {v['ecom_share']:.1f}% of total DC transaction "
            f"volume in {m}. "
            + (f"ATM cash dominates at {v['atm_share']:.1f}%. " if v["atm_share"] else "")
            + f"The vast majority of debit card holders transact primarily via ATM cash withdrawal, "
              f"with minimal digital payment activity.",
        implication=lambda v, m:
            f"Only {v['ecom_share']:.1f}% of debit card volume is online spending — the rest is mostly ATM cash. "
            "For the typical debit card holder, their transaction history is largely cash withdrawals, "
            "which tells you very little about their financial behaviour. "
            "To lend to this segment, bureau scores (CIBIL, Experian) and income proxies "
            "(salary credits, GST filings) will be far more reliable than transaction data models.",
        chain=lambda v, m: [
            f"DC ecommerce at only {v['ecom_share']:.1f}% of DC volume — debit history is predominantly ATM cash withdrawals",
            "Cash withdrawal records reveal nothing about spending behaviour — categories, merchants, frequency unknown",
            "Income proxies (salary credits, GST filings) and bureau scores are more reliable than transaction models for this segment",
        ],
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "dc_ecom"},
        type="gap",
    ),

    Card(
        id="gap-bharat-qr-contraction", group="infra", cut="total",
        reads={
            "bqr_mom": "groups.infra.total.metrics.bharat_qr.mom_pct",
            "bqr": "groups.infra.total.metrics.bharat_qr.latest",
            "upi": "groups.infra.total.metrics.upi_qr.latest",
        },
        # Only a meaningful decline. A flat month is not merchants walking away.
        fires_when=lambda v: v["bqr_mom"] is not None and v["bqr_mom"] <= -1,
        title=lambda v, m:
            f"Gap: Bharat QR contracting {v['bqr_mom']:.1f}% MoM — "
            f"{fmt_num(v['bqr'])} vs {fmt_num(v['upi'])} UPI QR",
        body=lambda v, m:
            f"Bharat QR codes fell {abs(v['bqr_mom']):.1f}% MoM in {m}, now at {fmt_num(v['bqr'])} — "
            f"compared to {fmt_num(v['upi'])} UPI QR codes{_ratio_gap(v['upi'], v['bqr'])}. "
            f"Merchant preference has consolidated on UPI QR as the dominant QR acceptance standard.",
        implication=lambda v, m:
            f"Bharat QR is shrinking {abs(v['bqr_mom']):.1f}% every month — merchants are removing it. "
            "If any part of your lending or payments product depends on Bharat QR acceptance, "
            "that's a real problem. Move everything to UPI QR. "
            "There is no viable future for Bharat QR as a payments or credit infrastructure.",
        chain=lambda v, m: [
            f"Bharat QR declining {abs(v['bqr_mom']):.1f}% MoM — merchants are actively removing it, not seasonal dip",
            f"UPI QR at {fmt_num(v['upi'])} vs Bharat QR at {fmt_num(v['bqr'])} — gap structural and widening",
            "Any payments or lending product built on Bharat QR infrastructure faces accelerating merchant disengagement",
        ],
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "mom", "focusCard": "bharat_qr"},
        type="gap",
    ),

    Card(
        id="gap-atm-offsite-decline", group="infra", cut="total",
        reads={
            "off_mom": "groups.infra.total.metrics.atm_offsite.mom_pct",
            "off": "groups.infra.total.metrics.atm_offsite.latest",
            "on_mom": "groups.infra.total.metrics.atm_onsite.mom_pct",
        },
        fires_when=lambda v: v["off_mom"] is not None and v["off_mom"] < 0,
        title=lambda v, m:
            f"Gap: Offsite ATMs declining {v['off_mom']:.1f}% MoM — rural cash access contracting",
        body=lambda v, m:
            f"Offsite ATMs fell {abs(v['off_mom']):.1f}% MoM in {m} (now {fmt_num(v['off'])})"
            + (f", while onsite ATMs grew {v['on_mom']:+.1f}% MoM" if v["on_mom"] and v["on_mom"] > 0 else "")
            + f". Offsite ATMs serve rural and semi-urban populations where branch presence is limited — "
              f"their decline reduces physical cash access for underserved geographies.",
        implication=lambda v, m:
            "Offsite ATMs are standalone machines in villages, petrol pumps, small towns — "
            "placed away from bank branches specifically to serve rural areas. "
            "When these decline and digital payments haven't reached those areas yet, "
            "rural borrowers lose their easiest way to access cash for repayment. "
            "If you have loans in rural geographies, check whether ATM coverage in those areas is shrinking — "
            "it can make EMI collection harder.",
        chain=lambda v, m: [
            f"Offsite ATMs (standalone machines in rural/semi-urban areas away from branches) fell {abs(v['off_mom']):.1f}% MoM",
            "Rural borrowers without digital payment access rely on offsite ATMs as primary cash access point for loan repayment",
            "Declining offsite ATM coverage can impair EMI collection in areas where digital payment penetration is still low",
        ],
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "mom", "focusCard": "atm_offsite"},
        type="gap",
    ),

    Card(
        id="gap-pos-concentration", group="infra", cut="top_n",
        reads={
            "top5": "groups.infra.top_n.top5_share_pct",
            "leader_share": "groups.infra.top_n.banks.0.share_pct",
        },
        labels={"leader": "groups.infra.top_n.banks.0.name"},
        fires_when=lambda v: v["top5"] is not None and v["top5"] >= 85,
        title=lambda v, m:
            f"Gap: Top 5 banks hold {v['top5']:.1f}% of POS terminals — acquiring market is highly concentrated",
        body=lambda v, m:
            f"In {m}, the top 5 banks account for {v['top5']:.1f}% of all deployed POS terminals in India. "
            f"{_leader_line(v['leader'], v['leader_share'])}"
            f"All remaining banks combined share less than {100 - v['top5']:.1f}% of merchant acquiring infrastructure.",
        implication=lambda v, m:
            f"{v['top5']:.1f}% of all POS machines in India are owned by just 5 banks — "
            "and so is most of the merchant transaction data that comes with them. "
            "If you're building merchant credit products (loans to shopkeepers or small businesses) "
            "and don't have data partnerships with these top banks, you're working with an incomplete picture. "
            "Alternate sources — GST filings, UPI transaction data — can partially fill this gap.",
        chain=lambda v, m: [
            f"Top 5 banks own {v['top5']:.1f}% of POS terminals — merchant acquiring infrastructure highly concentrated",
            "Merchant transaction data (sales history needed for credit underwriting) controlled by the same 5 institutions",
            "Merchant credit underwriting without data partnerships with these banks requires alternates — GST filings, UPI feeds",
        ],
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "pos_terminals"},
        explore={"mode": "top_n", "topN": 5},
        type="gap",
    ),
]

GAP = {g.id: g for g in GAPS}


# The ordered list of card producers. A producer is either a function (not yet migrated) or a
# GapCard declaration; main() dispatches on which. Keeping them in ONE list preserves the order
# cards appear on the dashboard, so migrating a card cannot silently reshuffle the page.
RULES = [
    # CC
    cc_ecom_vs_pos,
    cc_atm_withdrawal_trend,
    STREAK["cc-cards-streak"],
    YOY["cc-cards-yoy"],
    cc_spend_yoy,
    cc_transaction_surge,
    cc_category_share_shift,
    cc_top_bank_concentration,
    GAP["gap-foreign-cc-decline"],
    # DC
    dc_atm_trend,
    dc_atm_share_structural,
    dc_pos_cash_decline,
    dc_ecom_share,
    STREAK["dc-cards-streak"],
    YOY["dc-cards-yoy"],
    dc_category_dominance,
    dc_top_bank,
    GAP["gap-dc-cash-dominance"],
    GAP["gap-dc-ecom-low"],
    # Infra
    infra_qr_per_pos,
    STREAK["infra-pos-streak"],
    YOY["infra-pos-yoy"],
    YOY["infra-upi-yoy"],
    infra_upi_vs_bharat_qr,
    infra_category_pos,
    infra_top_bank_pos,
    GAP["gap-bharat-qr-contraction"],
    GAP["gap-atm-offsite-decline"],
    GAP["gap-pos-concentration"],
]


def main():
    with open(SIGNALS_IN) as f:
        signals = json.load(f)

    month = signals["meta"]["latest_month"]
    print(f"Generating insights for {month}…")

    insights, broken = [], []
    for producer in RULES:
        try:
            result = produce(producer, signals, month)
            if result:
                insights.append(result)
                print(f"  ✓ {result['id']} [{result['group']} / {result['cut']}]")
        except Exception as e:
            # Reported AND fatal (see the exit at the end of main). A rule that raises means a
            # card silently disappears from the dashboard; printing it while exiting 0 meant the
            # gate stayed green and nobody found out until the page looked wrong.
            broken.append(f"{producer_name(producer)}: {e}")
            print(f"  ✗ {producer_name(producer)}: {e}")

    # Relational cards (rotation/divergence) — signals.db-sourced, deterministic
    # prose; never routed through the LLM representation layer below.
    for card in relational_cards(signals, month):
        insights.append(card)
        print(f"  ✓ {card['id']} [{card['group']} / {card['cut']}] (relational)")

    print(f"\n{len(insights)} insights generated.")

    # Single-entity dominance guard — deterministic, so it runs unconditionally and BEFORE the
    # LLM layer. A move that is one issuer's reporting artifact gets attributed here whether or
    # not an evaluation exists for this period.
    period = signals["meta"]["latest_period"]
    guarded = apply_dominance_guard(insights, period)
    if guarded:
        print(f"  dominance guard: {guarded} card(s) attributed to a single entity.")

    # LLM representation layer — override prose of anchored scalar insights with
    # the LLM evaluation narrative (deterministic selection/routing preserved).
    eval_signals, prompt_version = load_eval_signals(period)
    if eval_signals:
        n = apply_llm_representation(insights, eval_signals, prompt_version, period)
        print(f"  LLM representation applied to {n} scalar insight(s) "
              f"(eval {period}, prompt {prompt_version}); rest deterministic.")
    else:
        print(f"  ⚠ no LLM evaluation found for {period} — all insights deterministic. "
              f"Run: python3 analysis/core/generate_signal_history.py evaluate --pipeline atm_pos --period {period}")

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

    if broken:
        print(f"\n✗ {len(broken)} rule(s) failed — those cards are MISSING from the dashboard:")
        for b in broken:
            print(f"    {b}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
