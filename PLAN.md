# PLAN: the one living plan

> Rewritten in place, never appended. Finished items are **deleted** (git keeps them). Hard cap
> 120 lines, enforced by `reconcile.py`. Standing rules live in `DECISIONS.md`; how to run a
> workflow lives in its skill (`.claude/skills/`). Last rewritten 2026-10-18.

## Now: make the credit system explainable (user, 2026-10-11)

The aim: explain why each line moves through the system's own drivers, so what remains is honestly
"not explained by them". Method: the explainability loop (SYSTEM_MODEL_SPEC v3.2 §16 Step 6c, built
2026-10-11/12): coverage count (6a, incl. base effect) → driver register (`rbi_sibc/driver_hypotheses.json`)
→ completeness grid (`rbi_sibc/explainability_grid.md`, `core/explainability.py report`) → generic
driver test, each line's delay found on earlier months and confirmed on later ones (`... test`).
**Target: every column of the grid complete** (user). Explained share is the outcome: SIBC 23% → 41%
of 218 moves after the base effect.
- **History is the binding constraint:** 25 usable monthly changes; the first driver run read 46 of 47
  `too_short` (one lead: petroleum credit vs fuel prices, delay 3, opposite sign, 13 months).
- Steps 4 (admission: a `driver` explanation in 6a, `prices_activity` handed over) and 5 (cycles on
  new data) wait until something is supported. **Review later (user): vehicles and durables input prices.**
- **Buyer first** (STRATEGY v3.1 §5): log who engages with X/LinkedIn, ask the 3 questions; a source is
  chosen by a buyer conversation and by the grid column it completes.

## Next, in order

1. **Extend history, both sides** (proposed 10-12, user to decide in the strategy session):
   DBIE "Deployment of Bank Credit by Major Sectors" + industry-wise, monthly from Jan 2019 (system-level,
   SIBC-shaped). SIBC releases stay primary; DBIE fills before Jan 2023 only after every 2023–26 overlap
   month matches (a ~1% September gap seen 10-10 must be explained first). Plus MoSPI's older-base
   (2011-12) WPI/IIP joined to the current base: without it older credit cannot be tested against prices
   and output. Together ~25 → ~80 changes (detectable |r| 0.40 → ~0.22). **Git LFS for signals.db
   first** (82 MB; GitHub warns at 50, refuses at 100).
2. **Releases due:** SIBC Sep ~30 Oct, payments Sep ~3–5 Nov, NBFC Sep ~6 Nov (`/ingest-period`, then
   `/model-pass` + `/s4-source`; NBFC also takes deferred proposals #17-19 in `s4_proposals/2026-09-30.json`).
   CPI Oct ~12 Nov: PDF from MoSPI's product feed (`api/product/get-product-data`, product 9 lists every
   release PDF), read with `fetch.py --cpi-pdf`; automating that fetch is a small next step.
3. **X:** posts built to 3 Nov (`output/x/2026-10-18/`, `2026-10-23/`); next batch from 4 Nov, release
   stories once SIBC/payments September land. Card e-commerce held: HDFC/SBI share break in Aug.
