"""
LLM evaluation engine for Layer 1 signals.

Reads computed signal values from signals.db, builds domain-grouped context
payloads, calls Claude API (temperature=0), caches results by content hash,
and writes structured evaluations to signals/evaluations/{pipeline}/{period}.json.

Determinism guarantees:
  - temperature=0: greedy decoding → same prompt → same output
  - content hash cache: same data → cache hit → zero API cost on re-runs
  - prompt_version: changing the prompt template invalidates the cache
  - structured output: JSON schema enforced — no free-form prose

Usage:
  from analysis.signals.evaluate import run_evaluate
  result = run_evaluate(pipeline, period, conn, registry)
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

REPO        = Path(__file__).resolve().parent.parent.parent
PROMPTS_DIR = Path(__file__).parent / "prompts"
EVALS_DIR   = Path(__file__).parent / "evaluations"

MODEL          = "claude-3-5-haiku-20241022"
PROMPT_VERSION = "1.0"

# ── Pipeline context blocks ───────────────────────────────────────────────────

PIPELINE_CONTEXT: dict[str, str] = {
    "sibc": (
        "Source: RBI Sectoral and Industrial Bank Credit (SIBC) report. "
        "Covers bank credit deployed by Indian commercial banks to agriculture, "
        "industry, services, and retail borrowers. "
        "Periods are bi-monthly fortnights; growth rates are year-on-year. "
        "Values in Lakh Crore (₹L Cr) unless stated otherwise."
    ),
    "atm_pos": (
        "Source: RBI ATM/POS/Card Statistics. "
        "Covers card infrastructure (ATMs, POS terminals, UPI/Bharat QR codes, Micro-ATMs) "
        "and transaction flows (credit card, debit card) across bank categories. "
        "Periods are monthly. Values: counts for infrastructure, ₹ thousands for "
        "transaction values, number of transactions for volumes."
    ),
}

# ── Domains per pipeline ──────────────────────────────────────────────────────

PIPELINE_DOMAINS: dict[str, list[str]] = {
    "sibc":    ["credit_headline", "sector_mix", "industry", "retail", "psl"],
    "atm_pos": ["infrastructure", "cards_stock", "credit_card_txn", "debit_card_txn"],
}


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _payload_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _cache_get(conn: sqlite3.Connection, input_hash: str) -> dict | None:
    row = conn.execute(
        "SELECT result FROM llm_cache WHERE input_hash=? AND prompt_version=?",
        (input_hash, PROMPT_VERSION)
    ).fetchone()
    return json.loads(row[0]) if row else None


def _cache_set(conn: sqlite3.Connection, input_hash: str, pipeline: str,
               period: str, domain: str, result: dict,
               model: str, tokens: int) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO llm_cache
           (input_hash, prompt_version, pipeline, period, domain,
            result, model, tokens_used)
           VALUES (?,?,?,?,?, ?,?,?)""",
        (input_hash, PROMPT_VERSION, pipeline, period, domain,
         json.dumps(result), model, tokens)
    )
    conn.commit()


# ── LLM call ─────────────────────────────────────────────────────────────────

def _call_llm(prompt: str) -> tuple[dict, int]:
    try:
        import anthropic
    except ImportError:
        raise RuntimeError(
            "anthropic package not installed. Run: pip install anthropic"
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY environment variable not set."
        )

    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model=MODEL,
        max_tokens=3000,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )

    text   = msg.content[0].text.strip()
    tokens = msg.usage.input_tokens + msg.usage.output_tokens

    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0].strip()

    result = json.loads(text)
    return result, tokens


# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_prompt(pipeline: str, domain: str, domain_description: str,
                  signals_payload: str) -> str:
    template = (PROMPTS_DIR / "domain_eval.txt").read_text()
    # Use simple string replacement to avoid str.format() choking on JSON
    # braces in the RETURN FORMAT example block.
    return (
        template
        .replace("{pipeline_context}", PIPELINE_CONTEXT[pipeline])
        .replace("{domain_name}",      domain)
        .replace("{domain_description}", domain_description)
        .replace("{signals_payload}",  signals_payload)
    )


# ── Domain evaluation ─────────────────────────────────────────────────────────

def _evaluate_domain(pipeline: str, period: str, domain: str,
                     signals_payload: str, signal_ids: list[str],
                     domain_description: str,
                     conn: sqlite3.Connection) -> tuple[dict, bool]:
    """
    Evaluate one domain. Returns (result_dict, from_cache).
    result_dict keys: signal_ids + '_domain_narrative'.
    """
    cache_key_obj = {
        "pipeline": pipeline,
        "period":   period,
        "domain":   domain,
        "payload":  signals_payload,
        "version":  PROMPT_VERSION,
    }
    input_hash = _payload_hash(cache_key_obj)

    cached = _cache_get(conn, input_hash)
    if cached is not None:
        return cached, True

    prompt = _build_prompt(pipeline, domain, domain_description, signals_payload)
    result, tokens = _call_llm(prompt)

    _cache_set(conn, input_hash, pipeline, period, domain, result, MODEL, tokens)
    return result, False


