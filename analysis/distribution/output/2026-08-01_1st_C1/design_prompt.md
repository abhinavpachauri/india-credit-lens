# Design prompt — 2026-08-01 · Headline levels (C1)

**Slot:** 1st of the month
**Question this answers:** What are the numbers
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

Open with the headline level, then the two or three numbers that qualify it. The reader should leave knowing the size and the direction, nothing more.

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

### Bank credit grew 18.6% YoY — fastest in this dataset

Bank credit grew 18.6% year-on-year in June 2026, the fastest rate in this ten-period window. Growth accelerated 1.0 percentage point (17.7% → 18.6%), extending the re-acceleration that began in May and reaching a new high above the prior May 2026 peak of 17.7%.

*So what:* June's 18.6% growth is the fastest in this dataset, with the system now expanding at a pace not seen in the prior nine periods. The two-month acceleration from April confirms the credit cycle is strengthening, not plateauing.

<sub>source: sibc_l1_annotations.json → bankCredit · signals: sibc-bank-credit-yoy</sub>

### Agriculture share flat at 12.36% — unchanged from prior period

Agriculture's share of total bank credit stands at 12.36% in Jun 2026. Share unchanged at 12.36%, identical to the prior period and holding near the median of its ten-period range (12.3%–12.5%).

*So what:* Agriculture holds a steady 12.4% slice of the book, unchanged in character from the prior period. The sector is neither gaining nor losing ground — lenders face no rebalancing pressure.

<sub>source: sibc_l1_annotations.json → mainSectors · signals: sibc-agriculture-share</sub>

### Large corporates 67.4% of industry credit — share ticking up

Large corporates account for 67.4% of industry credit in Jun 2026, up 0.17pp from the prior period. Share rose from 67.3% in May 2026 to 67.4% in Jun 2026. The trajectory over the last six periods is 67.3% → 66.8% → 67.1% → 67.2% → 67.2% → 67.3% → 67.4%.

*So what:* Large corporates are ticking up in share for the first time since the plateau began. The 0.17pp gain is small but breaks the five-period hold at 67.2–67.3%. If this continues, it signals large corporates are recapturing incremental credit from MSME segments — but one period is not yet a trend.

<sub>source: sibc_l1_annotations.json → industryBySize · signals: sibc-large-corporate-share</sub>

### Education loans at 2.22% of personal loans — record low

Education loans account for 2.22% of personal loans, the smallest share in this 10-period window. Share declined from 2.25% in May 2026 to 2.22% in Jun 2026 — a 0.02-point drop.

*So what:* The drop to 2.22% is a record low, confirming education loans are losing share despite steady 13% YoY growth. The segment is stable but not competitive with gold (which is growing faster) or housing (which dominates the mix).

<sub>source: sibc_l1_annotations.json → personalLoans · signals: sibc-pl-education-share</sub>

## The numbers you may use

This is the complete set. Nothing outside it may appear on the pager. `supplied_numbers` are the figures you may print; `chart_series` are the trailing histories you may **plot** — one array per claim, already in reading order. Plot these points as given; do not add, interpolate, or extend them.