4. **Model pass, owed:** risk-arrow signs (arrows that do not say which way they push) and NBFC causes
   (no `/model-pass nbfc` or `/s4-source` since its Aug ingest; deferred proposals #17-19 wait for it).
   Then S4 widened to market sources for the residual. NBFC force check stays off (9 moves of history).
5. **NBFC post-ingest count** (NBFC plan §6): how many files did pipeline #3 touch that were not its
   own? Record it in `ARCHITECTURE.md` §"Adding a pipeline"; it decides the generic card path fork.
6. **MoSPI open decisions (user):** textiles vs apparel (SIBC 2.4 ↔ nic:13 or 13+14); WPI weights for the
   6 combined deflators (eaindustry.nic.in); petroleum deflated by WPI mineral oils (§24.2). Candidate
   gate: the IIP weights rebuild (0.046 pt) as a standing 1d check.
7. **Sources, order by buyer and grid** (catalogue: `analysis/sources/README.md`): Lending & Deposit Rates
   (probed 10-10, paused; fills "price of credit", 83 lines), DBIE flow of resources/CP/ECB ("other
   finance", 52), per-bank quarterly (buyer-led), arc 3 regulatory watch (`archive/docs/PLAN_2026-09-09.md`;
   re-run the allowlist census first), BSR-1 (three measures per entity; occupation ≠ SIBC sectors).

## Open decisions and known debts (not scheduled)

- **Agentic layer:** `add-signal-family` and `measure-gate` skills ⬜, each written while doing its real task
  (the story-readings and driver-test builds of 10-10/12 were candidates; not yet written).
- **The merger gap is unexplained on screen** (10-10): growth cells absent for `merger_break` (Jan–Jun 2024)
  draw blank with no reason; "Every reading" skips them. A `/dashboard-change`.
- **12 S4 proposals unsearched** (`analysis/s4_proposals/2026-09-30.json`); 20 more from 2026-08-31.

- **Stage 5.7 checks the declared cut, not the drawn series** (found 2026-10-05). Payments cards
  naming a bank category were drawn over the top-5 banks, so the chart showed only Total, and 5.7
  was green. Fixed in the renderer (`AtmReadMode.tsx` picks by_type / individual from the highlight);
  the gate still cannot see it. Bank-named cards draw `individual`, so a bank outside the top 5 is safe.
  A guard needs a rendered-series check (measure first, per DECISIONS).
- **Share bar charts flatten real moves**: small shares (Small Finance Banks +0.97 pp at 2.0%) read
  as a sliver, and a 0–80% axis makes Large 71 → 66.5 look flat; at 375px the bars are 2px because
  the Y axis takes 96px of 255. A line of the share itself would show the move. Presentation; §22.3.
- **SIBC sub-cut totals** (found 2026-10-08): 7 sub-industry tables (Basic Metal, Chemicals,
  Engineering, Food Processing, NBFCs, Textiles, Trade) draw "—" for the total's growth while the
  band quotes it from the parent table's ROW. `table_rows` reads a parent rate only as a whole-cut
  aggregate; teach it a (signal, entity) parent, then delete `KNOWN_TOTAL_GAPS` in test_cut_table.
- **"Hover a — for why it is empty"** is written by `core/real_cells.footnote()`; now folded under
  "Notes on this table", it is redundant. Remove at source with the next table rebuild.
- **Heading hints don't work on touch** (hover/keyboard focus only); tapping a heading sorts.
- **Table-cell tolerance:** the six original columns are checked with the prose tolerance (±0.5%),
  which let 6/57 moved 1f cells pass before 1f went exact. Same fix for them, measured first.
- **Card/band dedup, option B**: every card records entity/metric ids in the band's vocabulary,
  so arbitration is a set intersection. Do it when entity naming is touched anyway. Option A (a
  test pinning which cards are superseded) is the cheap stopgap.
- **PSL `weight` / `weight_now`** divide by the sum of non-additive parts. Changing it rewrites
  PSL's Layer 2 mix state, so it needs a decision, not a side effect.
- **Bank growth off a negligible base** ranks first when sorted by growth (Bandhan +416,450% on
  24,993 cards). A `min_base` rule is undecided.
- **Generic card path vs table-as-the-L1-surface** (ARCHITECTURE item 3): decide from the count in Next #2.
- **NBFC phases 7–8** (cross-source concepts, links, construct, channel UI) are deferred by the
  user until L1 is reviewed (NBFC plan D5).
- **27 hand-written SIBC annotations** in `rbi_sibc.ts` (unchanged since 2026-06-12) render nowhere
  since Explore went charts-only (user, 2026-10-05); IDs stay. The March FOUNDATION decides:
  rewrite them for Read, or leave them retired.
- **Subject-plane cards** (50 SIBC, 26 payments) are still generated and narrated (paid) though no
  surface shows them; their numbers are table cells. Whether to stop generating them is open.
- **Prompt v1.13 fix list** (paid; bundle with the next evaluate run): 3 eval-authored 5.8 warnings
  (`through FY26`, `watch for`, `on track to`).
- **SIBC still ships its raw CSV** for client parsing; payments ships a compact precomputed
  series. Move SIBC to the same mechanism before relocating either CSV out of `web/public/`.
- **ai_pm_register** has not been updated for arcs 1–2 or NBFC; the injection numbers in those
  commit messages are loggable against topic #1.

## Parked (a trigger, not a date)

- **Distribution**: X daily since 10-10 (DISTRIBUTION_SPEC §16; `x/build_posts.mjs {batch} --base URL`;
  @RBI credit and API auto-post open). LinkedIn 3 sets/month; the NBFC story first, then the
  `linkedin-carousel` skill (user: parked till then). Substack paused.
- **PDF extraction** as a general capability: 11 of 21 remaining RBI sources are PDF-only. Start
  it when a PDF source is next in line, not before.
- **Future data bets**: longer history → forecasting; bank results → per-bank analytics.
- **Research bets** (from the retired RESEARCH_BACKLOG): open-source a financial-analysis eval set
  built from our deterministic ground truth; LLM reasoning over the causal graph, not only signals.
- Strategy, revenue and the content ladder: `STRATEGY_PLANNER.md`.
