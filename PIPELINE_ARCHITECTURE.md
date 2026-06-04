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
           All periods → consolidated CSV  (long format, all periods — for charts)
                      + sections_merged.json (time-series, analysis-ready — for signals)
           This is the single source of truth for all downstream stages.

[Stage 4]  Layer 1 — signal evaluate           (every period, always)
           Read compute specs from registry.json
           Compute status + value algorithmically from sections_merged.json
           Append to signals/history/{pipeline}.json
           No Claude involvement. No exceptions.

[Stage 5]  Layer 2a — signal evaluate          (every period, if model exists)
           Read evaluate specs from registry.json
           Apply rules using Layer 1 history outputs for this period
           Append Layer 2a signal statuses to signals/history/{pipeline}.json
           SKIP silently if system_model.json does not yet exist — signals stay pending.

[Stage 6]  Evals gate
           Validates all artifacts produced by Stages 0–5:
           data integrity, signal history consistency, model structure (if present)

[Stage 7]  Presentation promote
           Push validated insights to web (annotations, gaps, opportunities)
           Explicit promotion step — never a direct write

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
- `pipeline` — which source owns this signal
- `type` — `data` (observable) or `inference` (derived) or `insight` (narrative)
- `compute` — required for all `layer: 1` SIBC data signals; defines algorithmic derivation
- `evaluate` — required for all `layer: 2` and `layer: 3` signals once model exists

**Layer 1 `compute` spec** — reads from `sections_merged.json`:
```json
"compute": {
  "method": "series_yoy",
  "section": "bankCredit",
  "series": "Non-food Credit",
  "status_rules": [
    { "if": "value > prev_value and value > 10", "then": "strengthening" },
    { "if": "value > 10",                        "then": "active" },
    { "if": "value > 0",                         "then": "weakening" },
    { "if": "true",                              "then": "reversed" }
  ]
}
```

Compute methods: `series_yoy` | `series_abs` | `series_share` | `count_positive_yoy` |
`is_max_series` | `is_min_series` | `abs_undercount` | `yoy_spread` | `static_active`

**Layer 2a `evaluate` spec** — reads from Layer 1 signal history:
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

Signals without an `evaluate` spec carry forward their last known status — they do not
reset to `pending` on every period. Claude assigns status during the model update pass;
the registry spec formalises it for subsequent periods.

### History — append-only per-pipeline

`analysis/signals/history/{pipeline}.json` — one entry per ingested period.

```json
{
  "_meta": { "pipeline": "sibc", "schema_version": "1.0", "entry_count": 2 },
  "entries": [
    {
      "period": "YYYY-MM-DD",
      "appended_at": "ISO8601",
      "signals": {
        "<layer-1-signal>": { "status": "active",  "value": 17.1 },
        "<layer-2-signal>": { "status": "active" },
        "<unimplemented>":  { "status": "pending" }
      }
    }
  ]
}
```

Layer 1 entries always carry `value` (numeric). Layer 2+ carry `status` only.
`pending` means the layer's model does not yet exist for this pipeline.

**Status values:** `new` | `active` | `strengthening` | `weakening` | `reversed` | `absent` | `unknown` | `pending`

### Validator — Check 2e

`validate_signal_history.py` enforces:
- `layer` field present on every signal in registry
- `compute` spec present on every SIBC `layer: 1` data signal
- `value` present in history for every non-`static_active` layer-1 signal
- No orphan signal IDs in history files
- `current_status` in registry matches latest history entry

---

## SIBC Pipeline

**Gate:** `python3 analysis/run_evals.py`
**Source:** RBI Sector/Industry-wise Bank Credit (monthly XLSX)
**Cadence:** Monthly

### Scripts per stage

| Stage | Script | Output |
|---|---|---|
| 0 | `detect_format.py` | `{period}/format_report.json` |
| 1 | `extract_sibc.py` | `{period}/sections.json` |
| 2 | `validate_sections.py` (Check 1) | — |
| 3 | `generate_merge.py` + `update_web_data.py` | `merged/sections_merged.json` + `rbi_sibc_consolidated.csv` |
| 4 | `generate_signal_history.py append --pipeline sibc` | `signals/history/sibc.json` |
| 5 | `generate_signal_history.py evaluate --pipeline sibc` (pending) | `signals/history/sibc.json` (L2a statuses) |
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

### Current state vs target architecture

| Stage | Target | Current state | Gap |
|---|---|---|---|
| 0 | Format detection | `detect_atm_pos_format.py` ✓ | — |
| 1 | Extraction | `extract_atm_pos.py` ✓ | — |
| 2 | Per-period validation | `validate_atm_pos.py` ✓ | — |
| 3 | Consolidation + Merge | CSV ✓ · sections_merged.json ✗ | Need merged JSON for L1 compute |
| 4 | Layer 1 evaluate | Presence/absence only | Need numeric compute specs from CSV |
| 5 | Layer 2a evaluate | Not implemented | `generate_atm_pos_insights.py` (currently in gate) must move here |
| 6 | Evals gate | `run_atm_pos_evals.py` ✓ | Insights generation currently conflated in gate |
| 7 | Presentation promote | Direct write, no promotion step | Need explicit promotion |

**Key structural fix pending:** `generate_atm_pos_insights.py` is a Layer 2a artifact
(Claude-generated insights). It currently sits inside the eval gate as a data stage.
It must be moved to Stage 5 once the Layer 2a architecture is formalised. Until then
it runs as-is — the current web presentation is not affected.

**Layer 1 compute for ATM/POS:** The 21 ATM/POS signals currently have `layer: 1` in the
registry but no `compute` specs. They are derived from presence/absence in insights.json —
which is a Layer 2a output, not a data stage. Once `sections_merged.json` exists for ATM/POS,
proper numeric `compute` specs must be added to the registry for all 21 signals and
`generate_signal_history.py` updated to read from consolidated data.

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
□  IF system_model.json exists AND signals moved materially:
   python3 analysis/generate_signal_history.py evaluate --pipeline sibc --period {dataDate}
   (Stage 5 — Layer 2a evaluate; skip if no change in L1 inputs)
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
   (Stage 4 — Layer 1: currently presence/absence; will be numeric once compute specs added)
□  [Stage 5 — Layer 2a evaluate: NOT YET WIRED — generate_atm_pos_insights.py runs inside
   gate for now; do not move until ATM/POS sections_merged.json and compute specs exist]
□  Commit per-period → web/ separately
□  git push
```

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
│   ├── registry.json               ← Universal signal catalog (layer/compute/evaluate specs)
│   └── history/
│       ├── sibc.json               ← Append-only (L1: values; L2/3: pending or active)
│       └── atm_pos.json            ← Append-only (L1: presence/absence → numeric pending)
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
