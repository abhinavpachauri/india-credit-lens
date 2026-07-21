# Design prompt — 2026-08-14 · Openings & risks (C6)

**Slot:** 14th of the month
**Question this answers:** So what, and for whom
**Data vintage:** Both halves are on the same data month: May 2026 credit data and May 2026 payments data.
**Pages:** 1

## The arc

Lead with the opening or the risk itself, then the computed basis underneath it. The basis is the credibility, so give it room.

## The claims

Each block below is verbatim from a gate-validated artifact. Use the wording as the source of truth for what is being said; you may shorten for the page, but you may not change a number or add a qualifier that is not here.

### Co-lending & warehouse-financing infrastructure

Small business credit is growing at 26.18 percent this year and now represents 23.06 percent of all business lending. Growth in micro and small business lending jumped by 23.77 percentage points, powered by government systems like UDYAM registration and GST data that make it much easier to verify that tiny businesses are real and can repay loans. Banks cannot reach thousands of small borrowers on their own, so they need partners who can do the ground work of finding customers and checking their creditworthiness.

*So what:* Banks should build partnerships with fintech companies and NBFCs who specialize in reaching small businesses, using these partners to handle customer acquisition and initial credit checks while the bank provides the funding.

<sub>source: opportunities_feed.json · signals: sibc-msme-micro-small-fy-acceleration, sibc-msme-micro-small-share, sibc-msme-micro-small-yoy, sibc-msme-size-yoy-spread</sub>

### Rural cash distribution via Micro ATM / Business Correspondent networks

India has 1358241.0 micro ATMs that let villagers withdraw cash without visiting a full branch. The number of these machines dropped -8.11 percent recently, meaning fewer are being added or some are closing. Even though the count is falling, people in small towns still need cash daily and a micro ATM costs far less to operate than opening a real branch.

*So what:* A bank should keep investing in micro ATMs in villages where branches are too expensive, because villagers still depend on cash and these machines are much cheaper to run than full branches.

<sub>source: opportunities_feed.json · signals: micro-atm-yoy, micro-atms-abs</sub>

### Cross-system signal: credit_card flow leading stock — origination headroom

Credit card spending at shops (POS) is up 9.32 percent and online (e-commerce) is up 4.97 percent, but the actual credit card loans outstanding grew only 1.33 percent. ATM cash withdrawals on cards fell 1.0 percent. People are swiping cards more but not borrowing much more yet, which means there is room to lend.

*So what:* The bank should push credit card loans now because customers are spending but loan balances have not caught up, so there is clear headroom to grow the book before demand cools.

<sub>source: opportunities_feed.json · signals: cc-atm-val-abs, cc-atm-val-share, cc-atm-val-yoy, cc-ecom-val-abs, cc-ecom-val-share, cc-ecom-val-yoy, cc-other-val-abs, cc-other-val-share, cc-other-val-yoy, cc-pos-val-abs, cc-pos-val-share, cc-pos-val-yoy, sibc-pl-cc-abs, sibc-pl-cc-below10-streak, sibc-pl-cc-share, sibc-pl-cc-yoy</sub>

### Gold loan market entry / deepening for banks

Banks are growing gold loans by 105.5 percent compared to last year, and this growth has kept climbing for 12.0 periods in a row. Gold prices jumped sharply between 2023 and 2026, so customers can now borrow much more money using the same gold jewelry or coins as security. Banks are winning customers from finance companies because they have local branches where staff can check the gold is real and store it safely, plus they charge lower interest rates.

*So what:* A bank should open more branches in neighborhoods where people own gold jewelry, train staff to test gold quickly and accurately, and offer simple gold loan products with fast approval to capture customers switching from finance companies.

<sub>source: opportunities_feed.json · signals: sibc-pl-gold-pos-streak, sibc-pl-gold-yoy</sub>

## The numbers you may use

This is the complete set. Nothing outside it may appear on the pager.

