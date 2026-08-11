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
                  so what a card cites is what it used. May instead be a callable taking the
                  resolved labels, for cards whose paths depend on what they find: "whichever
                  bank category gained the most share" is only a path once you know the name.
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
    reads: object           # {name: path}, or a callable given the resolved labels
    fires_when: object
    title: object
    body: object
    implication: object
    chain: object
    effect: object          # a dict, or a callable given the read values
    explore: dict | None = None
    type: str = "insight"
    metric: str | None = None
    streak: str | None = None
    # Display-only, non-numeric reads (a bank name). Deliberately separate from `reads`: these
    # are prose, and a card's cited sourceSignals must all be traceable numbers.
    labels: dict = field(default_factory=dict)

    def _base(self) -> str:
        return f"groups.{self.group}.total.metrics.{self.metric or self.streak}"

    def paths(self, labels: dict | None = None) -> dict:
        """Every numeric path this card reads, shorthand expanded.

        `labels` are resolved first so a card can point at a path it had to look up — the
        top-gaining category, say — rather than one fixed when the card was written.
        """
        reads = self.reads(labels or {}) if callable(self.reads) else dict(self.reads)
        if self.metric:
            base = self._base()
            return {
                "yoy": f"{base}.yoy_pct",
                "prior_yoy": f"{base}.yoy_prior_pct",
                "accel": f"{base}.yoy_accel_pp",
                "latest": f"{base}.latest",
            } | reads
        if self.streak:
            base = self._base()
            return {
                "latest": f"{base}.latest",
                "streak": f"{base}.streak_months",
                "qoq": f"{base}.qoq_pct",
            } | reads
        return reads

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
    # Labels first: they are what a dynamic path is built from.
    labels = {name: read_raw(s, path) for name, path in spec.label_paths().items()}
    paths = spec.paths(labels)
    v = {name: get_signal_value(s, path) for name, path in paths.items()}
    v.update(labels)
    if not spec.fires_when(v):
        return None
    # `effect` is usually a fixed dict, but a card that highlights a named bank only knows
    # which one after reading the data — so a callable is allowed too.
    effect = spec.effect(v) if callable(spec.effect) else spec.effect
    return insight(
        spec.id, spec.group, spec.cut, month,
        spec.title(v, month), spec.body(v, month),
        effect=effect, explore=spec.explore, type_=spec.type,
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


def _per(numerator, denominator) -> float:
    """One side per the other, rounded — "80 QR codes per terminal", "150x Bharat QR"."""
    if not (numerator and denominator):
        return 0.0
    return round(numerator / denominator)


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


# ══════════════════════════════════════════════════════════════════════════════
# INFRA RULES
# ══════════════════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════════════════
# GAP RULES  (type_="gap" — structural blind spots or underserved areas)
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# YoY TRAJECTORY RULES  (seasonally-clean — unlocked by the 2024 backfill)
# Year-on-year strips the seasonal swings (March FY-end, festive spikes) that
# dominate MoM. These rules report the YoY rate AND whether it is accelerating or
# decelerating vs the prior month's YoY rate — a trajectory MoM/streak can't show.
# ══════════════════════════════════════════════════════════════════════════════

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
# TOP-BANK CARDS — declared (see Card / render_card above)
# ══════════════════════════════════════════════════════════════════════════════
# Who leads a market and how concentrated it is. Two of these used to be a single function with
# a hidden fork: if any bank changed rank this month, emit the rank-change card, otherwise emit
# the concentration card — two different ids and two different chart routings from one producer.
# That fork is now two declarations whose conditions are mutually exclusive, which is the same
# behaviour said out loud. It also means the branch that is NOT firing this month is still
# visible in the file rather than buried in an else.

def _has_rank_change(v) -> bool:
    return bool(v.get("rank_changes"))


def _rc(v) -> dict:
    """The most notable rank change this month."""
    return (v.get("rank_changes") or [{}])[0]


TOP_BANK_CARDS = [
    Card(
        id="cc-top-bank-rank-change", group="cc", cut="top_n",
        reads={"top5": "groups.cc.top_n.top5_share_pct"},
        labels={"rank_changes": "groups.cc.top_n.rank_changes",
                "delta": "groups.cc.top_n.top5_share_delta_pp"},
        fires_when=_has_rank_change,
        title=lambda v, m:
            f"{_rc(v)['name']} moves "
            f"{'up' if _rc(v)['to_rank'] < _rc(v)['from_rank'] else 'down'} "
            f"to #{_rc(v)['to_rank']} in CC cards",
        body=lambda v, m:
            f"{_rc(v)['name']} moved from #{_rc(v)['from_rank']} to #{_rc(v)['to_rank']} in credit cards outstanding "
            f"in {m}. "
            + (f"Top 5 banks collectively hold {v['top5']:.1f}% of total CC cards"
               + (f" ({sign(v['delta'])}pp vs prior month)" if v["delta"] else "") + "."
               if v["top5"] else ""),
        implication=lambda v, m:
            "A rank change among the top CC issuers means one bank is either issuing cards faster "
            "or closing inactive accounts more aggressively. For anyone watching the credit card market, "
            "it's worth understanding the reason — growing rank means gaining customers, falling rank "
            "could mean pruning a portfolio or losing share to a competitor.",
        chain=lambda v, m: [
            f"{_rc(v)['name']} moved from #{_rc(v)['from_rank']} to #{_rc(v)['to_rank']} in CC cards outstanding",
            ("Rising rank means faster card issuance or competitor attrition in that bank"
             if _rc(v)["to_rank"] < _rc(v)["from_rank"] else
             "Falling rank suggests portfolio pruning or losing acquisition pace to competitors"),
            "Track whether the move reflects new card issuance (gaining customers) or balance attrition (losing them)",
        ],
        effect=lambda v: {"highlight": [_rc(v)["name"], "Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "credit_cards"},
        explore={"mode": "top_n", "topN": 10},
    ),

    Card(
        id="cc-top5-concentration", group="cc", cut="top_n",
        reads={
            "top5": "groups.cc.top_n.top5_share_pct",
            "delta": "groups.cc.top_n.top5_share_delta_pp",
            "leader_share": "groups.cc.top_n.banks.0.share_pct",
            "leader_mom": "groups.cc.top_n.banks.0.mom_pct",
        },
        labels={"rank_changes": "groups.cc.top_n.rank_changes",
                "leader": "groups.cc.top_n.banks.0.name"},
        # The other half of the old fork: only when nothing changed rank.
        fires_when=lambda v: not _has_rank_change(v) and v["top5"] is not None and v["leader"],
        title=lambda v, m:
            f"Top 5 banks hold {v['top5']:.1f}% of CC cards — {v['leader']} leads at {v['leader_share']:.1f}%",
        body=lambda v, m:
            f"In {m}, the top 5 banks account for {v['top5']:.1f}% of total credit cards outstanding"
            + (f" ({sign(v['delta'])}pp vs prior month)" if v["delta"] else "") + ". "
            + f"{v['leader']} leads with {v['leader_share']:.1f}% share ({v['leader_mom']:+.1f}% MoM).",
        # The share used to be hardcoded as "74%" in this sentence while the number beside it was
        # computed — frozen prose that would have gone stale the moment concentration moved.
        implication=lambda v, m:
            f"{v['top5']:.1f}% of all credit cards in India are with just 5 banks. "
            "In practice, this means the national credit card data from RBI tells you largely "
            "what HDFC, SBI, ICICI, Axis, and Kotak are doing — not the market as a whole. "
            "If your strategy relies on industry-level CC data, keep this concentration in mind.",
        chain=lambda v, m: [
            f"Top 5 banks hold {v['top5']:.1f}% of all CC cards — {v['leader']} alone accounts for {v['leader_share']:.1f}%",
            "RBI aggregate CC data is effectively proxied by these 5 institutions — smaller banks are statistically marginal",
            "Industry-level CC strategy analysis must account for this concentration — it reflects large-bank dynamics, not the full market",
        ],
        effect=lambda v: {"highlight": [v["leader"]], "tab": "distribution", "distMode": "pct", "focusCard": "credit_cards"},
        explore={"mode": "top_n", "topN": 10},
    ),

    Card(
        id="dc-top-bank-rank-change", group="dc", cut="top_n",
        reads={"top5": "groups.dc.top_n.top5_share_pct"},
        labels={"rank_changes": "groups.dc.top_n.rank_changes",
                "delta": "groups.dc.top_n.top5_share_delta_pp"},
        fires_when=_has_rank_change,
        title=lambda v, m:
            f"{_rc(v)['name']} moves to #{_rc(v)['to_rank']} in debit cards (from #{_rc(v)['from_rank']})",
        body=lambda v, m:
            f"{_rc(v)['name']} shifted from #{_rc(v)['from_rank']} to #{_rc(v)['to_rank']} in {m}. "
            + (f"Top 5 banks: {v['top5']:.1f}% of total DC cards"
               + (f" ({sign(v['delta'])}pp)" if v["delta"] else "") + "."
               if v["top5"] else ""),
        implication=lambda v, m:
            "Rank changes in debit cards usually mean one of two things: a PSB is closing "
            "dormant Jan Dhan accounts (drops in rank), or a private bank is pushing into "
            "smaller towns and cities (rises in rank). "
            "The bank moving up is reaching new customers — which often translates to more "
            "credit origination potential over the next few quarters.",
        chain=lambda v, m: [
            f"{_rc(v)['name']} shifted from #{_rc(v)['from_rank']} to #{_rc(v)['to_rank']} in debit cards",
            "PSB rank drops often reflect Jan Dhan dormant account closures; private bank rises reflect geographic expansion",
            "Bank moving up is reaching new customers — leading indicator of future credit origination volume in that segment",
        ],
        effect=lambda v: {"highlight": [_rc(v)["name"], "Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "debit_cards"},
        explore={"mode": "top_n", "topN": 10},
    ),

    Card(
        id="dc-top-bank-leader", group="dc", cut="top_n",
        reads={
            "top5": "groups.dc.top_n.top5_share_pct",
            "delta": "groups.dc.top_n.top5_share_delta_pp",
            "leader_share": "groups.dc.top_n.banks.0.share_pct",
            "leader_mom": "groups.dc.top_n.banks.0.mom_pct",
        },
        labels={"rank_changes": "groups.dc.top_n.rank_changes",
                "leader": "groups.dc.top_n.banks.0.name"},
        fires_when=lambda v: not _has_rank_change(v) and v["leader"] and v["top5"] is not None,
        title=lambda v, m: f"{v['leader']} leads DC cards at {v['leader_share']:.1f}%",
        body=lambda v, m:
            f"{v['leader']} holds {v['leader_share']:.1f}% of total debit cards in {m} "
            f"({v['leader_mom']:+.1f}% MoM). "
            f"Top 5 banks account for {v['top5']:.1f}%"
            + (f" ({sign(v['delta'])}pp vs prior month)" if v["delta"] else "") + ".",
        implication=lambda v, m:
            f"Top 5 banks hold {v['top5']:.1f}% of debit cards. If you're using debit transaction data "
            "for credit underwriting (assessing someone's spending behaviour before giving them a loan), "
            "the quality of that data depends heavily on whether these top banks are sharing data with you. "
            "Without coverage from at least 2-3 of them, you're missing nearly half the market.",
        chain=lambda v, m: [
            f"Top 5 banks hold {v['top5']:.1f}% of debit cards — {v['leader']} alone accounts for {v['leader_share']:.1f}%",
            "Debit transaction data coverage for underwriting depends on data-sharing with these top institutions",
            "Without data from 2-3 of these banks, nearly half the debit market is invisible for credit decisions",
        ],
        effect=lambda v: {"highlight": [v["leader"]], "tab": "distribution", "distMode": "pct", "focusCard": "debit_cards"},
        explore={"mode": "top_n", "topN": 10},
    ),

    Card(
        id="infra-top-bank-pos", group="infra", cut="top_n",
        reads={
            "top5": "groups.infra.top_n.top5_share_pct",
            "leader_share": "groups.infra.top_n.banks.0.share_pct",
            "leader_mom": "groups.infra.top_n.banks.0.mom_pct",
        },
        labels={"rank_changes": "groups.infra.top_n.rank_changes",
                "leader": "groups.infra.top_n.banks.0.name",
                "delta": "groups.infra.top_n.top5_share_delta_pp",
                "leader_value": "groups.infra.top_n.banks.0.value"},
        # Unlike the card pair above, this one always shows the leader and folds any rank change
        # into a trailing sentence rather than becoming a different card.
        fires_when=lambda v: bool(v["leader"]),
        title=lambda v, m:
            f"{v['leader']} leads POS terminal deployment at {v['leader_share']:.1f}% market share",
        body=lambda v, m:
            f"{v['leader']} has deployed {fmt_num(v['leader_value'])} POS terminals in {m}, "
            f"accounting for {v['leader_share']:.1f}% of total ({v['leader_mom']:+.1f}% MoM). "
            + (f"Top 5 banks hold {v['top5']:.1f}% of all POS terminals"
               + (f" ({sign(v['delta'])}pp vs prior month)" if v["delta"] else "") + "."
               if v["top5"] else "")
            + (f" Notable: {_rc(v)['name']} moved from #{_rc(v)['from_rank']} to #{_rc(v)['to_rank']}."
               if _has_rank_change(v) else ""),
        implication=lambda v, m:
            f"5 banks own {(v['top5'] or 0):.1f}% of all POS machines in India. "
            "That also means merchant sales data — what shopkeepers sell, how much, how often — "
            "sits largely with those same 5 banks. "
            "If you want to lend to merchants and need their sales history to decide how much credit to give, "
            "you either need a data partnership with one of these banks or an alternate source "
            "like GST returns or UPI transaction feeds.",
        chain=lambda v, m: [
            f"Top 5 banks own {(v['top5'] or 0):.1f}% of POS terminals — merchant acquiring infrastructure is highly concentrated",
            "Merchant transaction data (sales history for credit underwriting) sits with the same institutions",
            "Merchant credit without data partnerships with these banks requires alternate sources — GST returns, UPI transaction feeds",
        ],
        effect=lambda v: {"highlight": [v["leader"]], "tab": "distribution", "distMode": "pct", "focusCard": "pos_terminals"},
        explore={"mode": "top_n", "topN": 10},
    ),
]

TOP_BANK = {c.id: c for c in TOP_BANK_CARDS}


# ══════════════════════════════════════════════════════════════════════════════
# CATEGORY-SHARE CARDS — declared (see Card / render_card above)
# ══════════════════════════════════════════════════════════════════════════════
# Which kind of bank — public sector, private, foreign, small finance — is gaining ground. These
# are the cards whose paths are not known when the card is written: "the category that gained the
# most share" is a name you have to look up first. Hence `reads` as a callable over the labels.

def _cat(group: str, name: str, field: str) -> str:
    return f"groups.{group}.by_type.categories.{name}.{field}"


CATEGORY_CARDS = [
    Card(
        id="cc-category-share-shift", group="cc", cut="by_type",
        labels={"gainer": "groups.cc.by_type.top_gainer", "loser": "groups.cc.by_type.top_loser"},
        reads=lambda lab: {
            "g_share": _cat("cc", lab.get("gainer"), "share_pct"),
            "g_delta": _cat("cc", lab.get("gainer"), "share_delta_pp"),
            "l_share": _cat("cc", lab.get("loser"), "share_pct"),
            "l_delta": _cat("cc", lab.get("loser"), "share_delta_pp"),
        },
        # Both movers must exist, and at least one must have moved enough to be worth saying.
        fires_when=lambda v: bool(v["gainer"] and v["loser"]) and not (
            abs(v["g_delta"] or 0) < 0.05 and abs(v["l_delta"] or 0) < 0.05),
        title=lambda v, m: f"{v['gainer']} banks gained CC card share in {m} (+{(v['g_delta'] or 0):.1f}pp)",
        body=lambda v, m:
            f"{v['gainer']} banks hold {(v['g_share'] or 0):.1f}% of total credit cards outstanding in {m} "
            f"({sign(v['g_delta'] or 0)}pp vs prior month). "
            f"{v['loser']} banks lost the most share at {sign(v['l_delta'] or 0)}pp, now at {(v['l_share'] or 0):.1f}%. "
            + ("SFB growth in credit cards reflects increased fintech partnerships." if v["gainer"] == "SFB" else "")
            + ("Private bank CC dominance continues to compound." if v["gainer"] == "Private" else ""),
        implication=lambda v, m:
            f"{v['gainer']} banks picking up credit card share — even by {(v['g_delta'] or 0):.1f}pp — signals a change in who's acquiring customers. "
            + ("SFBs (Small Finance Banks — banks that focus on underserved segments like AU or Equitas) growing in credit cards usually means fintech partnerships or co-branded products are kicking in."
               if v["gainer"] == "SFB" else "")
            + ("Private banks compounding their lead means the premium card market is further consolidating."
               if v["gainer"] == "Private" else "")
            + "For anyone benchmarking credit card portfolio quality, knowing which bank type is gaining share matters — their customer profiles and risk behaviour can be very different.",
        chain=lambda v, m: [
            f"{v['gainer']} banks gained {(v['g_delta'] or 0):.1f}pp CC share — {v['loser']} banks lost {abs(v['l_delta'] or 0):.1f}pp",
            ("SFB growth signals fintech partnerships or co-branded card activity in underserved segments"
             if v["gainer"] == "SFB" else
             "Private bank lead compounding as premium card market consolidates further"),
            "Customer risk profiles differ significantly across bank types — portfolio benchmarking must account for this mix shift",
        ],
        effect=lambda v: {"highlight": [v["gainer"], "Total"], "tab": "distribution",
                          "distMode": "pct", "focusCard": "credit_cards"},
        explore={"mode": "by_type"},
    ),

    Card(
        id="dc-psb-dominance", group="dc", cut="by_type",
        labels={"gainer": "groups.dc.by_type.top_gainer"},
        reads=lambda lab: {
            "psb_share": _cat("dc", "PSB", "share_pct"),
            "psb_delta": _cat("dc", "PSB", "share_delta_pp"),
            "priv_share": _cat("dc", "Private", "share_pct"),
            "gainer_delta": _cat("dc", lab.get("gainer"), "share_delta_pp"),
        },
        fires_when=lambda v: v["psb_share"] is not None,
        title=lambda v, m:
            f"PSB banks hold {v['psb_share']:.1f}% of debit cards — {v['gainer']} gaining share in {m}",
        body=lambda v, m:
            f"Public sector banks account for {v['psb_share']:.1f}% of total debit cards outstanding in {m}"
            + (f" ({sign(v['psb_delta'])}pp vs prior month)" if v["psb_delta"] else "") + ". "
            + f"Private banks hold {v['priv_share']:.1f}%. "
            + (f"{v['gainer']} banks are the fastest-growing category ({sign(v['gainer_delta'] or 0)}pp share gain)."
               if v["gainer"] else ""),
        implication=lambda v, m:
            f"PSBs (government-owned banks like SBI, PNB, Bank of Baroda) hold {v['psb_share']:.1f}% of debit cards, "
            "largely because of Jan Dhan — the government scheme that opened basic bank accounts "
            "for millions of low-income households. Many of these accounts have little activity. "
            "If you're using debit transaction data for credit assessment, PSB debit data needs to be "
            "treated very differently from, say, HDFC or Kotak debit customers.",
        chain=lambda v, m: [
            f"PSBs hold {v['psb_share']:.1f}% of debit cards — primarily through Jan Dhan scheme linkage, not active acquisition",
            "Jan Dhan portfolios skew toward low-income, low-activity accounts with thin or no transaction histories",
            "PSB and private bank debit data require separate calibration for transaction-based credit underwriting",
        ],
        effect=lambda v: {
            "highlight": ["PSB", v["gainer"], "Total"] if v["gainer"] and v["gainer"] != "PSB" else ["PSB", "Total"],
            "tab": "distribution", "distMode": "pct", "focusCard": "debit_cards",
        },
        explore={"mode": "by_type"},
    ),

    Card(
        id="infra-category-pos-share", group="infra", cut="by_type",
        labels={"gainer": "groups.infra.by_type.top_gainer", "loser": "groups.infra.by_type.top_loser"},
        reads=lambda lab: {
            "g_share": _cat("infra", lab.get("gainer"), "share_pct"),
            "g_delta": _cat("infra", lab.get("gainer"), "share_delta_pp"),
        },
        fires_when=lambda v: bool(v["gainer"]) and abs(v["g_delta"] or 0) >= 0.2,
        title=lambda v, m:
            f"{v['gainer']} banks fastest-growing in POS terminal deployment in {m} "
            f"({sign(v['g_delta'] or 0)}pp share)",
        body=lambda v, m:
            f"{v['gainer']} banks hold {(v['g_share'] or 0):.1f}% of total POS terminals in {m}, "
            f"gaining {sign(v['g_delta'] or 0)}pp vs prior month. "
            + (f"{v['loser']} banks lost the most share." if v["loser"] and v["loser"] != v["gainer"] else ""),
        implication=lambda v, m:
            f"{v['gainer']} banks gaining POS share means they're building more merchant relationships in that segment. "
            "Banks that own the POS network also own the merchant's transaction data — daily sales, "
            "busy periods, average ticket size. "
            "That data is the foundation for merchant lending (small business loans based on sales history). "
            "Watch which bank type is expanding POS — they're positioning for merchant credit.",
        chain=lambda v, m: [
            f"{v['gainer']} banks gained {(v['g_delta'] or 0):.1f}pp POS share — building more merchant acquiring relationships",
            "Banks owning the POS network own the merchant's transaction data (daily sales, ticket size, frequency)",
            "POS share expansion is a leading indicator of positioning for merchant credit (working capital, cash advances)",
        ],
        effect=lambda v: {"highlight": [v["gainer"], "Total"], "tab": "distribution",
                          "distMode": "pct", "focusCard": "pos_terminals"},
        explore={"mode": "by_type"},
    ),
]

CATEGORY = {c.id: c for c in CATEGORY_CARDS}


# ══════════════════════════════════════════════════════════════════════════════
# TWO-METRIC CARDS — declared (see Card / render_card above)
# ══════════════════════════════════════════════════════════════════════════════
# Cards that compare two things: QR codes against card terminals, online spend against in-store.
# The comparison is the point, so both sides are read explicitly. No `pair=` shorthand: two of
# these read the metrics tree and two read the cross tree with different field names, so a
# shorthand would serve two cards and mislead about the third. `metric=` and `streak=` earned
# their keep across four and three cards; this would not.

TWO_METRIC_CARDS = [
    Card(
        id="infra-qr-per-pos", group="infra", cut="total",
        reads={
            "upi": "groups.infra.total.metrics.upi_qr.latest",
            "pos": "groups.infra.total.metrics.pos_terminals.latest",
            "upi_prior": "groups.infra.total.metrics.upi_qr.prior",
            "pos_prior": "groups.infra.total.metrics.pos_terminals.prior",
            "upi_mom": "groups.infra.total.metrics.upi_qr.mom_pct",
            "pos_mom": "groups.infra.total.metrics.pos_terminals.mom_pct",
        },
        fires_when=lambda v: v["upi"] is not None and v["pos"],
        title=lambda v, m: f"India now has {_per(v['upi'], v['pos']):.0f} UPI QR codes per POS terminal",
        body=lambda v, m:
            f"As of {m}, there are {_per(v['upi'], v['pos']):.0f} UPI QR codes ({fmt_num(v['upi'])}) "
            f"for every POS terminal ({fmt_num(v['pos'])}). "
            + (f"This ratio was {_per(v['upi_prior'], v['pos_prior']):.0f} in the prior month. "
               if v["upi_prior"] and v["pos_prior"] else "")
            + (f"UPI QR grew {v['upi_mom']:+.1f}% MoM vs POS terminals at {v['pos_mom']:+.1f}% MoM — "
               f"digital acceptance infrastructure is "
               f"{'outpacing' if v['upi_mom'] > v['pos_mom'] else 'growing in line with'} hardware deployment."
               if v["upi_mom"] is not None and v["pos_mom"] is not None else ""),
        implication=lambda v, m:
            f"There are {_per(v['upi'], v['pos']):.0f} UPI QR codes for every POS (card swipe) machine in India. "
            "This means the typical small merchant — kirana store, auto driver, vegetable vendor — "
            "accepts payments through a QR code on their phone, not a card machine. "
            "Any credit product designed for small merchants (small business loans, BNPL for vendors) "
            "needs to work over UPI QR, not just over POS terminals.",
        chain=lambda v, m: [
            f"{_per(v['upi'], v['pos']):.0f} UPI QR codes per POS terminal — QR acceptance vastly outnumbers hardware deployment",
            "Typical small merchant (kirana, auto, vendor) accepts via QR only — no POS terminal",
            "Credit products for small merchants (BNPL, business loans) must work over UPI QR to reach this majority",
        ],
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "upi_qr"},
        explore={"mode": "by_type"},
    ),

    Card(
        id="infra-upi-vs-bharat-qr", group="infra", cut="total",
        reads={
            "upi": "groups.infra.total.metrics.upi_qr.latest",
            "bqr": "groups.infra.total.metrics.bharat_qr.latest",
            "upi_mom": "groups.infra.total.metrics.upi_qr.mom_pct",
            "bqr_mom": "groups.infra.total.metrics.bharat_qr.mom_pct",
        },
        fires_when=lambda v: bool(v["upi"]) and v["bqr"] is not None and v["bqr"] > 0,
        title=lambda v, m:
            f"UPI QR codes are {_per(v['upi'], v['bqr']):.0f}x Bharat QR in scale — "
            f"{fmt_num(v['upi'])} vs {fmt_num(v['bqr'])}",
        body=lambda v, m:
            f"As of {m}, there are {fmt_num(v['upi'])} UPI QR codes deployed vs {fmt_num(v['bqr'])} Bharat QR codes — "
            f"a {_per(v['upi'], v['bqr']):.0f}x gap. "
            + (f"UPI QR grew {v['upi_mom']:+.1f}% MoM vs Bharat QR at {v['bqr_mom']:+.1f}% MoM. "
               if v["upi_mom"] is not None and v["bqr_mom"] is not None else "")
            + "UPI has decisively won the QR standard battle in India.",
        implication=lambda v, m:
            f"Bharat QR was an earlier QR code standard that lost out to UPI QR — which is now "
            f"{_per(v['upi'], v['bqr']):.0f} times bigger. "
            "Building any credit product (credit on UPI, BNPL) on Bharat QR today would be like "
            "building on a platform that merchants have already abandoned. "
            "UPI QR is the only QR standard worth designing for.",
        chain=lambda v, m: [
            f"UPI QR at {fmt_num(v['upi'])} vs Bharat QR at {fmt_num(v['bqr'])} — a {_per(v['upi'], v['bqr']):.0f}x gap",
            "Bharat QR was an earlier standard; merchants have consolidated on UPI QR as the accepted norm",
            "Building payments or lending infrastructure on Bharat QR rails is operationally unviable at any meaningful merchant scale",
        ],
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "upi_qr"},
    ),

    Card(
        id="cc-ecom-vs-pos-share", group="cc", cut="total",
        reads={
            "ecom": "groups.cc.total.cross.cc_ecom_txn_vol.share_pct",
            "pos": "groups.cc.total.cross.cc_pos_txn_vol.share_pct",
            "ecom_prior": "groups.cc.total.cross.cc_ecom_txn_vol.prior_share_pct",
            "delta": "groups.cc.total.cross.cc_ecom_txn_vol.share_delta_pp",
        },
        # Either ecommerce has taken the majority, or it moved enough to be closing the gap.
        fires_when=lambda v: v["ecom"] is not None and v["pos"] is not None and (
            v["ecom"] >= 50 or (v["delta"] is not None and v["delta"] > 0.5)),
        title=lambda v, m:
            (f"CC ecommerce exceeds POS for the first time"
             if v["ecom"] >= 50 and v["ecom_prior"] and v["ecom_prior"] < 50 else
             f"CC ecommerce holds above POS at {v['ecom']:.1f}% of total CC volume" if v["ecom"] >= 50 else
             f"CC ecommerce closing in on POS — now {v['ecom']:.1f}% of total volume"),
        body=lambda v, m:
            (f"In {m}, ecommerce accounted for {v['ecom']:.1f}%"
             + (f" ({sign(v['delta'])}pp vs prior month)" if v["delta"] is not None else "")
             + f" of total CC transaction volume vs POS at {v['pos']:.1f}%. "
             + "This structural shift — digital-first over in-store — has persisted for "
             + ("multiple months." if v["ecom_prior"] and v["ecom_prior"] >= 50
                else "the first time in this data series.")
             ) if v["ecom"] >= 50 else
            (f"In {m}, CC ecommerce is {v['ecom']:.1f}% of total CC transaction volume vs POS at {v['pos']:.1f}%. "
             f"Ecom gained {sign(v['delta'])}pp vs prior month. The gap to POS is {v['pos'] - v['ecom']:.1f}pp."),
        implication=lambda v, m:
            "More than half of credit card spending is now online — not at physical stores. "
            "Online transactions (called CNP, or card-not-present, because the card isn't physically swiped) carry higher fraud risk. "
            "If your fraud detection was built around in-store spending patterns, it needs to be updated for an online-first customer base.",
        chain=lambda v, m: [
            f"CC ecommerce at {v['ecom']:.1f}% of volume — majority of CC spend is now online, not at physical stores",
            "Online transactions (card-not-present / CNP) carry higher fraud risk since the card is never physically verified",
            "Fraud detection built for in-store patterns needs recalibration for an online-first customer base",
        ],
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "cc_ecom"},
        explore={"mode": "by_type"},
    ),

    Card(
        id="cc-spend-yoy", group="cc", cut="total",
        reads={
            "ecom_yoy": "groups.cc.total.metrics.cc_ecom_txn_vol.yoy_pct",
            "pos_yoy": "groups.cc.total.metrics.cc_pos_txn_vol.yoy_pct",
        },
        fires_when=lambda v: v["ecom_yoy"] is not None and v["pos_yoy"] is not None and (
            abs(v["ecom_yoy"]) >= 5 or abs(v["pos_yoy"]) >= 5),
        title=lambda v, m:
            f"CC spend YoY — ecommerce {v['ecom_yoy']:.1f}% vs in-store POS {v['pos_yoy']:.1f}%",
        body=lambda v, m:
            f"On a year-on-year basis, credit card ecommerce transaction volume grew {v['ecom_yoy']:.1f}% "
            f"and in-store POS volume grew {v['pos_yoy']:.1f}% as of {m}. "
            f"Year-on-year removes the heavy seasonality in the monthly numbers — "
            + ("online is outpacing in-store" if v["ecom_yoy"] > v["pos_yoy"] else "in-store is outpacing online")
            + " on a clean comparison.",
        implication=lambda v, m:
            "Credit card spend is growing across both channels year-on-year "
            + ("(ecom faster). " if v["ecom_yoy"] > v["pos_yoy"] else "(POS faster). ")
            + "For credit-risk teams this matters: a spend mix tilting online means more "
            "card-not-present volume, where fraud and dispute rates run higher — provisioning "
            "and fraud models should track the channel mix, not just the headline spend growth.",
        chain=lambda v, m: [
            f"CC ecommerce volume up {v['ecom_yoy']:.1f}% YoY vs POS up {v['pos_yoy']:.1f}% YoY — both growing, seasonally clean",
            ("Online (CNP) is the faster-growing channel" if v["ecom_yoy"] > v["pos_yoy"]
             else "In-store POS is the faster-growing channel") + " on a year-on-year basis",
            "Channel mix shift changes the fraud and dispute profile — risk models must track mix, not just total spend",
        ],
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "yoy", "focusCard": "cc_ecom"},
        explore={"mode": "by_type"},
    ),
]

TWO_METRIC = {c.id: c for c in TWO_METRIC_CARDS}


# ══════════════════════════════════════════════════════════════════════════════
# CHANNEL-SHARE CARDS — declared (see Card / render_card above)
# ══════════════════════════════════════════════════════════════════════════════
# How a card base splits its volume between channels — ATM cash, in-store, online — and which way
# that split is moving. The recurring reading: cash leaves no record, digital does, and a debit
# holder moving from one to the other is becoming underwritable.

def _cross(group: str, metric: str, field: str) -> str:
    return f"groups.{group}.total.cross.{metric}.{field}"


CHANNEL_CARDS = [
    Card(
        id="dc-ecom-share", group="dc", cut="total",
        reads={
            "ecom": _cross("dc", "dc_ecom_txn_vol", "share_pct"),
            "delta": _cross("dc", "dc_ecom_txn_vol", "share_delta_pp"),
            "atm": _cross("dc", "dc_atm_withdrawal_vol", "share_pct"),
        },
        fires_when=lambda v: v["ecom"] is not None and not (
            v["ecom"] < 2 and (v["delta"] is None or abs(v["delta"]) < 0.3)),
        title=lambda v, m: f"DC ecommerce is {v['ecom']:.1f}% of total DC transaction volume in {m}",
        body=lambda v, m:
            f"Debit card ecommerce accounted for {v['ecom']:.1f}% of total DC transaction volume in {m}"
            + (f" ({sign(v['delta'])}pp vs prior month)" if v["delta"] else "") + ". "
            + (f"ATM cash still dominates at {v['atm']:.1f}%. " if v["atm"] else "")
            + "The structural shift away from cash toward digital payments is ongoing.",
        implication=lambda v, m:
            f"Only {v['ecom']:.1f}% of debit card spending is online, but that group is valuable. "
            "These are debit-only customers who already shop digitally — which means their spending "
            "leaves a traceable record. For cross-selling a first credit card or personal loan, "
            "debit customers with online spending history are much easier to assess than pure ATM-cash users.",
        chain=lambda v, m: [
            f"DC ecommerce is {v['ecom']:.1f}% of DC volume — small but digitally traceable subgroup within a cash-dominant base",
            "Online debit customers leave structured purchase records; ATM-cash users leave none",
            "Digital-active debit customers are higher-value cross-sell targets for first credit products — traceable history enables underwriting",
        ],
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "dc_ecom"},
        explore={"mode": "by_type"},
    ),

    Card(
        id="dc-atm-share-structural", group="dc", cut="total",
        reads={
            "atm": _cross("dc", "dc_atm_withdrawal_vol", "share_pct"),
            "atm_delta": _cross("dc", "dc_atm_withdrawal_vol", "share_delta_pp"),
            "ecom": _cross("dc", "dc_ecom_txn_vol", "share_pct"),
            "ecom_delta": _cross("dc", "dc_ecom_txn_vol", "share_delta_pp"),
        },
        # Only when cash is actually losing ground — a rising ATM share is a different story.
        fires_when=lambda v: v["atm"] is not None and v["atm_delta"] is not None and v["atm_delta"] < 0,
        title=lambda v, m:
            f"DC ATM cash losing share — {v['atm']:.1f}% of DC volume ({sign(v['atm_delta'])}pp) as digital grows",
        body=lambda v, m:
            f"Debit card ATM withdrawals account for {v['atm']:.1f}% of total DC transaction volume in {m} "
            f"({sign(v['atm_delta'])}pp vs prior month). "
            + (f"DC ecommerce has grown to {v['ecom']:.1f}% ({sign(v['ecom_delta'])}pp). "
               if v["ecom"] and v["ecom_delta"] else "")
            + "The structural shift from cash to digital payments is underway in the debit segment.",
        implication=lambda v, m:
            f"Debit card ATM cash is at {v['atm']:.1f}% and falling — which means a growing group of "
            "debit card holders is switching to digital payments (online or at stores). "
            "Those customers start leaving a spending history that lenders can actually use. "
            "Debit customers who are moving to digital are among the best targets for a first credit card "
            "or personal loan — they have a track record, just not a credit one yet.",
        chain=lambda v, m: [
            f"DC ATM cash share fell {abs(v['atm_delta']):.1f}pp to {v['atm']:.1f}% — customers shifting away from cash",
            "Digital debit transactions (POS, ecommerce) create structured spending records; cash leaves none",
            "Debit customers moving to digital build a usable credit history — prime candidates for first credit origination",
        ],
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "absolute", "focusCard": "dc_atm"},
    ),

    Card(
        id="dc-pos-cash-decline", group="dc", cut="total",
        # NOT the `streak=` shorthand, though it gates on a streak. That shorthand also reads a
        # level and a QoQ move, and this card uses neither — taking it would have made the card
        # cite two numbers it never looks at. A shorthand that has to be stretched is the wrong
        # shorthand for the card.
        reads={
            "mom": "groups.dc.total.metrics.dc_pos_withdrawal_vol.mom_pct",
            "streak": "groups.dc.total.metrics.dc_pos_withdrawal_vol.streak_months",
        },
        labels={"streak_dir": "groups.dc.total.metrics.dc_pos_withdrawal_vol.streak_dir"},
        fires_when=lambda v: v["streak_dir"] == "down" and (v["streak"] or 0) >= 2 and v["mom"] is not None,
        title=lambda v, m:
            f"DC POS cash withdrawals: {streak_label(int(v['streak']), 'down')} ({v['mom']:.1f}% MoM)",
        body=lambda v, m:
            f"Debit card POS cash-back withdrawal volume fell {abs(v['mom']):.1f}% MoM in {m}, "
            f"the {streak_label(int(v['streak']), 'down')}. "
            f"This is a separate channel from ATM cash — POS cash-back usage is contracting "
            f"while digital POS payments continue to grow.",
        implication=lambda v, m:
            "Some merchants used to let customers withdraw cash at their POS machine — called cash-back at POS. "
            "This is declining. That's actually good for data quality: POS transaction records now reflect "
            "real purchases, not cash withdrawals disguised as purchases. "
            "Better purchase data means more accurate signals when assessing credit for small businesses or retail customers.",
        chain=lambda v, m: [
            f"DC POS cash-back withdrawals fell {abs(v['mom']):.1f}% MoM for {int(v['streak'])} months — merchants reducing cash-out via POS",
            "POS records now reflect real purchases rather than cash access events disguised as transactions",
            "Cleaner purchase data improves signal quality for credit underwriting of MSME and retail customers",
        ],
        effect={"highlight": ["Total"], "tab": "trend", "trendMode": "mom", "focusCard": "dc_pos_wd"},
    ),
]

