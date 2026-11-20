# Bank-wise credit pipeline (`rbi_bankwise`): specification

> v0.2, 2026-11-14. Status: **phases 1–3 built**; **backfill complete**: all 46 quarters from Mar 2015 saved. Onboarded through the `onboard-source` skill.
> v0.2 folds in the three reviewers (population, absence, plausibility; 21 findings, all verified;
> table at the end). Probe: `analysis/sources/README.md` §"Per-bank quarterly variables" (opened
> 2026-10-11, probed 2026-11-14).

## 1. Why

The user's goal (2026-11-14): **as deep a view as possible of each bank's credit, from official
RBI records only.** Bank-specific investor documents are separate work and out of scope.
Later, this becomes a bank-level view on the SIBC page, the way payments has one (a
`/dashboard-change`, ASCII first; not part of this spec).

Decision filter: per-bank credit mix, growth and asset quality is what CPOs, CROs and PE/VC
analysts ask about first, and nobody publishes it as a clean, standardised series even though RBI
does. It reuses our bank pages, scorecards and the private-bank card format.

## 2. What official RBI records exist per bank (survey, 2026-11-14)

| Record | Where | Cadence · from | Per bank? | Use here |
|---|---|---|---|---|
| **Variables to be published Bank and Bank Group wise (For Public Access)** | DBIE › Banking – Performance Indicators | quarterly · Mar 2002 → Jun 2026 | **yes, every SCB** | **the core of this pipeline** |
| Bank-wise 1-year MCLR | sheet "Bank wise 1 Year MCLR" in RBI's monthly rates file (`rbi_rates` raw workbooks, already downloaded) | monthly | yes | phase 4: each bank's price of credit beside its book |
| Card and payment metrics | RBI ATM/POS/card statistics (`atm_pos`) | monthly | yes | already a pipeline; joined by bank identity (§6) |
| Bank-wise GNPA, gross advances, GNPA ratio | DBIE, annual, 2004 → 2026 | annual | yes | subset of the quarterly table; not needed |
| BSR-1 (occupation, district, rate band) | DBIE / rbi.org.in | annual / quarterly | **bank group only** | no |
| Sectoral deployment (SIBC) | RBI monthly | monthly | **system only** | the system total these banks are compared with |

Nothing else official splits credit by bank. Gold loans, NBFC lending and industry below its
total exist per bank only in banks' own disclosures (out of scope).

## 3. What one export contains

DBIE cannot be scripted (an Angular app over SAP BusinessObjects; `sources/README` access table).
The editor's Chrome runs the report: prompts **Reporting Period** (multi-select quarters), **Bank
Name** (ALL REPORTING ENTITIES), **Unit** (CRORES) → Run → Export → Excel → All reports. One
workbook, eight sheets, the same layout on each: a title row, two header rows (measure, then
Domestic / Overseas / Global Operation), then rows of `period | bank | values`, the period written
only on the first row of each quarter's block. Header text is irregular (double spaces: "Services 
- Gross NPAs"; "Other Retail Loans" without the "Retail Loans - " prefix).

| Sheet | Measures (₹ crore unless a ratio) | Operations |
|---|---|---|
| Major Balance Sheet Items | cash, due from banks, SLR and non-SLR investments, **net loans and advances**, fixed and other assets, total assets, capital, reserves, **deposits**, borrowings | domestic / overseas / global |
| Capital Adequacy | Tier I, CET1, Tier II, total capital, RWAs (credit, market, operational), CRAR | domestic / global |
| Asset Quality | **gross advances**, gross NPAs (sub-standard, doubtful, loss), GNPA ratio, provisions, net NPAs, … | domestic / overseas / global |
| Profitability (April-to-date, cumulative) | interest income, interest expense, NII, other operating income, operating expenses, provisions, profit | domestic / overseas / global |
| Performance Indicators (annualised ratios) | **cost of funds, yield on funds**, cost-income, profit margin, **NIM**, ROE, ROA, … | domestic / overseas / global |
| **Major Sectoral** | gross advances, GNPAs and GNPA ratio for: food, non-food, **agriculture, industry, services, retail, other non-food**; retail split into **housing, vehicle/auto, credit card receivables, education, other retail** | domestic only |
| Priority / Non-priority | gross advances, GNPAs, ratio: priority sector and its parts, non-priority | domestic only |
| Infrastructure Financing Items | ~60 lines: transport (roads, ports, airports, railways…), energy (generation, transmission, distribution, by Central / State PSU / private), water and sanitation, communication, social and commercial | not stated (one value) |

