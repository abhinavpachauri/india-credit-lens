# `signals/` — signal store, compute engine, evaluation

The Layer-1 signal subsystem: a registry of signal specs, the SQLite fact store, the
deterministic compute engine, and the LLM evaluation layer.

## Store + catalog
- **`registry.json`** — universal signal catalog (L1/L2/L3 tagged; L1 signals carry compute
  specs). The single declaration of what each signal is.
- **`signals.db`** — **primary store** (SQLite): `(pipeline, period, metric_id, entity_type,
  entity_id)` fact table + `metric_ranges`. Binary — guarded by `guards/check_signal_freshness`.
- **`db.py`** — schema init + `refresh_ranges()`.

## Compute (`compute/`)
- **`engine.py`** — `run_append(pipeline, period, db, registry)` dispatches each signal to its
  method. **`sibc.py`** / **`atm_pos.py`** implement the 1a/1b/1c/1d methods (read the
  consolidated CSV; hot filter columns are `category`-dtype for speed). Both cache the CSV
  per process via `_load_df()`.

## The method catalogue — what Layer 1 measures

> Added 2026-09-12, when a new reconcile check asked for the first time whether every
> dispatchable compute method appears in this file. **Eighteen did not** — every one of them from
> the original 1a–1d foundation. The spec had grown by documenting each new family in detail
> while the methods the whole platform rests on were never written down at all. The check is a
> name check and cannot judge a section's quality; it can only stop a method entering the engine
> unmentioned, which is the population the spec-first rule was always about.

Layer 1 asks five kinds of question. Every method below belongs to exactly one of them, and the
sub-layer tag on a registry entry says which.

### 1a — one number about a whole thing
*How big is it, how fast is it moving?* One row, `aggregate`/`total`.

| method | measures |
|---|---|
| `csv_total_abs` · `csv_sector_abs` | the level of one named thing |
| `csv_total_yoy` · `csv_sector_yoy` · `csv_sum_yoy` | growth against the same month a year earlier (`csv_sum_yoy` over a bundle of metrics) |
| `csv_total_ratio` · `csv_ratio_sum` | one metric over another, or over a bundle |
| `csv_sector_count_positive_yoy` | how many named sectors are growing — a breadth reading |

### 1b — one number about one named part
*How fast is Agriculture? What share is Large?* Scalar, but scoped to a child rather than the whole.

| method | measures |
|---|---|
| `csv_sector_share` · `csv_category_share` | a part's share of its parent |
| `csv_category_yoy` | one bank category's growth on one metric |
| `csv_sector_yoy_spread` | the gap in pp between two named parts — the entity axis of divergence |

### 1c — the same number for EVERY part at once (a scan)
*Rank all nineteen industry types.* One row per part; the rows **are** the distribution.

| method | measures |
|---|---|
| `csv_sector_scan_abs` · `csv_category_scan_abs` | the **size** of every part (see the next section) |
| `csv_sector_scan_share` · `csv_category_scan_share` | every part's **share**, of its parent or of a declared denominator |
| `csv_sector_scan_yoy` · `csv_category_scan_yoy` | every part's **growth** |
| `csv_psl_scan_yoy` | growth across the PSL memo block, which no `parent_code` can reach |
| `csv_bank_scan` | the same, at individual-bank granularity — payments only; SIBC publishes no per-bank credit |

### 1d — a number compared with its OWN past
*How many readings in a row? How does this year compare with last?*

| method | measures |
|---|---|
| `csv_yoy_streak` | consecutive periods a **YoY** condition has held (SIBC) |
| `csv_mom_streak` | consecutive periods a **month-on-month** level move has held (payments) |
| `csv_sector_fy_acceleration` | the change in growth between the two most recent 31-March readings |
| `csv_sector_fy_delta` | the rupees added between those same two FY-ends |

The two streak methods were once **one registry name meaning two things** — a YoY condition and a
MoM level move, with different parameters, vocabulary and zero-handling. They are named for the
comparison basis precisely so they cannot be confused again.

