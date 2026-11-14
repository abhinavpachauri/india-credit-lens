# Bank-wise credit pipeline (`rbi_bankwise`): specification

> v0.2, 2026-11-14. Status: **phases 1–2 built** (roster, reader, saved quarters, local table, checks against RBI's totals). Onboarded through the `onboard-source` skill.
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

## 9. Decisions (user, 2026-11-14: "use your proposals")

1. **All eight sheets** in phase 1: the whole record, read once.
2. **History from Mar 2002**, the full record; the group set before 2016 differs and §5.1 reads it
   from the layout.
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
