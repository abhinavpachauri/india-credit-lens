# Pipeline Architecture — India Credit Lens

> **What every pipeline does, stage by stage, and why the stages are in that order.** This is the
> reference; it is not a runbook. To *run* an ingestion use the skills (`/ingest-period`,
> `/model-pass`, `/s4-source`). What is generic across pipelines and what is not is in
> `ARCHITECTURE.md`; the per-folder READMEs and `ARCHITECTURE.generated.md` map the code. Revised
> 2026-09-24: the March–July material (per-period authoring, subsystems, mermaid, a hand-drawn
> directory tree) was removed and is in git history.

---

## 1. Principles

- **One gate, many pipelines.** `analysis/core/gate.py --pipeline {id}` runs every pipeline.
  A pipeline is a manifest (`analysis/pipelines/{id}/pipeline.json`) that declares its stages,
  modules, paths, compute shape and the artifacts it rewrites. The gate never branches on the id.
  Pipelines run independently: a new credit file does not block a payments file.
- **Same stage purposes, different scripts.** Stage order is the contract; the manifest names
  the script that fulfils each stage.
- **Deterministic where mechanical, LLM where judgment.** Computation, status, selection, routing
  and every published number are deterministic. The LLM only narrates, and every number it writes
  is checked against the signal store. It never decides a number (`DECISIONS.md`).
- **Evaluating the model ≠ changing the model.** Layer 2 is *evaluated* every period (S3,
  deterministic). The model is *changed* only in an explicit, sourced authoring pass.
- **Presentation is downstream.** Dashboards read sidecars stamped by the gate; nothing in the web
  layer computes or formats a number that a validator cannot see.
- **A committed artifact is stale until proven fresh.** Derived artifacts declare themselves in the
  manifest (`derived`), and the pre-commit hook regenerates and compares them; `signals.db` is
  recomputed from the CSVs and compared row by row.

---

## 2. Layers

| Layer | What | Where | Cadence |
|---|---|---|---|
| **L1** computed signals | rates, shares, sizes, movement, scans — from the consolidated CSV | `signals/registry.json` (spec) → `signals/signals.db` (values) | every ingestion |
| **L2 · S1** structural skeleton | entities + composition edges, URNs, concept tags | `core/generate_skeleton.py` → `system_model.json` | deterministic, every ingestion |
| **L2 · S2a** causal structure | channels over concepts | `analysis/ontology/{concepts,channels}.json` (shared hub) | authored, rarely |
| **L2 · S2b** forces | dated, **sourced** activations of a channel | `force_instances[]` in `system_model.json` | authored (`/model-pass`) |
| **L2 · S3** dynamic state | forces/edges/loops firing, mix states, opportunity status | `core/generate_system_state.py`, `core/derive_opportunities.py` | computed, every ingestion |
| **L2 · S4** inference | unexplained movements → proposed forces (hypotheses) | `core/run_inference.py` → `s4_proposals/{period}.json` | on demand; human-sourced (`/s4-source`) |
| **L2b / L3** cross-system | constructs, eco-edges, cross-pipeline loops, reconciliation constraints | `cross_source/{composition,ecosystem_model}.json` → `ecosystem_state_{period}.json` | projected every ingestion; authored rarely |

Specs: `analysis/signals/README.md` (L1), `analysis/SYSTEM_MODEL_SPEC.md` (L2),
`analysis/COMPOSITION_SPEC.md` (cross-system), `analysis/DASHBOARD_SPEC.md` (what reaches a reader).

---

## 3. The stage sequence

The manifest is the source of truth for the exact list per pipeline; this is the shape every
pipeline follows. Stage labels differ between pipelines; purposes do not.

