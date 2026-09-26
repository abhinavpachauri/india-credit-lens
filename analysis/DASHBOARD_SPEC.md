# Dashboard Spec — what reaches a reader

> **Live spec for all three dashboards** (`/`, `/payments`, `/nbfc`). Sections are numbered from
> §15 because §1–§14 (the July read-mode design: planes, depth ladder, grid, chip strip) were
> superseded by §17–§20 and moved on 2026-09-24 to
> `archive/docs/DASHBOARD_SPEC_read_mode_2026-07.md`, which keeps its numbering so older
> citations of §11 and §14 still resolve there.
>
> Authoring rule: ASCII layout → explicit approval → implement. Every section below is **built**
> unless its own status line says otherwise.

**What a reader sees, in order (as built, September 2026):**

| Tier | What | Section |
|---|---|---|
| Front door | one tile per dimension, carrying every read about it | §20 |
| State band | two standing sentences per dimension: **speed** (L1) and **mix** (L2) | §16 |
| Notable | cards that earned a place above the table | §18 |
| The table | one Layer 1 table per dimension; each cell opens its own chart; rows open into their sub-cut | §17, §19, §20 |
| vs the real economy | two columns (Real credit, Output) on the SIBC tables, from MoSPI — **specced, not built** | §21 |
| The chart | always the cut the card or cell is about, drawn | §15 |

---

## 15. The card↔chart cut contract (v0.2, 2026-08-25; BUILT: steps 1–4 done, stage 5.7 strict) ⭐

> **Status: built** (2026-08-25 → 08-30): the check (§15.7, gate stage 5.7, now strict), every card
> declaring its cut, the charts drawing it, and the prose rules. Findings went 52 → 0 on both
> pipelines. Applies to every pipeline by construction; a per-section fix is out of scope.

### 15.1 The defect, measured

A card is generated from a signal computed over some **cut** of the data — a set of entities and,
where the number is a share or a ratio, the total it is measured against. The chart under the card
is supposed to be that claim, drawn.

Today a card does not describe its cut. It writes down **the name of a series the chart already
renders** — `chart_series` in SIBC, `effect.focusCard` in payments. A name can only point at
something already on the chart, so when a card is about something the chart cannot draw, the name
degrades to the nearest thing that *is* drawable — the parent, or one side of a pair — and the
reader is shown a different quantity from the one the card claims. **Nothing in either gate
notices**, because a pointer that resolves to the wrong series and a pointer that resolves to the
right one are the same shape.

Enumerated over every card in both pipelines at 2026-06-30 (not sampled):

| Pipeline | Cards carrying a cut | Chart matches the claim | **Mismatched** | Cut not declared at all |
|---|---|---|---|---|
| SIBC | 32 | 15 | **17** | 0 |
| ATM/POS | 20 | 12 | **8** | **13** (card-declared rules, no registered signal) |

The 13 undeclared payments cards are not a clean bill of health — the check cannot evaluate them.
That is the same failure shape as the mismatches: *absence of a declaration reads as compliance.*

Worked example (the report that started this):

```
card   Iron and Steel holds 69.0% of basic-metals credit; Other Metal 31.0%
       cut = children of 2.13, out of 2.13
chart  Basic Metal and Metal Product — 11.2%
       cut = children of 2,    out of 2      ← different entities, different denominator
```

Both figures are correct. Neither the page nor the card says the denominator changed.

### 15.2 The contract

**A card declares the cut it is a claim about. The chart renders that cut. A cut that cannot be
resolved is a hard failure, never a fallback to an ancestor.**

The cut is not new information — every signal already records it at compute time. It is discarded
at the card boundary and replaced with a guessed series name. This contract connects what exists;
it does not add a new authored field to maintain.

### 15.3 Cut shapes — the enumerated set

Four shapes cover every card in both pipelines today. A fifth requires a spec revision, not a
special case in code.

| Shape | Means | SIBC source | ATM/POS source |
|---|---|---|---|
| `level` | one entity's own series | scalar signals (`csv_sector_yoy`, `csv_sector_abs`, …) | `csv_total_yoy`, `csv_mom_streak` |
| `decomposition` | the children of one parent | `parent_code` + `child_level` + `statement` | bank `cut` (`total` / `by_type` / `top_n`) |
| `share_of` | a part against a named total | `denominator_code` (+ `denominator_statement`) | `denominator_metrics[]` |
| `pair` | two named sides compared | `code_a` / `code_b` (a spread) | `a.metrics[]` / `b.metrics[]`, `denominator_metric` |

`level` is the already-working case and is included so the contract is total: every card has a
shape, so "no cut" stops being expressible. It covers a *named set* as well as a single entity —
`child_codes`, as in "how many of these four sectors grew", is a claim about all four.

**Correction, forced by the derivation (2026-08-25).** This table first read "SIBC has no pair
shape — it carries one measure, so there is nothing to pair". That was true of the *metric* axis
and false of the *entity* axis: `csv_sector_yoy_spread` names `code_a` and `code_b` and quotes the
distance between them, which is the same claim shape as a payments pair. It went unnoticed because
a hand-typed `chart_series` had been carrying both names all along — the authored field was
concealing a shape the spec did not have. Deriving the cuts is what surfaced it, on the first run,
by dropping a highlight that had been correct.

So `pair` spans two axes: **entities** on one measure (SIBC spreads) and **metrics** on one entity
(payments ratios and gaps). Both render as two lines with the gap between them, which is why they
are one shape and not two.

Note the two axes are independent and both already exist in payments: `cut` there means *which bank
aggregation* (§14.5 (archived read-mode record)), which is orthogonal to *which quantity*. A payments cut is therefore a pair —
(bank aggregation, quantity) — and today only the first half is declared.

### 15.4 Derivation, per pipeline

The cut is **derived, never hand-typed.** Hand-typing is what produced the two live defects below,
and a derived cut makes both unrepresentable:

- `sibc-chemicals-sub-yoy-scan` declares `chart_series: ["Chemicals and Chemical Products",
  "Petroleum, Coal Products and Nuclear Fuels"]`. Petroleum is code `2.8` — a different industry
  type, not part of chemicals (`2.9`). The chart highlights a line the card never mentions.
- `sibc-infra-sub-allocation` declares `highlight: ["Power"]`. `Power` is code `2.18.1` and is on
  no chart in the dashboard, so the highlight renders nothing at all.

| Pipeline | Where the cut comes from |
|---|---|
| SIBC | the signal's `compute` block in `registry.json` — already carries `parent_code`, `child_level`, `statement`, `denominator_code`, `denominator_statement` |
| ATM/POS, registry-backed | the signal's `compute` block — `metric`, `denominator_metric(s)`, `a`/`b` sides |
| ATM/POS, card-declared (13 cards) | the `Card` declaration, beside `reads` — these have no registered signal, so the declaration **is** the spec |

`chart_series` and `effect.focusCard` become **derived outputs** of the cut, retained only as the
wire format the web layer already consumes. Neither is authored again.

### 15.5 Resolution — and the ban on falling back

The web layer resolves a cut to concrete series at build time. Sections declare their own cut
identity so a match is an equality test on declared values, never string-matching a label — the
audit above threw one false positive (`sibc-psl-allocation`, cut `PSL` vs section `psl`) purely
from inferring identity out of names.

Resolution has exactly two outcomes: **resolved**, or **hard fail**. Rendering the nearest
resolvable ancestor is prohibited — that behaviour is the defect, and it is worse than a blank
chart because it looks like an answer.

### 15.6 Render shapes — BUILT 2026-08-26 (approved in session)

Three shapes need a layout (`level` renders as today, unchanged). All three reuse the existing
`TrendChart` / `DistributionChart` / `AtmPosTrendChart` with the section's normal Absolute / YoY /
Share controls over the full period series — a cut changes *which codes feed the chart*, never how
a chart behaves. Every L3 child carries the full 21-period history its parent does, so no shape
degrades to a single value.

**(a) `decomposition`** — 17 SIBC cards

```
┌─ INDUSTRY BY TYPE ─────────────────────────────────────────────────┐
│ Iron and Steel holds 69.0% of basic-metals credit;                 │
│ Other Metal and Metal Product 31.0%                                │
│                                                                     │
│ [ Basic Metal — 2 sub-types ▾ ]        ‹ all 19 industry types      │
│ ( ) Absolute   ( ) YoY %   (•) Share      · % of basic-metals credit│
│                                                                     │
│  72% ┤●─●─●─●                                                       │
│  69% ┤       ●─●─●──●                                    ●──●  69.0 │
│  66% ┤              ●──●──●──●──●──●──●──●──●──●──●─●               │
│  33% ┤              ○──○──○──○──○──○──○──○──○──○──○─○               │
│  30% ┤       ○─○─○──○                                    ○──○  31.0 │
│  27% ┤○─○─○─○                                                       │
│      └──────────────────────────────────────────────────────────    │
│       Dec 23        Jun 24      Mar 25        Dec 25      Jun 26    │
│       ● Iron and Steel      ○ Other Metal and Metal Product         │
│                                                                     │
│ Basic Metal is 11.2% of industry credit, growing 20.9% YoY ›        │
└─────────────────────────────────────────────────────────────────────┘
```

The footer keeps the parent's own figures — what the reader sees today — as *context with a link
back*, so the fix adds a level rather than replacing one.

**(b) `share_of`** — 3 payments cards (`cc-ecom-vs-pos-share`, `dc-atm-share-structural`,
`dc-ecom-share`) + 2 gap cards. The claim is a percentage; today the chart plots the numerator's
raw transaction count.

