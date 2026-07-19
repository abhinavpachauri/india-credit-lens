# Fable task — stale LLM narrative survives a computed-state flip on cross-system cards

> Logged 2026-07-08 (found on Opus while explaining the cc-spend cross-edge card).
> **Do this on Fable** — it's a mechanism/correctness fix in the opportunities feed layer.
> Small, well-scoped. Read `COMPOSITION_SPEC.md` §23.2 + §21 first (narrative contract).

---

## Symptom (what the user saw)

The `/opportunities` cross-system card `xopp_x_cc_spend_leads_cc_stock` is **self-contradictory**:

- **Title (deterministic):** "credit_card flow **leading** stock — origination **headroom**" → spend is *rising*.
- **Body (LLM narrative):** "Credit card spending is **slowing down** … causing total credit card debt to **drop**" → spend is *falling*.

Both cannot be true. The user (correctly) could not reconcile the card.

## Diagnosis (confirmed 2026-07-08)

The computed state is **flow up**: `ecosystem_state_2026-06-30.json` →
`x_cc_spend_leads_cc_stock: from_direction=1, to_direction=1, state=aligned`. So the **title is
correct** and the **body is stale** — it is the *previous* period's narrative (April, when
`from_direction=-1` → "softening ahead of stock") carried forward onto this period's flipped title.

### Root cause — exact location

`analysis/crosssource/generate_opportunities_feed.py:436-443` (the preserve-narrative-across-regen
block). It carries `body/implication/chain` forward **by `id` only**, with no check that the state
the narrative described still holds:

```python
for it in bundle["cross_system"] + [...pipelines...]:
    if (it.get("driver") or {}).get("kind") == "eco_loop":
        continue                      # loop cards already exempt (prior fix)
    if it["id"] in narrated:
        it.update(narrated[it["id"]]) # ← carries stale body when direction flipped
        it["narrative"] = True        # ← now marked narrated …
```

Then `generate_opportunity_narrative.py:153` skips any cross-system item that is already
`narrative:True` (`... and not c.get("narrative")`), so the narrative step **never regenerates**
the flipped card. Result: last month's body permanently pinned under this month's title.

This is the **same bug family** as the eco-loop card ("fully engaged" vs computed "partial,
1 segment reversed"), fixed earlier by making loop cards never-narrated (§23.2 exception). That
patch only covered `eco_loop`; **cross-edge and construct cards have the same exposure** whenever
their deterministic title flips direction (softening↔headroom, expanding↔contracting).

## Approved fix design (Fable review, 2026-07-19 — supersedes the first proposal)

**Preserve a narrative only if BOTH the deterministic title AND the status it was written against
still match.** Title alone (the first proposal) has a hole: *pipeline* opportunity titles are static
model labels (`n["label"]` — never state-encoding), so a pipeline card's status can flip
active↔watch while its title stays identical, and the stale narrative would survive. `(title,
status)` closes both cases — in the observed bug, both changed (`softening…`→`…headroom`,
watch→active); on pipeline cards, status is the state signal.

In the preservation block (`generate_opportunities_feed.py:429-445`):

1. Collect: `narrated[it["id"]] = {body/implication/chain..., "_title": it.get("title"),
   "_status": it.get("status")}`.
2. Re-apply **only if** `new["title"] == _title and new["status"] == _status`. Else drop —
   the item keeps its deterministic templated copy and is re-narrated on the next narrative run
   (`generate_opportunity_narrative` picks it up because `narrative` is no longer set).
3. Keep the existing `eco_loop` skip (loop cards are never narrated — spec §23.2 exception).

**Graceful degradation is part of the design (no-LLM budget):** when a stale narrative is dropped
and the operator does NOT run the narrative step, the card shows its deterministic fallback copy —
which exists for every item and is written to be publishable. Correct-but-plainer beats
fluent-but-wrong; this is the deterministic-first principle applied.

**Testing (deterministic, not fuzzy):** unit tests on the preservation behavior with synthetic
prev/new feeds — (a) title+status match → narrative preserved; (b) title changed → dropped;
(c) status changed, title same (the pipeline-card case) → dropped; (d) eco_loop → never preserved.
The first proposal's direction-word substring guard is REJECTED as a production check (fuzzy,
noisy — same reason the 2g status-substring heuristic is warning-only); the deterministic
key comparison makes it unnecessary.

Also regenerate the feed once after the fix so the live cc-spend card drops its stale body
(deterministic copy until the next narrative run), and run Check 4f strict + the full sibc gate.

## Verify

```bash
python3 analysis/crosssource/compose_ecosystem.py            # confirm from_direction=1 (flow up)
python3 analysis/crosssource/generate_opportunities_feed.py  # with the fix, flipped card drops stale body
source .env.local
python3 analysis/crosssource/generate_opportunity_narrative.py   # re-narrates the flipped card
python3 analysis/core/validate_opportunity_traceability.py --strict   # 4f still green
python3 analysis/core/gate.py --pipeline sibc --merged        # full gate incl. build
```

Expected after fix: the cc-spend card body describes spend **rising / origination headroom**,
matching the title; Check 4f green; suite green.

## Interim state (until fixed)

The live card is wrong in the body only. User guidance already given: **trust the title
(spend up, origination headroom), ignore the stale body.** No data is wrong — signals.db and the
title are correct; only the preserved prose is stale.

## Files

| File | Role |
|---|---|
| `analysis/crosssource/generate_opportunities_feed.py:436-443` | the preservation block to fix |
| `analysis/crosssource/generate_opportunity_narrative.py:151-153` | the skip that hides the flip (works once preservation drops the stale flag) |
| `analysis/COMPOSITION_SPEC.md` §23.2 | narrative contract + the eco_loop exception note (extend it here) |
| `analysis/cross_source/composition.json` | the cross-edge definition (flow=cc_spend_value → stock=SIBC 4.5) |
