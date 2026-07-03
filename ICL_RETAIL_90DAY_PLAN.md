# ICL-Retail — 90-Day Plan
**Product thesis:** Government data (RBI + the wider govt-data pool) → sector → listed-stock transmission intelligence for Indian retail investors.
**Positioning line (working):** *"See what government data says about your stocks — before the market reads the PDF."*
**Operator budget:** ~30% time ≈ 12–14 hrs/week → split ~6 build / 5 content+distribution / 2 ops.
**Starting audience:** zero. The plan manufactures distribution; it does not assume it.

---

## The one strategic rule

**Publish before you build; log every claim.** The product is not "insights" (anti-moat — anyone with an LLM can make correlations). The product is:
1. **The transmission layer** — systematic mapping of govt-data releases → specific listed names (nobody does this; screener/Trendlyne do fundamentals, not data-flow).
2. **The dated, public, scoreable call register** — the moat AI can't fake, compounding from note #1.
3. **Monitoring** — "your stocks × these signals" alerts = recurring relationship, not one-off reads.

**SEBI guardrail (non-negotiable):** analytics and monitoring language only. "EPFO payroll growth turned negative for these 12 consumer names" ✅. "Buy Muthoot, target ₹2,400" ❌ — that's Research Analyst territory. No buy/sell/target-price language anywhere, free or paid. Revisit RA registration only if the product later moves to recommendations.

---

## Asset audit (what's already built and reusable — from india-credit-lens/)

| Asset | Reuse in retail product |
|---|---|
| RBI SIBC pipeline (84+ signals, 28 mo history) | Bank credit by sector → **banks, gold-loan NBFCs (Muthoot, Manappuram), MSME lenders, housing financiers** |
| RBI ATM/POS pipeline (84 signals) | Consumption/payments proxy → **SBI Cards, banks' fee income, consumption names** |
| signals.db + compute engine, traceability gates | The alert engine and the "every number traces to source" trust layer — *directly* the paid product's backbone |
| Causal system model (v4.0) | The transmission maps — repoint entities from "lenders" to "listed tickers" |
| Newsletter/LinkedIn generators | Repoint prompts at investor audience |

**~70% of the hard engineering is done.** The pivot is packaging + audience, not a rebuild.

---

## Execution notes (read before any build task)

Added 2026-07-02 after execution-readiness review. These resolve the ambiguities an implementing
session would otherwise guess at. Repo context still governs: `CLAUDE.md` (engineering principles,
gates) and `PIPELINE_ARCHITECTURE.md` (pipeline stages) apply to everything below.

### EN-1 · Entity → ticker layer = a mapping artifact, never a model edit

The Phase 1 build task "repoint the causal model's entity layer to tickers" does **not** modify
either `system_model.json` — those are skeleton-regenerated and validator-gated; entities stay
as-is. Build instead:

- **`analysis/ontology/ticker_map.json`** — new shared artifact, peer of `concepts.json`/
  `channels.json`: URN → list of `{ticker, exchange, relationship, transmission_note}`
  where `relationship ∈ pure_play | major_segment | partial`. Many-to-many is expected
  (one URN → several tickers; one ticker ← several URNs). URNs may be **entity URNs or
  ecosystem-construct URNs** (`icl:eco/…`, COMPOSITION_SPEC v1.1 §14) — a construct is often
  the right transmission anchor and brings its evidence set with it.
- **`analysis/validate_ticker_map.py`** — every URN must exist in a system model; ticker format
  valid; relationship enum enforced. Wire into both gates (advisory while being populated,
  strict once the first 3 transmission maps are in).
- The "stock ↔ signals" table for ~80 names is **derived, not authored**: a script walks
  ticker_map → entity → its registered signals + chart_series → emits compact
  `web/public/data/stock_signal_map.json` (compute-once-ship-compact). The web app reads only
  this artifact, never signals.db or the models directly.

This keeps one generic mechanism: any future pipeline's entities become investable coverage by
adding rows to `ticker_map.json` — nothing else changes.

### EN-2 · Where things live

- **Same repo** (`india-credit-lens/`). The retail product consumes signals.db and the system
  models; a separate repo would fork the single source of truth. Revisit at rebrand (Week 6+)
  as a *rename*, never a split.
