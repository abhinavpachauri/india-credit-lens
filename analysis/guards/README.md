# `guards/` — deterministic freshness + integrity checks

Fail-fast guards that catch "committed artifact drifted from its source". Run inside the
gates and in the git pre-commit hook (`analysis/git_hooks/pre-commit`). All deterministic
(no LLM); each regenerates-and-compares or re-validates.

- **`check_signal_freshness.py`** (Check 2f / 5b2) — recompute every `(pipeline, period)`
  from the consolidated CSV into a scratch DB and fail on any value/status/missing/orphan
  drift vs the committed `signals.db`. Closes the gap a binary-DB git-diff can't see. Fix on
  failure = re-append **every** period, not just the latest.
- **`check_derived_fresh.py`** — regenerate the deterministic S1→S3 chain (skeleton,
  system_state, opportunities, cross-links, feed, chart_series) **plus the architecture graph +
  generated doc**, then fail if any tracked derived artifact changed. Pre-commit guard.
- **`validate_signal_history.py`** (Check 2e) — signal-history integrity: DB rows, registry
  schema, status sync vs the DB latest.