# ── Source reference ─────────────────────────────────────────────────────────

# Canonical source files per pipeline (relative to repo root)
_SOURCE_FILE: dict[str, str] = {
    "sibc":    "analysis/rbi_sibc/merged/sections_merged.json",
    "atm_pos": "web/public/data/atm_pos_consolidated.csv",
}


def _source_ref(sig: dict) -> dict:
    """
    Build a source-reference dict from a signal's registry entry.
    Carries enough information to locate the exact data series in the
    source file — no values, no interpretation, pure provenance.

    SIBC:    { source_file, section, series }          (1a/1b)
             { source_file, section, series_a, series_b } (spread)
    ATM/POS: { source_file, metric, record_type }      (1a)
             { source_file, metric, record_type, bank_category } (1b/1c)
             { source_file, metrics, record_type }     (csv_sum_yoy)
    """
    pipeline  = sig.get("pipeline", "")
    compute   = sig.get("compute",  {})
    sub_layer = sig.get("sub_layer", "1a")

    ref: dict = {
        "source_file": _SOURCE_FILE.get(pipeline, ""),
        "method":      compute.get("method", ""),
    }

    if pipeline == "sibc":
        if "section" in compute:
            ref["section"] = compute["section"]
        if "series" in compute:
            ref["series"] = compute["series"]
        # spread signals reference two series
        if "series_a" in compute:
            ref["series_a"] = compute["series_a"]
        if "series_b" in compute:
            ref["series_b"] = compute["series_b"]
        if "entity_type" in compute:
            ref["entity_type"] = compute["entity_type"]

    elif pipeline == "atm_pos":
        # record_type: 1a/1c scans on total rows; 1b/1c bank-level
        ref["record_type"] = "bank" if sub_layer in ("1b", "1c") else "total"
        if "metric" in compute:
            ref["metric"] = compute["metric"]
        if "metrics" in compute:           # csv_sum_yoy sums multiple columns
            ref["metrics"] = compute["metrics"]
        if "denominator_metric" in compute:
            ref["denominator_metric"] = compute["denominator_metric"]
        if "denominator_metrics" in compute:
            ref["denominator_metrics"] = compute["denominator_metrics"]
        if "category" in compute:          # 1b named-category signals
            ref["bank_category"] = compute["category"]
        if "value_type" in compute:        # csv_bank_scan: "value" vs "yoy"
            ref["value_type"] = compute["value_type"]

    return ref


# ── Main entry point ──────────────────────────────────────────────────────────

def run_evaluate(pipeline: str, period: str,
                 conn: sqlite3.Connection, registry: dict) -> dict:
    """
    Evaluate all domains for (pipeline, period).
    Returns summary dict. Writes evaluation JSON to evaluations/{pipeline}/{period}.json.
    """
    from .query import build_domain_payload

    domains      = PIPELINE_DOMAINS.get(pipeline, [])
    all_domains  = registry.get("domains", {})
    output: dict = {
        "pipeline":     pipeline,
        "period":       period,
        "evaluated_at": datetime.now().isoformat(timespec="seconds"),
        "prompt_version": PROMPT_VERSION,
        "model":        MODEL,
        "domains":      {},
    }

    total_signals = 0
    cache_hits    = 0
    api_calls     = 0

    for domain in domains:
        domain_description = all_domains.get(domain, domain)
        signals_payload, signal_ids = build_domain_payload(
            conn, pipeline, period, domain, registry
        )

        if not signal_ids:
            print(f"    {domain}: no signals with data — skipped")
            continue

        result, from_cache = _evaluate_domain(
            pipeline, period, domain,
            signals_payload, signal_ids,
            domain_description, conn
        )

        # Separate signal interpretations from domain narrative
        narrative = result.pop("_domain_narrative", "")

        # Build signal entries: LLM interpretation + source provenance
        signals_out: dict = {}
        for sid in signal_ids:
            if sid not in result:
                continue
            sig_entry = dict(result[sid])   # observation / direction / inference
            sig_def   = registry["signals"].get(sid, {})
            sig_entry["source_ref"] = _source_ref(sig_def)
            signals_out[sid] = sig_entry

        output["domains"][domain] = {
            "narrative": narrative,
            "signals":   signals_out,
        }

        n = len(signal_ids)
        total_signals += n
        if from_cache:
            cache_hits += 1
            print(f"    {domain:<22} {n:>2} signals  (cache hit)")
        else:
            api_calls += 1
            print(f"    {domain:<22} {n:>2} signals  (API call)")

    # Write output file
    out_path = EVALS_DIR / pipeline / f"{period}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return {
        "domains_evaluated": len(output["domains"]),
        "signals_interpreted": total_signals,
        "api_calls":  api_calls,
        "cache_hits": cache_hits,
        "output_path": str(out_path),
    }