CHANNEL = {c.id: c for c in CHANNEL_CARDS}


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
    TWO_METRIC["cc-ecom-vs-pos-share"],
    cc_atm_withdrawal_trend,
    STREAK["cc-cards-streak"],
    YOY["cc-cards-yoy"],
    TWO_METRIC["cc-spend-yoy"],
    cc_transaction_surge,
    CATEGORY["cc-category-share-shift"],
    TOP_BANK["cc-top-bank-rank-change"],
    TOP_BANK["cc-top5-concentration"],
    GAP["gap-foreign-cc-decline"],
    # DC
    dc_atm_trend,
    CHANNEL["dc-atm-share-structural"],
    CHANNEL["dc-pos-cash-decline"],
    CHANNEL["dc-ecom-share"],
    STREAK["dc-cards-streak"],
    YOY["dc-cards-yoy"],
    CATEGORY["dc-psb-dominance"],
    TOP_BANK["dc-top-bank-rank-change"],
    TOP_BANK["dc-top-bank-leader"],
    GAP["gap-dc-cash-dominance"],
    GAP["gap-dc-ecom-low"],
    # Infra
    TWO_METRIC["infra-qr-per-pos"],
    STREAK["infra-pos-streak"],
    YOY["infra-pos-yoy"],
    YOY["infra-upi-yoy"],
    TWO_METRIC["infra-upi-vs-bharat-qr"],
    CATEGORY["infra-category-pos-share"],
    TOP_BANK["infra-top-bank-pos"],
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
