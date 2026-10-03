# PLAN: the one living plan

> Rewritten in place, never appended. Finished items are **deleted** (git keeps them). Hard cap
> 120 lines, enforced by `reconcile.py`. Standing rules live in `DECISIONS.md`; how to run a
> workflow lives in its skill (`.claude/skills/`). Last rewritten 2026-10-03 (pruned the same day).

## Now: the agentic layer (design: `archive/docs/PLAN_2026-09-24_AGENTIC_LAYER.md`)

The engine (gate, compute, registry, traceability) stays deterministic code. On top of it:
skills = procedure, subagents = independent review, hooks + `reconcile.py` = enforcement.
Phases 0–3 ✅ (2026-09-24/26: hooks, knowledge split, four skills tested on the Aug 2026 ingest,
three reviewer subagents accepted cold at 4/4 caught, 0/3 false). **Phase 4 ⬜:** `onboard-source`,
`add-signal-family`, `measure-gate`, `dashboard-change`, each written while doing its real task.

## Next, in order

1. **NBFC August ingest** when RBI publishes (SIBC + payments Aug done 2026-10-03, with model
   passes and S4). Then `/model-pass nbfc` + `/s4-source`, which also takes the 3 deferred
   NBFC-raised proposals (#17-19 in `analysis/s4_proposals/2026-09-30.json`).
2. **NBFC post-ingest count** (NBFC plan §6 "after the ingest"): how many files did pipeline #3
   touch that were not its own? Record it in `ARCHITECTURE.md` §"Adding a pipeline", and let it
   decide the open fork on a generic card path.
3. **MoSPI (IIP, WPI, NAS, CPI) as pipeline #4**: a reference pipeline with no page of its own;
   its numbers reach the credit tables through one generic join driven by a concordance (user,
   2026-09-26). Pulled by hand until two clean cycles. Spec: signals/README §1f + "MoSPI",
   COMPOSITION_SPEC §24, DASHBOARD_SPEC §21 (layouts need a final look before code).
   Phases 0–2 ✅ (2026-09-26/29): spec, ingest + gate, concordance + stage 1d. IIP weights sourced
   from MoSPI's own table 2026-10-03: output covers 12/19 industry types (45% of industry credit).
   - **Phase 3 (next):** the two 1f methods + registry entries + `reason`/`operands` in signals.db +
     SIBC `depends_on`. Two questions put to the user 2026-10-03, unanswered: (a) periods before
     the reference series exist (SIBC Dec 2023–24; CPI before Jan 2026): a new per-period reason
     `reference_history_gap`, or no rows; (b) quarterly NAS rows stored at quarter-ends only.
     Candidate: the IIP weights rebuild (0.046 pt measured by hand) as a standing 1d check.
   - **Then:** 4 table columns (stamp_table + `CutTable`); write `onboard-source` as we go.
   - **Replace the hand-read CPI PDFs** with the press-release annex in MoSPI's eSankhyiki
     catalogue (Excel, base 2024, monthly from Feb 2026, e.g. `CPIMCY26004AUG`). Index:
     `api.mospi.gov.in/api/esankhyiki/cms/golden-sheet/list?product=CPI`; files:
     `…/api/esankhyiki/file/download{file_path}{file_name}`. Retires `cpi_release.py`, whose PDF
     layout changed three times in eight releases. The catalogue (~4,800 tables) is the place to
     look first for any MoSPI table, weights included.
   - **Open, user deciding:** textiles vs apparel (SIBC 2.4 ↔ nic:13 or 13+14); WPI weights for the
     6 combined deflators (WPI is DPIIT's, not in MoSPI's catalogue: eaindustry.nic.in); petroleum
     deflated by WPI mineral oils (a judgment, §24.2).
4. **Arc 3: RBI regulatory watch** (S4 pointed at RBI, push not pull). Admission rule: an item
   enters only if it attaches to a model entity, channel or cut. ⚠️ Re-run the allowlist census
   first; the 2026-08-19 one predates the probe-bug retraction. Design: `archive/docs/PLAN_2026-09-09.md` arc 3.
5. **BSR-1 Table 1.4** (quarterly, credit by occupation). The real cost: three measures per entity
   (accounts / limit / outstanding) where every layer assumes one, and an occupation taxonomy
   that overlaps SIBC sectors without matching them.
6. **Lending & Deposit Rates** (monthly PDF; `pdftotext` works, so it is table extraction).

## Open decisions and known debts (not scheduled)

- **S4 cannot explain medium-term moves (user, 2026-10-03). Design with MoSPI phase 3.** S4 asks
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

- **Explore's Insights section (user, 2026-10-03, deferred):** legacy step-through UI, but Explore
  is the only surface where every card is reachable (DASHBOARD_SPEC §18–19). Recommended: keep the
  inventory as one shared plain list, drop `InsightCTAStrip` + insight mode. ASCII first.
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
- **26 hand-written SIBC annotations** in `rbi_sibc.ts` last changed 2026-06-12; nothing refreshes
  them. `/model-pass` decides at the March FOUNDATION whether to refresh or retire them.
- **Prompt v1.13 fix list** (paid; bundle with the next evaluate run): 3 eval-authored 5.8 warnings
  (`through FY26`, `watch for`, `on track to`).
- **S4 worklist 2026-08-31**: 20 proposals still need a browser (`run_inference.py --worklist`).
- **signals.db → Git LFS at ~80 MB** (GitHub's hard limit is 100 MB per file).
- **SIBC still ships its raw CSV** for client parsing; payments ships a compact precomputed
  series. Move SIBC to the same mechanism before relocating either CSV out of `web/public/`.
- **ai_pm_register** has not been updated for arcs 1–2 or NBFC; the injection numbers in those
  commit messages are loggable against topic #1.

## Parked (a trigger, not a date)

- **Distribution**: Substack paused (generators kept); the user reads a few cycles first. Next
  channel idea = an X per-bank blurb feed, which is payments-only because no per-bank credit exists monthly.
- **PDF extraction** as a general capability: 11 of 21 remaining RBI sources are PDF-only. Start
  it when a PDF source is next in line, not before.
- **Future data bets**: longer history → forecasting; bank results → per-bank analytics.
- **Research bets** (from the retired RESEARCH_BACKLOG): open-source a financial-analysis eval set
  built from our deterministic ground truth; LLM reasoning over the causal graph, not only signals.
- Strategy, revenue and the content ladder: `STRATEGY_PLANNER.md`.
