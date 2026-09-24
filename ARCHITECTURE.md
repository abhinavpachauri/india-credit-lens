# Architecture

Authoritative system-of-record for *how India Credit Lens is built* — the rationale,
invariants, and layer model. It is split deliberately into two halves:

| Half | File | Kind | Maintenance |
|---|---|---|---|
| **Rationale** (this file) | `ARCHITECTURE.md` | Authored prose — *why* | Hand-edited; stable, doesn't drift |
| **Structure** | [`ARCHITECTURE.generated.md`](ARCHITECTURE.generated.md) | Derived facts — *what* | **Generated from code**; never hand-edited |

This split is itself an application of the platform's #1 engineering principle (below):
structural facts that drift — the data-flow, artifact lineage, gate call-graph, module
map — are **derived from the code that actually runs and guarded for freshness**, never
re-stated in prose that silently rots. Prose is reserved for what *doesn't* drift: the
design intent.

> `PIPELINE_ARCHITECTURE.md` is the *stage-by-stage operating manual* (how to run a period
> through the pipeline). This file is the *system model* (how data and modules connect and
> why). They are complementary.

---

## Engineering principle (non-negotiable) — design for the long term

This platform is **multi-pipeline by design** (SIBC, ATM/POS, future sources). Every
decision must scale to N ingestion types and N pipelines:

- **One generic mechanism per pipeline, not per-pipeline one-offs.**
- **Compute once, ship compact.** Precompute artifacts at build time; the browser never
  parses raw consolidated data or re-derives series.
- **Single source of truth.** No parallel copies that "agree today but could drift" —
  guard with a deterministic freshness/traceability check.
- Given "quick win vs proper fix", **default to the proper fix.**

---

## Invariants (what the guards exist to protect)

1. **Determinism.** Layer 1 compute, the system-model skeleton, S3 state, opportunity
   firing, and chart series are all deterministic functions of the consolidated CSV +
   authored model. The same input always yields the same output.
2. **Traceability.** Every number rendered in an insight, chain, implication, or
   opportunity must trace to a computed value (`signals.db` / `signals.json` / declared
   evidence). LLMs *narrate* grounded numbers; they never invent them.
3. **Single source of truth.** One consolidated CSV per pipeline; one signal store
   (`signals.db`); no parallel recomputation of a value that's already a registered signal.
4. **Freshness.** Derived artifacts are treated as stale until proven fresh — every commit
   re-derives the deterministic chain and fails on drift.
5. **Legibility.** The architecture is discoverable from code; the docs are validated
   against it, not trusted blind.

## Guards (each enforces an invariant — see the gates in `ARCHITECTURE.generated.md` §2)

| Guard | Enforces | What it checks |
|---|---|---|
| `validate_signal_history.py` (2e) | single-source | `signals.db` rows + registry schema + status sync |
| `check_signal_freshness.py` (2f/5b2) | freshness | recompute every period from CSV; fail on any drift |
| `validate_sibc_traceability.py` (2g) | traceability | every number in a SIBC insight traces to `signals.db` |
| `validate_atm_pos_insights.py` (4c) | traceability | ATM/POS analog of 2g (numbers → `signals.json`/db) |
| `validate_opportunity_traceability.py` (4f, strict) | traceability | opportunity numbers → driver's full `evidence_all` |
| `validate_system_model.py` | determinism/structure | skeleton + D1/D2/D3 discipline + force sourcing |
| `check_derived_fresh.py` (pre-commit) | freshness | re-derive the deterministic chain; fail on drift |
| `architecture/reconcile.py` | legibility | living docs' script/artifact refs exist on disk |

---

## Layer model

- **Layer 1 — Computable from the CSV alone.** Algorithmic, runs every period, no LLM for
  compute. Signals in `signals.db`; the LLM only *narrates* them for the insight layer.
- **Layer 2 — Crosses data boundaries.** Causal graph (`system_model.json`: deterministic
  skeleton + authored-and-sourced behavioral layer) → S3 maps live signals onto it → live
  opportunity/risk status → LLM narration. L2b composes across pipelines via the ontology
  hub. Findings = signals mapped onto the model, never independent LLM inference.
- **Layer 3 — Lending-workflow strategic implications.** Authored ~6-monthly; consumes the
  L2a/L2b causal graphs. (Ecosystem model still to be built.)

The canonical end-to-end flow (`raw XLSX → extract → consolidate → L1 compute → evaluate
→ chart series + model → S3 → opportunities → cross-source`) is rendered, with the exact
producing/consuming scripts, in [`ARCHITECTURE.generated.md`](ARCHITECTURE.generated.md) §1.

---

## Adding a pipeline — what is generic, and what is not (measured 2026-09-16)

The engineering principle says every decision must scale to N pipelines. Two are live. This is
what a THIRD (NBFC sectoral deployment is next) would actually cost, counted rather than assumed
— and the split is sharp: **the data layer generalised, the plumbing and the presentation did not.**

