# Pipeline Architecture — India Credit Lens

> Single source of truth for the data ingestion, signal, and content generation pipeline.
> Referenced by `CLAUDE.md`. Read this before adding any new report or period.

---

## Architectural Principles

**Separate gates per pipeline.** Each data source (SIBC, ATM/POS, future sources) has its own
eval gate. Pipelines run independently — a new credit file does not block a payments file.

**Identical stage sequence.** Every pipeline follows the same stage numbering and purpose.
Scripts differ per pipeline; stages do not.

**Every layer has two distinct concerns:**

| Layer | Model | Signal evaluation |
|---|---|---|
| 1 | `compute` specs in registry — written once per signal | Every ingestion — algorithmic from consolidated data |
| 2a | `system_model.json` per source — FOUNDATION or UPDATE, rare | Every ingestion — rules from model + L1 outputs |
| 2b | Cross-source model per tuple — after both L2a FOUNDATION | Every ingestion — after both constituent L2a evaluate |
| 3  | `ecosystem_model.json` — authored once, updated ~6 monthly | Every ingestion — rules from model + L2b outputs |

**v4.0 (June 2026) — the Layer 2/3 model is now built and operational.** See `analysis/COMPOSITION_SPEC.md`
v1.0 (extends `SYSTEM_MODEL_SPEC.md` v3.0). It refines the above into **five strata**:

| Stratum | What | Where | Cadence |
|---|---|---|---|
| **S1** structural skeleton | entities + composes_into/reclassifies, URNs, concept_tags | `generate_skeleton.py` → `system_model.json` | deterministic, every ingestion |
| **S2a** causal structure | data-less channels over concepts | **shared hub** `analysis/ontology/{concepts,channels}.json` | authored, rarely changes |
| **S2b** force instances | dated, sourced activations of a channel | `force_instances[]` in `system_model.json` | authored |
| **S3** dynamic state | forces/edges/loops fire from live signals; opportunity status | `generate_system_state.py`, `derive_opportunities.py`, `compose_ecosystem.py` | computed, every ingestion |
| **S4** inference | LLM proposes new channels/instances/cross-edges, gated by sourcing | (next build) | on pattern |

Cross-system composition is **federated** (no monolith): each pipeline maps entities to the shared hub
once; `derive_cross_links.py` derives cross-edges through shared concepts (stock↔flow + shared channel);
`cross_source/composition.json` holds confirmed edges; the combined view is **projected**, never authored.
Both gates (`run_evals.py`, `run_atm_pos_evals.py`) run skeleton-regen + `validate_system_model.py` + S3 +
opportunities each ingestion. Legacy `validate.py` checks 4/5, `validate_claims.py`, `generate_mermaid.py`,
`source_claims.py` are **retired** (detached from the gate).

Model updates and signal evaluation are never conflated. A new period always runs signal
evaluation for all layers where a model exists. Model updates are explicit, separate steps
with their own cadence. If no model exists yet, evaluation is skipped silently and signals
carry `pending` status.

**Presentation is always downstream.** The web dashboard, insight pages, and opportunities
are generated from the final signal layer outputs — not from any intermediate pipeline artifact.

**Newsletter is an exception.** Newsletter generation is not yet standardised to this
architecture. Do not modify newsletter scripts until the signal layer is complete across
all pipelines.

---

## Standard Stage Sequence

Applies to every pipeline. Scripts differ; stage purpose and order do not.

