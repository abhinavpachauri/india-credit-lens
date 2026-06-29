# `pipelines/{id}/` — per-pipeline custom modules

Each data source is a directory with a **manifest** (`pipeline.json`) plus the **custom
modules** that genuinely differ between sources (extractors, insight generators, validators).
Generic logic lives in `core/`; this dir holds only what is source-specific. The gate never
hard-codes a pipeline — it reads `pipeline.json`.

## `pipeline.json` (the contract)
- `paths` / `schema` — where the data lives + the CSV column names generic engines read.
- `modules` — logical stage name → script in this dir (e.g. `insights` →
  `generate_atm_pos_insights.py`).
- `gate` — the ordered stage list (this IS the gate sequence); each stage targets a
  `core.*` engine, a `pipeline.*` module, or a builtin (pytest / web_build / web_tests /
  csv_integrity). `requires` / `skip_if` / `args_merged` tune per-mode behaviour.
- `period_resolver` (atm_pos) — how `--xlsx` ingest derives the period from a raw file.

## `sibc/` — RBI SIBC (bank credit)
Hand-authored annotation path. detect_format · extract_sibc · update_web_data · generate_merge ·
validate_{sections,annotations,content,annotation_basis,web_series} · generate_analysis_report
(Stage 5.5 insights) · validate_sibc_traceability (Check 2g) · promote_annotations (Stage 7).

## `atm_pos/` — RBI ATM/POS (payments)
Fully deterministic insight path. detect_atm_pos_format · extract_atm_pos · validate_atm_pos ·
consolidate_atm_pos · compute_atm_pos_signals (Stage 4a) · generate_atm_pos_insights (4b) ·
validate_atm_pos_insights (4c) · validate_atm_pos_claims (4d).

Adding source #3 = a new `pipelines/{x}/pipeline.json` + a thin extractor module, reusing
`core.*` stages — zero edits to `core/` or `gate.py`. See `core/MANIFEST_DESIGN.md`.