### Generic — a third pipeline inherits these for free

| | how it generalises |
|---|---|
| the gate | `core/gate.py` is manifest-driven; a pipeline is a `pipeline.json`, not a script |
| L1 cut tables | `stamp_table` DISCOVERS its cuts from the registry (`csv_*_momentum` → a cut; `csv_bank_scan` + metric → a bank breakout). 40 cuts, none listed |
| the state band | population DERIVED from the cuts that have a mix state (2026-09-15). 43 blocks, none listed |
| table rendering | one `table_rows.build` for both pipelines; columns declared per cut |
| traceability | one validator per concern, `--pipeline` argument, scope read off the artifact's own declarations |
| cadence | declared per signal (2026-09-14), so a quarterly source needs no code |

### NOT generic — what a third pipeline has to add or edit

| | cost |
|---|---|
| ~~the pipeline pair, hardcoded~~ | **CLOSED 2026-09-16.** `manifest.discover_pipeline_ids()` reads the directories that declare a `pipeline.json`, ordered by a declared `order` field (not alphabetically — both pipelines write the shared feed, so name-sorting would reorder who writes last). 21 literal sites removed; a test bans the literal, with two exemptions on the record. `manifest.pipelines_with_stage()` gives guards and tests the population they actually want — *every pipeline that produces this artifact* — so a source that legitimately makes no planes sidecar is not asked for one |
| ~~compute module per pipeline~~ | **CLOSED 2026-09-16.** A module is a SHAPE, not a pipeline: `compute/csv_sector.py` is *one measure over a code hierarchy*, and a manifest declares the shape it is (`compute_module`) instead of the engine branching on the id. The optional columns a source may or may not have — SIBC's `statement` scope and its priority-sector memo lens — are declared in `schema` and VERIFIED against the file on load. NBFC adds a manifest entry, not a module |
| **card generator per pipeline** | 753 LOC (SIBC) and 2,123 LOC (payments) — a third pipeline has no generic path to cards, only two patterns to pick between |
| **web adapter + page per pipeline** | `SibcReadMode` 211 LOC, `AtmReadMode` 230 LOC, plus a route; `"sibc" | "atm_pos"` is a TYPE UNION in 6 lib files, so a third id is a compile error in each |
| **MOVEMENT_CUTS** | still a hand-written table per pipeline. The BAND no longer reads it (derived), but the movement CARDS still do |

### What this means for the next pipeline

**A new source reaches Layer 1 on the dashboard only through work that is per-pipeline today.**
Even with Layer 2 and 3 left switched off — which is the plan for NBFC — the L1 path still needs a
compute module, a card generator, a web adapter and fifteen edits to hardcoded pairs. That is the
gap between "the architecture scales" and "the plumbing scales", and it is worth closing in the
order the third pipeline exposes it, not speculatively:

1. ~~**Pipeline ids from the manifest**~~ — **done 2026-09-16.** Both gates ran end-to-end afterwards with **zero derived artifacts changed**, which is the no-op proof; freshness recomputed 17,809 SIBC and 151,448 payments rows identically.
2. **A schema-declared CSV compute path**, so a SIBC-shaped source is a manifest entry rather than
   a copied module. NBFC is the case that tests it, because it is genuinely SIBC-shaped.
3. **A generic card path**, or an explicit decision that cards stay per-pipeline and the TABLE is
   the generic surface — which after §17–§20 is defensible: the table needs no generator at all.
4. **A pipeline-agnostic web adapter**, driven by the same declarations the tables already carry.

Item 3 is a genuine fork and should be decided, not drifted into: the dashboard's L1 surface is now
the table + the band, both of which are derived. Cards are the news layer, and news may legitimately
stay hand-shaped per source.

---

## Architecture tooling (`analysis/architecture/`)

Architecture-as-code: the structural doc is derived, not written.

```bash
python3 analysis/architecture/discover.py   # code → graph.json (imports, call-graph, lineage)
python3 analysis/architecture/render.py      # graph.json → ARCHITECTURE.generated.md
python3 analysis/architecture/reconcile.py   # validate living docs against code (--strict to gate)
```

- **`discover.py`** — static analysis: AST import graph + subprocess call-graph (authoritative)
  + artifact IO lineage (canonicalized; path-join + variable-binding reconstruction). Layout-
  agnostic (resolves repo root via `.git`), so it survives the planned `analysis/` restructure.
- **`render.py`** — renders the graph to the generated Markdown (data-flow, call-graph,
  lineage table, dep-map, drift findings).
- **`reconcile.py`** — the "docs can't lie" guard: every `*.py` and repo-relative artifact
  path named in a living doc must exist on disk. Forward-references marked "does not yet
  exist"/"planned" are exempt. Advisory today; `--strict` exits non-zero for gate wiring.