```
[Stage 0]  Format detection
           Compare incoming file structure against prior period
           Gate: must be confirmed clean or changes reviewed before Stage 1

[Stage 1]  Extraction
           Raw file → per-period sections.json (schema-validated, typed)

[Stage 2]  Per-period validation
           Validate extracted data: schema, required series, value ranges, known banks/sectors

[Stage 3]  Consolidation + Merge
           All periods → rbi_sibc_consolidated.csv (long format — single source of truth for charts + signals)
                      + sections_merged.json (time-series, analysis-ready — for Layer 2a model + annotations)
           Both files are produced; the CSV is the canonical data source for signal compute.

[Stage 4]  Layer 1 — signal compute            (every period, always)
           Read compute specs from registry.json
           Compute status + value algorithmically from consolidated data
             SIBC:    reads rbi_sibc_consolidated.csv filtered by csv_date
                      (dataDate → csv_date resolved via timeline.json csv_date field)
             ATM/POS: reads atm_pos_consolidated.csv filtered by report_date
           Write all entity-level rows to signals.db (INSERT OR REPLACE) with period=dataDate
           Refresh metric_ranges in signals.db for all affected metrics
           Update current_status + first_seen in registry.json
           No Claude involvement. No exceptions.

[Stage 5]  Layer 2a — signal evaluate          (every period)
           Load prior period evaluation JSON if it exists (auto-detected from signals.db)
           Inject prior signal narratives into prompt for narrative diff
           Call LLM (claude -p CLI); cache by payload hash + prompt_version
           Write evaluations/{pipeline}/{period}.json
           First period: no diff (no prior eval). Second period onward: diff is automatic.

[Stage 5.5] Analysis report generation     (every period, after Stage 5)
           SIBC:    python3 analysis/generate_analysis_report.py
                    Reads evaluations/sibc/{period}.json + registry.json
                    Maps signals → UI sections via domain + signal-level routing
                    Composes body (observation+direction), implication (inference)
                    Derives title from eval `title` field (v1.5+) or observation
                    Populates effect.highlight from registry.chart_series
                    Writes web/public/data/sibc_l1_annotations.json
           ATM/POS: python3 analysis/generate_atm_pos_analysis_report.py
                    Reads evaluations/atm_pos/{period}.json
                    Updates title/body/implication for layer:1 insights in-place
                    Preserves effect/group/cut/exploreAction (chart-wiring metadata)
                    Writes web/public/data/atm_pos_insights.json

[Stage 6]  Evals gate
           Validates all artifacts produced by Stages 0–5.5:
           data integrity, signal DB consistency, model structure (if present)

[Stage 7]  Presentation promote
           Push validated insights to web (annotations, gaps, opportunities)
           Explicit promotion step — never a direct write
           SIBC: promote_annotations.py merges L1 (from sibc_l1_annotations.json)
                 with L2/L3 (from annotations_merged.ts) at makeSection() time

────────────────────── cross-pipeline boundary ──────────────────────────────────

[Stage X]  Layer 2b — cross-source signal evaluate   (after BOTH pipelines complete Stages 0–7)
           Read cross-source evaluate specs from catalog.json
           Apply rules using L2a outputs from both constituent pipelines
           NOT YET IMPLEMENTED — pending first cross-source model FOUNDATION pass

[Stage Y]  Layer 3 — ecosystem signal evaluate        (after Stage X)
           Apply rules from ecosystem_model.json using L2b outputs
           NOT YET IMPLEMENTED — pending first ecosystem model authoring
```

---

## Model Update Cadence

Model updates are named explicitly and run on their own schedule — they are not part of
the per-period gate. When a model update runs, it must be followed by a full eval gate pass.

### Layer 2a model — per-source system model

**FOUNDATION** — full rebuild. Triggers:
- First-ever period for a new source (always FOUNDATION)
- FY-end period (March file, dataDate April–May) for SIBC
- Equivalent annual anchor period for other sources
- Structural event that changes multiple causal relationships simultaneously

**UPDATE** — additive only. Triggers:
- Any interim period where new nodes or signals emerge
- Never restructure existing nodes/edges in UPDATE mode

**Guard in `_meta`:**
```json
{
  "_meta": {
    "mode": "foundation | update",
    "last_foundation_date": "YYYY-MM-DD",
    "last_updated": "YYYY-MM-DD"
  }
}
```

After any Layer 2a model update:
- Re-run Stage 5 (Layer 2a evaluate) for the current period
- Re-run Stage 6 (evals gate)
- Add `evaluate` specs to registry for any new Layer 2a signals

### Layer 2b model — cross-source model

- FOUNDATION after both constituent sources have completed a FOUNDATION pass
- UPDATE when the cross-source interaction patterns shift materially
- One model per declared tuple in `cross_source/catalog.json`
- Tuple must be declared in catalog before model is authored

### Layer 3 model — ecosystem expert model

- Authored once; updated approximately every 6 months or on a major model release
- Full rebuild each time — no UPDATE mode
- Location: `analysis/ecosystem_model.json`
- Requires strict claim validation before use in signal evaluation
- NOT YET IMPLEMENTED

