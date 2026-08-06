# Design prompt — 2026-08-04 · Headline levels (C1)

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

### Bank credit at ₹219.3L Cr — highest on record

Total bank credit outstanding reached ₹219.3L Cr in June 2026, the highest level on record. Volume climbed ₹4.1L Cr period-on-period (₹215.2L Cr → ₹219.3L Cr), the largest monthly gain in this ten-period window and a continuation of the upward trajectory from ₹178.7L Cr in January 2025.

*So what:* June's ₹4.1L Cr gain is the largest monthly addition in this dataset, pushing the book to a new all-time high. The credit cycle is expanding at an accelerating pace, with no sign of the post-year-end correction that briefly slowed April.

<sub>source: sibc_l1_annotations.json → bankCredit · signals: sibc-bank-credit-abs</sub>

### Personal loans at 15.76% YoY — re-accelerating after May dip

Personal loans credit grew 15.76% YoY in Jun 2026, up from 15.38% last period. Growth re-accelerated 0.38pp from 15.38% to 15.76%, reversing the prior period's deceleration and climbing back near the 75th percentile (15.8%).

*So what:* Personal loans have bounced back from the May 2026 dip — the re-acceleration to 15.76% confirms the prior slowdown was a pause, not a trend break. The sector remains in a solid growth phase, though no longer at the top of the range.

<sub>source: sibc_l1_annotations.json → mainSectors · signals: sibc-personal-loans-yoy</sub>

### Credit cards +9.57% YoY — fastest growth in 17 months

Credit cards outstanding grew 9.57% year-on-year in Jun 2026, up 1.10 points from 8.47% prior period. YoY growth re-accelerated for the fifth consecutive period: 7.7% in Feb 2026 → 8.0% in Mar 2026 → 8.1% in Apr 2026 → 8.5% in May 2026 → 9.6% in Jun 2026. The rate is now at the upper end of the 18-period range (6.7%–9.6%).

<sub>source: atm_pos_insights.json → cc · signals: cc-outstanding-yoy</sub>

### POS terminal growth -15.8% YoY — but it's ICICI Bank, not the market

The headline -15.8% year-on-year move is almost entirely ICICI Bank: its reported count fell sharply in a single month and accounts for nearly all of the change, while across every other bank the fleet edged up over the year. This looks like a base or reporting change at ICICI Bank — most likely a reclassification of how terminals are counted — not a market-wide shift. (The specific reason is not yet sourced; the concentration is straight from the bank-level data.)

*So what:* Read the market signal off the other banks — flat-to-steady — not the headline, which is ICICI Bank's reporting change.

<sub>source: atm_pos_insights.json → infra · signals: pos-terminals-yoy</sub>

## The numbers you may use

This is the complete set. Nothing outside it may appear on the pager. `supplied_numbers` are the figures you may print; `chart_series` are the trailing histories you may **plot** — one array per claim, already in reading order. Plot these points as given; do not add, interpolate, or extend them.

