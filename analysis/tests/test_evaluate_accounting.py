#!/usr/bin/env python3
"""Every signal sent to the model comes back ACCOUNTED FOR — answered, or failed with a reason.

The absence reviewer (2026-09-26) found four paths in the Stage 5 evaluator that lost signals
while reporting success, plus a caller that exited 0 whatever happened:

  A. a failed half-chunk was dropped when its sibling succeeded;
  B. a signal the model left out was skipped, and still counted as interpreted;
  C. a partial answer was cached, then replayed on every re-run as a "cache hit";
  D. a failed domain was simply absent from the evaluation file;
  E. `generate_signal_history evaluate` returned 0 on a failed or partial run.

Downstream (the card generators) cannot tell "the model had nothing to say" from "we never got an
answer", so the evaluator must say which. These tests drive each path with a fake LLM and an
in-memory cache: no paid call is made and signals.db is never touched.

Run: python3 -m pytest analysis/tests/test_evaluate_accounting.py -q
"""
import re
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from signals import evaluate as E                          # noqa: E402
from core.llm_budget import LLMSpendNotApproved             # noqa: E402

IDS = [f"sig-{i}" for i in range(6)]


def payload(ids):
    return "\n".join(f"--- {sid} [type: scalar] ---\nvalue: 1.0\n" for sid in ids)


def cache_conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("""CREATE TABLE llm_cache (input_hash TEXT NOT NULL, prompt_version TEXT NOT NULL,
        pipeline TEXT, period TEXT, domain TEXT, result TEXT NOT NULL, model TEXT,
        tokens_used INTEGER, created_at TEXT, PRIMARY KEY (input_hash, prompt_version))""")
    return conn


def fake_llm(monkeypatch, behave):
    """Replace the model with `behave(ids_in_request) -> dict | Exception`. Records every call."""
    calls = []

    def call(system_prompt, user_message):
        asked = re.findall(r"--- (\S+) \[", user_message)
        calls.append(asked)
        out = behave(asked)
        if isinstance(out, BaseException):
            raise out
        return out, 100, 0, 0

    monkeypatch.setattr(E, "_call_llm", call)
    monkeypatch.setattr(E, "_get_system_prompt", lambda: "system")
    return calls


def answer(ids, omit=()):
    out = {sid: {"observation": f"about {sid}"} for sid in ids if sid not in omit}
    out["_domain_narrative"] = "narrative"
    out["_asked"] = sorted(ids)          # stamps which request this answer belongs to
    return out


def run(conn, ids=IDS):
    return E._evaluate_domain("sibc", "2026-08-31", "industry", payload(ids), ids, "desc",
                              conn, chunk_size=len(ids))


def test_a_complete_answer_is_answered_cached_and_replayed(monkeypatch):
    conn = cache_conn()
    calls = fake_llm(monkeypatch, lambda asked: answer(asked))
    merged, from_cache, *_, failed = run(conn)
    assert failed == {} and all(sid in merged for sid in IDS) and not from_cache
    merged2, from_cache2, *_ = run(conn)
    assert from_cache2 and len(calls) == 1, "a complete answer is cached and replayed"


def test_A_a_failed_half_is_recorded_not_dropped(monkeypatch):
    conn = cache_conn()

    def behave(asked):
        if len(asked) == 6 or "sig-4" in asked:     # full chunk fails; the second half fails too
            return RuntimeError("upstream timed out")
        return answer(asked)

    fake_llm(monkeypatch, behave)
    merged, from_cache, *_, failed = run(conn)
    # The failing half [3,4,5] is split again: [3,4] still fails, [5] is answered — the split
    # rescues what it can, and records the rest.
    assert {s for s in IDS if s in merged} == {"sig-0", "sig-1", "sig-2", "sig-5"}
    assert set(failed) == {"sig-3", "sig-4"}
    assert all("timed out" in why for why in failed.values()), "the reason travels with the gap"
    assert not from_cache, "a retried chunk is never reported as a cache hit"


def test_B_a_signal_the_model_leaves_out_is_recorded(monkeypatch):
    conn = cache_conn()
    fake_llm(monkeypatch, lambda asked: answer(asked, omit={"sig-5"}))
    merged, *_, failed = run(conn)
    assert "sig-5" not in merged
    assert "sig-5" in failed and "did not answer" in failed["sig-5"]
    assert set(failed) == {"sig-5"}, "the siblings of an omitted signal are still answered"


def test_C_an_incomplete_answer_is_never_cached(monkeypatch):
    conn = cache_conn()
    calls = fake_llm(monkeypatch, lambda asked: answer(asked, omit={"sig-5"}))
    run(conn)
    first = len(calls)
    run(conn)
    assert len(calls) > first, "the chunk that lost sig-5 is asked again, not replayed from cache"
    import json
    rows = [json.loads(r) for (r,) in conn.execute("SELECT result FROM llm_cache")]
    assert rows, "complete answers are still cached"
    for row in rows:
        assert set(row["_asked"]) <= set(row), \
            f"cached an answer missing {set(row['_asked']) - set(row)} from its own request"


