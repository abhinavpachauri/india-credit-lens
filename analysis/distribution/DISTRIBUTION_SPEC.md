# Distribution Spec v1.1

> Authored design for content distribution across newsletter, LinkedIn, X, and the AI PM track.
> Status: **built** (2026-07-21) — §12 steps 1–4 live; §8 register wiring is the monthly habit.
> Run it: `python3 analysis/distribution/generate_slot.py --slot 7th` (or `--all` to rehearse
> a whole month). Every slot self-gates; see `validate_distribution.py`.
> Related: `analysis/newsletter/CLAUDE.md` (v2 newsletter, live) · `analysis/legacy/replydesk/` (X, retired — see §9)

---

## 1. Governing principle

Distribution is a **rendering problem over artifacts the pipelines already compute** — not a
second content system. One content spine per monthly cycle, many renderings. The channel changes
*length, framing, and selection*; it never changes *where the number came from*.

This means:

- One shared source layer (a generalisation of `newsletter/newsletter_sources.py`) reads only
  gate-validated artifacts: `signals.db`, `sibc_l1_annotations.json`, `atm_pos_insights.json`,
  `opportunities_feed.json`, `ecosystem_model.json`.
- Per-channel renderers sit on top. No renderer re-derives a number.
- One traceability gate (`validate_newsletter.check_doc`, generalised) covers all channels.

Test it against the standing rule: *does this hold at N channels and N pipelines?* Adding a channel
must mean adding a renderer, never a second source path.

---

## 2. Anti-repetition: categories, not a ledger

Seven-plus outputs a month come off one data drop. Repetition is prevented **at design time** by
partitioning the signal space into non-overlapping editorial categories and assigning each calendar
slot a category it owns. The ledger (§7) is the *verifier* that catches accidental overlap — it is
not the mechanism that prevents it.

Same discipline as the rest of the platform: fix the spec so the failure cannot happen, then check
it deterministically.

---

## 3. Category taxonomy

Ten categories. More categories than slots — that surplus is what makes rotation possible and
repetition structurally hard.

| ID | Category | Question it answers | Source artifacts |
|---|---|---|---|
| C1 | **Headline levels** | What are the numbers | L1 scalars, both pipelines |
| C2 | **Rotation** | What's gaining ground, at whose expense | `csv_sector_rotation`, `csv_category_rotation` |
| C3 | **Divergence** | What used to move together and no longer does | `csv_sector_divergence`, `csv_bank_divergence`, `csv_pair_divergence` |
| C4 | **Spread** | Broad-based, or a few names carrying it | scan signals, concentration signals |
| C5 | **Turns** | What changed direction — accel/decel, streaks breaking, status flips | trajectory signals, period-over-period status deltas |
| C6 | **Openings & risks** | So what, and for whom | S3 → `derive_opportunities` → `opportunities_feed.json` |
| C7 | **Cross-system** | What credit + payments say together that neither says alone | constructs, eco-edges, cross-pipeline loops, reconciliation constraints |
| C8 | **Watchlist** | What could flip next month | `signals/proximity.py` — distance to the next status flip (§6) |
| C9 | **Corrections** | Where our earlier read was wrong | expired forces (S4 temporal validity), retired signals, revised status |
| C10 | **Method** | How this thing is built | AI PM register (§8) |

### Category boundary rules

- A claim belongs to exactly one category. If a number could serve two, it belongs to the
  category whose *question* it answers, not the one whose data it came from.
- C1 states levels. The moment you say "and that's a change in direction", it's C5.
- C2 is about *share* moving. C3 is about *co-movement breaking*. A single sector growing faster
  than another is C2 if you're framing mix, C3 only if the two are a declared pair or a
  parent/child hierarchy.
- C6 is model-driven (opportunity nodes), never an LLM inference over C1–C5.

---

## 4. Calendar

