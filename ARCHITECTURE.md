# Architecture

Authoritative system of record for *how India Credit Lens is built*: the rationale, the
invariants, and what is and is not generic. It is split deliberately into two halves:

| Half | File | Kind | Maintenance |
|---|---|---|---|
| **Rationale** (this file) | `ARCHITECTURE.md` | Authored prose: *why* | Hand-edited; stable |
| **Structure** | [`ARCHITECTURE.generated.md`](ARCHITECTURE.generated.md) | Derived facts: *what* | **Generated from code**; never hand-edited |

Structural facts that drift (data flow, artifact lineage, gate call graph, module map) are
derived from the code and guarded for freshness. Prose is kept for what does not drift.

Related: `PIPELINE_ARCHITECTURE.md` (the stage sequence, layer by layer), the skills in
`.claude/skills/` (how to run a workflow), `PLAN.md` (what is being built), `DECISIONS.md`
(standing rules). Revised 2026-09-24.

---

## Engineering principle (non-negotiable): design for the long term

The platform is **multi-pipeline by design**; three pipelines are live and the count only grows.
Every decision must scale to N ingestion types and N pipelines:

- **One generic mechanism per pipeline, not per-pipeline one-offs.**
- **Compute once, ship compact.** Precompute at build time; the browser never parses raw
  consolidated data, re-derives series, or formats a number.
- **Single source of truth.** No parallel copies that "agree today but could drift"; guard with a
  deterministic freshness or traceability check.
- Given "quick win vs proper fix", **default to the proper fix.**

---

## Invariants (what the guards exist to protect)

1. **Determinism.** Layer 1 compute, the model skeleton, S3 state, opportunity firing, tables,
   the state band and chart series are deterministic functions of the consolidated CSV and the
   authored model. The same input always yields the same output.
2. **Traceability.** Every number a reader sees traces to a computed value, scoped to what that
   surface declares it reads. LLMs narrate grounded numbers; they never invent them.
3. **Single source of truth.** One consolidated CSV per pipeline; one signal store (`signals.db`).
4. **Freshness.** Derived artifacts are stale until proven fresh: every commit re-derives the
   deterministic chain, and `signals.db` is recomputed row by row.
5. **Legibility.** The architecture is discoverable from code; docs, skills and settings are
   validated against it, not trusted.

## Guards

Every gate stage is listed, with its producing script, in `ARCHITECTURE.generated.md` §2.

| Guard | Enforces | What it checks |
|---|---|---|
| `guards/validate_signal_history.py` (2e) | single source | registry schema, DB continuity, status sync, the share-of-net bound, cadence |
| `guards/check_signal_freshness.py` (2f) | freshness | recompute every period in `timeline.json` from the CSV; fail on any drift |
| `pipelines/sibc/validate_sibc_traceability.py` (2g) | traceability | SIBC card numbers → the card's declared signals |
| `pipelines/atm_pos/validate_atm_pos_insights.py` (4c) | traceability | payments card numbers → `signals.json` / `signals.db`, plus a YoY drift guard |
| `guards/validate_card_cuts.py` (5.7) | legibility | the chart under a card answers the card's question |
| `guards/validate_card_prose.py` (5.8) | trust | no advice, forecasts or banned register in dashboard prose |
| `guards/validate_state_band.py` (5.9b), cut-table check (5.9d) | traceability | band and table numbers, scoped per entity, per column, per period |
| `core/validate_opportunity_traceability.py` (4f) | traceability | opportunity numbers → the driver's full evidence set |
| `core/validate_system_model.py` | structure | skeleton, structure discipline, force sourcing |
| `guards/check_derived_fresh.py` (pre-commit) | freshness | regenerate the manifest-declared derived artifacts; fail on drift |
| `architecture/reconcile.py` (5) | legibility | script paths exist exactly; skills/settings run no retired script; counts; evidence pointers; every compute method specced; context budget |
| `core/llm_budget.require_approval` | cost | no paid call without per-run approval and an estimate; $5 ceiling |

---

## Layer model

- **Layer 1: computable from the CSV alone.** Rates, shares, sizes, movement, scans. No LLM in
  compute; the LLM only narrates card prose.
- **Layer 2: crosses data boundaries.** The causal graph (`system_model.json`: deterministic
  skeleton + authored, sourced behavioral layer) → S3 maps live signals onto it → mix states and
  opportunity status. L2b composes across pipelines through the ontology hub.
- **Layer 3: lending-workflow implications.** The ecosystem meta-model (constructs, eco-edges,
  cross-pipeline loops, reconciliation constraints) is live and projected every ingestion. The
  authored strategic layer on top of it is not built.

The end-to-end flow with exact scripts is in `ARCHITECTURE.generated.md` §1; the stage order and
its reasons are in `PIPELINE_ARCHITECTURE.md`.

---

## Adding a pipeline: what is generic, and what is not

Measured 2026-09-16 against a third pipeline, then tested by building it (NBFC, 2026-09-22/23).
**The data layer generalised; the plumbing and presentation had to be made to.**

### Generic: a new pipeline inherits these