```json
{
 "supplied_numbers": [
  {
   "value": "18.6%",
   "claim": "sibc-bank-credit-yoy",
   "signals": [
    "sibc-bank-credit-yoy"
   ]
  },
  {
   "value": "1.0",
   "claim": "sibc-bank-credit-yoy",
   "signals": [
    "sibc-bank-credit-yoy"
   ]
  },
  {
   "value": "17.7%",
   "claim": "sibc-bank-credit-yoy",
   "signals": [
    "sibc-bank-credit-yoy"
   ]
  },
  {
   "value": "12.36%",
   "claim": "sibc-agriculture-share",
   "signals": [
    "sibc-agriculture-share"
   ]
  },
  {
   "value": "12.3%",
   "claim": "sibc-agriculture-share",
   "signals": [
    "sibc-agriculture-share"
   ]
  },
  {
   "value": "12.5%",
   "claim": "sibc-agriculture-share",
   "signals": [
    "sibc-agriculture-share"
   ]
  },
  {
   "value": "12.4%",
   "claim": "sibc-agriculture-share",
   "signals": [
    "sibc-agriculture-share"
   ]
  },
  {
   "value": "67.4%",
   "claim": "sibc-large-corporate-share",
   "signals": [
    "sibc-large-corporate-share"
   ]
  },
  {
   "value": "0.17pp",
   "claim": "sibc-large-corporate-share",
   "signals": [
    "sibc-large-corporate-share"
   ]
  },
  {
   "value": "67.3%",
   "claim": "sibc-large-corporate-share",
   "signals": [
    "sibc-large-corporate-share"
   ]
  },
  {
   "value": "66.8%",
   "claim": "sibc-large-corporate-share",
   "signals": [
    "sibc-large-corporate-share"
   ]
  },
  {
   "value": "67.1%",
   "claim": "sibc-large-corporate-share",
   "signals": [
    "sibc-large-corporate-share"
   ]
  },
  {
   "value": "67.2%",
   "claim": "sibc-large-corporate-share",
   "signals": [
    "sibc-large-corporate-share"
   ]
  },
  {
   "value": "67.2",
   "claim": "sibc-large-corporate-share",
   "signals": [
    "sibc-large-corporate-share"
   ]
  },
  {
   "value": "2.22%",
   "claim": "sibc-pl-education-share",
   "signals": [
    "sibc-pl-education-share"
   ]
  },
  {
   "value": "10",
   "claim": "sibc-pl-education-share",
   "signals": [
    "sibc-pl-education-share"
   ]
  },
  {
   "value": "2.25%",
   "claim": "sibc-pl-education-share",
   "signals": [
    "sibc-pl-education-share"
   ]
  },
  {
   "value": "0.02",
   "claim": "sibc-pl-education-share",
   "signals": [
    "sibc-pl-education-share"
   ]
  },
  {
   "value": "13%",
   "claim": "sibc-pl-education-share",
   "signals": [
    "sibc-pl-education-share"
   ]
  }
 ],
 "chart_series": [
  {
   "claim": "sibc-bank-credit-yoy",
   "signal": "sibc-bank-credit-yoy",
   "unit": "",
   "series": [
    {
     "period": "2025-02-28",
     "value": 11.37
    },
    {
     "period": "2025-03-30",
     "value": 11.11
    },
    {
     "period": "2025-04-30",
     "value": 10.95
    },
    {
     "period": "2026-01-30",
     "value": 14.54
    },
    {
     "period": "2026-02-27",
     "value": 14.59
    },
    {
     "period": "2026-03-30",
     "value": 14.5
    },
    {
     "period": "2026-04-30",
     "value": 16.09
    },
    {
     "period": "2026-05-29",
     "value": 16.01
    },
    {
     "period": "2026-06-30",
     "value": 17.65
    },
    {
     "period": "2026-07-31",
     "value": 18.62
    }
   ]
  },
  {
   "claim": "sibc-agriculture-share",
   "signal": "sibc-agriculture-share",
   "unit": "",
   "series": [
    {
     "period": "2025-02-28",
     "value": 12.65
    },
    {
     "period": "2025-03-30",
     "value": 12.52
    },
    {
     "period": "2025-04-30",
     "value": 12.45
    },
    {
     "period": "2026-01-30",
     "value": 12.4
    },
    {
     "period": "2026-02-27",
     "value": 12.31
    },
    {
     "period": "2026-03-30",
     "value": 12.3
    },
    {
     "period": "2026-04-30",
     "value": 12.42
    },
    {
     "period": "2026-05-29",
     "value": 12.44
    },
    {
     "period": "2026-06-30",
     "value": 12.36
    },
    {
     "period": "2026-07-31",
     "value": 12.36
    }
   ]
  },
  {
   "claim": "sibc-large-corporate-share",
   "signal": "sibc-large-corporate-share",
   "unit": "",
   "series": [
    {
     "period": "2025-02-28",
     "value": 71.01
    },
    {
     "period": "2025-03-30",
     "value": 70.72
    },
    {
     "period": "2025-04-30",
     "value": 70.85
    },
    {
     "period": "2026-01-30",
     "value": 67.32
    },
    {
     "period": "2026-02-27",
     "value": 66.79
    },
    {
     "period": "2026-03-30",
     "value": 67.12
    },
    {
     "period": "2026-04-30",
     "value": 67.24
    },
    {
     "period": "2026-05-29",
     "value": 67.15
    },
    {
     "period": "2026-06-30",
     "value": 67.26
    },
    {
     "period": "2026-07-31",
     "value": 67.43
    }
   ]
  },
  {
   "claim": "sibc-pl-education-share",
   "signal": "sibc-pl-education-share",
   "unit": "",
   "series": [
    {
     "period": "2025-02-28",
     "value": 2.32
    },
    {
     "period": "2025-03-30",
     "value": 2.32
    },
    {
     "period": "2025-04-30",
     "value": 2.3
    },
    {
     "period": "2026-01-30",
     "value": 2.3
    },
    {
     "period": "2026-02-27",
     "value": 2.3
    },
    {
     "period": "2026-03-30",
     "value": 2.29
    },
    {
     "period": "2026-04-30",
     "value": 2.25
    },
    {
     "period": "2026-05-29",
     "value": 2.24
    },
    {
     "period": "2026-06-30",
     "value": 2.25
    },
    {
     "period": "2026-07-31",
     "value": 2.22
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

<sub>generated by analysis/distribution/generate_slot.py · category C1 · 2026-08-01</sub>
