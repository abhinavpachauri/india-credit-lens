# Report Analysis Prompt
## Use this as input to Claude when analysing a new report

---

## HOW TO USE

**Option A — PDF / text report**
1. Attach the PDF (or paste the relevant sections)
2. Fill in the `[REPORT METADATA]` section
3. Paste this prompt and send

**Option B — CSV / Excel data**
1. Attach the CSV/XLSX file, or confirm the file path (e.g. `consolidated/consolidated_long.csv`)
2. Fill in the `[REPORT METADATA]` section — set `Report type: structured_data`
3. In `Data format`, describe the schema (columns, units, date range, what each row represents)
4. Paste this prompt and send — Claude will compute metrics directly from the data before writing

**Both options produce the same three output files:**
`[report_id]_summary.md`, `[report_id]_gaps.md`, `[report_id]_opportunities.md`

---

## [REPORT METADATA] — fill before sending

```
Report title:
Publisher:
Published date:
Data coverage period:
Report type: [snapshot / time_series / benchmark / structured_data]
Primary subject: [e.g. women's credit, MSME lending, rural finance, monetary policy]
Audience context: [e.g. lending business looking for product/market opportunities]
Report ID (kebab-case): [e.g. crif_credit_goes_to_her_mar2026]

# For CSV/Excel only — describe the data schema:
Data format: [e.g. long / wide]
Key columns: [e.g. date, sector, outstanding_cr]
Units: [e.g. ₹ Crore]
Date range: [e.g. Jan 2024 – Jan 2026, 5 snapshots]
Rows represent: [e.g. one sector × one date]
Known caveats: [e.g. Priority Sector rows are memo items, not additive]
```

---

## PROMPT

You are analysing a report for India Credit Lens — a platform that extracts strategic value from credit and lending reports published by RBI, CRIF, SIDBI, CIBIL, NABARD, PLFS, and others.

Your task is to produce three structured markdown files. The input may be a PDF report or structured data (CSV/Excel). Follow the relevant preparation step before writing:

**If the input is a PDF or text report:** Read the full report before writing anything. Do not summarise what you haven't read.

**If the input is CSV or Excel data:** First compute the key metrics — YoY growth rates, shares, absolute changes — for all relevant segments using the actual data. Output the computed table before writing the files so the numbers can be verified. Every claim in all three files must be traceable to a specific computed number, not an estimate.

The quality of each file depends on what the data actually shows, not on the report's framing or on plausible assumptions.

---

### FILE 1: SUMMARY (`[report_id]_summary.md`)

Produce a summary with three sections:

**Section A — Headline numbers**
A clean table of the most important quantitative facts in the report. Include source page references. Only include numbers that are directly stated or directly derivable from the report.

**Section B — Key insights (5-7 max)**
Each insight should:
- Lead with a single declarative statement of what the data shows
- Follow with 2-4 supporting data points from the report
- End with one sentence on what this means for a lending business

Do not repeat what the report says as insight. Insight = what the numbers reveal that the report may not have surfaced.

**Section C — Systems view**

Map the subject of this report as a system using the elements below. **Each element must be represented visually using ASCII diagrams** — not prose paragraphs. The goal is to show structure and causality at a glance, not to describe it in words.

**C1 — Stock & Flow overview** (one diagram for the whole system)

Use this format. Stocks in `[ ]`, flows as arrows with labels, rates/drivers as `(  )`:

```
(driver) ──→ [ STOCK name | current value | trend ↑/↓/─ ] ──→ (outflow)
                    ↑
              (reinforcing driver)
```

Show all major stocks and the flows between them. Use `~~→` for a stalled or declining flow.

**C2 — Causal loops** (one box per loop, 2–4 loops maximum)

Mark each loop as `[R]` reinforcing or `[B] balancing`. Show the chain of causation with `+` (same direction) or `−` (opposite direction) on each link:

```
┌─────────────────────────────────────┐
│  [R] Loop name                      │
│                                     │
│  Variable A ──(+)──→ Variable B     │
│       ↑                    │        │
│       └────(+)─────────────┘        │
│                                     │
│  One-line explanation of the loop   │
└─────────────────────────────────────┘
```

**C3 — Delays & hidden risks** (timeline format)

```
NOW ──────────────────────────────────────────────→ TIME
 │          +12 mo              +24 mo    +36 mo
 │            │                   │          │
 │      [Risk A name]       [Risk B]    [Risk C]
 │      brief description   brief       brief
```

**C4 — Leverage points** (ranked list with causal chain)

```
#1  [Intervention] → [Immediate effect] → [System-level change]
#2  ...
```

The systems view should answer WHY the numbers look the way they do, not just what they are. Prioritise showing causal structure over completeness.

**Section D — Coverage boundary**
One short paragraph on what this report covers and what it explicitly or implicitly excludes. This sets the boundary for interpreting all other findings.

---

### FILE 2: SIGNAL VS NOISE (`[report_id]_gaps.md`)

For each significant inconsistency, selective framing, or analytical gap you find, create one entry:

