# PLAN: the one living plan

> Rewritten in place, never appended. Finished items are **deleted** (git keeps them). Hard cap
> 120 lines, enforced by `reconcile.py`. Standing rules live in `DECISIONS.md`; how to run a
> workflow lives in its skill (`.claude/skills/`). Last rewritten 2026-10-08.

## Now: the agentic layer (design: `archive/docs/PLAN_2026-09-24_AGENTIC_LAYER.md`)

The engine (gate, compute, registry, traceability) stays deterministic code. On top of it:
skills = procedure, subagents = independent review, hooks + `reconcile.py` = enforcement.
Phases 0–3 ✅ (2026-09-24/26: hooks, knowledge split, four skills tested on the Aug 2026 ingest,
three reviewer subagents accepted cold at 4/4 caught, 0/3 false). **Phase 4:** `onboard-source` ✅ 2026-10-05 (from NBFC + MoSPI);
`add-signal-family`, `measure-gate` ⬜, each written while doing its real task. `dashboard-change` ⬜:
its real task happened 2026-10-05/06 (Read hierarchy, DASHBOARD_SPEC §22); write it from §22.6 + the
ASCII → approve → build → verify at 1440/375, light/dark loop, before the next dashboard change.

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
   - **CPI each month** (Sep due ~12–14 Oct; MoSPI 1b fails overdue without it, and SIBC's gate with it).
   - **Replace the hand-read CPI PDFs** with the press-release annex in MoSPI's eSankhyiki
     catalogue (Excel, base 2024, monthly from Feb 2026, e.g. `CPIMCY26004AUG`). Index:
     `api.mospi.gov.in/api/esankhyiki/cms/golden-sheet/list?product=CPI`; files:
     `…/api/esankhyiki/file/download{file_path}{file_name}`. Retires `cpi_release.py`.
   - **The S4 decomposition** reads 1f (open decisions below): design first, ASCII first.
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
6. **Lending & Deposit Rates** (monthly PDF; `pdftotext` works, so it is table extraction).

## Open decisions and known debts (not scheduled)

- **S4 cannot explain medium-term moves (user, 2026-10-03). 1f is built; design this next.** S4 asks
  "which instrument took effect inside the window", so a lagged response or a slow-building
  condition reads as `expired` or gets a decorative citation. Aug 2026 showed it: the two causes
  that sourced cleanly (#12 ATM fees, RBI 1 May 2025; #8 TReDS, 7 Nov 2024) are real and fit the
  movement only through a lag, and are held unpromoted. Directions, in payoff order:
  (1) **decompose before attributing**: 1f real growth + output explain the price/activity share,
  so S4 explains only the residual; (2) a **response lag** on forces, so the temporal check is
  "effective date + declared lag overlaps the window", not "effective date inside it";
  (3) sourced **standing conditions** as a class distinct from statistics; (4) record what stays
  unexplained as such. Until then: source, do not promote; the Aug worklist keeps 12 proposals
  unsearched (`analysis/s4_proposals/2026-09-30.json`).

- **Stage 5.7 checks the declared cut, not the drawn series** (found 2026-10-05). Payments cards
  naming a bank category were drawn over the top-5 banks, so the chart showed only Total, and 5.7
  was green. Fixed in the renderer (`AtmReadMode.tsx` picks by_type / individual from the highlight);
  the gate still cannot see it. Bank-named cards draw `individual`, so a bank outside the top 5 is safe.
  A guard needs a rendered-series check (measure first, per DECISIONS).
- **Share bar charts flatten real moves**: small shares (Small Finance Banks +0.97 pp at 2.0%) read
  as a sliver, and a 0–80% axis makes Large 71 → 66.5 look flat; at 375px the bars are 2px because
  the Y axis takes 96px of 255. A line of the share itself would show the move. Presentation; §22.3.
- **Payments POS value table**: the total row shows "—" for growth though the band says 9.1% YoY.
- **"lowest in N periods"** card titles count readings, not months: SIBC history has gaps
  (Aug–Nov 2024 and 2025), so "25 periods" reads as two years when it means "since Dec 2023".
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

- **Distribution**: LinkedIn carousels began with Aug 2026 (3 posts: headline stats, market-share
  mix, MoSPI real credit; `analysis/distribution/output/2026-10-08_linkedin_set*`). Flow: Claude
  drafts text + source table + ASCII layout → user rewrites → approves → PDF. Tooling (uncommitted,
  hand-tuned per set) in `analysis/distribution/carousel/`; make it one generic builder, and a
  `linkedin-carousel` skill, when the September posts repeat it. Substack paused; X per-bank feed idea stands.
- **PDF extraction** as a general capability: 11 of 21 remaining RBI sources are PDF-only. Start
  it when a PDF source is next in line, not before.
- **Future data bets**: longer history → forecasting; bank results → per-bank analytics.
- **Research bets** (from the retired RESEARCH_BACKLOG): open-source a financial-analysis eval set
  built from our deterministic ground truth; LLM reasoning over the causal graph, not only signals.
- Strategy, revenue and the content ladder: `STRATEGY_PLANNER.md`.
