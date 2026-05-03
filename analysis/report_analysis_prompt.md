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
  // ── Explainability fields ──────────────────────────────────────────────────
  // Required whenever body or implication makes a causal, comparative, or
  // forward-looking claim. Optional for pure data observations.
  claim_type?: "data" | "inference" | "hypothesis";
  // "data"       — directly readable from sections.json. No external source needed.
  // "inference"  — causal explanation referencing something outside SIBC data
  //                (RBI circulars, policy, macro context). Must have basis.inferences.
  // "hypothesis" — forward-looking or unverifiable. Must be explicit.
  //                Newsletter generator will add a caveat marker on hypothesis claims.
  basis?: {
    facts:       string[];   // verbatim data points this rests on, e.g. "+33.1% YoY, ₹10.63L Cr"
    inferences:  string[];   // analytical steps beyond the raw data
    hypothesis?: string[];   // forward claims — what would falsify this
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

Each type has a forcing question. If the annotation doesn't satisfy the forcing
question, it belongs in a different bucket or should not be written at all.

---

**Insight** — *"What does the data show, and what is the most defensible interpretation?"*

An insight is a non-obvious finding with an analytical interpretation. It can be a
pure data observation ("Personal loans overtook industry credit") or an inference
("the acceleration is structural, not cyclical") — but every claim must be clearly
labelled with `claim_type`.

Rules:
- Does NOT include pipeline or methodology observations (e.g. "RBI uses April dates").
  That is internal documentation, not an audience-relevant insight.
- Superlatives ("strongest in this cycle", "largest single-year add") must be
  verifiable within the attached data. State the comparison explicitly in the body.
- If the body contains causal language ("reflects", "driven by", "structural shift",
  "because of") → set `claim_type: "inference"` and populate `basis.inferences`.
- If the body contains forward-looking language ("will", "entering FY27", "tailwind
  for X years") → set `claim_type: "hypothesis"` and populate `basis.hypothesis`.

---

**Gap** — *"What might a lender wrongly conclude from this data, and why?"*

A gap is an audience-relevant limitation — something that looks like a signal but
is actually a distortion, a missing series, or a seasonal effect that a reader
could misinterpret.

Rules:
- Must answer: what wrong conclusion could a CRO draw if they didn't know this?
- Pipeline/methodology notes are NOT gaps for the audience:
  ✗ "RBI publishes Bank Credit on a fortnightly cycle" — this is internal pipeline context
  ✗ "The April date labels are not true April data" — solved by the pipeline, invisible to users
  ✓ "January food credit spike is seasonal, not structural" — a reader could misread it
  ✓ "Bank-to-NBFC credit double-counts downstream retail exposure" — a lender could overstate risk
- Gaps are the hardest type to write well. Aim for 2–3 high-quality gaps per section,
  not 4–5 mediocre ones.

---

**Opportunity** — *"What specific action should a specific lender take, in which segment, and why now?"*

An opportunity is prescriptive, not descriptive. The implication field must complete
this template:

> **[Lender type] should [action verb] [segment/product] because [data finding] —
> window is [timeframe or condition].**

Test: replace the implication with "This is a tailwind" — if the meaning barely
changes, it is not an opportunity, it is an insight.

Rules:
- The implication MUST contain an action verb: build, enter, exit, prioritise, avoid,
  hedge, partner, target, develop, scale, launch, expand, specialise.
- Must name the lender type (NBFC, bank, fintech, co-lender) and the specific segment.
- Must state the window: a timeframe ("FY27"), a condition ("before base normalises"),
  or a trigger ("once second bureau vintage data is available").
- "Lenders with scalable origination have a compounding tailwind" → NOT an opportunity.
  "Fintechs should build MSME co-origination capacity now — the annual credit target
  rises ₹5L Cr/year and NBFCs without alt-data infrastructure will cede this to
  bureau-based lenders within 2 FY cycles" → opportunity.

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

After producing the ANNOTATIONS object, produce three markdown documents.
These are for human consumption — Substack posts, briefings, internal strategy docs.

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

---

## Output 3 — System Model JSON (structured, replaces system_model.md)

After Output 1 and Output 2 are complete, produce `system_model.json`.

This is the machine-readable causal model of the credit system. It is the single
source of truth that powers the newsletter generator, Mermaid diagram, and the
dashboard System View tab. All three rendering formats read from this file.

**Critical rule: this file must not reinterpret annotations. It organises and
connects what already exists in Output 1. The only genuinely new content is
(a) driver nodes and (b) edges.**

### Node taxonomy

Produce nodes across five tiers:

| Tier | What it represents | New content or derived? |
|---|---|---|
| `driver` | Macro forces causing credit to move (policy, regulation, prices, structural) | **New** — not in annotations directly |
| `sector` | Credit categories with ₹ values and growth rates | Derived from annotations |
| `gap` | Data limitations and blind spots | Derived from gap annotations |
| `opportunity` | Actionable lending opportunities | Derived from opportunity annotations |
| `pressure` | Latent risks and stress points | Derived from annotation implications |

### Node schema

```json
{
  "id": "snake_case_unique_id",
  "tier": "driver | sector | gap | opportunity | pressure",
  "label": "Short display label (3–5 words)",
  "description": "1–2 sentences. For derived nodes, paraphrase from annotation body — do not add new interpretation.",
  "stat": "+14.6% YoY or null",
  "value_lcr": 204.8,
  "annotation_ids": ["exact-id-from-output-1", "another-id"],
  "claim_type": "data | inference | hypothesis",
  "source": "exact citation — e.g. \"RBI Circular RBI/2023-24/73, Nov 2023\"",
  "source_url": "public URL if available, else \"\""
}
```

**`claim_type` / `source` / `source_url` — mandatory on every driver, opportunity, pressure, and gap node:**

- `"data"` — directly observable in the SIBC data attached. No external source needed. Growth rates, outstanding values, trends visible in sections.json.
- `"inference"` — causal explanation that references something outside the SIBC data (RBI circulars, government schemes, macro context). Requires a real source citation — name the document, circular number, or dataset. Do not use "SIBC data" as source for an inference.
- `"hypothesis"` — forward-looking or unverifiable claim. Allowed but must be explicit. The sourcing pipeline will attempt to find a source; if none found, it stays as hypothesis and is flagged in the newsletter.

Sector nodes do not need `claim_type`/`source`/`source_url` — they are data nodes by definition.

**`annotation_ids` hard constraint:** every string must exactly match an `id` field
from the ANNOTATIONS object produced in Output 1. Copy-paste, do not retype.
A node with no matching annotations gets `"annotation_ids": []` — do not invent ids.

### Edge schema

Edges represent causal or structural relationships between nodes. This is the
primary new analytical work in Output 3 — read across all sections and define
what drives what.

```json
{
  "from": "node_id",
  "to": "node_id",
  "type": "causes | reroutes_demand_to | suppresses | reinforces | creates_risk | creates_opportunity | is_data_gap | creates_gap | signals | contrast",
  "label": "One phrase explaining the causal mechanism"
}
```

Edge type definitions:
- `causes` — direct causal link (formalisation → MSME growth)
- `reroutes_demand_to` — demand shifted from one sector to another due to a driver
- `suppresses` — driver or sector reduces growth elsewhere
- `reinforces` — amplifies an existing trend without causing it
- `creates_risk` — sector growth introduces a latent risk
- `creates_opportunity` — sector growth opens a specific lending opportunity
- `is_data_gap` — sector node is itself a data gap (broken series etc.)
- `creates_gap` — a driver introduces analytical ambiguity in a sector
- `signals` — indirect signal relationship (not direct causation)
- `contrast` — structural comparison between two sector nodes

### JSON structure

```json
{
  "_meta": {
    "report_id": "string",
    "report_name": "string",
    "period": "Mon YYYY",
    "generated": "YYYY-MM-DD",
    "total_credit_lcr": 0.0,
    "yoy_growth_pct": 0.0,
    "schema_version": "1.0"
  },
  "nodes": [ ...node objects... ],
  "edges": [ ...edge objects... ]
}
```

Use `"_comment"` keys freely within the arrays to group related nodes/edges
(e.g. `"_comment": "── DRIVERS ──"`). These are ignored by renderers.

### How many nodes and edges to aim for

- Drivers: 4–8 (the macro forces that explain the data this period)
- Sectors: one node per meaningful credit category in the data (typically 12–20)
- Gaps: one node per gap annotation that represents a systemic blind spot (not just a data quirk)
- Opportunities: one node per actionable opportunity (typically 4–8)
- Pressure points: one node per latent risk visible in the data (typically 2–5)
- Edges: 15–30 is healthy. More than 40 makes the diagram unreadable.

Do not create nodes for trivial observations. Every node should earn its place
by being referenced in at least one edge or having 2+ annotation_ids.

---

## Validation checklist before submitting

**Output 1 — ANNOTATIONS:**
- [ ] Every `highlight`/`dim`/`dash` value is in the corresponding `section.seriesNames`
- [ ] Every date string matches a `date` field in `absoluteData` exactly
- [ ] Every number is computed from the JSON, not approximated
- [ ] No annotation references a series from a different section
- [ ] `preferredMode` is set on every annotation that involves growth rates
- [ ] Each section has at least 2 annotations across insights/gaps/opportunities
- [ ] No two annotations say the same thing with different wording
- [ ] Every superlative ("strongest", "largest", "fastest", "first", "only") is
      verified within the attached data — the comparison is stated explicitly in body
- [ ] Every annotation body with causal language has `claim_type: "inference"` or `"hypothesis"`
- [ ] Every gap annotation answers: what wrong conclusion could a CRO draw?
      No gap is a pipeline/methodology note (RBI dates, fortnightly publication, etc.)
- [ ] Every opportunity implication contains an action verb and names a lender type,
      segment, and window — it completes the template sentence
- [ ] `basis` is populated on every annotation with `claim_type: "inference"` or `"hypothesis"`

**Output 3 — system_model.json:**
- [ ] Every `annotation_ids` entry exactly matches an `id` from Output 1 (copy-paste)
- [ ] No node description adds interpretation not present in its source annotation
- [ ] Every edge `from` and `to` references a valid node `id` in the same file
- [ ] Driver nodes have edges pointing TO at least one sector node
- [ ] Every opportunity and pressure node has at least one incoming edge from a sector node
- [ ] Gap nodes with `is_data_gap` or `creates_gap` edges are flagged in gaps.md too
- [ ] Total edges are between 15–40 (fewer = incomplete, more = unreadable diagram)
- [ ] Every driver, opportunity, pressure, and gap node has a `claim_type` field
- [ ] Nodes with claim_type "inference" have a non-empty `source` field (not "SIBC data")
- [ ] Nodes with claim_type "hypothesis" have `claim_type` explicitly set (not left blank)
- [ ] No node description asserts external facts (EV sales figures, capex wave timing, government scheme approvals) without claim_type = "inference" or "hypothesis"

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
5. Run in this order — do not skip steps or combine:

**Step 1 — Output 1 (ANNOTATIONS)**
Ask section by section rather than all at once. Each section can have 10–15
annotations and the full object for 7 sections is large. Validate each section
before moving to the next.

**Step 2 — Output 2 (Markdown documents)**
Once ANNOTATIONS is finalised, produce gaps.md, insights.md, and opportunities.md.
These draw on the same analysis — no new data reading needed.

**Step 3 — Output 3 (system_model.json)**
Produce this last, after Output 1 is fully validated. It references annotation IDs
directly — if Output 1 changes, the JSON must be updated to match.
Save as: `analysis/[report_id]_[YYYY-MM-DD]/system_model.json`

**What replaces what:**
- `system_model.md` is retired — `system_model.json` replaces it entirely
- The JSON is both machine-readable (for renderers) and human-reviewable
- Downstream generators (newsletter, diagram, dashboard SystemView) read from JSON only
