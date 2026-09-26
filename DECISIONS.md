# DECISIONS: standing rules made during the work

> One entry per decision, with its reason and the event that would reopen it. When a revisit
> trigger fires, decide again and **edit or delete the entry**; do not add a second one. Hard cap
> 150 lines, enforced by `reconcile.py`. Non-negotiable project rules (API spend, git, ASCII-first,
> date normalisation) live in `CLAUDE.md`, not here. Harvested 2026-09-24 from ~50 session logs.

## Numbers and signals

- **An LLM never decides a number.** Compute is deterministic; the LLM narrates only, and every published number must trace to signals.db. *Revisit: never.*
- **Never publish a number no gate can ground.** Coherence and tilt are derived, so prose quotes their stored operands ("took 14.0% of the growth while holding 9.2%") instead. *Why:* invented 0.73 and 0.31 both passed Check 4f. *Revisit: if the value becomes a stored row.*
- **Coherence routes, never gates.** Momentum, acceleration and contribution always publish; coherence only picks the sentence (aligned ≥0.90 / contested / handover <0.50). *Why:* the lowest-coherence windows are the best stories. *Revisit: never.* (2026-08-19)
- **Registry stays Layer-1-computed-only.** Layer 2 lives on the system model and `mix_states`, never as registry entries. *Revisit: never.* (2026-06)
- **A share divides by the total it is actually a share of.** `weight_now` sits beside `weight`; the parent's published row and the sum of its parts differ (4.9% on main sectors). *Revisit: never.*
- **A share of a NET move can exceed 100%.** Check 2e asserts `|share| ≤ 100/coherence`, not ≤100. "₹137 of every ₹100" is a prose problem for the card layer, not a data error. (2026-09-12)
- **Pairing rule.** A share is never published without that entity's speed and acceleration, and a speed never without its size. *Why:* alone, each reads as its opposite.
- **Attribute, don't suppress.** A move dominated by one entity keeps the raw number and names the entity ("but it's ICICI Bank, not the market"); only a ratio corrupted by a dominated denominator is zeroed. (`signals/dominance.py`)
- **Absences stay visible.** Where a reading cannot exist, the row carries its declared reason; a row that vanishes reads as broken.
- **A remainder is not a sector.** RBI's "Others" residual is never headlined.
- **Cadence = how often the VALUE can change**, not how often the source publishes. Declared on every signal; Check 2e fails a missing one.
- **Windows are declared per signal** (`window: 12`), never defaulted in code, so a title's "12 months" grounds.
- **PSL has no share-of-parent**: its parts are non-additive, so no invented denominator. (The `weight`/`weight_now` question is open; see PLAN.)
- **SIBC has no pair signals**: one measure (outstanding) per entity, so there is nothing to pair. *Revisit: a source with a second measure per entity.*

## Guards and storage

- **signals.db stays committed until ~80 MB, then Git LFS.** The committed DB is what freshness verifies; never untrack it and rebuild from CSV. (2026-09-14)
- **Freshness is NOT input-fingerprinted.** Skipping on unchanged inputs would stop catching a hand-edited DB. Its population is `timeline.json`, never the DB it checks.
- **A check's population is a design decision.** Every new guard states what set it iterates and where that set comes from; a derived set beats a hand-written list.
- **Make the unknown case loud.** A failure must never return the same value as a legitimate null (outage vs "found nothing", refusal vs cache hit, empty ingest vs success).
- **No gate changes without a measured catch rate AND false-rejection rate**, by enumeration not sampling, with one known-good and one known-bad control through the harness first. *Why:* 4 probe bugs produced false findings in 3 days. Log it in `ai_pm_register.json`.
- **Sentences are rendered in Python and shipped as strings.** A browser that formats numbers is a publishing surface no validator can see.
- **Units are lakh/crore, converted deterministically** at eval write time, not by prompt.
- **Card/band dedup stays as-is, weakness known**: stable under recompute, not under rewording. Fix = option B in PLAN. (user, 2026-09-15)

## Sourcing and Layer 2

- **Layer 2 = signals mapped onto the model.** Real-world causes enter only as sourced forces (URL + verbatim excerpt verified on the page + effective date in force for the window); nothing is auto-promoted.
- **Every current-period ingest runs a model pass + S4 sourcing** (skills `model-pass`, `s4-source`). An honest null is recorded, never fabricated.
- **Chrome is the primary sourcing channel**; the API source hunt is opt-in. *Why:* many allowlisted hosts block crawlers. PIB and RBI are open; NPCI is genuinely blocked.
- **A hypothesis with no source beats one with a decorative citation.** An excerpt that restates our own series is the effect, not a cause.
- **Allowlist tiers:** nabard.org T1 (statutory); sidbi.in T2 (research, never a rung-1 official source).
- **Triage never promotes.** A `duplicate` ruling must name the force it duplicates; ruled-out proposals are reported with counts, never silently dropped.

## Dashboard

- **Layer 1 surface = one table per dimension + the state band**, both derived; cards are the news layer. `DEEP_ENABLED = false` while L1 is being got right.
- **SIBC nests, payments filters** (an accepted inconsistency). Insights sit below the table; sorting is by clicking a column header; Explore never goes away. (user, 2026-09-13)
- **NBFC v1 = table + band, no card generator.** *Revisit: ~12 releases* (D2). Cross-source UI waits until L1 is reviewed (D5).
- **Type and radius scale live in `web/lib/tokens.ts`**, and a test fails any literal outside it. Colours stay CSS custom properties.
- **Explore mode stays per-pipeline.** *Revisit: when several more pipelines exist.*

## Distribution

- **The user writes the words.** Claude supplies verified numbers, arc, traps and design briefs, never a finished LinkedIn post. Machine "so what" lines are observations, never advice or forecasts.
- **Substack is paused, not deleted**; the generators stay. *Revisit: after the user has read a few cycles.*
- **Reads are ranked by the machine and picked by the editor.** The same pattern applies to deep-read spines.
- **Reply desk retired.** X needs its own design.

## Sources and roadmap

- **Order: NBFC → MoSPI (IIP, WPI, NAS, CPI) → arc 3 regulatory watch → BSR-1 → Lending & Deposit Rates.** (user, 2026-09-16; MoSPI placed first 2026-09-26)
- **MoSPI is pulled by hand until two clean cycles, then scheduled.** *Why:* no provisional/final flag and revisions overwrite silently, so revision behaviour must be seen before it is automated. *Revisit: after two clean cycles.* (user, 2026-09-26)
- **Bank presentations/results rejected** as a source: unstructured, and per-bank credit is annual only (STRBI).
- **A compute module is a shape, not a pipeline**, and a pipeline declares itself in its manifest. A new SIBC-shaped source is a manifest entry.

## Working model

- **One living `PLAN.md`, no journal, no dated plans.** git log is the history. `PLAN.md`, `DECISIONS.md` and `CLAUDE.local.md` are capped. (user, 2026-09-24)
- **The agentic layer sits on the engine, never in it.** A skill runs engine commands and is done only when a named gate passes. Claude may start `measure-gate`, `dashboard-change` and `add-signal-family` on its own; ingest, spend, source and commit stay user-invoked. (user, 2026-09-24)
- **Solo on `main`, no branches or worktrees; never auto-push.**
- **Backdated periods are backfill-only** (no costly LLM authoring) unless the user asks otherwise.