| | how it generalises |
|---|---|
| the gate | manifest-driven; a pipeline is a `pipeline.json`, not a script |
| pipeline ids | `manifest.discover_pipeline_ids()`, ordered by a declared `order` (both pipelines write the shared feed, so order matters); a test bans the literal pair. `pipelines_with_stage()` gives checks the population they want |
| compute | a module is a **shape**, not a pipeline. `csv_sector.py` = one measure over a code hierarchy (SIBC, NBFC); `atm_pos.py` = many measures over shared entities. Optional columns are declared in `schema` and verified on load |
| L1 cut tables | discovered from the registry (40+ cuts, none listed) |
| the state band | derived from the cuts that have a mix state |
| Layer 2 mix states | join on a momentum signal's `parent_code`: a new cut gets a causal reading with zero authoring (NBFC got three) |
| traceability | one validator per concern, `--pipeline` argument, scope read off the artifact's own declarations |
| cadence | declared per signal, so a quarterly source needs no code |
| web | one `Pipeline` type; an adapter declares its dimensions (NBFC's is ~70 lines) |

### Not generic (yet)

| | state |
|---|---|
| **card generator** | per pipeline: SIBC ~750 LOC, payments ~2,100. NBFC deliberately has none. **Open fork:** build a generic card path, or decide cards stay per-pipeline and the table + band is the generic L1 surface (which NBFC shows is viable). Decide from the post-NBFC count in `PLAN.md` |
| **`MOVEMENT_CUTS`** | still a hand-written table per pipeline for movement *cards* (the band no longer reads it) |
| **SIBC timeline registration** | by hand; the other two pipelines' consolidate step registers the period |
| **a new ingestion type** | every source so far is a downloaded XLSX. An API pull (MoSPI) or a PDF table is the next capability to pay for once |

---

## Architecture tooling (`analysis/architecture/`)

```bash
python3 analysis/architecture/discover.py   # code → graph.json (imports, call graph, lineage)
python3 analysis/architecture/render.py      # graph.json → ARCHITECTURE.generated.md
python3 analysis/architecture/reconcile.py   # validate living docs, skills and settings (--strict gates)
```

`discover.py` is static analysis (AST imports + subprocess call graph, exact; artifact IO lineage,
heuristic). The manifests' `derived` declarations are the authoritative record of what each stage
rewrites; lineage is a cross-check.

---

## Platform components

Status of what is live. History is in git; plans are in `PLAN.md`.

| Component | Where | State |
|---|---|---|
| SIBC pipeline + dashboard `/` | `pipelines/sibc/`, `rbi_sibc/` | live: 24 periods; tables, band, 96 generated cards + 26 hand-written annotations |
| Payments pipeline + `/payments` | `pipelines/atm_pos/`, `rbi_atm_pos/` | live: 31 periods, 63 banks, 26 measures with bank breakouts |
| NBFC pipeline + `/nbfc` | `pipelines/nbfc/`, `rbi_nbfc/` | live: 11 dates; tables + band, no cards |
| Signal store | `signals/registry.json` (Universal signal catalog — 570 signals), `signals/signals.db` | live; L1 computed only |
| Movement + mix states | `csv_*_momentum/acceleration/allocation`; `generate_system_state.mix_states` | live on every cut; coherence routes the sentence, never gates |
| Card narration | `signals/evaluate.py`, prompt `signals/prompts/domain_eval_system.txt` | live, paid, per-run approval |
| System models + S3 | `rbi_*/merged/system_model.json`, `core/generate_system_state.py` | live for all three pipelines |
| S4 inference + sourcing | `core/run_inference.py`, `distribution/bank_sourcing.py`, `guards/audit_force_sources.py` | live; Chrome is the primary sourcing channel |
| Cross-system | `ontology/`, `cross_source/`, `cross/` | live: composition, ecosystem projection, opportunities feed (Deep view disabled on the dashboard) |
| Distribution | `distribution/` (slots, monthly issue, deep read) | built and gated; **paused** |
| Agent layer | `.claude/skills/`, `.claude/settings.json`, `PLAN.md`, `DECISIONS.md` | skills live; guarded by reconcile Checks 6–7 |

## Where things live

| Area | Entry points |
|---|---|
| Gate + generic engines | `core/gate.py`, `core/manifest.py`, `core/generate_signal_history.py` (append / evaluate / status) |
| Per-pipeline modules | `pipelines/{sibc,atm_pos,nbfc}/` — each with its `pipeline.json` |
| Compute | `signals/compute/{engine,csv_sector,atm_pos,common}.py`; spec `signals/README.md` |
| Dashboard sidecars | `signals/stamp_{state,planes,table}.py` → `web/public/data/*.json` |
| Guards | `guards/` (freshness, history, card cuts/prose, state band, force-source audit) |
| Layer 2 | `core/{generate_skeleton,validate_system_model,generate_system_state,derive_opportunities,run_inference}.py` |
| Cross-system | `cross/{derive_cross_links,compose_ecosystem,validate_composition,generate_opportunities_feed,generate_opportunity_narrative}.py` |
| Distribution | `distribution/{generate_slot,slot_render,validate_distribution,categories,ledger}.py`, `distribution/issues/` |
| Measurement | `measure_groundedness.py`, `measure_coherence_threshold.py`, `distribution/ai_pm_register.json` |
| Web | `web/components/read/` (shell + one adapter per pipeline), `web/lib/`; context in `web/AGENTS.md` |
| Retired code | `analysis/legacy/` (see its README) |
