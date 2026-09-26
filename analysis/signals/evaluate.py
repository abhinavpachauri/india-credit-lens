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
import subprocess
import time
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core.paths import ROOT as REPO
from core import manifest
from core.llm_budget import require_approval, estimate_usd, LLMSpendNotApproved
PROMPTS_DIR = Path(__file__).parent / "prompts"
EVALS_DIR   = Path(__file__).parent / "evaluations"

MODEL          = "claude-sonnet-4-5-20250929"

# The run's cost estimate, filled in by `evaluate_period` before any billing call. Held at module
# level because the estimate is a property of the RUN (domains × recorded tokens/domain), while
# the guard sits at the single call site.
_EST: dict = {}
PROMPT_VERSION = "1.12"


# ── Deterministic unit normalisation (v1.12) ──────────────────────────────────
# Unit formatting is mechanical, not judgment, so it must not be left to the model —
# which reliably reverts to "120.5M / 78K" however firmly the prompt asks for lakh/crore.
# This converts every M/K/B and million/billion token in the eval prose to Indian
# lakh/crore AFTER the model returns, so the stored narratives are clean by construction.
# The traceability policies scale "crore"/"lakh" too (core.traceability), so the converted
# value still traces to signals.db.
import re as _re

_MKB = {"K": 1e3, "M": 1e6, "B": 1e9, "MILLION": 1e6, "BILLION": 1e9}


def _to_lakh_crore(raw: float) -> str:
    if abs(raw) >= 1e7:
        return f"{raw / 1e7:.2f}".rstrip("0").rstrip(".") + " crore"
    if abs(raw) >= 1e5:
        return f"{raw / 1e5:.2f}".rstrip("0").rstrip(".") + " lakh"
    return f"{raw:,.0f}"


def normalize_units(text: str) -> str:
    """M/K/B and million/billion counts → lakh/crore. Leaves %, x, ₹ L Cr, dates alone."""
    if not isinstance(text, str):
        return text

    def repl(m):
        return _to_lakh_crore(float(m.group(1)) * _MKB[m.group(2).upper()])

    text = _re.sub(r"(?<![A-Za-z\d.])(\d+(?:\.\d+)?)\s?([MKB])\b", repl, text)
    text = _re.sub(r"(?<![A-Za-z\d.])(\d+(?:\.\d+)?)\s?(million|billion)\b", repl, text,
                   flags=_re.I)
    return text


def _normalize_output(output: dict) -> None:
    """Walk the assembled eval and normalise units in every prose field, in place."""
    for domain in output.get("domains", {}).values():
        domain["narrative"] = normalize_units(domain.get("narrative", ""))
        for sig in domain.get("signals", {}).values():
            for k in ("title", "observation", "direction", "inference"):
                if k in sig:
                    sig[k] = normalize_units(sig[k])
            if isinstance(sig.get("chain"), list):
                sig["chain"] = [normalize_units(s) for s in sig["chain"]]
# CLI is fragile with large outputs; API is reliable — larger chunks = fewer calls
CHUNK_SIZE_CLI = 8
CHUNK_SIZE_API = 12

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


def expected_tokens_per_call(conn: sqlite3.Connection, pipeline: str) -> float:
    """What one CALL has actually cost this pipeline, from our own recorded usage.

    One row of llm_cache is one chunk call, so this is per call, not per domain.

    A cost estimate built from a guessed token count is barely better than no estimate, and this
    project already stores the real figure on every call it has ever made. Falls back to a
    deliberately HIGH constant when a pipeline has no history, so a first run over-states rather
    than under-states what the editor is approving.
    """
    # The RECENT average, not all-time. Averaging every row ever written pulled the figure down
    # with small retry/sub-chunk calls and old, narrower payloads: the Jul 2026 run was estimated
    # at $0.29 and cost about $0.45. Payloads grow as the registry grows, so the newest periods
    # are the honest guide. Falls back to a deliberately HIGH constant with no history, so a
    # first run over-states rather than under-states what is being approved.
    row = conn.execute(
        """SELECT AVG(tokens_used) FROM (
               SELECT tokens_used FROM llm_cache
               WHERE pipeline=? AND tokens_used > 0
               ORDER BY created_at DESC LIMIT 12)""",
        (pipeline,)).fetchone()
    return (row[0] if row and row[0] else 0) or 20000.0


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