**IO lineage is a validator, not the source.** Python builds paths via `/` and f-strings,
so pure derivation of *which artifact* a script writes is necessarily heuristic; the
call-graph and import graph are exact. When the `pipeline.json` manifests land (the §4
restructure), they become the declared source for IO and `discover.py` validates them.

---

## Platform state — component status

Live components only. Planned work lives in `PLAN.md`. Moved here from CLAUDE.md on 2026-09-24 — it describes the system, so it is read on demand rather than loaded every session.

| Component | Status |
|---|---|
| RBI SIBC dashboard | **Live** — 7 sections, 49 annotations (merged Jan 2024–Mar 2026) |
| SEO layer | **Live** — metadata, OG image, sitemap, JSON-LD |
| Email / Substack CTA | **Live** — `SubstackCTA.tsx` + `EmailGate.tsx` |
| Reply desk (X distribution) | **Retired (2026-07-21)** → `analysis/legacy/replydesk/` — distribution serves Substack + LinkedIn; X is reactive and needs its own design. Never used (`reply_log.json` never created in 17 days). Its SEBI guardrail was salvaged into `distribution/slot_render.lint_compliance` (blurbs + design prompts) — it was the only one in the codebase. |
| Long-form / Substack (2-post cadence) | **Live** — folded into `analysis/distribution/` on 2026-07-21 (it is a channel, not a system). Deterministic rendering over gate-validated artifacts: `issues/merged_issue.py` (L1, within 24h of release) + `issues/deep_read.py` (L2/L3 + ecosystem, mid-cycle). Self-gating traceability (`validate_distribution.check_doc`: verbatim cards + **per-block** declared scope — the pooled version measured 0% catch, see the gate docstring). Output = .md + Substack-paste .html. v1 (config/mermaid/LinkedIn) archived to `archive/analysis/newsletter_v1/` — LinkedIn posts are now written by the user in their own voice. |
| validate_content.py (Check 2b) | **Live** — content accuracy eval on annotation bodies |
| validate_claims.py (Check 2c) | **Retired** — superseded by `core/validate_system_model.py` (sourcing built in); archived in `analysis/legacy/` |
| validate_annotation_basis.py (Check 2d) | **Live** — basis completeness check (inference/hypothesis → basis.inferences non-empty) |
| promote_annotations.py (Stage 7) | **Live** — automated verified copy to web |
| signal_registry.json | **Live** — 7 signals tracked across 3 issues (newsletter subsystem) |
| signal compute layer | **Live** — `analysis/signals/` — registry.json (**570 signals**), signals.db (SQLite — sole store); compute engine in signals/compute/; Check 2e validates DB + registry, Check 2f/5b2 verifies DB == fresh recompute from CSV |
| **Movement signals (momentum + acceleration + allocation)** | **Live (2026-08-19)** — 37 L1 signals across **all 7 SIBC cuts + 3 payments cuts** (main sectors, industry by size, industry by type, services, personal loans, priority sector, infrastructure sub-types) (spec: `analysis/signals/README.md`). **Payments is where the regimes actually fire**: credit cards 18/18 aligned, debit cards 12 aligned / 6 contested, POS terminals 12 aligned / 5 contested / **1 handover** (coherence **0.120**, May 2026 — private banks −257,290 terminals, public +204,595, net only −55,885). SIBC runs 0.99–1.00 at every depth. Methods: `csv_sector_momentum` (units added over 12 calendar months + `net_movement`/`gross_movement`/`coherence` aggregate rows), `csv_sector_acceleration` (Δ YoY vs prior period), `csv_sector_allocation` (`contribution` = share of gross movement, always; `alloc` = share of net, when coherence ≥ 0.90), plus `sibc-main-yoy-scan` (speed — the main cut had no per-sector YoY). **Coherence ROUTES, never gates**: `|net|/gross` picks which sentence is true (aligned / contested / handover) and nothing computed is suppressed — the lowest-coherence windows carry the strongest stories. Bound `max|share| ≤ 1/coherence` verified over 132 windows. `core/relational_insights.movement_insight` renders one card from all four (three cards would say one thing three times). **Pairing rule enforced in the builder**: a share is never rendered without that entity's speed and acceleration — published alone it reads as decline. Check 2g scopes it to the card's declared `sourceSignals` (18× tighter than period-wide; in-range injection catch 4/4). |
| **Layer 1 cut coverage (size + share)** | **Live (2026-09-12)** — L1 held 229 computed signals and could not state the SIZE of a single sector: every one was a rate or a share, so the platform could say industry grew 20.0% and could not say, from any stored value, that industry is ₹48 lakh crore. New `csv_sector_scan_abs` / `csv_category_scan_abs` give **all 10 cuts** a per-part level (+ the cut's own total, summed from the parts RBI actually publishes). Share coverage was ragged — 4 credit cuts had a share scan and 3 did not — so every SIBC cut now also carries **share of ALL bank credit** (`denominator_code: I`), the "one rupee in every seven" number, which was hand-arithmetic before. **PSL is the one documented exception**: `gap_psl_totals_methodology` says its parts are non-additive, so it has no total to be a share OF and that signal was removed rather than given an invented denominator. Allocation also gained **`weight_now`** — the share of the cut TODAY over the same denominator as `weight` (share a year ago); the share scan divides by the parent's published row while these divide by the sum of the parts, and for main sectors those differ by **4.9%** (the four sectors do not add up to non-food credit), so reading "then" from one family and "now" from the other compares two different questions. One `_child_frame` selector now serves every family, which is how the share scan finally became able to see the PSL block at all. Registry 267 → 286; proven a no-op on the 18,272 pre-existing rows (0 changed, 0 lost). `tests/test_l1_coverage.py` asks of each CUT "is it completely described" rather than of each signal "is it correct". |
| **Mix state (Layer 2, `SYSTEM_MODEL_SPEC` §16 Step 2b)** | **Live (2026-08-19)** — S3 reduced every signal to `direction ∈ {+1,0,−1}`, discarding magnitude, speed, tilt and agreement, so the causal layer could not express a mix being *managed*. `generate_system_state.mix_states` now reads the L1 movement rows straight from signals.db → `steered` / `drifting` / `contested` / `reallocating`, with `toward` + `away_from`. **No new registry signals** (the registry stays L1-computed-only). Joined declaratively on a momentum signal's `compute.parent_code`, so a new cut is a registry entry and nothing else. **Keyed by CUT, not entity** — industry's by-size and by-type decompositions hang off one node and are different mixes. "Material" is measured against each cut's own median max-tilt, never a constant (5.6 pp median across 4 main sectors vs 23.7 pp across 19 industry types). At 2026-07-31: main sectors **steered** toward Services (+4.9 pp) away from Personal Loans; services **steered** toward NBFCs (+15.9 pp); infra sub-types **contested**. All **7 SIBC cuts** carry a mix state — the PSL lens node (`code: PSL`, `additive: false`, own `psl_lens` decomposition) was added to the skeleton because PSL entities were reclassification orphans with `parent_code: null` and nothing to belong to. |
| **Relational signals (rotation + divergence)** | **Live (2026-07-20)** — 12 L1 signals (spec: `analysis/signals/README.md`): `csv_sector_rotation`/`csv_category_rotation` (Δshare over a 12-calendar-month window, share-scan reuse, per-entity rows + aggregate rotation-mass row) and `csv_sector_divergence`/`csv_bank_divergence` (one hierarchy operator, both trees — child vs parent YoY / bank vs bank_category YoY; flagged rows only). Backfilled all periods; covered by Check 2e/2f. `core/relational_insights.py` (`rotation_insight` + `divergence_insight`) renders deterministic publishable prose (theme = majority `economic_role` of material movers from the system model's concept_tags; honest fallbacks). **Wired on both dashboards (2026-07-20)**: SIBC Stage 5.5 routes them like scans (4 cards, Check 2g green); payments Stage 4b emits 6 `deterministic-db` cards validated vs their own signals.db rows (4c strict + 4d). **`csv_pair_divergence` (metric axis) live (2026-07-21)**: 5 authored pairs (cards issued vs spent on ×2, POS fleet vs POS value, ATM fleet vs cash withdrawn, + one bank-level) — total level emits the gap plus two `pair_side` component rows carrying each side's own YoY, so `pair_divergence_insight` reads direction from data (both-grew / both-shrank / split are three stories with identical arithmetic). Scalar-shaped ground truth, not scan-shaped; negative-tested. A `stable` gap (±3 pp) is the null result and emits no card. |
| signal evaluate layer | **Live** — `analysis/signals/evaluate.py` — Stage 5 LLM evaluation via `claude -p` CLI (Pro subscription, no API cost); **prompt v1.11** (executive tone, full period series + full scan distribution in payload, per-signal **chain** output, traceability + no-invented-seasonality rules); prior-period narratives auto-injected for diff; evaluations written to `signals/evaluations/{pipeline}/{period}.json` |
| **Insight schema + traceability** | **Live** — ONE shared insight schema across both pipelines: `basis.{facts, inferences}` (facts = traceable data points, inferences = the chain the card renders). SIBC **scalar** insights = LLM chain (prompt v1.11); SIBC **scan/distribution** insights = deterministic (`generate_analysis_report.deterministic_scan_insight`, grounded by construction). **ATM/POS now mirrors SIBC**: Stage 4b does deterministic selection + UI routing + `basis.facts`, then **overrides the prose of anchored scalar insights with the LLM eval narrative** (`EVAL_ANCHOR` map → registered signal_id; consumes `evaluations/atm_pos/{period}.json`, prompt v1.11; scan/share/concentration/composed/gap stay deterministic). Each insight carries `representation: llm|deterministic`. **Check 2g** (`validate_sibc_traceability.py`) + ATM/POS Stage 4c (`validate_atm_pos_insights.py`) hard-fail any number in body/chain/implication that doesn't trace to the computed signals — ATM/POS LLM insights validate vs the **period-wide signals.db** ground truth (like 2g), deterministic ones vs signals.json, plus a strict signals.json==signals.db **YoY drift guard**. SIBC `_signal_type=='scan'` branch overrides LLM text with deterministic. (3 fuzzy status-substring warnings remain non-blocking — see Open Notes.) |
| L1 annotation classification | **Done** — all 49 SIBC annotations classified: 26 L1 / 18 L2 / 5 L3; all 21 ATM/POS insights classified: 16 L1 / 3 L2 / 2 gaps |
| Subsystem generation | **Retired** — the 821-line legacy mermaid generator was deleted 2026-07-28; the deep read draws its own loop/constraint diagrams via `analysis/distribution/mermaid.py` |
| detect_format.py (Stage 0) | **Live** — flags format changes in new XLSX before extraction |
| ATM/POS pipeline | **Live** — `rbi_atm_pos/` — Stages 0–3 + L1 compute (84 signals) + evaluate. **28 periods Jan 2024 → Apr 2026** (2024 backfilled 2026-06-20 → YoY now computes for all 16 of 2025+2026, was 4). Detector handles older formats (abbreviated months, date-less sheets → filename, content-based sheet detection); canonical roster time-aware (Fincare merged Apr 2024, Dhanalaxmi rename Nov 2024). **Dashboard insights** come from a *separate deterministic path*: Stage 4a `compute_atm_pos_signals.py` → `rbi_atm_pos/signals.json` → Stage 4b `generate_atm_pos_insights.py` → `atm_pos_insights.json` (17 insights, Apr 2026). Both stages run inside `core/gate.py --pipeline atm_pos`. 4b is the single authoritative payments insight generator — the old "Stage 5.5" `generate_atm_pos_analysis_report.py` (a no-op) was retired to `analysis/legacy/` in the §4 cutover. |
| **Standing state band (Arc 1, `DASHBOARD_SPEC` §16)** | **Live (2026-09-11)** — the tier ABOVE the reads: two sentences on **every** dashboard dimension (7 SIBC + 3 payments), every period whether or not anything is news. Standing furniture, so both rows always render — where a reading cannot exist the row carries its **declared reason** (Bank Credit’s only split is food vs non-food; PSL is a memo lens with no published total), because a row that vanishes reads as broken. **speed** (L1, the parent's own YoY + whether the pace is moving) and **mix** (L2, the `mix_states` the causal layer has computed every ingestion since August and which had **never reached a browser**). Read together they separate *where the money went* from *whether that changed the shape of the book* — e.g. "Large took 60.8% of all new industry credit" sits above "Drifting toward Medium", because 60.8% of the flow is less than Large's 68.6% of the stock. Sentences are rendered in Python (`core/state_lines.py`) and shipped as **strings** — a browser that formats numbers is a publishing surface no validator can see. Sidecar `{pipeline}_state.json` (`signals/stamp_state.py`, `--check` guard); gate stages **5.9** + **5.9b** in both pipelines. Never the coherence number, never the tilt (a subtraction traces to nothing — its two stored operands are quoted instead); an absent input renders nothing; a dominated aggregate is attributed, not suppressed (POS terminals would otherwise republish ICICI's reclassification every month forever). Catch 100% / false rejection 0%, enumerated. |
| AppShell + DLS | **Live** — shared Header (one instance), `dls/InsightCard`, `dls/InsightCTAStrip` used by both SIBC and Payments |
| **Layer 2a system models (v4.0)** | **Live** — `system_model.json` for both pipelines (SIBC 85 entities, ATM/POS 35). Deterministic structural skeleton (`generate_skeleton.py`) + behavioral-causal split into shared **channels** (S2a) + dated **force_instances** (S2b). Specs: `analysis/SYSTEM_MODEL_SPEC.md` v3.0 + `analysis/COMPOSITION_SPEC.md` **v1.1** (Part II = ecosystem meta-model: constructs/eco-edges/cross-loops/reconciliation constraints/domains — spec'd 2026-07-03, not yet implemented). Validated by `validate_system_model.py` in both gates. |
| **Composition hub (Layer 2b)** | **Live** — `analysis/ontology/{concepts,channels}.json` shared across pipelines; entities carry global URNs + `concept_tags`. `derive_cross_links.py` derives cross-system candidates (stock↔flow + shared-channel); `cross_source/composition.json` holds confirmed cross-edges; `validate_composition.py` enforces the no-monolith rule. |
| **Ecosystem meta-model (Part II, v1.1)** | **Live (2026-07-03)** — `cross_source/ecosystem_model.json` (2 constructs, 2 eco-edges, 1 cross-pipeline loop, 1 reconciliation constraint) + `ontology/domains.json` (`lending` lens). Compose computes construct/eco-edge/loop/constraint states each run; eco-driven `scope:cross_source` opportunities carry a deterministic **`basis` block** (member signals → directions → state, values from signals.db) rendered as "Why — computed basis" on `/opportunities`; LLM narrates prose only (4f-checked vs `evidence_all`). Constraint `cx_cc_balance_per_card` reconciles SIBC CC outstanding vs payments card count (₹24.9k/card, corridor 8k–60k, severity **fail** — negative-tested). `validate_composition` §20 checks wired into **both** gates; 15 unit tests in `tests/test_ecosystem_compose.py`. |
| **S3 dynamic state + opportunities** | **Live** — `generate_system_state.py` (forces/edges/loops fire from `signals.db`), `derive_opportunities.py` (status active/watch/closed/retired from driver firing), `compose_ecosystem.py` (cross-system premium feed). Both gates run these each ingestion. |
| **Opportunities UI** | **Live** — gated `/opportunities` reads `web/public/data/opportunities_feed.json` (`generate_opportunities_feed.py`); `generate_opportunity_narrative.py` adds plain-English, numbers-grounded copy (post-gate step). |
| ~~validate.py checks 4/5 · validate_claims (2c) · mermaid gen · source_claims · subsystems~~ | **Retired** — superseded by the v4.0 system model + `validate_system_model.py`. Most scripts remain on disk detached from the gate; the mermaid generator was deleted 2026-07-28 (its capability moved into `distribution/mermaid.py`). |

---

## Key files

| File | Purpose |
|---|---|
| `CLAUDE.md` | This file |
| `STRATEGY_PLANNER.md` | Content ladder, revenue model, product roadmap |
| `PIPELINE_ARCHITECTURE.md` | **Pipeline stages, system model cadence, adding-period checklist** |
| `analysis/report_analysis_prompt.md` | Master prompt + analytical framework for all report analyses |
| `analysis/core/gate.py` | Master eval gate — Stages 3 and 6 |
| `analysis/core/validate_timeline.py` | Check 0: timeline.json schema + path existence |
| `analysis/pipelines/sibc/validate_sections.py` | Check 1: sections.json data integrity |
| `analysis/pipelines/sibc/validate_annotations.py` | Check 3: live rbi_sibc.ts structure (Checks A–H) |
| `analysis/pipelines/sibc/validate_content.py` | Check 2b: dates/values/growth in annotation bodies vs sections.json |
| `analysis/legacy/validate_claims.py` | Check 2c (**retired** — archived): claim sourcing — superseded by `core/validate_system_model.py` |
| `analysis/pipelines/sibc/validate_annotation_basis.py` | Check 2d: basis completeness — inference/hypothesis annotations must have basis.inferences |
| `analysis/guards/validate_signal_history.py` | Check 2e: signal history integrity — DB rows, registry schema, status sync vs DB |
| `analysis/guards/check_signal_freshness.py` | Check 2f/5b2: deterministic signals.db freshness — recompute all periods from CSV, fail on drift. Closes the staleness gap `check_derived_fresh.py` leaves (it excludes the binary DB). **Parallel by period (2026-09-13): 2m47s → 24.6s on 8 cores**, guarantee untouched — every row still recomputed and compared; falls back to serial on any pool failure. Deliberately NOT input-fingerprinted: skipping when inputs look unchanged would stop catching a hand-edited DB, which is the capability that makes this evidence rather than bookkeeping. **Its population is `timeline.json`, not the DB** — it used to read the period set off the committed rows, so deleting a whole month left it reporting "fresh — 46,013 rows match (sibc:10p)". Stale values were caught; an absent period was not. |
| `analysis/pipelines/sibc/validate_sibc_traceability.py` | Check 2g: every number in a SIBC insight's body/chain/implication must trace to a value in signals.db (scalar = hard fail; scan = deterministic so grounded by construction). Status-substring contradictions = non-blocking warnings. Ground truth = `query.signal_numbers`/`flat_numbers` (period-wide, unit-aware). |
| `analysis/pipelines/atm_pos/validate_atm_pos_insights.py` | Stage 4c: ATM/POS traceability — numbers in body/**chain**/implication must trace to `signals.json`. Mirror of Check 2g for the deterministic payments path. |
| `analysis/guards/validate_card_prose.py` | **Check 5.8**: the voice gate for dashboard cards. `core.voice` had linted the distribution surfaces for a year while the dashboard — the surface most people read — was linted by nothing, and a card told the reader to *"Move everything to UPI QR"*. Severity follows ownership (DISTRIBUTION_SPEC §5.3): prose the generator writes **hard-fails**; the eval's narration **warns** and goes on the next prompt's fix list. SEBI hits warn until the measured precision fix — the substring list trips on "what shopkeepers sell". |
| `analysis/guards/validate_state_band.py` | **Check 5.9b**: the state band's numbers (`DASHBOARD_SPEC` §16). Scoped to each block's declared `source_signals` **at this period, for the entity the sentence names** — not the signal's history. That distinction is the check: at history width four of twenty-three near-miss injections survived by colliding with the signal's own past readings. `traceability.DISTRIBUTION` policy, since the band quotes stored values rather than reasoning about magnitudes. |
| `analysis/guards/validate_card_cuts.py` | **Check 5.7**: the card↔chart cut check (`DASHBOARD_SPEC` §15.7). Every other traceability gate asks *is this number true?*; this one asks *is the chart under the card an answer to the card's question?* A card's cut (entities + denominator) is read off its signal's own `compute` block and compared with what its section's chart renders. Catches: a card charted at the wrong level · a share measured against a total the chart does not draw · a highlight naming a series that renders nothing · a card declaring no cut at all. Section cuts are DECLARED (`pipelines/{name}/section_cuts.json`), never inferred from labels. Advisory until the §15.2 contract lands, then `--strict`. |
| `analysis/core/validate_opportunity_traceability.py` | Check 4f: opportunity (Layer 2) number traceability — every number in an opportunity body/chain/implication must trace to the driver's **full declared evidence set (`evidence_all`)** (period-wide is vacuous at cross-pipeline scale). **STRICT in both gates** (the L2 analog of Check 2g; `derive_opportunities` emits `evidence_all` = driver's full signal set so structural risks ground even when not firing). |
| `analysis/pipelines/sibc/generate_analysis_report.py` | Stage 5.5: eval JSON → `sibc_l1_annotations.json`. Scalar insights carry the LLM chain → `basis.inferences`; **scan insights generated deterministically** (`deterministic_scan_insight`). Attaches `basis.facts` from `signal_numbers`. |
| `analysis/legacy/validate.py` | Checks 4, 5: system_model.json + subsystems.json |
| `analysis/pipelines/sibc/extract_sibc.py` | Stage 1: SIBC xlsx → sections.json + format_report.json |
| `analysis/pipelines/sibc/detect_format.py` | Stage 0: detect structural changes in new XLSX vs prior period (SIBC) |
| `analysis/pipelines/sibc/update_web_data.py` | Stage 3: all xlsx → rbi_sibc_consolidated.csv |
| `analysis/pipelines/sibc/generate_merge.py` | Stage 3: sections.json[] → sections_merged.json (auto-validates) |
| `analysis/distribution/mermaid.py` | Deep-read inline diagrams — a focused loop/constraint renderer (§11.2). Replaced the deleted legacy mermaid generator on 2026-07-28. |
| `analysis/legacy/source_claims.py` | Post-model-update: source all claims in system_model.json |
| `analysis/pipelines/sibc/promote_annotations.py` | Stage 7: annotations_merged.ts → rbi_sibc.ts (verified copy + ID diff) |
| `analysis/core/generate_signal_history.py` | Stage 4 (`append`) + Stage 5 (`evaluate`) + `status` + `seed` commands |
| `analysis/signals/registry.json` | Universal signal catalog — 570 signals, layer 1/2/3 tagged; all Layer 1 signals have compute specs (SIBC + ATM/POS). Counts here are checked by `reconcile.py` |
| `analysis/signals/signals.db` | **Primary signal store** — SQLite; (pipeline, period, metric_id, entity_type, entity_id) fact table + metric_ranges |
| `analysis/signals/compute/` | Compute engine: engine.py dispatches on the manifest's declared `compute_module`; `csv_sector.py` (any sector-hierarchy source — SIBC today) + `atm_pos.py` implement all 1a/1b/1c/1d methods. Both read their pipeline's consolidated CSV. A module offering `resolve_csv_date` maps `dataDate → csv_date` via `timeline.json` before querying. |
| `analysis/signals/evaluate.py` | Stage 5 LLM evaluation engine — reads signals.db, builds domain payloads (full period series included), calls `claude -p` CLI, writes to evaluations/. prompt_version=1.4. Cache in llm_cache table. |
| `analysis/signals/query.py` | Builds signal payloads for evaluate — scalar + scan + full chronological series per signal |
| `analysis/signals/prompts/domain_eval_system.txt` | System prompt v1.4 — executive tone, trajectory style, no jargon |
| `analysis/signals/evaluations/sibc/2026-05-29.json` | Latest SIBC evaluation — 5 domains, prompt v1.5 |
| `analysis/signals/evaluations/atm_pos/2026-04-30.json` | Latest ATM/POS evaluation — 4 domains, prompt v1.5 |
| `analysis/signals/db.py` | DB init, schema, refresh_ranges() |
| `analysis/cross_source/catalog.json` | Tuple registry — all declared cross-source pairs (Layer 2b) |
| `analysis/cross_source/ecosystem_model.json` | **Authored meta-model** (COMPOSITION_SPEC Part II): constructs, eco-edges, cross-pipeline loops, reconciliation constraints — owns only what no pipeline can own |
| `analysis/ontology/domains.json` | Domain lenses (§18) — zero structure; scopes the one meta-model for Layer 3 narrative + UI |
| `analysis/tests/test_ecosystem_compose.py` | Unit tests for the §14–§17 pure state functions (construct direction, eco-edge state, loop firing, constraint eval) |
| `analysis/rbi_atm_pos/merged/system_model.json` | ATM/POS per-source system model (Layer 2a — pending first FOUNDATION) |
| `analysis/rbi_sibc/timeline.json` | Registry of all ingested periods (includes `is_fy_end`, `dataDate` = report release date, `csv_date` = actual data date matching the consolidated CSV) |
| `analysis/rbi_sibc/merged/` | Merged outputs (Jan 2024–Mar 2026) — source for live dashboard |
| `web/lib/reports/rbi_sibc.ts` | Live dashboard annotations (promoted from merged) |
| `web/CLAUDE.md` | Web-specific context — Next.js, AppShell, DLS components, colour system, mobile rules |
| `web/components/AppShell.tsx` | Shared shell: Header rendered once + dark mode state across all pages |
| `web/components/dls/InsightCard.tsx` | DLS: shared insight card (SIBC + Payments) |
| `web/components/dls/InsightCTAStrip.tsx` | DLS: shared entry/exit strip with headline ticker |
| `analysis/rbi_atm_pos/CLAUDE.md` | ATM/POS pipeline context — read before any ATM/POS work |
| `analysis/rbi_atm_pos/timeline.json` | Registry of ingested ATM/POS months |

### Distribution subsystem

**Live (2026-07-21)** — one renderer over the categories partition; every slot self-gates and
Claude never writes a finished post (each slot emits a *closed* design prompt + a blurb).

| File | Purpose |
|---|---|
| `analysis/distribution/DISTRIBUTION_SPEC.md` | **Design v1.1** — 10-category taxonomy, monthly slot map + fallbacks, per-slot output contract, blurb voice, AI PM track. §13 records the Fable-brief reconciliation + the measured data-month offset. Read before any distribution work. |
| `analysis/distribution/generate_slot.py` | **The generator** — `--slot {1st,7th,14th,21st,28th}` or `--all`. Calendar → category (primary, then fallback) → slate → gate → `output/{date}_{slot}_{cat}/{design_prompt,blurb}.md` → ledger. Empty primary *and* fallback = skip, recorded. |
| `analysis/distribution/categories.py` | The §3 partition in code: compute method → category, precedence for multi-signal cards. An unclassified method fails the run. |
| `analysis/distribution/distribution_sources.py` | Data layer for every channel — absorbed `newsletter_sources` on 2026-07-21. Claims by category, data vintage read fresh per run, turns/corrections/watchlist. |
| `analysis/distribution/slot_render.py` | Slate → closed design prompt (+ machine-readable supplied-numbers block) + blurb; §10 voice lint. |
| `analysis/distribution/validate_distribution.py` | The gate — verbatim feed prose, per-claim number scope, declared derived numbers, voice lint. Uses the tighter `core.traceability.DISTRIBUTION` policy (no ratio grounding). |
| `analysis/distribution/ledger.py` | `distribution_ledger.json` — verifies the partition held (signal reused within 20 days), records skips, snapshots statuses so C9 can catch our own reversals. `python3 analysis/distribution/ledger.py` audits. |
| `analysis/signals/proximity.py` | **C8 net-new compute** — distance from each signal to its next status flip, ranked by the signal's own typical monthly move. Signal-layer, registry-driven; dashboard + reply desk are the next consumers. |
| `analysis/distribution/issues/{merged_issue,deep_read}.py` | The two long-form (Substack) issues — 1st and 14th. Formerly `newsletter/generate_*`. |
| `analysis/distribution/longform_render.py` | Long-form render layer — typed blocks → .md + Substack-paste .html |
| `analysis/distribution/NEWSLETTER_CONTEXT.md` | Long-form channel context — read before content generation |
| `analysis/distribution/signal_registry.json` | Editorial record of every signal ever published (distinct from the mechanical ledger) |
| `analysis/measure_groundedness.py` | Gate measurement harness — inject fakes, report catch + false-rejection rate. AI PM topic #1. |
| `analysis/distribution/ai_pm_register.json` | AI PM learning register — 20-topic curriculum, one active per month, measurements appended as build work produces them |

**AI PM active topic: #1 Groundedness / hallucination measurement (2026-08).**
Standing rule — when any session produces a number that measures the active topic (traceability
pass rate, negative-test catch rate, scope tightness), append it to `ai_pm_register.json`
`topics[].measurements[]` before the session ends. No entry publishes on prose alone; every
measurement needs a value and a source file.
