# India Credit Lens — Report Analysis Prompt

Use this prompt with Claude to generate dashboard annotations and markdown documents
from a new RBI report. Feed it the sections JSON (exported from the dashboard) and
the original PDF report.

---

## Context

You are analysing RBI bank credit data for **India Credit Lens** — a public analytics
dashboard that helps banking professionals understand where credit is flowing, what's
growing, and where lending opportunities exist.

The dashboard shows 7 sections of credit data. Each section has:
- An **Absolute** view (₹ Crore outstanding over time)
- A **YoY Growth** view (same month vs prior year, e.g. Jan 2025 vs Jan 2024)
- An **FY Growth** view (vs previous March-end, e.g. Jan 2026 vs Mar 2025)

The audience is mid-to-senior banking professionals — credit officers, product heads,
risk teams, fintech founders — not academics or general public.

---

## Inputs you have

1. **sections.json** — the exact data the dashboard renders (attached). Contains:
   - `sections[].id` — section identifier used in code
   - `sections[].title` — display name
   - `sections[].seriesNames` — exact series names rendered in charts
   - `sections[].absoluteData` — array of `{date, [seriesName]: value}` points in ₹ Crore
   - `sections[].growthData` — YoY % growth for each series at each valid date
   - `sections[].fyData` — FY-to-date % growth for each series at each valid date

2. **PDF report** — the original RBI narrative (attached). Cross-reference claims in the
   text against what the numbers actually show.

---

## What to analyse

For each section, examine **every combination** that could yield insight:
- Every series vs every other series (share, relative growth, divergence)
- Every time period (Jan 2024, Mar 2024, Jan 2025, Mar 2025, Jan 2026)
- Absolute level vs YoY growth vs FY growth — they tell different stories
- What the PDF narrative says vs what the numbers actually show (tension = insight)
- Seasonal patterns (Jan vs March systematically differs for agriculture/food credit)
- Cross-section connections (growth in one section implies pressure in another)

Then across all sections:
- Causal chains: what is driving what
- Structural shifts: things that have been changing slowly and are now undeniable
- Gaps the RBI report doesn't mention but the data reveals

---

## Output 1 — Dashboard ANNOTATIONS (primary)

Produce a TypeScript object in exactly this shape, one entry per section:

```typescript
const ANNOTATIONS: Record<string, SectionAnnotations> = {
  [section.id]: {
    insights:      Annotation[],
    gaps:          Annotation[],
    opportunities: Annotation[],
  },
  // ... one entry per section
};
```

### Annotation schema

```typescript
interface Annotation {
  id:             string;           // kebab-case, unique, descriptive
  title:          string;           // 4–6 words, plain noun phrase
  body:           string;           // 2–3 sentences, see style guide below
  implication?:   string;           // "For lenders: ..." — practical so-what
  preferredMode?: "absolute" | "yoy" | "fy";  // which chart view to auto-switch to
  effect: {
    highlight?: string[];   // series to emphasise (full opacity, bold stroke)
    dim?:       string[];   // series to fade (20% opacity)
    dash?:      string[];   // series to show dashed (use for "misleading" or caveat series)
  };
}
```

### Hard constraints — MUST follow

1. **Every string in `highlight`, `dim`, `dash` must exactly match a name in
   `section.seriesNames`**. Copy-paste from the JSON. Do not paraphrase.

2. **Every date mentioned in `body` or `title` must match a `date` value in
   `absoluteData`** (formatted as "Jan 2024", "Mar 2024" etc). No invented dates.

3. **Every number cited must come from the data**. Compute values from the JSON;
   do not guess or round aggressively. Show the calculation if helpful.

4. **`preferredMode`**: use `"yoy"` when the annotation is about growth rates;
   `"absolute"` when it's about scale/level; `"fy"` when it's about within-year
   progress vs the FY start.

5. **Aim for 3–5 annotations per section per type** (insights/gaps/opportunities).
   Don't pad with weak observations but don't stop at 1–2 if more exist.

### Annotation type definitions

- **Insight** — something true and non-obvious about what's in the data.
  "Personal loans overtook industry credit" is an insight.

- **Gap** — a limitation, caveat, seasonal distortion, or missing piece that makes
  the data misleading if read naively. "January food credit spike is seasonal, not structural" is a gap.

