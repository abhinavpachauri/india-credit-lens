# Credit Data Gaps — RBI SIBC Mar 2026 (annual snapshot, published Apr 30 2026)

This file is unusual in the SIBC series. It contains only three FY-end
snapshots (Mar 2024, Mar 2025, Mar 2026) — not the typical monthly cadence —
and uses split date conventions across statements. Below: the seven gaps a
reader needs to be aware of before quoting any number.

---

## 1. Bank Credit dates are early-April fortnights, not Mar-end

**What the data shows on the surface:** Bank Credit, Food Credit, and Non-food
Credit appear with three time points labelled "Apr 2024", "Apr 2025", "Mar
2026".

**Why it's misleading:** RBI publishes Bank Credit on a fortnightly cycle. The
"Apr 2024" date is **Apr 5, 2024** — the FY24-end fortnight; "Apr 2025" is **Apr
4, 2025** — the FY25-end fortnight. Sub-sectors (Agriculture, Industry,
Services, Personal Loans) use Mar 22, 2024 and Mar 21, 2025 — different actual
dates inside the same statement.

**What a reader should do:** Treat all three Bank Credit dates as FY-end
snapshots. The labelling differs but the values are like-for-like across years.
The 16.1% growth quoted is the file's published variation column (Mar 31, 2026
versus Apr 4, 2025) — not a recomputed YoY.

---

## 2. FY-to-date growth is empty for the bank credit aggregate

**What the data shows on the surface:** The dashboard's FY view is blank for
bankCredit (only Bank Credit, Food Credit, Non-food Credit lines).

**Why it's misleading:** FY-to-date growth requires a March base column to
anchor against. Because Bank Credit's earlier columns are early-April
fortnights, there is no internal March anchor for the aggregate. FY data
displays correctly for sectors 1-4 but not for the bank credit aggregate.

**What a reader should do:** Use the Absolute or YoY views for the bank credit
aggregate — not FY. The 16.1% headline growth uses RBI's published variation
column.

---

## 3. Three data points limit within-FY pacing analysis

**What the data shows on the surface:** A clean 3-point progression Mar 2024 →
Mar 2025 → Mar 2026.

**Why it's misleading:** Year-end-to-year-end growth can hide whether the
acceleration was front-loaded (Apr-Sep 2025) or back-loaded (Jan-Mar 2026).
Lenders pricing FY27 risk need to know which.

**What a reader should do:** Supplement this file with the consolidated CSV
that has Jan/Feb monthly snapshots for FY26. Use this file for clean YoY
comparisons; use the monthly stream for trajectory.

---

## 4. The four main sectors don't sum to total bank credit

**What the data shows on the surface:** Agriculture + Industry + Services +
Personal Loans for Mar 2026 sums to ₹202.3L Cr.

**Why it's misleading:** Total Bank Credit is ₹213.6L Cr at Mar 2026. Adding
Food Credit (₹0.70L Cr) brings the visible total to ₹203.0L Cr — leaving
**₹10.6L Cr of "other" non-food lending** invisible in the main-sector view.
This is roughly 5% of bank credit — small business loans, public-sector
advances, and other categories not classified into the four selected sectors.

**What a reader should do:** Treat the main-sector view as "selected sectors"
coverage. For full system accounting, anchor on Bank Credit total; for thematic
analysis, use the sector breakdown.

---

## 5. PSL Housing's 39.8% surge is a classification event, not new demand

**What the data shows on the surface:** Priority Sector Housing grew from
-1.1% YoY in FY25 to +39.8% YoY in FY26. The book jumped ₹7.47L Cr →
₹10.44L Cr.

**Why it's misleading:** RBI revised PSL housing limits in October 2024
(metro: ₹35L → ₹45L; non-metro: ₹25L → ₹35L). Existing housing loans that
previously fell outside the PSL bracket got reclassified IN. They are not new
originations — they are loans that already existed, now showing in a different
column.

**What a reader should do:** Never quote PSL Housing as a demand signal. Use
personalLoans.Housing (+11.5% YoY) as the real housing trajectory. PSL line
shifts of 30+ percentage points in a single year are almost always definition
changes.

---

## 6. Most of Gold Loans' 123% growth is reclassification + price, not new lending

**What the data shows on the surface:** Gold Loans went 5x from ₹0.93L Cr to
₹4.60L Cr in 24 months.

**Why it's misleading:** RBI's Sep 2024 circular tightened gold-loan
classification — bullet-repayment loans previously booked under "agri" or
"business" categories had to be reclassified into "loans against gold
jewellery". Gold prices also rose ~30% over the period, expanding the
collateral value of existing loan books.

Both effects compound: more loans visible AS gold loans, each loan secured by
collateral worth more. The 123% YoY rate overstates real new disbursement
demand.

**What a reader should do:** When forecasting gold-loan trajectory into FY27,
separate stock effect (reclassification, fully recognised by Mar 2026) from
flow effect (real new disbursements). Stress-test for a gold-price reversal
scenario; collateral-value contraction would shrink reported balances.

---

## 7. Bank credit to NBFCs is double-counted in any system aggregate

**What the data shows on the surface:** NBFC credit (within Services) is
₹20.66L Cr at Mar 2026 — the largest single line in the Services category.

**Why it's misleading:** Bank credit to NBFCs becomes NBFC on-lending to retail
and MSME borrowers. Those downstream loans appear again in personal-loan or
industrial-loan tables published by NBFCs themselves. There is no system-wide
deduplicated view of end-borrower credit.

**What a reader should do:** When triangulating debt-to-income or debt-to-GDP
ratios, deduct bank-to-NBFC flow first. Headline household-leverage numbers
that add bank credit + NBFC credit are systematically overstated.
