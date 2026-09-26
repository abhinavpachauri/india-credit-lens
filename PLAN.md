# PLAN: the one living plan

> Rewritten in place, never appended. Finished items are **deleted** (git keeps them). Hard cap
> 120 lines, enforced by `reconcile.py`. Standing rules live in `DECISIONS.md`; how to run a
> workflow lives in its skill (`.claude/skills/`). Last rewritten 2026-09-24.

## Now: the agentic layer (design: `archive/docs/PLAN_2026-09-24_AGENTIC_LAYER.md`)

The engine (gate, compute, registry, traceability) stays deterministic code. On top of it:
skills = procedure, subagents = independent review, hooks + `reconcile.py` = enforcement.

| Phase | Work | State |
|---|---|---|
| 0 | edit hook runs the v4 validator; allowlist repointed; `.claude/` tracked in git; reconcile Checks 6 (agent layer names live files) + 7 (context budget) | ✅ 2026-09-24 |
| 1 | knowledge split: `PLAN.md` + `DECISIONS.md` imported by CLAUDE.md; CLAUDE.local.md capped; dated plans archived | ✅ 2026-09-24 |
| 2 | skills `ingest-period`, `model-pass`, `s4-source`, `session-close`; 3 stale March skills deleted | ✅ 2026-09-24. **Untested on real work**: the first August ingest is the test |
| 3 | reviewer subagents `population-auditor`, `absence-auditor`, `plausibility-auditor` + `/review-change` + `data-inspector` refreshed | ✅ 2026-09-26. **Accepted cold:** 4/4 real past defects caught, 0/3 false re-flags (run via `claude -p` outside the repo, rule written first). First live catches fixed: freshness missing NBFC; evaluator losing signals |
| 4 | `onboard-source`, `add-signal-family`, `measure-gate`, `dashboard-change` | ⬜ write each while doing its real task, not in the abstract |

## Next, in order

1. **August 2026 ingest**, the first run through `/ingest-period`. SIBC releases ~30 Sep;
   payments ~M+2; NBFC ~early Oct (July came 7 Sep). Then `/model-pass` + `/s4-source` (standing
   rule). Fix every place the skill was wrong **in the skill**, in the same session.
2. **NBFC post-ingest count** (NBFC plan §6 "after the ingest"): how many files did pipeline #3
   touch that were not its own? Record it in `ARCHITECTURE.md` §"Adding a pipeline", and let it
   decide the open fork on a generic card path.
3. **Arc 3: RBI regulatory watch** (S4 pointed at RBI, push not pull). Admission rule: an item
   enters only if it attaches to a model entity, channel or cut. ⚠️ Re-run the allowlist census
   first; the 2026-08-19 one predates the probe-bug retraction. Design: `archive/docs/PLAN_2026-09-09.md` arc 3.
4. **BSR-1 Table 1.4** (quarterly, credit by occupation). The real cost: three measures per entity
   (accounts / limit / outstanding) where every layer assumes one, and an occupation taxonomy
   that overlaps SIBC sectors without matching them.
5. **Lending & Deposit Rates** (monthly PDF; `pdftotext` works, so it is table extraction).
6. **MoSPI eSankhyiki: the real economy behind the credit** (`STRATEGY_PLANNER.md` §8.1).
   ⏸ **Position in this order is the user's call.** Probe done 2026-09-26 (free):
   - **Base:** IIP and WPI are on a 2022-23 base the spec omits; use it only (IIP Apr 2023 →, WPI →
     Aug 2026). Never chain across bases; field names differ by base (`majorgroup` vs `major_group`).
   - **Snapshot:** two fetches are identical in content and order; the natural key (year, month,
     type, category, sub-category) is unique; values arrive as strings. **No provisional/final
     flag**: revisions overwrite silently, so saving each release is mandatory, not optional.
   - **Mapping** (SIBC's 19 industry types): 7 map 1:1 to an IIP group (mining, food, leather, wood,
     paper, petroleum, rubber/plastics). 5 combine IIP groups by their **2022-23 weights**: beverage &
     tobacco (NIC 11+12), chemicals + pharma (20+21), basic + fabricated metals (24+25), engineering
     (26+27+28), vehicles (29+30). Weights: PIB PRID 2267531, Statement II-A (sum 76.062); fixed for
     the base, so a one-time sourced table, not a monthly pull. Verified: they rebuild the published
     manufacturing index within ~1 point and its YoY within ~0.2 pp (MoSPI aggregates from 455 item
     groups, so exact is impossible). Glass + cement share one group; textiles is ambiguous over
     apparel; construction, infrastructure, gems and "other" have no counterpart. **12 of 19 covered.**
   - **Open decisions (user):** position in the source order; display (recommended: two columns on
     the industry-by-type table, ASCII first); manual vs scheduled pull (recommended: manual until
     two clean cycles). WPI group weights for deflating combined sectors: first new-series WPI
     release (Office of the Economic Adviser), not yet checked.
   - **The metric:** credit (nominal stock) vs IIP (real volume) needs WPI deflation first.
   - **Recommended build:** IIP + WPI as one API-pull pipeline, the NIC ↔ SIBC concordance authored
     once in the ontology, and "credit growth vs output growth, price-adjusted" as a column on the
     industry-by-type table (ASCII approval first).

## Open decisions and known debts (not scheduled)

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