### Mermaid generation (SIBC — on-demand)

`generate_mermaid.py` is not part of the per-period gate. Run it:
- Always after a Layer 2a FOUNDATION pass
- After an UPDATE pass only if new nodes or edges were added
- Check node/edge count before and after UPDATE to decide

---

## Signal Layer Architecture

### Registry — universal signal catalog

`analysis/signals/registry.json` is the single catalog for all signals across all pipelines.
Signal IDs are immutable once created. Add signals; never rename or delete.

Every signal carries:
- `layer` — 1, 2, or 3
- `sub_layer` — `"1a"` | `"1b"` | `"1c"` (Layer 1 only)
- `pipeline` — which source owns this signal
- `type` — `data` (observable) or `inference` (derived) or `insight` (narrative)
- `compute` — required for all `layer: 1` signals; defines algorithmic derivation
- `evaluate` — required for all `layer: 2` and `layer: 3` signals once model exists

**Layer 1 sub-layers:**
- `1a` — aggregate scalars from total rows (YoY, ratios, shares, spreads)
- `1b` — composition scalars across natural data boundaries (sector share, category breakdown)
- `1c` — full entity scans — one row per entity (all banks, all industry types, all categories)
  Entity rows stored in DB with entity_type / entity_id. No filtering in compute layer —
  analysis layer extracts top-N / directional / outlier observations via DB queries.

**Layer 1 `compute` spec — SIBC** (reads `rbi_sibc_consolidated.csv`, period resolved via `csv_date`):
```json
"compute": {
  "method": "csv_sector_yoy",
  "code": "III",
  "statement": "Statement 1",
  "status_rules": [
    { "if": "value > prev_value and value > 0", "then": "strengthening" },
    { "if": "value > 0",                        "then": "active" },
    { "if": "true",                             "then": "declining" }
  ]
}
```

Params: `code` = CSV sector code (e.g. "I", "III", "1", "2.1", "4.8", "i" for PSL).
`statement` = "Statement 1" (main sectors, PSL) or "Statement 2" (industry by type).
`parent_code` = required for `csv_sector_share` and scan methods.
`is_psl: true` = filters `is_priority_sector_memo=True` rows.

SIBC compute methods: `csv_sector_yoy` | `csv_sector_abs` | `csv_sector_share` |
`csv_sector_yoy_spread` | `csv_sector_count_positive_yoy` |
`csv_sector_scan_yoy` | `csv_sector_scan_share` | `csv_psl_scan_yoy`

**Layer 1 `compute` spec — ATM/POS** (reads atm_pos_consolidated.csv):
```json
"compute": {
  "method": "csv_bank_scan",
  "metric": "debit_cards",
  "value_type": "value"
}
```

ATM/POS compute methods: `csv_total_yoy` | `csv_total_ratio` | `csv_ratio_sum` | `csv_sum_yoy` |
`csv_category_share` | `csv_category_yoy` | `csv_category_scan_share` | `csv_bank_scan`

**Layer 2a `evaluate` spec** — reads from Layer 1 DB outputs:
```json
"evaluate": {
  "requires": ["psl-msme-structural-acceleration", "micro-small-growth-tripled"],
  "rules": [
    { "if": "psl-msme-structural-acceleration == 'strengthening' and micro-small-growth-tripled in ['active', 'strengthening']", "then": "active" },
    { "if": "psl-msme-structural-acceleration == 'weakening'", "then": "weakening" },
    { "if": "true", "then": "absent" }
  ]
}
```

### DB — primary signal store

`analysis/signals/signals.db` — SQLite, single file for all pipelines.

**`signals` table** — fact table, one row per (pipeline, period, metric_id, entity_type, entity_id):
- `entity_type`: `aggregate` | `bank` | `bank_category` | `industry_type` | `section_series` | `loan_type` | `psl_category`
- `entity_id`: `total` for aggregates; entity name for 1c scans
- `value`: computed numeric value (NULL for signals without numeric output)
- `status`: result of status_rules evaluation

**`metric_ranges` table** — min/max/mean/p25/p75 per metric, refreshed after every append.
Used by analysis layer to understand where the current value sits in historical context.