```
### [Number]. [Short title of the issue]

**Report claim:** [Exact quote or close paraphrase of what the report says]

**What the data actually shows:**
[The number, metric, or context that changes the interpretation]

**The gap:**
[Why this matters — what the difference implies for how the report should be read]

**What would be more honest:**
[What the report should have shown or said instead]

**Severity:** [🔴 High | 🟡 Medium | 🟠 Low-Medium]
**Category:** [metric_choice | data_exclusion | headline_inflation | comparison_baseline]
```

Check specifically for:
- **Metric choice**: Is the cited metric the most honest available? (e.g., growth rate vs share; LFPR vs WPR; volume vs value)
- **Data exclusions**: What populations or segments are outside the dataset? Is this disclosed prominently?
- **Missing comparators**: Is a finding presented as segment-specific when it applies equally to the comparison group?
- **Uncontextualised positives**: Is a positive metric shown without the constraint or risk that frames it?
- **Selective omissions**: What data is in the report but not highlighted? What is implied but not stated?
- **Vintage and timing effects**: Do growth metrics or quality metrics reflect structural features of the data rather than real trends?

End with a summary scorecard table:

| Claim | Status | Severity |
|---|---|---|
| [claim] | [what it hides] | 🔴/🟡/🟠 |

---

### FILE 3: OPPORTUNITIES (`[report_id]_opportunities.md`)

Produce a structured opportunities analysis for a lending business. Organise by:

**Section 1 — Where growth is fastest** (highest growth differential vs comparison group)
- Table of top 5 segments by growth delta
- For each: what the data shows, strategic inference

**Section 2 — Where underweight is largest** (low share, upward trajectory)
- Table of segments with largest gap between current share and structural potential
- For each: what the data shows, strategic inference

**Section 3 — The pipeline** (what cohort or segment represents future conversion)
- Identify the most important latent asset in the data (e.g., NTC cohort, underserved geography, underpriced risk segment)
- Map the pipeline math: if X% convert at Y ticket, the portfolio implication is Z
- Identify what is blocking conversion today

**Section 4 — Risk mispricing** (where pricing doesn't reflect actual risk)
- Identify segments where standard underwriting overestimates or underestimates risk
- State the evidence and the commercial opportunity

**Section 5 — Geographic strategy**
- Where is share concentrated vs dispersed?
- What is the frontier — and is it outside current geography or deeper within it?

**Section 6 — Product maturity curve**
- Classify each product into: Mature (defend/deepen) | Growth (accelerate) | Emerging (watch)
- One-line strategic inference per product

**Section 7 — Structural risks**
- What does the positive data obscure?
- What risks are being built into the portfolio today that will surface in 18-36 months?
- What is the single most important unresolved data point before scaling?

End with a **3-year playbook table**:

| Priority | Opportunity | Data basis | Action |
|---|---|---|---|
| 1 | [title] | [data] | [what to do] |

---

### QUALITY STANDARDS

- Every claim must be traceable to a specific data point in the report or a direct derivation from it
- Never repeat the report's framing as insight — insight means going beyond what the report surfaces
- Where the report is silent on something important, say so explicitly
- The systems view should reveal structural causes, not just describe observations
- Opportunities should be specific enough to be actionable — "expand women's credit" is not an opportunity; "build a ₹2L → ₹10L graduation ladder for existing women business borrowers via proactive UBL offers at 12-month SBL repayment milestone" is

**Writing style**

Write like a knowledgeable colleague explaining something clearly — not a consulting deck being presented. The audience is a general banking professional: credit officers, product managers, branch bankers, analysts. They are smart but don't need jargon.

Rules:
- Plain English throughout. Avoid: "structural headwind", "collateral-first incumbents", "de facto credit enhancement", "evaluate rotation into", "orient primarily toward", "durable edge", "risk-adjusted returns", "mispricing"
- Short sentences over compound ones. One idea per sentence.
- Use the actual numbers. Specific figures are clearer than abstractions ("grew 5x faster" beats "significantly outpaced")
- Say the uncomfortable thing directly. Don't soften risk findings with hedged language like "may warrant consideration"
- Body text: what the data shows, in plain terms, with key numbers
- Implication text: what this means practically for someone working in lending — not "lenders should consider" but "if your book is heavy on X, the data says Y"
- Explain acronyms and schemes on first use (PLI = Production Linked Incentive, PMAY = government's affordable housing scheme, PSL = loans banks are required to make to certain sectors)

---

---

### FOR CSV/EXCEL INPUTS — ADDITIONAL CHECKS

Run these checks on structured data before writing, and surface any issues in the Gaps file:

- **Memo / cross-classification rows:** Are any rows subsets of other rows (e.g. Priority Sector)? Flag if they could be double-counted.
- **Seasonality:** Do values fluctuate by observation date in ways that make point-in-time comparisons misleading? Check Jan vs March if both exist.
- **Coverage gaps:** Which segments have missing data for some dates? State this explicitly when citing growth rates.
- **Unit consistency:** Are all values in the same unit across all rows? Verify before computing derived metrics.
- **Outlier detection:** Flag any segment with >50% YoY growth or >30% YoY decline — these warrant a separate "Signal vs Noise" entry to determine if they are real or artefact.

---

*This prompt is part of India Credit Lens. Save outputs as [report_id]_summary.md, [report_id]_gaps.md, [report_id]_opportunities.md*
