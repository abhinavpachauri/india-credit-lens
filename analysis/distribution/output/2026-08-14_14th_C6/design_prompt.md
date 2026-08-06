# Design prompt — 2026-08-14 · Openings & risks (C6)

**Slot:** 14th of the month
**Question this answers:** So what, and for whom
**Data vintage:** Both halves are on the same data month: June 2026 credit data and June 2026 payments data.

## Format

- **LinkedIn carousel PDF, portrait 1080×1350 (4:5)** — fills the mobile feed. Not landscape.
- **6 slides**, one idea per slide. Slide 1 is the hook; the last slide signs off + invites a subscribe.
- **Mobile-first:** legible held at arm's length — the number is the hero, the headline ≤ 7 words,
  the body ≤ 25 words. Nothing on a slide should be hard to read on a phone.
- **Fill the canvas** — no slide more than ~30% empty; centre the content, don't strand it top-left.

## Visual system

- **Brand:** India Credit Lens. A small wordmark + `indiacreditlens.com` and a page counter on every
  slide, same position each time. Quiet, consistent, not loud.
- **Palette:** ink `#0f1720` for text; **credit-blue `#1f6feb`** as the accent for numbers/trends; a
  distinct **muted sand `#efe7dc`** reserved *only* for the one 'looks-right-but-isn't' caveat slide
  (so it reads differently at a glance); off-white `#f4f7fb` background; one dark closing slide.
- **Type:** one strong grotesk/sans. Stats set huge (the hero of the slide); eyebrow labels in small
  caps; body two–three lines max. Consistent margins and eyebrow position on every slide.
- **Charts:** clean and axis-light — a sparkline, a short bar run, or two lines and the gap between
  them. Colour the one series that matters; grey the rest. No gridlines-as-decoration, no 3-D, no legends
  a caption can replace.

## The arc

Lead with the opening or the risk itself, then the computed basis underneath it. The basis is the credibility, so give it room.

## Layout kit

Pick a layout per slide and **vary them** — the failure mode is one template repeated. Menu:
1. **Hook** — the headline sentence big, plus 2–3 stat chips. (slide 1)
2. **Big-stat + sparkline** — one hero number with its trailing trend beneath it.
3. **Chart-focus** — a supplied series as a bar/line, minimal words, the takeaway as one caption.
4. **Caveat callout** — the 'headline says X, the data says Y' slide, on the sand background, with the
   comparison shown (e.g. the one entity vs everyone else). This is the most valuable slide — give it room.
5. **Sign-off** — dark slide, wordmark, one-line what-you-just-read, subscribe invite.

## The claims

One slide each, in this order (plus the hook slide and the sign-off).

Each block below is verbatim from a gate-validated artifact. Use the wording as the source of truth for what is being said; you may shorten for the page, but you may not change a number or add a qualifier that is not here.

### Co-lending & warehouse-financing infrastructure

Small business credit is growing at 26.2% this year and now makes up 23.1% of all business lending. Growth in micro and small business loans jumped by 23.8pp because government systems like UDYAM registration and GST data now let lenders check if tiny businesses are real and can pay back. Banks cannot reach thousands of small borrowers alone, so they lend through partners who find customers and do the checking.

*So what:* Lenders who can work with partners to reach small businesses now have data to judge whether those businesses will repay, opening a large and fast-growing segment that was hard to serve before.

<sub>source: opportunities_feed.json · signals: sibc-msme-micro-small-fy-acceleration, sibc-msme-micro-small-share, sibc-msme-micro-small-yoy, sibc-msme-size-yoy-spread</sub>

### Rural cash distribution via Micro ATM / Business Correspondent networks

Micro ATM growth counter-trending against overall ATM network contraction signals persistent rural and semi-urban cash demand at a scale below the economics of full ATM deployment. Banks and fintechs expanding Business Correspondent channels with micro ATM deployment can serve this demand at lower capex than branch or full ATM infrastructure.

<sub>source: opportunities_feed.json · signals: micro-atm-yoy, micro-atms-abs</sub>

### Cross-system signal: credit_card flow leading stock — origination headroom

Credit card spend (value) (Payments) is the early signal; Credit Card Outstanding (Credit) usually follows it a few months later. Reading the two together gives an early view of where the slower side is heading.

*So what:* Use the leading side to plan ahead for the lagging side, before it shows up there.

<sub>source: opportunities_feed.json · signals: cc-atm-val-abs, cc-atm-val-share, cc-atm-val-yoy, cc-ecom-val-abs, cc-ecom-val-share, cc-ecom-val-yoy, cc-other-val-abs, cc-other-val-share, cc-other-val-yoy, cc-pos-val-abs, cc-pos-val-share, cc-pos-val-yoy, sibc-pl-cc-abs, sibc-pl-cc-below10-streak, sibc-pl-cc-share, sibc-pl-cc-yoy</sub>

### Gold loan market entry / deepening for banks

Banks are growing their gold loan books by 105.5% compared to last year, and this growth has now continued for 12 straight periods. Gold prices jumped sharply between 2023 and 2026, so customers can borrow much more money using the same gold jewelry or coins as security. Banks are winning customers from finance companies because they have local branches where staff can check the gold is real and store it safely, plus they charge lower interest rates.