**`ingestion_log` table** — one row per append run; tracks metric_count and row_count.

Current state (June 2026):
- SIBC: 28 compute signals × 3 periods = 254 rows
- ATM/POS: 22 compute signals × 6 periods = 874 rows (includes full bank-level 1c scans)

**Status values:** `new` | `active` | `strengthening` | `weakening` | `reversed` | `absent` | `unknown` | `pending`

### Validator — Check 2e

`validate_signal_history.py` enforces:
- A: registry.json schema — required fields, valid statuses, known pipelines/domains
- B: signals.db integrity — tables present, L1 metrics have rows (continuity), no orphaned metric_ids,
     metric_ranges populated, registry current_status matches latest DB row per L1 signal

---

## SIBC Pipeline

**Gate:** `python3 analysis/run_evals.py`
**Source:** RBI Sector/Industry-wise Bank Credit (monthly XLSX)
**Cadence:** Monthly

### Date normalization rules (update_web_data.py)

RBI publishes Statement 1 (Bank Credit / Food Credit / Non-food Credit) as a fortnightly
release. The publication date is always a Friday — which can fall in the first week of the
**following** month. These must be remapped to the prior month-end. Two rules are baked into
`_canonical_month_end`; specific dates are also captured in `{period}/date_overrides.json`.

| Publication date | Maps to | Mechanism | Reason |
|---|---|---|---|
| Apr 1–7 | Mar 31 | normalization rule | Post-FY-end Bank Credit release |
| May 1–7 | Apr 30 | normalization rule | Post-April Bank Credit release |
| Mar 1–7 | Feb 28/29 | `date_overrides.json` in the Feb/Mar period dir | Early-March Bank Credit = Feb data |
| All other dates | last day of same month | normalization fallback | Mid-month sector snapshots |

**Always ask for confirmation before `update_web_data.py` writes the CSV.**
Show the full remapping table (overrides + normalization) and wait for explicit sign-off.

### Scripts per stage

| Stage | Script | Output |
|---|---|---|
| 0 | `detect_format.py` | `{period}/format_report.json` |
| 1 | `extract_sibc.py` | `{period}/sections.json` |
| 2 | `validate_sections.py` (Check 1) | — |
| 3 | `generate_merge.py` + `update_web_data.py` | `merged/sections_merged.json` + `rbi_sibc_consolidated.csv` |
| 4 | `generate_signal_history.py append --pipeline sibc` | `signals/signals.db` + registry update |
| 5 | `generate_signal_history.py evaluate --pipeline sibc` | `signals/evaluations/sibc/{period}.json` |
| 6 | `run_evals.py --period merged --merged` | — |
| 7 | `promote_annotations.py` | `web/lib/reports/rbi_sibc.ts` |

### Layer 2a model — SIBC system model

Location: `analysis/rbi_sibc/merged/system_model.json`
Status: **Live** — updated to Mar 2026 (FOUNDATION pass complete)

FOUNDATION trigger: March year-end file (`is_fy_end: true` in timeline.json)
UPDATE trigger: Interim months where new signals emerge

After any model update: run `source_claims.py` → run Stage 6 → run promote.

### Per-period folder (minimal)

```
rbi_sibc/{YYYY-MM-DD}/
    ├── sections.json        ← Stage 1 output
    ├── format_report.json   ← Stage 0 output
    └── delta_brief.md       ← Lightweight Claude delta (150–200 words)
```

`delta_brief.md` structure:
```markdown
## Period
{month} {year} | dataDate: {YYYY-MM-DD} | vs prior: {prev_period}

## What moved
- 2–4 bullet observations on what changed vs prior period

## Data quality flags
- Any format anomalies, null series, reclassification effects

## Signal watch
- Which Layer 1 signals are showing movement worth watching
```

No system_model, subsystems, annotations_draft, or mermaid output in per-period folders.

### timeline.json schema

