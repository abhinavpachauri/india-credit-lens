# Design prompt — 2026-08-01 · Headline levels (C1)

**Slot:** 1st of the month
**Question this answers:** What are the numbers
**Data vintage:** Both halves are on the same data month: May 2026 credit data and May 2026 payments data.
**Pages:** 1

## The arc

Open with the headline level, then the two or three numbers that qualify it. The reader should leave knowing the size and the direction, nothing more.

## The claims

Each block below is verbatim from a gate-validated artifact. Use the wording as the source of truth for what is being said; you may shorten for the page, but you may not change a number or add a qualifier that is not here.

### Bank credit at ₹215.2L Cr — new all-time high

Total bank credit outstanding reached ₹215.2L Cr in May 2026, the highest level on record. Volume climbed ₹3.0L Cr period-on-period (₹212.1L Cr → ₹215.2L Cr), reversing April's ₹1.5L Cr decline and resuming the upward trajectory from ₹178.7L Cr in January 2025.

*So what:* The April correction was a brief post-year-end adjustment. May's ₹3.0L Cr gain confirms the credit cycle remains in expansion mode, with the book now at its highest level in this dataset.

<sub>source: sibc_l1_annotations.json → bankCredit · signals: sibc-bank-credit-abs</sub>

### Personal loans 15.38% YoY — easing from peak

Personal loans credit grew 15.38% YoY in May 2026, down from 16.01% last period. Growth decelerated 0.64pp from 16.01% to 15.38%, slipping from above the 75th percentile (15.7%) toward the median.

*So what:* Personal loans are decelerating from the Apr 2026 peak — the 15.38% rate is still solid but no longer at the top of the range. The sector may be plateauing after a strong run; unsecured exposure warrants monitoring as growth stabilizes.

<sub>source: sibc_l1_annotations.json → mainSectors · signals: sibc-personal-loans-yoy</sub>

### Credit cards +8.5% YoY — fastest growth in 12 months

Credit cards outstanding grew 8.47% year-on-year in May 2026, up 0.32 points from 8.15% prior period. YoY growth re-accelerated for the fourth consecutive period: 7.7% in Feb 2026 → 8.0% in Mar 2026 → 8.1% in Apr 2026 → 8.5% in May 2026. The rate is now at the upper end of the 17-period range (6.7%–9.4%).

<sub>source: atm_pos_insights.json → cc · signals: cc-outstanding-yoy</sub>

### POS terminals -0.48% YoY — first contraction on record

POS terminals contracted 0.48% year-on-year in May 2026, down from 1.45% growth in Apr 2026. YoY growth turned negative 1.5% → -0.5%, a 1.9-point drop — the rate has fallen from Jan's 11.5% peak and is now negative for the first time in the 17-period series.

*So what:* The -0.5% YoY rate is the first contraction on record and confirms the POS network is shrinking year-on-year. The rate has fallen 12 points from Jan's 11.5% peak, and the network now holds fewer terminals than it did a year ago. This is a structural decline signal — the POS channel is contracting, not consolidating.

<sub>source: atm_pos_insights.json → infra · signals: pos-terminals-yoy</sub>

## The numbers you may use

This is the complete set. Nothing outside it may appear on the pager.

```json
{
 "supplied_numbers": [
  {
   "value": "₹215.2L Cr",
   "claim": "sibc-bank-credit-abs",
   "signals": [
    "sibc-bank-credit-abs"
   ]
  },
  {
   "value": "₹3.0L Cr",
   "claim": "sibc-bank-credit-abs",
   "signals": [
    "sibc-bank-credit-abs"
   ]
  },
  {
   "value": "₹212.1L Cr",
   "claim": "sibc-bank-credit-abs",
   "signals": [
    "sibc-bank-credit-abs"
   ]
  },
  {
   "value": "₹1.5L Cr",
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
   "value": "15.38%",
   "claim": "sibc-personal-loans-yoy",
   "signals": [
    "sibc-personal-loans-yoy"
   ]
  },
  {
   "value": "16.01%",
   "claim": "sibc-personal-loans-yoy",
   "signals": [
    "sibc-personal-loans-yoy"
   ]
  },
  {
   "value": "0.64pp",
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
   "value": "15.7%",
   "claim": "sibc-personal-loans-yoy",
   "signals": [
    "sibc-personal-loans-yoy"
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
   "value": "12",
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
   "value": "0.32",
   "claim": "cc-cards-yoy",
   "signals": [
    "cc-outstanding-yoy"
   ]
  },
  {
   "value": "8.15%",
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
   "value": "17",
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
   "value": "9.4%",
   "claim": "cc-cards-yoy",
   "signals": [
    "cc-outstanding-yoy"
   ]
  },
  {
   "value": "0.9",
   "claim": "cc-cards-yoy",
   "signals": [
    "cc-outstanding-yoy"
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
   "value": "0.48%",
   "claim": "infra-pos-yoy",
   "signals": [
    "pos-terminals-yoy"
   ]
  },
  {
   "value": "1.45%",
   "claim": "infra-pos-yoy",
   "signals": [
    "pos-terminals-yoy"
   ]
  },
  {
   "value": "1.5%",
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
   "value": "1.9",
   "claim": "infra-pos-yoy",
   "signals": [
    "pos-terminals-yoy"
   ]
  },
  {
   "value": "11.5%",
   "claim": "infra-pos-yoy",
   "signals": [
    "pos-terminals-yoy"
   ]
  },
  {
   "value": "17",
   "claim": "infra-pos-yoy",
   "signals": [
    "pos-terminals-yoy"
   ]
  },
  {
   "value": "12",
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
