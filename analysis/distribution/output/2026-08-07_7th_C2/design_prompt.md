# Design prompt — 2026-08-07 · Rotation (C2)

**Slot:** 7th of the month
**Question this answers:** What's gaining ground, at whose expense
**Data vintage:** Both halves are on the same data month: May 2026 credit data and May 2026 payments data.
**Pages:** 1

## The arc

Show the mix moving: who gained share, who gave it up, and how much of the mix changed hands in total. A before/after of the same pie reads better than a bar chart.

## The claims

Each block below is verbatim from a gate-validated artifact. Use the wording as the source of truth for what is being said; you may shorten for the page, but you may not change a number or add a qualifier that is not here.

### Services credit mix rotating toward Non-Banking Financial Companies (+3.43 pp share in a year)

Compared with the same month a year ago, the biggest share gains in services credit came from Non-Banking Financial Companies +3.43 pp; Computer Software +0.19 pp; Aviation +0.04 pp. The ground came from Other Services -2.13 pp; Trade -0.60 pp; Transport Operators -0.56 pp. In all, 3.72 pp of the mix changed hands. The gains concentrate in financial intermediation, the cessions in trade & distribution — the mix is tilting toward financial intermediation.

*So what:* This is a composition read: it says where the mix is shifting, not why and not what happens next. The tilt toward financial intermediation is the line to watch — confirm it holds next month before treating it as a trend.

<sub>source: sibc_l1_annotations.json → services · signals: sibc-services-rotation</sub>

### Personal loans mix rotating toward Loans against gold jewellery (+3.21 pp share in a year)

Compared with the same month a year ago, the biggest share gains in personal loans came from Loans against gold jewellery +3.21 pp; Vehicle Loans +0.18 pp. The ground came from Housing -1.93 pp; Other Personal Loans -0.64 pp; Credit Card Outstanding -0.58 pp. In all, 3.39 pp of the mix changed hands. The cessions concentrate in consumer finance; the gains span several parts of the economy.

*So what:* This is a composition read: it says where the mix is shifting, not why and not what happens next. With no single theme behind the movers, treat each segment's shift on its own terms rather than as one story.

<sub>source: sibc_l1_annotations.json → personalLoans · signals: sibc-pl-rotation</sub>

### Industry credit mix rotating toward All Engineering (+0.91 pp share in a year)

Compared with the same month a year ago, the biggest share gains in industry credit came from All Engineering +0.91 pp; Petroleum, Coal Products and Nuclear Fuels +0.70 pp; Basic Metal and Metal Product +0.35 pp. The ground came from Infrastructure -1.73 pp; Textiles -0.43 pp; Food Processing -0.17 pp. In all, 2.83 pp of the mix changed hands. The cessions concentrate in traditional consumer sectors; the gains span several parts of the economy.

*So what:* This is a composition read: it says where the mix is shifting, not why and not what happens next. With no single theme behind the movers, treat each segment's shift on its own terms rather than as one story.

<sub>source: sibc_l1_annotations.json → industryByType · signals: sibc-industry-rotation</sub>

### Credit cards mix rotating toward Small Finance Banks (+0.67 pp share in a year)

Compared with the same month a year ago, the biggest share gains in credit cards came from Small Finance Banks +0.67 pp; Private Sector Banks +0.04 pp. The ground came from Foreign Banks -0.53 pp; Public Sector Banks -0.18 pp. In all, 0.70 pp of the mix changed hands.

*So what:* This is a composition read: it says where the mix is shifting, not why and not what happens next. Watch whether Small Finance Banks holds its gains next month before reading the shift as a trend.

<sub>source: atm_pos_insights.json → cc · signals: cc-category-rotation</sub>

## The numbers you may use

This is the complete set. Nothing outside it may appear on the pager.

```json
{
 "supplied_numbers": [
  {
   "value": "3.43 pp",
   "claim": "sibc-services-rotation",
   "signals": [
    "sibc-services-rotation"
   ]
  },
  {
   "value": "0.19 pp",
   "claim": "sibc-services-rotation",
   "signals": [
    "sibc-services-rotation"
   ]
  },
  {
   "value": "0.04 pp",
   "claim": "sibc-services-rotation",
   "signals": [
    "sibc-services-rotation"
   ]
  },
  {
   "value": "-2.13 pp",
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
   "value": "-0.56 pp",
   "claim": "sibc-services-rotation",
   "signals": [
    "sibc-services-rotation"
   ]
  },
  {
   "value": "3.72 pp",
   "claim": "sibc-services-rotation",
   "signals": [
    "sibc-services-rotation"
   ]
  },
  {
   "value": "3.21 pp",
   "claim": "sibc-pl-rotation",
   "signals": [
    "sibc-pl-rotation"
   ]
  },
  {
   "value": "0.18 pp",
   "claim": "sibc-pl-rotation",
   "signals": [
    "sibc-pl-rotation"
   ]
  },
  {
   "value": "-1.93 pp",
   "claim": "sibc-pl-rotation",
   "signals": [
    "sibc-pl-rotation"
   ]
  },
  {
   "value": "-0.64 pp",
   "claim": "sibc-pl-rotation",
   "signals": [
    "sibc-pl-rotation"
   ]
  },
  {
   "value": "-0.58 pp",
   "claim": "sibc-pl-rotation",
   "signals": [
    "sibc-pl-rotation"
   ]
  },
  {
   "value": "3.39 pp",
   "claim": "sibc-pl-rotation",
   "signals": [
    "sibc-pl-rotation"
   ]
  },
  {
   "value": "0.91 pp",
   "claim": "sibc-industry-rotation",
   "signals": [
    "sibc-industry-rotation"
   ]
  },
  {
   "value": "0.70 pp",
   "claim": "sibc-industry-rotation",
   "signals": [
    "sibc-industry-rotation"
   ]
  },
  {
   "value": "0.35 pp",
   "claim": "sibc-industry-rotation",
   "signals": [
    "sibc-industry-rotation"
   ]
  },
  {
   "value": "-1.73 pp",
   "claim": "sibc-industry-rotation",
   "signals": [
    "sibc-industry-rotation"
   ]
  },
  {
   "value": "-0.43 pp",
   "claim": "sibc-industry-rotation",
   "signals": [
    "sibc-industry-rotation"
   ]
  },
  {
   "value": "-0.17 pp",
   "claim": "sibc-industry-rotation",
   "signals": [
    "sibc-industry-rotation"
   ]
  },
  {
   "value": "2.83 pp",
   "claim": "sibc-industry-rotation",
   "signals": [
    "sibc-industry-rotation"
   ]
  },
  {
   "value": "0.67 pp",
   "claim": "cc-category-rotation",
   "signals": [
    "cc-category-rotation"
   ]
  },
  {
   "value": "0.04 pp",
   "claim": "cc-category-rotation",
   "signals": [
    "cc-category-rotation"
   ]
  },
  {
   "value": "-0.53 pp",
   "claim": "cc-category-rotation",
   "signals": [
    "cc-category-rotation"
   ]
  },
  {
   "value": "-0.18 pp",
   "claim": "cc-category-rotation",
   "signals": [
    "cc-category-rotation"
   ]
  },
  {
   "value": "0.70 pp",
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
