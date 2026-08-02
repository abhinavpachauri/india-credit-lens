# Design prompt — 2026-08-01 · Headline levels (C1)

**Slot:** 1st of the month
**Question this answers:** What are the numbers
**Data vintage:** Both halves are on the same data month: June 2026 credit data and June 2026 payments data.
**Pages:** 1

## The arc

Open with the headline level, then the two or three numbers that qualify it. The reader should leave knowing the size and the direction, nothing more.

## The claims

Each block below is verbatim from a gate-validated artifact. Use the wording as the source of truth for what is being said; you may shorten for the page, but you may not change a number or add a qualifier that is not here.

### Bank credit at ₹219.3L Cr — highest on record

Total bank credit outstanding reached ₹219.3L Cr in June 2026, the highest level on record. Volume climbed ₹4.1L Cr period-on-period (₹215.2L Cr → ₹219.3L Cr), the largest monthly gain in this ten-period window and a continuation of the upward trajectory from ₹178.7L Cr in January 2025.

*So what:* June's ₹4.1L Cr gain is the largest monthly addition in this dataset, pushing the book to a new all-time high. The credit cycle is expanding at an accelerating pace, with no sign of the post-year-end correction that briefly slowed April.

<sub>source: sibc_l1_annotations.json → bankCredit · signals: sibc-bank-credit-abs</sub>

### Personal loans at 15.76% YoY — re-accelerating after May dip

Personal loans credit grew 15.76% YoY in Jun 2026, up from 15.38% last period. Growth re-accelerated 0.38pp from 15.38% to 15.76%, reversing the prior period's deceleration and climbing back near the 75th percentile (15.8%).

*So what:* Personal loans have bounced back from the May 2026 dip — the re-acceleration to 15.76% confirms the prior slowdown was a pause, not a trend break. The sector remains in a solid growth phase, though no longer at the top of the range.

<sub>source: sibc_l1_annotations.json → mainSectors · signals: sibc-personal-loans-yoy</sub>

### Credit cards +9.57% YoY — fastest growth in 17 months

Credit cards outstanding grew 9.57% year-on-year in Jun 2026, up 1.10 points from 8.47% prior period. YoY growth re-accelerated for the fifth consecutive period: 7.7% in Feb 2026 → 8.0% in Mar 2026 → 8.1% in Apr 2026 → 8.5% in May 2026 → 9.6% in Jun 2026. The rate is now at the upper end of the 18-period range (6.7%–9.6%).

<sub>source: atm_pos_insights.json → cc · signals: cc-outstanding-yoy</sub>

### POS terminals -15.8% YoY — steepest contraction on record

POS terminals contracted 15.79% year-on-year in Jun 2026, down from -0.48% in May 2026. YoY growth fell -0.5% → -15.8%, a 15.3-point drop — the steepest monthly deterioration in the 18-period series and the weakest reading on record.

*So what:* The -15.8% YoY rate is the steepest contraction on record and confirms the POS network is in structural collapse. The network now holds 15.8% fewer terminals than it did a year ago, the first double-digit contraction in the dataset. The 15.3-point deterioration in one month is the steepest on record and signals the contraction is accelerating, not stabilising. This is a network collapse event — the POS channel is shrinking at an unprecedented rate.

<sub>source: atm_pos_insights.json → infra · signals: pos-terminals-yoy</sub>

## The numbers you may use

This is the complete set. Nothing outside it may appear on the pager.