| When | Channel | Primary | Fallback |
|---|---|---|---|
| 1st | Newsletter (merged) + LinkedIn | C1 (+ light C5) | — always fires |
| 7th | LinkedIn | C2 + C3 | C4 |
| 14th | Newsletter (deep read) + LinkedIn | C6 + C7 | C4 |
| 21st | LinkedIn | C10 (AI PM) | C9 |
| 28th | LinkedIn | C8 | C9 |

**X / Twitter** is not on the calendar and is **out of scope for this layer** — it is reactive by
design and needs its own treatment, which it does not yet have (§9).

### Fallbacks are mandatory, not decoration

The generators emit honest null results — the ±3 pp stable band suppresses pair-divergence cards,
rotation mass under 0.5 pp renders "steady mix". Some months a slot genuinely has nothing worth
publishing. The declared fallback is what gets published then. **Never publish a weak primary
because the calendar said so.**

If both primary and fallback are empty, skip the slot and log the skip in the ledger. A missed slot
is cheaper than a thin post.

---

## 5. Per-slot output contract

Each slot generates **two artifacts**. Neither is a finished post.

### 5.1 `design_prompt.md`

The prompt pasted into a separate Claude design session to produce a one-or-more-pager visual.

Must contain:
- the category and the slot date
- the grounded numbers, **verbatim** from validated artifacts, each with its label and unit
- the intended narrative arc for the pager
- page count
- a hard constraint block: **use only the numbers in this prompt; invent nothing; do not
  compute new figures from these numbers**

**The design session sits outside the gate.** Every other public surface on this platform is
number-traced. A pager built in a fresh session is the one place a fabricated figure could reach
the feed. Therefore the prompt must be *closed* — self-contained, with no invitation to look
anything up or derive anything.

Future hardening (not v1): a checker that the returned pager's number set is a subset of the
number set the prompt supplied. Design the prompt format now so that check is possible later —
i.e. emit the supplied numbers as a machine-readable block alongside the prose.

### 5.2 `blurb.md`

The LinkedIn copy that accompanies the pager. Generated, not hand-written.

---

## 6. Net-new compute required

Only one item in this whole plan is not a re-rendering of existing artifacts:

**C8 Watchlist — proximity-to-threshold.** Compute, per signal, the distance between its current
value and the threshold that would change its `current_status`. Rank. The 28th post is "here are
the three things that could turn next month."

This is deterministic, sits naturally in the signal layer, and is the most forwardable post on the
calendar. Build it as a registry-driven computation over `signals.db`, not as a distribution-layer
one-off — it is a signal property, and other consumers (the dashboard is the obvious next one)
will want it. **Built 2026-07-21** as `analysis/signals/proximity.py`; it separates *level* edges
from momentum *knife edges* and only levels earn a watchlist slot.

Everything else in §4 renders artifacts that already exist.

---

## 7. The ledger

`analysis/distribution/distribution_ledger.json` — generalises the role
`newsletter/signal_registry.json` plays today.

Records, per published item: date, channel, slot, category, the signal IDs and claims used,
and a link. Purpose:

1. **Verify** the category partition held — flag when the same signal ID appears in two slots
   within a window.
2. **Record skips** (§4) so a pattern of empty slots is visible rather than forgotten.
3. Feed engagement learning later.

The ledger does not decide what to publish. It checks what was published.

---

## 8. AI PM track

### 8.1 Shape

One deep post per month, anchored at the 21st. One topic (or sub-topic) per month.

**The register fills as a byproduct of build work, not from separate study.** If the month's topic
is evals and we build an eval harness that month, the metrics land in the register because that is
the month's topic. The post is assembled from measurements the normal work already produced. There
is no separate homework session.

### 8.2 Admission rule

**No register entry without a number and a source.** A topic cannot be marked `published` on prose
alone. This is what keeps the track off surface-level commentary, and it is the same bar every
other claim on this platform meets.

### 8.3 Curriculum — 20 topics

Seeded in `analysis/distribution/ai_pm_register.json`. The curriculum is *authored*, not derived —
edit it freely as understanding improves.