```json
{
  "report_id": "rbi_sibc",
  "periods": [
    {
      "period":           "Mar 2026",
      "dataDate":         "2026-04-30",
      "is_fy_end":        true,
      "total_credit_lcr": 213.6,
      "yoy_growth_pct":   16.1,
      "fy_growth_pct":    16.1,
      "paths": {
        "sections":      "rbi_sibc/2026-04-30/sections.json",
        "format_report": "rbi_sibc/2026-04-30/format_report.json",
        "delta_brief":   "rbi_sibc/2026-04-30/delta_brief.md"
      }
    }
  ],
  "merged": {
    "sections":     "rbi_sibc/merged/sections_merged.json",
    "system_model": "rbi_sibc/merged/system_model.json",
    "subsystems":   "rbi_sibc/merged/subsystems.json",
    "annotations":  "rbi_sibc/merged/annotations_merged.ts"
  }
}
```

---

## ATM/POS Pipeline

**Gate:** `python3 analysis/run_atm_pos_evals.py`
**Source:** RBI ATM/Acceptance Infrastructure and Card Statistics (monthly XLSX)
**Cadence:** Monthly

### Current state

| Stage | Script | Status |
|---|---|---|
| 0 | `detect_atm_pos_format.py` | ✓ Live |
| 1 | `extract_atm_pos.py` | ✓ Live |
| 2 | `validate_atm_pos.py` | ✓ Live |
| 3 | `consolidate_atm_pos.py` → `atm_pos_consolidated.csv` | ✓ Live |
| 4 | `generate_signal_history.py append --pipeline atm_pos` | ✓ Live — writes to signals.db + registry; 82 signals, 6 periods |
| 5 | Layer 2a evaluate | ⏳ Pending — first FOUNDATION pass on system_model.json required |
| 6 | `run_atm_pos_evals.py` | ✓ Live |
| 7 | Presentation promote | ⏳ Pending — direct write for now |

**ATM/POS Layer 1 compute reads directly from `atm_pos_consolidated.csv`** — no
sections_merged.json needed. All 22 signals have `compute` specs; full bank-level
entity rows stored in signals.db (1c signals store all ~60 banks per period, not top-N).

**`generate_atm_pos_insights.py`** is a Layer 2a artifact (Claude-generated insights)
currently running inside the eval gate. It will move to Stage 5 once the ATM/POS
system_model.json FOUNDATION pass is complete.

### Layer 2a model — ATM/POS system model

Location: `analysis/rbi_atm_pos/merged/system_model.json`
Status: **Pending** — first FOUNDATION pass required

Directory `analysis/rbi_atm_pos/merged/` exists. Author system_model.json after at least
one full fiscal year of ATM/POS data is available.

---

## Cross-Pipeline Stages

These run after both SIBC and ATM/POS have completed Stages 0–7 for the same period.
They are not gated on each other — if only one pipeline has a new period, cross-pipeline
stages still run using the latest available data from each source.

### Layer 2b — cross-source signal evaluate

**Catalog:** `analysis/cross_source/catalog.json`
**Status:** Not yet implemented — no cross-source model exists

Declared tuples:

| Tuple | Sources | Interaction |
|---|---|---|
| `sibc_x_atm_pos` | SIBC × ATM/POS | personalLoans ↔ credit_cards, debit_cards |

To activate a tuple:
1. Author `analysis/cross_source/{tuple_id}/system_model.json` (FOUNDATION pass)
2. Add `evaluate` specs to all Layer 2b signals in registry
3. Set `status: "active"` in catalog entry
4. Wire `generate_signal_history.py evaluate --pipeline cross:{tuple_id}` into cross-pipeline gate

### Layer 3 — ecosystem signal evaluate

**Location:** `analysis/ecosystem_model.json` (does not yet exist)
**Status:** Not yet implemented

The ecosystem model is Claude's structured understanding of the Indian lending ecosystem —
risk transmission, NBFC vs bank dynamics, policy effects on credit cycles, collections
behaviour. It is not derived from any single ingested data source. It provides the
"for lenders" interpretive layer that sits above all pipeline-specific signals.

**Authoring cadence:** Once, then updated approximately every 6 months or on a major
model release. Always a full rebuild — no UPDATE mode.

**Claim validation:** Every claim in ecosystem_model.json must pass `validate_claims.py`
before it is used in any signal evaluation or presentation output.

---

## Key Rules

