# Handoff — Engineering Health / Technical-Design Correctness (the non-functional track)

**Framing (Risham, 2026-06-23):** we've optimised for *functional* correctness (does the output trace, is it
fresh, is it aligned). We have **not** systematically addressed *technical* correctness — architecture
legibility, optimality, reusability/structure, understandability, test coverage, design-system coherence.
This is the single authoritative backlog + cadence for that track. None of it is blocking today; it's the work
that keeps the platform scalable and trustworthy as it grows. Active focus is still LinkedIn distribution
(`HANDOFF_2026-06-23.md`); this is the parallel non-functional track. Pairs with [[feedback-design-for-long-term]].

Honest grading (`A`=good, `C`=gap, `F`=absent):

| Dimension | Grade | Reality |
|---|---|---|
| Authoritative architecture | **C** | `PIPELINE_ARCHITECTURE.md` (stage prose) + 49/49 module docstrings exist; **no system-level data-flow diagram, artifact lineage, or module-dependency reference**, no README |
| Unit tests / correctness | **F** | **1 test file, 9 tests** (`tests/test_system_state.py`, S3 only). The deterministic core is untested. Zero web tests (no runner configured) |
| Optimality / performance | **C** | one win shipped (4.6 MB CSV → precompute); **no systematic perf pass**; the gate cold-starts ~20 python subprocesses/run; freshness recomputes ALL periods each commit |
| Structure / reusability | **C** | 49 flat scripts; ingestion/gate layer is copy-per-pipeline → **§4 (the `analysis/` restructure)** |
| Understandability | **B–** | strong module docstrings; gaps: no per-dir READMEs, naming drift (e.g. prop still named `rows` after `AtmPosRow→AtmPosSeries`) |
| Design-system coherence (web) | **C** | DLS exists + shared; SIBC vs payments **have drifted before** (chart components, legend toggles, YoY mode) — needs a recurring audit |

---

## 1. Authoritative end-to-end architecture (build `ARCHITECTURE.md`)

`PIPELINE_ARCHITECTURE.md` says *how stages run*; it is **not** a system-of-record for *how data and modules
connect*. Create a top-level `ARCHITECTURE.md` with: (a) a **data-flow diagram** source→…→UI, (b) an
**artifact-lineage table** (e.g. `consolidated.csv → {signals.db, chart_series.json, system_model}`), (c) a
**module-dependency map** (post-restructure: `core/` ← `pipelines/{name}/`), (d) the **invariants in one
place** (determinism, traceability, single-source, the guards Check 2e/2f/2g/4c/4f and what each enforces),
(e) the **layer model** L1/L2/L3.

**Canonical flow (seed for the diagram — keep this accurate):**
```
raw XLSX → extract → validate → consolidate (CSV = single source)
  → L1 compute (signals.db, deterministic)
  → L1 evaluate (LLM, prompt v1.11, via API)        →  insight annotations (traceable: Check 2g/4c)
  → chart_series.json (compact, web)
  → L2 model (skeleton[det] + behavioral[authored,sourced])
  → S3 dynamic state (signals fire on model, det)
  → opportunities (status from firing) + narrative(LLM)  →  /opportunities (traceable: Check 4f strict)
  → L2b cross-source (ontology hub + composition)
  → S4 inference (proposes sourced forces; manual)
Guards: 2e schema · 2f signals.db freshness · 2g/4c insight traceability · 4f opportunity traceability · derived-fresh
```

## 2. Unit tests for the deterministic core (highest correctness ROI)

The platform's value *is* "deterministic + traceable", yet the compute is unverified except by
consistency-gates (which catch drift, not wrong-from-the-start logic). Add golden/property tests for:
- **`signals/compute/`** methods — `csv_total_yoy`, `csv_streak` (both directions), `csv_total_ratio`,
  `csv_ratio_sum`, category/scan — against a tiny fixture CSV with hand-computed expected values.
- **SIBC date-normalisation** (`update_web_data.py`) — the Apr/May/Mar remap + `date_overrides`. Error-prone,
  currently only human-gated; a wrong remap silently corrupts every downstream number.