```
┌─ CREDIT CARD · eCommerce Transactions ─────────────────────────────┐
│ Ecommerce volume share at 50.19% — up 0.42pp from May              │
│                                                                     │
│ ( ) Absolute   ( ) YoY %   (•) Share    · % of credit card volume  │
│                                                                     │
│  50% ┤                                              ●──●──●   50.19 │
│  45% ┤                              ●──●──●──●──●                   │
│  40% ┤        ●──●──●──●──●──●──●                                   │
│      └──────────────────────────────────────────────────────────    │
│       ● eCommerce      ▫ in-store POS  ▫ ATM  ▫ other  (the total)  │
│                                                                     │
│ Denominator: POS + eCommerce + ATM + other CC volume ›              │
└─────────────────────────────────────────────────────────────────────┘
```

The denominator's components are named and individually toggleable, because "50% of *what*" is the
question the card cannot currently answer.

**(c) `pair`** — 5 payments cards. The claim is a comparison; today one side is missing entirely.

```
┌─ DIGITAL INFRASTRUCTURE · POS Terminals ───────────────────────────┐
│ Value transacted at POS grew while POS terminals deployed fell     │
│ (-21.76 pp apart over a year)                                      │
│                                                                     │
│ ( ) Absolute   (•) YoY %   [ both sides ▾ ]                         │
│                                                                     │
│ +20% ┤                    ●──●──●──●  value transacted   +6.0%      │
│   0% ┼────────────────────────────────────────────────────          │
│ −20% ┤    ○──○──○──○──○──○──○──○──○   terminals deployed −15.8%    │
│      └──────────────────────────────────────────────────────────    │
│                                          gap: −21.76 pp             │
└─────────────────────────────────────────────────────────────────────┘
```

Both sides plot on one axis in YoY, because the gap the card quotes is the distance between the two
lines — a claim that is only legible when both are drawn.

### 15.7 The gate check — write this first

A new check in **both** gates, standalone rather than folded into Check 2g or Stage 4c: those
validate that a card's *numbers* trace to `signals.db`; this validates that a card's *chart routing*
resolves. Different ground truth, and 2g is currently precise — overloading it would blunt it.

Fails on: a cut that resolves to no series · a declared series absent from the resolved cut
(catches the Petroleum and Power defects) · a card carrying no cut declaration at all (catches the
13 payments rules) · a cut whose denominator is not the one the signal computed against.

Measured like every other gate here — catch rate and false-rejection rate by injection via
`measure_groundedness.py`, appended to `ai_pm_register.json` topic #1 before the work is called done.

### 15.8 Prose defects — BUILT 2026-08-26

Content, not representation, and fixed in L1 insight generation (`signals/README` + `core.voice`).
Recorded here because the audit found them and the fixes belong together.

**A speed is never published without its size.** The growth scan's so-what now reads the cut's own
share scan and names what the leader carries — *"Jute Textiles is the fastest at 21.4% but holds
1.7% of textiles credit; the largest block, Other Textiles at 45.5%, grew 19.6%"*. The card declares
both signals in `sourceSignals`, so Check 2g scopes to their union (22 candidate values, 78× tighter
than period-wide) rather than falling back. Two SIBC cuts have no share scan and lose the size
clause rather than gain a fabricated one.

**A new gate, stage 5.8** (`guards/validate_card_prose.py`, both pipelines). `core.voice` had linted
the distribution surfaces for a year while the dashboard — the surface most people read — was linted
by nothing. Who owns the words decides the severity, per §5.3: prose we generate **hard-fails**; the
eval's narration **warns** and goes on the next prompt's fix list, because hand-editing a validated
artifact is the thing this project does not do. SEBI hits warn in both cases until the precision fix
§5.3 already calls for — the substring list trips on "what shopkeepers sell".

This required SIBC cards to start carrying `representation`, which CLAUDE.md had described since
June and the generator never emitted. Without it the gate cannot tell our sentences from the eval's.

The original three, all now closed:

1. ~~*"Lenders can lean into {fastest}"* with no size context.~~ Replaced by the pairing sentence
   above, in an observation register.
2. ~~The same sentence is advice, and dashboard prose is linted by nothing.~~ Stage 5.8. The audit
   also found worse than the lint could see: a card instructed the reader to *"Move everything to
   UPI QR"* and asserted *"there is no viable future for Bharat QR"* — neither phrase was in the
   advice or forecast lists. Both lists widened, each addition evidenced by a live hit; a bare
   `will be` was tried and dropped for firing on ordinary comparative prose.
3. ~~`infra-qr-per-pos` live with its number missing.~~ The dominance guard stripped **every**
   number from a headline rather than a trailing stale rate, so a title whose number was its
   subject shipped empty. Now anchored to the end and to rate-shaped tokens.

**Two more found while fixing those.** Deterministic payments prose spoke M/K/B while the eval layer
normalises to lakh and crore and `core.voice` flags the M/K form — the dashboard said it both ways
depending on the card. `fmt_num` now speaks Indian units, which surfaced that
`traceability.extract_numbers` read "73,426" as two numbers and rejected both; digit-grouping commas
are collapsed first, narrowly enough that "In 2026, 45% of…" is untouched.

### 15.9 Build order

1. ~~**§15.7 gate check** — before any fix.~~ **DONE 2026-08-25.** `guards/validate_card_cuts.py`,
   advisory as stage 5.7 in both gates. Catch 100% (98/98 injections), false rejection 0%.
2. ~~§15.2–§15.5 contract + one resolver per pipeline.~~ **DONE 2026-08-26.** All 95 SIBC and 33
   payments cards declare `effect.cut`; `chart_series` and `focusCard` are derived from
   `core/cuts.py`, shared with the check so the two cannot drift (guarded by C5). Findings
   52 → 38: **C2 6 → 0, C4 13 → 0, C5 0**. What remains is C1/C3 — the charts that cannot yet draw
   the cut, which is step 3's job and is now visible rather than silent.
3. ~~§15.6 render shapes.~~ **DONE 2026-08-26.** SIBC sections carry a `subCuts` entry for every
   code RBI breaks down further (`buildSubCuts`, one level deep — RBI publishes no fourth), and the
   payments read surface renders `share_of` on its own denominator (`buildShareData`) and `pair` on
   its two named sides (`buildPairData`). **Findings 38 → 0 on both pipelines.**
4. ~~Flip stage 5.7 to `--strict`.~~ **DONE 2026-08-26**, the moment the count reached zero.
5. §15.8 prose fixes — independent, still open.

**A pair's sides are bundles, not metrics.** `csv_pair_divergence` authors a label per side, and one
side can be several metrics — "value transacted at POS" is credit-card POS value plus debit-card POS
value. The first cut flattened both sides into one metric list and drew three unlabelled lines under
a two-sided claim; the Cut now carries `sides`, so the chart plots one line per side under the name
the card's own prose uses.

**One remount rule worth keeping.** `TrendChart` seeds its hidden-series state once via `useState`,
so a sub-cut inherited whichever legend toggles the parent chart was left in — its defaulted-off
"Total" came back. The charts are keyed by the cut's id: same key within a section, so a reader's own
toggles survive switching cards; new key on a sub-cut, so its defaults apply.

**Fixed outright in step 2** (no chart change needed): 7 highlights that rendered nothing, 1 card
highlighting a series from a different industry, and `gap-atm-offsite-decline`, which pointed at
`atm_offsite` — a metric, not a section — so `AtmReadMode`'s `?? SECTION_DEFS.find(d => d.group ===
group)` drew POS terminals under a card about off-site ATMs.

At every step: both gates green, both pipelines, no per-section branches.

---

## 16. The standing state tier (v1.0 — BUILT 2026-09-11) ⭐

> Arc 1 of `archive/docs/PLAN_2026-09-09.md`. **Rendering only.** Every number below is already computed,
> already gate-validated, and has never reached a browser.

### 16.1 The problem this answers

The top tier of read mode is *what is news*. This period that is **29 of 96** SIBC cards
(planes: 29 read / 17 composition / 50 subject; payments 9 / 1 / 22). Twenty-nine cards is
not an answer to "what is happening" — and in a quiet month the honest answer is *nothing
crossed the threshold*, which leaves the reader with a directory.

Meanwhile `system_state_{period}.json` computes, every ingestion, a **mix state per cut**:
`steered` / `drifting` / `contested` / `reallocating`, with `toward`, `away_from` and the
tilt in pp. It is validated by both gates and ships nowhere.

**So: add a tier above the reads. Do not redesign.** The §14 (archived read-mode record) layout and the §15 cut contract
stay exactly as they are.

### 16.2 What the tier says — the layer boundary, made legible

Two sentences per cut, present **every period whether or not anything is news**:

```
speed   Non-food credit growing 19.1% YoY, accelerating.        ← L1: how fast
mix     Steered toward Services (+5.8pp), away from Personal    ← L2: is anyone steering
        Loans.
```

That contrast is the whole point of the tier. L1 is the speed; L2 is whether the mix is
being managed. A reader sees the two layers doing different jobs in one block.

### 16.3 Sentence grammar (deterministic, rendered in Python)

**speed** — needs the cut's declared `parent_yoy` signal. The pace word comes from that
signal's own last two readings, not from the movement family's acceleration row: that row is
keyed to the momentum signal's parent code, which is absent for two cuts, and a clause that
appears for one industry cut and not the other reads as a finding when it is a lookup gap.
The band is ±0.5 pp — deliberately the same band `ACCEL_DEFAULT_RULES` uses.

| Case | Renders |
|---|---|
| rate up more than 0.5 pp | `Industry credit growing 20.0% YoY, accelerating.` |
| rate within ±0.5 pp | `Personal loans growing 16.2% YoY, at a steady pace.` |
| rate down more than 0.5 pp | `Infrastructure credit growing 10.2% YoY, but slowing.` |
| negative rate | `POS terminals at -15.8% YoY, contracting.` |
| **no `parent_yoy`** | **whole line omitted** |
| **dominance-guarded** | `POS terminals at -15.8% YoY — but it's ICICI Bank, not the market.` |