### 1e — two things compared (the relational layer)
*Is the mix shifting? Is a child out of step with its parent? Are two metrics diverging?* Specified
in full in the two sections below: `csv_sector_rotation` · `csv_category_rotation` ·
`csv_sector_divergence` · `csv_bank_divergence` · `csv_pair_divergence` · `csv_sector_momentum` ·
`csv_category_momentum` · `csv_sector_acceleration` · `csv_category_acceleration` ·
`csv_sector_allocation` · `csv_category_allocation`.

### Rules that hold across all five
- **A method is dispatched only from `METHODS`.** A registry entry naming a method that is not
  there raises rather than silently producing zero rows — twelve payments signals were once
  unwired that way and the freshness check stayed green.
- **Status is evaluated by declared `status_rules`, never in the method body**, so what counts as
  "strengthening" is a property of the signal rather than of the code.
- **Every method reads the consolidated CSV and nothing else.** No method may read another
  signal's stored rows; a value that depends on another signal belongs to the layer above.

## Cut coverage — size & share (the table families)

> **Written 2026-09-12, AFTER the compute landed.** The rule in this project is spec first;
> this section did not exist when `csv_sector_scan_abs` was built. It is therefore a record of
> decisions already taken, not a design that disciplined them. Noted because a spec that quietly
> back-fills its own code reads identically to one that led it, and the difference matters.

A **cut** is a parent plus the parts it decomposes into — the unit the dashboard renders as a
dimension, and the unit `MOVEMENT_CUTS` already declares. The question these families answer is
not "is this signal correct" but **"is this cut completely described"**, which nothing had asked.
It had not been asked for a reason worth recording: the registry held 229 computed signals and
**not one of them was the size of a sector**. Every signal was a rate or a share, so the platform
could say industry grew 20.0% and could not say, from any stored value, that industry is
₹48 lakh crore — the number a reader starts from.

### what counts as a cut — the coverage contract

> Written **before** the entries this section requires (2026-09-12), which is the order the rule
> asks for and the order the previous pass did not follow.

A cut is **any parent whose parts the dashboard draws** — not only the seven credit dimensions and
three payments groups that `MOVEMENT_CUTS` happens to name. That distinction was doing damage
invisibly: `MOVEMENT_CUTS` is a table in the *card generator*, and coverage had been audited
against it, so anything the dashboard rendered by another route was never checked at all.

Audited 2026-09-12, two populations were half-covered:

- **Seven SIBC sub-cuts** — trade, NBFC sub-types, basic metals, engineering, food processing,
  textiles, chemicals. `buildSubCuts` draws every one (DASHBOARD_SPEC §15.6) and each carried
  share and growth only: no size, no momentum, no pace, no allocation.
- **Twenty-three payments metrics.** Only credit cards, debit cards and POS terminals had any
  per-category signal, while the consolidated CSV carries per-bank rows for **all 26 metrics
  across all 5 bank categories** — a registry gap, never a data gap.

**The contract:** every cut carries all six families — size, share, growth, pace, momentum,
allocation — so a table of its parts has no empty column for a reason nobody decided. Where a
family is genuinely undefined for a cut, the reason is *declared and named* (PSL's share, see
below), never left as an absence.

**Registry coverage is not publication.** These families compute for every cut; which cuts earn a
*card* is a separate, editorial decision that stays in each generator's `MOVEMENT_CUTS`. Widening
compute must not widen the dashboard by side effect — the 2026-08-19 decision to watch the
movement card rank before widening it still stands.

**Layer 2 grows as a consequence, and that is expected.** `mix_states` selects on the momentum
method, so a cut that gains momentum gains a mix state. That is the causal layer seeing more of
the same system, not a new claim — but it is a downstream effect of an L1 change, so it is stated
here rather than discovered later.

### size — how big each part is
`csv_sector_scan_abs` (SIBC) · `csv_category_scan_abs` (ATM/POS). METHOD_TYPE: `scan`.

- **Rows:** one per part, value = the level in the source's own unit (`rs_cr` / `count`),
  sorted descending. Plus one `aggregate`/`total` row.
- **That total is summed from the parts, NOT read off the parent's published row**, and this is
  the load-bearing choice: it is the same denominator `weight` uses, so "this part is X of the
  cut" stays answerable when a parent does not equal the sum of its children. For SIBC main
  sectors it does not — the four sectors total ₹208.9L Cr against non-food credit's ₹219.6L Cr,
  a **4.9% residual** RBI attributes to no sector.