**Rows (measured, Jun 2026):** 89 banks (Public 12, Private 21, Foreign 43, Small Finance 11, Local
Area 2; Sep 2024 and Jun 2025: 90) and **six group rows**: Public Sector Banks, Private Sector Banks,
Foreign Bank Group, Small Finance Bank Group-scheduled, Local Area Bank Group, All Scheduled
Commercial Banks. Each group row closes the block of its banks.
**All SCBs = Public + Private + Foreign + Small Finance, exactly; the Local Area Bank group is
outside it** (the five groups exceed All SCBs by exactly the LAB row in all three probed quarters).
Earlier eras have other groups (SBI and associates, nationalised, old and new private); the group
set is read from the layout each quarter, never from a list (§5.1). Source line on each sheet:
"Offsite returns (OSMOS) collected at Department of Banking Supervision, RBI".

## 4. Cadence, lag, saving and revisions

- **Cadence of the values:** quarterly (quarter-end stock), except Profitability (financial-year-to-
  date flows) and Performance Indicators (annualised ratios RBI computes; stored as published,
  never re-derived). A quarter's own flow = this quarter's cumulative minus the previous quarter's
  **in the same financial year**; the Q1 (June) flow is the cumulative itself; a missing earlier
  reading makes the flow absent (`prior_cumulative_missing`), never cumulative − 0.
- **Release lag:** Jun 2026 was available on 14 Nov 2026 (137 days). Until two clean cycles are
  measured, a **declared lag ceiling of 165 days** defines the latest quarter that must be saved;
  the calendar check later only tightens it.
- **A release is keyed by quarter, not by publication date** (DBIE has none). Saving reports every
  quarter in the export as **new / unchanged / revised**, and fails:
  - when a current-period export holds **no quarter newer than the latest saved** (stale prompts, or
    the quarter not yet on DBIE), unless `--no-new-quarter-expected` is passed;
  - when a re-read quarter differs as a set: rows **added, removed or changed** are each listed and
    the quarter is raised for a decision, never overwritten (the `rbi_rates` principle; its
    publication-date ordering does not apply, so backfill saves in any order).
- **Revision coverage is reported, not assumed:** each save prints "revisions checked: k saved
  quarters re-read, j changed"; k = 0 reads "not checked", never "no revisions". A current-period
  export must re-read the latest 8 saved quarters or the save fails. The gate lists quarters read
  only once.
- **Bank perimeter changes** (mergers, conversions, new SFBs, exits) are real. Seen in three
  quarters: North East SFB leaves and Slice SFB arrives (Sep 2024 → Jun 2025); Rabobank leaves by Jun
  2026. Every bank added or removed against the previous quarter is listed by name (§6).

## 5. The gate

Every check states the set it iterates and where that set comes from; the set never comes from the
export it checks.

**Declared populations (manifest):** the eight sheets with their **ordered, exact header lists**
(whitespace-normalised); the quarter range from the decided history start (open decision 2) to the
latest quarter older than the lag ceiling; the unit CRORES; the time-aware bank roster (§6).

0. **Shape:** all eight sheets present; each sheet's headers equal its declared list in order, in
   both directions (a missing, extra or moved column fails); unit read from the sheet and equal to
   CRORES; every quarter in the declared range saved.
1. **Banks sum to their group row**, for every group row the layout shows (a row that closes a block
   is a group; never matched by name: "AUSTRALIA AND NEW ZEALAND BANKING GROUP LIMITED" is a bank),
   per sheet, measure and quarter. Then **All SCBs = sum of its member groups** (today: Public +
   Private + Foreign + Small Finance). A group with no members, or a bank in no group, fails. The
   check prints how many groups it checked per quarter.
2. **Printed ratios recompute** (GNPA ratio = GNPAs / gross advances on Sectoral, Priority, Asset
   Quality; CRAR = capital / RWAs) exact to the printed decimals. **A null ratio is legitimate only
   when its denominator is exactly 0**; a null with a non-zero denominator, or a value with a zero
   denominator, fails.
3. **Domestic + overseas = global** where the sheet prints all three. An overseas or global null is
   legitimate only for a bank with no overseas operations (roster). Each sheet prints checked /
   skipped-by-rule / failed counts; a declared operation column that checked 0 rows fails.
4. **Identities within a row**, one per sheet that has them: food + non-food = gross; the five
   sectors = non-food; the five retail parts = retail; priority parts = priority; infrastructure
   subtotals = their parts; sub-standard + doubtful + loss = GNPAs; Tier I + Tier II = total capital;
   RWA parts = total RWA; NII = interest income − expense. Each identity has **one bound, measured
   once on the probe export and approved** (probe: parts within 0.0004 cr on every row); the bound
   is never rewritten by a later run. **Parts are ≥ 0** (probe: AmEx "Other Retail Loans" is
   −0.00005 cr: a declared tolerance, not a free pass).
5. **Banks on every sheet:** in a quarter, all eight sheets carry the same bank set, and it equals
   the roster's banks valid on that date.
