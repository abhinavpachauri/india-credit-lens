# Credit Data Gaps — RBI SIBC Feb 2026

> Period: Feb 2026 | Publication date: 2026-03-30
> These are not data errors — they are structural limitations that mislead naive readers.

---

## 1. PSL Housing data is contaminated by a classification revision

**What the data shows on the surface:** PSL Housing grew +38.4% FY, from ₹7.47L Cr (Mar 2025) to ₹10.33L Cr (Feb 2026). After a year of contraction (-1.1% YoY in FY25), this looks like a dramatic lending surge.

**Why it's misleading:** The Oct 2024 RBI guideline revision raised PSL housing loan limits — metro cities from ₹35L to ₹45L, non-metro from ₹25L to ₹35L. Loans already on bank books that previously fell outside the PSL definition now qualify. The ₹2.87L Cr addition includes existing loans reclassified into PSL, not new disbursements. The SIBC report does not flag this change.

**What a reader should do:** Never quote PSL housing growth without checking the PSL limit revision history. Use the non-PSL housing figures (personal loans Housing at +9.8% FY) as the proxy for genuine new lending activity. When comparing periods, verify whether a limit revision fell in the intervening window.

---

## 2. No Feb 2026 YoY comparison available for most sections

**What the data shows on the surface:** Six of seven sections (all except industryByType) have three absolute dates — Mar 2024, Mar 2025, and Feb 2026. Growth rates are either FY-to-date (Feb 2026 vs Mar 2025) or full-year (Mar 2025 vs Mar 2024).

**Why it's misleading:** FY-to-date from a March base compares a February month-end (seasonal peak for some categories) to a March year-end. This overstates FY growth for seasonally high-February categories (food credit, agriculture, gold lending) and understates for categories where March is the peak. A true YoY comparison needs Feb 2025 data, which this file does not contain.

**What a reader should do:** For a Feb 2026 vs Feb 2025 YoY comparison across main sectors, use the consolidated CSV or cross-reference with the Jan 2026 SIBC file (SIBC27022026) which has Jan 2025 as a reference point. The industryByType section is the exception — it has Feb 2024, Feb 2025, and Feb 2026 data for proper YoY analysis.

---

## 3. Food credit FY growth is a seasonal artifact

**What the data shows on the surface:** Food credit grew +126.2% FY, from ₹0.37L Cr (Mar 2025) to ₹0.83L Cr (Feb 2026). This is the fastest-growing item in the bankCredit section.

**Why it's misleading:** Food credit spikes every January-February during rabi crop procurement. Government agencies (FCI, state procurement entities) draw credit lines and repay by March-end. The FY growth figure compares a seasonal peak (Feb) to a seasonal trough (Mar). This pattern has appeared consistently in prior periods — it is not a signal of structural lending growth.

**What a reader should do:** Never quote food credit FY growth from a February observation. Food credit will fall back to approximately ₹0.4-0.5L Cr by March 2026. The correct approach is to compare Feb 2026 food credit to Feb 2025 food credit, not Feb 2026 to Mar 2025.

---

## 4. NBFC credit is double-counted with end-borrower categories

**What the data shows on the surface:** Bank credit to NBFCs at ₹19.48L Cr (Feb 2026, +19.1% FY) is the largest services sub-sector and one of the fastest-growing categories in the system.

**Why it's misleading:** NBFCs borrow from banks and lend onward to retail borrowers, MSMEs, and gold customers. That end-borrower exposure shows up again in Personal Loans, Industry, and Agriculture sections under the respective borrower categories. The total credit in the system is not the sum of all SIBC sections — the NBFC credit is an intermediate flow. Adding NBFC credit to personal/MSME credit overstates total credit by a significant margin.

**What a reader should do:** When calculating system-level credit penetration or total household debt, exclude NBFC bank borrowings from the numerator. The RBI SIBC is a bank balance sheet view (who banks lend to), not an end-borrower view (who ultimately uses the credit). These two views differ by the NBFC intermediation layer.

---

## 5. Gold loans here capture banks only — total systemic exposure is 2× higher

**What the data shows on the surface:** Gold loans at ₹4.29L Cr are growing at +107.8% FY and now represent 6.3% of personal credit.

**Why it's misleading:** Muthoot Finance, Manappuram Finance, and smaller gold NBFCs collectively hold ₹1.5-2.5L Cr in gold AUM (rough estimate — this changes with gold prices). Hundreds of microfinance and cooperative bank players add more. The SIBC captures only scheduled commercial bank gold loans. Total gold-backed credit in the Indian system likely exceeds ₹7-8L Cr.

**What a reader should do:** SIBC gold loan data is a floor estimate, not a ceiling. For total systemic gold credit exposure, triangulate with CIBIL MSME or CRIF reports that show NBFC gold loan portfolios. The bank share of gold lending is growing — but the base comparison should acknowledge the full market.

---

## 6. Weaker Sections and PSL totals are not additive

**What the data shows on the surface:** The Priority Sector table shows 10 categories including Weaker Sections (₹20.32L Cr). Summing all rows gives an apparent total.

**Why it's misleading:** Weaker Sections is a sub-set of the PSL categories — SC/ST borrowers, small farmers, and SHG members who appear in Agriculture, MSME, and Housing rows. They are not an additional PSL category; they are a cross-cutting descriptor. Summing across all PSL rows leads to double-counting. The same borrower can appear in Agriculture PSL and in Weaker Sections.

**What a reader should do:** Never sum PSL categories to get a total. Use the official PSL achievement ratios published in RBI's annual reports and bank disclosures. The correct PSL total is 40% of ANBC (Adjusted Net Bank Credit) — use that as the denominator for any PSL penetration analysis.

---

## 7. Other Services and Other Personal Loans — 20-25% of their sectors with zero visibility

**What the data shows on the surface:** 'Other Services' at ₹12.37L Cr (21.3% of Services) and 'Other Personal Loans' at ₹17.03L Cr (25% of Personal Loans) both show steady mid-single-digit to low-double-digit FY growth.

**Why it's misleading:** These residual categories are large enough to materially affect sector-level conclusions. Other Personal Loans alone is larger than Vehicle Loans and Education combined. We cannot know whether the growth is from salary advances, personal overdrafts, fintech-originated personal loans, or top-up home loans.

**What a reader should do:** For any analysis that draws conclusions from sector-level growth, treat the residual categories as structural uncertainty bands. BSR-1 quarterly data provides granular sub-classification within personal loans. For deep analysis, request BSR-1 or CIBIL credit institution data.

---

## 8. Gems and Jewellery credit growth conflates price and volume effects

**What the data shows on the surface:** Gems and Jewellery credit grew +40.2% YoY (Feb 2026 vs Feb 2025), one of the fastest sub-sectors in Industry by Type.

**Why it's misleading:** Gold prices rose approximately 25% in the same period. Jewellers use working capital proportional to the value of their gold inventory — if gold prices rise 25%, their credit requirement rises 25% with no volume change. Of the 40.2% YoY growth, at least 20-25 percentage points are pure price effect. Real volume growth is likely 10-15%.

**What a reader should do:** When assessing Gems and Jewellery credit risk or growth quality, deflate by gold price change over the same period. Credit stress-test scenarios should include a 15-20% gold price retracement — which would compress working capital requirements and potentially trigger LTV-linked covenant breaches.

---

*For the full set of data-driven insights: see insights.md and annotations_draft.ts in this directory.*
