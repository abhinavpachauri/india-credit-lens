# Design prompt — 2026-08-07 · Rotation (C2)

**Slot:** 7th of the month
**Question this answers:** What's gaining ground, at whose expense
**Data vintage:** Both halves are on the same data month: June 2026 credit data and June 2026 payments data.
**Pages:** 1

## The arc

Show the mix moving: who gained share, who gave it up, and how much of the mix changed hands in total. A before/after of the same pie reads better than a bar chart.

## The claims

Each block below is verbatim from a gate-validated artifact. Use the wording as the source of truth for what is being said; you may shorten for the page, but you may not change a number or add a qualifier that is not here.

### Services credit mix rotating toward Non-Banking Financial Companies (+2.80 pp share in a year)

Compared with the same month a year ago, the biggest share gains in services credit came from Non-Banking Financial Companies +2.80 pp; Computer Software +0.16 pp; Commercial Real Estate +0.06 pp. The ground came from Other Services -1.65 pp; Transport Operators -0.60 pp; Trade -0.55 pp. In all, 3.08 pp of the mix changed hands. The gains concentrate in financial intermediation, the cessions in trade & distribution — the mix is tilting toward financial intermediation.

*So what:* This is a composition read: it says where the mix is shifting, not why and not what happens next. The tilt toward financial intermediation is the line to watch — confirm it holds next month before treating it as a trend.

<sub>source: sibc_l1_annotations.json → services · signals: sibc-services-rotation</sub>

### Personal loans mix rotating toward Loans against gold jewellery (+3.03 pp share in a year)

Compared with the same month a year ago, the biggest share gains in personal loans came from Loans against gold jewellery +3.03 pp; Vehicle Loans +0.14 pp. The ground came from Housing -2.06 pp; Credit Card Outstanding -0.57 pp; Other Personal Loans -0.33 pp. In all, 3.18 pp of the mix changed hands. The gains concentrate in consumer finance — the mix is tilting toward consumer finance.

*So what:* This is a composition read: it says where the mix is shifting, not why and not what happens next. The tilt toward consumer finance is the line to watch — confirm it holds next month before treating it as a trend.

<sub>source: sibc_l1_annotations.json → personalLoans · signals: sibc-pl-rotation</sub>

### Industry credit mix rotating toward All Engineering (+0.96 pp share in a year)

Compared with the same month a year ago, the biggest share gains in industry credit came from All Engineering +0.96 pp; Petroleum, Coal Products and Nuclear Fuels +0.95 pp; Other Industries +0.61 pp. The ground came from Infrastructure -2.39 pp; Textiles -0.45 pp; Rubber, Plastic and their Products -0.13 pp. In all, 3.23 pp of the mix changed hands. No single economic theme unites the movers — the rotation is broad-based rather than a story about one part of the economy.

*So what:* This is a composition read: it says where the mix is shifting, not why and not what happens next. With no single theme behind the movers, treat each segment's shift on its own terms rather than as one story.

<sub>source: sibc_l1_annotations.json → industryByType · signals: sibc-industry-rotation</sub>

### Credit cards mix rotating toward Small Finance Banks (+0.76 pp share in a year)

Compared with the same month a year ago, the biggest share gains in credit cards came from Small Finance Banks +0.76 pp; Private Sector Banks +0.10 pp. The ground came from Foreign Banks -0.58 pp; Public Sector Banks -0.28 pp. In all, 0.86 pp of the mix changed hands.

*So what:* This is a composition read: it says where the mix is shifting, not why and not what happens next. Watch whether Small Finance Banks holds its gains next month before reading the shift as a trend.

<sub>source: atm_pos_insights.json → cc · signals: cc-category-rotation</sub>

## The numbers you may use

This is the complete set. Nothing outside it may appear on the pager.