- **Opportunity** — a specific, actionable lending opportunity for a credit professional.
  Must be grounded in the data, not generic advice.

### Writing style — strictly enforced

Write like a sharp analyst talking to a peer, not a consultant writing a deck.

**Good:**
> "Gold loans went from ₹0.92L Cr to ₹4.01L Cr in 24 months — a 335% increase.
> This is not a blip. Three consecutive data points show the same trajectory."

**Bad:**
> "Gold-secured retail credit has exhibited structural acceleration, reflecting
> a paradigm shift in collateral-backed consumer lending behaviour."

Rules:
- Use real numbers from the data, not ranges or approximations
- Name the specific series you're talking about
- One idea per sentence
- No jargon: not "paradigm", "trajectory", "ecosystem", "leverage", "unlock"
- `implication` should tell a lender specifically what to do or watch, not restate the body

---

## Output 2 — Markdown documents (secondary)

After producing the ANNOTATIONS object, produce four markdown documents.
These are for human consumption — Substack posts, briefings, internal strategy docs.
They can be richer and more narrative than the tightly-constrained annotation bodies.

### gaps.md
Title: **Credit Data Gaps — [Report Name] [Date]**

One section per major gap or data limitation. Each section:
- What the data shows on the surface
- Why it's misleading or incomplete
- What a reader should do differently because of this gap

### insights.md
Title: **Credit Insights — [Report Name] [Date]**

The 5–8 most important cross-section insights from this report. Each insight:
- The observation with exact numbers
- Why it matters now (not historically)
- One implication for a lender or fintech

### opportunities.md
Title: **Lending Opportunities — [Report Name] [Date]**

The 3–5 highest-conviction lending opportunities visible in the data. Each:
- The opportunity in one sentence
- Data evidence (series names, values, growth rates)
- What type of lender is best positioned and why
- Key risk or caveat

### system_model.md
Title: **System Model — [Report Name] [Date]**

This is the premium document. It should explain **why** the credit system looks the way
it does — causal chains, structural shifts, policy effects — not just describe it.

Structure:
1. **The current state** — what the system looks like right now in 3–4 sentences
2. **What's driving it** — 3–5 causal factors with evidence from the data
3. **Structural shifts** — things that have changed irreversibly (not just grown)
4. **Pressure points** — where the system is stressed or about to shift
5. **The 2-year view** — where this is likely heading based on current trajectories

The system model must synthesise across ALL sections. A good system model makes
connections the per-section annotations miss — e.g. MSME formalisation growth →
priority sector pressure → gold loan substitution → retail credit composition shift.

---

## Validation checklist before submitting

Before finalising the ANNOTATIONS object, verify:

- [ ] Every `highlight`/`dim`/`dash` value is in the corresponding `section.seriesNames`
- [ ] Every date string matches a `date` field in `absoluteData` exactly
- [ ] Every number is computed from the JSON, not approximated
- [ ] No annotation references a series from a different section
- [ ] `preferredMode` is set on every annotation that involves growth rates
- [ ] Each section has at least 2 annotations across insights/gaps/opportunities
- [ ] No two annotations say the same thing with different wording

---

## Example of a good annotation (for reference)

```typescript
{
  id:    "msme-formalisation-base-effect",
  title: "Some of this growth is businesses newly visible, not new borrowing",
  body:  "A lot of Micro & Small's growth isn't businesses borrowing more — it's " +
         "businesses that always existed, now showing up in bank data for the first " +
         "time after GST registration and UDYAM enrolment. The economy hasn't grown " +
         "31%; the formally visible part of it has.",
  implication: "Many of these new borrowers have no credit history — bureau checks " +
               "will come back thin or blank. If you're entering MSME lending, your " +
               "ability to assess creditworthiness without a credit score matters " +
               "more than how many leads you can generate.",
  preferredMode: "yoy",
  effect: { highlight: ["Micro and Small"], dash: ["Micro and Small"] },
}
```

---

## How to use this prompt

1. Export the dashboard data: open the dashboard, click "Export data model" at the bottom
2. Attach the downloaded JSON to this conversation
3. Attach the original PDF report
4. Paste this prompt
5. Ask Claude to produce Output 1 first (ANNOTATIONS), validate it, then Output 2

For Output 1, it helps to ask section by section rather than all at once — each section
can have 10–15 annotations and the full ANNOTATIONS object for 7 sections is large.