def test_C_a_partial_answer_already_in_cache_is_not_replayed(monkeypatch):
    """Caches written before this check existed may hold partial answers."""
    conn = cache_conn()
    calls = fake_llm(monkeypatch, lambda asked: answer(asked))
    run(conn)                                           # populate the cache with a full answer
    conn.execute("UPDATE llm_cache SET result = ?", ('{"sig-0": {}}',))  # corrupt it to partial
    merged, from_cache, *_, failed = run(conn)
    assert len(calls) == 2 and not from_cache and failed == {}
    assert all(sid in merged for sid in IDS)


def test_nothing_answered_fails_the_domain_with_its_reason(monkeypatch):
    conn = cache_conn()
    fake_llm(monkeypatch, lambda asked: RuntimeError("credit balance is too low"))
    with pytest.raises(RuntimeError, match="credit balance"):
        run(conn)


def test_a_spend_refusal_stops_the_run_and_is_not_split(monkeypatch):
    conn = cache_conn()
    calls = fake_llm(monkeypatch, lambda asked: LLMSpendNotApproved("not approved"))
    with pytest.raises(LLMSpendNotApproved):
        run(conn)
    assert len(calls) == 1, "splitting cannot fix 'not authorised'"


@pytest.mark.parametrize("errors,missing,code", [(0, 0, 0), (1, 0, 1), (0, 3, 1)])
def test_E_evaluate_exits_nonzero_when_incomplete(monkeypatch, errors, missing, code):
    from core import generate_signal_history as G
    import signals.evaluate as ev
    summary = {"errors": errors, "signals_missing": missing, "failed_domains": {},
               "domains_evaluated": 1, "signals_interpreted": 5, "api_calls": 1,
               "cache_hits": 0, "prior_period": None, "total_tokens": 0,
               "cache_read_tokens": 0, "output_path": "x.json"}
    monkeypatch.setattr(ev, "run_evaluate", lambda *a, **k: summary)
    monkeypatch.setattr("signals.db.init_db", lambda: None)
    assert G.cmd_evaluate("sibc", "2026-08-31") == code


def test_BD_the_file_records_failed_domains_and_unanswered_signals(monkeypatch, tmp_path):
    """Run level: a failed domain and an unanswered signal are written INTO the evaluation file,
    and only answered signals are counted as interpreted."""
    import json
    domains = {"industry": ["sig-0", "sig-1", "sig-2"], "retail": ["sig-3", "sig-4"]}

    def behave(asked):
        if "sig-3" in asked or "sig-4" in asked:
            return RuntimeError("retail upstream down")
        return answer(asked, omit={"sig-2"})

    fake_llm(monkeypatch, behave)
    monkeypatch.setattr(E, "EVALS_DIR", tmp_path)
    monkeypatch.setattr(E, "PIPELINE_DOMAINS", {"sibc": list(domains)})
    monkeypatch.setattr(E, "_find_prior_period", lambda *a: None)
    monkeypatch.setattr(E, "expected_tokens_per_call", lambda *a: 1000.0)
    monkeypatch.setattr("signals.query.build_domain_payload",
                        lambda conn, pl, per, d, reg: (payload(domains[d]), domains[d]))
    monkeypatch.setattr("signals.db.init_db", cache_conn)

    summary = E.run_evaluate("sibc", "2026-08-31", cache_conn(),
                             {"domains": {}, "signals": {f"sig-{i}": {"pipeline": "sibc"}
                                                         for i in range(5)}})
    written = json.loads((tmp_path / "sibc" / "2026-08-31.json").read_text())

    assert summary["signals_interpreted"] == 2, "only answered signals are counted"
    assert summary["signals_missing"] == 1 and summary["errors"] == 1
    assert "sig-2" in written["domains"]["industry"]["missing_signals"]
    assert "retail upstream down" in written["failed_domains"]["retail"]


def test_an_unreadable_prior_evaluation_is_not_reported_as_missing(monkeypatch, tmp_path):
    """Missing and unreadable are different answers. Only the first may return {}."""
    monkeypatch.setattr(E, "EVALS_DIR", tmp_path)
    assert E._load_prior_eval("sibc", "2026-07-31") == {}, "a missing file is a legitimate {}"
    (tmp_path / "sibc").mkdir()
    (tmp_path / "sibc" / "2026-07-31.json").write_text('{"domains": {"industry": ')   # truncated
    with pytest.raises(RuntimeError, match="cannot be read"):
        E._load_prior_eval("sibc", "2026-07-31")