```json
{
 "supplied_numbers": [
  {
   "value": "₹219.3L Cr",
   "claim": "sibc-bank-credit-abs",
   "signals": [
    "sibc-bank-credit-abs"
   ]
  },
  {
   "value": "₹4.1L Cr",
   "claim": "sibc-bank-credit-abs",
   "signals": [
    "sibc-bank-credit-abs"
   ]
  },
  {
   "value": "₹215.2L Cr",
   "claim": "sibc-bank-credit-abs",
   "signals": [
    "sibc-bank-credit-abs"
   ]
  },
  {
   "value": "₹178.7L Cr",
   "claim": "sibc-bank-credit-abs",
   "signals": [
    "sibc-bank-credit-abs"
   ]
  },
  {
   "value": "15.76%",
   "claim": "sibc-personal-loans-yoy",
   "signals": [
    "sibc-personal-loans-yoy"
   ]
  },
  {
   "value": "15.38%",
   "claim": "sibc-personal-loans-yoy",
   "signals": [
    "sibc-personal-loans-yoy"
   ]
  },
  {
   "value": "0.38pp",
   "claim": "sibc-personal-loans-yoy",
   "signals": [
    "sibc-personal-loans-yoy"
   ]
  },
  {
   "value": "75",
   "claim": "sibc-personal-loans-yoy",
   "signals": [
    "sibc-personal-loans-yoy"
   ]
  },
  {
   "value": "15.8%",
   "claim": "sibc-personal-loans-yoy",
   "signals": [
    "sibc-personal-loans-yoy"
   ]
  },
  {
   "value": "9.57%",
   "claim": "cc-cards-yoy",
   "signals": [
    "cc-outstanding-yoy"
   ]
  },
  {
   "value": "17",
   "claim": "cc-cards-yoy",
   "signals": [
    "cc-outstanding-yoy"
   ]
  },
  {
   "value": "1.10",
   "claim": "cc-cards-yoy",
   "signals": [
    "cc-outstanding-yoy"
   ]
  },
  {
   "value": "8.47%",
   "claim": "cc-cards-yoy",
   "signals": [
    "cc-outstanding-yoy"
   ]
  },
  {
   "value": "7.7%",
   "claim": "cc-cards-yoy",
   "signals": [
    "cc-outstanding-yoy"
   ]
  },
  {
   "value": "8.0%",
   "claim": "cc-cards-yoy",
   "signals": [
    "cc-outstanding-yoy"
   ]
  },
  {
   "value": "8.1%",
   "claim": "cc-cards-yoy",
   "signals": [
    "cc-outstanding-yoy"
   ]
  },
  {
   "value": "8.5%",
   "claim": "cc-cards-yoy",
   "signals": [
    "cc-outstanding-yoy"
   ]
  },
  {
   "value": "9.6%",
   "claim": "cc-cards-yoy",
   "signals": [
    "cc-outstanding-yoy"
   ]
  },
  {
   "value": "18",
   "claim": "cc-cards-yoy",
   "signals": [
    "cc-outstanding-yoy"
   ]
  },
  {
   "value": "6.7%",
   "claim": "cc-cards-yoy",
   "signals": [
    "cc-outstanding-yoy"
   ]
  },
  {
   "value": "0.2",
   "claim": "cc-cards-yoy",
   "signals": [
    "cc-outstanding-yoy"
   ]
  },
  {
   "value": "9.4%",
   "claim": "cc-cards-yoy",
   "signals": [
    "cc-outstanding-yoy"
   ]
  },
  {
   "value": "-15.8%",
   "claim": "infra-pos-yoy",
   "signals": [
    "pos-terminals-yoy"
   ]
  },
  {
   "value": "15.79%",
   "claim": "infra-pos-yoy",
   "signals": [
    "pos-terminals-yoy"
   ]
  },
  {
   "value": "-0.48%",
   "claim": "infra-pos-yoy",
   "signals": [
    "pos-terminals-yoy"
   ]
  },
  {
   "value": "-0.5%",
   "claim": "infra-pos-yoy",
   "signals": [
    "pos-terminals-yoy"
   ]
  },
  {
   "value": "15.3",
   "claim": "infra-pos-yoy",
   "signals": [
    "pos-terminals-yoy"
   ]
  },
  {
   "value": "18",
   "claim": "infra-pos-yoy",
   "signals": [
    "pos-terminals-yoy"
   ]
  },
  {
   "value": "15.8%",
   "claim": "infra-pos-yoy",
   "signals": [
    "pos-terminals-yoy"
   ]
  }
 ]
}
```

## Hard constraints

- Use **only** the numbers listed above. Invent nothing.
- Do **not** compute new figures from these numbers — no totals, no differences, no percentages of percentages, no annualising.
- Do not look anything up. This prompt is the whole world for this pager.
- Do not add forecasts, targets, or attributions to any policy or event.
- Keep the data vintage line on the pager exactly as given above.
- If something seems missing, leave it out rather than filling the gap.

<sub>generated by analysis/distribution/generate_slot.py · category C1 · 2026-08-01</sub>