6. **A bank row of all zeros is `not_reported`, not a zero book**, when another sheet shows the
   same bank with a book that quarter (probe: FirstRand, JSC VTB, NatWest Markets, Rabobank carry
   all-zero sectoral rows). A bank going from a book to all zeros is reported like a bank leaving.
7. **Scale guard (a units mistake, not a definition check):** All SCBs gross advances within a wide
   band of the previous saved quarter and of SIBC's non-food credit.
8. **Reconciliation with SIBC, reported, not gated:** All SCBs vs SIBC per sector. Probe, Jun 2026,
   DBIE / SIBC: within ±3.4% except **housing 0.92** (SIBC includes priority-sector housing) and
   **food credit 1.10** (small, volatile base). Growth differs more than levels (industry YoY 15.9%
   vs 19.2%), so the two are never mixed.

**Before any check gates:** measured by injection over its whole population with a known-good
control (DECISIONS), using at least: a shifted cell, a dropped bank, a swapped quarter, **a
mislabelled column, an unlisted group row, a missing first and a missing last quarter, a nulled
operation column, the unit set to lakhs, a partial bank selection, a stale re-export.**

## 6. Bank identity: one roster for every pipeline

DBIE and payments name banks differently (51 of 89 DBIE banks match the payments roster after
normalising; most of the rest are foreign banks payments does not cover). A per-bank view on the
SIBC page and a joined bank page need **one identity**.

- `analysis/ontology/banks.json`: `bank_id` (stable slug), canonical name, and **per source**
  either an alias with validity dates (renames, mergers: HDFC Ltd into HDFC Bank, Jul 2023;
  whitespace changes such as "KRISHNA  BHIMA  SAMRUDDHI   LAB LTD.") **or `not_in_source` with a
  reason**. A bank with neither fails the join, so "payments does not cover this bank" is never
  confused with "alias missing". An alias used outside its dates fails.
- **No group field in the roster.** A bank's group on a date is the block RBI printed it in;
  payments' categories map to DBIE groups through an explicit, checked crosswalk.
- `atm_pos/canonical_banks.json` moves onto it (one source of truth); both pipelines read names
  through it, and an unknown name **fails** the read.

## 7. What it does not measure

- Below its splits: no gold loans, NBFC lending, MSME by size, or industry by type per bank.
- Overseas/global is not available on the sectoral, priority and infrastructure sheets.
- It is **all SCBs**, quarter-end; SIBC is select banks, fortnight dates. Bank figures are compared
  with this table's own totals, never with SIBC's.

## 8. Build phases (each a commit)

| Phase | Scope | Done when |
|---|---|---|
| 0 | this spec; the three reviewers (done, v0.2); user approval | open decisions settled |
| 1 | manifest (`kind: primary`, surfaced in SIBC), shared bank roster, reader for the agreed sheets, releases saved per quarter as `json.gz` with the save rules of §4, consolidate to one tidy CSV | reader reproduces the probe export exactly; every failure in §5.0 raises |
| 2 | gate: §5.0–5.7, each measured by the injections above | gate green on the probe export, every injection caught |
| 3 | backfill to the decided start in Chrome (≈ 8 quarters per export, user OK per batch) | every quarter in the declared range saved; gate green |
| 4 | signals (below) and the bank-wise MCLR | freshness green; formulas pinned by worked examples |
| 5 | the SIBC page's bank view: ASCII with live numbers, approval, build | `/dashboard-change` done |

**Phase 4 signal rules** (decided here, before any number is published):
- **A sector's share of a bank** divides by the bank's **domestic gross advances** (food + non-food);
  worked example: SBI retail Jun 2026 = 41.69% (42.09% of non-food would be the other reading).
- **A bank's share of the system** divides by **All SCBs**, for banks inside it; Local Area Banks
  are outside All SCBs and get no system share (`outside_system_total`).