| # | Stage | What it guarantees |
|---|---|---|
| T | unit tests | the deterministic core behaves |
| 0 | **format detection** | the new file has the structure the extractor expects; drift stops here, loudly |
| 0.6 | **extract** → `{period}/sections.json` | typed, schema-validated rows (the file is archived into `{period}/raw/`) |
| 0.7 | **consolidate** → the pipeline's consolidated CSV (+ timeline for NBFC/ATM-POS) | one long-format CSV per pipeline: the single source for charts and signals. SIBC's **date remap** is gated here (see §5) |
| 1 | data validation | sections, CSV integrity, pipeline-specific checks (e.g. NBFC 1c: computed YoY vs RBI's printed column) |
| — | *L1 append* (`generate_signal_history.py append`) | signals computed into `signals.db`; run before the gate so the gate checks this period |
| 2e / 2f | signal history + **freshness** | registry ↔ DB consistent; every stored row equals a fresh recompute from the CSV |
| — | *L1 narration* (`evaluate`, **paid**, SIBC + ATM/POS) | per-signal narrative; approved per run, $5 ceiling |
| 5.5 / 4b | **insight cards** (SIBC `generate_analysis_report`, ATM/POS `generate_atm_pos_insights`) | deterministic selection + routing; scalar prose from the eval, scan prose deterministic |
| 2g / 4c | **card traceability** | every number in a card traces to its declared signals |
| 5.7 / 5.8 | card ↔ chart cut, card prose voice | the chart answers the card's question; no advice, forecasts or banned register |
| 4-pre / 4 | skeleton regen + model validation | structure regenerated from the CSV; forces sourced; behavioral layer preserved |
| 4b | **S3 system state** | forces fire, mix states computed, from `signals.db` |
| 5.9 | **state band, planes, cut tables** + their traceability | the dashboard sidecars, with every number scoped to its own signals |
| 4c–4f | opportunities, composition, ecosystem projection, feed, **opportunity traceability** | cross-system state; every opportunity number traces to its evidence set |
| 5 | architecture reconcile | docs, skills and settings name files that exist; context stays within budget |
| 5b / 6 | web tests, `tsc` + `npm run build` | the site builds |

NBFC has no card layer by design, so it skips 5.5–5.8 and the paid narration.

---

## 4. Layer 2 model cadence

- **UPDATE** (every current-period ingestion, standing rule): S4 proposals → Chrome sourcing →
  promote only verified forces; additive only; an honest null goes in `_meta.update_note`.
- **FOUNDATION** (the March file, `is_fy_end: true`; the first period of a new source; a
  structural event): a full review of the behavioral layer.
- Backdated ingests are **backfill-only** unless the user asks otherwise.
- `_meta` records `mode`, `last_foundation_date`, `last_updated`.

How to run it: `/model-pass`. After any model change the full gate re-runs S3 onward.

---

## 5. Pipelines

### SIBC: RBI Sector/Industry-wise Bank Credit
- Monthly XLSX, released on the last day of M+1; manual download. Data dir `analysis/rbi_sibc/`.
- **Date normalisation** is a hard, gated rule (CLAUDE.md § SIBC date normalisation). The
  approved record is `analysis/rbi_sibc/date_remap.json`; `update_web_data.py --check` runs as
  stage 1a and `--xlsx` ingestion stops at 0.7 on an unclassified date. Approve with
  `update_web_data.py --approve` only after the user classifies each date.
- `timeline.json` entries are added **by hand** (`dataDate`, `csv_date`, `is_fy_end`), unlike the
  other two pipelines, whose consolidate step registers the period.
- Cards: 96 generated (`sibc_l1_annotations.json`) + 26 hand-written annotations in
  `rbi_sibc.ts`, promoted from `merged/annotations_merged.ts` only by `promote_annotations.py`.
- Compute shape: `csv_sector` (one measure over a code hierarchy, optional `statement` scope and
  PSL memo lens declared in the manifest `schema`).

### ATM/POS: RBI ATM, Acceptance Infrastructure and Card Statistics
- Monthly XLSX, ~M+2, irregular; 63 banks (roster is time-aware: `rbi_atm_pos/canonical_banks.json`).
- Compute shape: `atm_pos` (many measures over the same bank/category entities). 26 measures break
  out by bank; each breakout ships as its own file, fetched when opened.
- Cards: Stage 4a (`compute_atm_pos_signals.py` → `rbi_atm_pos/signals.json`) **must** precede 4b,
  or the dashboard serves the prior month. 4b overrides anchored scalar prose with the eval
  (`EVAL_ANCHOR`); the dominance guard attributes a move owned by one bank. Pipeline-specific
  notes: `analysis/rbi_atm_pos/CLAUDE.md`.

### NBFC: RBI Sectoral Deployment of NBFC Credit
- Monthly XLSX, ~M+2; manual download. The press release states headline numbers in text, which is
  free ground truth for the extractor (stage 1c checks our YoY against RBI's printed column).
- Covers ~87% of the NBFC sector: a page-level caveat, never a per-table footnote.
- Compute shape: `csv_sector` (same as SIBC). **No card layer** (v1): the dashboard is the state
  band + cut tables only. Revisit at ~12 releases.

---

## 6. The signal store

- **Registry** (`signals/registry.json`): the catalog of Layer 1 **computed** signals only. IDs are
  permanent. Every signal declares `layer`, `pipeline`, `compute` (method + params), `cadence`
  (how often the value can change) and, where relevant, `window`. Methods are specified in
  `signals/README.md`; `reconcile.py` Check 5 fails a method that is dispatchable but unspecced.
- **`signals.db`** (SQLite, committed): `signals` fact table keyed (pipeline, period, metric_id,
  entity_type, entity_id), plus `ingestion_log` and `llm_cache`. It has a history index and
  runs `ANALYZE` at init; without statistics SQLite ignores the index.
- **Checks:** 2e (`guards/validate_signal_history.py`: schema, continuity, status sync, the
  share-of-net bound, cadence) and 2f (`guards/check_signal_freshness.py`: recompute every period
  listed in `timeline.json` and compare). A source revision means re-appending **every** period.

---

## 7. Rules that hold across pipelines

- **Annotation IDs are permanent.** FOUNDATION may restructure only after
  `promote_annotations.py --dry-run` accounts for every removed ID.
- **Signal IDs are permanent;** the registry holds Layer 1 computed signals only. Layer 2 lives on
  the model and in S3, never as registry entries.
- **Layer 1 always runs;** it is never conditioned on model state.
- **A force needs a verified source** (URL + verbatim excerpt on the page + effective date in force
  for the window). Nothing is auto-promoted.
- **Paid model calls need approval in the current conversation** (`core/llm_budget`).
- Git and deployment rules are in `CLAUDE.md`.

## 8. Adding things

| To add | Use |
|---|---|
| a period (any pipeline) | `/ingest-period` |
| a model pass / sourced forces | `/model-pass`, `/s4-source` |
| a new source (pipeline) | `ARCHITECTURE.md` §"Adding a pipeline"; `/onboard-source` is planned in `PLAN.md` |
| a signal family | spec in `signals/README.md` first, then registry → compute → backfill every period → freshness |