```json
{
 "supplied_numbers": [
  {
   "value": "2.80 pp",
   "claim": "sibc-services-rotation",
   "signals": [
    "sibc-services-rotation"
   ]
  },
  {
   "value": "0.16 pp",
   "claim": "sibc-services-rotation",
   "signals": [
    "sibc-services-rotation"
   ]
  },
  {
   "value": "0.06 pp",
   "claim": "sibc-services-rotation",
   "signals": [
    "sibc-services-rotation"
   ]
  },
  {
   "value": "-1.65 pp",
   "claim": "sibc-services-rotation",
   "signals": [
    "sibc-services-rotation"
   ]
  },
  {
   "value": "-0.60 pp",
   "claim": "sibc-services-rotation",
   "signals": [
    "sibc-services-rotation"
   ]
  },
  {
   "value": "-0.55 pp",
   "claim": "sibc-services-rotation",
   "signals": [
    "sibc-services-rotation"
   ]
  },
  {
   "value": "3.08 pp",
   "claim": "sibc-services-rotation",
   "signals": [
    "sibc-services-rotation"
   ]
  },
  {
   "value": "3.03 pp",
   "claim": "sibc-pl-rotation",
   "signals": [
    "sibc-pl-rotation"
   ]
  },
  {
   "value": "0.14 pp",
   "claim": "sibc-pl-rotation",
   "signals": [
    "sibc-pl-rotation"
   ]
  },
  {
   "value": "-2.06 pp",
   "claim": "sibc-pl-rotation",
   "signals": [
    "sibc-pl-rotation"
   ]
  },
  {
   "value": "-0.57 pp",
   "claim": "sibc-pl-rotation",
   "signals": [
    "sibc-pl-rotation"
   ]
  },
  {
   "value": "-0.33 pp",
   "claim": "sibc-pl-rotation",
   "signals": [
    "sibc-pl-rotation"
   ]
  },
  {
   "value": "3.18 pp",
   "claim": "sibc-pl-rotation",
   "signals": [
    "sibc-pl-rotation"
   ]
  },
  {
   "value": "0.96 pp",
   "claim": "sibc-industry-rotation",
   "signals": [
    "sibc-industry-rotation"
   ]
  },
  {
   "value": "0.95 pp",
   "claim": "sibc-industry-rotation",
   "signals": [
    "sibc-industry-rotation"
   ]
  },
  {
   "value": "0.61 pp",
   "claim": "sibc-industry-rotation",
   "signals": [
    "sibc-industry-rotation"
   ]
  },
  {
   "value": "-2.39 pp",
   "claim": "sibc-industry-rotation",
   "signals": [
    "sibc-industry-rotation"
   ]
  },
  {
   "value": "-0.45 pp",
   "claim": "sibc-industry-rotation",
   "signals": [
    "sibc-industry-rotation"
   ]
  },
  {
   "value": "-0.13 pp",
   "claim": "sibc-industry-rotation",
   "signals": [
    "sibc-industry-rotation"
   ]
  },
  {
   "value": "3.23 pp",
   "claim": "sibc-industry-rotation",
   "signals": [
    "sibc-industry-rotation"
   ]
  },
  {
   "value": "0.76 pp",
   "claim": "cc-category-rotation",
   "signals": [
    "cc-category-rotation"
   ]
  },
  {
   "value": "0.10 pp",
   "claim": "cc-category-rotation",
   "signals": [
    "cc-category-rotation"
   ]
  },
  {
   "value": "-0.58 pp",
   "claim": "cc-category-rotation",
   "signals": [
    "cc-category-rotation"
   ]
  },
  {
   "value": "-0.28 pp",
   "claim": "cc-category-rotation",
   "signals": [
    "cc-category-rotation"
   ]
  },
  {
   "value": "0.86 pp",
   "claim": "cc-category-rotation",
   "signals": [
    "cc-category-rotation"
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

<sub>generated by analysis/distribution/generate_slot.py · category C2 · 2026-08-07</sub>