**Every rate is SIGNED.** "shrinking 15.8%" reads more naturally and was the first thing the
traceability stage rejected: the stored row is `-15.8269`, so the unsigned figure traces to
nothing. Direction lives in the verb *and* in the number, which is the only version a gate
can check.

**mix** — needs the cut's `mix_states` entry.

| State | Renders |
|---|---|
| `steered` | `Steered toward Medium — it took 14.0% of the growth while holding 9.2% of the total. Away from Large.` |
| `drifting` | `Drifting toward …` (same shape) |
| `contested` | `Contested — parts are moving in opposite directions, with no single destination.` |
| `reallocating` | `Reallocating — gains and losses very nearly cancel.` |

**The tilt is never printed as a pp figure.** It is `alloc − weight` — a subtraction, which
traces to nothing. Both operands *are* stored rows, so the sentence quotes those instead. That
is simultaneously the checkable version and the plainer English one: "+4.9 pp" asks the reader
to decode a tilt; "took 14.0% of the growth while holding 9.2% of the total" *is* the tilt.

**The growth/contraction noun is read off the stored net**, never assumed. A coherent cut can
be one in which every part is shrinking, and "took 14% of the growth" would then be the exact
inversion of what happened — the mistake the movement family's contested branch already made
once, on POS terminals.

**No third line, and no coherence number.** The regime *word* carries the meaning (decision #4:
coherence lives in a state file, not signals.db, so no gate can ground it — an invented `0.73`
PASSED). A "4 of 4 parts agree" count was considered and dropped: `children` is `0` in every
contested/reallocating window (`alloc` is withheld below 0.90), so the count would read "0 of 4"
exactly where the finding is most interesting.

### 16.4 Page 1 — the grid front door (desktop 1440)

Every value below is real, read off `sibc_l1_annotations.json` + `sibc_planes.json` +
`system_state_2026-08-31.json` on 2026-09-11. **Bold = net-new in this arc; everything
else is on screen today.**

```
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║  India Credit Lens · RBI Sectoral Deployment                       [Read ⇄ Explore]  ☾   ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝

  THE READ · 29 MOVED THIS AUGUST
  ┌──────────────────────────┐ ┌──────────────────────────┐ ┌──────────────────────────┐
  │▎Vehicle loans at 18.78%  │ │▎Medium Enterprises 29.20%│ │▎PSL Others -1.12% YoY —  │
  │ YoY — highest in this    │ │ YoY — highest on record, │ │ least severe contraction │
  │ window                   │ │ up 1.66pp                │ │ on record, up 8.28pp     │
  │ ▲ record · YoY  Personal │ │ ▲ record · YoY   Priority│ │ ▲ record · YoY   Priority│
  └──────────────────────────┘ └──────────────────────────┘ └──────────────────────────┘
  ┌──────────────────────────┐ ┌──────────────────────────┐
  │▎Credit card outstanding  │ │▎Consumer Durables turned │      +24 more moved →
  │ fell to ₹2.98L Cr —      │ │ positive at 0.39% YoY —  │
  │ first decline in 2 per.  │ │ first growth in 11 per.  │
  │ ▼ reversal · Abs Personal│ │ ▲ reversal · YoY Personal│
  └──────────────────────────┘ └──────────────────────────┘

  BROWSE · 7 DIMENSIONS · 96 INSIGHTS
  ┌────────────────────────────┐ ┌────────────────────────────┐ ┌────────────────────────────┐
  │ 🏦                         │ │ 📊                         │ │ 🏭                         │
  │ Bank Credit                │ │ Main Sectors               │ │ Industry by Size           │
  │                            │ │                            │ │                            │
  │ ▲ 19.3% YoY · accelerating │ │ ▲ 19.1% YoY · accelerating │ │ ▲ 20.0% YoY · accelerating │  ← ★ NEW
  │                            │ │ ⇢ steered → Services       │ │ ⇢ drifting → Medium        │  ← ★ NEW
  │                            │ │                            │ │                            │
  │ 9 insights      ▲ 4 moved  │ │ 13 insights     ▲ 5 moved  │ │ 10 insights     ▲ 4 moved  │
  └────────────────────────────┘ └────────────────────────────┘ └────────────────────────────┘
  ┌────────────────────────────┐ ┌────────────────────────────┐ ┌────────────────────────────┐
  │ 🛎️                         │ │ 💳                         │ │ ⭐                         │
  │ Services                   │ │ Personal Loans             │ │ Priority Sector            │
  │                            │ │                            │ │                            │
  │ ▲ 22.9% YoY · accelerating │ │ ▲ 16.2% YoY                │ │                            │
  │ ⇢ steered → NBFCs          │ │ ⇢ drifting → gold jewellery│ │ ⇢ drifting → Micro & Small │  ← no rate exists
  │                            │ │                            │ │                            │
  │ 8 insights      ▲ 1 moved  │ │ 25 insights     ▲ 9 moved  │ │ 14 insights     ▲ 4 moved  │
  └────────────────────────────┘ └────────────────────────────┘ └────────────────────────────┘
  ┌────────────────────────────┐
  │ 🔩                         │
  │ Industry by Type           │
  │                            │
  │ ▲ 20.0% YoY                │      ← no acceleration row for code 2 on Statement 2:
  │ ⇢ drifting → All Engineer. │        the clause is dropped, not invented
  │ ⇢ contested (infra sub)    │      ← a dimension carrying TWO cuts shows two ⇢ rows
  │ 17 insights     ▲ 2 moved  │
  └────────────────────────────┘
```

**What changes on this page:** two rows inside each dimension tile. Nothing else. The read
grid, the ordering, the counts, the chrome are all untouched.

**What it buys:** the browse grid stops being a directory. Today a reader who sees "Services ·
8 insights · ▲ 1 moved" learns only that services is quiet. Now they learn services credit is
growing **22.9% and accelerating**, and that its mix is being **steered toward NBFCs** — which
is the single most consequential thing in the SIBC data this period, and it was invisible
because it is not news, it is *state*.

**Every dimension carries the band — that is the point of a standing tier.** A band that
appears on some sections and not others reads as a feature, not as furniture, and the reader
cannot tell a section with nothing to say from one that failed to load. So each dimension has
a block, and each block answers both questions — with a reading, or with a stated reason.

Two dimensions can only half-answer, and both say so in the detail pane rather than going
quiet: **Bank Credit** is the whole book, whose only split at that level is food vs non-food —
an accounting line, not a mix anyone steers; **Priority Sector** is a memo lens over the main
tree rather than a slice of it, so RBI publishes no total for it to grow at. Those reasons are
DECLARED on the cut, never inferred — a silently short block is indistinguishable from a
broken one.

---

### 16.5 Page 2 — click "Industry by Size" (desktop 1440)

This is the worked example, because it is the one where **the state band changes how the top
card reads**.

```
  ‹ Credit dashboard                                    [Brief] [·Full·] [Deep ⌁]
                                                        Detail: with the reasoning

  ‹ ★ What moved·▲29 │🏦 Bank Credit·▲4│📊 Main Sectors·▲5│【🏭 Industry by Size·▲4】│🛎️ Serv… ›

  ┌─ RAIL (360px) ────────────┐  ┌─ DETAIL ──────────────────────────────────────────────┐
  │ INDUSTRY BY SIZE ·        │  │▎🏭 INDUSTRY BY SIZE                                   │
  │ 10 INSIGHTS · ▲ 4 MOVED   │  │                                                       │
  │                           │  │ ┌───────────────────────────────────────────────────┐ │ ★
  │ ┌───────────────────────┐ │  │ │ THE STATE · every month, news or not              │ │ ★
  │ │ Medium growing        │ │  │ │                                                   │ │ ★
  │ │ fastest at 30.5%;     │ │  │ │ speed   Industry credit growing 20.0% YoY,        │ │ ★
  │ │ Large slowest 17.7%   │ │  │ │         accelerating.                             │ │ ★
  │ └───────────────────────┘ │  │ │                                                   │ │ ★
  │                           │  │ │ mix     Drifting toward Medium (+4.9pp), away     │ │ ★
  │  Large                    │  │ │         from Large.                               │ │ ★
  │ ┌───────────────────────┐ │  │ └───────────────────────────────────────────────────┘ │ ★
  │ │ Large corporates at   │ │  │                                                       │
  │ │ 67.3% — down 0.18pp   │ │  │ Large took 60.8% of all new industry credit in the    │
  │ └───────────────────────┘ │  │ past year                                             │
  │ ┌───────────────────────┐ │  │                                                       │
  │ │▲Large corporate credit│ │  │  ○ Absolute  ● YoY %  ○ Share      [Total: off]       │
  │ │ at 17.7% YoY —        │ │  │ ┌───────────────────────────────────────────────────┐ │
  │ │ highest on record     │ │  │ │ 32│              ╭──── Medium 30.5%               │ │
  │ └───────────────────────┘ │  │ │ 28│        ╭─────╯                                │ │
  │ ┌───────────────────────┐ │  │ │ 24│   ╭────╯   ╭──── Micro & Small 22.6%          │ │
  │ │▲Large took 60.8% of   │ │  │ │ 20│───╯   ╭────╯                                  │ │
  │ │ all new industry      │ │  │ │ 16│━━━━━━━━━━━━━━━ LARGE 17.7%  ← highlighted     │ │
  │ │ credit ◀ SELECTED     │ │  │ │   └──────────────────────────────────────────────  │ │
  │ └───────────────────────┘ │  │ │    Sep25  Nov25  Jan26  Mar26  May26  Jul26        │ │
  │                           │  │ └───────────────────────────────────────────────────┘ │
  │  Medium                   │  │                                                       │
  │ ┌───────────────────────┐ │  │ Composition: Micro & Small grew 8.9% in FY25, 32.7%   │
  │ │▲Medium enterprises at │ │  │ in FY26 — 23.8pp step-up                              │
  │ │ 10.0% share — record  │ │  │                                                       │
  │ └───────────────────────┘ │  │ Of the industry credit added over the past twelve     │
  │ ┌───────────────────────┐ │  │ months, Large took 60.8% — the largest share of the   │
  │ │▲Medium enterprises at │ │  │ new money — growing 17.7% and accelerating. The rest  │
  │ │ 30.5% YoY — record    │ │  │ went to Micro and Small 25.2%; Medium 14.0%. …        │
  │ └───────────────────────┘ │  │                                                       │
  │                           │  │ WHY THIS READS                                        │
  │  Micro and Small          │  │ 1. Every sector's industry credit is compared with    │
  │ ┌───────────────────────┐ │  │    the same month a year earlier, and each one's      │
  │ │ Micro & Small grew    │ │  │    share of the total increase is taken.              │
  │ │ 8.9% FY25, 32.7% FY26 │ │  │ 2. Large accounts for 60.8% of the increase.          │
  │ └───────────────────────┘ │  │ 3. All sectors moved the same way this window, so     │
  │ ┌───────────────────────┐ │  │    the shares are bounded and sum to a hundred.       │
  │ │ Micro & Small at      │ │  │                                                       │
  │ │ 22.8% share — off     │ │  └───────────────────────────────────────────────────────┘
  │ │ five-period plateau   │ │
  │ └───────────────────────┘ │
  │ ┌───────────────────────┐ │   ★ = net-new. Everything else renders today,
  │ │ Micro & Small 22.6%   │ │       unchanged, in this exact position.
  │ │ YoY — 4th straight    │ │
  │ │ deceleration          │ │
  │ └───────────────────────┘ │
  │ ┌───────────────────────┐ │
  │ │ MSME-Large spread at  │ │
  │ │ 4.9pp — narrowest     │ │
  │ │ since Mar 2025        │ │
  │ └───────────────────────┘ │
  └───────────────────────────┘
```

