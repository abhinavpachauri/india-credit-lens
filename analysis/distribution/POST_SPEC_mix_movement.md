# Post spec — mix movement (2 LinkedIn carousels)

**Who writes what.** You write the words. This file gives you (a) the numbers, already checked
against `signals.db` and the consolidated CSV, (b) a suggested arc, (c) the traps — sentences that
are tempting and wrong — and (d) a design brief to paste into Claude Design.

**One hard rule, carried over from the slot generator (`DISTRIBUTION_SPEC` §5.1).** The design
session sits *outside* the gate, so it is the one place a made-up number could reach a reader.
**Every figure it is given must be quoted from this file. It invents nothing and derives nothing** —
no percentages it worked out itself, no totals it added up.

Category per `DISTRIBUTION_SPEC` §3: **Post 1 = C2** (rotation — what's gaining ground, at whose
expense). **Post 2 = C10** (method / AI PM), which has no generator by design and is assembled by
hand.

---

## POST 1 — "The mix didn't move. Look one level down."

### The one claim
The chart everyone looks at — four sectors, share of the book — is the **one cut where India's
credit mix moved least**. Go one level down and the same three years show swings of 7 to 27 points.

### The numbers (verbatim — do not recompute)

**Level 1, the chart everyone shows.** Book grew **₹152 L Cr → ₹207 L Cr** (Dec 2023 → Jun 2026):

| sector | Dec 2023 | Jun 2026 | change |
|---|---|---|---|
| Agriculture | 13.10% | 12.99% | −0.10 pp |
| Industry | 23.83% | 23.02% | −0.81 pp |
| Services | 28.95% | 29.68% | +0.73 pp |
| Personal Loans | 34.13% | 34.31% | +0.19 pp |

**Level 2, where the money actually went.** "Tilt" = a segment's share of *new* lending minus its
share of the existing book. Swing = how far that tilt travelled, Feb 2025 → Jul 2026:

| cut | gained most | swing | lost most | swing |
|---|---|---|---|---|
| **Services** | **NBFCs** | **+27.2 pp** | Other Services | −14.7 pp |
| Priority Sector | Housing | +12.4 pp | Weaker Sections | −9.0 pp |
| Industry by type | Infrastructure | +11.4 pp | Basic Metal | −6.5 pp |
| Personal Loans | Gold loans | +10.5 pp | Housing | −11.6 pp |
| Main sectors | Industry | +7.3 pp | Personal Loans | −7.0 pp |
| Industry by size | Large | +3.6 pp | Medium | −4.8 pp |

NBFCs went from taking **11.3 points less** than their weight to **15.9 points more**. The
main-sector pair — the one the headline chart shows — is the **smallest** move in the table.

**And in payments, the extreme case.** POS terminals, 12 months to May 2026:

| bank category | terminals |
|---|---|
| Public Sector Banks | **+204,595** |
| Small Finance Banks | +270 |
| Foreign Banks | −3,460 |
| Private Sector Banks | **−257,290** |
| **net** | **−55,885** |
| **total movement** | **465,615** |

**465,615 terminals changed hands to produce a headline that says the fleet shrank by 55,885.**

### Suggested arc (6 slides)
1. **Hook** — the four shares, three years apart, all within a point. "Nothing happened."
2. **One level down** — the swing table. NBFCs +27.2. Same three years, same book.
3. **Why level 1 can't show it** — a year's lending is ~15% of the book, and moves that reverse
   cancel. The mix is an average of movements going opposite ways.
4. **The extreme** — POS terminals. 465,615 moved; the headline says −55,885.
5. **Caveat slide** *(sand background)* — "personal loans collapsed" is wrong. They grew **15.76%
   YoY**, still accelerating **(+0.38 pp)**, ₹6.4 L Cr → ₹9.7 L Cr. A smaller slice of a bigger pie.
6. **Sign-off.**

### Traps — do not write these
- ❌ "Banks pulled back from personal loans." They didn't. Growth **accelerated**.
- ❌ "The mix is frozen." It is the opposite — the *summary* is flat, the mix is not.
- ❌ Any claim about *why*. This is a composition read; the cause is not in this data.
- ❌ Forecasts. Nothing about next quarter.
- ❌ Naming the issuer behind the POS move. The category-level fact stands on its own; the
  attribution is a separate, sourced claim.

## POST 2 — "Do the parts agree? That's arithmetic, not a judgement."

### The one claim
When you say "credit is expanding", you are summarising parts that may disagree. Whether they agree
is a *measurable quantity*, not an editorial call — and measuring it changed what we publish.

