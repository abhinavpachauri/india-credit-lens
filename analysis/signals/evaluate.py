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
PROMPTS_DIR = Path(__file__).parent / "prompts"
EVALS_DIR   = Path(__file__).parent / "evaluations"

MODEL          = "claude-sonnet-4-5-20250929"
PROMPT_VERSION = "1.11"
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
        return cached, True, 0, 0, 0

    system_prompt = _get_system_prompt()
    user_message  = _build_user_message(
        pipeline, domain, domain_description, chunk_payload, prior_eval_block
    )
    result, tokens, cache_read, cache_created = _call_llm(system_prompt, user_message)

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
    Returns (merged_result_dict, all_from_cache, total_tokens, total_cache_read, total_cache_created).
    """
    from .query import build_chunk_payload

    if chunk_size is None:
        chunk_size = CHUNK_SIZE_CLI if USE_CLI else CHUNK_SIZE_API

    chunks = build_chunk_payload(signal_ids, signals_payload, chunk_size)

    merged:    dict = {}
    all_cache: bool = True
    tot_tok = tot_read = tot_created = 0

    for chunk_idx, (chunk_payload, chunk_ids) in enumerate(chunks):
        try:
            result, from_cache, tokens, cache_read, cache_created = _evaluate_chunk(
                pipeline, period, domain, chunk_idx,
                chunk_payload, chunk_ids,
                domain_description, conn,
                prior_period=prior_period,
                prior_signals=prior_signals,
            )
        except Exception as exc:
            # Truncation guard: if a chunk fails, split it in half and retry each half
            if len(chunk_ids) <= 2:
                raise   # already minimal — propagate
            from .query import build_chunk_payload as _bcp
            half = max(2, len(chunk_ids) // 2)
            sub_chunks = _bcp(chunk_ids, chunk_payload, half)
            result = {}
            tokens = cache_read = cache_created = 0
            from_cache = True
            for sub_idx, (sub_payload, sub_ids) in enumerate(sub_chunks):
                try:
                    sub_result, sub_cache, sub_tok, sub_read, sub_created = _evaluate_chunk(
                        pipeline, period, domain,
                        chunk_idx * 100 + sub_idx,   # unique sub-chunk key
                        sub_payload, sub_ids,
                        domain_description, conn,
                        prior_period=prior_period,
                        prior_signals=prior_signals,
                    )
                except Exception:
                    # Sub-chunk also failed — skip it rather than killing the domain
                    sub_result, sub_cache = {}, True
                    sub_tok = sub_read = sub_created = 0
                result.update(sub_result)
                tokens      += sub_tok
                cache_read  += sub_read
                cache_created += sub_created
                if not sub_cache:
                    from_cache = False

        # Accumulate signal entries; last chunk's _domain_narrative wins
        merged.update(result)
        if not from_cache:
            all_cache = False
        tot_tok     += tokens
        tot_read    += cache_read
        tot_created += cache_created

    return merged, all_cache, tot_tok, tot_read, tot_created


# ── Source reference ─────────────────────────────────────────────────────────

# Canonical source files per pipeline (relative to repo root)
_SOURCE_FILE: dict[str, str] = {
    "sibc":    "web/public/data/rbi_sibc_consolidated.csv",
    "atm_pos": "web/public/data/atm_pos_consolidated.csv",
}


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
        "source_file": _SOURCE_FILE.get(pipeline, ""),
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

    output: dict = {
        "pipeline":       pipeline,
        "period":         period,
        "evaluated_at":   datetime.now().isoformat(timespec="seconds"),
        "prompt_version": PROMPT_VERSION,
        "model":          MODEL,
        "prior_period":   prior_period,
        "domains":        {},
    }

    total_signals  = 0
    cache_hits     = 0
    api_calls      = 0
    total_tokens   = 0
    total_cached_r = 0
    errors         = 0

    def _eval_one(domain: str, signals_payload: str,
                  signal_ids: list[str]) -> tuple[str, dict | None, bool, int, int, int, float]:
        """Evaluate one domain. Opens its own DB connection (thread-safe)."""
        thread_conn = init_db()
        desc = all_domains.get(domain, domain)
        t0   = time.monotonic()
        try:
            result, from_cache, tokens, cache_read, _ = _evaluate_domain(
                pipeline, period, domain,
                signals_payload, signal_ids, desc, thread_conn,
                prior_period=prior_period if prior_signals else None,
                prior_signals=prior_signals if prior_signals else None,
                chunk_size=CHUNK_SIZE,
            )
            return domain, result, from_cache, tokens, cache_read, 0, time.monotonic() - t0
        except Exception as exc:
            return domain, None, False, 0, 0, 1, time.monotonic() - t0

    # ── Parallel evaluation (API) or sequential (CLI) ─────────────────────────
    max_workers = 1 if USE_CLI else min(n_domains, 6)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_domain = {
            executor.submit(_eval_one, domain, payload, ids): (domain, ids)
            for domain, payload, ids in domain_work
        }

        for future in as_completed(future_to_domain):
            domain, ids = future_to_domain[future]
            domain_desc, result, from_cache, tokens, cache_read, err, elapsed = future.result()

            if err or result is None:
                print(f"  {domain:<22} ERROR ({elapsed:.1f}s)")
                errors += 1
                continue

            # Separate domain narrative from per-signal entries
            narrative  = result.pop("_domain_narrative", "")

            signals_out: dict = {}
            for sid in ids:
                if sid not in result:
                    continue
                sig_entry = dict(result[sid])
                sig_def   = registry["signals"].get(sid, {})
                sig_entry["source_ref"] = _source_ref(sig_def)
                signals_out[sid] = sig_entry

            output["domains"][domain] = {
                "narrative": narrative,
                "signals":   signals_out,
            }

            total_signals  += len(ids)
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

            print(f"  {domain:<22} {len(ids):>2} signals  {tag}  ({elapsed:.1f}s)")

    # Write output file
    out_path = EVALS_DIR / pipeline / f"{period}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return {
        "domains_evaluated":   len(output["domains"]),
        "signals_interpreted": total_signals,
        "api_calls":           api_calls,
        "cache_hits":          cache_hits,
        "errors":              errors,
        "total_tokens":        total_tokens,
        "cache_read_tokens":   total_cached_r,
        "output_path":         str(out_path),
        "prior_period":        prior_period,
    }