#### Why this example is the argument for the whole tier

Read the selected card alone: **"Large took 60.8% of all new industry credit — highest on
record."** The natural reading is *lenders are concentrating into large corporates.*

Now read the state band above it: **the mix is drifting toward Medium, away from Large.**

Both are true, and the band is what makes the card readable:

| | Large | Medium | Micro & Small |
|---|---|---|---|
| share of the **book** (weight) | 68.6% | 9.2% | 22.3% |
| share of the **new money** (alloc) | 60.8% | 14.0% | 25.2% |
| **tilt** | **−7.8pp** | **+4.9pp** | +2.9pp |

Large takes most of the new money **because it is most of the book** — and it is taking
*less* than its weight. That is the L1/L2 boundary in one screen: **L1 is where the money
went; L2 is whether that changed the shape of the book.** No amount of ranking or re-ordering
of cards produces that sentence. It has been computed every period since August and has never
been rendered.

#### Behaviour rules

- The band belongs to the **dimension**, so it does **not** change as the reader clicks
  between the 10 cards in the rail. The chart and card below it change; the state stands.
- It renders at **every depth** — `Brief` collapses the card body and the why-chain, never
  the state. A reader on Brief gets chart + state, which is the fastest honest answer.
- It is **not** a card: no id, no plane, no news score, never in the rail, never in
  `+24 more moved`. It is chrome for the dimension.

---

### 16.5b The same page, two other dimensions (the branches that differ)

**Industry by Type — two cuts on one dimension, stacked and named:**

```
  │ ┌───────────────────────────────────────────────────┐ │
  │ │ THE STATE · every month, news or not              │ │
  │ │                                                   │ │
  │ │ Industry credit                                   │ │
  │ │ speed   Industry credit growing 20.0% YoY.        │ │  ← no accel row → clause dropped
  │ │ mix     Drifting toward All Engineering (+5.1pp), │ │
  │ │         away from Infrastructure.                 │ │
  │ │ ────────────────────────────────────────────────  │ │
  │ │ Infrastructure sub-types                          │ │
  │ │ mix     Contested — parts are moving in opposite  │ │  ← no speed line at all;
  │ │         directions, with no single destination.   │ │    the mix line stands alone
  │ └───────────────────────────────────────────────────┘ │
```

The cut name is shown **only when a dimension carries more than one** — a single-cut
dimension would be repeating its own title.

**Bank Credit and Priority Sector — a row that carries its reason instead of a number:**

```
  │ ┌───────────────────────────────────────────────────┐ │
  │ │ THE STATE · every month, news or not              │ │
  │ │                                                   │ │
  │ │ SPEED   Bank credit growing 19.3% YoY,            │ │
  │ │         accelerating.                             │ │
  │ │ MIX     — This is the whole book — its only split │ │   ← muted italic,
  │ │           here is food vs non-food credit, which  │ │     a stated fact
  │ │           is an accounting line rather than a mix │ │     about the data
  │ │           anyone steers.                          │ │
  │ └───────────────────────────────────────────────────┘ │

  │ │ SPEED   — Priority sector is a memo lens over the │ │
  │ │           main tree, not a slice of it, so RBI    │ │
  │ │           publishes no total for it to grow at.   │ │
  │ │ MIX     Drifting toward Micro and Small           │ │
  │ │         Enterprises — it took 37.2% of the growth │ │
  │ │         while holding 30.0% of the total. …       │ │
```

**Payments / POS Terminals — the dominance guard, which is why this is not optional:**

```
  │ ┌───────────────────────────────────────────────────┐ │
  │ │ THE STATE · every month, news or not              │ │
  │ │                                                   │ │
  │ │ speed   POS terminals down 15.8% YoY — but that   │ │
  │ │         is ICICI Bank, not the market.            │ │
  │ │ mix     Contested — parts are moving in opposite  │ │
  │ │         directions, with no single destination.   │ │
  │ └───────────────────────────────────────────────────┘ │
```

−15.8% YoY is the figure this project already established is ~98% one issuer's
reclassification. A *standing* line publishes it **every month, forever**, so the speed clause
routes through `signals/dominance.py` — whose `SCAN_FOR` already maps all three payments
parent signals. Without that, this arc would re-introduce the exact defect
[[feedback_why_over_what]] was written about.

---

### 16.6 Mobile — 375px

```
┌───────────────────────────────┐   ┌───────────────────────────────┐
│ India Credit Lens        ☾    │   │ ‹ Credit dashboard            │
│ [Read ⇄ Explore]              │   │ [Brief] [·Full·] [Deep ⌁]     │
│                               │   │                               │
│ THE READ · 29 MOVED           │   │ ‹ ★│🏦│📊│【🏭】│🛎️│💳 ›       │
│ ┌───────────────────────────┐ │   │                               │
│ │▎Vehicle loans at 18.78%   │ │   │▎🏭 INDUSTRY BY SIZE           │
│ │ YoY — highest in window   │ │   │ ┌───────────────────────────┐ │
│ │ ▲ record · YoY   Personal │ │   │ │ THE STATE                 │ │ ★
│ └───────────────────────────┘ │   │ │                           │ │ ★
│ ┌───────────────────────────┐ │   │ │ speed                     │ │ ★
│ │▎Medium Enterprises 29.20% │ │   │ │   Industry credit growing │ │ ★
│ │ ▲ record · YoY   Priority │ │   │ │   20.0% YoY, accelerating.│ │ ★
│ └───────────────────────────┘ │   │ │                           │ │ ★
│           …                   │ │  │ │ mix                       │ │ ★
│ +24 more moved →              │   │ │   Drifting toward Medium  │ │ ★
│                               │   │ │   (+4.9pp), away from     │ │ ★
│ BROWSE · 7 DIMENSIONS         │   │ │   Large.                  │ │ ★
│ ┌────────────┐ ┌────────────┐ │   │ └───────────────────────────┘ │ ★
│ │ 🏦         │ │ 📊         │ │   │                               │
│ │ Bank Credit│ │ Main Sect. │ │   │ Large took 60.8% of all new   │
│ │            │ │            │ │   │ industry credit in the past   │
│ │ ── no cut  │ │ ▲ 19.1% ·  │ │   │ year                          │
│ │            │ │   accel.   │ │   │                               │
│ │            │ │ ⇢ steered →│ │   │ ○ Abs ● YoY ○ Share           │
│ │            │ │   Services │ │   │ ┌───────────────────────────┐ │
│ │ 9 · ▲4     │ │ 13 · ▲5    │ │   │ │      [ chart ]            │ │
│ └────────────┘ └────────────┘ │   │ └───────────────────────────┘ │
│ ┌────────────┐ ┌────────────┐ │   │ Composition: …                │
│ │ 🏭         │ │ 🛎️         │ │   │ Of the industry credit added… │
│ │ Industry   │ │ Services   │ │   │                               │
│ │ by Size    │ │            │ │   │ WHY THIS READS                │
│ │ ▲ 20.0% ·  │ │ ▲ 22.9% ·  │ │   │ 1. Every sector's industry…   │
│ │   accel.   │ │   accel.   │ │   │                               │
│ │ ⇢ drifting │ │ ⇢ steered →│ │   │ ── rail moves BELOW ──        │
│ │   → Medium │ │   NBFCs    │ │   │  Large                        │
│ │ 10 · ▲4    │ │ 8 · ▲1     │ │   │  ▸ Large corporates at 67.3%  │
│ └────────────┘ └────────────┘ │   │  ▸ ▲Large corporate credit …  │
└───────────────────────────────┘   └───────────────────────────────┘
       grid, 2 columns                    detail, single column
```