### The numbers (verbatim)

The measure, in full:

```
coherence = | sum of the changes |  ÷  sum of the sizes of the changes
```

1.00 = every part moving the same way. 0.00 = they cancel exactly. **No model involved.**

Across the seven cuts of Indian bank credit (Jun 2026):

| cut | coherence |
|---|---|
| main sectors, industry ×2, services, personal loans | 1.000 |
| priority sector | 0.993 |
| **infrastructure sub-types** | **0.778** |

And across payments, over 18 windows each — this is where the vocabulary earns itself:

| metric | aligned | contested | handover |
|---|---|---|---|
| credit cards | 18 | — | — |
| debit cards | 12 | 6 | — |
| **POS terminals** | 12 | 5 | **1** |

Resulting states: **2 steered, 4 drifting, 1 contested.** Main sectors are *steered* toward Services
(**+4.9 pp** tilt) away from Personal Loans; services *steered* toward NBFCs (**+15.9 pp**).

**The two cards that made the case.** Before this, two cross-system readings published in identical
words — *"expanding (5/5 measurements observed)"*. One had five members all rising. The other had
**three rising, one falling, one flat**. "5/5" is *coverage* — how many parts we could see — and
every reader takes it as *agreement*.

**The reversal worth telling.** It was first specced as a **publish gate** — suppress the reading
when the parts disagree. The data killed that: the two lowest-coherence windows in the entire
dataset were the **best stories** — a POS-terminal handover (private banks **−257,290**, public
**+204,595**, net only **−55,885**) and a debit-card e-commerce consolidation (private **+4.24M**,
public **−2.49M**). A gate would have silenced exactly those. It became a **router**: coherence now
picks *which sentence is true*, and nothing computed is ever suppressed.

### Suggested arc (6 slides)
1. **Hook** — two sentences, identical wording. One is 5-0. One is 3-1-1. Which is which?
2. **The measure** — the one-line formula. Plain, no model.
3. **What it reads across Indian credit** — 1.000 six times, 0.778 once.
4. **The reversal** *(sand background)* — I built it as a filter. The filter was deleting the best
   material. The POS numbers.
5. **What it does now** — routes to one of three sentences: aligned / contested / handover.
6. **Sign-off.**

### Traps — do not write these
- ❌ "We used AI to measure agreement." **We did not.** It is one line of arithmetic, and that is
  the point of the post.
- ❌ Quoting a coherence number as a percentage in prose without the cut it belongs to.
- ❌ Naming clients, banks-as-advice, or anything that reads as a recommendation (§10 voice rules).

---

## Design brief — paste this into Claude Design

Both posts use the house system already defined in `slot_render.py`. Give the design session:

- **Format:** LinkedIn carousel PDF, **portrait 1080×1350 (4:5)**, 6 slides, one idea per slide.
  Mobile-first — legible at arm's length. Headline ≤ 7 words, body ≤ 25 words, the number is the
  hero. Fill the canvas; no slide more than ~30% empty.
- **Palette:** ink `#0f1720` text · **credit-blue `#1f6feb`** for numbers and the series that
  matters · **muted sand `#efe7dc`** reserved *only* for the caveat slide, so it reads differently
  at a glance · off-white `#f4f7fb` background · one dark closing slide.
- **Type:** one strong grotesk. Stats huge. Eyebrow labels in small caps, same position every slide.
- **Charts:** axis-light. Colour the one series that matters, grey the rest. No gridline decoration,
  no 3-D, no legend a caption can replace.
- **Brand:** small wordmark + `indiacreditlens.com` + page counter, same position on every slide.
- **Vary the layouts** — the failure mode is one template repeated six times.

### ASCII layouts — approve before any design work

**POST 1**