- **Status compares with the same month a year earlier, not the prior period.** A level larger
  than last month is not news in a series that grows every month.
- **Why a size must be a signal rather than arithmetic in a browser:** a derived number is one no
  gate can ground (the same rule that kept the tilt and the coherence figure out of published
  prose). A size is also what stops a 31.7% on a ₹16,014 crore book reading like a 31.7% on a
  ₹32 lakh crore one — the pairing rule, applied at the level the reader begins from.

### share — of the parent, and of the whole book
Both use `csv_sector_scan_share`; they differ only in the declared `denominator_code`.

- **Share of parent** — denominator is the parent's own published row. Answers *"how much of
  industry is this"*.
- **Share of all bank credit** (`denominator_code: I`) — answers *"one rupee in every seven"*.
  A genuinely different fact for any cut below the top, and hand-arithmetic until now.
- **Both denominators are always NAMED in the rendering** (DASHBOARD_SPEC §15). Two share columns
  side by side with unnamed denominators is the defect §15 was written about.
- ATM/POS needs only one: a payments cut's parent **is** its root.

### the PSL exception — named, never papered over
`sibc-psl-share-scan` was declared, computed **zero rows**, and was **removed rather than given a
denominator**. PSL is a memo lens: `gap_psl_totals_methodology` already records that its
sub-category totals are non-additive, so there is no published total for its parts to be a share
*of*. Summing them to manufacture one would have produced a plausible number with nothing behind
it. PSL keeps `share-of-credit`, whose denominator is real. Check 2e caught the empty signal on
the first run — an empty registry entry is the exact shape of a failure that looks like an absence.

### `weight_now` — the mix comparison must use one denominator
`csv_sector_allocation` / `csv_category_allocation` already stored `weight`, each part's share of
the cut **at the start of the window**, so Layer 2 could read `tilt = alloc - weight`. They now
also store **`weight_now`**, the same parts over the same denominator **today**.

Not a convenience. The share scan divides by the parent's published row; `weight` divides by the
sum of the parts. For main sectors those differ by 4.9%. Reading "share of the book a year ago"
from the allocation family and "share today" from the share family would have compared **two
different questions**, silently and plausibly, in adjacent columns.

### one selector per cut
`_child_frame(params, period, df)` is the single definition of *"the parts of this cut"*, shared
by `_children_at`, the share scan and the size scan. The share scan previously carried its own
copy of that query and therefore **could not see the PSL memo block at all**, while momentum and
allocation could. Two descriptions of one concept is the drift the engineering principle forbids;
a cut should be one declaration and every family should agree on what its parts are.

### one cut, one stem — signal id naming

**Every family of a cut shares one id stem**, so the six signals describing a cut can be found
by name rather than by lookup table:

    sibc-services-size-scan · -share-scan · -yoy-scan · -acceleration · -momentum · -allocation

This was NOT true until 2026-09-12, and the reason is worth keeping. The scan families were named
in the original spec (`sibc-services-yoy-scan`, `sibc-industry-type-share-scan`). Four months
later the movement family arrived, needed a short label for its own `MOVEMENT_CUTS` table, and
coined `svcs` and `ind-type` — so one cut had two names.

**Nothing broke, and that is the interesting part.** `MovementCut` takes its speed signal as a
DECLARED field, so the one place that had to bridge the two spellings simply wrote the other one
down:

    MovementCut("svcs", "services", "sibc-services-yoy-scan", ...)
                  ^slug                ^ the other spelling, hand-carried

Declaring rather than inferring is right in general, but here it absorbed the inconsistency
instead of surfacing it. The mismatch only appeared when `test_l1_coverage` became the first code
to build ids from a stem and expect all six families — and it reported a **false gap**, naming two
fully-covered cuts as missing share and growth. A check that cannot tell a naming quirk from a
real hole is a check people stop believing.

**The rule, enforced in `tests/test_l1_coverage.py`:** a cut's stem is the one its families already
use; a new family joins the existing stem rather than coining a shorter one. Prefer the stem that
matches the dashboard's own section id (`services`, not `svcs`) — a reader debugging a column
should not have to translate.