- **Traceability validators** — `extract_numbers` (FY-range edge cases like `FY22-24`), matching tolerance,
  the YoY drift guard.
- **`generate_chart_series` + `buildSectionData`** — total/by_type/top_n/individual + MoM/YoY derive, vs a
  fixture (guards the perf-refactor against regressions).
- Runner: keep `pytest` for python; add **Vitest** for web `lib/` pure functions. **Wire `pytest` into the
  gates** (currently `tests/` runs nowhere automatic). Do this **before §4** so it catches migration regressions.

## 3. Optimality / performance pass

- Gate latency: ~20 cold python subprocess starts per run; consider an in-process orchestrator or batching.
- `check_signal_freshness` recomputes every period from CSV on every commit (pre-commit) — fine now, watch as
  periods grow; could scope to changed periods.
- Audit remaining client-side heavy lifting on the web (payments CSV fixed; verify SIBC `data.ts` PapaParse
  stays small; `/opportunities` `section-chart-data.ts`).

## 4. Structure / reusability — the `analysis/` restructure (was a separate handoff; merged here)

**Decision:** the folder structure should mirror the architecture and scale to N pipelines. **Design + prove
it on the 2 existing pipelines now; when source #3 arrives it slots in as config and *validates* the design**
(don't co-change structure + add a source). Everything is git-committed/recoverable. **Execute in a fresh,
full-context session** — it's a 49-file move with path surgery; phase it, verify gates each step, commit in
small batches.

**The real problem (not just folders):** half the architecture is already generic/pipeline-parameterized
(`generate_skeleton --pipeline`, `system_state`, `derive_opportunities`, `chart_series`, `signal_history`,
`run_inference`, `signals/compute/`). The **ingestion + gate layer is copy-per-pipeline**
(`extract_sibc`/`extract_atm_pos`, `run_evals`/`run_atm_pos_evals`, the per-pipeline validators,
`generate_analysis_report`/`generate_atm_pos_analysis_report`) — the one-off pattern the engineering principle
forbids; it grows linearly with sources. **Fix = (1) folder layout reflecting generic-vs-custom, and
(2) converge the one-offs onto a generic gate runner + per-pipeline manifest.**

**Generic vs custom (the key call):**
- *Stays custom, per pipeline (~10%):* the **extractor** (raw XLSX parsing), `skeleton_profile.md`,
  date-normalisation rules, section/insight definitions, the data dir.
- *Becomes generic (one engine, config-driven):* the **gate runner**, traceability/freshness validators,
  consolidation pattern, signals-payload build, insights framework — plus what's already generic.
- A **pipeline manifest** (`pipelines/{name}/pipeline.json`) declares: extractor module, csv path, date column,
  entity/category columns, stages, gate sequence. **Adding a pipeline = manifest + a thin extractor, not 10
  copied scripts.**

**Target structure:**
```
analysis/
  core/          generic engines + the ONE manifest-driven gate runner (gate.py replaces run_*_evals);
                 skeleton · system_model_validate · system_state · opportunities · chart_series ·
                 signal_history · inference · traceability · consolidate · paths.py
  pipelines/
    sibc/        pipeline.json · extract.py · detect_format.py · merge.py · profile.md · sibc validators ·
                 analysis_report.py · promote_annotations.py · backfill_basis.py · timeline.json · merged/ · periods/
    atm_pos/     pipeline.json · extract.py · detect_format.py · consolidate.py · profile.md · validate_data.py ·
                 signals_payload.py · insights.py · insights_validate.py · claims_validate.py · timeline.json · merged/
  signals/       registry.json · signals.db · compute/ · evaluations/ · prompts/ · query · evaluate · db   (mostly unchanged)
  crosssource/   derive_cross_links · compose_ecosystem · validate_composition · opportunities_feed · opportunity_narrative · catalog/composition.json
  ontology/      concepts.json · channels.json   (unchanged)
  guards/        check_signal_freshness · check_derived_fresh · validate_signal_history · git_hooks/
  content/       newsletter/ (incl. LinkedIn)
  legacy/        validate.py · generate_mermaid · source_claims · build_behavioral_layer · migrate_forces_to_instances
```

**Mechanical surface (enumerated, verified 2026-06-23 — small + tractable):**
1. **Path-depth hazard (do FIRST):** ~12 scripts hardcode `ROOT = Path(__file__).resolve().parent.parent`
   (assumes `analysis/x.py`). Any move into a subfolder breaks it. Add `core/paths.py` (resolve repo root by
   walking up to `.git`); every moved script imports `ROOT`/`ANALYSIS` from it. Grep: `parent.parent`, `ANALYSIS = `.
2. **35 subprocess `.py` path-refs in exactly 4 files:** `run_evals.py`, `run_atm_pos_evals.py`,
   `check_derived_fresh.py`, `git_hooks/pre-commit`. (The two run_*_evals become `core/gate.py`.)
3. **Module imports (low coupling):** `import generate_skeleton` (×11 → `from core import skeleton` or a shim),
   `from signals.*` (×5, unaffected), `from validate_sibc_traceability` (×1), `from validate` (×1); ~10
   `sys.path.insert` shims.
4. **Doc refs:** CLAUDE.md, PIPELINE_ARCHITECTURE.md, newsletter/CLAUDE.md, rbi_*/CLAUDE.md, per-period command lists.
5. Output paths unaffected (scripts write to `web/public/data/...` via ROOT-relative → fixed by #1).

**Phased migration (verify gates + diff eval summaries each phase; commit per phase):**
- **P0** `core/paths.py` + repoint the ~12 ROOT scripts (no moves; gates stay green) — de-risks everything.
- **P1** move the already-generic scripts → `core/`/`guards/`/`crosssource/`; update the 4 path-ref files.
- **P2** group per-pipeline scripts under `pipelines/{name}/` (relocation + import/doc updates only).
- **P3** converge the gate: replace `run_*_evals` with one `core/gate.py` driven by each `pipeline.json`;
  prove identical eval-summary output on both pipelines.
- **P4** `legacy/` the retired scripts; tidy docs.
- **Later (source #3):** author only `pipelines/{x}/pipeline.json` + `extract.py`. If it runs end-to-end with
  zero new top-level scripts, the design is validated.

## 5. Understandability

Strong module docstrings already (keep the 100% rule). Add: one **README per top-level dir** (`core/`,
`pipelines/`, `signals/`, `guards/`) stating its contract; a **naming-consistency pass** (rename the `rows`
prop → `series` post-refactor; consistent `*_validate` vs `validate_*`). Also dedupe the near-identical
traceability validators (`validate_sibc_traceability` vs `validate_atm_pos_insights` share
`extract_numbers`/matching — finish the consolidation as part of §4).

## 6. Design-system coherence (web) — needs a CADENCE, not a one-off

The two dashboards share the DLS but drift. Establish a **recurring check (every few days / each web PR):**
- Both pipelines use the same `dls/` primitives, `theme.ts` colours (`pickColor`, `TYPE_COLOR`, accents), card
  shell, insight-card/CTA-strip structure, controls layout, mobile rules (375px), dark mode.
- Chart parity: trend modes, legend-toggle behaviour, highlight/intelligence mode, the Total/series conventions
  stay aligned across SIBC and payments.
- Tooling: the `vercel:react-best-practices` skill + a short DLS checklist in `web/AGENTS.md`; visual-regression
  snapshots once Vitest/Playwright exists.

---

## Recommended order (when this track is picked up)
1. **`ARCHITECTURE.md`** (cheap, high-leverage; do alongside §4 so it documents the target).
2. **Deterministic-core unit tests + wire pytest into the gate** (highest correctness ROI; do **before** §4 so
   it catches migration regressions).
3. **§4 restructure** (reusability/structure) — design on the 2 pipelines, validate with source #3.
4. Perf pass + READMEs + naming.
5. Stand up the **design-coherence cadence** (web).

Schedule these as deliberate quality investment, not squeezed into feature work. Git-revertible, gate-verified.
