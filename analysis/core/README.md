# `core/` — generic engines + the gate

Pipeline-agnostic machinery. **Nothing here inspects a pipeline id** — every engine is
parameterized by `--pipeline {id}` and reads the per-pipeline manifest
(`pipelines/{id}/pipeline.json`). Adding a data source must not require editing this dir
(the source-#3 litmus). Design rationale: `core/MANIFEST_DESIGN.md`.

## The gate
- **`gate.py`** — the ONE manifest-driven gate runner (replaced `run_evals` /
  `run_atm_pos_evals`, now in `legacy/`). Executes the manifest's ordered stage list;
  `CORE_MAP` resolves `core.*` stage names to scripts here. Modes: `--merged`, `--period`,
  `--xlsx`, `--skip-build`.
- **`paths.py`** — `ROOT` / `ANALYSIS` via `.git`-walk, so every script resolves repo paths
  independent of its own location (survives the §4 relocations).

## Model + state engines (run inside the gate, both pipelines)
- **`generate_skeleton.py`** — S1 structural skeleton from the consolidated CSV.
- **`validate_system_model.py`** — v4.0 model gate (structure + D1/D2/D3 + force sourcing).
- **`generate_system_state.py`** — S3 dynamic state (forces/edges/loops fire from `signals.db`).
- **`derive_opportunities.py`** — opportunity status (active/watch/closed) from S3 firing.
- **`validate_opportunity_traceability.py`** — Check 4f: every number in an opportunity traces
  to its driver's evidence (binds the SIBC `NumberPolicy` off `traceability.py`).
- **`generate_chart_series.py`** — compact precomputed chart series (compute-once-ship-compact).
- **`generate_signal_history.py`** — Stage 4/5 `append` / `evaluate` / `status` / `seed`.
- **`run_inference.py`** — S4 sourcing-gated proposals (never auto-promoted).
- **`validate_timeline.py`** — Check 0: timeline.json schema + path existence.
- **`traceability.py`** — shared number-tracing core (`extract_numbers` / `matches` /
  `ratio_matches`) parameterized by a `NumberPolicy` (SIBC vs ATM_POS); the per-pipeline
  traceability validators are thin wrappers over this.
