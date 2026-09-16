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
| **the pipeline pair, hardcoded** | `PIPELINE_IDS = ("sibc", "atm_pos")` in `core/manifest.py` — and the same literal pair repeated in **15 modules** (argparse `choices`, sidecar dict comprehensions, guard loops) |
| **compute module per pipeline** | `compute/sibc.py` + `compute/atm_pos.py`, dispatched by `if pipeline == …`. NBFC is SIBC-SHAPED, so it either copies `sibc.py` or `sibc.py` learns to read a manifest-declared CSV schema. **This is the decision that matters most** |
| **card generator per pipeline** | 753 LOC (SIBC) and 2,123 LOC (payments) — a third pipeline has no generic path to cards, only two patterns to pick between |
| **web adapter + page per pipeline** | `SibcReadMode` 211 LOC, `AtmReadMode` 230 LOC, plus a route; `"sibc" | "atm_pos"` is a TYPE UNION in 6 lib files, so a third id is a compile error in each |
| **MOVEMENT_CUTS** | still a hand-written table per pipeline. The BAND no longer reads it (derived), but the movement CARDS still do |

### What this means for the next pipeline

**A new source reaches Layer 1 on the dashboard only through work that is per-pipeline today.**
Even with Layer 2 and 3 left switched off — which is the plan for NBFC — the L1 path still needs a
compute module, a card generator, a web adapter and fifteen edits to hardcoded pairs. That is the
gap between "the architecture scales" and "the plumbing scales", and it is worth closing in the
order the third pipeline exposes it, not speculatively:

1. **Pipeline ids from the manifest**, not a literal — one constant, fifteen call sites.
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