**Evaluation & quality**
1. Groundedness / hallucination measurement — *traceability pass rate, negative-test catch rate*
2. Eval set design & regression detection — *suite size, pass rate, injected-regression catch rate*
3. LLM-as-judge reliability — *judge↔human agreement, verbosity/position bias*
4. Human-in-the-loop review design — *review time per item, override rate*

**Model behaviour & control**

5. Determinism vs judgment boundary — *% output deterministic vs generated*
6. Prompt engineering & versioning — *version-over-version delta on a fixed eval set*
7. Structured outputs / schema enforcement — *schema violation rate, retry rate*
8. Context engineering — *tokens per call, quality across context sizes*
9. Sampling & reproducibility — *output variance across identical runs*

**Systems**

10. Agent loops & tool use — *steps to completion, tool-call error rate*
11. Retrieval / RAG quality — *recall@k, attribution rate*
12. Caching & cost architecture — *cost per unit of output, cache hit rate*
13. Latency & throughput — *p50/p95, tokens per second*
14. Failure modes & degradation — *fallback rate, blast radius when the model is wrong*

**Product & economics**

15. Unit economics of an LLM feature — *cost per insight / per report*
16. Model selection & routing — *cost-quality frontier per task*
17. Trust & UX for probabilistic output — *correction rate, uncertainty surfaced*
18. Data flywheel design — *usage → quality lift*
19. Safety & policy boundaries in product — *refusal rate, false-positive refusals*
20. Versioning & model migration — *eval delta on model swap*

### 8.4 Opening sequence

| Month | Topic | Why this order |
|---|---|---|
| 1 | #1 Groundedness | Most evidence already exists (Check 2g / 4c / 4f, the +9.99 pp negative-test story). Zero new build, strongest differentiation. |
| 2 | #5 Determinism vs judgment | Natural sequel; the LLM-vs-deterministic split per pipeline is the number. |
| 3 | #2 Evals | Forces a build already owed — unit tests for the deterministic core is on the engineering-health backlog. |

First two are write-ups of what exists. The third makes the track pull its weight.

### 8.5 Standing capture rule

**When any session produces a number that measures the active AI PM topic, append it to
`ai_pm_register.json` before the session ends.** The active topic is named in `CLAUDE.md` so it is
always in context — memory retrieval alone is not reliable enough for a standing rule.

Rotating the active topic each month is a one-line edit in `CLAUDE.md` plus a status change in the
register.

---

## 9. X / Twitter — out of scope (revised 2026-07-21)

**This layer serves Substack and LinkedIn only.** X is reactive: what is worth saying depends on
what is already being discussed, so it cannot be put on a calendar and it does not fit the
slot → category → slate shape everything else here uses. It needs a design of its own, and does
not have one yet.

The reply desk (`analysis/replydesk/`) was the previous answer and is **retired to
`analysis/legacy/replydesk/`**. The evidence was decisive: `reply_log.json` was never created, so
in the 17 days it existed no reply was ever run through it. Keeping it would have meant carrying a
standing obligation — every new signal family routed into its `TOPICS` table — for a ritual nobody
ran. That obligation, stated in the previous version of this section, is **void**; the 17 relational
signals never routed are no longer a gap.

**What survived the retirement.** The reply desk held `SEBI_BANNED`, the only investment-advice
guardrail in the codebase. That is a compliance control, not a channel preference, so it moved into
`slot_render.lint_compliance` and now runs against **both** the blurb and the design prompt — the
latter matters because a design prompt becomes a public pager in a session outside the gate. Before
this move, LinkedIn output had no SEBI check at all.

**Open:** X needs its own treatment. When it gets one, the honest starting question is not "how do
we generate posts" but "what makes a reply worth posting at all" — the previous attempt answered
the second question well and still went unused, which is itself the most useful datum available.

---

## 10. Blurb voice

Indian conversational English. Plain. The blurb's job is to say what happened and what you noticed —
not to explain why it matters in consultant register.

**Rules**
- Short sentences. One idea each.
- Indian number words: lakh, crore. Never billion.
- Say the thing plainly. State the number, state what's odd about it.
- **Banned register:** "firing on all cylinders", "robust", "yield optimisation", "unlock",
  "headwinds/tailwinds", "poised to", "double down", "at an inflection point".
