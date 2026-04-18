# Data Gaps — RBI SIBC Merged (Jan 2024 – Feb 2026)

> Period: Jan 2024 – Feb 2026 | Generated: 2026-04-14
> Source: RBI SIBC merged across all ingested periods

---

## 1. January SIBC files do not report Gold Loans or PSL Housing sub-classification

Gold Loans and PSL Housing both appear as null in all January data rows. These series only exist in the March SIBC files. As a result, Jan→Jan YoY comparisons for gold loans and PSL housing are not possible — the cross-period acceleration story for these categories can only be told using March data points.

**Impact:** Any analysis of gold loan trends using merged data must explicitly note that January figures are absent. Readers cannot assess whether the March-to-March trajectory holds in interim months.

---

## 2. January SIBC files do not report NBFC credit or Tourism sub-classification in Services

NBFC credit and Tourism are null in all January service rows. Only March SIBC files capture NBFC sub-classification. Since NBFCs are the largest single services sub-sector, January services totals do not reflect the full picture. The merged Jan→Jan services YoY comparison excludes the NBFC channel.

**Impact:** Services growth rates in January-to-January comparisons understate the true services credit trajectory if NBFC credit grew faster than the other sub-sectors in the year.

---

## 3. Food credit seasonal artifact distorts January bank credit totals

Food credit (NABARD-channelled agricultural procurement credit) peaks in January at kharif marketing season and drops sharply by March. This makes January bank credit totals appear larger than the March figures for the same fiscal year, distorting FY-to-date growth calculations that use January as the base.

**Correct signal:** Non-food credit is the right metric for January-to-January comparisons. Food credit should be stripped from all trend analyses using January data.

---

## 4. PSL Housing +38% FY growth is reclassification, not organic lending

PSL Housing: ₹7.47L Cr (Mar 2025) → ₹10.33L Cr (Feb 2026), +38.4% FY. The Oct 2024 RBI revision raised PSL housing loan ceilings (metro: ₹35L → ₹45L, non-metro: ₹25L → ₹35L). Loans already on bank books that previously exceeded the old limits now qualify as PSL. The ₹2.87L Cr appearing in the data as credit growth is reclassification of existing exposures, not new lending.

**Impact:** PSL Housing growth rates for FY26 are not comparable to prior years. Any lender citing PSL achievement figures for FY26 must disclose the classification change.

---

## 5. PSL totals are not additive across sub-categories

PSL sub-category totals (Housing + Micro & Small + Export Credit + Education + Renewable Energy + Others) do not sum to the PSL aggregate. The discrepancy arises because some loans qualify under multiple PSL categories and are counted in each. Treating sub-category figures as exhaustive slices produces incorrect totals.

**Impact:** Cross-category PSL market share analysis must use category-specific figures, not derived shares from the aggregate.

---

## 6. Consumer Durables YoY deepening contraction is not visible in merged January data alone

Consumer Durables: -1.0% YoY (Jan 2025) → -9.6% YoY (Jan 2026). The worsening trend is only visible with the Jan→Jan comparison enabled by merged data. Any single-period analysis would see a contraction but could not determine whether it was accelerating or stabilizing.

**Impact:** The merged view is essential for distinguishing trend from noise for small, volatile categories like consumer durables. Without it, the policy causation (RBI risk-weight hike driving accelerating contraction) cannot be confirmed.

---

## 7. Other Services and Other Personal Loans remain opaque across all periods

"Other Services" and "Other Personal Loans" are residual catch-all categories. Neither SIBC file provides sub-classification. These residuals are large enough to materially affect sector totals but their composition is unknown across all merged periods.

**Impact:** Any significant change in these residuals cannot be attributed to a structural driver without supplementary data (BSR-1, credit bureau data). They are black boxes in the causal model.

---

## 8. Gems & Jewellery credit conflates gold price appreciation with volume growth

Gems & Jewellery: ₹0.73L Cr (Jan 2025) → ₹0.91L Cr (Jan 2026), +24.7% YoY. Gold prices rose approximately 40% in the same period. If working capital loans are collateral-based and LTV-constrained, a significant portion of the growth is gold price appreciation inflating collateral values and loan amounts — not volume expansion.

**Impact:** Gems & Jewellery YoY growth overstates genuine business expansion during gold price surges. The real growth rate (volume-adjusted) is likely lower.

---

*For the full annotation set: see annotations_merged.ts. For lending opportunities arising from these gaps: see opportunities_merged.md.*