# ── LLM backend selection ─────────────────────────────────────────────────────
#
# Default: claude CLI (Pro subscription, no extra API cost).
# Fallback: Anthropic SDK if ANTHROPIC_API_KEY is set and --use-api flag passed.
# The CLI path is used whenever `claude` is available in PATH.

def _claude_cli_available() -> bool:
    try:
        r = subprocess.run(["claude", "--version"], capture_output=True, timeout=5)
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

# Prefer Anthropic SDK (API key) over CLI when key is available — faster, no subprocess overhead.
# Falls back to CLI if no key set, falls back to error if neither available.
USE_CLI: bool = (not os.environ.get("ANTHROPIC_API_KEY")) and _claude_cli_available()


def _extract_json(text: str) -> dict:
    """
    Robustly extract the outermost JSON object from a response string.
    Handles: plain JSON, markdown fences, leading/trailing prose.

    Uses raw_decode so it stops at the end of the first complete JSON
    object — never fails on "Extra data" from trailing LLM prose.
    """
    # Strip markdown fences
    if "```" in text:
        for part in text.split("```"):
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                text = part
                break

    # Locate the opening brace (skip any leading prose)
    start = text.find("{")
    if start == -1:
        raise ValueError(f"No JSON object found in LLM response:\n{text[:500]}")

    # raw_decode reads exactly one JSON value and returns (obj, end_pos)
    # — it does not fail on trailing characters after the closing brace
    try:
        obj, _ = json.JSONDecoder().raw_decode(text, start)
        return obj
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON parse error ({exc}). Raw text:\n{text[:800]}")


# ── LLM call ─────────────────────────────────────────────────────────────────