- **Call register:** append-only `analysis/call_register.json` — fields `id, date, claim,
  basis (signal_ids), review_date, status (open|right|wrong), resolution`. IDs are permanent
  (same rule as annotation IDs). Rendered by a public `web/` route `/register`. Numbers in
  claims must trace to signals.db — give the register its own Check-2g-style validator once
  the first calls are logged.
- **Release calendar:** `analysis/release_calendar.json` — fields `source, cadence,
  expected_day, publication_lag, url`. A data artifact, not prose. 🔧 drafts it via web
  research; 👤 signs off the dates (same A/B gate pattern as `detect_format.py`).
- **Web app v0 (Phase 2):** routes inside the existing `web/` Next.js app (e.g. `/stocks`),
  reusing AppShell + DLS components. Email magic-link auth = reactivate the dormant Clerk
  integration; do not add a new auth system.
- **SEBI guardrail, enforced deterministically:** before Signal Note #1 ships, add a forbidden-
  language lint to the note/content generators (buy/sell/target-price/accumulate/book-profit
  vocabulary → hard fail), in the spirit of `validate_content.py`. Judgment stays human;
  the floor is mechanical.

### EN-3 · Pricing (single source for all copy)

Standard paid tier: **₹1,999 per half-year** or **₹3,999/yr** (₹333/mo billed annually).
Founding members: **first 100 get the annual plan at ₹1,999/yr, locked for life** — a year at
the half-year price. All pricing copy anywhere derives from this paragraph.

### EN-4 · VAHAN/FADA ingestion = "source #3" of the §4 architecture

Follow the atm_pos template exactly: `analysis/pipelines/vahan/` + a manifest entry in
`core/gate.py`; Stage 0 detect-format → extract → validate → consolidate → L1 signal specs in
`registry.json` + a compute module in `signals/compute/`. No one-off scripts. This is
deliberately the "validate with source #3" test from `HANDOFF_TECH_QUALITY.md` §4 — if the
generic gate can't absorb it cleanly, that is a finding to fix in `core/`, not something to
work around per-pipeline.

### EN-5 · Division of labour

| 👤 User (never the model) | 🔧 Model |
|---|---|
| Create X/Substack accounts, post, reply-guy, collab asks | Release-calendar draft, register page + validator |
| Sign off calendar dates and date remaps | ticker_map.json + validator, stock_signal_map derivation |
| Pricing/launch decisions, SEBI final review of every note | Web app v0, digest automation, VAHAN pipeline, alert engine |
| Source new data files (XLSX/CSV downloads) | Note drafts, charts, X/LinkedIn packages via generators |

---

## Phase 0 — Aim (Weeks 1–2) · ~10 hrs total

1. **Define ICP precisely:** active Indian retail investor, direct-equity holder, already pays or would pay for screener.in/Trendlyne premium (₹3–5k/yr), lives on X-fintwit / YouTube / r/IndianStockMarket.
2. **Build the release calendar** — the content engine's heartbeat. Monthly: RBI SIBC, RBI ATM/POS+cards, GST collections (1st), auto retail VAHAN/FADA (~1st week), SIAM wholesale, EPFO payroll, TRAI subscribers, POSOCO/Grid-India power demand (daily→monthly), rail freight, DGCA traffic, trade data. *(Verify exact dates/lags in week 1.)*
3. **Pick the first 3 transmission maps** (already-built data only):
   - SIBC gold-loan credit → Muthoot/Manappuram/IIFL Fin
   - SIBC sectoral bank credit growth → specific PSU/private banks
   - ATM/POS + card spend → SBI Cards + consumption basket
4. **Stand up the public call register** — a single page: date, claim, data basis, review date, outcome (open/right/wrong). Empty is fine; it exists from day one.
5. **Branding decision deferred to Week 6** — publish under a working handle; don't burn week 1 on naming. (indiacreditlens.com is credit-scoped; the retail product is govt-data-scoped — likely a new name later.)

**Exit criteria:** calendar built, 3 maps chosen, register page live, X + Substack accounts created.

## Phase 1 — Prove the intelligence in public (Weeks 3–6) · ~5 hrs/wk content + 5 build

**Ship one "Signal Note" per week — 4 total.** Anatomy of a note (one sitting to produce, given pipelines):
- One chart from your own signals (traceable, branded)
- The transmission chain in 3 steps (data → sector mechanism → listed names affected)
- One **dated, checkable, quantified observation** (not advice): "Gold-loan credit grew 41% YoY for a 3rd month; the two listed pure-plays' combined AUM guidance implies X. Review: Sep SIBC release."
- Log it in the register. End with: follow + free Substack.

