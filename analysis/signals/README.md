# `signals/` — signal store, compute engine, evaluation

The Layer-1 signal subsystem: a registry of signal specs, the SQLite fact store, the
deterministic compute engine, and the LLM evaluation layer.

## Store + catalog
- **`registry.json`** — universal signal catalog (L1/L2/L3 tagged; L1 signals carry compute
  specs). The single declaration of what each signal is.
- **`signals.db`** — **primary store** (SQLite): `(pipeline, period, metric_id, entity_type,
  entity_id)` fact table + `metric_ranges`. Binary — guarded by `guards/check_signal_freshness`.
- **`db.py`** — schema init + `refresh_ranges()`.

## Compute (`compute/`)
- **`engine.py`** — `run_append(pipeline, period, db, registry)` dispatches each signal to its
  method. **`sibc.py`** / **`atm_pos.py`** implement the 1a/1b/1c/1d methods (read the
  consolidated CSV; hot filter columns are `category`-dtype for speed). Both cache the CSV
  per process via `_load_df()`.

## Relational signal methods — rotation & divergence

Cross-segment L1 methods. Same architectural status as `csv_streak`/`csv_sector_scan_*`: registry
spec → deterministic compute → per-entity rows in `signals.db` → deterministic insight builders.
They serve the fixed monthly outputs in `FABLE_BRIEF_cross_segment_insights.md` (posts 2/3/4).
**Deterministic prose is the product** — the insight builders must emit publishable copy with zero
LLM calls (quality bar: `deterministic_scan_insight`).

### rotation — who is gaining/losing ground
`csv_sector_rotation` (SIBC) · `csv_category_rotation` (ATM/POS). METHOD_TYPE: `rotation`.

- **Compute:** for each child of `parent_code` (SIBC) / each `bank_category` on a metric (ATM/POS):
  `Δshare_pp = share(period) − share(period − window)`. `window: 12` **calendar months** default
  (annual — avoids seasonality). The window resolves calendar-wise (same month-end, `window` months
  earlier, which must exist in the CSV), **not** by positional index — the SIBC CSV has coverage
  gaps, and a positional 12-back would silently land 24 months out. Absent comparison month → no
  rows. Share basis reuses the existing share-scan computation at two periods — no parallel math.
