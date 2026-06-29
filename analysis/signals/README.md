# `signals/` — signal store, compute engine, evaluation

The Layer-1 signal subsystem: a registry of signal specs, the SQLite fact store, the
deterministic compute engine, and the LLM evaluation layer.

## Store + catalog
- **`registry.json`** — universal signal catalog (L1/L2/L3 tagged; L1 signals carry compute
  specs). The single declaration of what each signal is.
- **`signals.db`** — **primary store** (SQLite): `(pipeline, period, metric_id, entity_type,
  entity_id)` fact table + `metric_ranges`. Binary — guarded by `guards/check_signal_freshness`.
- **`db.py`** — schema init + `refresh_ranges()`.

## Compute (`compute/`)
- **`engine.py`** — `run_append(pipeline, period, db, registry)` dispatches each signal to its
  method. **`sibc.py`** / **`atm_pos.py`** implement the 1a/1b/1c/1d methods (read the
  consolidated CSV; hot filter columns are `category`-dtype for speed). Both cache the CSV
  per process via `_load_df()`.

## Evaluate + query
- **`evaluate.py`** — Stage 5 LLM evaluation: builds domain payloads from `signals.db`, calls
  the model, writes `evaluations/{pipeline}/{period}.json`. Caches by payload hash + prompt
  version.
- **`query.py`** — builds signal payloads (scalar + scan + full chronological series) for
  evaluate and for traceability ground-truth (`signal_numbers` / `flat_numbers`).
- **`apply_status_rules.py`**, **`update_registry.py`**, **`rebuild_*_signals.py`**,
  **`migrate_to_db.py`** — maintenance/backfill helpers.

Append/evaluate are driven via `core/generate_signal_history.py`, not these scripts directly.
