# Design prompt — 2026-08-07 · Rotation (C2)

**Slot:** 7th of the month
**Question this answers:** What's gaining ground, at whose expense
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

Show the mix moving: who gained share, who gave it up, and how much of the mix changed hands in total. A before/after of the same pie reads better than a bar chart.

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

This is the complete set. Nothing outside it may appear on the pager. `supplied_numbers` are the figures you may print; `chart_series` are the trailing histories you may **plot** — one array per claim, already in reading order. Plot these points as given; do not add, interpolate, or extend them.

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
 ],
 "chart_series": [
  {
   "claim": "sibc-services-rotation",
   "signal": "sibc-services-rotation",
   "unit": "",
   "series": [
    {
     "period": "2025-02-28",
     "value": 1.47
    },
    {
     "period": "2025-03-30",
     "value": 1.22
    },
    {
     "period": "2025-04-30",
     "value": 1.53
    },
    {
     "period": "2026-01-30",
     "value": 0.97
    },
    {
     "period": "2026-02-27",
     "value": 0.97
    },
    {
     "period": "2026-03-30",
     "value": 1.61
    },
    {
     "period": "2026-04-30",
     "value": 2.31
    },
    {
     "period": "2026-05-29",
     "value": 2.73
    },
    {
     "period": "2026-06-30",
     "value": 3.72
    },
    {
     "period": "2026-07-31",
     "value": 3.08
    }
   ]
  },
  {
   "claim": "sibc-pl-rotation",
   "signal": "sibc-pl-rotation",
   "unit": "",
   "series": [
    {
     "period": "2025-02-28",
     "value": 1.51
    },
    {
     "period": "2025-03-30",
     "value": 1.54
    },
    {
     "period": "2025-04-30",
     "value": 1.82
    },
    {
     "period": "2026-01-30",
     "value": 3.09
    },
    {
     "period": "2026-02-27",
     "value": 3.16
    },
    {
     "period": "2026-03-30",
     "value": 3.29
    },
    {
     "period": "2026-04-30",
     "value": 3.47
    },
    {
     "period": "2026-05-29",
     "value": 3.52
    },
    {
     "period": "2026-06-30",
     "value": 3.39
    },
    {
     "period": "2026-07-31",
     "value": 3.18
    }
   ]
  },
  {
   "claim": "sibc-industry-rotation",
   "signal": "sibc-industry-rotation",
   "unit": "",
   "series": [
    {
     "period": "2025-02-28",
     "value": 2.47
    },
    {
     "period": "2025-03-30",
     "value": 2.44
    },
    {
     "period": "2025-04-30",
     "value": 2.44
    },
    {
     "period": "2026-01-30",
     "value": 2.4
    },
    {
     "period": "2026-02-27",
     "value": 2.41
    },
    {
     "period": "2026-03-30",
     "value": 2.68
    },
    {
     "period": "2026-04-30",
     "value": 2.66
    },
    {
     "period": "2026-05-29",
     "value": 2.43
    },
    {
     "period": "2026-06-30",
     "value": 2.83
    },
    {
     "period": "2026-07-31",
     "value": 3.23
    }
   ]
  },
  {
   "claim": "cc-category-rotation",
   "signal": "cc-category-rotation",
   "unit": "",
   "series": [
    {
     "period": "2025-06-30",
     "value": 0.67
    },
    {
     "period": "2025-07-31",
     "value": 0.6
    },
    {
     "period": "2025-08-31",
     "value": 0.53
    },
    {
     "period": "2025-09-30",
     "value": 0.47
    },
    {
     "period": "2025-10-31",
     "value": 0.36
    },
    {
     "period": "2025-11-30",
     "value": 0.39
    },
    {
     "period": "2025-12-31",
     "value": 0.44
    },
    {
     "period": "2026-01-31",
     "value": 0.53
    },
    {
     "period": "2026-02-28",
     "value": 0.64
    },
    {
     "period": "2026-03-31",
     "value": 0.69
    },
    {
     "period": "2026-04-30",
     "value": 0.75
    },
    {
     "period": "2026-05-31",
     "value": 0.7
    },
    {
     "period": "2026-06-30",
     "value": 0.86
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

<sub>generated by analysis/distribution/generate_slot.py · category C2 · 2026-08-07</sub>
