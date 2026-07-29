# Distribution Spec v1.5

> Authored design for content distribution across newsletter, LinkedIn, X, and the AI PM track.
> Status: **built** (2026-07-21) — §12 steps 1–4 live; §8 register wiring is the monthly habit.
> **v1.2 (2026-07-23):** §11.1 monthly-issue template aligned — no forced cross-read, two
> data-shaped halves, deterministic measured "reads" selector, per-output gate contract.
> **v1.3 (2026-07-23):** §11.2 deep-read template aligned — computed floor (bank rotation/
> divergence) + editorial spine(s) chosen from a machine-ranked option list; two gated source
> refs per spine (bank-level why + independent corroboration); mermaid for loops/constraints;
> theme-level non-repetition. Screenshot-placeholder convention specced for both formats.
> Both are design sessions — the builds (harness fix first) are still ahead.
> **v1.4 (2026-07-23):** §5 LinkedIn slot content aligned — vintage honesty, "so what" = observation
> not advice/forecast, and §5.3 resolves lint scope across surfaces (design prompt gets the full
> prose lint; no-forecast hard-fails; warn-card / fail-ours split; SEBI precision-fix-first). All
> three formats now specced. Next: build, harness fix first.
> **v1.5 (2026-07-29):** §11.2-R deep-read revision — the read must read like a person wrote it.
> One shared prose/voice layer across all surfaces (build once, reuse); the diagram is representation
> over the system model, never synthesised; bank "why" is tiered S4a sourcing (official / reputed
> reports / named-press allowlist), WebFetch-verified, cost paid once and cached. Design agreed;
> Part 1 (prose + diagram) then Part 2 (S4a sourcing) — builds ahead.
> Run it: `python3 analysis/distribution/generate_slot.py --slot 7th` (or `--all` to rehearse
> a whole month). Every slot self-gates; see `validate_distribution.py`.
> Related: `NEWSLETTER_CONTEXT.md` (long-form channel) · `analysis/legacy/replydesk/` (X, retired — see §9)

---

## 1. Governing principle

Distribution is a **rendering problem over artifacts the pipelines already compute** — not a
second content system. One content spine per monthly cycle, many renderings. The channel changes
*length, framing, and selection*; it never changes *where the number came from*.

This means:

- One shared source layer (`distribution_sources.py`, which absorbed the newsletter's) reads only
  gate-validated artifacts: `signals.db`, `sibc_l1_annotations.json`, `atm_pos_insights.json`,
  `opportunities_feed.json`, `ecosystem_model.json`.
- Per-channel renderers sit on top. No renderer re-derives a number.
- One traceability gate (`validate_distribution.py` — `check_doc` for long-form, `check_slate`
  for slots) covers all channels.

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
- a **vintage line** stating each pipeline's data month and the gap between them — read per run,
  never assumed (§13.2). Do **not** print "both halves are on the same data month" as a template
  constant; that is true only when the two releases happen to coincide.
- the grounded numbers, **verbatim** from validated artifacts, each with its label and unit
- the intended narrative arc for the pager
- for each claim, a **"so what" line that is an *observation*, not advice and not a forecast** —
  it says what is *notable* ("gold's share is climbing fastest"), never a recommendation ("banks
  should…") and never a prediction ("on track to double digits within two quarters"). Same prose
  rule as the newsletters (§11). Deterministic cards (rotation/scan) already read this way; LLM
  scalar cards inherit consulting-speak and forecasts until eval prompt v1.12 lands.
- page count
- a hard constraint block: **use only the numbers in this prompt; invent nothing; do not
  compute new figures from these numbers**

**The design session sits outside the gate.** Every other public surface on this platform is
number-traced. A pager built in a fresh session is the one place a fabricated figure could reach
the feed. Therefore the prompt must be *closed* — self-contained, with no invitation to look
anything up or derive anything. And because the pager **is** a public surface, the prompt's own
prose is linted, not just its numbers — see §5.3.

No screenshot placeholder here (unlike the newsletters, §11): the design session builds *original*
visuals, so the prompt is a brief, not a slot to drop a dashboard screenshot into.

Future hardening (not v1): a checker that the returned pager's number set is a subset of the
number set the prompt supplied. Design the prompt format now so that check is possible later —
i.e. emit the supplied numbers as a machine-readable block alongside the prose.

### 5.2 `blurb.md`

The LinkedIn copy that accompanies the pager. Generated, not hand-written. Voice is §10 — opener as
a plain statement, 3–4 one-idea lines, close on an observation or the Substack funnel. §10 voice is
largely working today; the weak spot is C6/C7, which inherit raw floats from
`generate_opportunity_narrative` (§14) and read mechanically.

### 5.3 Lint scope — which rule applies to which surface (aligned 2026-07-23)

A rule attaches to a **risk**, not to whichever surface happened to introduce it. Three risks, three
scopes — the design prompt is in scope for all of them because it becomes a **public pager**:

| Rule | Risk it guards | Blurb | Design prompt | How a hit is treated |
|---|---|---|---|---|
| **SEBI / compliance** | reads as investment advice | ✅ | ✅ | hard fail (see note on precision below) |
| **No-forecast** | predicts, on a surface that declares "no forecasts" | ✅ | ✅ **hard fail** | self-consistency failure — the prompt's own constraint block forbids it |
| **No-advice** | recommendation voice ("banks should…") | ✅ | ✅ | **warn** inside a verbatim card body (feeds the v1.12 fix list); **hard fail** in generated so-what/blurb text |
| **Banned register** | consultant-speak (§10) | ✅ | ✅ | same warn-card / fail-ours split |
| **Unformatted number** | raw float reaches a reader (`1358241.0`) | ✅ | ✅ | hard fail everywhere — no case where a raw float is correct |

The warn-vs-fail split is the same one the newsletters use: a hit inside **verbatim card prose**
(eval output, which §11 forbids hand-editing) is a **warning** carrying the card id, so it feeds the
eval-prompt v1.12 fix; a hit in text the **renderer generated** (so-what lines, blurb) is a **hard
fail**, because that text is ours to fix now.

**SEBI precision is a prerequisite, not done here.** The current list is substring-matched and trips
on ordinary lending English (`buy cars`, `invest in systems`, `cross-sell`, `buy-now-pay-later`) while
its securities-specific terms (`multibagger`, `target price`, `stop loss`) are safe. Widening the SEBI
lint onto a new surface must be preceded by the precision fix (require an advice frame, not a bare
substring) and **measured — catch + false-rejection rate, before and after** (the standing AI PM
rule). Until then the SEBI lint stays where it already is; do not widen it blind.

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

### 11.1 Post 1 — monthly issue (1st)

**BUILT 2026-07-23** — `analysis/distribution/issues/monthly_issue.py` (merged, two halves, no
forced cross-read). Reads selector is the deterministic `signals/is_news.py`. Word-vs-number
agreement + advice/forecast prose lint live in `validate_distribution.py`
(`word_number_conflicts`, `prose_lint`). The per-pipeline `merged_issue.py` is retired to
`analysis/legacy/`. Industry-total YoY signal confirmed = `sibc-industry-yoy`; tiles show level +
YoY, no standalone status word. Measured (per decision point + scope band) and logged to
`ai_pm_register` topic #1. **Built to spec (the full grouped flip table, Option A);** the
flip-table noise finding is recorded in §14 as an improvement, not silently changed.

**Template aligned 2026-07-23 (design session).** The per-pipeline
`--pipeline sibc|atm_pos` generator is now **legacy** — it produced one issue per pipeline; the
monthly issue is a single issue with a credit half and a payments half. Retired to `legacy/` (not
a fallback).

**Design decision — no forced cross-read (reverses the earlier v1.1 rule).** The prior spec
mandated one cross-system paragraph "that neither pipeline could produce alone." We dropped it: a
forced merge paragraph is worse than none, and the genuine cross-system material already has two
proper homes — `/opportunities` and the deep read (§11.2). The monthly issue is **two sections,
each shaped by its own data**, under one masthead. The merge is in the *envelope*, not forced into
the prose.

**What it is.** The one email a lending subscriber gets on the 1st: what RBI's credit and payments
data said this cycle. **Backward-looking only** — no watch, no proximity, no "could turn next
month" (that is the deep read and the 28th slot). ~4 minutes.

**Reader.** Someone in lending — credit / product / risk at an NBFC, bank, or fintech — who did not
open the dashboard. Assume they know what a personal loan and a POS terminal are; do **not** assume
they know "non-food credit," "base effect," or "yield."

**Opening.** `India Credit Lens — credit and payments, {month}` + a vintage line stating both data
months and that the two RBI releases run on different clocks. Offset is read per run, never assumed
(§13.2).

#### Credit half

The dataset is **one measure (outstanding ₹) over a hierarchy**, so its only question is *which part
of the tree is moving*.

1. **The level** — 3 tiles: **Bank credit** (total) · **Personal loans** YoY · **Industry** YoY.
   No food/non-food anywhere — it is jargon. (Confirm the exact industry-total YoY signal id at
   build; there are by-size and by-type cuts.)
2. **How each sector is growing** (revised 2026-07-23) — a **table grouped by parent sector**
   (Bank Credit · Agriculture · Industry · Services · Personal Loans · Priority Sector), one row per
   sub-sector showing **YoY growth %**, with a marker (▲/▼ *turned*) on the sub-sectors that changed
   **regime** (grew↔shrank) this cycle — NOT the accelerate↔decelerate wobble, which fires on ~half
   the signals every month and is noise (§14). Everything is shown, grouped; the movers are flagged,
   not isolated. This replaces the earlier "every status flip" list (that list was mostly wobble and
   was not what a reader expects — they expect the state of every sector, with rates). A **volume
   column (₹ L Cr)** is a fast follow: it needs per-sector `-abs` signals (only four sectors carry one
   today), so v1 ships YoY-only and adds volume once those signals exist.
3. **Where the mix is shifting** — rotation (`csv_sector_rotation`), honest-null below 0.5pp mass.
   Written as **fuller conversational prose, not a terse template** (revised 2026-07-23): name the
   biggest gainer and giver, say the direction in plain words, and add a "put simply" gloss — e.g.
   "Within services lending the mix is tilting toward NBFCs: their slice grew 3.4 points over the
   year while other services gave up 2.1. Put simply, a bigger share of every rupee lent to services
   now goes to finance companies."
4. **The reads** — **editor-picked from a machine-ranked shortlist** (revised 2026-07-23), one chart
   each. The is-news score (below) *ranks* the candidate cards; it does not auto-select them. The
   generator runs `--shortlist`, which lists the ranked candidates per half; the editor picks a couple
   with `--credit`/`--payments` (same human-in-the-loop pattern as the deep read's `--spine`, and the
   same determinism-vs-judgment boundary, AI PM topic #5). *Which* reads carry the issue is editorial
   judgment; the machine only says which changed most. Unattended (no picks), it falls back to the top
   2 by score so the pipeline still runs. Verbatim card **title + body only — the prescriptive "So
   what" implication is dropped**: the monthly issue is descriptive and backward-looking, so an advice
   line ("lenders should…") is out of place and out of voice here. Prescription lives in the deep read
   and /opportunities.

#### Payments half

The dataset is **many measures over the same entities**, so its question is the opposite one: *do
the measures agree*, and *which banks stand out*.

5. **The level** — 3 total tiles (cards in force · card spend · POS terminals) + a **top-5-banks**
   sub-line on the same dimensions.
6. **Fleet vs usage** — pair gaps (`csv_pair_divergence`), overall. Written as **prose, not raw
   signal titles** (revised 2026-07-23): each pair carries two plain-language side labels and a "what
   the gap means" clause — "Banks kept issuing debit cards, but people are using them less: the number
   of cards grew 2.8% over the year while spending on them fell 4.3%, a 7-point gap between having a
   card and using it." Never the registry title with "(YoY gap, pp)" showing through. Honest-null
   outside the ±3pp band.
7. **The biggest banks** — top 5 banks per dimension, rendered as a **table** (revised 2026-07-23).
   The three dimensions are **credit cards in force · debit cards in force · POS terminals** — all
   per-bank *counts* (`cc/dc/pos-bank-scan`). There is **no per-bank (or total) card-spend signal**,
   so there is no spend column (§14); the earlier "cards issued / card spend" labels were wrong — the
   scans are stocks in force, not flows or value. **No divergence framing** here — that is deep-read
   material. RBI does not publish sectoral credit per bank, so no credit equivalent.
8. **The reads** — editor-picked from the is-news shortlist + chart, exactly as the credit half (#4).
   Title + body only, implication dropped.

**Closing.** Dashboard link · How this is made.

#### Charts are screenshot placeholders

Every chart in the issue is a **placeholder carrying a reproducible recipe** — dashboard path + view
+ highlight (e.g. `indiacreditlens.com → Industry by Size → YoY % view → highlight: Large`) — so the
editor takes the exact screenshot before sending. The generator never embeds an image; it emits the
recipe and a `> 📊 [CHART — replace with screenshot]` marker. Same convention in the deep read (§11.2).

#### The reads selector — deterministic and measured

Today's generator takes feed order; that is the weakest part of it. A card qualifies as a *read*
only if it is **news**, scored on four factors, all computable from `signals.db`:

1. **Record / extreme** — all-time high/low **on a reversal-capable series**. A new high on a
   monotonic series (total outstanding rises every month) is arithmetic, not news, and scores zero.
2. **Regime flip** — status crossed grew↔shrank↔flat this cycle. **Not** the accelerate↔decelerate
   wobble within the growing regime, which fires on ~half the signals every month (§14).
3. **Just crossed** — a status threshold was crossed this period (the backward twin of C8).
4. **Magnitude** (added 2026-07-23, reco (b)) — the signal moved much more than its own typical
   month (> 2× its median period-over-period move). Without it the selector answers *"did this change
   state"* but misses a big, genuinely interesting move that sets no record and flips no regime —
   measured, the three-factor version caught only **54.5%** of the month's largest movers. Magnitude
   closes the gap between "changed state" and "moved a lot", which is what a reader means by a
   headline read.

**Score = 2·record + 2·regime-flip + 2·magnitude + 1·crossed.** The score **ranks** candidates; it
does not auto-select. The editor picks the couple that carry the issue from the ranked shortlist
(`--shortlist` → `--credit`/`--payments`) — the machine says what changed most, the human says what
matters. A read must clear a **strong** factor (floor 2.0) to appear on the shortlist as news —
`just crossed` alone is never a read; a structural template ("Power is 57% of infrastructure") scores
zero on all four and never surfaces. Unattended, the top 2 by score are used as a fallback. This is the same *is-this-news* problem the dashboard read-mode notes flagged; the
classifier built here is the one the dashboard reuses. **Per the standing AI PM rule it ships with a
measured catch / template-reject rate** — no selector gate lands on prose alone.

#### Honest nulls

Every section can come up empty — rotation below 0.5pp, no pair gap outside ±3pp, fewer than 2 cards
clearing the is-news floor. When it does, **say so plainly and move on. Never pad a section because
the template has a slot for it**, and never fake a read.

#### Partition — mechanical, not editorial

The issue reads `signals.db` (**Layer 1 only**). It never contains: forward-looking claims,
system-model items (constructs / loops / opportunities / risks), or a spine. Enforced by
compute-method + layer, exactly as `categories.py` enforces the slot partition — not by editorial
judgment. The within-Substack no-overlap rule against the deep read (§11.2) holds **by construction**
because the deep read is Layer 2/3.

#### Prose

Indian conversational English. Short sentences, one idea each. Lakh/crore, never billion. State the
number, say what is odd about it, stop. No consulting register (§10 banned list), no advice voice
("lenders should…"). The renderer **never hand-edits validated card text** — register problems in
card bodies are fixed upstream at eval prompt v1.12, not scrubbed here.

#### What's checked (this output's gate contract)

| Axis | How | Honest limit |
|---|---|---|
| **Numbers** | Every figure traces to `signals.db`, **per-block scoped**, via `check_doc` + the `DISTRIBUTION` policy. | The measurement harness only ever injected the **first** `p` block (handoff §1.1). **Fix `measure_groundedness.py` to inject every eligible block before any before/after** — the current 100%/99.5% measures one decision point, not the issue. |
| **Word-vs-number agreement** | **New check.** A status word next to a value must not contradict it (the `up, −2.6% YoY` class — see §11.2 / the direction-render decision). | A traces-but-contradicts defect is invisible to the number gate; this is the first non-number-tracing check since Check 2g. |
| **Prose** | Banned-register + no-advice lint. | Machine floor only; the source fix is upstream (v1.12). Lint scope across surfaces is still being settled (§14). |
| **The reads selector** | Its own catch / false-rejection rate, before and after. | — |

#### Measurement & reporting obligation (AI PM topic #1)

The gate contract above says *what is checked*. This says *what must be measured and logged* — they
are different, and the second is the standing rule (CLAUDE.md §8.5): **topic #1 is ground-truth
scoping, and no number that measures it may be left unlogged.** Building the monthly issue produces
exactly such numbers, so building it without appending them is an incomplete build.

Report these per build, per half (credit / payments) and **per decision point — never one
issue-level headline** (a pooled number is the exact mistake the gate has no pooled ground truth to
avoid):

| Metric | What it answers | Where it comes from |
|---|---|---|
| **Scope width per block/claim** | Is the candidate set small enough for a pass to *mean* something? Any block scoping to four figures is **unmeasured, not safe**. | `declared_ground_truth` per block — cheap, no injection. The *leading* indicator. |
| **Catch rate** — near-miss + in-range | Share of injected fabrications the gate rejects. **Injected at every eligible block**, not the first (handoff §1.1 — fix the harness before trusting any number). | `measure_groundedness.py`, per decision point + per scope band. The *lagging* indicator. |
| **False-rejection rate** | Share of legitimate numbers the gate wrongly rejects. | same harness. |
| **The reads selector** — catch / false-rejection | Does the is-news score admit real news and reject templates? | the selector's own negative test. |
| **Word-vs-number agreement** — catch rate | Does the new contradiction check fire on the `up, −2.6%` class? | the new check's negative test. |

**Append to `ai_pm_register.json` `topics[].measurements[]` at build time**, each with
`metric / value / date / how_measured / source`. **Admission rule: a value AND a source file — no
entry on prose alone.** Anything qualitative (a failure mode found, a harness bias) goes to
`observations[]`, not `measurements[]`.

**Logging is not retrospective.** The register fills as a byproduct of the build that produces the
numbers — it is not backfilled from prior analysis. The plan is to add the logging *mechanism* while
auditing decision gates and ground truths during the build, so the entries are generated where they
are measured. (The one standing exception the spec still names is the D2 correction — that the
existing 100% / 99.5% figures measured **decision point D2, one zero-scope block per doc, not the
gate**. It is C9 corrections material for the distribution track regardless of whether it is entered
into the register. Whether to log it is a build-time call, not a debt this template asserts.)

#### Open at build (not blocking the spec)

- **Tile status word.** A tile shows a *level* (`1.2 crore POS terminals`); today it prints
  `(accelerating)` next to a level whose *rate* is falling — same contradiction class as the
  direction bug. Likely resolution: tiles show **level + YoY, no standalone status word**. Decide at
  build.
- **Industry YoY signal id** — confirm which registered signal is the industry total (by-size vs
  by-type cut).

### 11.2 Post 2 — deep read (14th)

**BUILT 2026-07-28** (template aligned 2026-07-23). `analysis/distribution/issues/deep_read.py` —
`--shortlist` ranks spine candidates, `--spine 1,3` picks, no pick → top spine (unattended). Part A
computed, Part B editorial. Self-gated (per-block traceability incl. the D1 basis-scope fix + the
word/number + prose lints + the bank-sourcing store gate), measured (basis-line scope cut ~35× to a
65-value median with 99.7% in-range catch held), 14 unit tests. The deep read is **not entirely
automatable, by design** — it is an editorial product with a human editor. Structurally it is **a
computed floor plus an editorial spine**: one part always computes and needs no judgment; the other is
a question (or questions) the editor chooses from a machine-ranked list.

**What it is.** Not a second scan — the 1st already reported what moved. The deep read takes **one or
more questions that have been building across the data** and answers each with sourced evidence.
~7 minutes.

**Reader.** The same lending reader, opted into depth on the 14th. Still no jargon.

**Why it can't overlap the 1st.** It reads the **system model** (Layer 2/3) — forces, opportunities,
risks, loops, constructs, constraints — plus bank-level L1 rotation/divergence that the monthly issue
deliberately does *not* carry. The binding rule is **non-repetition** (a signal appears in at most one
Substack post per month; a spine *kind* does not repeat within ~6 months), not a rigid layer wall.
Because bank rotation/divergence was dropped from the 1st (§11.1 §7), it is free to anchor the deep
read.

#### Part A — Banks this month (fixed, computed, no human decision)

Always present. Fully deterministic from L1 bank signals (`csv_bank_divergence`,
`csv_category_rotation`, bank scans). The **only** build-time input is *which banks to show* — a
priority ranking (biggest divergence, biggest share move), not an editorial call.

- **Who's rotating** — bank-category share shifts.
- **Who's diverging** — banks pulling away from their own category (flagged rows only).

#### Part B — The spine(s) (editorial; the editor chooses)

Human-in-the-loop on purpose — *which question matters this month* is judgment (the
determinism-vs-judgment boundary, AI PM topic #5).

1. **Options — machine.** `deep_read.py --shortlist` hands the editor a **ranked list of candidate
   spines** drawn from L2/L3, each tagged with the question, the elements that support it, whether it
   rests on a loop/constraint (→ diagram), and its **freshness** (down-ranked if the same *kind* ran
   recently). Sample:

   ```
   SPINE OPTIONS — deep read, May 2026 (ranked)

   1. [eco-loop]   "Is the card boom real, or just existing users spending more?"
      supports: unsecured spend–stock loop (running) · CC flow-leads-stock ·
                PSB card under-issuance (23.8% vs 70.9%)
      diagram: YES (reinforcing loop)     fresh: not done in 6 months
   2. [force]      "Why are banks eating finance companies' gold-loan lunch?"
      supports: gold-price-surge force (RBI SGB) · risk-weight-hike force ·
                gold loans +105% / 12-month streak
      diagram: no                         fresh: SPINE USED Mar 2026 → down-ranked
   3. [constraint] "₹24,951 outstanding per card — stretched or normal?"
      supports: cc-balance-per-card constraint · CC outstanding · cards in force
      diagram: YES (reconciliation constraint)   fresh: never used
   ```

2. **Pick — editor.** `--spine <id>` — **one or more.** The editor may run several spines in one issue.
3. **Enrich — machine.** For each chosen spine, attach the two source references below.
4. **Diagram — machine.** If the spine rests on a **loop or constraint**, render a **mermaid diagram**
   inline to explain it (not a screenshot).
5. **Guard — machine.** Enforce no repeat of the same spine *kind* vs recent issues — ledger-tracked,
   ~6-month window. A long-running "active" opportunity falls down the shortlist the longer it runs
   unless its *story* changed.

#### Two source references per spine (both gated — never a raw LLM claim)

Beyond the computed basis, every spine carries:

1. **Bank-level sourced claim** — the *why* behind a featured bank's move, sourced for key banks
   (top 5 public + top 5 private, count tuned to API cost). **The one genuinely new build.**
2. **Independent corroborating reference** — a second reliable external source saying the same or a
   similar thing (RBI bulletin, rating-agency note, mainstream financial press). The point is
   triangulation: *we are not the only ones seeing this.*

Both go through the **S4 sourcing gate** (URL, excerpt, verified date; never auto-promoted, never an
ungrounded paraphrase). The template reserves both slots now; the bank-level sourcing engine is a
follow-on (Fable-tier mechanism work). Until it lands, a spine falls back to its computed basis + the
system-model force already attached, and the corroborating reference is added by hand.

#### Published shape

```
Masthead + the chosen spine question(s)
  Why this question now   spine card + sourced why + corroborating ref
                          + [mermaid diagram if loop/constraint]
  Bank angle              sourced claims for key public + private banks
  [second spine, if chosen — same shape]
── Banks this month ──    Part A, always present: who's rotating · who's diverging
  What we're watching     one C8 proximity line (level edges only)
  Closing                 /opportunities link · How this is made
```

#### Charts and diagrams

Charts follow the **screenshot-placeholder** convention of §11.1 — a reproducible recipe plus a
`> 📊 [CHART — replace with screenshot]` marker, so the editor takes the exact screenshot. Mermaid
diagrams for loops/constraints render **inline** (they are generated, not screenshotted).

**Mermaid render lives in the distribution layer — not referenced from legacy.** DONE (2026-07-28):
`analysis/distribution/mermaid.py` is a focused loop/constraint renderer (two shapes, ~120 lines);
the 821-line legacy system-model/subsystem generator was **deleted**, not archived — no lingering
cross-reference into `legacy/`. Same discipline the platform applied to the reply desk and newsletter
v1: a capability that becomes live moves into the live layer; it is not consumed from the archive.

#### Honest nulls · prose · direction render · gate · measurement

- **Honest nulls** — if no spine kind is fresh, or Part A has no flagged divergence, say so plainly.
  Never pad a movement or invent a spine to fill the shape.
- **Prose** — identical to §11.1 (Indian conversational, short sentences, lakh/crore, no consulting
  register, no advice voice).
- **Direction render** — the "how we know" basis lines show the **observed** value; when a member is
  moving *against* its authored polarity, tag it `(moving against)` rather than printing a word that
  contradicts the number. Fixes the live `up, −2.6% YoY` bug.
- **Gate contract** — same table as §11.1, **plus the D1 scope fix**: each basis line scopes to the
  member's *own* signal, not the driver's whole `evidence_all` (handoff §2, D1 — the widest scope in
  the pipeline, med 2,258 values). Expect numbers that pass loosely today to start failing; that is
  the gate working, and the prose tightens in the same increment.
- **Measurement/logging** — same obligation as §11.1: built-time, per decision point, non-retrospective.

#### Known blocker (carried)

`generate_opportunity_narrative` prints raw floats (`120454115.0 credit cards`, `1358241.0 micro
ATMs`, `12.0 periods`). Worst in this format because it is opportunity-narrative prose. Fix is
upstream formatting, not this template (§14).

---

### 11.2-R — v1.5 revision (2026-07-29): the read must read like a person wrote it

The first build (2026-07-28) got the *skeleton* right — computed floor, editorial spine, gated
numbers — but the *prose* still read like machine output: `A → B: running` basis lines, a terse
jargon "so what", a 3-node triangle drawn as if it were an insight, and an empty "Bank angle" with
no real sourcing. A 7-minute editorial read for a lending audience cannot read that way. Three
mechanisms fix it, and each is **built once and reused**, not bolted onto this one template.

#### R1 — One prose layer, every surface (`analysis/core/voice.py`)

The voice is not a deep-read concern; it is the platform's reader-facing voice, and it appears in the
two monthly issues, the LinkedIn blurbs, the deep read, **and** the LLM-sourced why (R3). Today its
rules are scattered — `slot_render.lint_compliance`/`BANNED`, `validate_distribution.prose_lint`,
`relational_insights` prose, `core.traceability`. That is exactly the parallel-copy the platform
forbids. Consolidate into **one voice layer** that every generator calls:

- **The voice, defined once.** Indian conversational English; short sentences; lakh/crore never
  million/billion; no consulting register (`BANNED`); no advice or forecast verbs in the machine's own
  words; understandable by a reader with basic lending experience and no analyst jargon
  (`non-food`, `base effect`, `yield`, `entrenched`, `firing on all cylinders` are all out).
- **The lint, once.** `voice.lint(text, mode) → (hard, warn)` subsumes both existing linters. Every
  surface — deterministic template *and* LLM output post-check — runs the same lint.
- **Conversational builders, once.** Small helpers turn a *gated fact* into a plain sentence
  (`voice.change(...)`, `voice.level(...)`, direction phrasing, "put simply"). The deep read's basis,
  intros and "so what"; the monthly issue's rotation/pair lines; `relational_insights` — all render
  through these, so the voice cannot drift between surfaces.
- **What does NOT move**: number grounding stays `core.traceability`; measurement stays
  `measure_groundedness`. Voice sits beside them, not on top.

Applied to the deep read:

- **Basis → sentences.** `Unsecured retail credit appetite → Credit card spend: running` becomes
  *"Appetite for unsecured credit is showing up as more card spending; that spending piles up as
  bigger card balances; and those balances are themselves a sign the appetite is real."* Numbers stay
  scoped to their own member signal (the D1 fix holds); only the *wording* changes.
- **"So what" = a plain observation, not a prescription.** The machine says what it means for a
  lender, in plain words, with no advice/forecast verb. The sharp, prescriptive take stays the
  **editor's** — the handwritten/reMarkable layer (the machine deliberately withholds it; that gap is
  the human's, per the strategic note). This is a design boundary, not a limitation.
- **What is replaced vs kept.** The machine-y basis lines (`A → B: running`) and the boilerplate
  implication (`Move on this while the trend is still running in your favour` — backwards on a risk)
  are **dropped**, replaced by the voice-rendered read + the plain "so what". The one thing kept
  verbatim is the **substantive validated body** — for #8, *"merchants who drop POS terminals cannot
  accept international cards, EMI, premium credit-card features…"* — because that is real, gated depth,
  not consulting-speak, and rewording it would forfeit the verbatim guarantee. Consulting register
  that does slip into a body still **warns** (never hand-edited; fixed upstream at eval v1.12). The
  title is dropped (the heading names the subject; the feed title carries a dashboard-state suffix).

**Ground truth + control (non-negotiable, same as everywhere).** Every voice-rendered block carries
its signal scope; the injection harness measures catch across **all** surfaces, reported per surface;
the voice lint is negative-tested. No prose ships on "reads nicely" — it ships on a measured catch
rate and a passing lint, like every number does.

#### R2 — The diagram is representation, not generation (model → mermaid)

A diagram must show the **real structure the system model already holds**, not a shape synthesised in
the distribution layer. `mermaid.py` is demoted to a pure renderer: it takes `(nodes, edges, note)`
and draws; it never invents a node. The **graph is extracted from `system_model.json` /
`ecosystem_model.json`** for the chosen spine:

- **loop** → the loop's constructs **plus their member signals** and the loop edges (the rich graph,
  not the 3-segment triangle);
- **construct** → the construct and the series that measure it;
- **risk / opportunity** → the sourced **force → mechanism node → affected signals** subgraph (e.g.
  #8: `force_upi_zero_mdr → acceptance infrastructure → POS/UPI divergence`);
- **constraint** → the two operand sources → ratio → corridor.

The diagram earns its place when that extracted subgraph is non-trivial (more than a bare edge). **If
the model cannot produce a diagram worth showing, that is a model gap to revisit** — not a cue to
draw a decorative triangle. This resurrects the *intent* of the deleted `generate_mermaid` (draw the
model) as a focused, per-spine representation, without its 821-line weight.

#### R3 — Bank "why": tiered S4a sourcing, cost paid once and cached

The bank angle carries a real, sourced *why* for the featured banks — and a why is a claim about the
world, so it is sourced and verified, never inferred. The engine and its trust contract:

- **Tiered source registry (extends S4).** S4 today validates forces against **Tier 1** only. It is
  widened to a per-tier **allowlist** — a source not on the list is *rejected*, so "reputed" is
  auditable, not a judgment call:
  - **Tier 1 — Official/regulatory**: RBI, PIB/Cabinet, Union Budget, SEBI, NPCI, bank regulatory
    filings/disclosures.
  - **Tier 2 — Reputed structured reports**: credit bureaus (CIBIL/TransUnion, CRIF, Equifax), rating
    agencies (CRISIL, ICRA, CARE), RBI bulletins, industry bodies (PCI, IBA), payments processors'
    published reports (e.g. Worldline India Digital Payments Report).
  - **Tier 3 — Named financial press**: a fixed allowlist (see §11.2-R allowlist below), never "any
    article".
- **Every entry**: `bank`, `dimension`, `why`, `url`, **verbatim `excerpt`**, `date`, `tier`,
  `status`. Publishing requires `status: verified` **and** a WebFetch check that the excerpt
  **literally appears on the page** — the deterministic, free step that kills the hallucinated-URL
  risk. Nothing is auto-trusted (`bank_sourcing.validate_entry`, already built, extends to carry the
  tier + the fetch check).
- **Cost is paid once, at the S4a step, then cached.** The LLM proposes the why + candidate sources
  (web-search enabled) and WebFetch verifies them; the verified result is written to the gated store.
  **Deep read generation reads the store deterministically — zero API cost per render**, however many
  times the issue is regenerated or the spine re-picked. Re-sourcing runs on a cadence (monthly, or
  when a new bank diverges), bounded to the featured banks (~top 3 public + 3 private per dimension).
  Estimated cost per sourcing run: ~₹0 via the `claude -p` CLI path the evals use, up to ~$2 on the
  Opus API — amortised to ≈0 per read.
- **Tier discipline in the render.** A Tier-1/2 source publishes as the primary *why*; a Tier-3 press
  source is labelled as such and is preferred as the **corroborating** second reference ("others are
  seeing it too"). No verified source in any tier → the honest fallback: the computed divergence is
  the read, and the post says so. **A why is never paraphrased from the model or invented to fill the
  slot.**
- **Negative-tested**: a fabricated URL (excerpt not on the page) is rejected; a source off the
  allowlist is rejected; a `status: verified` entry missing its excerpt fails the store gate.

**Built + measured (2026-07-29).** The engine is live in `bank_sourcing.py`: tiered allowlist +
`tier_of` + `validate_entry` (host-on-allowlist + declared-tier match + excerpt-verified + status) +
`excerpt_on_page` (the pure verification) + `add_bank_claim` (verify → gate → write) + an `add` CLI.
Six unit tests cover tier resolution, excerpt verification, the gated writer, and a tier-lie.

**Operational finding — the verification channel matters as much as the allowlist.** On the first
live run for #8, the automated fetch (Claude Code WebFetch, i.e. Anthropic's crawler) was **403'd by
essentially every relevant Indian source** — PIB, NPCI, Business Standard — and `web.archive.org` is
unreachable to it; a permissive control (Wikipedia) fetched fine, so the tool works and the *sites*
block the crawler. The gate behaved correctly: **it published nothing**, because nothing could be
verified. The Anthropic API's own `web_search` uses the same crawler identity, so a "direct API" path
does not get past this; spoofing a browser user-agent to evade a site's bot block is out of scope. The
resolution (decided with the user): the excerpt is verified against page text obtained through a
channel the sites permit — **the editor's own logged-in browser** (Claude-in-Chrome → `get_page_text`)
or a paste — fed to the same `excerpt_on_page` anchor. `add_bank_claim(entry, page_text)` is agnostic
to how the text was obtained, so this is a channel choice, not an engine change. Until a source is
verified through such a channel, the Bank angle renders its honest fallback.

**Live population succeeded via the editor's Chrome (2026-07-29).** With the user's browser connected,
#8 earned **two verified corroborations**, each excerpt confirmed literally on the page via
`get_page_text` → `excerpt_on_page`: a **Tier-1 official** PIB release ("Advancing Cashless India")
grounding the zero-MDR driver, and a **Tier-3 press** Business Standard piece ("…may hurt PoS machines
deployment") triangulating the POS side. The deep read renders the official one as "On the official
record" and the press one as "Others are seeing it too", each tier-labelled with its link. Per-bank
POS-divergence *whys* were searched and none met the bar (no citable third-party source per bank), so
the Bank angle stays its honest fallback — the mechanism publishing what verifies and refusing what
does not. Two presentation-only leaks surfaced and were fixed at the strip (URLs and FY/budget-year
ranges are locators/dates, not figures).

#### Build sequence (agreed 2026-07-29)

Part 1 (no API): R1 prose layer + R2 model-sourced diagram, on the chosen spine (**#8 — POS acceptance
contracting while UPI grows**). Part 2: R3 — extend S4 to the tiered registry, run S4a sourcing on
#8's featured banks with LLM + WebFetch, cache to the store; the deep read then renders the cache for
free. Each part self-gated and measured before the next.

#### §11.2-R Tier-3 press allowlist

The **only** general-press mastheads admissible as a Tier-3 source, by URL host. Anything not on this
list is rejected by the S4 gate regardless of how the LLM proposes it:

| Masthead | Host(s) |
|---|---|
| The Economic Times | economictimes.indiatimes.com |
| Business Standard | business-standard.com |
| Mint | livemint.com |
| The Hindu BusinessLine | thehindubusinessline.com |
| Financial Express | financialexpress.com |
| Moneycontrol | moneycontrol.com |
| Reuters | reuters.com |
| Bloomberg | bloomberg.com |

Adding a masthead is a deliberate edit to this table (and the gate's allowlist), never an inline
call. Tier-3 is always labelled press in the render and never outranks a Tier-1/2 source for the same
claim.

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

- **Flip-table noise — RESOLVED in the §11.1 revision (2026-07-23).** The full "every status flip"
  list was mostly accelerate↔decelerate wobble (May 2026: 14 flips, only 1 a regime change). Replaced
  by the grouped **sector growth table** (all sectors, YoY, regime-turned flagged). The is-news
  selector's regime/wobble distinction is now the shared rule.
- **Payments "card spend" — RESOLVED (dropped) in the §11.1 revision.** There is no per-bank or total
  card-spend signal (spend is split POS/ecom/atm/other). Tiles use cards-in-force / debit-cards /
  POS-terminals; the bank table uses the three per-bank *count* scans. A total-spend signal remains a
  possible future compute add, but the templates no longer claim a tile with no signal.
- **Per-sector volume (₹ L Cr) column — deferred.** The sector growth table ships YoY-only; a volume
  column needs per-sector `-abs` signals (only four sectors carry one). Small compute add when wanted.
- Eval prompt v1.12 tone rule — blocks clean blurb voice (§10). The monthly issue's `prose_lint`
  now surfaces the exact fix list: 6 advice/forecast hits in verbatim reads-card prose this cycle.
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