*So what:* The 12-period winning streak and 105.5% growth rate show banks are steadily taking market share in gold lending, which is notable because the collateral itself has become more valuable and banks can offer safer storage and lower rates than competitors.

<sub>source: opportunities_feed.json · signals: sibc-pl-gold-pos-streak, sibc-pl-gold-yoy</sub>

## The numbers you may use

This is the complete set. Nothing outside it may appear on the pager. `supplied_numbers` are the figures you may print; `chart_series` are the trailing histories you may **plot** — one array per claim, already in reading order. Plot these points as given; do not add, interpolate, or extend them.

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
 ],
 "chart_series": [
  {
   "claim": "opp_colending_infra",
   "signal": "sibc-msme-micro-small-fy-acceleration",
   "unit": "",
   "series": [
    {
     "period": "2025-02-28",
     "value": 23.77
    },
    {
     "period": "2025-03-30",
     "value": 23.77
    },
    {
     "period": "2025-04-30",
     "value": 23.77
    },
    {
     "period": "2026-01-30",
     "value": 23.77
    },
    {
     "period": "2026-02-27",
     "value": 23.77
    },
    {
     "period": "2026-03-30",
     "value": 23.77
    },
    {
     "period": "2026-04-30",
     "value": 23.77
    },
    {
     "period": "2026-05-29",
     "value": 23.77
    },
    {
     "period": "2026-06-30",
     "value": 23.77
    },
    {
     "period": "2026-07-31",
     "value": 23.77
    }
   ]
  },
  {
   "claim": "opp_rural_cash_distribution",
   "signal": "micro-atm-yoy",
   "unit": "",
   "series": [
    {
     "period": "2025-06-30",
     "value": -4.29
    },
    {
     "period": "2025-07-31",
     "value": -0.8
    },
    {
     "period": "2025-08-31",
     "value": 1.51
    },
    {
     "period": "2025-09-30",
     "value": 0.49
    },
    {
     "period": "2025-10-31",
     "value": 0.96
    },
    {
     "period": "2025-11-30",
     "value": -1.69
    },
    {
     "period": "2025-12-31",
     "value": -4.18
    },
    {
     "period": "2026-01-31",
     "value": -5.59
    },
    {
     "period": "2026-02-28",
     "value": -5.34
    },
    {
     "period": "2026-03-31",
     "value": -6.21
    },
    {
     "period": "2026-04-30",
     "value": -7.17
    },
    {
     "period": "2026-05-31",
     "value": -8.11
    },
    {
     "period": "2026-06-30",
     "value": -8.39
    }
   ]
  },
  {
   "claim": "xopp_x_cc_spend_leads_cc_stock",
   "signal": "cc-atm-val-abs",
   "unit": "",
   "series": [
    {
     "period": "2025-06-30",
     "value": 3448545.7
    },
    {
     "period": "2025-07-31",
     "value": 3616171.86
    },
    {
     "period": "2025-08-31",
     "value": 3656376.27
    },
    {
     "period": "2025-09-30",
     "value": 3688141.52
    },
    {
     "period": "2025-10-31",
     "value": 4038788.73
    },
    {
     "period": "2025-11-30",
     "value": 3784610.29
    },
    {
     "period": "2025-12-31",
     "value": 3931494.95
    },
    {
     "period": "2026-01-31",
     "value": 3940422.68
    },
    {
     "period": "2026-02-28",
     "value": 3642662.62
    },
    {
     "period": "2026-03-31",
     "value": 4075917.57
    },
    {
     "period": "2026-04-30",
     "value": 3654395.47
    },
    {
     "period": "2026-05-31",
     "value": 3664229.15
    },
    {
     "period": "2026-06-30",
     "value": 3565214.61
    }
   ]
  },
  {
   "claim": "opp_gold_loan_entry",
   "signal": "sibc-pl-gold-pos-streak",
   "unit": "",
   "series": [
    {
     "period": "2025-02-28",
     "value": 2.0
    },
    {
     "period": "2025-03-30",
     "value": 3.0
    },
    {
     "period": "2025-04-30",
     "value": 4.0
    },
    {
     "period": "2026-01-30",
     "value": 8.0
    },
    {
     "period": "2026-02-27",
     "value": 9.0
    },
    {
     "period": "2026-03-30",
     "value": 10.0
    },
    {
     "period": "2026-04-30",
     "value": 11.0
    },
    {
     "period": "2026-05-29",
     "value": 12.0
    },
    {
     "period": "2026-06-30",
     "value": 13.0
    },
    {
     "period": "2026-07-31",
     "value": 14.0
    }
   ]
  }
 ]
}
```

## Hard constraints

- Use **only** the numbers listed above. Invent nothing.
- Do **not** compute new figures from these numbers — no totals, no differences, no percentages of percentages, no annualising.
- **Charts:** plot only the points in `chart_series`; label axes from those values; add no point, trendline, or projection that is not in the data.
- Do not look anything up. This prompt is the whole world for this pager.
- Do not add forecasts, targets, or attributions to any policy or event.
- Keep the data vintage line on the pager exactly as given above.
- **One idea per slide; headline ≤ 7 words; body ≤ 25 words.** Vary the layouts (see the kit).
- If something seems missing, leave it out rather than filling the gap.

<sub>generated by analysis/distribution/generate_slot.py · category C6 · 2026-08-14</sub>