def _call_llm(system_prompt: str, user_content: str) -> tuple[dict, int, int, int]:
    """
    Call Claude via the claude CLI (Pro subscription) or the Anthropic SDK
    (API key). CLI is preferred — no extra cost on top of Claude Pro.

    Returns (result_dict, tokens, cache_read, cache_created).
    Token counts are 0 when using the CLI (not metered that way).
    """
    if USE_CLI:
        # Combine system + user into one prompt passed via stdin
        # so we avoid shell-quoting issues with large payloads
        combined = f"{system_prompt}\n\n{'─'*60}\n\n{user_content}"
        proc = subprocess.run(
            ["claude", "-p", "--output-format", "text"],
            input=combined,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"claude CLI exited {proc.returncode}: {proc.stderr[:300]}"
            )
        text = proc.stdout.strip()
        result = _extract_json(text)
        return result, 0, 0, 0

    # ── Anthropic SDK fallback ────────────────────────────────────────────────
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "claude CLI not found and ANTHROPIC_API_KEY not set. "
            "Either install Claude Code or export ANTHROPIC_API_KEY."
        )
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("pip install anthropic  (or install Claude Code)")

    client = anthropic.Anthropic(api_key=api_key)
    require_approval("Stage 5 signal evaluation", "1 per domain",
                     est_usd=_EST.get("usd"), basis=_EST.get("basis", ""))
    msg = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        temperature=0,
        system=[{
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": user_content}],
        extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
    )
    text = msg.content[0].text.strip()
    usage         = msg.usage
    tokens        = usage.input_tokens + usage.output_tokens
    cache_read    = getattr(usage, "cache_read_input_tokens",    0) or 0
    cache_created = getattr(usage, "cache_creation_input_tokens", 0) or 0
    result = _extract_json(text)
    return result, tokens, cache_read, cache_created


# ── Prompt builder ────────────────────────────────────────────────────────────

_system_prompt_cache: str | None = None

def _get_system_prompt() -> str:
    global _system_prompt_cache
    if _system_prompt_cache is None:
        _system_prompt_cache = (PROMPTS_DIR / "domain_eval_system.txt").read_text()
    return _system_prompt_cache


def _build_user_message(pipeline: str, domain: str, domain_description: str,
                        signals_payload: str,
                        prior_eval_block: str = "") -> str:
    template = (PROMPTS_DIR / "domain_eval_user.txt").read_text()
    return (
        template
        .replace("{pipeline_context}",   PIPELINE_CONTEXT[pipeline])
        .replace("{domain_name}",        domain)
        .replace("{domain_description}", domain_description)
        .replace("{signals_payload}",    signals_payload)
        .replace("{prior_eval_block}",   prior_eval_block)
    )


# ── Prior evaluation helpers ──────────────────────────────────────────────────

def _find_prior_period(conn: sqlite3.Connection, pipeline: str, period: str) -> str | None:
    """Return the latest period in signals.db before the given period, or None."""
    row = conn.execute(
        "SELECT MAX(period) FROM signals WHERE pipeline=? AND period < ?",
        (pipeline, period)
    ).fetchone()
    return row[0] if row and row[0] else None


def _load_prior_eval(pipeline: str, prior_period: str) -> dict:
    """
    Load evaluations/{pipeline}/{prior_period}.json and return a flat dict of
    signal_id → {observation, direction, inference}.
    Returns empty dict if the file doesn't exist.
    """
    path = EVALS_DIR / pipeline / f"{prior_period}.json"
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            data = json.load(f)
        flat: dict = {}
        for domain_data in data.get("domains", {}).values():
            for sig_id, sig_eval in domain_data.get("signals", {}).items():
                flat[sig_id] = {
                    k: sig_eval[k]
                    for k in ("observation", "direction", "inference")
                    if k in sig_eval
                }
        return flat
    except Exception:
        return {}


def _build_prior_eval_block(prior_period: str,
                             domain_signal_ids: list[str],
                             prior_signals: dict,
                             pipeline: str = "") -> str:
    """
    Build the PRIOR PERIOD CONTEXT section for the user prompt.
    Only includes signals that are both in this domain's chunk and have a prior eval entry.
    Returns empty string if nothing to show.
    """
    relevant = {sid: prior_signals[sid] for sid in domain_signal_ids if sid in prior_signals}
    if not relevant:
        return ""

    # Show the data month, not the RBI release date (see query.display_date).
    from .query import display_date
    prior_label = display_date(prior_period, pipeline) if pipeline else prior_period

    lines = [
        "",
        "===========================================================",
        f"PRIOR PERIOD CONTEXT ({prior_label})",
        "===========================================================",
        "These narratives describe the previous period. Note meaningful changes.",
        "",
    ]
    for sig_id, entry in relevant.items():
        lines.append(f"{sig_id}:")
        if "observation" in entry:
            lines.append(f"  observation: {entry['observation']}")
        if "direction" in entry:
            lines.append(f"  direction:   {entry['direction']}")
        if "inference" in entry:
            lines.append(f"  inference:   {entry['inference']}")
        lines.append("")

    return "\n".join(lines)


# ── Domain evaluation ─────────────────────────────────────────────────────────
#
# Every signal sent to the model must come back ACCOUNTED FOR: answered, or failed with a
# reason. Four paths used to lose a signal while reporting success (found by the absence
# reviewer, 2026-09-26): a failed half-chunk dropped when its sibling succeeded; a signal the
# model left out skipped and still counted as interpreted; a partial answer cached and replayed
# as a "cache hit"; a failed domain absent from the file with no marker. Downstream cannot tell
# "the model said nothing" from "we never got an answer", so the difference is recorded here.

class IncompleteAnswer(Exception):
    """The model replied, but not for every signal it was asked about."""

    def __init__(self, missing: list[str], partial: dict, tokens: int = 0):
        self.missing, self.partial, self.tokens = list(missing), partial, tokens
        shown = ", ".join(self.missing[:3]) + (" …" if len(self.missing) > 3 else "")
        super().__init__(f"model did not answer {len(self.missing)} signal(s): {shown}")


def _unanswered(result: dict, ids: list[str]) -> list[str]:
    return [sid for sid in ids if sid not in result]


def _reason(exc: BaseException) -> str:
    text = str(exc).splitlines()[0][:200] if str(exc) else ""
    return f"{type(exc).__name__}: {text}" if text else type(exc).__name__


def _evaluate_chunk(pipeline: str, period: str, domain: str, chunk_idx: int,
                    chunk_payload: str, chunk_ids: list[str],
                    domain_description: str,
                    conn: sqlite3.Connection,
                    prior_period: str | None = None,
                    prior_signals: dict | None = None) -> tuple[dict, bool, int, int, int]:
    """
    Evaluate one chunk of signals. Cache key includes chunk_idx so each chunk
    is cached independently. Prior eval narratives are injected into the prompt
    when available (signal-level, only for signals in this chunk).
    """
    prior_eval_block = ""
    if prior_period and prior_signals:
        prior_eval_block = _build_prior_eval_block(prior_period, chunk_ids, prior_signals, pipeline)

    cache_key_obj = {
        "pipeline":       pipeline,
        "period":         period,
        "domain":         domain,
        "chunk":          chunk_idx,
        "payload":        chunk_payload,
        "version":        PROMPT_VERSION,
        "prior_period":   prior_period or "",
        "prior_eval":     prior_eval_block,   # content change → cache miss
    }
    input_hash = _payload_hash(cache_key_obj)

    cached = _cache_get(conn, input_hash)
    if cached is not None:
        if not _unanswered(cached, chunk_ids):
            return cached, True, 0, 0, 0
        # An incomplete answer cached before this check existed. Replaying it is how a gap becomes
        # permanent: every re-run reports "cache hit, 0 tokens" and the missing signals never
        # return. Treat it as a miss (the call is still priced and approved like any other).

    system_prompt = _get_system_prompt()
    user_message  = _build_user_message(
        pipeline, domain, domain_description, chunk_payload, prior_eval_block
    )
    result, tokens, cache_read, cache_created = _call_llm(system_prompt, user_message)

    # Only a complete answer is cached. A truncated or partial reply goes to the split-and-retry
    # path instead — which is what that path was written for — carrying what did come back.
    missing = _unanswered(result, chunk_ids)
    if missing:
        raise IncompleteAnswer(missing, result, tokens)
    _cache_set(conn, input_hash, pipeline, period, domain, result, MODEL, tokens)
    return result, False, tokens, cache_read, cache_created


def _evaluate_domain(pipeline: str, period: str, domain: str,
                     signals_payload: str, signal_ids: list[str],
                     domain_description: str,
                     conn: sqlite3.Connection,
                     prior_period: str | None = None,
                     prior_signals: dict | None = None,
                     chunk_size: int | None = None) -> tuple[dict, bool, int, int, int]:
    """
    Evaluate one domain, chunking into batches of chunk_size to avoid max_tokens
    truncation for large domains (industry=22, retail=23 signals).
    Prior eval narratives (signal-level) are forwarded to each chunk.
    Returns (merged_result_dict, all_from_cache, total_tokens, total_cache_read,
    total_cache_created, failed) — `failed` maps every signal that still has no answer after the
    split-and-retry to the reason. Raises only when NO signal in the domain was answered.
    """
    from .query import build_chunk_payload

    if chunk_size is None:
        chunk_size = CHUNK_SIZE_CLI if USE_CLI else CHUNK_SIZE_API

    chunks = build_chunk_payload(signal_ids, signals_payload, chunk_size)

    def attempt(key: int, payload: str, ids: list[str]):
        """One chunk → (result, from_cache, tokens, cache_read, cache_created, failed{sid: why}).

        A failed or incomplete chunk is split in half and each half retried — the truncation
        guard — down to two signals. Whatever still has no answer is RECORDED with its reason.
        A spend refusal is never split or recorded: splitting cannot fix "not authorised", so it
        propagates and stops the run.
        """
        try:
            r, fc, t, rd, cr = _evaluate_chunk(
                pipeline, period, domain, key, payload, ids, domain_description, conn,
                prior_period=prior_period, prior_signals=prior_signals)
            return r, fc, t, rd, cr, {}
        except LLMSpendNotApproved:
            raise
        except Exception as exc:
            why = _reason(exc)
            partial = exc.partial if isinstance(exc, IncompleteAnswer) else {}
            spent = exc.tokens if isinstance(exc, IncompleteAnswer) else 0
            if len(ids) <= 2:
                return (dict(partial), False, spent, 0, 0,
                        {sid: why for sid in _unanswered(partial, ids)})
            half = max(2, len(ids) // 2)
            result: dict = {}
            failed: dict = {}
            tokens, read, created = spent, 0, 0
            for sub_idx, (sub_payload, sub_ids) in enumerate(
                    build_chunk_payload(ids, payload, half)):
                r, _, t, rd, cr, f = attempt(key * 100 + sub_idx, sub_payload, sub_ids)
                result.update(r)
                failed.update(f)
                tokens, read, created = tokens + t, read + rd, created + cr
            # A retried chunk is never reported as a cache hit, even if its halves were cached:
            # it failed once, and "cache hit, 0 tokens" is the most reassuring line there is.
            return result, False, tokens, read, created, failed

    merged:    dict = {}
    failed:    dict = {}
    all_cache: bool = True
    tot_tok = tot_read = tot_created = 0

    for chunk_idx, (chunk_payload, chunk_ids) in enumerate(chunks):
        result, from_cache, tokens, cache_read, cache_created, chunk_failed = attempt(
            chunk_idx, chunk_payload, chunk_ids)
        # Accumulate signal entries; last chunk's _domain_narrative wins
        merged.update(result)
        failed.update(chunk_failed)
        if not from_cache:
            all_cache = False
        tot_tok     += tokens
        tot_read    += cache_read
        tot_created += cache_created

    if signal_ids and all(sid in failed for sid in signal_ids):
        # Nothing at all came back: the domain failed. Say so, and say WHY.
        first = next(iter(failed.values()), "no reason recorded")
        raise RuntimeError(f"{domain}: no signal was answered — {first}")

    return merged, all_cache, tot_tok, tot_read, tot_created, failed


# ── Source reference ─────────────────────────────────────────────────────────

def _source_file(pipeline: str) -> str:
    """The pipeline's consolidated CSV, repo-relative, as cited in a signal's source reference.
    Read from the manifest rather than restated here — this used to be a second copy of a path
    the manifest already declares."""
    return str(manifest.consolidated_csv(pipeline).relative_to(REPO))


def _source_ref(sig: dict) -> dict:
    """
    Build a source-reference dict from a signal's registry entry.
    Carries enough information to locate the exact data series in the
    source file — no values, no interpretation, pure provenance.

    SIBC:    { source_file, method, code, statement }            (scalar)
             { source_file, method, code_a, code_b, statement }  (spread)
             { source_file, method, parent_code, statement }     (scan)
             Adds is_psl=true for PSL memo items.
    ATM/POS: { source_file, metric, record_type }                (1a)
             { source_file, metric, record_type, bank_category } (1b/1c)
             { source_file, metrics, record_type }               (csv_sum_yoy)
    """
    pipeline  = sig.get("pipeline", "")
    compute   = sig.get("compute",  {})
    sub_layer = sig.get("sub_layer", "1a")

    ref: dict = {
        "source_file": _source_file(pipeline),
        "method":      compute.get("method", ""),
    }

    if pipeline == "sibc":
        # scalar signals: code + statement
        for k in ("code", "statement", "code_a", "code_b",
                  "parent_code", "child_codes", "entity_type",
                  "denominator_code", "denominator_statement"):
            if k in compute:
                ref[k] = compute[k]
        if compute.get("is_psl"):
            ref["is_psl"] = True

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
    Domains are evaluated in parallel when using the API (USE_CLI=False).
    Each parallel thread opens its own DB connection for thread safety.
    Returns summary dict. Writes evaluation JSON to evaluations/{pipeline}/{period}.json.
    """
    from .query import build_domain_payload
    from .db    import init_db
    from concurrent.futures import ThreadPoolExecutor, as_completed

    CHUNK_SIZE = CHUNK_SIZE_CLI if USE_CLI else CHUNK_SIZE_API

    domains      = PIPELINE_DOMAINS.get(pipeline, [])
    all_domains  = registry.get("domains", {})

    # ── Load prior period evaluation for narrative diffing ────────────────────
    prior_period  = _find_prior_period(conn, pipeline, period)
    prior_signals = _load_prior_eval(pipeline, prior_period) if prior_period else {}
    if prior_period and prior_signals:
        print(f"  Prior period: {prior_period} ({len(prior_signals)} signal narratives loaded)")
    elif prior_period:
        print(f"  Prior period: {prior_period} (no evaluation file found — diff inactive)")
    else:
        print(f"  Prior period: none (first evaluation for this pipeline)")

    # ── Build all payloads upfront (main thread, single connection) ───────────
    domain_work: list[tuple[str, str, list[str]]] = []   # (domain, payload, ids)
    for domain in domains:
        payload, ids = build_domain_payload(conn, pipeline, period, domain, registry)
        if not ids:
            print(f"  {domain:<22} — no data, skipped")
        else:
            domain_work.append((domain, payload, ids))

    n_domains = len(domain_work)
    mode = "parallel" if not USE_CLI else "sequential"
    print(f"  Evaluating {n_domains} domain(s) [{mode}, chunk_size={CHUNK_SIZE}] ...")

    # Price the run BEFORE anything can bill, from this pipeline's own recorded usage. A domain
    # already in cache costs nothing, so the estimate counts only the work that would really be
    # sent; the guard at the call site refuses if this was never computed.
    # Count CHUNKS, not domains. A domain is split into chunks of CHUNK_SIZE signals and each
    # chunk is its own call — industry alone is 3 — so pricing per domain understated the bill
    # roughly two-fold. The recorded tokens_used is likewise per chunk, so the two line up.
    n_chunks = sum(max(1, -(-len(ids) // CHUNK_SIZE)) for _, _, ids in domain_work)
    per_chunk = expected_tokens_per_call(conn, pipeline)
    _EST["usd"] = estimate_usd(per_chunk * max(n_chunks, 1), MODEL)
    _EST["basis"] = (f"{n_chunks} call(s) across {n_domains} domain(s) x {per_chunk:,.0f} "
                     f"tokens/call (this pipeline's recorded average), {MODEL} list price")
    print(f"  Estimated cost: ~${_EST['usd']:,.2f}  ({_EST['basis']})")

    output: dict = {
        "pipeline":       pipeline,
        "period":         period,
        "evaluated_at":   datetime.now().isoformat(timespec="seconds"),
        "prompt_version": PROMPT_VERSION,
        "model":          MODEL,
        "prior_period":   prior_period,
        "domains":        {},
    }

    _FAILURES: dict[str, str] = {}
    total_signals  = 0
    total_missing  = 0
    cache_hits     = 0
    api_calls      = 0
    total_tokens   = 0
    total_cached_r = 0
    errors         = 0

    def _eval_one(domain: str, signals_payload: str,
                  signal_ids: list[str]) -> tuple[str, dict | None, bool, int, int, int, float, dict]:
        """Evaluate one domain. Opens its own DB connection (thread-safe)."""
        thread_conn = init_db()
        desc = all_domains.get(domain, domain)
        t0   = time.monotonic()
        try:
            result, from_cache, tokens, cache_read, _, failed = _evaluate_domain(
                pipeline, period, domain,
                signals_payload, signal_ids, desc, thread_conn,
                prior_period=prior_period if prior_signals else None,
                prior_signals=prior_signals if prior_signals else None,
                chunk_size=CHUNK_SIZE,
            )
            return domain, result, from_cache, tokens, cache_read, 0, time.monotonic() - t0, failed
        except Exception as exc:
            # Carry the reason out. "ERROR" alone sends the reader hunting; the actual cause is
            # usually immediately actionable (spend not approved, no credit, bad JSON).
            _FAILURES[domain] = f"{type(exc).__name__}: {str(exc).splitlines()[0][:160]}"
            return domain, None, False, 0, 0, 1, time.monotonic() - t0, {}

    # ── Parallel evaluation (API) or sequential (CLI) ─────────────────────────
    max_workers = 1 if USE_CLI else min(n_domains, 6)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_domain = {
            executor.submit(_eval_one, domain, payload, ids): (domain, ids)
            for domain, payload, ids in domain_work
        }

        for future in as_completed(future_to_domain):
            domain, ids = future_to_domain[future]
            (domain_desc, result, from_cache, tokens, cache_read, err, elapsed,
             failed) = future.result()

            if err or result is None:
                why = _FAILURES.get(domain, "")
                print(f"  {domain:<22} ERROR ({elapsed:.1f}s)" + (f"  {why}" if why else ""))
                errors += 1
                # Recorded IN the file: a domain absent from it reads as "nothing to say".
                output.setdefault("failed_domains", {})[domain] = why or "no reason recorded"
                continue

            # Separate domain narrative from per-signal entries
            narrative  = result.pop("_domain_narrative", "")

            signals_out: dict = {}
            missing: dict = {}
            for sid in ids:
                if sid not in result:
                    missing[sid] = failed.get(sid, "not returned by the model")
                    continue
                sig_entry = dict(result[sid])
                sig_def   = registry["signals"].get(sid, {})
                sig_entry["source_ref"] = _source_ref(sig_def)
                signals_out[sid] = sig_entry

            output["domains"][domain] = {
                "narrative": narrative,
                "signals":   signals_out,
            }
            if missing:
                # Declared, per signal, with the reason: the insight stage must be able to tell
                # "the model had nothing to say" from "we never got an answer".
                output["domains"][domain]["missing_signals"] = missing

            total_signals  += len(signals_out)
            total_missing  += len(missing)
            total_tokens   += tokens
            total_cached_r += cache_read

            if from_cache:
                cache_hits += 1
                tag = f"cache hit"
            else:
                api_calls += 1
                backend    = "CLI" if USE_CLI else "API"
                tag        = f"{backend} call"
                if tokens:
                    tag += f"  {tokens:,} tok"
                    if cache_read:
                        tag += f"  (cached {cache_read:,})"

            gap = f"  ⚠ {len(missing)} unanswered" if missing else ""
            print(f"  {domain:<22} {len(signals_out):>2}/{len(ids)} signals  {tag}  ({elapsed:.1f}s){gap}")

    # An evaluation with no content is not an evaluation. Refuse to WRITE one: Stage 5.5 and the
    # insight layer read this file and cannot tell "the model said nothing" from "nothing moved",
    # so an empty file here becomes a silently unnarrated period downstream.
    if not output["domains"]:
        raise RuntimeError(
            f"{pipeline}/{period}: no domain produced an evaluation ({errors} failed) — "
            f"nothing was written.")
    empty = [d for d, v in output["domains"].items()
             if not v.get("narrative") and not v.get("signals")]
    if empty and len(empty) == len(output["domains"]):
        raise RuntimeError(
            f"{pipeline}/{period}: every domain came back empty ({', '.join(empty)}) — "
            f"nothing was written. This is a failed run, not a cheap one.")
    if empty:
        print(f"  ⚠ {len(empty)} domain(s) produced no narrative: {', '.join(empty)}")

    # Units are deterministic — normalise M/K/B → lakh/crore before writing, so the stored
    # narratives never depend on the model getting the format right (v1.12).
    _normalize_output(output)

    # Write output file
    out_path = EVALS_DIR / pipeline / f"{period}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return {
        "domains_evaluated":   len(output["domains"]),
        "signals_interpreted": total_signals,
        "signals_missing":     total_missing,
        "failed_domains":      output.get("failed_domains", {}),
        "api_calls":           api_calls,
        "cache_hits":          cache_hits,
        "errors":              errors,
        "total_tokens":        total_tokens,
        "cache_read_tokens":   total_cached_r,
        "output_path":         str(out_path),
        "prior_period":        prior_period,
    }
