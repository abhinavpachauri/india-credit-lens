# RBI SIBC Jan 2026 — Signal vs Noise
**Report ID:** `rbi_sibc_jan2026`

---

### 1. Food Credit 58.9% YoY growth is a seasonal artefact

**Report claim:** Bank Credit YoY growth includes Food Credit at +58.9% for Jan 2026 vs Jan 2025.

**What the data actually shows:**
Food Credit is structurally seasonal. It peaks in January (kharif procurement season) and troughs in March (post-procurement). The data shows:
- Jan 2024: ₹0.456 L Cr → Mar 2024: ₹0.231 L Cr (−49% in 2 months)
- Jan 2025: ₹0.562 L Cr → Mar 2025: ₹0.365 L Cr (−35% in 2 months)
- Jan 2026: ₹0.893 L Cr

The Jan 2026 high of ₹0.893 L Cr vs Jan 2025 low of ₹0.562 L Cr produces 58.9% YoY. But Jan 2025 was itself lower than Jan 2024 (0.456 L Cr). The underlying trend is not a structural acceleration — it is seasonal volatility amplified by a low base.

**The gap:**
The 58.9% figure will reverse to near-zero or negative by Mar 2026. Using January-to-January comparisons for Food Credit produces noise, not signal.

**What would be more honest:**
Compare March-to-March (post-procurement trough to trough): Mar 2024 (₹0.231L) to Mar 2025 (₹0.365L) = +57.9% — a genuinely high growth rate, but from a tiny base. State both the base and the seasonal structure clearly.

**Severity:** 🟡 Medium
**Category:** `comparison_baseline` | `metric_choice`

---

### 2. Infrastructure 6.4% YoY growth headline obscures sub-sector collapse

**Report claim:** Infrastructure credit at ₹14.27 L Cr, up +6.4% YoY.

**What the data actually shows:**
Power (₹7.89 L Cr, +17.5% YoY) represents 55.3% of total infrastructure credit and is the sole driver of the positive headline. The remaining 44.7% of infrastructure credit is declining:
- Roads: ₹3.31 L Cr, +0.2% YoY (flat in nominal terms, negative in real terms)
- Telecom: ₹1.06 L Cr, −17.2% YoY
- Airports: ₹0.06 L Cr, −26.1% YoY
- Railways: ₹0.10 L Cr, −24.2% YoY
- Other Infrastructure: ₹1.76 L Cr, −4.0% YoY

Ex-Power, infrastructure credit = ₹6.38 L Cr, down ~3.7% YoY.

**The gap:**
The aggregate number creates an impression of healthy infrastructure financing. In reality, 4 of 6 sub-sectors are in nominal decline, and the system is dependent on a single sub-sector (Power) to produce a positive headline.

**What would be more honest:**
Decompose infrastructure into Power vs rest. The "rest" is actively deleveraging, consistent with the end of the earlier infrastructure buildout cycle and absence of a comparable new pipeline.

**Severity:** 🔴 High
**Category:** `data_exclusion` | `headline_inflation`

---

### 3. Gold Jewellery +128.8% YoY growth is uncontextualised

**Report claim:** Gold Jewellery loans = ₹4.01 L Cr, one of the personal loan sub-categories.

**What the data actually shows:**
Gold Jewellery has grown from ₹0.92 L Cr (Jan 2024) to ₹4.01 L Cr (Jan 2026) — a 337.9% increase in 24 months. The YoY growth of +128.8% is the highest of any personal loan sub-category except the small "Advances against Shares/Bonds" (₹0.10 L Cr, +39.8% on a negligible base). Gold prices rose approximately 25–30% in this period. The credit volume grew ~4.4x while collateral values grew ~1.3x.

**The gap:**
The gold loan surge is presented as a product category statistic with no commentary on what it signals. Three explanations exist: (a) genuine demand for working capital / consumption smoothing, especially from lower-income households, (b) borrowers using gold to refinance unsecured debt as RBI tightens that market, (c) NBFCs aggressively expanding gold lending and banks competing. Any of these has material risk implications — for credit quality, systemic risk, and household balance sheets — that are invisible in the aggregate number.

**What would be more honest:**
Flag the gold loan growth as a risk signal that needs delinquency data and borrower purpose data alongside it. The 337% growth rate is not a success story without knowing why people are borrowing.

**Severity:** 🔴 High
**Category:** `uncontextualised_positives` | `selective_omissions`

---

### 4. NBFC credit share (33.3% of Services) is a wholesale funding figure, not an end-borrower figure

**Report claim:** NBFCs represent ₹19.05 L Cr of Services credit, the largest sub-sector.

**What the data actually shows:**
SIBC captures bank-to-NBFC credit — the wholesale funding leg. The end-borrower is an NBFC retail or MSME customer. Housing Finance Companies (₹3.53 L Cr) and Public Financial Institutions (₹3.06 L Cr) are broken out under NBFCs. The remaining ~₹12.5 L Cr goes to consumer and MSME-facing NBFCs — but the end-use is invisible in this dataset.

