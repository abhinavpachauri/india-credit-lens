# Dashboard Read-Mode — Design Spec v0.1 (DRAFT for approval)

> Status: **design only, no code**. Authoring rule: ASCII layout → explicit approval → implement.
> Supersedes the design-discussion block in `CLAUDE.local.md` (2026-07-21). Nothing here changes a
> ground-truth gate — this is a **presentation-layer** redesign. Check 2g / Stage 4c / 4f untouched.
> Companion: `DISTRIBUTION_SPEC.md` (the same curation engine, a different surface).

---

## 1. Why — the problem, measured (not estimated)

Both dashboards render **every signal as its own card, in generation order, with no ranking anywhere
in the web layer** (only sort in `components/`+`lib/` is Top-N banks by value, `lib/atm_pos_data.ts:145`).

- SIBC = **84 insights** over 7 sections (personalLoans **23**, industryByType **15**).
- Payments = **29 insights** over 3 groups.
- `/opportunities` = **20 items** (cross-system + per-pipeline).

"Too many cards" is **three different problems**. Ranking alone fixes none of them:

| # | Problem | Evidence | Fix plane |
|---|---|---|---|
| 1 | **Card unit is the signal, not the subject.** Reader asks "what's happening with credit cards?"; answer is spread over 4 carousel positions. | 84 SIBC cards → 36 subjects, 26 multi-card (credit cards 4, gold loans 3). One-signal-one-card was a *compute-layer* convention that leaked into presentation. | Subjects plane (nest) |
| 2 | **Much of it isn't news.** "Power is 57% of infrastructure" is true every month. | ~12 of 15 Industry-by-Type cards are structural. A different *class*, not a lower rank. | Composition plane (demote to caption) |
| 3 | **Only the residue is a ranking problem.** | est. 15–25 cards, not 131. | Read plane (rank) |

**Core principle:** one card per signal is correct for the **ground truth** (one card = one traceable
value; keeps Check 2g / Stage 4c honest). It is wrong for the **reader**. So we **nest and rank at the
presentation layer, and never merge cards** — every existing card stays addressable and individually
gated.

---

## 2. The three planes

The redesign replaces "one flat carousel per section" with three planes that answer three different
reader questions.

| Plane | Reader question | Source | Render |
|---|---|---|---|
| **The read** | *What changed this month?* | `is_news.ranked()` over the section's signals, floor 2.0 | Ranked list above the chart, ≤ ~3–5 per pipeline |
| **Subjects** | *What's happening with X?* | subject resolver (`effect.highlight` SIBC / `effect.focusCard` payments) | Accordion; cards nest under their subject; **all 84 stay addressable** |
| **Composition** | *What's the structure?* | share/structural signals (`csv_*_share`, distributions) | **Caption on the Distribution tab** — NOT cards. The distribution chart already *is* the composition plane. |