```
SLIDE 1 (hook)                     SLIDE 2 (one level down)
+---------------------------+      +---------------------------+
| INDIA CREDIT LENS      1/6|      | SAME BOOK, ONE LEVEL   2/6|
|                           |      | DOWN                      |
|  Three years.             |      |                           |
|  Four sectors.            |      |   NBFCs        +27.2 pp   |
|  Nothing moved.           |      |   PSL Housing  +12.4 pp   |
|                           |      |   Gold loans   +10.5 pp   |
|  13.1 -> 13.0             |      |   ------------------------|
|  23.8 -> 23.0             |      |   Main sectors  +7.3 pp   |
|  29.0 -> 29.7             |      |   <- the chart on slide 1 |
|  34.1 -> 34.3             |      |                           |
|                           |      |  [h-bars, NBFC blue and   |
|  ...that's the summary.   |      |   longest, main-sector    |
|     Not the mix.          |      |   bar grey and shortest]  |
+---------------------------+      +---------------------------+

SLIDE 3 (why it hides)             SLIDE 4 (the extreme)
+---------------------------+      +---------------------------+
| WHY THE TOP LINE     3/6  |      | 465,615 MOVED          4/6|
| CAN'T SHOW IT             |      |                           |
|                           |      |   Public banks  +204,595  |
|  A year's lending is only |      |   Private banks -257,290  |
|  a sixth of the book.     |      |   ----------------------- |
|                           |      |   Headline       -55,885  |
|  And a tilt that reverses |      |                           |
|  gives back what it took. |      |  POS terminals, year to   |
|                           |      |  May 2026.                |
|  [two arrows, opposite,   |      |                           |
|   cancelling to a stub]   |      |  Nearly half a million    |
|                           |      |  changed hands.           |
+---------------------------+      +---------------------------+

SLIDE 5 (caveat -- SAND bg)        SLIDE 6 (sign-off -- DARK)
+---------------------------+      +---------------------------+
| LOOKS RIGHT, ISN'T     5/6|      |                        6/6|
|                           |      |   INDIA CREDIT LENS       |
|  "Personal loans          |      |                           |
|   collapsed."             |      |   The mix didn't move.    |
|                           |      |   Look one level down.    |
|  They grew 15.76% YoY.    |      |                           |
|  Still accelerating.      |      |   RBI SIBC + ATM/POS,     |
|  Rs 6.4 L Cr -> 9.7 L Cr  |      |   read monthly.           |
|                           |      |                           |
|  A smaller slice of a     |      |   indiacreditlens.com     |
|  much bigger pie.         |      |                           |
+---------------------------+      +---------------------------+
```

**POST 2**

```
SLIDE 1 (hook)                     SLIDE 2 (the measure)
+---------------------------+      +---------------------------+
| INDIA CREDIT LENS      1/6|      | THE MEASURE            2/6|
|                           |      |                           |
|  Two readings.            |      |   |sum of changes|        |
|  Same six words.          |      |   ------------------      |
|                           |      |   sum of |changes|        |
|  "expanding               |      |                           |
|   (5/5 measurements)"     |      |   1.00 = all one way      |
|                           |      |   0.00 = they cancel      |
|  One is 5-0.              |      |                           |
|  One is 3-1-1.            |      |   No model. No judgement. |
|                           |      |   One line of arithmetic. |
|  Which one?               |      |                           |
+---------------------------+      +---------------------------+

SLIDE 3 (across the book)          SLIDE 4 (reversal -- SAND bg)
+---------------------------+      +---------------------------+
| SEVEN CUTS             3/6|      | I BUILT IT BACKWARDS   4/6|
|                           |      |                           |
|  1.000  main sectors      |      |  I specced it as a filter:|
|  1.000  industry x2       |      |  hide the reading when    |
|  1.000  services          |      |  the parts disagree.      |
|  1.000  personal loans    |      |                           |
|  0.993  priority sector   |      |  POS terminals:           |
|                           |      |   private   -257,290      |
|  0.778  infrastructure    |      |   public    +204,595      |
|         ^^^^^^^^^^^^^^    |      |   net        -55,885      |
|  the one that disagrees   |      |                           |
|                           |      |  The filter was deleting  |
|  [7 bars, six full blue,  |      |  the best story I had.    |
|   one short, sand-tipped] |      |                           |
+---------------------------+      +---------------------------+

SLIDE 5 (what it does now)         SLIDE 6 (sign-off -- DARK)
+---------------------------+      +---------------------------+
| IT ROUTES, NOT GATES   5/6|      |                        6/6|
|                           |      |   INDIA CREDIT LENS       |
|  >= 0.90   "X took N% of  |      |                           |
|            the new money" |      |   Whether the parts agree |
|                           |      |   is a number, not an     |
|  0.50-0.90 "...but these  |      |   opinion.                |
|            moved against" |      |                           |
|                           |      |   How this dashboard is   |
|  < 0.50    "a handover,   |      |   built, monthly.         |
|            not growth"    |      |                           |
|                           |      |   indiacreditlens.com     |
|  Nothing is suppressed.   |      |                           |
+---------------------------+      +---------------------------+
```

**Slide 5 of Post 1 and slide 4 of Post 2 are the sand slides** — the "looks right, isn't" moment.
They are the most valuable slide in each deck; give them room.
