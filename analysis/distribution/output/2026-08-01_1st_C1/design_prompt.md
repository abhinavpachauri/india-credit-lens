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

Total bank credit outstanding reached ₹215.2L Cr in May 2026, the highest level on record. Volume rose ₹3.0L Cr period-on-period (₹212.1L Cr → ₹215.2L Cr), reversing April's post-year-end dip and resuming the climb from ₹178.7L Cr in January 2025.

*So what:* The credit cycle is back on track. Lenders should prepare for sustained high-volume deployment through FY27 — this is a growth environment, not a consolidation phase. Watch for capacity constraints and asset quality pressure as the system scales.

<sub>source: sibc_l1_annotations.json → bankCredit · signals: sibc-bank-credit-abs</sub>

### Personal loans at 15.38% YoY — decelerating from Apr high

Personal loans credit grew 15.38% YoY in May 2026, down from 16.01% last period. Growth decelerated 0.64pp from 16.01% to 15.38%, slipping from near the upper range (p75 = 15.7%) toward the median. The trajectory shows: 16.0% → 15.4%.

*So what:* Personal loans remain a growth engine at 15.38% YoY, but the deceleration from 16.01% signals the sector may be plateauing after a strong run. Lenders should monitor unsecured exposure — especially credit cards and personal loans — as growth stabilizes at elevated levels. Watch for further softening below 14% as a signal of peak momentum passing.

<sub>source: sibc_l1_annotations.json → mainSectors · signals: sibc-personal-loans-yoy</sub>

### Credit cards +8.5% YoY — fastest growth in 13 months

Credit cards outstanding grew 8.5% year-on-year in May 2026, up 0.3 points from 8.1% prior period. YoY growth re-accelerated for the fourth consecutive period: 8.0% in Mar 2026 → 8.1% in Apr 2026 → 8.5% in May 2026. The rate is now at the upper end of the 17-period range (6.7%–9.4%).

*So what:* Credit card growth has fully reversed its deceleration trend — the 8.5% rate is the fastest in 13 months, confirming the purge-driven slowdown has ended and issuers are now expanding at a pace that exceeds the Mar 2025 baseline. The four-period re-acceleration (7.7% → 8.0% → 8.1% → 8.5%) confirms the market has entered a new growth phase, and the 8.5% rate is only 0.9 points below the Jan 2025 peak (9.4%), signaling the market is on track to return to double-digit growth within two quarters. The recovery is complete, and the market is now accelerating.

<sub>source: atm_pos_insights.json → cc · signals: cc-outstanding-yoy</sub>

### POS terminals -0.48% YoY — first contraction on record

POS terminals contracted 0.48% year-on-year in May 2026, down from 1.45% growth in Apr 2026. YoY growth turned negative 1.5% → -0.5%, a 1.9-point drop — the first sub-zero reading in the 17-period series.

*So what:* The POS network is in year-on-year contraction — the -0.5% rate confirms the channel is shrinking, not consolidating. Lenders financing POS acceptance infrastructure should treat this as a structural decline signal. The network will need sustained monthly gains of 100K+ units to return to positive YoY growth — a scenario not yet visible in the data.

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
   "value": "₹178.7L Cr",
   "claim": "sibc-bank-credit-abs",
   "signals": [
    "sibc-bank-credit-abs"
   ]
  },
  {
   "value": "27",
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
   "value": "16.0%",
   "claim": "sibc-personal-loans-yoy",
   "signals": [
    "sibc-personal-loans-yoy"
   ]
  },
  {
   "value": "15.4%",
   "claim": "sibc-personal-loans-yoy",
   "signals": [
    "sibc-personal-loans-yoy"
   ]
  },
  {
   "value": "14%",
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
   "value": "13",
   "claim": "cc-cards-yoy",
   "signals": [
    "cc-outstanding-yoy"
   ]
  },
  {
   "value": "0.3",
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
   "value": "8.0%",
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
   "value": "7.7%",
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
   "value": "17",
   "claim": "infra-pos-yoy",
   "signals": [
    "pos-terminals-yoy"
   ]
  },
  {
   "value": "100",
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
