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
- **A real-economy (1f) cell holds its own period's reading or a reason** (user, 2026-10-03): a period before MoSPI's base reaches reads `reference_history_gap`; a quarterly value is stored at quarter-ends only and shown labelled (·Q1), never repeated into months. *Why:* nothing carries forward, and absences stay visible. *Revisit:* if MoSPI back-casts its current base.
- **A real-credit number always names its deflator and that deflator's change** (user, 2026-10-04). *Why:* petroleum −17.1% real (Aug 2026) was a 38.5% fuel-price jump and reads as a collapse without it. *Revisit: never.*
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
- **A cause that predates the window is sourced, not promoted** (user, 2026-10-03). S4's temporal rule cannot see a lagged or slow-building cause, so such a proposal gets its official excerpt recorded (`--resolve` without `--in-force`) and waits. *Why:* Aug 2026's two clean sources (ATM fees, TReDS) fit the movement only through a lag. *Revisit:* forces now carry delay/fade fields (v3.1), but S4's `--in-force` still checks the window only; decide again with the S4 redesign.
- **A force is judged against its group, inside its window** (user, 2026-10-08; SYSTEM_MODEL_SPEC §16 Step 3). Delay and fade come from a rule per kind of force (`timing_rule`), not per force. A standing force explains a steady gap, never a sudden move. Switched per pipeline in its manifest (`force_check`). *Why:* the old check could not fail (237 of 325 SIBC force-readings "active"; the Nov 2023 risk weights read `reversed` on cards growing 3.6% vs 16.9%). Payments switched on 2026-10-10 once its group totals carried a YoY signal; its card-lifecycle force reads contradicted only because "cards in force" is ~90% debit (accepted misfit, fixed in the next model pass). *Revisit:* when a force's claim is a step change, not a steady gap.
- **A move is a change > 3× the line's typical month-to-month change, one data month apart** (2026-10-08, Step 6a). *Why:* at 1× half of all readings "move" by construction (47% SIBC); across a hole in the history (Aug–Nov 2025) one reading showed 32 false moves. Re-measured after the 2026-10-10 backfill (23 changes per line): 3× flags 10%, unchanged. *Revisit:* after the next backfill.
- **Relationships between parts are proposed with a reason, then admitted by a test, never discovered** (2026-10-08, Step 6b). Reason, sign and lag are declared first; the shared tide (root growth) is removed; several declared together share one bar (Bonferroni); nulls are recorded. *Why:* 86 cross-group SIBC pairs co-move at |r| > 0.6 and a shuffled control gives 48; HFC vs housing looked linked (p 0.03) only through the bank-credit tide (p 0.43 once removed). *Revisit:* with ≥ 60 monthly changes, discovery may be reconsidered.
- **An authored arrow is a hypothesis until its test admits it** (user, 2026-10-10). Arrow states, loops, coverage and line-driven opportunities read the arrow's latest relationship test; untested reads dormant. A line with no group to compare with makes its opportunity `unassessable`, never `closed`. *Why:* the 12 arrows already in the models were judged against zero and all 12 failed their test; payments' card-penetration loop read active on that basis. *Revisit:* never.
- **A null relationship test with short history means "too weak to see", not "absent"** (2026-10-08). With 15 monthly changes only |r| ≥ 0.51 can pass (0.63 as one of four); 60 changes would show 0.25. At 23 (after the 2026-10-10 backfill) the bar is ~0.41 and all five tested links stay below it (|r| ≤ 0.31). *Revisit:* each time the usable history grows.
- **A proposal raised by a pipeline whose ingest is pending waits for that ingest** (user, 2026-10-03), recorded as a `deferred` attempt, so one verified force can attach to every pipeline it explains.
- **Triage never promotes.** A `duplicate` ruling must name the force it duplicates; ruled-out proposals are reported with counts, never silently dropped.

## Dashboard

- **Layer 1 surface = one table per dimension + the state band**, both derived; cards are the news layer. `DEEP_ENABLED = false` while L1 is being got right.
- **SIBC nests, payments filters** (an accepted inconsistency). Insights sit below the table; sorting is by clicking a column header; Explore never goes away. (user, 2026-09-13)
- **Read is the authoritative surface for insights; Explore is charts only** (user, 2026-10-05). *Why:* every card Read hides is a cell of its table, so Explore's cards were repeats, and the 27 hand-written annotations were stale since June. *Revisit:* if a card type appears whose content has no cell or band line.
- **NBFC v1 = table + band, no card generator.** *Revisit: ~12 releases* (D2). Cross-source UI waits until L1 is reviewed (D5).
- **Type and radius scale live in `web/lib/tokens.ts`**, and a test fails any literal outside it. Colours stay CSS custom properties.
- **One information hierarchy on every surface** (user, 2026-10-05): five `TEXT` levels, claim → evidence → reference, one chart frame, captions triaged (DASHBOARD_SPEC §22). *Why:* tiles, rail and row chart each picked their own and read as three products. *Revisit: never; extend §22 instead.*
- **Explore mode stays per-pipeline.** *Revisit: when several more pipelines exist.*

## Distribution

- **The user writes the words.** Claude drafts when asked (post text + a source row per number + traps + ASCII layout); the user rewrites it and decides what is posted. Every number is a stored dashboard value, a real-credit number names its deflator, and causes we have not sourced are framed as questions. Machine "so what" lines are observations, never advice or forecasts. (user, 2026-10-08, Aug 2026 carousels) *Revisit:* if the user stops rewriting drafts.
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