- No rhetorical questions as openers. No "Here's why that matters."
- It's fine to end on an observation rather than a conclusion.

**Reference sample** (1st-of-month, C1):

> RBI's May credit numbers are out.
>
> Bank credit is growing at X% — the slowest in N months. Gold loans crossed ₹X lakh crore and are
> still the fastest growing thing on the books.
>
> On the payments side, debit cards in force went up but spending on them came down. Those two
> usually move together, so that's worth watching.
>
> Full breakdown on Substack.

**Known upstream conflict:** card bodies currently carry eval-prompt consulting-speak from the
domain eval system prompt. The proper fix is the tone rule in prompt v1.12 at the next evaluate run
— not hand-editing validated artifacts, and not a scrubbing pass in the renderer. Until v1.12
lands, blurbs generated from card text will inherit the register problem.

---

## 11. Newsletter

### 11.1 Post 1 — merged monthly summary (1st)

SIBC and payments in **one issue**. For a list this size, two issues split attention for no gain.

Two conditions:

1. **State the data-month offset.** The pipelines run on different release clocks. If the issue is
   "credit through May, payments through April", say so in the issue. Do not smooth it over.
   Confirm the actual offset before finalising the template.
2. **The merge must be earned.** Two stapled halves is worse than two emails. The thing only a
   merged issue can do is the **cross-read** — constructs, eco-edges, the CC-balance-per-card
   reconciliation constraint. Structure: two clearly dated halves + one cross-system paragraph
   that neither pipeline could produce alone. That paragraph is the reason the merge exists.

Template/structure review is a separate working session, done against actual current output rather
than in the abstract.

### 11.2 Post 2 — deep read (14th)

The current generator renders what fired. That is a feed, not an essay. The design gap is
**selection**.

Structure: **one spine question + three supporting movements + one thing we're watching.**

The spine is human-chosen from a deterministically ranked candidate list (largest status flips,
widest relational gaps, newly-active opportunities). Everything beneath it is grounded cards. The
machine shortlists; the human picks; nothing ungrounded enters.

---

## 12. Phasing

All six slots stand up together (decided 2026-07-21). Cadence credibility comes from never missing,
so the fallback rules in §4 carry the load on thin months.

Build order within that — **steps 1–4 built 2026-07-21**:

| # | Step | Where it landed |
|---|---|---|
| 1 | Shared source layer + ledger | `distribution_sources.py`, `ledger.py`, `categories.py` |
| 2 | C1 / C2 / C3 / C6 / C7 | selectors in `generate_slot.py` over one renderer |
| 3 | C8 proximity-to-threshold | `signals/proximity.py` — signal layer, registry-driven |
| 4 | C9 corrections | `distribution_sources.corrections` — ledger + registry retirements |
| 5 | AI PM register wiring | seeded; the monthly habit is §8.5, not code |

### One renderer, ten selectors — not five renderers

Step 2 says "renderers", and building five of them would have been the literal reading.
It is the wrong shape: the categories differ in *what they select*, never in *how it is
rendered* — every slot emits the same two artifacts in the same format. So there is one
renderer (`slot_render.py`) and one selector per category. Adding a category is a branch in
`select()` plus a row in `categories.py`; adding a slot is a row in `CALENDAR`. Neither is a
new code path, which is the same reason the categories are data rather than functions.

### The partition is enforced, not documented

`categories.METHOD_CATEGORY` maps every Layer-1 compute method to its category, and
`generate_slot.py` refuses to run if the registry contains a method the partition does not
cover. A new compute method must be classified deliberately — silently defaulting into C1 is
exactly how two slots would start telling the same story.

---

## 13. Reconciliations (closed 2026-07-21)

### 13.1 `FABLE_BRIEF_cross_segment_insights.md` posts 2/3/4 — resolved

The brief's consumption contract predates this spec and its calendar conflicts with §4. Resolution:

| Brief post | Brief's slot | Resolution |
|---|---|---|
| 2 — "how the SIBC ecosystem is changing" | 7th | **Folded into the 7th slot (C2+C3).** Not a separate generator. |
| 3 — "how the payments ecosystem is changing" | 14th | **Folded into the same 7th slot.** The 14th belongs to C6+C7. |
| 4 — "bank-specific highlights" | 21st | **Not a distribution slot.** The 21st is C10 (AI PM). |

Rationale:

- **Categories are pipeline-agnostic; slots own categories, not pipelines.** The brief split by
  pipeline (SIBC on the 7th, payments on the 14th) because at the time rotation/divergence existed
  only as a proposal. They are now live on *both* pipelines through one mechanism
  (`core/relational_insights.py`, four compute methods, twelve L1 signals). Splitting the output by
  pipeline would re-introduce the per-pipeline duplication the platform's engineering principle
  forbids — and it would put the same category in two slots, which is exactly what §2's partition
  exists to prevent. One 7th-of-month slot renders rotation + divergence across both pipelines.
- **The brief's "generators still don't exist" item is therefore the 7th-of-month renderer** —
  the C2/C3 selectors in this layer. There is no separate cross-segment generator to build.
- **Brief post 4 (per-bank anomaly + on-demand lookup) is a capability, not a slot.** Its
  anomaly-surfacing half already ships as `csv_bank_divergence` and flows into C3. Its on-demand
  lookup half was the reply desk's `lookup` pattern — and the reply desk is now retired (§9), so
  that half is **unowned**. It was never built and was never used; if per-entity lookup is wanted
  again it is a small job over `distribution_sources.py`. Either way it is not a calendar slot,
  and the 21st is spoken for.

The brief remains authoritative for the *signal layer* work it specified (all shipped). Its
five-post consumption contract is superseded by §4 of this document.

### 13.2 SIBC ↔ payments data-month offset — measured

Measured from `rbi_sibc/timeline.json` (release date per data month) and
`rbi_atm_pos/timeline.json` (ingestion timestamps, which upper-bound publication):

| Pipeline | Rule | Evidence |
|---|---|---|
| SIBC | data month M releases on the **last day of M+1** — clockwork | 8/8 periods: May 2026 → 2026-06-30, Apr → 2026-05-29, Mar → 2026-04-30, … |
| ATM/POS | data month M publishes **~M+2, irregular** | Mar 2026 → ingested Jun 4 · Apr → Jul 3 · May → Jul 21 |

**Consequence for the merged template (§11.1): the offset is normally one data month on the 1st,
occasionally two — and it is never assumed.** On 1 Aug the credit half carries June data (released
31 Jul) while the payments half carries May (June payments typically lands in the first week of
August, i.e. after the issue). Right now both pipelines happen to sit on May 2026 because the May
payments file landed today; that coincidence must not be baked into the template.

The generator therefore **reads each pipeline's data month from its own artifacts every run** and
renders the vintage line from what it found (`distribution_sources.data_vintage`). The issue always
states both months explicitly, and states the gap in months when there is one.

## 14. Open items

- Eval prompt v1.12 tone rule — blocks clean blurb voice (§10).
- Design-prompt subset checker (§5.1) — deferred; the prompt now emits a machine-readable
  `supplied numbers` block, so the check is buildable without changing the format.
- **Upstream: `generate_opportunity_narrative` prints raw floats** ("120454115.0 credit cards",
  "12.0 periods"). The blurb lint (`slot_render.UNFORMATTED`) rejects those outright, and `_lede`
  quotes a different sentence rather than tidying one — but the fix belongs in the narrative
  generator's formatting, not here. Until then some C6/C7 sentences are simply unquotable.
- **C10 has no generator, by design.** The AI PM post is assembled by hand from
  `ai_pm_register.json` (§8.1); `select("C10")` returns nothing, so the 21st falls back to C9 and,
  when that is empty too, skips and records the skip. That is correct behaviour, not a gap —
  but it means the 21st needs a human before it publishes.
