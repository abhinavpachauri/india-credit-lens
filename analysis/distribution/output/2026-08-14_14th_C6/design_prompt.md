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

Small business credit is growing at 26.2% this year and now makes up 23.1% of all business lending. Growth in micro and small business loans jumped by 23.8pp because government systems like UDYAM registration and GST data now let lenders check if tiny businesses are real and can pay back. Banks cannot reach thousands of small borrowers alone, so they lend through partners who find customers and do the checking.

<sub>source: opportunities_feed.json · signals: sibc-msme-micro-small-fy-acceleration, sibc-msme-micro-small-share, sibc-msme-micro-small-yoy, sibc-msme-size-yoy-spread</sub>

### Rural cash distribution via Micro ATM / Business Correspondent networks

India has 13.6 lakh micro ATMs that let villagers withdraw cash without visiting a full branch, but the number fell -8.1% recently. These machines are closing or fewer are being added even though people in small towns still need cash every day. A micro ATM costs far less to run than opening a real branch.

<sub>source: opportunities_feed.json · signals: micro-atm-yoy, micro-atms-abs</sub>

### Cross-system signal: credit_card flow leading stock — origination headroom

Credit card spending at shops (POS) is up 9.32 percent and online (e-commerce) is up 4.97 percent, but the actual credit card loans outstanding grew only 1.33 percent. ATM cash withdrawals on cards fell 1.0 percent. People are swiping cards more but not borrowing much more yet, which means there is room to lend.

<sub>source: opportunities_feed.json · signals: cc-atm-val-abs, cc-atm-val-share, cc-atm-val-yoy, cc-ecom-val-abs, cc-ecom-val-share, cc-ecom-val-yoy, cc-other-val-abs, cc-other-val-share, cc-other-val-yoy, cc-pos-val-abs, cc-pos-val-share, cc-pos-val-yoy, sibc-pl-cc-abs, sibc-pl-cc-below10-streak, sibc-pl-cc-share, sibc-pl-cc-yoy</sub>

### Gold loan market entry / deepening for banks

Banks are growing gold loans by 105.5% compared to last year, and this growth has continued for 12 straight periods. Gold prices jumped sharply between 2023 and 2026, so customers can now borrow much more money using the same gold jewelry or coins as security. Banks are winning customers from finance companies because they have local branches where staff can check the gold is real and store it safely, plus they charge lower interest rates.

<sub>source: opportunities_feed.json · signals: sibc-pl-gold-pos-streak, sibc-pl-gold-yoy</sub>

## The numbers you may use

This is the complete set. Nothing outside it may appear on the pager.

```json
{
 "supplied_numbers": [
  {
   "value": "26.2%",
   "claim": "opp_colending_infra",
   "signals": [
    "sibc-msme-micro-small-fy-acceleration",
    "sibc-msme-micro-small-share",
    "sibc-msme-micro-small-yoy",
    "sibc-msme-size-yoy-spread"
   ]
  },
  {
   "value": "23.1%",
   "claim": "opp_colending_infra",
   "signals": [
    "sibc-msme-micro-small-fy-acceleration",
    "sibc-msme-micro-small-share",
    "sibc-msme-micro-small-yoy",
    "sibc-msme-size-yoy-spread"
   ]
  },
  {
   "value": "23.8pp",
   "claim": "opp_colending_infra",
   "signals": [
    "sibc-msme-micro-small-fy-acceleration",
    "sibc-msme-micro-small-share",
    "sibc-msme-micro-small-yoy",
    "sibc-msme-size-yoy-spread"
   ]
  },
  {
   "value": "13.6 lakh",
   "claim": "opp_rural_cash_distribution",
   "signals": [
    "micro-atm-yoy",
    "micro-atms-abs"
   ]
  },
  {
   "value": "-8.1%",
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
   "value": "105.5%",
   "claim": "opp_gold_loan_entry",
   "signals": [
    "sibc-pl-gold-pos-streak",
    "sibc-pl-gold-yoy"
   ]
  },
  {
   "value": "12",
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