- **Growth never stands without its base** (pairing rule): every YoY carries the two levels. Tiny
  bases dominate a growth ranking (39 bank × sector pairs grew > 100% Jun 2025 → Jun 2026; Unity SFB
  cards 7.57 → 238.11 cr, +3,046%), so a **minimum-base rule is decided once for this pipeline and
  payments** (PLAN's open Bandhan +416,450% debt) before any growth ranking ships.
- **A zero denominator is an absence with a reason** (`no_book`, `not_reported`), never a vanished row.

## 8a. Phase 4 design: signals and model (user approved the layout and "primary with a model", 2026-11-17)

**Shape.** The local table is rewritten in the payments shape (`report_date, bank_name, bank_category,
record_type, metric, value, unit`) so the payments compute module (`signals/compute/atm_pos.py`,
already keyed by pipeline) serves both: one generic per-bank mechanism, not a second one.
`bank_name` is the roster id, `bank_category` the group RBI printed the bank under that quarter,
`record_type` is `bank` or `total` (the All SCBs row; the Local Area Bank group sits outside it).
Group values are sums of their banks, as in payments; RBI's own group rows stay in the releases and
are what the §5 checks compare against. `metric` = `{sheet}.{column}`, only for declared metrics.

**Declared metrics** (`pipelines/rbi_bankwise/signals.json`, the one list the registry is built
from): Major Sectoral gross advances; food; non-food; agriculture; industry; services; retail;
housing; vehicle; credit cards; education; other retail; and the gross NPA ratio. Infrastructure
lines and the other sheets follow once the view needs them.

**Signals per metric** (existing methods unless marked): each bank's size (`csv_bank_scan`), its share
of all banks (`csv_bank_scan_share`), its growth a year (`csv_bank_scan` yoy), its share of the
year's new money (`csv_bank_allocation`, a 12-month window = four quarters), the total's growth
(`csv_total_yoy`), and the group scans (size, share, growth). **New:** a sector's share of the bank's
own book (`csv_bank_ratio_scan`: metric ÷ the bank's gross advances, per bank).

**Merger breaks.** Declared once in `rbi_bankwise/series_breaks.json` (the shared series-break
mechanism, `core/series_breaks`; statement `bank`, code = bank id, group label or `total`): SBI and its associates (Apr 2017), Bank of Baroda with Dena and Vijaya (Apr 2019),
the April 2020 amalgamations (PNB, Canara, Union, Indian Bank), Kotak with ING Vysya (Apr 2015),
IDFC First (Dec 2018), DBS with Lakshmi Vilas (Nov 2020), HDFC Bank with HDFC Ltd (Jul 2023). Growth
and new-money share for the absorbing bank across a break are absent with reason `merger_break`;
size and shares stay. The bank-scan methods take the breaks as a parameter, so payments can use
the same mechanism later.

**Flags.** Cells in `inconsistencies.json` are honoured where cells are rendered (the table stamp,
phase 5): shown "—" with the reason, never as if they held.

**Model.** Primary, with a system model whose skeleton comes from an authored profile, like
payments: entities are the credit measures (gross advances → food / non-food → the four sectors and
other non-food → the five retail parts); banks and bank groups are a lens, not nodes, and the
per-bank signals attach to their measure's entity. The behavioural layer (sourced forces: the
mergers above, IDBI's recategorisation, recapitalisation) comes with the first FOUNDATION model pass
after the view ships.

**Timeline.** `analysis/rbi_bankwise/timeline.json` lists the saved quarters (written by
consolidate from the releases); it is the freshness check's population.

## 8b. Phase 5 gaps (user, 2026-11-17), all five built 2026-11-20 (DASHBOARD_SPEC §20 "as built")

Decided 2026-11-20 (user): a bank ranks by growth only off ≥ 0.25% of the total a year earlier, and pace
is a generic per-bank family for both pipelines (DECISIONS). One correction to gap 5 as written: a flag
touches growth and new money at its quarter and at the same quarter a year on (the two ends of a year's
comparison), and pace at each of those and the quarter after; not "four later". 48 bank flags on the 13
measures; none on Jun 2026. Built in `core/bank_tables.py`; the gate (`validate_cut_table`) reads every
book file and accepts a "—" only where `inconsistencies.json` lists it.

The original list:

The Banks view was built on the shared read-mode parts; these departures from the approved draft are open:
1. **Pace per bank** is not stored (`csv_bank_acceleration` does not exist; payments stores none either). The
   bank-group table has pace. Decide whether per-bank pace earns a signal family.
2. **A bank row opening into its own sector mix** ("SBI ▾ Agriculture · Industry · Services · Retail ▸ Housing …").
   Needs a per-bank table (parts = the bank's lines, columns from the of-book, size, share and growth scans at
   that bank) fetched on open, like the breakouts; the shell has no on-demand sub-cut today. Until then each
   sector's bank table carries "of book".
3. **Merger markers on the chart.** Growth across a declared merger is a gap in the line; the size line keeps the
   jump. A labelled marker ("Apr 2017: SBI absorbs its associates") needs `series_breaks.json` shipped with the
   table and drawn by the cell panel.
4. **Growth sorting is off on bank-wise by-bank tables** (declared in the sidecar, `unsortable`) until the
   minimum-base rule (PLAN, shared with payments) is decided. Extremes on Jun 2026: Sberbank +299% on ₹588 Cr;
   in cards, Unity SFB +3,047% on ₹238 Cr.
5. **Flagged cells** (48 on the 13 measures, none in Jun 2026) are not yet blanked in the history lines, nor do
   they carry their reason. Do it in the table stamp from `inconsistencies.json`: a flagged (quarter, bank,
   metric) nulls that point in size and shares, and growth/new at that quarter and four later.

## 9. Decisions (user, 2026-11-14: "use your proposals")

1. **All eight sheets** in phase 1: the whole record, read once.
2. **History from Mar 2015** (user, 2026-11-15; was Mar 2002 on 11-14): the SIBC history we hold does
   not reach further, and before Mar 2015 RBI's sector columns hold different content (below).
3. **Primary, surfaced inside the SIBC page**, no page of its own for now.
4. **One shared bank roster**; payments' roster moves onto it (a change to a live pipeline, in its
   own commit with the payments gate green).
5. **One minimum-base rule for growth rankings**, shared with payments, decided before any ranking
   ships (the value is still to be chosen; phase 4).

## Review, 2026-11-14 (v0.1 → v0.2)

Three reviewers, read-only, in parallel. Every finding verified against the probe export
(`review_dbie_sect.json`, 3 quarters) before folding in.

| Reviewer | Finding | Verdict | Where now |
|---|---|---|---|
| plausibility | All SCBs excludes the Local Area Bank group; group list wrong (missed Small Finance) | confirmed (Σ 4 groups − All SCBs = 0.00, LAB outside, 3 quarters) | §3, §5.1, phase 4 |
| plausibility | "92 banks" wrong: 89 (90 earlier) | confirmed (95 rows − 6 groups) | §3 |
| plausibility | growth on tiny bases, 0/0 shares, a negative part | confirmed | §5.4, phase 4 |
| plausibility | ±3.4% contradicted by food 1.10; share denominator undeclared | confirmed | §5.8, phase 4 |
| population | hand-written group list | confirmed | §5.1 |
| population | sums cannot see a mislabelled column | confirmed by construction | §5.0, §5.4 |
| population | quarter range read from the saved files | confirmed | §5 populations, §5.0 |
| population | bank set not checked across sheets or roster | confirmed | §5.5 |
| population | nulls skipped by 5.2/5.3 and uncounted | confirmed (nulls in sample) | §5.2, §5.3 |
| population, absence | residual set from the data it checks | confirmed | §5.4 |
| population | group stored twice | confirmed | §6 |
| population, absence | revision check sees only overlaps and changed rows | confirmed | §4 |
| absence | a stale export saves as "duplicate" | confirmed (rbi_rates pattern exits 0) | §4 |
| absence | wrong unit or partial bank selection passes §5 | confirmed by construction | §5.0, §5.7 |
| absence | null ratio vs zero denominator | confirmed | §5.2 |
| absence | all-zero bank rows read as no book | confirmed (11 rows in sample) | §5.6 |
| absence | cumulative profit read as a quarter's flow | confirmed by construction | §4 |
| absence | roster cannot tell "not covered" from "alias missing" | confirmed | §6 |

Nothing dropped as not reproducible; nothing by design.

## As built

**Phase 1a (2026-11-14): roster, reader, saved releases.**
- `analysis/ontology/banks.json` + `core/banks.py`: 98 banks, two sources (`rbi_bankwise`,
  `atm_pos`); 58 in both (6 paired by hand: Dhanlaxmi, J&K, Bank of America, Citibank, Deutsche,
  HSBC). Every bank answers for every source with names or `not_in_source` (6 payments banks: not
  in DBIE's table; 34 DBIE-only banks, mostly foreign and the 2 Local Area Banks: not in the card
  statistics). Names compare ignoring case, spacing and punctuation; dated aliases supported.
  North East SFB and slice SFB are kept separate until an RBI record links them. Payments does not
  read through it yet (its own commit, §9.4).
- `pipelines/rbi_bankwise/reader.py` + `sheets.json`: the declared shape (8 sheets, 339 columns in
  order, 7 group spellings) is written once from the probe (`--declare`) and every export is
  compared with it. Groups by layout (bold; ANZ "…BANKING GROUP LIMITED" is not bold). The probe
  reads as 89/90/90 banks with groups PSB 12, private 21, foreign 43–44, SFB 11, LAB 2, All SCBs
  (no members). 10,045 sectoral cells identical to an independent parse of the same file.
- `pipelines/rbi_bankwise/fetch.py`: one release per quarter, `analysis/rbi_bankwise/releases/
  {quarter}/{saved}.json.gz` (≈ 145 KB each; ≈ 10 MB for 2002 → 2026). NEW / UNCHANGED / REVISED,
  with the three refusals of §4. Loads its own `reader` by file (rbi_rates also has `reader` and
  `fetch`; a bare import took the wrong one in the full test run).
- `tests/test_rbi_bankwise.py`: 18 controls (mislabelled column, missing/extra sheet, lakhs, an
  undeclared bold row, a bank named like a group, an unknown bank, banks after the last group, an
  empty merged header, roster completeness, dated aliases, new/unchanged/stale, revision refused
  then accepted keeping the old, a removed bank, a new quarter without the re-read, a backfill).

**Found while building:**
- **RBI leaves some merged headers empty over columns with data**: Asset Quality's last three
  columns (after "21. Loans sold to ARCs") and Major Sectoral's last column hold numbers in Jun 2025
  only (e.g. Bank of Baroda ₹7,91,974 Cr in the sectoral one). Declared as `unlabelled_{n}`, kept,
  never published until identified. Forward-filling headers had named them after their neighbour.
- **The Infrastructure sheet prints no unit line** and spells All SCBs "Scheduled Commercial
  Banks", in title case ("Bank Of Baroda"). Declared; the unit is asserted on the other seven sheets.
- **A primary pipeline must have signals and a model** (`test_kind_and_capabilities_agree`). Until
  phase 4 this is honestly reference data.

**Phase 1b (2026-11-14): manifest, local table, gate.** User decision: commit the saved quarters
(the record, ~10 MB for the full history); rebuild the long table locally from them.
- `pipelines/rbi_bankwise/pipeline.json`: `kind: reference` until phase 4 (a primary pipeline must
  already store signals and have a model). Gate: consolidate → table equals a rebuild → tests →
  calendar (the currency stage) → reconcile.
- `consolidate.py`: releases → `analysis/rbi_bankwise/rbi_bankwise_consolidated.csv`, git-ignored,
  reference schema (dataset = sheet, code = bank or group, measure = column, status = bank/group);
  86,880 values for the 3 probe quarters. An empty store refuses rather than writing an empty table.
- `validate_calendar.py`: current when the newest saved quarter is at or past the latest quarter
  due under the 165-day ceiling; the declared history from Mar 2002 is counted and every missing
  quarter named (now 2 of 97 due; `history_required` turns the gap into a failure at phase 3).
- `core/explainability.py`: the register check now reads only the reference pipelines its
  hypotheses name, instead of every reference CSV (it would have read this table on every run).
- Not committed: the raw Excel exports (the saved quarters carry every cell, unlabelled ones too).

**Phase 2 (2026-11-14): checks against RBI's own totals** (`validate_bankwise.py`, gate stage 1c).
Population per check printed every run (3 quarters: 18 group rows × 257 amount columns; 287 rows ×
39 printed ratios × 61 identities; 269 bank-quarters × 8 sheets). Structure read from RBI's labels;
bounds measured once (max observed gaps: sums 8e-8 Cr, ratios 5e-7 pp; bounds 0.05 Cr / 0.001 pp).
**What the data taught the checks** (each measured, reasoned, never a looser bound):
- RBI prints a blank where every part is zero (a group row, a total) and a blank ratio where GNPAs
  are 0; both are allowed only in exactly that case.
- Domestic + overseas = global holds for **credit only** (Asset Quality): balance-sheet and profit
  items eliminate inter-office balances in the global figure.
- Parts ≥ 0 on the credit sheets only: reserves go negative with accumulated losses.
- **Small Finance and Local Area Banks never appear on the Capital Adequacy sheet.**
- 52 named exceptions: RBI's printed Net Operating Income is not its own "[5 − 6]" for HDFC, ICICI,
  IDBI and Yes Bank in every quarter (up to 12.5%); one blank ratio (Sonali, Sep 2024); global loans
  sold to ARCs printed as half the domestic figure (Karur Vysya, Sep 2024). Anything else fails.
- 5.6 found no all-zero credit rows with a book elsewhere in these quarters (the FirstRand/VTB/
  NatWest rows are zero on every sheet).
**Measured** (`ai_pm_register`): control 0 failures; caught 100% of +1% shifts (34,987 cells), adjacent
column swaps (40,543), dropped banks with a book (269), nulled ratios (6,048), a bank missing from one
sheet (2,113), lakhs (3/3), +0.01 pp on every ratio RBI's export carries a formula for (7,680).
Not checkable: 7,522 ratios RBI computes from data outside the export (performance indicators,
provision coverage). The first run found a bug in the check itself ("ratio" matched inside
"Generation" and "Operational") and it is pinned by a test. Not covered: a swapped quarter label
(caught only by a later re-export's revision diff); a partial bank selection whose group rows DBIE
recomputes.

**Phase 3, batch 1 (2026-11-14): Dec 2023 → Mar 2026.** One Chrome export (8 new quarters + Sep 2024
re-read, unchanged); 11 of 97 quarters saved. Roster: AB Bank and Sonali Bank under their pre-2024
names (dated aliases, to Mar 2024), Credit Suisse AG (last seen Mar 2024, not linked to UBS), Fincare
SFB (already in payments). `reader.py --unknown` lists every unknown name in an export at once.
- **Membership is per sheet**: NatWest Markets is on six sheets but not Capital Adequacy or
  Profitability in Mar 2024. Groups now record `members_by_sheet`; sums use each sheet's own block;
  §5.5 still names the absent bank. The probe quarters were re-saved in this format.
- **RBI's own figures disagree in isolated places (user decision: flag, don't fail).** Across
  354,249 cells, 150 failures, at most 2 banks in any column of a quarter (the Jun 2024 foreign group
  total exceeds its listed banks in 88 columns, cash funds by ₹391 Cr, likely a bank's book not
  printed after Credit Suisse leaves; NOI ≠ [5 − 6] also at Indian Overseas and Capital SFB). The
  gate now fails a check only when 10 or more banks break the same column in a quarter (5× the
  observed maximum: a reading error maps a column the same way for every bank); everything else is
  written to `analysis/rbi_bankwise/inconsistencies.json` (150 flags), which signals must honour.
  Shape, unit, headers and the scale guard still fail outright.
- **Measured** (11 quarters): control 0 column-wide failures; a single-cell disagreement is flagged
  6,336/6,336 and fails the gate 0 times; a column-wide swap fails the gate 2,055/2,293 (89.6%). The
  238 not caught by content sit in no sum or ratio (provisions, staff expenses, write-offs, sibling
  infrastructure lines); the exact-header check at read time is what catches those.

**Phase 3, batch 2 (2026-11-14): Dec 2021 → Sep 2023.** 8 new quarters (Jun and Sep 2024 re-read,
unchanged); 19 of 97 saved. Roster: HSBC's older spelling (dated), Abu Dhabi Commercial Bank, Krung
Thai Bank, RBS N.V. (not linked to NatWest Markets). What the older quarters taught the reader and
the checks, each found in the data and now encoded:
- **DBIE prints only the measures with data in the selected quarters.** Profitability had 42
  columns for 2024-26 and 51 for 2021-23 (13. Provisions for liabilities, 14. PBT, 15. Tax). An
  export's header must now be an ORDERED SUBSET of the declared layout (labels exact, order kept);
  a column the declaration lacks stops the read until `reader.py --declare-merge` inserts it at its
  printed position. Ids always come from the declaration.
- **A label can print blank in one export and in full in another**: Asset Quality's last three
  columns are "22. Loss or gain on loan sales (April to date)" (blank in the probe, labelled in batch
  2); declared with that label and `blank_ok_labels`. Their sums now run, and RBI's foreign-group
  total for them does not match its banks (flagged). Major Sectoral's blank column is still unknown.
- **The return changed in Jun 2022.** Infrastructure was re-listed (52 "R." lines to Mar 2022, 59
  numbered lines from Jun 2022): one sheet can now carry several declared layouts, each quarter
  records its layout, and the checks build one structure per layout (the tree read from RBI's codes
  in both schemes). On Major Sectoral, up to Mar 2022 gross advances = food + the five sectors and
  the printed "Non-Food Credit" is a narrower aggregate apart from them (SBI Dec 2021: 22,64,217 =
  26,871 + 22,37,346; non-food printed 18,28,400); encoded as the old-return identities.
- A non-scheduled Small Finance Bank group (Unity SFB, Dec 2021 – Mar 2022) is declared.
- Ratios are checked to the decimals RBI prints (2 in older quarters: CRAR 19.98 for 19.98167);
  an identity whose parts are not printed is skipped (SFB RWA components); Mar 2023's non-food total
  sits slightly below its sectors for 13 banks (Citibank 50,173 vs 50,208 Cr) — a quarter-level named
  exception, non-food taken as printed.
- Gate on 19 quarters: 0 column-wide failures; 453 isolated inconsistencies flagged.

**Phase 3, batch 3 (2026-11-14): Dec 2019 → Sep 2021.** 8 new quarters (Jun and Sep 2024 re-read,
unchanged); 27 of 97 saved; 98–99 banks in Dec 2019 – Mar 2020. No new layout or column. Roster: the
six banks amalgamated in April 2020 (Allahabad, Andhra, Corporation, OBC, Syndicate, United Bank;
last in the table Mar 2020), Lakshmi Vilas (to Mar 2021), Westpac (to Jun 2020), Subhadra Local
Area Bank (Mar–Sep 2020), each its own bank, not linked to a successor (merger adjustment is a
signals decision). Gate: 0 column-wide failures; 544 isolated inconsistencies flagged.

**Phase 3, batch 4 (2026-11-14): Dec 2017 → Sep 2019.** 8 new quarters (re-reads unchanged); 35 of 97
saved; 97–100 banks. No new layout or column. Roster: Dena and Vijaya (to Mar 2019), National
Australia Bank (to Jun 2019); "IDFC BANK LIMITED" is IDFC First Bank's name to Dec 2018 (dated alias).
- **RBI's group totals do not always count the banks printed in their block.** Dec 2017 – Dec 2018:
  the public-sector total includes IDBI Bank, which is printed among private banks (the private
  total leaves it out); IDBI was recategorised as private in Jan 2019. The gate now finds such a
  case itself: when ONE bank's figures equal a group's gap on every amount column of a sheet (at
  least 3), the sum is checked with RBI's own count and the move is reported, not flagged. It also
  found the foreign total leaving out Société Générale (Sep 2023) and UBS AG (Jun 2024). Gaps no
  single bank explains (Small Finance Banks 2017–19, Local Area Banks Sep 2019) stay flagged.
- Gate: 0 column-wide failures; 1,697 isolated inconsistencies flagged (of which 1,195 are those
  unexplained group gaps).

**Phase 3, batch 5 (2026-11-14): Dec 2015 → Sep 2017.** 8 new quarters (re-reads unchanged); 43 of 97
saved; 96–101 banks. No new layout or column. Roster: the five SBI associates and Bharatiya Mahila
Bank (to Mar 2017), Commonwealth Bank of Australia (to Jun 2017), KBC Bank (to Mar 2016), Capital
Local Area Bank (to Mar 2016; kept apart from Capital SFB until an RBI record links them). The
membership rule follows IDBI in the public-sector total back to Dec 2015, and finds ESAF SFB printed
among scheduled SFBs but counted in the non-scheduled total (Mar–Jun 2017). Gate: 0 column-wide
failures; 2,021 flags.

**Phase 3, batch 6 and the end of the backfill (2026-11-15): Mar 2015 → Sep 2015.** The export also
returned Dec 2013 – Dec 2014, where Major Sectoral breaks column-wide: agriculture, industry and food
are blank and the "non-food" and "services" cells hold small, different figures (SBI Dec 2014: non-food
₹19,978 Cr, services ₹4,683 Cr, gross ₹10,40,810 Cr), and Priority / Non-priority does not add for most
banks. **User decision: history from Mar 2015** (SIBC history does not reach further either). Those
five quarters were not committed and were removed; the declared start is now Mar 2015, `fetch.py`
skips (and reports) any quarter before it, and the history check is required: all 46 quarters
Mar 2015 → Jun 2026 saved. Roster: HSBC Bank Oman and ING Vysya (both to Mar 2015). Gate: 0 column-wide
failures; 2,144 isolated inconsistencies flagged; 1,243,828 values in the local table.

**Phase 4 (2026-11-17): signals and model.** Built as §8a, with these as-built facts:
- The local table is in the payments shape and the manifest is `primary` with `compute_module:
  atm_pos`; 130 registry entries come from `pipelines/rbi_bankwise/build_registry.py`, which reads
  the 13 measures from the skeleton profile (10 signals each, 9 for gross, plus the gross NPA ratio;
  each allocation has its momentum companion, whose coherence bounds the shares).
  Gate stage 4-reg fails if the registry and the profile disagree.
- Appended for all 46 quarters (239,732 rows, all matching a recompute). Spot check: HDFC Bank 15.4% a year to Jun 2026
  = 30.11 / 26.09 lakh crore; all banks 17.0% (SIBC bank credit ~19% in the same months).
- Breaks are honoured in the payments module for every bank, group and total method (payments
  freshness unchanged: 216,164 rows). Seven mergers in `series_breaks.json`, each checked in the data
  by the absorbing bank's jump. Two also break the group and the all-banks total (IDFC–Capital First,
  Dec 2018; HDFC Ltd, Jul 2023), so all-banks growth is absent for the four quarters after each.
  **Open (user):** Capital First added about 0.3% to all banks' credit, so blanking a year of
  all-banks growth for it may cost more than it protects.
- The skeleton profile declares what is NOT a line (`outside_model`, a pattern and a reason each):
  NPA columns, the priority and infrastructure cuts, and the bank-measure sheets. `generate_skeleton`
  and `validate_system_model` both read it, so an undeclared new column still fails completeness.
- The behavioural layer is declared deferred (`_meta.behavioral_status`) until the FOUNDATION pass.
- The coverage count reads "no reading" on all 12 lines: it is monthly by construction (a move is
  one data month apart). **Open:** whether quarterly lines get a quarter-step move rule.
- RBI's All-banks row differs from its banks' sum by 0–1.6% (continuous, from flagged cells), so
  shares divide by the published total. The "of which never sums to 100" test now judges only
  windows where the two denominators differ by ≥1 pt: all 84 SIBC and 44 NBFC windows, 5 of 102 bank-wise.
- The pace column is not stored per bank (payments stores none either).