### Conventions
- **Coverage is the contract, and it is tested.** `tests/test_l1_coverage.py` enumerates every cut
  from its own momentum signal and asserts each carries a size, a groundable share, and rows that
  actually exist. Negative-tested by deleting a cut's size signal.
- A new family for an existing cut **inherits that cut's declaration** (`parent_code`, `statement`,
  `child_level`, `psl_memo`, `exclude_codes`) rather than restating it.
- Backfill every period on introduction; Check 2f recomputes all and will fail on any drift.

### Assessed and deliberately NOT added
- **Rotation on the cuts that lack it.** Share-today and share-a-year-ago are both stored, so a
  rendering shows **two operands instead of a subtraction no gate can ground** — the same call made
  for the tilt in DASHBOARD_SPEC §16.3.
- **Per-entity month-on-month.** Credit is a stock; the 12-calendar-month window is mandatory for
  this family (see allocation above, where 5 of 20 monthly steps were arithmetically impossible).
- **Per-entity streak counts.** The run of actual readings is strictly more informative than a
  count of them, and it is already recoverable from the stored series.

### Known, pre-existing, NOT fixed here
`weight`/`weight_now` for the PSL cut divide by the sum of parts that
`gap_psl_totals_methodology` declares non-additive. It predates this work, and changing it would
rewrite PSL's Layer 2 mix state — a causal reading should not move as a side effect of a
coverage pass. Flagged for a decision.

## Relational signal methods — rotation & divergence

Cross-segment L1 methods. Same architectural status as `csv_yoy_streak`/`csv_mom_streak`/`csv_sector_scan_*`: registry
spec → deterministic compute → per-entity rows in `signals.db` → deterministic insight builders.
They serve the fixed monthly outputs in `archive/docs/FABLE_BRIEF_cross_segment_insights.md` (posts 2/3/4).
**Deterministic prose is the product** — the insight builders must emit publishable copy with zero
LLM calls (quality bar: `deterministic_scan_insight`).

### rotation — who is gaining/losing ground
`csv_sector_rotation` (SIBC) · `csv_category_rotation` (ATM/POS). METHOD_TYPE: `rotation`.

- **Compute:** for each child of `parent_code` (SIBC) / each `bank_category` on a metric (ATM/POS):
  `Δshare_pp = share(period) − share(period − window)`. `window: 12` **calendar months** default
  (annual — avoids seasonality). The window resolves calendar-wise (same month-end, `window` months
  earlier, which must exist in the CSV), **not** by positional index — the SIBC CSV has coverage
  gaps, and a positional 12-back would silently land 24 months out. Absent comparison month → no
  rows. Share basis reuses the existing share-scan computation at two periods — no parallel math.