Mobile rules: the label column (`speed` / `mix`) **stacks above** its sentence below 640px.
Tiles stay 2-up; the state rows wrap to two lines each and the tile grows — acceptable,
because the tile is now carrying the answer rather than a count. No horizontal scroll at
375px (the existing hard rule).

### 16.7 What it says today, all ten cuts (real values, 2026-09-11)

| Cut | speed | mix |
|---|---|---|
| **Bank Credit** | growing 19.3% YoY, accelerating | *no mix — the only split here is food vs non-food* |
| Main sectors | growing 19.1% YoY, accelerating | **steered** → Services (+5.8pp), away Personal Loans |
| Industry by size | growing 20.0% YoY, accelerating | drifting → Medium (+4.9pp), away Large |
| Industry by type | growing 20.0% YoY | drifting → All Engineering (+5.1pp), away Infrastructure |
| Services | growing 22.9% YoY, accelerating | **steered** → NBFCs (+17.2pp), away Other Services |
| Personal loans | growing 16.2% YoY, holding its pace | drifting → gold jewellery (+21.0pp), away Housing |
| Priority sector | *no total — a memo lens, not a slice* | drifting → Micro & Small, away Housing |
| Infrastructure sub-types | growing 10.2% YoY, but slowing | **contested** |
| Credit cards | growing 9.9% YoY | **steered** → Small Finance Banks (+9.7pp), away Foreign Banks |
| Debit cards | growing 2.0% YoY | **reallocating** |
| POS terminals | down 15.8% YoY — **but that is ICICI Bank, not the market** | **contested** |

Three things to read off that table:

1. **Payments is where the regimes fire.** Every SIBC cut runs coherence 0.99–1.00; payments
   gives the tier its first live `contested` and `reallocating` renders.
2. **The dominance guard is load-bearing here, not optional.** POS terminals at −15.8% YoY is
   the exact number this project already established is ~98% one issuer's reclassification.
   A standing line would republish it every month. The tier therefore routes its speed clause
   through `signals/dominance.py` (`SCAN_FOR` already maps all three payments parent signals).
3. **The only genuine absences are facts about the data, and they are stated.** PSL has no
   total because it is a memo lens (`additive: false`); Bank Credit has no mix because its only
   split is food vs non-food. Infrastructure sub-types looked like a third but was a real gap —
   closed by adding `sibc-infra-yoy`, which now reads **10.2% YoY but slowing** against a
   **contested** mix, one of the better lines on the board.

### 16.8 What was built

| Piece | File |
|---|---|
| The one renderer, both pipelines | `analysis/core/state_lines.py` |
| Two declared fields per cut | `MovementCut.parent_yoy` / `.parent_label` in `core/movement_cards.py`, filled in each pipeline's own `MOVEMENT_CUTS` |
| The parent signal infrastructure lacked | **`sibc-infra-yoy`** (code `2.18`, Statement 2) — registry 266 → 267, 11 periods backfilled |
| The sidecar | `analysis/signals/stamp_state.py` → `web/public/data/{pipeline}_state.json`, `--check` freshness guard |
| The gate stages | **5.9** `stamp_state` + **5.9b** `state_band` (`analysis/guards/validate_state_band.py`), both pipelines, placed after `system_state` because that is what computes the mix |
| The band | `StateBand` in `components/read/parts.tsx` — shared, so both pipelines inherit one design. Renders BOTH rows always; an empty one carries its declared reason |
| Dimensions with a rate but no mix | `RateOnlyCut` + each pipeline's `STATE_RATE_ONLY`, declared beside `MOVEMENT_CUTS` |
| The tile rows | `DimensionCard` in the same file |
| Data layer | `web/lib/state.ts` |

**Sentences are rendered in Python and shipped as strings; the browser formats nothing.**
That is not only compute-once-ship-compact — it is what makes the band checkable at all. A
browser that formats numbers is a publishing surface no validator can see, and this is the
first place the dashboard publishes a Layer-2 reading.

**Freshness came free.** `check_derived_fresh` is manifest-driven, so declaring `derived` on
the new stage took the watched-artifact count from 19 to 21 with no edit to the guard.

### 16.8b Measurement (AI PM topic #1)

Injection over **every** block and **every** number in both sidecars — enumerated, not sampled.

