# PLAN: the one living plan

> Rewritten in place, never appended. Finished items are **deleted** (git keeps them). Hard cap
> 120 lines, enforced by `reconcile.py`. Standing rules live in `DECISIONS.md`; how to run a
> workflow lives in its skill (`.claude/skills/`). Last rewritten 2026-10-09.

## Now: tightening the model under S4 (user, 2026-10-08)

S4 was asked to explain growth, not change, and could only accept government instruments, because
the layers under it were thin. Order agreed: fix the force check → count what the model explains
→ relationships inside a pipeline → links between pipelines → master model → S4 redesign.
Built 2026-10-08 (SYSTEM_MODEL_SPEC v3.1 §16):
- **Force check** (Step 3, `core/force_check.py`): against the line's group, with timing; live for
  SIBC and payments (8 group-total YoY signals). Active: SIBC 8, payments 2; KCC in doubt.
- **Coverage count** (Step 6a, `core/coverage.py`): moves vs explained, every state file; S4 reads
  its list from it. SIBC Aug 2026: 6 moves, 2 structural, 4 unexplained (food credit, loans
  against FDs, other industries, fertiliser). History: 102 unexplained → 86 after structural.
- **Relationship test** (Step 6b, `core/relationship_test.py`): HFC vs housing and the four
  construction links all `not_supported` (`analysis/rbi_sibc/relationship_tests.json`).
  **History is the binding constraint:** 15 monthly changes see only |r| ≥ 0.51.
- **12 model arrows tested** (10-10): none supported; states, loops, coverage, line-driven opportunities
  follow tests. **Card spend → card outstanding (1-month lead) supported** (r=+0.54, borderline).
- **Buyer first** (STRATEGY v3.1 §5, 10-11): log who engages with X/LinkedIn, ask the 3 questions; the
  next source waits on it. Per-bank quarterly found on DBIE (`analysis/sources/README.md`), not ingested.

Agentic layer: phases 0–4 as before (`dashboard-change`, `onboard-source` ✅); `add-signal-family`,
`measure-gate` ⬜, each written while doing its real task.

## Next, in order

1. **NBFC August ingest** when RBI publishes (SIBC + payments Aug done 2026-10-03, with model
   passes and S4). Then `/model-pass nbfc` + `/s4-source`, which also takes the 3 deferred
   NBFC-raised proposals (#17-19 in `analysis/s4_proposals/2026-09-30.json`).
2. **NBFC post-ingest count** (NBFC plan §6 "after the ingest"): how many files did pipeline #3
   touch that were not its own? Record it in `ARCHITECTURE.md` §"Adding a pipeline", and let it
   decide the open fork on a generic card path.
3. **MoSPI (IIP, WPI, NAS, CPI), pipeline #4: phases 0–4 ✅ (2026-09-26 → 10-04).** A reference
   pipeline joined to SIBC by `ontology/concordance/sibc__mospi.json`; the 1f signals put Real
   credit and Output 12m on 8 SIBC tables. Spec as built: signals/README §1f + "MoSPI",
   COMPOSITION_SPEC §24, DASHBOARD_SPEC §21.8. Pulled by hand until two clean cycles. Next:
   - **CPI each month (settled 10-18):** release-day source is the press-release PDF (`fetch.py --cpi-pdf`);
     the eSankhyiki annex arrives later (Sep not listed by 10-18) and confirms. Dashboard workbook retired
     (user): redundant, and its name stopped dating its contents. Next: fetch the PDF automatically from
     MoSPI's product feed (`api/product/get-product-data`, product 9 lists every release PDF).
   - 1f now feeds the coverage count's prices/activity check (Step 6a); S4 redesign below.
   - Candidate gate: the IIP weights rebuild (0.046 pt, measured by hand) as a standing 1d check.
   - **Open, user deciding:** textiles vs apparel (SIBC 2.4 ↔ nic:13 or 13+14); WPI weights for the
     6 combined deflators (WPI is DPIIT's, not in MoSPI's catalogue: eaindustry.nic.in); petroleum
     deflated by WPI mineral oils (a judgment, §24.2; shown with its price note since 2026-10-04).
4. **Arc 3: RBI regulatory watch** (S4 pointed at RBI, push not pull). Admission rule: an item
   enters only if it attaches to a model entity, channel or cut. ⚠️ Re-run the allowlist census
   first; the 2026-08-19 one predates the probe-bug retraction. Design: `archive/docs/PLAN_2026-09-09.md` arc 3.
5. **BSR-1 Table 1.4** (quarterly, credit by occupation). The real cost: three measures per entity
   (accounts / limit / outstanding) where every layer assumes one, and an occupation taxonomy
   that overlaps SIBC sectors without matching them.
6. **Lending & Deposit Rates: probed 10-10, onboarding paused (user).** Excel, full history in each
   file (Jun–Sep 2026 in repo root); findings in `analysis/sources/README.md`. **Open, user deciding
   after stepping back:** reference vs primary-with-page; the source order (#4–6); which of the 9 tables.

## Open decisions and known debts (not scheduled)

- **Open for the model:** explainability loop (SYSTEM_MODEL_SPEC §16 Step 6c), step 3 next; **review
  later: vehicles and durables input prices** (`rbi_sibc/explainability_grid.md`). SIBC releases Sep–Dec
  2024 still to add (user). 12 S4 proposals unsearched (`analysis/s4_proposals/2026-09-30.json`).

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
- **S4 worklist 2026-08-31**: 20 proposals still need a browser (`run_inference.py --worklist`).
- **signals.db → Git LFS at ~80 MB** (GitHub's hard limit is 100 MB per file).
- **SIBC still ships its raw CSV** for client parsing; payments ships a compact precomputed
  series. Move SIBC to the same mechanism before relocating either CSV out of `web/public/`.
- **ai_pm_register** has not been updated for arcs 1–2 or NBFC; the injection numbers in those
  commit messages are loggable against topic #1.

## Parked (a trigger, not a date)

- **Distribution**: **X daily from 2026-10-10** (DISTRIBUTION_SPEC §16): 25-day plan in
  `output/x/2026-10-10_to_11-03_plan.md`; `x/build_posts.mjs {batch}` → post.txt + 16:9 card (phone
  text ≥ 9px, every number traced); posts 1–5 built, next batch = plan #6–10. LinkedIn: 3 sets/month
  (Aug done, `carousel/`); NBFC story first, then the `linkedin-carousel` skill (user: parked till then).
  Open: @RBI source credit in X posts; auto-post via API after two clean weeks. Substack paused.
- **PDF extraction** as a general capability: 11 of 21 remaining RBI sources are PDF-only. Start
  it when a PDF source is next in line, not before.
- **Future data bets**: longer history → forecasting; bank results → per-bank analytics.
- **Research bets** (from the retired RESEARCH_BACKLOG): open-source a financial-analysis eval set
  built from our deterministic ground truth; LLM reasoning over the causal graph, not only signals.
- Strategy, revenue and the content ladder: `STRATEGY_PLANNER.md`.