### Annotation IDs are permanent
An `id` in `annotations_merged.ts`, once created, is never renamed or deleted.
UPDATE mode may add new IDs. FOUNDATION mode may restructure — but before promoting,
run `promote_annotations.py --dry-run` and explicitly account for every removed ID.
`annotation_ids` in `system_model.json` must exactly match `id` fields in the annotations file.

### Signal IDs are permanent
A signal `id` in `registry.json`, once created, is never renamed or deleted.
Signals tagged `layer: 2` or `layer: 3` are preserved in the registry even before their
evaluation layer is implemented — they carry `pending` status in history until then.

### Stage 3 self-validates
`generate_merge.py` auto-runs `validate_sections.py --merged` after writing.
If post-merge validation fails, the script exits 1 and Stage 4 must not run.

### Layer 1 always runs — no exceptions
If Stage 3 produces a valid `sections_merged.json`, Stage 4 always runs.
Layer 1 signal evaluation is not optional, not skippable, not conditioned on model state.

### Layer 2a evaluate ≠ Layer 2a model update
Running Stage 5 (Layer 2a evaluate) every period is mandatory when a model exists.
Updating `system_model.json` (FOUNDATION or UPDATE) is a separate, explicitly triggered step.
Never conflate the two.

### Promotion is automated, never manual
`promote_annotations.py` verifies annotation IDs match before and after write.
Never copy `annotations_merged.ts` → `rbi_sibc.ts` manually.

### Git / deployment
- Work directly on `main` — solo project, no feature branches
- Never auto-push to GitHub
- Always run full evals (including build) before `git push`
- Commit per-period outputs, merged outputs, and web/ separately

---

## Adding a New Period

### SIBC — interim period (UPDATE mode)

```
□  Place xlsx in analysis/rbi_sibc/{dataDate}/raw/
□  python3 analysis/detect_format.py {xlsx}
   — review format_report.json; confirm before proceeding
□  python3 analysis/extract_sibc.py {xlsx}
□  python3 analysis/update_web_data.py
□  Update timeline.json — add period entry, is_fy_end: false
□  Claude: delta_brief.md  (150–200 words; see structure above)
□  python3 analysis/run_evals.py --period {dataDate} --skip-build
   (Checks 0, 0.5, 1, 1b — data integrity only)
□  python3 analysis/generate_merge.py
□  python3 analysis/generate_signal_history.py append --pipeline sibc --period {dataDate}
   (Stage 4 — Layer 1 always runs here)
□  python3 analysis/generate_signal_history.py evaluate --pipeline sibc --period {dataDate}
   (Stage 5 — LLM signal evaluate; always runs every period)
□  python3 analysis/generate_analysis_report.py
   (Stage 5.5 — generate sibc_l1_annotations.json for UI from eval output)
□  READ rbi_sibc/merged/system_model.json — is a model UPDATE warranted?
   If yes (new signals, material pattern shift): run Layer 2a model UPDATE pass
   — update stats in existing nodes, add new nodes only for genuinely new signals
   — set _meta.mode = "update", bump _meta.last_updated
   — python3 analysis/source_claims.py rbi_sibc/merged/system_model.json
   — python3 analysis/generate_mermaid.py (only if new nodes/edges added)
□  python3 analysis/run_evals.py --period merged --merged --skip-build
□  python3 analysis/promote_annotations.py --dry-run
□  python3 analysis/promote_annotations.py
□  python3 analysis/run_evals.py --period merged --merged
□  Commit per-period → merged → web/ separately
□  git push
```

### SIBC — FY-end period (FOUNDATION mode)

```
□  All steps above through generate_merge.py + Stage 4 signal append
□  Confirm: is_fy_end true? dataDate April–May? Full fiscal year visible?
   If not certain, treat as UPDATE.
□  Layer 2a model FOUNDATION pass:
   — full rebuild of system_model.json from sections_merged.json
   — set _meta.mode = "foundation", _meta.last_foundation_date = dataDate
   — full rebuild of subsystems.json
   — full rewrite of annotations_merged.ts (ID guard applies — see Key Rules)
   — python3 analysis/source_claims.py rbi_sibc/merged/system_model.json
□  python3 analysis/generate_signal_history.py evaluate --pipeline sibc --period {dataDate}
   (re-run Stage 5 after model rebuild)
□  python3 analysis/run_evals.py --period merged --merged --skip-build
□  python3 analysis/generate_mermaid.py rbi_sibc/merged/system_model.json
□  python3 analysis/promote_annotations.py --dry-run  (REVIEW every removed ID)
□  python3 analysis/promote_annotations.py
□  python3 analysis/run_evals.py --period merged --merged
□  Commit per-period → merged → web/ separately
□  git push
```