Two facts already in the code (reuse, don't rebuild):
- **Subject resolution already exists per pipeline:** SIBC `effect.highlight`, payments
  `effect.focusCard` (`credit_cards`, `cc_ecom`). One interface, two resolvers — same shape as the
  chart-highlight path today.
- **`is_news.py` is the ranking engine**, built for the newsletter, explicitly designed to be reused
  here. `select_reads(k, floor)` already picks reads; `ranked()` returns the full scored list.

---

## 3. The plane classifier — the one net-new compute (measured, AI PM-gated)

`categories.py` **cannot** classify the planes (it answers *which question* a signal asks, not *does it
change*): C1 holds both `csv_sector_yoy` (pure delta) and `csv_sector_share` (pure structure). The
read↔composition split needs its **own rule**, and per the standing AI PM rule it **ships with a
measured catch / false-rejection rate, not before**.

- **Read (news):** `is_news.score ≥ 2.0` (clears a strong factor — record / regime-flip / magnitude).
  Engine done; already `--measure`d (template-reject 100%, catch 54.5% by design — magnitude-blind).
- **Composition (structural):** the residue — a signal whose trailing-12m range sits inside its
  per-unit materiality band **and** whose status has been stable (candidate rule; both computable from
  signals.db). This is the classifier to **build + measure** (AI PM topic #1 / #2). Do not ship it
  without the number.
- **Subject:** everything is addressable in the accordion regardless of plane — the classifier only
  decides what gets *promoted* (read) vs *demoted* (caption). Nothing is hidden.

---

## 4. Depth ladder → the paid seam (this is where Opportunities lands)

Depth maps onto the pipeline's **own** layer architecture, so the paid seam falls out of the
architecture instead of being invented for it (same pattern as `OPPORTUNITIES_GATED`):

```
  Brief   →  L1   the read line + value          (headline, always free)
  Full    →  L1+  the card body + inference chain (basis.inferences / reasoning.chain)
  Deep ⌁  →  L2/L3  why it moved + what it opens   (opportunities, forces, loops, constraints)
```

> **SUPERSEDED 2026-08-12 — Option A was taken after all.** The reasoning below stands as the
> record of why B looked right at the time, and the objection that overturned it is worth keeping:
> *a separate surface turns a **depth** into a **category***. An opportunity is not a different
> kind of thing from an insight — it is a deeper reading of the same subject, and giving it its
> own page told the reader there was another section rather than showing them another layer.
> Option A's stated cost ("loses the cross-system page that no single pipeline can produce") was
> answered rather than accepted: cross-system findings now attach to every dimension holding one
> of their member signals, each with the local measurement that anchors it there. The register
> changed with it — we report what the data shows and why, we do not suggest moves. See §12.1.

**Decision — where Opportunities live (recommend Option B):**

- **A — Fold fully into the dashboard, kill `/opportunities`.** Loses the cross-system page that no
  single pipeline can produce (constructs, eco-edges, cc-balance constraint). ✗
- **B — Opportunities = the `Deep ⌁` (L2/L3) plane of the *same* dashboard, per subject; `/opportunities`
  stays as the cross-system standalone.** ✓ **Recommended.** A subject's `Deep ⌁` expansion pulls its
  live opportunity/risk from `opportunities_feed.json` (already keyed to entities). The dashboard
  becomes the *pull* surface for L2/L3; `/opportunities` remains the *cross-system* view. One engine,
  two entry points, no new compute.
- **C — Keep them fully separate (status quo).** Two disconnected surfaces; the reader never sees "cards
  fell → here's the opening that creates" in one place. ✗

**The paid pivot, deferred honestly:** build the depth seam now (`Deep ⌁` is a distinct render tier),
**gate nothing yet.** At <10 visitors/day, gating fights reach — same call already made for
`OPPORTUNITIES_GATED` (public, Clerk dormant). When users arrive, `Deep ⌁` flips behind the *existing*
`NEXT_PUBLIC_GATE_*` flag with **zero restructuring**. "Pivot later when we have users" = the seam is
architected, the gate is a one-line env flip. **Revisit trigger = real signups, not a date.**

---

## 5. Information hierarchy (read this before the wireframe)

The page answers **three reader questions in priority order**. Prominence = position: Tier 1 is what
the eye hits first. Everything is still reachable — the hierarchy decides *emphasis*, never *access*.

```
                        ONE PIPELINE PAGE  (e.g. SIBC · Credit deployment)

 ┌── TIER 1 · THE READ ───────────────────────────── most prominent · top ──┐
 │  Q: "What changed this month?"                                            │
 │  The 3–5 signals that actually MOVED. Ranked, not generation order.       │
 │  Source: is_news.ranked()   glyphs: ▲ rose   ▼ fell   ⌁ crossed a line    │
 └───────────────────────────────────────────────────────────────────────────┘
                    │  click a read  ─────────────────┐
                    ▼                        it DRIVES ▼
 ┌── TIER 2 · THE CHART ──────────────────────────── centre · always on ────┐
 │  Q: "Show me the evidence."                                               │
 │  Trend / Distribution of the selected read OR subject.                    │
 │  COMPOSITION (structure — "Power is 57% of infra") lives HERE as a        │
 │  one-line caption, NOT as its own cards. The chart already IS structure.  │
 └───────────────────────────────────────────────────────────────────────────┘
                    ▲  select a subject  ─────────────┘
                    │
 ┌── TIER 3 · SUBJECTS ───────────────────────────── drill-down · retains all ┐
 │  Q: "What's happening with X?"                                            │
 │  Accordion of ~36 subjects; the 84 cards NEST under them (never merged).  │
 │  The read PROMOTES a few; the accordion RETAINS every one. Nothing hidden.│
 └───────────────────────────────────────────────────────────────────────────┘

 DEPTH — a control that cross-cuts all three tiers (maps to the pipeline's own layers):

        Brief ─────────── Full ─────────── Deep ⌁
         L1                L1+               L2 / L3
        headline + value  + inference chain  + the opening/risk it drives
        (free)            (free)             (opportunities_feed · paid seam later)
```

The three planes from §2 are exactly these three tiers. **Read = rank · Chart = evidence + composition
caption · Subjects = nest.** Depth is orthogonal: it deepens whatever tier you're looking at.

---

## 6. Layout — desktop wireframe (SIBC shown; payments identical shape)

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ICL · SIBC Credit deployment                    Apr 2026 · released May 29 │  ← AppShell header
├──────────────────────────────────────────────────────────────────────────┤
│ [ ● Read    ○ Explore ]                                                    │  ← PAGE MODE toggle
├──────────────────────────────────────────────────────────────────────────┤
│ THE READ · 3 moved this month                       Brief · Full · Deep ⌁ │  ← TIER 1 + depth
│ ┌──────────────────────────────────────────────────────────────────────┐ │
│ │ ▲  Large corporates     +14.4% YoY · fastest in 11 months            │ │  ranked by is_news;
│ │ ▼  Credit-card o/s        fell · 2nd straight month                  │ │  click → drives chart
│ │ ⌁  Gold loans             crossed 7% of personal loans               │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
├─────────────────────────┬────────────────────────────────────────────────┤
│ SUBJECTS      (Tier 3)  │ CHART  (Tier 2)          📈 Trend  📊 Distrib.  │  ← controls ALWAYS
│ ─────────────────────── │ ┌────────────────────────────────────────────┐ │    visible (fixes the
│ ▸ Bank credit           │ │                                            │ │    AGENTS.md step-4
│ ▾ Personal loans   (23) │ │            selected series                 │ │    "hidden in insights
│   ▾ Credit cards    (4)●─┼─▶                                           │ │    mode" conflict)
│     ▼ outstanding       │ │                                            │ │
│     ▲ YoY               │ └────────────────────────────────────────────┘ │
│     · e-com share       │ Composition:  Power 57 · Roads 18 · Telecom 9 % │  ← caption, not cards
│     · per-card balance  │                                                │
│   ▸ Gold loans      (3) │ ⌁ DEEP  (only when depth = Deep)                │
│ ▸ Industry (by size)    │ ┌────────────────────────────────────────────┐ │
│ ▸ Services              │ │ Opening: services-entry · active           │ │  ← from opportunities_
│ ▸ Priority sector       │ │ Why → 3-step computed basis                │ │    feed.json, keyed to
│ ▸ Industry (by type)    │ └────────────────────────────────────────────┘ │    the subject
└─────────────────────────┴────────────────────────────────────────────────┘
   ~⅓ width                  ~⅔ width
```

Proportions & rules:
- **Tier 1 (full width, top)** — max ~5 rows. Overflow is **not** "…and 79 more"; the rest live in
  Subjects. A row = glyph + subject + one clause.
- **Tier 3 (~⅓, left)** — accordion; indent = hierarchy (Personal loans ▸ Credit cards ▸ its 4
  signals). Count badge on collapsed parents. Selecting any leaf highlights its series in the chart.
- **Tier 2 (~⅔, right)** — controls **always visible**; the read *drives* the chart, never hides it. A
  user chart-touch overrides the mode but never dismisses the read. Composition = one caption line.
- `⌁ DEEP` block appears only at depth = Deep, per selected subject.

---

## 7. Layout — one subject expanded (the nest + depth, the least obvious part)

Selecting **Credit cards** in the accordion. This is what "cards nest, never merge" means in practice:
its 4 signals stay 4 individually-gated cards, but they collapse under one subject and deepen together.

```
 SUBJECT ▾ Credit cards                              depth: Brief · Full · Deep ⌁
 ────────────────────────────────────────────────────────────────────────────────
                              Brief          Full                    Deep ⌁
  ▼ outstanding      →  ▼ o/s fell 2nd mo   + body + inference       + risk_cc_market_
  ▲ YoY              →  ▲ +8.1% YoY         chain (basis.inferences)   concentration
  · e-com share      →  · 34% e-com          — one expander per        · the opening this
  · per-card balance →  · ₹24.9k / card        card, still 1:1 gated     subject drives
                                                                        (opportunities_feed)
  each row is still ONE signal = ONE Check-2g-traceable card. Nesting is visual only.
```

- **Brief** = one line per signal (the read glyph + value). Free.
- **Full** = each line expands to its card body + `basis.inferences` chain. Free.
- **Deep ⌁** = the subject's live opening/risk from `opportunities_feed.json` (Option B, §4). The paid
  seam — public now, one env flag away from gated later.

---

## 8. Layout — mobile (375px, stacked; test before "done")

```
┌────────────────────────────┐
│ ICL · SIBC   Apr 2026       │  header
├────────────────────────────┤
│ THE READ                    │
│  [Brief][Full][Deep⌁]       │  depth segmented control
│ ┌────────────────────────┐  │
│ │▲ Large corp +14.4% YoY │  │  read cards swipe H (existing
│ │  fastest in 11 months  │  │  InsightCard swipe pattern)
│ └────────────────────────┘  │  ● ○ ○   1 of 3
├────────────────────────────┤
│ 📈 Trend   📊 Distribution  │  controls (always visible)
│ ┌────────────────────────┐  │
│ │      chart              │  │  chart of the active read/subject
│ └────────────────────────┘  │
│ Power 57% · Roads 18% …     │  composition caption
├────────────────────────────┤
│ SUBJECTS                ▾   │  accordion collapses below the fold
│  ▸ Bank credit              │  (tap a subject → scrolls chart up,
│  ▾ Personal loans      (23) │   loads its series)
│    ▸ Credit cards       (4) │
└────────────────────────────┘
```

Mobile keeps the **read → chart → subjects** vertical order (read is the value proposition; subjects
are the drill-down). Reuse the existing `InsightCard` horizontal swipe for the read stack.

---

## 9. What changes vs what does not

**Changes (presentation only):**
- New `useReadMode(section)` layer over the existing `useSectionInsights` — adds `ranked` (from
  is_news), `subjects` (grouped by resolver), `plane` per card.
- Controls card **no longer hidden in insights mode** (AGENTS.md step 4) — the read *drives*
  `preferredMode` + `effect.highlight`; a user chart-touch overrides the mode but **never dismisses the
  read**. This is the one behavioural conflict to resolve at build.
- Subjects accordion component (nest, don't merge).
- Depth ladder render tier; `Deep ⌁` pulls from `opportunities_feed.json`.

**Does NOT change:**
- Any ground-truth gate (Check 2g, Stage 4c, 4f) — cards nest, never merge; each stays 1:1 with its
  signal and individually traceable.
- The compute layer, signals.db, the eval path, the distribution surface.
- Explore mode of each pipeline (see §9 — stays as-is).

---

## 10. Measurement obligations (AI PM topic #1/#2, non-negotiable)

No classifier ships on prose. Before/after, logged to `ai_pm_register.json`:
- **Plane classifier** — catch rate (a known structural card is demoted) + false-rejection rate (a
  known news card is wrongly demoted). Reuse `is_news.measure()` as the harness template.
- **Read selector** — the `is_news` catch/false-rej already measured; re-report on the dashboard's
  candidate set.
- **Prominence formula** — inputs available: is_news score, `proximity.py` distance + `typical_move`,
  record/extreme, share materiality. Pick the weighting, then measure it doesn't invert obvious cases.

---

## 11. Read ⇄ Explore — two modes on one page

The three tiers are the **Read** mode: a curated "what changed" view. It does **not** replace
exploration — a page-level toggle sits under the header (`● Read  ○ Explore`):

- **Read (default)** — the three tiers (§5). The curation layer.
- **Explore** — today's dashboard **exactly as it is**: every section, all controls/filters, the full
  card set in generation order. Untouched by this spec. It is the escape hatch for "I want to see
  everything myself."

Read mode is a lens *over* the same data Explore already renders — not a fork of it. Both read from the
same annotations JSON + chart series; Read adds ranking/nesting, Explore adds nothing and removes
nothing. **Mode is sticky** (localStorage, like depth and `icl-dark`).

### Decided / out of scope (from the 2026-07-21 discussion — do not re-litigate)

- **Explore mode stays AS-IS.** Each pipeline renders its own data its own way; the design system stays
  shared. No series index, no cross-pipeline basket, no free-form picker. Revisit trigger = several more
  pipelines ingested ("design on 2, validate with #3"). Known drift to fix then: payments ships
  precomputed `atm_pos_chart_series.json` while SIBC still ships raw CSV client-side — two chart-data
  mechanisms.
- **DROPPED — ✎ "note a finding" on the dashboard.** Public page, no login; authoring belongs in S4.

---

## 12. Decisions — RESOLVED (2026-07-31)

1. **Opportunities placement — ~~Option B~~ → Option A (revised 2026-08-12).** The Deep plane is
   in-dashboard and `/opportunities` is **retired** (archived; the route redirects to `/`). See
   §12.1 for what changed and why.
2. **Depth stickiness — sticky.** ✅ localStorage, same pattern as `icl-dark`. Page mode (Read/Explore)
   is sticky too. (§11)
3. **Prominence weighting — `is_news.score` alone for v1.** ✅ Order the read by the existing score;
   do **not** build a blended materiality/proximity formula speculatively. Review the ordering on live
   data; add a materiality tiebreak only if it reads wrong. (Measure-first, §8.)
4. **Read-plane cap — floor + soft cap.** ✅ Show all rows with `is_news.score ≥ 2.0`, visibly capped at
   ~5 with a "+N more moved →" expander. Never pads a quiet month, never buries a busy one.
5. **Deep inline vs page — ~~inline first, retire only after review~~ → retired (2026-08-12).** The
   review happened and found the fold was never actually inline: it rendered a list of *links out*
   to the page, so the condition for retiring was never met and the content had no home but the
   page. It is now genuinely inline. Original text below.
   ~~✅ v1 = `⌁ Deep` expands **inline** under the subject; `/opportunities` **stays**. Decision to retire the standalone
   page is a follow-up, gated on "does the inline fold read cleanly" — taken deliberately, not now.

---

## 13. Build order (after ASCII approval)

1. ✅ **DONE (2026-07-31)** — the classifier + its measurement (§3, §8), the gate on everything else.
   `analysis/signals/planes.py` (read/composition/subject; reuses is_news + proximity). Measured
   **catch 100% / false-reject 0%**, partition read 73 / composition 19 / subject 100. 19 unit tests
   (`tests/test_planes.py`), logged to ai_pm_register topic #1 (26 measurements). Two design
   corrections earned by the measurement (share pp-band; dropped the status-stable gate — see the
   module docstring).
2. ✅ **DONE (2026-07-31)** — the data bridge. `analysis/signals/stamp_planes.py` precomputes each
   card's plane into a compact **sidecar** (compute-once-ship-compact); wired into the SIBC gate
   (stage 5.6) + `check_derived_fresh` (freshness-guarded like other derived artifacts). SIBC gate
   ALL STAGES PASSED.

   **DATA CONTRACT for the web layer** — join on card `id`:
   ```
   web/public/data/{sibc,atm_pos}_planes.json
     { "_meta": {...},
       "planes": { "<card id>": { "plane": "read"|"composition"|"subject",
                                  "news_score": <float|null>,  // is_news score; ranks the read tier
                                  "subject": "<chart series / focusCard>",
                                  "reason": "record"|"reversal"|"surge"|"shift"|null, // read chip
                                  "direction": "up"|"down"|"flat"|null } } }          // read glyph
   ```
   Every card in `sibc_l1_annotations.json` / `atm_pos_insights.json` has an entry. `plane` drives the
   tier; `news_score` orders the read tier (floor 2.0 + soft cap ~5); `subject` groups the accordion;
   `reason`/`direction` populate the read card's chip + ▲▼ glyph (reads only, else null).

--- everything below is the WEB build (next chunk — React/Next.js, presentation only) ---

3. `useReadMode` data layer over `useSectionInsights` — join the planes sidecar onto the cards; expose
   `reads` (plane==read, sorted by news_score, floor+cap), `subjects` (grouped by `subject`),
   `composition` (plane==composition → caption text).
4. **Page-level `Read ⇄ Explore` toggle** (§11) — Explore renders today's dashboard unchanged; Read
   renders the tiers. Mode sticky in localStorage.
5. Subjects accordion (nest) + read plane render (floor + soft cap); controls-always-visible refactor
   (§7 conflict).
6. Depth ladder (Brief/Full/Deep, sticky) + `Deep ⌁` **inline** wiring to `opportunities_feed.json`
   (Option B, decision 5).
7. Payments parity (same shape, `effect.focusCard` resolver) — MUST follow §14 representation exactly.
8. Measure, log to ai_pm_register, then `npm run build` + preview at 375px before push.

---

## 14. Representation — the LOCKED visual layout (Option A · both pipelines) ⭐

The reference every read surface renders to — SIBC first, **payments must match this** so the two
dashboards read as one system. Presentation only; the tiers (§5) and planes (§3) are unchanged.

### 14.1 Shell + panes (fixes the ~30% desktop whitespace)

- **Read mode shell = `max-w-[1440px] px-6`** (Explore stays `max-w-5xl` — a single column doesn't want
  1440px). This roughly halves today's dead side margins.
- **Two-pane on `lg`+**: left **rail 360px fixed**, right **detail `flex-1`** (chart pane ≈ 1040px on a
  1440 canvas — far bigger than today's whole column), `gap-6`, detail is `lg:sticky lg:top-6`.
- **Below `lg` → ONE column**, source order **reads → detail → subjects** (tap a read, its detail is the
  next block). Achieved with CSS-grid placement so mobile needs no separate markup. The 360px is a
  desktop-only track; it never applies on mobile. Everything wraps, nothing truncates, test at 375px.

```
 max-w-[1440px]  ·  lg:grid-cols-[360px_minmax(0,1fr)]  gap-6
┌──────────────────────────┬────────────────────────────────────────────────┐
│ LEFT RAIL (360px)        │ DETAIL (flex-1, sticky)                          │
│ THE READ · N moved       │ {Section kicker}                                 │
│ ┌──────────────────────┐ │ {Card title}                                    │
│ │▎ Subject      VALUE   │ │ ┌────────────────────────────────────────────┐ │
│ │▎ ▲ record · Absolute  │ │ │  chart — subject series highlighted        │ │
│ └──────────────────────┘ │ └────────────────────────────────────────────┘ │
│ … cards …  +N more ▾     │ Composition: … (muted one-liner)                │
│ ──────────               │ {body}    Why this reads → ① ② ③   ⌁ Opens: … → │
│ SUBJECTS (accordion)     │                                                 │
└──────────────────────────┴────────────────────────────────────────────────┘
   mobile: reads → detail → subjects, stacked, full width
```

### 14.2 Colour language — **colour = section** (reuse `SEC_COLORS`, no new colours)

A card's section colour is also its chart-line colour, so a purple Services card *is* the purple line.
Colour appears ONLY as: read-card left spine, the headline value, the detail kicker, the chain number
markers, the Deep link, and the subject-row spine. Everything else uses the two neutral tokens
(`--font`, `--font-muted`) over `--bg-card`. Works in both themes (tint the section colour over the card
bg; selected read card bg = section @ ~8% light / ~16% dark).

### 14.3 Type scale (readable desktop AND mobile — headlines a touch larger)

| Element | Size / weight | Colour |
|---|---|---|
| Rail eyebrow ("THE READ · N moved") | 12px / 600 / uppercase / tracking 0.06em | `--font-muted` |
| Read-card subject | 14px / 500 | `--font` |
| Read-card **value** | 17px / 700 | **section** |
| Read-card sub-line (`▲ reason · mode`) | 12px / 500 | `--font-muted` (glyph tinted) |
| Detail kicker (section name) | 12px / 600 / uppercase | **section** |
| Detail title | 22px / 700 | `--font` |
| Composition caption | 13px / 400 | `--font-muted` |
| Detail body | 15px / 400 / lh 1.6 | `--font` |
| "Why this reads" — heading / steps | 12px·600 / 14px·400 | steps `--font`; ①②③ markers **section** |
| Deep opening link | 14px / 600 | **section** |
| Subject accordion — title / count | 14px·600 / 12px | `--font`; row spine **section** |

### 14.4 Read card anatomy (better than a plain tag)

```
 idle                             selected
┌────────────────────────────┐   ┌────────────────────────────┐
│▎ Services          20.4%   │   │▎ Services          20.4%   │  ▎ 3px spine = section
│▎ ▲ record · YoY            │   │▎ ▲ record · YoY            │  value 17px 700 in section colour
└────────────────────────────┘   └━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛  selected: bg section@8% + bold spine
```

- **Section = colour** (spine + value tint), NOT a repeated text pill.
- **Chip = why it surfaced**, from the sidecar `reason`: `▲/▼ record · ⇄ reversal · ⚡ surge · • shift`
  (glyph = `direction`), then the chart `mode`. This tells the reader *why it's news* — a section name
  never does. The section name lives once, large, on the detail kicker.

### 14.8 Navigation — three controls for three navs (chip strip)

The rail must NOT do all three navigations at once (browse items + switch dimension + be a 7-way
accordion) — that overloads it. Each nav gets one control:

```
 ‹ Credit dashboard                                        Brief · Full · Deep⌁     ← nav 3 + depth
 ‹ [★ What moved ·▲27][🏦 Bank Credit ·▲5][📊 Main Sectors ·▲2][🏭…][🛎…][💳…] ›   ← nav 2 (chips)
 ┌───────────────────────────────┬────────────────────────────────────────────┐
 │ PERSONAL LOANS · 29 · ▲11      │  detail (kicker / title / chart / body …)   │
 │ ▾ Credit cards                 │                                             │   ← nav 1: the rail =
 │   ▲ Advances 8.3% YoY  ●       │                                             │      ONE list's items
 │ … only this dimension's cards… │                                             │
 └───────────────────────────────┴────────────────────────────────────────────┘
```

- **nav 1 · between items** — the left rail shows **one list only**: either a dimension's cards
  (subjects → cards, ▲ on movers) or the reads. Clicking a card changes the detail; the list stays.
- **nav 2 · switch list** — the **horizontal chip strip**: `★ What moved` (the reads, pinned first) +
  one chip per dimension, coloured by section, active chip filled, `▲ K` badge. It **does not wrap** —
  it scrolls horizontally with `‹ ›` arrows (`overflow-x:auto`, scrollbar hidden; the active chip
  auto-scrolls into view). The reads are just another selectable list, reachable from anywhere.
- **nav 3 · to the dashboard** — the `‹ {homeLabel}` breadcrumb → the grid front door.

This **supersedes the in-rail dimension accordion** (and the §14.7 "single-open on select" rule, now
moot — there is no accordion). Payments uses the same strip: `★ What moved` + cc/dc/infra chips.

### 14.6 Grid front-door (the landing state)

Read mode opens on a **grid overview**, not straight into the detail — this is what makes the
dimensions visibly a browsable layer (the earlier plain list buried them). Two states, one component:

- **GRID (landing, `view="grid"`):** the reads ("what changed") as a responsive card grid on top
  (`sm:2 / lg:3` cols), then **`Browse · N dimensions · M insights`** and the dimensions as a card grid
  (`2 / sm:3 / lg:4`). Each **dimension card** = section-colour spine + icon + title + `N insights` and,
  when it has news, `▲ K moved` in the section colour. Nothing selected, no chart mounted.
- **DETAIL (`view="detail"`):** click any read or dimension card → **220ms crossfade** into the §14.1
  two-pane. A **`‹ All dimensions`** link returns to the grid.

Why a plain crossfade suffices (not a layout-morph): the detail rail *already* carries the dimension
directory, so you switch dimensions **in the rail**, not by bouncing back to the grid — the grid is a
front door passed through ~once per session. Entering a dimension opens **only** that one in the rail
directory (`openSections = {entered}`), so the rail reads as a directory, not a wall of expanded cards.
No `framer-motion`; the chart simply mounts fresh in the detail pane (a morph is where jank would live).
If frequent overview↔detail bouncing is ever wanted, add `framer-motion` `layout` for a glide — deferred.

### 14.7 Interaction + polish rules (apply to BOTH pipelines)

- **Hover:** every clickable card lifts/highlights — read cards + rail rows get `box-shadow` + a
  section-colour border on hover; dimension tiles also translateY(-2px); the back link + Deep links
  darken. **Card border/spine/background MUST live in the CSS class, NOT inline** — an inline `border`
  or `box-shadow` wins specificity over the `:hover` rule and silently kills the hover (this bit us).
  Only the dynamic `--sec` (section colour) + `--sel` (selected tint) custom props go inline; the
  `.rm-card` / `.rm-flat` classes read them, and `.sel` marks the selected state.
- **Single-open on select.** Clicking a card (read or rail row) sets the open dimension set to JUST that
  card's dimension — the other dimensions collapse. (Expanding via a dimension *header* still allows
  multiple open for browsing; committing to a card focuses one.) Picking also scrolls the detail/chart
  into view (all viewports), since the pick may come from deep in the rail.
- **Grid resets the reads.** The "+N more" reads expansion is local to a visit — returning to the grid
  front door resets it to the top-5 overview.
- **Home label:** the back link reads **`‹ {homeLabel}`** — a prop: "Credit dashboard" (SIBC),
  "Payments dashboard" (payments). Never hard-code "All dimensions".
- **Detail is NOT sticky.** The detail pane scrolls with its own content so chart → composition → body
  → why read as one motion. (Sticky pinned a tall pane and cut off the body, and made scrolling feel
  like it moved the left rail — removed.)
- **Left column bundles reads + dimensions** in one flex column (`lg:grid-cols-[360px_1fr]`, left =
  reads then the dimension directory, right = detail). Do NOT use a `row-span` detail with the
  dimensions in a separate grid row — a detail taller than the rail inflates the row and strands the
  dimensions far down with a blank gap. A short sidebar with clean whitespace beneath it is correct.
- **Enter on the news, not the first card.** Opening a dimension selects its top *read* if it has one,
  else its first card — so a "3 moved" dimension lands on something that moved.
- **Mark the movers.** Inside an expanded dimension, cards that are reads carry a leading **▲** in the
  section colour and bold weight; the dimension header shows a **`▲ K`** badge. Structural/quiet cards
  are unmarked — so "which of these actually moved" is visible without opening each.
- **Depth must be self-evident.** The Brief/Full/Deep ladder was invisible in use (default Full, and
  Deep changed nothing where there was no opportunity). Three rules: (1) a live descriptor under the
  ladder — `Detail: chart only` / `with the reasoning` / `with what it opens`; (2) **Deep is only
  offered where an opportunity exists** — elsewhere the ladder shows Brief/Full only, and a sticky
  `deep` preference renders as Full (`effDepth`); (3) **on a depth increase, scroll the newly-revealed
  block into view and flash it** (Web Animations background pulse) so the reader sees what the level
  added. Brief = title+chart+composition · Full = +body+"Why this reads" · Deep = +"What this opens".
- **No chart controls in read mode — a static view label.** The insight's `preferredMode` already
  overrides the mode radios (they were dead), so the whole control strip is gone. Instead show one muted
  label of what's displayed — `📈 Trend · YoY %` / `📈 Trend · ₹ absolute` / `📈 Trend · FY cumulative`
  / `📊 Distribution · % share` — derived from the insight. The chart renders the insight's own view;
  the series legend stays display-only. Exploring other modes is what Explore mode is for.

### 14.5 Payments binding (so parity is mechanical, not a redesign)

Payments renders the SAME three DOM blocks + §14.1 shell + §14.2–14.4 styling. Only the resolvers
differ: subject = `effect.focusCard`; section colour = `GROUP_ACCENT[group]` (cc blue / dc green / infra
orange) instead of `SEC_COLORS`; cards come from the flat `atm_pos_insights.json` grouped by cc/dc/infra;
chart = `AtmPosTrendChart`. Everything else — spine/value/chip/kicker/type scale/pane grid — is shared.

---

## 12.1 The deeper reading, in the insight (2026-08-12)

`/opportunities` is retired. Layer 2 findings now render at the `Deep ⌁` rung of the dimension
they belong to, and the page redirects to `/` (a published deep-read post links to the old URL).

**Why.** A separate surface made a *depth* look like a *category*. The reader was told there was
another section rather than shown another layer of what they were already reading — and the same
framing pushed the machine into suggesting moves, which is not the register this platform wants.
We stay at analyst level: what the data shows, and the mechanism behind it.

**Register.** The model keeps `tier: opportunity | risk` — that is how the system model classifies
a node, and rewriting it would touch the spec, the validators and S3 for no reader benefit. It is
deliberately *not* what the reader sees:

| Was | Is | Why |
|---|---|---|
| `⌁ What this opens` | **Deeper reading** | states depth, not action |
| Opportunity / Risk badge | *dropped* | model vocabulary, not reader vocabulary |
| `For lenders` | **The mechanism** | explains rather than advises |
| `Why — computed basis` | **How we know** | plainer, same content |
| — | `· active` / `· watch` chip | descriptive of driver firing, not a call |

**Cross-system findings** attach to every dimension holding one of their member signals, each with
an anchor line — "On this dimension: Vehicle Loans, +17.3% YoY" — so five appearances of one
construct are five locally specific readings rather than the same paragraph five times. They sit
under a *Read together with credit/payments* sub-heading, which names why something spanning both
datasets is showing up here.

**What did not change.** Nothing in `analysis/`. The chain from system model → S3 →
`derive_opportunities` → feed → narrative is untouched, and Check 4f still validates every number
in every finding. This was a presentation change end to end.

**Gating** moved from route to rung: `OPPORTUNITIES_GATED` now hides the `Deep ⌁` step rather than
a URL. The reader reaches the subject they care about and finds another layer, instead of being
told about a section they cannot open.

**Explore mode** no longer surfaces L2 at all — no teaser, and the CTA strip's opportunity count is
zero. Explore is the raw-series surface; depth belongs to read.

**One bug found while verifying**, same class as the long-form `up, -2.6%` issue fixed in July:
`BasisBlock` drew its arrow from `member.direction`, which is the member's *contribution* to the
construct, not the sign of its number — so a contra-indicator or a member moving against the read
rendered as "Consumer Durables ▲ −0.6% YoY". The glyph now reads off the observed value (mirroring
`core.voice.observed_dir`), and a member whose observed direction opposes its contribution is
labelled *· moving against the read* rather than given an arrow that argues with the figure.

---

## 15. The card↔chart cut contract (v0.2 — DRAFT for approval, 2026-08-25) ⭐

> **Status: spec only, no code.** Two of the four sub-sections below (§15.6 render shapes) need
> ASCII approval before any chart code is written. §15.1–§15.5 and §15.7 are mechanism, not layout.
> Applies to **both pipelines by construction** — a per-section fix is explicitly out of scope.

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
aggregation* (§14.5), which is orthogonal to *which quantity*. A payments cut is therefore a pair —
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

> Arc 1 of `PLAN_2026-09-09.md`. **Rendering only.** Every number below is already computed,
> already gate-validated, and has never reached a browser.

### 16.1 The problem this answers

The top tier of read mode is *what is news*. This period that is **29 of 96** SIBC cards
(planes: 29 read / 17 composition / 50 subject; payments 9 / 1 / 22). Twenty-nine cards is
not an answer to "what is happening" — and in a quiet month the honest answer is *nothing
crossed the threshold*, which leaves the reader with a directory.

Meanwhile `system_state_{period}.json` computes, every ingestion, a **mix state per cut**:
`steered` / `drifting` / `contested` / `reallocating`, with `toward`, `away_from` and the
tilt in pp. It is validated by both gates and ships nowhere.

**So: add a tier above the reads. Do not redesign.** The §14 layout and the §15 cut contract
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
  │ ── no mix cut ──           │ │ ▲ 19.1% YoY · accelerating │ │ ▲ 20.0% YoY · accelerating │  ← ★ NEW
  │                            │ │ ⇢ steered → Services       │ │ ⇢ drifting → Medium        │  ← ★ NEW
  │                            │ │                            │ │                            │
  │ 9 insights      ▲ 4 moved  │ │ 13 insights     ▲ 5 moved  │ │ 10 insights     ▲ 4 moved  │
  └────────────────────────────┘ └────────────────────────────┘ └────────────────────────────┘
  ┌────────────────────────────┐ ┌────────────────────────────┐ ┌────────────────────────────┐
  │ 🛎️                         │ │ 💳                         │ │ ⭐                         │
  │ Services                   │ │ Personal Loans             │ │ Priority Sector            │
  │                            │ │                            │ │                            │
  │ ▲ 22.9% YoY · accelerating │ │ ▲ 16.2% YoY · steady pace  │ │ ── speed not published ──  │  ← honest
  │ ⇢ steered → NBFCs          │ │ ⇢ drifting → gold jewellery│ │ ⇢ drifting → Micro & Small │    absence
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

**Three honest absences visible on one page** — Bank Credit has no mix cut at all (it is the
top level: food vs non-food); Priority Sector is a memo lens with no total, so no speed exists
to publish; Industry by Type has a speed but no acceleration row. Each renders as an omission
or a dash, never a placeholder number.

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
| Main sectors | growing 19.1% YoY, accelerating | **steered** → Services (+5.8pp), away Personal Loans |
| Industry by size | growing 20.0% YoY, accelerating | drifting → Medium (+4.9pp), away Large |
| Industry by type | growing 20.0% YoY | drifting → All Engineering (+5.1pp), away Infrastructure |
| Services | growing 22.9% YoY, accelerating | **steered** → NBFCs (+17.2pp), away Other Services |
| Personal loans | growing 16.2% YoY, holding its pace | drifting → gold jewellery (+21.0pp), away Housing |
| Priority sector | *(no parent signal — omitted)* | drifting → Micro & Small (+7.2pp), away Housing |
| Infrastructure sub-types | *(no parent signal — omitted)* | **contested** |
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
3. **Two cuts have no parent-YoY signal** — PSL (a memo lens with no total, `additive: false`)
   and infrastructure sub-types (code `2.18` has no `csv_sector_yoy` entry). PSL is a genuine
   absence. Infra is one registry entry away; see the open decision in 16.10.

### 16.8 What was built

| Piece | File |
|---|---|
| The one renderer, both pipelines | `analysis/core/state_lines.py` |
| Two declared fields per cut | `MovementCut.parent_yoy` / `.parent_label` in `core/movement_cards.py`, filled in each pipeline's own `MOVEMENT_CUTS` |
| The parent signal infrastructure lacked | **`sibc-infra-yoy`** (code `2.18`, Statement 2) — registry 266 → 267, 11 periods backfilled |
| The sidecar | `analysis/signals/stamp_state.py` → `web/public/data/{pipeline}_state.json`, `--check` freshness guard |
| The gate stages | **5.9** `stamp_state` + **5.9b** `state_band` (`analysis/guards/validate_state_band.py`), both pipelines, placed after `system_state` because that is what computes the mix |
| The band | `StateBand` in `components/read/parts.tsx` — shared, so both pipelines inherit one design |
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

### 16.9 Constraints carried in (non-negotiable)

- The regime **word** only, never the coherence number.
- Never a derived number: a subtraction traces to nothing, so its operands are quoted instead.
- An absent input renders **nothing** — never a placeholder, a zero, or a neighbour's number.
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
