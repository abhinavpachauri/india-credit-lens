# Design prompt — 2026-08-28 · Watchlist (C8)

**Slot:** 28th of the month
**Question this answers:** What could flip next month
**Data vintage:** Both halves are on the same data month: June 2026 credit data and June 2026 payments data.

## Format

- **LinkedIn carousel PDF, portrait 1080×1350 (4:5)** — fills the mobile feed. Not landscape.
- **4 slides**, one idea per slide. Slide 1 is the hook; the last slide signs off + invites a subscribe.
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

A distance-to-the-line layout: current value, the threshold, and the gap between. Nearest first.

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

Each block below was written deterministically from signals.db — the wording is the generator's, the numbers are the database's. Use the wording as the source of truth for what is being said; you may shorten for the page, but you may not change a number or add a qualifier that is not here.

### Pair divergence — debit cards issued vs spent on (YoY gap, pp)

Pair divergence — debit cards issued vs spent on (YoY gap, pp) is 3.3 pp and reads accelerating. A fall to 3.0 pp would change that reading to steady — a move of 0.3 pp, against a typical monthly move of 2.5 pp.

<sub>source: signals/proximity.py — distance to the next status flip · signals: dc-issuance-vs-spend-gap</sub>

### Consumer Durables YoY growth (%)

Consumer Durables YoY growth (%) is -0.6% and reads falling. A rise to 0.0% would change that reading to accelerating — a move of 0.6%, against a typical monthly move of 3.6%.

<sub>source: signals/proximity.py — distance to the next status flip · signals: sibc-pl-consumer-durables-yoy</sub>

## The numbers you may use

This is the complete set. Nothing outside it may appear on the pager. `supplied_numbers` are the figures you may print; `chart_series` are the trailing histories you may **plot** — one array per claim, already in reading order. Plot these points as given; do not add, interpolate, or extend them.

```json
{
 "supplied_numbers": [
  {
   "value": "3.3 pp",
   "claim": "dc-issuance-vs-spend-gap",
   "signals": [
    "dc-issuance-vs-spend-gap"
   ]
  },
  {
   "value": "3.0 pp",
   "claim": "dc-issuance-vs-spend-gap",
   "signals": [
    "dc-issuance-vs-spend-gap"
   ]
  },
  {
   "value": "0.3 pp",
   "claim": "dc-issuance-vs-spend-gap",
   "signals": [
    "dc-issuance-vs-spend-gap"
   ]
  },
  {
   "value": "2.5 pp",
   "claim": "dc-issuance-vs-spend-gap",
   "signals": [
    "dc-issuance-vs-spend-gap"
   ]
  },
  {
   "value": "-0.6%",
   "claim": "sibc-pl-consumer-durables-yoy",
   "signals": [
    "sibc-pl-consumer-durables-yoy"
   ]
  },
  {
   "value": "0.0%",
   "claim": "sibc-pl-consumer-durables-yoy",
   "signals": [
    "sibc-pl-consumer-durables-yoy"
   ]
  },
  {
   "value": "0.6%",
   "claim": "sibc-pl-consumer-durables-yoy",
   "signals": [
    "sibc-pl-consumer-durables-yoy"
   ]
  },
  {
   "value": "3.6%",
   "claim": "sibc-pl-consumer-durables-yoy",
   "signals": [
    "sibc-pl-consumer-durables-yoy"
   ]
  }
 ],
 "chart_series": [
  {
   "claim": "dc-issuance-vs-spend-gap",
   "signal": "dc-issuance-vs-spend-gap",
   "unit": "",
   "series": [
    {
     "period": "2025-06-30",
     "value": 18.41
    },
    {
     "period": "2025-07-31",
     "value": 19.9
    },
    {
     "period": "2025-08-31",
     "value": 19.16
    },
    {
     "period": "2025-09-30",
     "value": 13.55
    },
    {
     "period": "2025-10-31",
     "value": 14.68
    },
    {
     "period": "2025-11-30",
     "value": 17.81
    },
    {
     "period": "2025-12-31",
     "value": 12.57
    },
    {
     "period": "2026-01-31",
     "value": 8.25
    },
    {
     "period": "2026-02-28",
     "value": 9.19
    },
    {
     "period": "2026-03-31",
     "value": 8.31
    },
    {
     "period": "2026-04-30",
     "value": 5.82
    },
    {
     "period": "2026-05-31",
     "value": 7.08
    },
    {
     "period": "2026-06-30",
     "value": 3.35
    }
   ]
  },
  {
   "claim": "sibc-pl-consumer-durables-yoy",
   "signal": "sibc-pl-consumer-durables-yoy",
   "unit": "",
   "series": [
    {
     "period": "2025-02-28",
     "value": -2.38
    },
    {
     "period": "2025-03-30",
     "value": 2.6
    },
    {
     "period": "2025-04-30",
     "value": -1.04
    },
    {
     "period": "2026-01-30",
     "value": -5.15
    },
    {
     "period": "2026-02-27",
     "value": -4.04
    },
    {
     "period": "2026-03-30",
     "value": -9.78
    },
    {
     "period": "2026-04-30",
     "value": -5.34
    },
    {
     "period": "2026-05-29",
     "value": -3.38
    },
    {
     "period": "2026-06-30",
     "value": -2.64
    },
    {
     "period": "2026-07-31",
     "value": -0.64
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

<sub>generated by analysis/distribution/generate_slot.py · category C8 · 2026-08-28</sub>