### ATM/POS — new period

```
□  Place xlsx in analysis/rbi_atm_pos/incoming/
□  python3 analysis/run_atm_pos_evals.py --xlsx {file}
   (Stages 0–3: format detection, extraction, validation, consolidation)
□  python3 analysis/generate_signal_history.py append --pipeline atm_pos --period {YYYY-MM-DD}
   (Stage 4 — Layer 1: writes all signals to signals.db + updates registry)
□  python3 analysis/generate_signal_history.py evaluate --pipeline atm_pos --period {YYYY-MM-DD}
   (Stage 5 — LLM signal evaluate)
□  python3 analysis/generate_atm_pos_analysis_report.py
   (Stage 5.5 — update atm_pos_insights.json L1 content from eval output)
□  [Stage 5 — Layer 2a evaluate: NOT YET WIRED — generate_atm_pos_insights.py runs inside
   gate for now; will move to Stage 5 after ATM/POS system_model.json FOUNDATION pass]
□  Commit per-period → web/ separately
□  git push
```

---

## Annotation Migration Strategy

Annotations in `annotations_merged.ts` were authored before the signal compute layer existed.
Migration to computed output is layer-by-layer — the file is NOT retired until all three
layers have compute coverage.

### Principle
Do not do a big-bang replacement. Each layer migrates independently when its compute is ready.
The `layer` field on each annotation is the marker that controls which annotations are
authored vs auto-computed.

### Migration steps (in order)

**Step 1 — Tag annotations (prerequisite for everything else)**
Add `layer: 1 | 2 | 3` to every annotation object in `annotations_merged.ts`.
Metadata-only — no content change. Run `promote_annotations.py` after.

**Step 2 — Build `generate_analysis_report.py` formatter**
Reads `evaluations/{pipeline}/{period}.json`, outputs annotation-shaped objects for
`layer: 1` signals only. Does not touch layer 2/3 entries.

**Step 3 — Wire layer 1 to computed output**
Replace body/content of `layer: 1` annotations with formatter output each period.
Layer 2/3 annotations remain authored and unchanged.

**Step 4+ — Layer 2/3 compute (future)**
When L2 compute is built → retire authored layer 2 annotations.
When L3 compute is built → retire authored layer 3 annotations.
When all layers computed → retire `annotations_merged.ts` entirely.

### UPDATE pass scoping
The Layer 2a model UPDATE pass continues each period, but its scope narrows as layers migrate:
- Pre-Step 3: UPDATE pass authors all annotations
- Post-Step 3: UPDATE pass only refreshes `layer: 2` annotations (layer 1 auto-computed)
- Layer 3: unchanged each period (~6-monthly cadence regardless)

### Known annotation reclassifications
These annotations were initially classified as L1 but must remain L2 (authored):
- `psl-housing-anomalous-surge` — the 39.8% YoY surge is a regulatory reclassification
  artifact (RBI Oct 2024 PSL limit revision), not real demand. Computed signal inference
  gets this wrong. Requires authored causal framing.

### Known signal gaps (fix before replacing those annotations)
- `computer-software-multi-year-surge` and `transport-operators-decelerating` both map to
  `sibc-services-yoy-scan` which emits one merged narrative — transport doesn't appear.
  Fix: scan signals need per-entity evaluation output before these can be replaced.

---

## Directory Structure

