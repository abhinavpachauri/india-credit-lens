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
3. **MoSPI (IIP, WPI, NAS, CPI) as pipeline #4** (`STRATEGY_PLANNER.md` §8.1). Before arc 3, while SIBC Aug is pending (user, 2026-09-26).
   **Shape (user, 2026-09-26):** its own manifest, gate, snapshots and L1 signals; **no page of
   its own**. Its numbers reach the credit tables through one generic join driven by a concordance
   in the ontology, so NBFC ↔ NAS later needs no new code. MoSPI only for v1 (Eight Core Industries
   parked). Pull by hand until two clean cycles, then scheduled.
   - **Probed 2026-09-26 (free), per dataset:**
     - **IIP** 2022-23 base, Apr 2023 → Jul 2026, 2-digit NIC only. No provisional/final flag:
       revisions overwrite silently, so every release is saved.
     - **WPI** new base needs the UNDOCUMENTED `base_year=2022-23`; without it the API silently
       serves the old 2011-12 series (ends Apr 2026). Jan → Aug 2026, 953 items, 3/4-digit
       sub-groups (iron & steel, cement, glass, fertiliser, sugar, tea, jewellery).
     - **NAS** quarterly GVA, 2022-23 base, → Q1 FY27, 8 sectors at current AND constant prices
       (own deflator). Without `base_year` one response mixes both bases (153 new + 522 old rows).
     - **CPI** the API holds only the 2012 base, ending Dec 2025; the new base is not loaded (no
       endpoint, `base_year=2024` → no data). Take it from MoSPI's monthly release file until the
       API catches up; use MoSPI's published inflation, never our own link across bases.
     - **Guard for all four:** every row must carry the expected `base_year`, or the run fails.
   - **Concordance:** SIBC industry types ↔ IIP/WPI groups, 12 of 19 = 45% of industry credit; +
     Power ↔ Electricity → ~64%. 5 rows combine IIP groups by 2022-23 weights (PIB PRID 2267531,
     Statement II-A, sum 76.062; rebuilds the published index within ~1 pt). Exact sub-row matches:
     Power, Electronics (NIC 26), Pharma (NIC 21). No counterpart: construction (→ NAS), infra ex-power,
     gems, other; cement/glass share an IIP group; textiles vs apparel undecided. NAS sectors ↔ SIBC
     main sectors, services and Construction. CPI ↔ Personal Loans.
   - **Phase 0 (spec) ✅ 2026-09-26, v0.2 after the three reviewers:** signals/README §1f + "MoSPI";
     COMPOSITION_SPEC §24; DASHBOARD_SPEC §21. Decided: output over a trailing year; Personal Loans
     get no Output (48% housing); Industry, Services and the total are declared approximations, with computed notes;
     a closed list of absence reasons in code; overdue fails. Layouts in §21 need a final look before code.
   - **Found and fixed on the way (2026-09-26):** six pinned table rows showed the sum of the named
     parts, not the parent (NBFCs ₹7.38L vs ₹21.28L Cr); NBFC stage 1c passed on zero checks.
   - **Next phases:** 1 reference-kind plumbing (six all-pipeline populations, `depends_on`,
     always-fetch mode) + MoSPI ingest (fetch contract, saved releases, consolidate, gate) → 2 concordance
     file + `validate_concordance` → 3 the two 1f methods + registry entries + SIBC `depends_on` →
     4 table columns (stamp_table + `CutTable`) → write `onboard-source` as we go.
   - **Display:** see DASHBOARD_SPEC §21.
   - **Decided in spec:** 1f signals live in the credit pipeline's registry; MoSPI has no signals
     of its own in v1; match = exact or built from exact parts.
   - **Open:** WPI weights (6 Real-credit cells absent until sourced); textiles vs apparel;
     Petroleum deflated by WPI mineral oils (a judgment, flagged in §24.2).
4. **Arc 3: RBI regulatory watch** (S4 pointed at RBI, push not pull). Admission rule: an item
   enters only if it attaches to a model entity, channel or cut. ⚠️ Re-run the allowlist census
   first; the 2026-08-19 one predates the probe-bug retraction. Design: `archive/docs/PLAN_2026-09-09.md` arc 3.
5. **BSR-1 Table 1.4** (quarterly, credit by occupation). The real cost: three measures per entity
   (accounts / limit / outstanding) where every layer assumes one, and an occupation taxonomy
   that overlaps SIBC sectors without matching them.
6. **Lending & Deposit Rates** (monthly PDF; `pdftotext` works, so it is table extraction).

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