- **Rows:** one per entity — `value = Δshare_pp` (unit `pp`), signed, sorted desc; `status` via
  `status_rules` (default: `> +0.15` strengthening / `< −0.15` weakening / else stable). Plus ONE
  `entity_type='aggregate', entity_id='total'` row — **rotation mass** = Σ|Δshare|/2 (pp of the mix
  that moved; precedent: fy-acceleration's mixed aggregate+component rows).
- **Insight** (`core/relational_insights.py :: rotation_insight` — live): top gainers/losers by name
  + Δpp; the real-world line comes from the **majority `economic_role` of the top-3 gainers/losers**
  (roles resolved from the system model's `concept_tags`, majority taken over the *material* movers —
  `|Δ| ≥ 0.15pp`, the status-rule threshold — so a +0.04pp bystander cannot outvote a +3.4pp shift;
  untagged entities abstain). Mixed roles → honest fallback ("no single theme"); a wholly untagged
  entity set (bank categories — a lender mix, not an economic one) gets **no** theme sentence.
  Steady mix (mass < 0.5pp) is reported as the finding. Composition reads only — no lead/lag claims
  (COMPOSITION_SPEC §4). `divergence_insight` (same module) renders the hierarchy-divergence cards,
  citing ONLY the signal's own gap values. **Wired on both dashboards**: SIBC Stage 5.5 routes
  rotation/divergence through these builders (like scan); payments Stage 4b emits them as
  `representation: deterministic-db` cards validated strictly vs their own db rows (4c) with
  `reasoning.signals` resolved against signals.db (4d).

### divergence, hierarchy axis — child contradicting its parent
`csv_sector_divergence` (SIBC: children vs parent YoY) · `csv_bank_divergence` (ATM/POS: bank vs its
`bank_category` YoY on a metric). METHOD_TYPE: `divergence`. **One operator, both trees** — a bank
diverging from its category is structurally identical to a sub-sector diverging from its sector.

- **Flag rule (params, deterministic):** opposite YoY signs AND `|child_yoy| ≥ min_abs` (default
  2.0) AND `|child_yoy − parent_yoy| ≥ min_gap` (default 5.0).
- **Rows:** **flagged entities only** (anomaly-surfaced by construction — bounded output; 67 banks
  never produce 67 rows). `value = child_yoy − parent_yoy` (pp, signed; sign carries direction — no
  new status vocabulary). No flags → no rows → insight suppressed.

### divergence, metric axis — declared co-movement pairs
`csv_pair_divergence` (ATM/POS). METHOD_TYPE: `pair` at total level, `divergence` at bank level —
one method, two shapes, so the ground truth for each is the right shape (below).

**Not applicable to SIBC, by the shape of the source.** The metric axis needs two co-moving
*measures*; the SIBC CSV carries exactly one (`outstanding_cr`) — sector, statement and level are
dimensions of it. Comparing two SIBC sectors is rotation (share) or hierarchy divergence (child vs
parent), both already live, so a SIBC "pair" would be an existing operator under a second name.
This is a property of the source, not a backlog item: it changes only if a future ingestion carries
a second measure per entity. If one does, generalise then — the pair math (two bundles → two YoYs →
gap) is already pipeline-agnostic; only the metric-bundle resolver reads pipeline-specific columns.

- **The authored pair list IS the registry**: one signal per pair (e.g. `cc-issuance-vs-spend-gap`
  = cards YoY vs spend YoY). Only registered pairs are ever compared — "declared pairs only" falls
  out of the registry-is-the-spec rule; no separate relation file. **Live pairs (5):**
  `cc-issuance-vs-spend-gap` · `dc-issuance-vs-spend-gap` · `pos-fleet-vs-spend-gap` ·
  `atm-fleet-vs-withdrawal-gap` (total) + `cc-issuance-vs-spend-bank-gap` (bank).
- **Params:** `a`/`b` metric bundles (`{metrics: [...], label}` — a side may sum several CSV
  metrics, e.g. card spend = POS + e-com), `level: total|bank`, flag thresholds (`a_min`, `b_max`,
  `min_gap`), and **`min_base`** — both metrics must have a nonzero base for the entity.
  `min_base` is the structural-vs-surprising rule: issuer-only banks (cards > 0, POS = 0 —
  AU/HSBC/Utkarsh pattern) are *structure*, excluded by construction, never flagged as anomalies.
- **Rows:** `level: total` → one aggregate row (`value = yoy_a − yoy_b` pp) **plus two
  `entity_type='pair_side'` component rows** carrying each side's own YoY. The gap alone cannot
  tell "both grew, A faster" from "both shrank, B faster" from "A grew while B fell" — three
  different stories with identical arithmetic — so direction is read from data, never inferred
  from the sign. `level: bank` → flagged banks only.
- **Ground truth:** total-level pairs are **scalar-shaped** (value + series + the two side rows as
  `components`), *not* scan-shaped: a "distribution" of one pp gap and two pct rates would let
  cumulative-sum derivations admit numbers that mean nothing. Negative-tested — an invented gap in
  body or chain fails Stage 4c.
- **Insight** (`core/relational_insights.py :: pair_divergence_insight` — live): a pair earns a
  card only when the sides have come apart; a `stable` gap (inside ±3 pp) is the null result and is
  suppressed. Only the gap is stated as a figure; the side rates set the wording. Verbs are
  past-tense (grew/fell/shrank) so one template stays grammatical across authored labels of mixed
  number. Payments Stage 4b renders them as `deterministic-db` cards (`insight_kind:
  divergence_pair`), sourcing the bank-level rows too where a pair has them.

### Conventions shared by all three
- **Coverage additions are registry entries, not architecture** (e.g. per-bank spend rows for the
  bank-level pair signal = new bank-scan entries).
- **Backfill**: append every period on introduction (Check 2f recomputes all periods); the first
  `window` periods legitimately emit no rotation rows.
- **Traceability**: rows land in `signals.db` → Check 2g / Stage 4c period-wide ground truth covers
  them; `query.signal_numbers` treats `rotation`/`divergence` like `scan` (full row distribution).
- **Insight schema**: emitted insights carry `insight_kind: rotation | divergence_hierarchy |
  divergence_pair` (additive field; no restructure).
- **Consumption**: anomaly-surfaced insights on the dashboards; everything else on-demand via the
  reply-desk `lookup` pattern. Never pre-generate per-bank cards.

## Movement signal methods — momentum, acceleration & allocation

The Layer-1 vocabulary for *how a distribution is changing*, distinct from what it is. Same
architectural status as the relational methods: registry spec → deterministic compute →
per-entity rows in `signals.db` → deterministic insight builders.

**Why these exist.** We compute a thing's **size** (`csv_*_abs`) and its **speed** (`csv_*_yoy`),
and `rotation` computes the displacement of its *share*. Nothing computes how many units actually
moved, nor whether the speed itself is changing. That is why a material reallocation can run for
a year and read as a flat share chart. Measured 2026-08-18 on SIBC main sectors: a **14.8 pp**
swing in where new credit went registered as **1.63 pp** of rotation, and in the turning month
rotation read **0.09 pp** — under the 0.15 pp materiality band, i.e. filed as noise by our own rule.

**These are re-expressions, not new information.** `alloc = rotation ÷ f + weight`, where
`f = net movement ÷ total`; reconstruction error 4.4e-16. They earn their place because `f` ranges
**6.45–12.81** across the observed window, so rotation states real decisions in a unit where they
look like rounding error. Build for legibility and threshold calibration — never claim new facts.

### momentum — how many units actually moved
`csv_sector_momentum` (SIBC) · `csv_category_momentum` (ATM/POS). METHOD_TYPE: `momentum`.

- **Compute:** per child of `parent_code` / per `bank_category` on a metric:
  `delta = value(period) - value(period - window)`. `window: 12` **calendar months**, resolved by
  the same calendar rule as rotation — never positional (the SIBC CSV has coverage gaps, and a
  positional 12-back silently lands 24 months out).
- **Rows:** one per entity, `value = delta` in the **metric's own unit**, signed. Plus THREE
  `entity_type='aggregate'` rows: `net_movement` (sum of deltas), `gross_movement` (sum of
  |deltas|), and `coherence` (`|net| / gross`, unit `ratio`, range [0,1]).
- **Unconditional.** No division by a derived quantity, so momentum cannot blow up in a
  contracting or churning system. It is the safe backbone every other movement number rests on.
- **Why momentum and not just speed.** Speed discards scale. Measured 2026-06: agriculture grew
  **16.8%** and personal loans **15.8%** — agriculture looks faster — but agriculture added
  **Rs 3.9 L Cr** against personal's **Rs 9.7 L Cr**. Both readings are true; only both together
  are honest.
- **Why net AND gross.** They are equal only when every entity moves the same way. Measured on
  ATM/POS `pos_terminals`, 12m to 2026-05: private banks **-257,290**, public banks **+204,595** —
  net **-55,885**, gross **465,615**. "A great deal happened; nothing net happened" is a finding,
  not an error, and one total alone cannot say it.

### coherence — the ROUTER (never a gate)
Emitted by `momentum`, consumed by `allocation`. Not its own registry signal.

- `coherence = |sum of deltas| / sum of |deltas|`, in [0,1]. **1.0 = every entity moving the same
  direction.**
- **Load-bearing property (provable, verified both pipelines):**
  `max |share of net movement| <= 1 / coherence`. Coherence bounds the distortion *before* any
  share is computed. Observed 2026-08-18 — SIBC main 1.000 → worst share 45% · SIBC industry types
  0.825 (bound 121%) → 23% · payments credit cards 0.935 (bound 107%) → 75% · **payments POS
  terminals 0.120 (bound 833%) → 460%.** The bound held in every one of 132 windows.
- **Coherence ROUTES to a different story. It never suppresses one.** This is the load-bearing
  design decision, and it reverses an earlier draft that specced coherence as a publish gate. A
  gate would have silenced exactly the most valuable windows: the two lowest-coherence windows in
  the whole dataset are a **POS-deployment handover from private to public sector banks** and a
  **debit-card e-commerce consolidation into private banks** — both invisible in the net number,
  both stronger stories than any high-coherence window produced.

| coherence | regime | the sentence that is true |
|---|---|---|
| `>= 0.90` | aligned | *"Of every Rs 100 of new credit, services took Rs 33.80."* — allocation reading |
| `0.50 - 0.90` | contested | *"Card spend grew Rs X — but foreign banks moved against it."* — net direction holds, name the dissenters |
| `< 0.50` | handover | *"POS terminals barely moved on net — private shed 257,290 while public added 204,595."* — the transfer IS the story |

- **Observed distribution (132 windows, both pipelines, 2026-08-18):** `= 1.000` 35.6% ·
  `0.95-0.999` 43.2% · `0.80-0.95` 12.9% · `0.50-0.80` 6.1% · `< 0.50` 2.3%.
- **`coherence_min` default `0.90` is a SENTENCE-SELECTOR, not a publish switch.** Its only
  justification is the bound (no share beyond +/-111%). Per the standing AI PM rule it still ships
  with a measured catch / false-rejection rate — but nothing is silenced while that is pending.
- **A share above 100% is ORDINARY, and the guard that said otherwise was wrong (2026-09-12).**
  `alloc` divides by the NET, so when one part shrinks another can account for more than the whole
  net increase. Check 2e B6 spent three days asserting "a share cannot exceed the whole" — false
  for a net denominator, and contradicted by the two lines above it. It stayed quiet only because
  none of the 134 windows then in the store landed between 100% and 111%; at 520 windows, 30 did,
  and it fired on **100.003%**, where one category took all of the growth and two others shrank by
  a rounding whisker. **No threshold repairs it** — measured over 648 windows, `coherence_min` at
  1.00 still leaks 5 while withholding 62% of them. B6 now asserts the bound itself
  (`|share| <= 100 / coherence`), which is the provable property AND the one that justifies the
  threshold. Negative-tested three ways: an invented 137% at low coherence still fails; 105% where
  the bound allows it now passes; an `alloc` row with no coherence row to bound it fails rather
  than passing silently.
- **"Reads as impossible" is a PROSE problem, not a storage one.** The real concern inside the old
  B6 — that *"of every Rs 100, telecoms took Rs 137"* reads as a bug to a reader — is legitimate
  and belongs in the card layer beside the pairing rule and the router table, where sentences are
  decided. A guard over stored values is the wrong place to enforce it, and enforcing it there
  suppressed true numbers.
- **Report net and gross always; never "flag" their divergence.** A footnote that fires
  occasionally gets ignored; two totals side by side are self-explanatory.

### acceleration — is the speed itself changing
`csv_sector_acceleration` (SIBC) · `csv_category_acceleration` (ATM/POS).
METHOD_TYPE: `acceleration`.

- **Compute:** `delta_speed = yoy(period) - yoy(prior period)`, per entity. Unit `pp`.
- **Distinct from `csv_sector_fy_acceleration`**, which is annual and FY-end-only (5 signals).
  This is per-period and general.
- **It is the only member of the family that separates *slowing down* from *being overtaken*, and
  it is not optional for that reason.** Measured 2026-08-18: personal loans' share of new SIBC
  credit fell 44.7% → 30.1%, which reads as retreat. Acceleration shows personal at **+4.1 pp**
  against industry **+12.9** and services **+12.6** — nothing decelerated; personal accelerated
  least. The allocation number alone asserts the opposite of the truth.

### allocation — where the new units went
`csv_sector_allocation` (SIBC) · `csv_category_allocation` (ATM/POS). METHOD_TYPE: `allocation`.

- **Rows, two kinds, distinguished by `entity_type`:**
  - `contribution` — `100 * delta_i / gross`. **Always emitted, every regime.** Answers "of all
    the movement, how much was this one." Bounded by construction (cannot exceed 100%); valid in
    growth, contraction and churn alike.
  - `alloc` — `100 * delta_i / net`. **Emitted when `coherence >= coherence_min`.** Answers "of
    the net new units, how many went here." Sums to 100 across entities.
- **Below `coherence_min` there is no honest null and no silence** — `contribution` rows stand and
  the insight switches to the contested/handover sentence per the router table above.
- **The 12-calendar-month window is mandatory, not a preference.** Month-on-month is not merely
  noisier, it is undefined: measured on SIBC main sectors, **5 of 20** monthly steps produced
  impossible shares (137.4%, -366%), two of them because the book **contracted** in April — in
  both 2025 and 2026, a March year-end effect that unwinds. The annual window cancels it; **14/14**
  annual windows clean.
- **Depth is not the constraint; the source is.** An earlier draft claimed deep SIBC cuts break —
  that was an artefact of a strict [0,100] validity test which rejects a harmless -0.3% share.
  Measured coherence: SIBC main sectors **1.000** (14/14), industry-by-type min **0.825**,
  services+PL sub-categories min **0.995**. **SIBC is coherent at every depth.** Low coherence is
  payments-specific and episodic (bank-category cuts where one issuer reclassifies).

### Insight rules — the pairing rule is non-negotiable
`core/relational_insights.py :: movement_insight`.

- **An `alloc` figure is NEVER rendered without that entity's speed and acceleration beside it.**
  Alone, "personal loans fell from 44.7% to 30.1% of new credit" reads as contraction; the same
  entity grew **15.8% YoY, accelerating**, taking **Rs 6.4 L Cr → Rs 9.7 L Cr**. A falling share of
  a faster-growing flow is the most misreadable number in this family — it misled the author of
  this section for an hour before acceleration caught it. **Enforce in the builder, not in review.**
- **Momentum is quoted in the metric's own unit**, never as a bare percentage — restoring the scale
  that speed discards is the entire point of momentum.
- The router table decides the sentence. A builder must never emit an allocation sentence in a
  contested or handover regime, nor a handover sentence in an aligned one.
- Composition reads only — no lead/lag or causal claims (COMPOSITION_SPEC §4).

### Conventions
- Applicability: **momentum, acceleration and `contribution` are unconditional** — every cut, both
  pipelines, any future source. Only the *`alloc` sentence* is coherence-routed.
- Backfill: append every period on introduction (Check 2f recomputes all); the first `window`
  periods legitimately emit no momentum rows.
- Traceability: rows land in `signals.db` → Check 2g / Stage 4c period-wide ground truth covers
  them. `query.signal_numbers` treats `momentum`/`allocation` like `scan` (full row distribution);
  `acceleration` is scalar-shaped per entity.
- Insight schema: `insight_kind: movement_momentum | movement_allocation` (additive field).
- **Coverage gap this closes:** `csv_sector_rotation` is registered for industry, services and
  personal-loan sub-cuts only. The four main SIBC sectors — the one cut with coherence 1.000 in all
  14 observed windows — have **no rotation signal at all**, and are the blindest spot in the
  registry.
- **Coherence does not stop at Layer 1.** The same "do the parts agree?" question is unanswered in
  SYSTEM_MODEL_SPEC §16 Step 2 (mechanical propagation) and COMPOSITION_SPEC §14 (construct
  direction). Compute it once here; both consume it. See those sections.

## Evaluate + query
- **`evaluate.py`** — Stage 5 LLM evaluation: builds domain payloads from `signals.db`, calls
  the model, writes `evaluations/{pipeline}/{period}.json`. Caches by payload hash + prompt
  version.
- **`query.py`** — builds signal payloads (scalar + scan + full chronological series) for
  evaluate and for traceability ground-truth (`signal_numbers` / `flat_numbers`).
- **`apply_status_rules.py`**, **`update_registry.py`**, **`rebuild_*_signals.py`**,
  **`migrate_to_db.py`** — maintenance/backfill helpers.

Append/evaluate are driven via `core/generate_signal_history.py`, not these scripts directly.
