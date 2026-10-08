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
- `kind` — `primary` (signals, a system model, a page) or `reference` (data others measure
  against). Required; a test holds it to the declared capabilities.
- `depends_on` — the reference pipelines whose CSV this pipeline's signals read. The gate then
  runs each reference's `currency_stage` first.

## `mospi/` — MoSPI IIP, WPI, NAS, CPI (reference)
API pull, not XLSX. `datasets` declares each series as data (endpoint, filters and the row field
that verifies each, levels kept, printed-growth pairings, expected lag). fetch (CPI: eSankhyiki annex + workbook; `--cpi-pdf` fallback) ·
detect_format · consolidate · validate_csv (1b, release calendar) · validate_published_growth (1c).
Contract and rules: `analysis/signals/README.md`, "MoSPI".

## `sibc/` — RBI SIBC (bank credit)
Hand-authored annotation path. detect_format · extract_sibc · update_web_data · generate_merge ·
validate_{sections,annotations,content,annotation_basis,web_series} · generate_analysis_report
(Stage 5.5 insights) · validate_sibc_traceability (Check 2g) · promote_annotations (Stage 7).

## `atm_pos/` — RBI ATM/POS (payments)
Fully deterministic insight path. detect_atm_pos_format · extract_atm_pos · validate_atm_pos ·
consolidate_atm_pos · compute_atm_pos_signals (Stage 4a) · generate_atm_pos_insights (4b) ·
validate_atm_pos_insights (4c) · validate_atm_pos_claims (4d).

Adding a source = a new `pipelines/{x}/pipeline.json` + a thin extractor module, reusing
`core.*` stages — zero edits to `core/` or `gate.py`. See `ARCHITECTURE.md` §"Adding a pipeline".