| | |
|---|---|
| near-miss catch (nudged past display rounding) | **23/23 = 100%** |
| in-range catch (a fresh value from the block's own span) | **20/20 = 100%** |
| false rejection (untouched text) | **0/23 = 0%** |

Two things the measurement changed, both worth keeping:

1. **Scope, not tolerance, was the whole game.** Ground truth first used `flat_numbers`, which
   returns a signal's entire history — pools of 160–309 values. Four near-misses survived, none
   through tolerance slack: each landed on one of the signal's *own past readings*. The band
   never quotes history, so the scope narrowed to *this period's rows for the entity the
   sentence names*, taking pools to single digits and catch to 100%. Same lesson as Check 2g's
   `sourceSignals` and 4f's `evidence_all`: **a traceability gate is its scope.**
2. **Three "misses" were the harness reporting on itself.** Where a block's pool holds one
   value, `[lo, hi]` is a point and the only drawable number is the true one — so the harness
   was injecting the real value and scoring the gate for accepting it. Excluded as undefined.
   Fourth instance in three days of a probe producing a false negative; the tell each time is
   a probe that returns the same answer regardless of input.

### 16.12 The band follows the cut on screen (BUILT 2026-09-15) ⭐

Arc 1 shipped the band at DIMENSION level: ten blocks over ten anchor cuts. Layer 2 computes a
mix state for **forty** cuts, so thirty were computed every ingestion, gate-validated, and never
reached a browser — the finding Arc 1 opened with, one level down.

**The population is now DERIVED**, not listed. It was `MOVEMENT_CUTS`, a hand-written table in
the card generator, sitting beside a table layer that discovers its forty cuts from the registry.
A cut qualifies for a block by having a mix state; what it needs to SPEAK is a parent rate, and
the two pipelines hold that differently — so both are resolved from the registry rather than
declared twice:

| | parent rate |
|---|---|
| payments measure | its own total-YoY aggregate (all 26 have one) |
| SIBC sub-cut | one ROW of its parent table's YoY scan — RBI publishes no basic-metals total |

That second case is why `speed_line` takes a `parent_entity` and why a block carries it: the gate
scopes that number to the row the sentence names, so the pool stays in single digits.

**A measure SWAPS the band; an expanded row STACKS a second block.** The rule is what the reader
is looking at: a measure filter replaces the table, so it replaces the band; a row expansion
leaves the parent table on screen, so the parent's state stays with it.

    ┌─ Credit card eCommerce transactions ───────────────┐   measure = swap
    │ speed  growing 27.5% YoY, but slowing.             │
    │ mix    Drifting toward Public Sector Banks — took  │
    │        46.0% of the growth, held 27.7% a year ago. │
    └────────────────────────────────────────────────────┘

    ┌─ Industry credit ──────────────────────────────────┐   row = stack
    │ speed  growing 20.0% YoY, accelerating.            │
    ├─ Basic Metal and Metal Product credit ─────────────┤
    │ speed  growing 21.9% YoY, accelerating.            │
    │ mix    Drifting toward Iron and Steel — took 75.5% │
    │        of the growth, held 67.7% a year ago.       │
    └────────────────────────────────────────────────────┘

**A block declares whether it is the dimension's ANCHOR**, and the tile shows the anchor only: a
payments group carries eleven measures, and a tile listing eleven has stopped being a summary.
Declared by the generator's cut table, so widening the band cannot quietly rewrite the front door.

Blocks: SIBC 8 → **15**, payments 3 → **28**. Injection: payments 3/3 caught including a 0.1
near-miss; SIBC 2/3 — the survivor (19.8 → 19.9) sits inside the DISTRIBUTION policy's declared
0.5% relative tolerance, which is a tolerance decision, not a scope hole.

### 16.13 What the band and the cards may not both say (2026-09-15)

Two tiers earn their keep when they say DIFFERENT things about one cut: the band names where
the mix is tilting (*drifting toward Medium*), a card names the largest taker (*Large took
60.8%*). Both true, neither implied by the other.

They COMPETE when the card's entity and number are the band's own. Measured over the live
feed: **5 of 56 shown cards**, e.g. *"Bank credit at 19.3% YoY — fastest growth in this window"*
above a band reading *"Bank credit growing 19.3% YoY, accelerating"*, and a POS card that was the
band's sentence almost verbatim. Those are now marked `superseded_by_band` in the planes sidecar
and hidden from the notable list — **hidden, never deleted**: still generated, still gated, still
in Explore.

The rule requires the same NUMBER and the same thing measured (a shared signal, or the band's
subject being the card's). Number alone would suppress a different sector growing at the same
rate; a shared signal alone would suppress *Large took 60.8%*, which rests on the very allocation
rows the mix line reads and says something the band does not.

**This makes the planes stage depend on the band**, so it now runs after it (5.9 → 5.9a). A wrong
order fails silently — the rule simply compares against last month's band — so a test asserts the
order rather than trusting the manifest to stay in shape.

### 16.14 Order and emphasis (user, 2026-09-15)

- **What's notable sits ABOVE the table** in every dimension pane. The news is what a returning
  reader came for; the state is what they read next.
- **A dimension tile carries ALL of its notable items**, not three and a count. A count is not the
  news, and a reader deciding which dimension to open needs the items. The grid drops from three
  columns to two to give them the width. The tile's footer counts what is NOT on it (composition
  and gaps), because two counts of the same word is a tile arguing with itself.
- **The deeper reading (L2/L3) is off** while Layer 1 is being got right — `DEEP_ENABLED = false`
  in the shell. Display only: the opportunities feed is still built, still gated, still reachable
  at /opportunities.

### 16.9 Constraints carried in (non-negotiable)

- The regime **word** only, never the coherence number.
- Never a derived number: a subtraction traces to nothing, so its operands are quoted instead.
- An absent input renders its **declared reason**, never a placeholder, a zero, or a neighbour's
  number — and never silence: this is standing furniture, so a row that vanishes reads as broken.
- **Every dimension has a band.** Enforced by a test over the live artifacts, not by review.
- A dominated aggregate is **attributed, not suppressed** — the figure is real, the market
  reading is not.
- Cards **nest, never merge**. Checks 2g / 4c / 5.7 / 5.8 untouched. Presentation layer.

### 16.10 Decisions taken (user, 2026-09-11)

1. **Label style** — `speed` / `mix`, not `L1 speed` / `L2 mix`. The layer boundary is taught
   by the two lines doing visibly different jobs, not by naming the layers at the reader.
2. **`sibc-infra-yoy` added** rather than accepting the absence, so infrastructure sub-types
   carry a speed line. Priority Sector keeps its absence — it is a memo lens with no total,
   which is a fact about the data, not a gap in the registry.
3. **Grid tiles grow.** The browse grid stops being a directory; that is worth two rows.

### 16.11 Still open

- **SIBC ships its raw CSV for the browser to parse** while payments ships a compact artifact.
  Untouched here (the band is a new sidecar, not a change to how the charts get their data),
  but it remains the one compute-once-ship-compact violation on the dashboard.


---

## 17. The Layer 1 table (v0.1 — approved 2026-09-12, BUILT) ⭐

> Written before the code. The surface that finally shows what Layer 1 measures.

### 17.1 Why

The dashboard rendered Layer 1 as **cards** — one signal, one card, 96 of them on credit. A reader
asking "what is happening in industry" got the answer spread across nine cards in a rail, in
generation order. Meanwhile the mix post that worked was a **table**: every part of one cut, side
by side, with size, share, growth, pace and the run of readings on one line.

The card is the right unit for *news*. The table is the right unit for *state*.

### 17.2 The unit is a cut; the row is a part

One table per cut. Columns are the six Layer 1 families (`signals/README.md`):

| column | family | reads |
|---|---|---|
| Size | size | `{stem}-size-scan` |
| of cut | allocation | `{stem}-allocation` / `weight_now` |
| of book | share | `{stem}-share-of-credit-scan` (SIBC only — a payments cut's parent IS its root) |
| Growth | growth | `{stem}-yoy-scan` |
| Pace | pace | `{stem}-acceleration` |
| Run | growth | the same signal's trailing series |
| New ₹ | allocation | `{stem}-allocation` / `alloc` |

**The table makes the pairing rule structural.** A share of new money cannot be rendered without
that part's speed and acceleration, because they are cells in the same row. It stopped being a
rule the builder has to remember.

**"of cut" comes from `weight_now`, not the share scan.** The share scan divides by the parent's
published row; `weight_now` divides by the sum of the parts — the same denominator as `weight`, so
the Mix view's "then vs now" is like-for-like. Where they disagree (main sectors, 4.9%) the
difference is stated as a footer, never hidden:

    These four are 95.1% of non-food credit. RBI attributes the remaining
    ₹10.72L crore to no sector.

### 17.3 Numbers are rendered in Python and shipped as strings

Same rule as the state band (§16.8), for the same reason: **a browser that formats numbers is a
publishing surface no validator can see.**

Each cell ships as `{display, sort}` — `display` is the authoritative rendered string and the only
thing drawn; `sort` is the raw value, used for ordering and **never shown**. A column the data
cannot fill ships `null` and renders as `—`, never 0 and never blank.

### 17.4 Layout

```
 ▎🛎️ SERVICES                                 【Numbers】[ Chart ]       Jul 2026
 ┌───────────────────────────────────────────────────────────────────────────────┐
 │ THE STATE   speed  ...                          (§16, unchanged)              │
 └───────────────────────────────────────────────────────────────────────────────┘
                             Size   of cut  of book   Growth   Pace   Run     New ₹
 ────────────────────────────────────────────────────────────────────────────────────
 ▓ SERVICES                 ₹61.97L   100%    28.2%    22.9%  +1.52  ▃▄▅▆▇█      —
 ────────────────────────────────────────────────────────────────────────────────────
   NBFCs                    ₹21.28L  34.3%     9.6%    35.7%  +3.42  ▂▃▅▆▇█    48.3%
   Trade                    ₹14.09L  22.7%     6.4%    19.8%  +1.29  ▃▄▅▆▇█    20.2%
   ...                                             sort by 【size】 growth  new money
 ────────────────────────────────────────────────────────────────────────────────────
```

- **Parent row** is pinned at the top, visually separated, and never sorts.
- **Default sort is size** — the reader's mental model is "biggest first", and a growth-sorted
  table leads with the smallest book on the page.
- **Run** is a sparkline in the table; the actual readings appear when a row opens. Eight numbers
  across ten rows is a spreadsheet; eight numbers in one opened row is the argument.
- **Payments** reaches its tables through a measure strip (a group has many measures over the same
  entities; a credit cut has one measure over a hierarchy). Same table either way.
- `[Numbers] [Chart]` defaults to **Numbers**. The chart is NOT removed: §15's card-chart cut
  contract is what makes the chart under a card answer that card's question, and deleting it from
  read mode would discard that. The table leads; the chart is one click away.

### 17.5 Gate

A new stage validates every `display` string in the table against the row's declared
`source_signals`, scoped to that cut at that period — the §15.2 scoping rule, never period-wide.
The sidecar is freshness-guarded with `--check` like every other derived artifact.

### 17.6 Not in this build

No Layer 2 in the table — no forces, no gaps, no divergence flags. Layer 1 first, deliberately.
Row expansion shows the readings and nothing else. §16's band above the table is the only L2 on
the surface, and it was already there.

---

## 18. Which cards still earn a place (2026-09-13)

Once §17's table exists, most cards are a table row written out as a sentence. Measured over
the 96 live SIBC cards, by whether the card's entity is a row in some table:

| plane | cards | what it says | does the table say it? |
|---|---|---|---|
| **subject** | 50 | *"Large corporates at 67.3% — down 0.18pp"* | **Yes** — that is a cell |
| **read** | 29 | *"Services at 22.94% YoY — fastest in 11 periods"* | **No** |
| **composition** | 17 | 9 share rows · 8 FY step-ups | **Partly** |
| **gap** | 6 | *"RBI does not break this down"* | **No** — not a number |

### The decision: the SUBJECT plane stops rendering in read mode

A sentence is a worse way to read a cell than a cell is. Fifty cards go; the rail drops from
96 to 46.

**The reads stay, and that is the load-bearing half of this decision.** *"Highest on record"*,
*"fastest in 11 periods"*, *"first growth in 11 periods"* are judgements about the SERIES, not
values at a period — `is_news`, which the table structurally cannot express. The card is the
right unit for news; the table is the right unit for state. Dropping the reads would leave a
dashboard that says what is true and never what is new.

**Gaps and FY cards stay** for the same reason in a different form: a gap is not a number, and
an FY step-up compares two years where the table's Run column compares months. Neither has a
column to live in.

### Rules

- **Display only.** Every card is still generated, gated, traced and shipped. This hides them
  from one surface; it deletes nothing and is reversed by a constant.
- **Explore is untouched and keeps everything.** Explore's purpose IS the full inventory —
  curating it would leave no surface where every card is reachable.
- **The dimension badge counts what is SHOWN.** A tile reading "27 insights" over a rail of
  nine is a tile that lies.
- **Hidden is not gone.** The plane is a rendering decision; if a future reader needs the
  subject prose, the constant is one line.

---

## 19. A row opens into its own table (2026-09-13)

### The defect this fixes, and how it was made

Fourteen SIBC cut tables are computed, gated and shipped. **Seven rendered nowhere** — trade,
NBFC sub-types, basic metals, engineering, food processing, textiles, chemicals.

The cause is this session's own recurring failure, committed an hour after fixing the last
instance of it: `SIBC_CUTS` in the credit adapter is a **hand-written map**, while the payments
adapter **derives** its list from `SECTION_DEFS`. One pipeline enumerates, the other declares
from memory — and the declared one silently omitted seven cuts added that same hour.

### Where a sub-cut belongs

Not as a dimension. Checked against the data: **every sub-cut's parent is already a row in a
parent table.**

    sibc-basic-metal-sub  -> code 2.13 -> "Basic Metal and Metal Product" -> a row in industry-by-type
    sibc-nbfc-sub         -> code 3.9  -> "Non-Banking Financial Companies" -> a row in services

So a row **opens into its own table**. That is the hierarchy the data already has, and it is
how a reader drills in: *Basic Metal is 11.2% of industry — open it — Iron and Steel is 69% of
basic metals.*

**It also answers §15's founding defect.** The card that started that work said *"Iron and Steel
holds 69.0% of basic-metals credit"* above a chart reading *"Basic Metal — 11.2% of industry"*:
two correct artifacts answering different questions. The row expansion puts both on screen, one
inside the other, with the relationship visible rather than implied.

### Rules

- **The join is computed in Python, never in the browser.** A row carries `sub_cut: "<stem>"`
  when one exists; the browser looks it up. Resolving code -> CSV name -> row entity client-side
  would be a second implementation of a mapping the compute layer already knows.
- **One level.** RBI publishes no fourth, and `buildSubCuts` already makes the same assumption.
- **Reachability is TESTED, not trusted.** Every computed table must be reachable — as a
  dimension's cut or as a row's sub-cut. That test is the thing that would have caught the seven,
  and hand-maintained lists are exactly what it exists to police.

---

## 20. One table per dimension (v1.0 — approved 2026-09-13, BUILT) ⭐

> ASCII approved in session before any code, per the CLAUDE.md authoring rule.

### The problem with §17 as shipped

**The table repeated.** Select any card in a dimension's rail and the detail pane redrew the same
table with different prose beside it. The table was the constant and the cards the variable, and
the layout had that backwards. Payments was worse: a group is many measures over the same
entities, so §17 stacked six to eleven tables in one pane.

### What the data affords, and it decided the design

**Every cell is the latest reading of a stored series.** Verified in the store, not assumed — and
the verification changed the design: **a column's depth is its own.** Payments carries 31 readings
of a level and 19 of its YoY, because a year-on-year rate cannot exist until a year has passed.

So a cell opens its own chart, the `Run` column disappears (it was one series printed as text),
and the `[Numbers]/[Chart]` toggle is subsumed.

### SIBC — one table, insights below, chart in a side panel

```
 ▎🏭 INDUSTRY BY SIZE                                                    Jul 2026
 ┌ speed  Industry credit growing 20.0% YoY, accelerating.                      ┐
 │ mix    Drifting toward Medium — took 14.0% of the growth while holding       │
 │        9.2% of the total a year ago. Away from Large.                        │
 └──────────────────────────────────────────────────────────────────────────────┘
  PART                 SIZE   OF CUT  OF BOOK  GROWTH   PACE      NEW
 ───────────────────────────────────────────────────────────────────────
  Industry          ₹48.01L     100%    21.7%   20.0%  +0.71        —
 ───────────────────────────────────────────────────────────────────────
  Large             ₹32.29L    67.3%    14.6%   17.7%  +1.10     60.8%
  Micro and Small   ₹10.92L    22.8%     4.9%   22.6%  −0.48     25.2%
  Medium             ₹4.80L    10.0%     2.2%   30.5%  +0.21     14.0%
 ───────────────────────────────────────────────────────────────────────
  every cell opens its own chart · 11 periods behind each

 ─ WHAT'S NOTABLE · 5 ──────────────────────────────────────────────────
  ▲ Large corporate credit at 17.7% YoY — highest on record
  ▲ Large took 60.8% of all new industry credit in the past year
  ○ Micro & Small grew 8.9% in FY25, 32.7% in FY26 — 23.8pp step-up
```

The worked example is the argument: the band says the mix drifts toward **Medium** while the row
beneath shows **Large taking 60.8% of the new money against 67.3% of the book**. Both true, and a
reader can now see why — in one grid, with no card explaining it.

A nested dimension (Industry by Type) keeps §19's row expansion: `▸ Basic Metal 11.2% of industry`
opens into `Iron and Steel 69.1% of basic metals`, with the nest footer naming the denominator. A
dimension carrying two state cuts (industry-type + infra-sub) shows both bands and one table; the
second cut is reached by expanding its row, where the parent's 31.5% stays on screen beside it.

### The side panel — click any number

Slides over the right third (a bottom sheet under `lg`); the table stays visible and the clicked
cell stays lit. It draws the column's **whole stored history**, prints the readings as rendered in
Python, says how many and from when, and offers `compare` over siblings **in the same cut and the
same column** — the one overlay where units and depth match, and the one thing a table cannot do.

The line is `linear` with a dot per reading, never a spline: SIBC's period set has a gap in it
(eleven ingested periods, not eleven consecutive months), and a smoothed curve would draw a
confident shape across months nobody measured.

### Payments — the measure is a FILTER, not another table

```
  measure  【Cards outstanding】 POS  eCommerce  ATM withdrawals  Other
  showing  ● value  ○ volume
  PART                    SIZE   OF CUT  GROWTH   PACE     NEW
  Credit Cards        12.29 cr     100%    9.9%  +0.09       —
  Private Sector       8.69 cr    70.7%    9.8%  +0.09    70.3%
  ...
```

`of book` is **absent**, not dashed: a payments cut's parent IS its root, so the question has no
answer rather than a missing one. Columns are declared per cut for that reason.

The state band stays pinned to the group's anchor cut while the filter moves. That is unambiguous
only because §16's sentences name their own subject — *"Credit cards in force growing 9.9%"*
cannot be misread as describing the e-commerce table beneath it.

### The three states (user, 2026-09-13) — the navigation this settles

```
   A  every dimension as a tile, each carrying up to three of its OWN reads
   B  click a tile   — the tiles compress into a 300px rail, the dimension opens beside it
   C  click a row    — the rail collapses to ☰ and the chart takes the width it gave up
```

**Each close pops exactly one level**: ✕ on the chart returns to B with the rail restored, ✕ on
the dimension returns to A, and Esc does the same. ☰ slides the rail back over as an overlay so a
reader can change dimension without giving up the chart they opened.

**The chart is a COLUMN, not an overlay.** It occupies exactly the width the rail released, so
nothing is hidden behind it and the table it was opened from stays readable. That is the one
structural difference from the first cut of §20, where the panel slid over the table's right edge.

**A row click and a number click are the same gesture**, landing on different tabs: the six columns
are tabs inside the panel, and a row opens on `growth` — what a reader is asking when they click a
sector, since the size is already on the line in front of them.

**The rail is the dimension switcher, so the chip strip is deleted.** Two switchers for one nav was
the §14.8 (archived read-mode record) mistake, re-made.

**The tile carries up to three reads and no more.** A dimension with one shows one and says so: a
padded tile and a quiet month look identical otherwise, and Services being quiet IS the news in a
month when its mix is the one being steered hardest.

### A dimension with no table says why

Bank Credit owns no cut — it IS the top level, and its only split is food vs non-food, an accounting
line rather than a mix anyone steers. So its pane shows the state band, a declared `noTableNote`,
and **the series itself**; the sectors are one level down in Main Sectors. The note is deliberately
NOT a restatement of the band's own no-mix sentence directly above it.

### The pane rule (user, 2026-09-14) — three panes, never more than two at once

```
   A  dimensions            every dimension as a tile, each carrying its own news
   B  dimensions + table    the tiles compress into a rail; the TABLE is the child
   C  table + chart         the table compresses into a row list; the CHART is the child
```

**The child always takes the larger share, and the parent compresses into a list of its own
children.** That is the one compression that loses nothing the reader was using: what a parent
pane is FOR at that moment is changing their mind about which child they wanted. In C the left
pane is the table's rows with the value of the column being charted, so picking another row is
one click and the chart follows.

**There is no hamburger, because there is no third pane.** The first cut of §20 left the rail
reachable in state C behind a ☰ that opened it over the page — a third pane wearing a menu. One
control goes up, because there is only ever one level above.

**Mobile is the same stack with one pane at a time**: A stacks the tiles, B is the table with a
back link, C is the chart with a back link. The compressed parent list renders only at `lg`.

### Chrome removed (user, 2026-09-14): the ✕ is the navigation

The back links (`‹ Credit dashboard`, `‹ Industry by Size`, `‹ all dimensions`) are gone. Every
pane already carries a **✕**, each close pops exactly one level, and two controls doing one job
made the second one look like it did something else.

**The Brief / Full / Deep ladder is gone too.** The notable list expands on click and the deeper
reading has its own disclosure, so two of its three rungs controlled something a click already
controlled — a three-way switch for one real choice spends the reader's attention explaining
itself. The Deep rung survives as what it always was: **`▸ The deeper reading ⌁`** at the foot of
the dimension pane, rendered only where one exists, which keeps the L1 → L2/L3 seam intact.

### `break out by bank` (§20, built 2026-09-14)

A payments measure with bank-level signals gains a **level** toggle: the same table over the 63
reporting banks instead of the 5 bank categories. **A different LEVEL of one table, not a
drilldown into a row** — the banks are not children of the categories on screen, they are what
those categories are made of.

- Discovered by METHOD and METRIC, never by name: `cc-bank-scan` does not follow the stem
  convention and never will, and matching on a spelling is what hid three payments tables.
- A bank breakout carries **Size · of cut · Growth and nothing else** — it has no 12-month
  allocation window and no acceleration, and six columns of dashes would claim otherwise.
- Its parent row is the metric's own published total, from the SAME signal the category
  table's parent row reads.
- **All 26 measures carry one** (completed 2026-09-14): 69 registry entries over the 23
  measures that had none, 151,448 payments rows in the store.
- **A breakout ships as its own file** and is fetched when the reader opens it. Twenty-six of
  them inline is an 8 MB artifact every visitor downloads to look at one; the sidecar carries
  an INDEX (`_banks`: metric → cut, parts, file) so the toggle knows a breakout exists before
  anything is fetched, and the page pulls only the one that was asked for. `stamp_table`
  deletes a breakout file that stops being computed — a stale file would answer a fetch with
  last month's table and nothing would say so.

### Decisions (user, 2026-09-13)

1. **SIBC nests; payments filters.** A real inconsistency, accepted deliberately: one pipeline is
   one measure over a hierarchy, the other many measures over one entity set. The expansion shows
   parent and child together, which is what made the Iron-and-Steel case land.
2. **Insights below the table**, full width.
3. **The side panel does NOT retire Explore. Explore never goes away** — it is the surface where
   every card and every series stays reachable.
4. **Sorting is click-the-header**, decided now rather than deferred: `sort` already existed on
   every cell for exactly this. Default size descending; the parent row is pinned and never
   sorts; `—` sinks in both directions, so a column the data cannot fill never leads the table.
5. **`of book` on the parent row is COMPUTED**, not joined by eye — the share scan now stores the
   cut's own share of the book, numerator = the parent's own published row.

### What survived the refactor

- Numbers rendered in Python, shipped as strings — including **every point of every chart**, since
  the panel quotes its readings. A browser formatting those would be the second formatter this
  project keeps paying for.
- Gate 5.9c/5.9d, **tightened**: scope is now per COLUMN (the cut-wide pool let a growth cell trace
  to a share), and the chart behind a cell is checked like the cell.
- The pairing rule stays structural — a share of new money in the same row as its speed.

### The defect this build found: three payments ANCHOR tables reached no surface

Widening the reachability test from SIBC to both pipelines found it immediately. Payments
reconstructed each cut's stem from its metric's name (`credit_cards` → `credit-cards-category`),
which is right for 23 of 26 cuts and wrong for `credit_cards`, `debit_cards` and `pos_terminals` —
**every group's anchor**: the two card fleets and the POS fleet, computed, gated, shipped, rendered
nowhere. The sidecar now DECLARES the metric each payments cut measures and the adapter matches on
it; the test checks both pipelines.

The test that exists to police hand-maintained lists had itself been scoped to one pipeline. Third
instance of [[feedback_check_population]] in three days.

### Still open

- **Bank rows** (option B: 6 registry entries + one share method, ~34s) fold into a `break out by
  bank` filter — unbuilt.
- **SIBC history is 11 readings** where the consolidated CSV holds 24 dates: signals exist only for
  ingested PERIODS. Deeper charts are a signals backfill, not a render change — a data job with its
  own gate run, deliberately not folded into a UI refactor.

---

## 21. The real economy beside the credit (v0.2, specced 2026-09-26, NOT BUILT)

> Status: **specced, not built.** v0.1's layouts were shown and approved on 2026-09-26. v0.2
> takes in the same day's reviews (population, absence, plausibility): output over a trailing
> year, Personal Loans without an Output, notes on the approximate aggregates, and real gate work
> in place of "no new stage". Both layouts need a final look before code. Data: signals/README §1f
> + MoSPI; join: COMPOSITION_SPEC §24.

### 21.1 What it answers

"Industry credit grew 20%": fast compared with what? The table answers the credit half and is
silent on the economy it finances. Two columns put the other half beside it:
- **Real credit**: loans outstanding, year on year, net of that part's own prices. Nominal growth
  partly measures inflation, and the inflation differs by sector.
- **Output (12 mo)**: growth of the activity that credit finances, over the last year. It is a
  trailing year and not a single month, because single-month output swings 4–7 pp from one month
  to the next and would drown the comparison.

No "gap" column: it would be a third derived number to ground, and the reader can already see it.

### 21.2 Layout: industry by type (monthly)

```
 INDUSTRY BY TYPE · Jul 2026                                      ┌─ VS THE REAL ECONOMY ──┐
 PART                         SIZE  OF CUT OF BOOK GROWTH   PACE   NEW │ REAL CREDIT OUTPUT 12M │
 ─────────────────────────────────────────────────────────────────────┼────────────────────────┤
 Industry ⓘ             ₹48.01L Cr      —  21.7%  20.0%      —     — │   x.x% ·Q1   x.x% ·Q1  │
 ▸ Infrastructure       ₹15.13L Cr  31.5%   6.9%  10.2% -0.66pp 17.6% │     —          —       │
 ▸ Basic Metal & Metal   ₹5.38L Cr  11.2%   2.4%  21.9% +1.03pp 12.1% │     —        x.x%      │
   Other Industries      ₹3.89L Cr   8.1%   1.8%  32.3% +3.09pp 11.9% │     —          —       │
 ▸ Food Processing       ₹2.65L Cr   5.5%   1.2%  22.3% +2.75pp  6.0% │   x.x%       x.x%      │
   Petroleum, Coal …     ₹2.12L Cr   4.4%   1.0%  34.0% -14.5pp  6.7% │   x.x%       x.x%      │
   Construction          ₹1.94L Cr   4.0%   0.9%  24.4% +5.15pp  4.8% │     —          —       │
   Cement               ₹69,420 Cr   1.4%   0.3%  16.3% -0.11pp  1.2% │   x.x%         —       │
   …
 ─────────────────────────────────────────────────────────────────────┴────────────────────────
 Real credit = loans outstanding, year on year, net of the industry's own wholesale prices (WPI);
 the Industry row uses the national-accounts deflator. Output = IIP production over the last 12 months.
 Output: 12 of 19 types · 45% of industry credit. Real credit: 9 of 19 · 19%. Hover a — for why.
```

### 21.3 Layout: main sectors (quarterly)

```
 MAIN SECTORS · Jul 2026                                          ┌─ VS THE REAL ECONOMY ──┐
 PART                SIZE    OF CUT  OF BOOK  GROWTH    PACE   NEW │ REAL CREDIT OUTPUT 12M │
 ─────────────────────────────────────────────────────────────────┼────────────────────────┤
 Non-food credit ⓘ  ₹219.60L Cr   —    99.5%     …        —      — │   x.x% ·Q1   x.x% ·Q1  │
 ▸ Personal Loans  ₹71.83L Cr    …      …        …        …      … │   x.x% ·Q1     —       │
 ▸ Services ⓘ      ₹61.97L Cr    …      …        …        …      … │   x.x% ·Q1   x.x% ·Q1  │
 ▸ Industry ⓘ      ₹48.01L Cr    …      …      20.0%      …      … │   x.x% ·Q1   x.x% ·Q1  │
   Agriculture     ₹27.07L Cr    …      …        …        …      … │   x.x% ·Q1   x.x% ·Q1  │
 ─────────────────────────────────────────────────────────────────┴────────────────────────
 Real credit = loans outstanding, year on year, net of the sector's own prices (national-accounts
 deflator). Output = real GVA over the last 4 quarters; for the total, real GDP. Personal loans have
 no output measure: half is housing, which is investment, not consumption.
 ·Q1 = Apr–Jun 2026; credit is read at Jun, the quarter's end. Jul–Sep has no cell until SIBC's
 Aug–Nov history is backfilled. ⓘ = an approximate match; hover for what it includes.
```

The total row is keyed to one entity, **Non-food credit (III)**, for every cell. The live table
mixed the four sectors' sum (size) with III's share and growth; that is fixed separately (§21.7).

Sub-tables: Power, Electronics and Pharma rows get both cells. Iron & steel, Fertiliser, Sugar and
Edible oils get Real credit only. The Personal Loans sub-table's rows get Real credit from CPI
(monthly), and its total row repeats the main table's quarterly value (`·Q1`): same entity, same
number. Every other sub-row shows two dashes, each with its reason.

### 21.4 The rules the layout carries

- **One column = one signal = one cadence.** Construction's output is quarterly, so it is a dash
  on this monthly table and a value under Industry on the main one. A total row is a different
  signal (the parent cut's), so it carries its own period label (`·Q1`).
- **A cell never shows an older period than its row's.** No carry-forward. A cell whose data is not
  yet due shows `—` with `not_released`; one that is overdue fails the gate before anything ships.
- **An absent cell ships a reason code, and the sentence is rendered in Python from that code**:
  `{display: "—", reason: "shared_group", note: "IIP pools cement with glass"}`. Shown on hover
  or tap; never 0 and never blank (§17.3).
- **ⓘ marks an approximate aggregate** (COMPOSITION_SPEC §24.1). Its note carries a share computed
  that period ("9.6% of industry credit is infrastructure NAS counts as services").
- **The coverage line counts cells that have a value this period**, rows AND credit, and says how
  many are waiting on MoSPI ("2 awaiting the Aug IIP, due ~28 Sep"). It never counts what the
  concordance maps.
- **Same entity, same number**: Industry and Personal Loans are identical wherever they appear.
- The group header renders only on a cut that declares 1f columns. Other tables are unchanged.
- **A cell opens its own history**, like every column (§20).
- Phone: the table keeps its sideways scroll (min-width 520 px); it is two columns wider.

### 21.5 Gate: new work, not "no new stage"

v0.1 claimed the §17.5 stage covers the new columns unchanged. The population review showed it
cannot:
- **the column list is typed in three places** (`core/table_rows.py`, `guards/validate_cut_table.py`,
  `web/lib/table.ts`) with nothing keeping them in step. It becomes **one declaration** that the
  builder, the gate and a generated TS constant all read. Otherwise the gate never reads a new
  column;
- **each cell is checked at its own declared period**, not the table's (`·Q1` cells), and never by
  widening the scope for the whole table;
- **absent cells**: the reason code must be in the closed list, and the cell may carry no value;
- **the coverage line** is checked against the cells it counts;
- **operands**: Check 2f recomputes each 1f row from the two CSVs, including its operands and
  reason. A new check asserts that each row's series codes are the ones the concordance names for
  that part. v0.1 cited Check 2g here, but 2g reads annotation prose, not table cells.

### 21.6 Not in this build

Credit intensity (credit ÷ annualised GVA), the services sub-rows (quarterly NAS pools them),
annual NAS, any card or state-band sentence built from these columns. Layer 1 columns first.

### 21.7 Found while speccing: the main table's pinned row

The pinned row of `sibc-main` rendered **size = the four sectors' sum (₹208.88L Cr)** beside
**of book 99.5% and growth, which belong to Non-food credit (₹219.60L Cr)**. A part cannot be
99.5% of a book it is 94.6% of. **Fixed 2026-09-26**, independently of MoSPI: the size scan stores
the parent's own row (`aggregate`/`parent`), the pinned row reads it, and the gate checks each
pinned cell against the row it declares. Six pinned rows were wrong, on SIBC and NBFC.