**Distribution mechanics (this is manufactured, not hoped for):**
- X thread + LinkedIn post per note (reuse your generator pipeline); post within 24h of the underlying govt release — ride the news window.
- 1 Reddit post/week in r/IndianStockMarket or r/DalalStreetTalks where rules allow (as analysis, not promo).
- Reply-guy strategy: 15 min/day replying with *data* to large fintwit accounts discussing your sectors — the highest-ROI cold-start channel.
- Ask 2–3 mid-size fintwit/finfluencer accounts for a quote-tweet/collab from note #3 (they need content; your charts are content).

**In parallel (build, ~5 hrs/wk):** repoint the causal model's entity layer to tickers; build the "stock ↔ signals" mapping table for ~80 liquid names covered by existing pipelines.

**🚦 DG1 (end of week 6):** across 4 notes — ≥100 Substack emails **or** ≥300 X followers **or** one note with clear organic spread (>20k impressions / picked up by a bigger account).
- Pass → Phase 2.
- Fail → the *packaging* is wrong, not the thesis: run 2 more weeks testing sharper formats (single-chart takes, "what the data said vs what the stock did" retrospectives) before touching product code.

## Phase 2 — Product v0: the Monitor (Weeks 7–10) · ~8 build / 4 content

Keep publishing weekly (never stop — cadence is the moat's metronome). Build the thinnest product:

- **Web app v0:** enter up to 3 tickers (free) → see which govt-data signals map to them, current state, next release date. Reads signals.db. No auth beyond email magic-link.
- **Weekly email digest** (automated from the pipeline): what released, what moved, what's next.
- **Add one new data source** — highest signal-per-effort: **VAHAN/FADA auto retail** (monthly, clean, maps to 10+ liquid tickers, huge retail interest). This proves the ingestion layer generalizes beyond RBI.
- Free tier limits set to create upgrade pressure: 3 tickers, current period only, no alerts.

**🚦 DG2 (end of week 10):** ≥300 emails on the digest and ≥25% weekly open rate. Fail → distribution problem; divert 4 more weeks to content/collabs before building paid.

## Phase 3 — First revenue (Weeks 11–13) · pricing test, not a launch

- **Paid tier at ₹1,999/half-year or ₹333/mo-billed-annually (₹3,999/yr)** — anchored just under screener premium. Includes: unlimited tickers, event-triggered alerts ("signal crossed threshold on your holding"), full history, the sector deep-dive PDF each month, and register access.
- Launch to the list only (no public pricing page yet). Founding-member framing: first 100 get the annual plan at ₹1,999/yr locked for life — a year at the half-year price (see EN-3).
- **🚦 DG3 (end of week 13): ≥20 paying subscribers.**
  - ≥20 → real. Scale content cadence, add sources, plan the ₹1cr-trigger roadmap (≈4,000–5,000 subs).
  - 5–19 → price/packaging iteration, one more cycle.
  - <5 with a 500+ engaged list → the willingness-to-pay hypothesis is wrong for this ICP; stop and reassess *before* building more. (This is the honest kill-switch.)

---

## Data-source expansion ladder (post-90-day, ranked by signal-per-effort)

1. ✅ RBI SIBC, ATM/POS (built) → 2. VAHAN/FADA autos (wk 7–10) → 3. GST collections → 4. TRAI telecom subs → 5. EPFO payroll → 6. POSOCO power demand → 7. Rail freight + ports cargo → 8. DGCA aviation → 9. Trade (commerce ministry) → 10. Govt capex/tenders → infra names.

Each new source = new sectors covered = new content surface = new subscriber pool. The compounding loop.

## What is explicitly OUT for 90 days

- No mobile app, no portfolio import/broker integration, no Hindi, no YouTube (until text formats prove), no SaaS for institutions (conflict), no buy/sell calls (SEBI), no rebrand debate before Week 6, **no new strategy documents** — the next artifact after this file is Signal Note #1.

## Scoreboard (review every Sunday, 15 min)

| Metric | Wk 6 gate | Wk 10 gate | Wk 13 gate |
|---|---|---|---|
| Signal Notes shipped | 4 | 8 | 11 |
| Substack emails | 100 | 300 | 500 |
| Paying subs | — | — | **20** |
| Register: calls logged / resolved | 4 / 0 | 8 / 1–2 | 11 / 3+ |