```
analysis/
├── rbi_sibc/
│   ├── timeline.json               ← Registry of all ingested periods
│   ├── merged/
│   │   ├── sections_merged.json    ← Stage 3: combined time-series (source for L1 compute)
│   │   ├── system_model.json       ← Layer 2a model (living doc — FOUNDATION or UPDATE)
│   │   ├── subsystems.json         ← Subsystem map (append-only in UPDATE)
│   │   ├── annotations_merged.ts   ← Draft annotations (→ web via promote_annotations.py)
│   │   ├── insights.md
│   │   ├── gaps.md
│   │   └── opportunities.md
│   └── {YYYY-MM-DD}/
│       ├── sections.json
│       ├── format_report.json
│       └── delta_brief.md
│
├── rbi_atm_pos/
│   ├── timeline.json
│   ├── canonical_banks.json
│   ├── merged/
│   │   └── system_model.json       ← Layer 2a model (pending — first FOUNDATION pass needed)
│   └── {YYYY-MM-DD}/
│       ├── format_report.json
│       └── sections.json
│
├── cross_source/
│   ├── catalog.json                ← Tuple registry — all declared cross-source pairs
│   └── {tuple_id}/
│       └── system_model.json       ← Layer 2b model per tuple (pending)
│
├── signals/
│   ├── registry.json               ← Universal signal catalog (90 signals, layer/compute/evaluate specs)
│   ├── signals.db                  ← PRIMARY store — SQLite fact table (pipeline × period × metric × entity)
│   ├── db.py                       ← DB init, schema, refresh_ranges()
│   ├── migrate_to_db.py            ← One-time migration script (historical — no longer needed)
│   ├── update_registry.py          ← One-time script: added sub_layer + compute specs to registry
│   ├── compute/
│   │   ├── engine.py               ← Dispatch: reads registry, calls sibc/atm_pos, writes DB
│   │   ├── sibc.py                 ← SIBC compute methods (1a/1b/1c/1d) — reads consolidated CSV
│   │   └── atm_pos.py              ← ATM/POS compute methods (1a/1b/1c/1d) — reads CSV
│   └── evaluations/
│       ├── sibc/                   ← LLM evaluation JSONs per period (observation/direction/inference)
│       └── atm_pos/                ← LLM evaluation JSONs per period
│
├── output/
│   └── mermaid/rbi_sibc/{YYYY-MM-DD}/   ← On-demand mermaid diagrams
│
├── run_evals.py                    ← SIBC gate (Stages 0–6)
├── run_atm_pos_evals.py            ← ATM/POS gate (Stages 0–6)
├── extract_sibc.py                 ← Stage 1 SIBC
├── extract_atm_pos.py              ← Stage 1 ATM/POS
├── detect_format.py                ← Stage 0 SIBC
├── detect_atm_pos_format.py        ← Stage 0 ATM/POS
├── update_web_data.py              ← Stage 3 SIBC (CSV consolidation)
├── consolidate_atm_pos.py          ← Stage 3 ATM/POS (CSV consolidation)
├── generate_merge.py               ← Stage 3 SIBC (sections_merged.json)
├── generate_signal_history.py      ← Stage 4 + Stage 5: append | evaluate | status | seed
├── source_claims.py                ← Post-model-update: claim sourcing for system_model.json
├── promote_annotations.py          ← Stage 7 SIBC: verified copy to web
├── generate_mermaid.py             ← On-demand: system_model → .mmd diagrams
│
├── validate_timeline.py            ← Check 0
├── validate_sections.py            ← Check 1
├── validate_annotations.py         ← Check 3
├── validate_content.py             ← Check 2b
├── validate_claims.py              ← Check 2c
├── validate_annotation_basis.py    ← Check 2d
├── validate_signal_history.py      ← Check 2e
├── validate.py                     ← Checks 4, 5
│
├── report_analysis_prompt.md       ← Master prompt for all Claude analysis passes
│
└── newsletter/                     ← Exception — not yet standardised to this architecture
    ├── CLAUDE.md
    └── ...

web/
└── lib/reports/
    └── rbi_sibc.ts                 ← Live annotations (promoted from merged)

web/public/data/
    ├── rbi_sibc_consolidated.csv
    ├── atm_pos_consolidated.csv
    └── atm_pos_insights.json       ← Layer 2a output (will move to promotion step)
```

---

## Skills (load on demand)

| Skill | When to invoke |
|---|---|
| `/per-period-analysis` | Stage 2 delta_brief.md for a new period (~150 words) |
| `/merged-analysis` | Layer 2a model UPDATE or FOUNDATION pass — check `is_fy_end` first |
| `/add-new-report` | Full walkthrough: adding a new SIBC period end-to-end |