**The gap:**
Any analysis of services credit that does not call out the intermediary nature of the NBFC figure will misread where credit is actually deployed. The data suggests banks are increasingly lending to NBFCs rather than to end borrowers, which changes the risk profile (concentration to a small number of large NBFC counterparties) and obscures the true sectoral distribution.

**What would be more honest:**
Present the ₹19.05 L Cr NBFC figure with a clear note: "This is wholesale bank-to-NBFC lending; what those NBFCs do with the money is not captured here." Separately, use RBI's NBFC return data to show where the money actually ends up.

**Severity:** 🔴 High
**Category:** `data_exclusion` | `metric_choice`

---

### 5. Credit Card 14.7% 2-year growth is presented as growth — it's real-terms stagnation

**Report claim:** Credit Card outstanding at ₹2.96 L Cr.

**What the data actually shows:**
Trajectory: ₹2.59L (Jan 2024) → ₹2.57L (Mar 2024) → ₹2.92L (Jan 2025) → ₹2.84L (Mar 2025) → ₹2.96L (Jan 2026). The 14.7% two-year nominal growth is approximately equal to cumulative inflation over the same period. In real terms, credit card outstandings have been flat to slightly declining. YoY growth of +1.5% is effectively zero.

**The gap:**
Before November 2023 (when RBI raised risk weights on unsecured credit from 100% to 125%), credit card portfolios were growing at 25–35% annually. The deceleration from 25%+ to 1.5% represents regulatory intervention taking full effect. This structural break is not visible if you only look at the Jan 2026 number.

**What would be more honest:**
State explicitly: credit card growth has decelerated sharply post-RBI risk weight increase. This is not sector-specific softness — it is a policy-induced change in bank appetite for unsecured revolving credit.

**Severity:** 🟡 Medium
**Category:** `comparison_baseline` | `selective_omissions`

---

### 6. Priority Sector Memo figures are additive with main sector figures — this is rarely disclosed

**Report claim:** Priority Sector memo items show Agriculture at ₹25.65 L Cr, MSE at ₹27.35 L Cr, etc.

**What the data actually shows:**
Priority Sector (PS) numbers in Statement 1 are a cross-classification of the same loans already counted in the main sector rows (Agriculture, Industry, Services, Personal Loans). PS Housing (₹10.31 L Cr) is a subset of the ₹32.78 L Cr Housing figure in Personal Loans. PS Agriculture (₹25.65 L Cr) is a subset of the ₹25.10 L Cr Agriculture sector total (near-complete overlap). PS MSE (₹27.35 L Cr) spans Micro & Small in Industry + sub-segments of Services and Agriculture.

**The gap:**
A reader who sums PS amounts alongside main sector totals will double-count. The RBI SIBC form presents them as "memo" items, but this is not visually prominent enough to prevent misinterpretation, especially in data analysis workflows.

**What would be more honest:**
Label the Priority Sector section clearly as "cross-classification (subset of above totals, not additive)." In the data file, the `is_priority_sector_memo` flag handles this — but downstream analysis tools may lose this nuance.

**Severity:** 🟠 Low-Medium
**Category:** `metric_choice` | `data_exclusion`

---

### 7. FY March comparisons vs January comparisons produce different conclusions

**Report claim:** (Implicit in any YoY analysis) Growth rates are comparable across sectors.

**What the data actually shows:**
The dataset has two distinct date types: January observations (end of kharif season, post-harvest) and March observations (financial year-end, post-Rabi). These are structurally different in several sectors:
- Food Credit: Jan25 = ₹0.562 L Cr vs Mar25 = ₹0.365 L Cr (−35%)
- Agriculture: Jan25 = ₹22.54 L Cr vs Mar25 = ₹22.87 L Cr (+1.5%)
- Gold Jewellery: Jan25 = ₹1.75 L Cr vs Mar25 = ₹2.06 L Cr (+17.8%)

YoY Jan-to-Jan comparisons for gold, agriculture, and food credit embed seasonal distortions. The same data read differently on a FY basis would show different growth rates.

**What would be more honest:**
Explicitly label each observation as "crop-season snapshot" vs "FY-close snapshot" and avoid comparing sectors with different seasonal profiles on the same YoY metric.

**Severity:** 🟡 Medium
**Category:** `comparison_baseline`

---

## Scorecard

| Claim | What It Hides | Severity |
|---|---|---|
| Food Credit +58.9% YoY | Seasonal artefact vs Jan25 low; will reverse by Mar26 | 🟡 Medium |
| Infrastructure +6.4% YoY | 5 of 6 sub-sectors declining; Power is the entire story | 🔴 High |
| Gold Jewellery growth (+128.8%) | Potential household stress signal; not contextualised | 🔴 High |
| NBFC = 33.3% of Services | Wholesale funding, not end-borrower exposure | 🔴 High |
| Credit Cards "growing" (+1.5%) | Real-terms stagnation post-RBI risk-weight increase | 🟡 Medium |
| Priority Sector totals | Cross-classification of main-sector data; not additive | 🟠 Low-Medium |
| Jan-to-Jan YoY comparisons | Seasonal distortions for food credit, gold, agriculture | 🟡 Medium |