```json
{
 "supplied_numbers": [
  {
   "value": "₹219.3L Cr",
   "claim": "sibc-bank-credit-abs",
   "signals": [
    "sibc-bank-credit-abs"
   ]
  },
  {
   "value": "₹4.1L Cr",
   "claim": "sibc-bank-credit-abs",
   "signals": [
    "sibc-bank-credit-abs"
   ]
  },
  {
   "value": "₹215.2L Cr",
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
   "value": "15.76%",
   "claim": "sibc-personal-loans-yoy",
   "signals": [
    "sibc-personal-loans-yoy"
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
   "value": "0.38pp",
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
   "value": "15.8%",
   "claim": "sibc-personal-loans-yoy",
   "signals": [
    "sibc-personal-loans-yoy"
   ]
  },
  {
   "value": "9.57%",
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
   "value": "1.10",
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
   "value": "8.5%",
   "claim": "cc-cards-yoy",
   "signals": [
    "cc-outstanding-yoy"
   ]
  },
  {
   "value": "9.6%",
   "claim": "cc-cards-yoy",
   "signals": [
    "cc-outstanding-yoy"
   ]
  },
  {
   "value": "18",
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
   "value": "0.2",
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
   "value": "-15.8%",
   "claim": "infra-pos-yoy",
   "signals": [
    "pos-terminals-yoy"
   ]
  }
 ],
 "chart_series": [
  {
   "claim": "sibc-bank-credit-abs",
   "signal": "sibc-bank-credit-abs",
   "unit": "",
   "series": [
    {
     "period": "2025-02-28",
     "value": 17868478.53
    },
    {
     "period": "2025-03-30",
     "value": 18125412.6
    },
    {
     "period": "2025-04-30",
     "value": 18401354.28
    },
    {
     "period": "2026-01-30",
     "value": 20322515.47
    },
    {
     "period": "2026-02-27",
     "value": 20475381.96
    },
    {
     "period": "2026-03-30",
     "value": 20754077.69
    },
    {
     "period": "2026-04-30",
     "value": 21361434.74
    },
    {
     "period": "2026-05-29",
     "value": 21211828.32
    },
    {
     "period": "2026-06-30",
     "value": 21515965.07
    },
    {
     "period": "2026-07-31",
     "value": 21928364.69
    }
   ]
  },
  {
   "claim": "sibc-personal-loans-yoy",
   "signal": "sibc-personal-loans-yoy",
   "unit": "",
   "series": [
    {
     "period": "2025-02-28",
     "value": 11.85
    },
    {
     "period": "2025-03-30",
     "value": 11.74
    },
    {
     "period": "2025-04-30",
     "value": 11.69
    },
    {
     "period": "2026-01-30",
     "value": 14.38
    },
    {
     "period": "2026-02-27",
     "value": 14.94
    },
    {
     "period": "2026-03-30",
     "value": 15.22
    },
    {
     "period": "2026-04-30",
     "value": 16.21
    },
    {
     "period": "2026-05-29",
     "value": 16.01
    },
    {
     "period": "2026-06-30",
     "value": 15.38
    },
    {
     "period": "2026-07-31",
     "value": 15.76
    }
   ]
  },
  {
   "claim": "cc-cards-yoy",
   "signal": "cc-outstanding-yoy",
   "unit": "",
   "series": [
    {
     "period": "2025-06-30",
     "value": 6.89
    },
    {
     "period": "2025-07-31",
     "value": 6.92
    },
    {
     "period": "2025-08-31",
     "value": 6.71
    },
    {
     "period": "2025-09-30",
     "value": 6.98
    },
    {
     "period": "2025-10-31",
     "value": 6.78
    },
    {
     "period": "2025-11-30",
     "value": 7.24
    },
    {
     "period": "2025-12-31",
     "value": 7.16
    },
    {
     "period": "2026-01-31",
     "value": 7.15
    },
    {
     "period": "2026-02-28",
     "value": 7.67
    },
    {
     "period": "2026-03-31",
     "value": 7.96
    },
    {
     "period": "2026-04-30",
     "value": 8.15
    },
    {
     "period": "2026-05-31",
     "value": 8.47
    },
    {
     "period": "2026-06-30",
     "value": 9.57
    }
   ]
  },
  {
   "claim": "infra-pos-yoy",
   "signal": "pos-terminals-yoy",
   "unit": "",
   "series": [
    {
     "period": "2025-06-30",
     "value": 31.4
    },
    {
     "period": "2025-07-31",
     "value": 32.79
    },
    {
     "period": "2025-08-31",
     "value": 28.64
    },
    {
     "period": "2025-09-30",
     "value": 29.68
    },
    {
     "period": "2025-10-31",
     "value": 29.43
    },
    {
     "period": "2025-11-30",
     "value": 16.12
    },
    {
     "period": "2025-12-31",
     "value": 14.74
    },
    {
     "period": "2026-01-31",
     "value": 11.52
    },
    {
     "period": "2026-02-28",
     "value": 8.84
    },
    {
     "period": "2026-03-31",
     "value": 6.05
    },
    {
     "period": "2026-04-30",
     "value": 1.45
    },
    {
     "period": "2026-05-31",
     "value": -0.48
    },
    {
     "period": "2026-06-30",
     "value": -15.79
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

<sub>generated by analysis/distribution/generate_slot.py · category C1 · 2026-08-04</sub>