- **Rows:** one per entity — `value = Δshare_pp` (unit `pp`), signed, sorted desc; `status` via
  `status_rules` (default: `> +0.15` strengthening / `< −0.15` weakening / else stable). Plus ONE
  `entity_type='aggregate', entity_id='total'` row — **rotation mass** = Σ|Δshare|/2 (pp of the mix
  that moved; precedent: fy-acceleration's mixed aggregate+component rows).
- **Insight** (`core/relational_insights.py :: rotation_insight` — live): top gainers/losers by name
  + Δpp; the real-world line comes from the **majority `economic_role` of the top-3 gainers/losers**
  (roles resolved from the system model's `concept_tags`, majority taken over the *material* movers —
  `|Δ| ≥ 0.15pp`, the status-rule threshold — so a +0.04pp bystander cannot outvote a +3.4pp shift;
  untagged entities abstain). Mixed roles → honest fallback ("no single theme"); a wholly untagged
  entity set (bank categories — a lender mix, not an economic one) gets **no** theme sentence.
  Steady mix (mass < 0.5pp) is reported as the finding. Composition reads only — no lead/lag claims
  (COMPOSITION_SPEC §4). `divergence_insight` (same module) renders the hierarchy-divergence cards,
  citing ONLY the signal's own gap values. **Wired on both dashboards**: SIBC Stage 5.5 routes
  rotation/divergence through these builders (like scan); payments Stage 4b emits them as
  `representation: deterministic-db` cards validated strictly vs their own db rows (4c) with
  `reasoning.signals` resolved against signals.db (4d).

### divergence, hierarchy axis — child contradicting its parent
`csv_sector_divergence` (SIBC: children vs parent YoY) · `csv_bank_divergence` (ATM/POS: bank vs its
`bank_category` YoY on a metric). METHOD_TYPE: `divergence`. **One operator, both trees** — a bank
diverging from its category is structurally identical to a sub-sector diverging from its sector.

- **Flag rule (params, deterministic):** opposite YoY signs AND `|child_yoy| ≥ min_abs` (default
  2.0) AND `|child_yoy − parent_yoy| ≥ min_gap` (default 5.0).
- **Rows:** **flagged entities only** (anomaly-surfaced by construction — bounded output; 67 banks
  never produce 67 rows). `value = child_yoy − parent_yoy` (pp, signed; sign carries direction — no
  new status vocabulary). No flags → no rows → insight suppressed.

### divergence, metric axis — declared co-movement pairs
`csv_pair_divergence` (ATM/POS). METHOD_TYPE: `pair` at total level, `divergence` at bank level —
one method, two shapes, so the ground truth for each is the right shape (below).

- **The authored pair list IS the registry**: one signal per pair (e.g. `cc-issuance-vs-spend-gap`
  = cards YoY vs spend YoY). Only registered pairs are ever compared — "declared pairs only" falls
  out of the registry-is-the-spec rule; no separate relation file. **Live pairs (5):**
  `cc-issuance-vs-spend-gap` · `dc-issuance-vs-spend-gap` · `pos-fleet-vs-spend-gap` ·
  `atm-fleet-vs-withdrawal-gap` (total) + `cc-issuance-vs-spend-bank-gap` (bank).
- **Params:** `a`/`b` metric bundles (`{metrics: [...], label}` — a side may sum several CSV
  metrics, e.g. card spend = POS + e-com), `level: total|bank`, flag thresholds (`a_min`, `b_max`,
  `min_gap`), and **`min_base`** — both metrics must have a nonzero base for the entity.
  `min_base` is the structural-vs-surprising rule: issuer-only banks (cards > 0, POS = 0 —
  AU/HSBC/Utkarsh pattern) are *structure*, excluded by construction, never flagged as anomalies.
- **Rows:** `level: total` → one aggregate row (`value = yoy_a − yoy_b` pp) **plus two
  `entity_type='pair_side'` component rows** carrying each side's own YoY. The gap alone cannot
  tell "both grew, A faster" from "both shrank, B faster" from "A grew while B fell" — three
  different stories with identical arithmetic — so direction is read from data, never inferred
  from the sign. `level: bank` → flagged banks only.
- **Ground truth:** total-level pairs are **scalar-shaped** (value + series + the two side rows as
  `components`), *not* scan-shaped: a "distribution" of one pp gap and two pct rates would let
  cumulative-sum derivations admit numbers that mean nothing. Negative-tested — an invented gap in
  body or chain fails Stage 4c.
- **Insight** (`core/relational_insights.py :: pair_divergence_insight` — live): a pair earns a
  card only when the sides have come apart; a `stable` gap (inside ±3 pp) is the null result and is
  suppressed. Only the gap is stated as a figure; the side rates set the wording. Verbs are
  past-tense (grew/fell/shrank) so one template stays grammatical across authored labels of mixed
  number. Payments Stage 4b renders them as `deterministic-db` cards (`insight_kind:
  divergence_pair`), sourcing the bank-level rows too where a pair has them.

### Conventions shared by all three
- **Coverage additions are registry entries, not architecture** (e.g. per-bank spend rows for the
  bank-level pair signal = new bank-scan entries).
- **Backfill**: append every period on introduction (Check 2f recomputes all periods); the first
  `window` periods legitimately emit no rotation rows.
- **Traceability**: rows land in `signals.db` → Check 2g / Stage 4c period-wide ground truth covers
  them; `query.signal_numbers` treats `rotation`/`divergence` like `scan` (full row distribution).
- **Insight schema**: emitted insights carry `insight_kind: rotation | divergence_hierarchy |
  divergence_pair` (additive field; no restructure).
- **Consumption**: anomaly-surfaced insights on the dashboards; everything else on-demand via the
  reply-desk `lookup` pattern. Never pre-generate per-bank cards.

## Evaluate + query
- **`evaluate.py`** — Stage 5 LLM evaluation: builds domain payloads from `signals.db`, calls
  the model, writes `evaluations/{pipeline}/{period}.json`. Caches by payload hash + prompt
  version.
- **`query.py`** — builds signal payloads (scalar + scan + full chronological series) for
  evaluate and for traceability ground-truth (`signal_numbers` / `flat_numbers`).
- **`apply_status_rules.py`**, **`update_registry.py`**, **`rebuild_*_signals.py`**,
  **`migrate_to_db.py`** — maintenance/backfill helpers.

Append/evaluate are driven via `core/generate_signal_history.py`, not these scripts directly.