```json
{
 "supplied_numbers": [
  {
   "value": "26.18",
   "claim": "opp_colending_infra",
   "signals": [
    "sibc-msme-micro-small-fy-acceleration",
    "sibc-msme-micro-small-share",
    "sibc-msme-micro-small-yoy",
    "sibc-msme-size-yoy-spread"
   ]
  },
  {
   "value": "23.06",
   "claim": "opp_colending_infra",
   "signals": [
    "sibc-msme-micro-small-fy-acceleration",
    "sibc-msme-micro-small-share",
    "sibc-msme-micro-small-yoy",
    "sibc-msme-size-yoy-spread"
   ]
  },
  {
   "value": "23.77",
   "claim": "opp_colending_infra",
   "signals": [
    "sibc-msme-micro-small-fy-acceleration",
    "sibc-msme-micro-small-share",
    "sibc-msme-micro-small-yoy",
    "sibc-msme-size-yoy-spread"
   ]
  },
  {
   "value": "1358241.0",
   "claim": "opp_rural_cash_distribution",
   "signals": [
    "micro-atm-yoy",
    "micro-atms-abs"
   ]
  },
  {
   "value": "-8.11",
   "claim": "opp_rural_cash_distribution",
   "signals": [
    "micro-atm-yoy",
    "micro-atms-abs"
   ]
  },
  {
   "value": "9.32",
   "claim": "xopp_x_cc_spend_leads_cc_stock",
   "signals": [
    "cc-atm-val-abs",
    "cc-atm-val-share",
    "cc-atm-val-yoy",
    "cc-ecom-val-abs",
    "cc-ecom-val-share",
    "cc-ecom-val-yoy",
    "cc-other-val-abs",
    "cc-other-val-share",
    "cc-other-val-yoy",
    "cc-pos-val-abs",
    "cc-pos-val-share",
    "cc-pos-val-yoy",
    "sibc-pl-cc-abs",
    "sibc-pl-cc-below10-streak",
    "sibc-pl-cc-share",
    "sibc-pl-cc-yoy"
   ]
  },
  {
   "value": "4.97",
   "claim": "xopp_x_cc_spend_leads_cc_stock",
   "signals": [
    "cc-atm-val-abs",
    "cc-atm-val-share",
    "cc-atm-val-yoy",
    "cc-ecom-val-abs",
    "cc-ecom-val-share",
    "cc-ecom-val-yoy",
    "cc-other-val-abs",
    "cc-other-val-share",
    "cc-other-val-yoy",
    "cc-pos-val-abs",
    "cc-pos-val-share",
    "cc-pos-val-yoy",
    "sibc-pl-cc-abs",
    "sibc-pl-cc-below10-streak",
    "sibc-pl-cc-share",
    "sibc-pl-cc-yoy"
   ]
  },
  {
   "value": "1.33",
   "claim": "xopp_x_cc_spend_leads_cc_stock",
   "signals": [
    "cc-atm-val-abs",
    "cc-atm-val-share",
    "cc-atm-val-yoy",
    "cc-ecom-val-abs",
    "cc-ecom-val-share",
    "cc-ecom-val-yoy",
    "cc-other-val-abs",
    "cc-other-val-share",
    "cc-other-val-yoy",
    "cc-pos-val-abs",
    "cc-pos-val-share",
    "cc-pos-val-yoy",
    "sibc-pl-cc-abs",
    "sibc-pl-cc-below10-streak",
    "sibc-pl-cc-share",
    "sibc-pl-cc-yoy"
   ]
  },
  {
   "value": "1.0",
   "claim": "xopp_x_cc_spend_leads_cc_stock",
   "signals": [
    "cc-atm-val-abs",
    "cc-atm-val-share",
    "cc-atm-val-yoy",
    "cc-ecom-val-abs",
    "cc-ecom-val-share",
    "cc-ecom-val-yoy",
    "cc-other-val-abs",
    "cc-other-val-share",
    "cc-other-val-yoy",
    "cc-pos-val-abs",
    "cc-pos-val-share",
    "cc-pos-val-yoy",
    "sibc-pl-cc-abs",
    "sibc-pl-cc-below10-streak",
    "sibc-pl-cc-share",
    "sibc-pl-cc-yoy"
   ]
  },
  {
   "value": "105.5",
   "claim": "opp_gold_loan_entry",
   "signals": [
    "sibc-pl-gold-pos-streak",
    "sibc-pl-gold-yoy"
   ]
  },
  {
   "value": "12.0",
   "claim": "opp_gold_loan_entry",
   "signals": [
    "sibc-pl-gold-pos-streak",
    "sibc-pl-gold-yoy"
   ]
  },
  {
   "value": "2023",
   "claim": "opp_gold_loan_entry",
   "signals": [
    "sibc-pl-gold-pos-streak",
    "sibc-pl-gold-yoy"
   ]
  },
  {
   "value": "2026,",
   "claim": "opp_gold_loan_entry",
   "signals": [
    "sibc-pl-gold-pos-streak",
    "sibc-pl-gold-yoy"
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

<sub>generated by analysis/distribution/generate_slot.py · category C6 · 2026-08-14</sub>
