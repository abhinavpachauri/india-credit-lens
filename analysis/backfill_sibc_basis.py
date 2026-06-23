#!/usr/bin/env python3
"""
backfill_sibc_basis.py — India Credit Lens
-------------------------------------------
One-time backfill: adds claim_type + basis fields to all existing
SIBC annotations in annotations_merged.ts.

Run once, verify output, commit.

Usage:
    python3 analysis/backfill_sibc_basis.py [--dry-run]
"""

import re
import sys
import subprocess
from pathlib import Path

import sys
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core.paths import ROOT
ANN_FILE = ROOT / "analysis/rbi_sibc/merged/annotations_merged.ts"

# ── Basis data keyed by annotation id ─────────────────────────────────────────
# claim_type: "data" | "inference" | "hypothesis"
# basis.facts       — verbatim data points from sections.json
# basis.inferences  — analytical steps beyond the raw data
# basis.hypothesis  — forward-looking / unverifiable claims (optional)

BASIS: dict[str, dict] = {

  # ── Section 1: Bank Credit ─────────────────────────────────────────────────

  "credit-growth-accelerating-fy26": {
    "claim_type": "data",
    "facts": [
      "Bank Credit at Mar 2026: ₹213.6L Cr",
      "FY26 added ₹29.6L Cr vs ₹18.2L Cr in FY25 and ₹23.5L Cr in FY24",
      "YoY growth: +11.0% FY25 → +16.1% FY26",
      "Within FY26: Jan 2026 FY +12.0%, Feb 2026 FY +13.5%, Mar 2026 FY +16.1% — back-loaded acceleration",
    ],
    "inferences": [
      "Simultaneous acceleration across all main sectors means no single sector drove the headline",
      "Portfolios growing below 16% lost relative market share in a system-wide tailwind year",
      "Capital constraint (not demand) as the binding factor entering FY27 — derived from system-wide growth with no demand laggard visible",
    ],
  },

  "three-year-credit-trajectory": {
    "claim_type": "inference",
    "facts": [
      "Bank Credit: ₹160.5L Cr (Apr 2024) → ₹184.0L Cr (Apr 2025) → ₹213.6L Cr (Mar 2026)",
      "FY25 added ₹18.2L Cr; FY26 added ₹29.6L Cr — 63% more absolute credit in consecutive years",
      "YoY: +11.0% FY25 → +16.1% FY26",
    ],
    "inferences": [
      "Compounding means each year's absolute addition is larger even at the same growth rate — the system is in a self-reinforcing expansion",
      "'Multi-year credit supercycle' characterisation is an inference from trajectory shape and structural drivers, not a label in SIBC",
      "Lenders with scalable origination compound their advantage because each year's base is larger",
    ],
    "hypothesis": [
      "Absolute additions will keep growing if the macro holds — depends on policy rates, NPA cycle, and GDP growth remaining above 6%",
    ],
  },

  "nonfood-credit-all-the-signal": {
    "claim_type": "data",
    "facts": [
      "Non-food credit: ₹212.9L Cr of ₹213.6L Cr total at Mar 2026 — 99.7% of Bank Credit",
      "Food credit: ₹0.70L Cr at Mar 2026",
      "FY26 +16.1% headline growth is entirely a non-food signal",
    ],
    "inferences": [
      "Non-food credit is the structurally relevant metric for banking system capacity — food credit is seasonal procurement financing",
      "March-end non-food is the clean anchor for cross-cycle comparisons because it strips out seasonal kharif procurement peaks",
    ],
  },

  "food-credit-jan-artifact": {
    "claim_type": "inference",
    "facts": [
      "March-end food credit: ₹0.21L Cr (Mar 2024) → ₹0.29L Cr (Mar 2025, +38.4%) → ₹0.70L Cr (Mar 2026, +139.4%)",
      "Jan peaks: ₹0.46L Cr (Jan 2024) → ₹0.89L Cr (Jan 2026, +95%)",
      "Both peaks and troughs are rising across two cycles",
    ],
    "inferences": [
      "Seasonal pattern (Jan peak, March trough) is caused by kharif procurement agencies drawing in Jan and repaying by March — mechanism not stated in SIBC, inferred from PSU procurement structure",
      "Rising absolute peaks and troughs indicate the underlying procurement cycle is growing, not merely seasonal noise",
      "The mechanism is MSP procurement growth — MSP announcement values and procurement volumes are rising each cycle",
    ],
    "hypothesis": [
      "Future food credit growth depends on MSP policy and procurement agency behaviour — could reverse if procurement strategy changes or FCI reforms proceed",
    ],
  },

  "bankcredit-april-date-convention": {
    "claim_type": "data",
    "facts": [
      "Bank Credit aggregate columns labelled Apr 2024 (Apr 5, 2024) and Apr 2025 (Apr 4, 2025) — RBI fortnightly cycle",
      "Sub-sectors use Mar 22, 2024 and Mar 21, 2025 — different actual dates in the same statement",
      "Published 16.1% YoY uses RBI's own variation column, not a recomputed figure",
    ],
    "inferences": [
      "Different actual dates within the same SIBC statement create an arithmetic mismatch if mixed naively across rows",
      "RBI's fortnightly publication cycle is the structural cause of this date offset — the 'April' label is the closest fortnight to March 31",
    ],
  },

  "credit-cycle-expansion": {
    "claim_type": "inference",
    "facts": [
      "FY26 added ₹29.6L Cr (Mar 2025 → Mar 2026) vs ₹18.2L Cr in FY25 — 63% increase in annual flow",
      "Bank Credit: ₹184.0L Cr (Apr 2025) → ₹213.6L Cr (Mar 2026)",
    ],
    "inferences": [
      "'Formalisation of credit access' rather than rate-driven recovery characterisation derives from MSME, retail, services growth drivers visible in sub-sector data",
      "4-5 year structural tailwind framing inferred from GST formalisation timeline (2017-19) and UDYAM registration cohorts (2020+) now reaching credit age",
      "FY27 requires adding ₹34L Cr at 16% growth — computed from ₹213.6L Cr × 0.16",
    ],
    "hypothesis": [
      "Whether absolute additions keep rising depends on RBI policy rates, NPA cycle evolution, and macro growth remaining above 6%",
    ],
  },

  # ── Section 2: Main Sectors ────────────────────────────────────────────────

  "fy26-all-sectors-synchronised": {
    "claim_type": "data",
    "facts": [
      "FY26 YoY: Agriculture +15.7%, Industry +15.0%, Services +19.0%, Personal Loans +16.2%",
      "FY25 comparison: Agriculture +10.4%, Industry +8.2%, Services +12.0%, Personal Loans +11.7%",
      "Every sector added 3.5–7.0pp to its growth rate — a synchronised broad-based expansion",
    ],
    "inferences": [
      "Synchronised multi-sector acceleration of this magnitude is unusual — last comparable cycle was FY22-23 post-COVID re-opening",
      "Single-sector concentrated lenders still captured the tailwind because every sector simultaneously accelerated",
    ],
  },

  "services-growth-acceleration": {
    "claim_type": "inference",
    "facts": [
      "Services YoY: +12.3% Jan 2025 → +15.5% Jan 2026 → +19.0% Mar 2026",
      "Bank credit to NBFCs: +7.4% FY25 → +26.3% FY26, adding ₹4.30L Cr incremental",
    ],
    "inferences": [
      "NBFC re-acceleration identified as the primary Services driver — derived from the NBFCs sub-line being the largest within services and its 4× FY26 acceleration",
      "Services characterised as structural not cyclical based on multi-period trend and identification of NBFC + tech sector as structural sub-drivers",
      "Services overtaking Personal Loans as fastest-growing main category is directly verifiable: 19.0% vs 16.2% FY26 YoY",
    ],
  },

  "industry-reaccelerating": {
    "claim_type": "inference",
    "facts": [
      "Industry YoY: +8.2% FY25 → +15.0% FY26 — 6.8pp acceleration, largest single-year move across all main sectors",
      "Within Industry: Micro and Small +33.1%, Medium +21.7%, Large +8.9%",
      "Sub-sector drivers: All Engineering +32.2%, Petroleum +32.5%, Basic Metal +19.4%",
    ],
    "inferences": [
      "'SME-led with PLI capex overlay' is an inference from the concentration of growth in Micro/Small and specific capex-intensive sectors under PLI schemes",
      "Banks organised around large corporate lending are missing the fastest-growing industrial segment — derived from Large at only +8.9% vs total industry at +15.0%",
    ],
  },

  "personal-loans-largest-sector": {
    "claim_type": "data",
    "facts": [
      "Personal Loans: ₹52.3L Cr (Jan 2024) → ₹58.5L Cr (Jan 2025) → ₹67.2L Cr (Jan 2026) → est ₹69.6L Cr (Mar 2026)",
      "FY26 YoY +16.2% vs +11.7% FY25",
      "Gold Loans +123.1%, Vehicle Loans +18.6%, Credit Cards +3.5%, Consumer Durables -5.3% within FY26",
    ],
    "inferences": [
      "Retail has decisively overtaken wholesale as dominant credit category — Personal Loans at ₹69.6L Cr is larger than any other main sector",
      "Aggregate masking opposite directional trends — the 16.2% average is a misleading summary of simultaneously expanding and contracting sub-products",
    ],
  },

  "main-sectors-undercount": {
    "claim_type": "data",
    "facts": [
      "Agriculture + Industry + Services + Personal Loans = ₹202.3L Cr at Mar 2026",
      "Total Bank Credit: ₹213.6L Cr (adding Food Credit ₹0.70L Cr reaches ₹203.0L Cr)",
      "Gap: ₹10.6L Cr — ~5% of total bank credit unclassified",
    ],
    "inferences": [
      "Gap includes small business loans, public-sector advances, and other unclassified categories — implied by structure of SIBC statement",
      "Any macro leverage ratio built from sector sums will understate total credit by approximately 5%",
    ],
  },

  "services-credit-entry": {
    "claim_type": "inference",
    "facts": [
      "Services: ₹44.1L Cr (Jan 2024) → ₹60.6L Cr (Mar 2026) — ₹16.5L Cr addition in 27 months",
      "NBFCs ₹20.66L Cr (+26.3%), CRE +16.2%, Trade +16.1% within Services FY26",
    ],
    "inferences": [
      "Each services sub-sector has distinct risk and opportunity profile — NBFCs vs CRE vs Trade require different product capabilities",
      "Lenders building IT working capital, logistics finance, hospitality project finance are entering the fastest-growing formal credit channel",
    ],
    "hypothesis": [
      "Whether sub-sector growth rates persist depends on NBFC cycle timing, policy rates, and commercial real estate demand in data centre and grade-A office",
    ],
  },

  # ── Section 3: Industry by Size ────────────────────────────────────────────

  "micro-small-growth-tripled": {
    "claim_type": "inference",
    "facts": [
      "Micro and Small YoY: +9.6% FY25 → +33.1% FY26",
      "Absolute credit: ₹7.17L Cr (Jan 2024) → ₹7.98L Cr (Mar 2025) → ₹10.63L Cr (Mar 2026)",
      "FY26 incremental: ₹2.65L Cr — 4× the FY25 incremental of ₹0.64L Cr",
      "PSL MSE confirms: ₹22.4L Cr → ₹29.0L Cr, +29.5% YoY — two independent series aligned",
    ],
    "inferences": [
      "Jan, Feb, Mar 2026 all showing 29–33% rules out a single-month anomaly — multi-period consistency confirms trend",
      "GST formalisation, UDYAM enrolment, and digital banking making millions of MSMEs newly creditworthy — inference from timing of regulatory changes (GST 2017, UDYAM 2020) and credit age of these cohorts",
      "'Inflection confirmed' characterisation based on multi-period data consistency plus independent PSL MSE series alignment",
    ],
    "hypothesis": [
      "Continuation of 30%+ growth depends on bureau coverage filling in and credit losses not materialising at scale — first-cycle borrowers have no through-cycle history",
    ],
  },

  "large-corporate-stagnant": {
    "claim_type": "data",
    "facts": [
      "Large enterprise YoY: +6.8% FY25 → +8.9% FY26",
      "Absolute: ₹26.03L Cr (Jan 2024) → ₹29.31L Cr (Jan 2026)",
      "FY26: Large grew ₹2.7L Cr while Micro and Small grew ₹2.65L Cr — near-parity for the first time in this dataset",
    ],
    "inferences": [
      "'Relationship maintenance, not a growth game' is a strategic inference from the relative growth rate differential vs the overall system",
      "Banks must re-allocate origination resources to the SME segment — a strategic inference from where absolute credit additions are concentrating",
    ],
  },

  "medium-enterprise-sweet-spot": {
    "claim_type": "inference",
    "facts": [
      "Medium enterprise YoY: +18.4% FY25 → +21.7% FY26",
      "Faster than Large (+8.9%), nearly as fast as Micro & Small (+33.1%)",
    ],
    "inferences": [
      "'Too large for MSME fintech products and too small for DCM access' — structural product gap inference based on ticket size and credit market segmentation, not in SIBC",
      "₹1L Cr+ addressable market for working capital and capex facilities — inference from medium enterprise outstanding and sector growth trajectory",
    ],
  },

  "size-definition-boundary-issue": {
    "claim_type": "inference",
    "facts": [
      "Micro and Small YoY: +33.1% FY26",
      "MSME categories follow MSMED Act definitions — size boundaries defined by turnover and investment thresholds",
    ],
    "inferences": [
      "Enterprise reclassification when crossing MSMED Act thresholds inflates the series growth without reflecting new credit disbursement",
      "PSL MSE at +29.5% uses a different boundary definition and provides a partial sanity check — consistent direction reduces (but doesn't eliminate) the reclassification concern",
      "33.1% should be treated as an upper bound on real MSME credit growth; true disbursement growth is lower",
    ],
    "hypothesis": [
      "The precise share attributable to reclassification vs genuine new lending cannot be quantified from SIBC alone — requires UDYAM and MSME census data",
    ],
  },

  "msme-first-cycle-window": {
    "claim_type": "inference",
    "facts": [
      "Micro and Small: ₹7.17L Cr (Jan 2024) → ₹10.63L Cr (Mar 2026), adding ₹3.46L Cr in 27 months",
    ],
    "inferences": [
      "'Meaningful share are first-cycle formal borrowers' — inference from the timing of GST registration (2017–19) and UDYAM enrolment (2020+) cohorts reaching credit age",
      "GST-registered MSMEs from 2019–22 now have 4–6 years of digital financial history (GST returns, UPI flows, e-way bills) — timeline arithmetic",
      "2–3 year pricing advantage window for alt-data underwriting — inference from competitive dynamics: data network effects take 2–3 years to replicate",
    ],
    "hypothesis": [
      "FY27–28 will be the first stress test — first-cycle borrowers have no through-the-cycle performance history; loss curves could surprise",
    ],
  },

  # ── Section 4: Services ────────────────────────────────────────────────────

  "nbfc-risk-weight-cycle-complete": {
    "claim_type": "inference",
    "facts": [
      "Bank credit to NBFCs: ₹15.23L Cr (Mar 2024) → ₹16.35L Cr (Mar 2025, +7.4%) → ₹20.66L Cr (Mar 2026, +26.3%)",
      "FY25 incremental: ₹1.12L Cr; FY26 incremental: ₹4.30L Cr — nearly 4×",
    ],
    "inferences": [
      "The 2023 RBI risk-weight hike on consumer lending (Nov 2023 circular) constrained bank-to-NBFC flows in FY24–25 — causal link inferred from timing of circular and observed FY25 slowdown to +7.4%",
      "'Risk-weight cycle fully absorbed' characterisation requires knowledge of the RBI Nov 2023 circular on unsecured and consumer lending risk weights",
      "Banks actively re-building NBFC lending books in FY26 inferred from the 4× flow acceleration back to pre-tightening trajectory",
    ],
    "hypothesis": [
      "RBI could re-tighten if NBFC sector overheats again — watch RBI Financial Stability Reports H1 FY27 for any systemic risk signal",
    ],
  },

  "computer-software-multi-year-surge": {
    "claim_type": "inference",
    "facts": [
      "Computer Software: ₹0.26L Cr (Jan 2024) → ₹0.41L Cr (Jan 2026) → ₹0.46L Cr (Feb 2026)",
      "+28.2% YoY Jan 2025, +20.7% YoY Jan 2026 — three consecutive periods of 20%+ growth",
    ],
    "inferences": [
      "IT services working capital scales with headcount and project volume — structural inference linking the credit series to IT sector operating dynamics",
      "Multi-year trend characterisation based on 3+ period consistency at above-market growth rates",
    ],
  },

  "transport-operators-decelerating": {
    "claim_type": "inference",
    "facts": [
      "Transport Operators YoY: +12.0% Jan 2025 → +4.3% Jan 2026",
      "₹2.29L Cr (Jan 2024) → ₹2.57L Cr (Jan 2025) → ₹2.68L Cr (Jan 2026)",
      "Sharpest deceleration across all services sub-sectors this cycle",
    ],
    "inferences": [
      "Post-COVID fleet normalisation is identified as the cause — inferred from timing: COVID drove fleet additions in 2021–23, normalisation plateau visible from 2024",
      "Fleet utilisation rates as leading indicator of repayment stress — inference from the operating leverage structure of transport businesses: fixed cost, variable revenue",
    ],
    "hypothesis": [
      "Whether deceleration indicates stress vs saturation depends on fleet utilisation data not available in SIBC — requires route-level operational data",
    ],
  },

  "cre-trade-consistent-growth": {
    "claim_type": "inference",
    "facts": [
      "CRE YoY: +14.1% Jan 2025 → +16.2% Jan 2026, at ₹5.98L Cr",
      "Trade YoY: +14.5% Jan 2025 → +16.1% Jan 2026, at ₹13.09L Cr",
      "Trade is the 2nd-largest services sub-sector after NBFCs + Other Services combined",
    ],
    "inferences": [
      "CRE growth driven by data centers, logistics, grade-A office — not residential developer exposure — requires external context (CBRE, JLL market data) to confirm sub-composition",
      "Trade credit at ₹13.09L Cr at 16% growth is the single largest opportunity by absolute size within services — derived from sub-sector size comparison",
    ],
  },

  "nbfc-double-counting": {
    "claim_type": "inference",
    "facts": [
      "NBFC credit at ₹20.66L Cr (Mar 2026) is the largest single line in Services",
      "Bank credit to NBFCs is the upstream funding; NBFC on-lending to retail/MSME is downstream",
    ],
    "inferences": [
      "Bank-to-NBFC credit flow becomes downstream NBFC loans to retail and MSME borrowers — those loans appear again in personal loans and industrial sub-sector tables",
      "No system-wide deduplicated credit view exists in SIBC — the double-counting is structural, not a data error",
      "Household leverage ratios that add bank credit + NBFC credit systematically overstate total debt — the NBFC channel is intermediate, not additive",
    ],
  },

  "other-services-opacity": {
    "claim_type": "data",
    "facts": [
      "'Other Services': ₹9.37L Cr (Jan 2024) → ₹12.36L Cr (Feb 2026), +31.9% in 24 months",
      "~21% of the entire Services sector at ₹12.4L Cr — larger than CRE, Computer Software, or Transport",
    ],
    "inferences": [
      "Without sub-classification, the growth drivers of the second-largest services component are analytically opaque",
      "BSR-1 quarterly data from RBI provides granular sub-classification; SIBC does not publish it at this level",
    ],
  },

  "co-lending-infrastructure": {
    "claim_type": "inference",
    "facts": [
      "Bank credit to NBFCs added ₹4.30L Cr in FY26 — nearly 4× the FY25 flow of ₹1.12L Cr",
    ],
    "inferences": [
      "NBFCs need bank balance sheet capacity; banks need NBFC origination reach — strategic complementarity inference from the two-sided structure of bank-NBFC partnerships",
      "Co-origination agreements, warehouse lines, and LMS with co-lending partition logic are the specific product wedges — inferred from the contractual and operational requirements of co-lending",
      "12–18 month window before in-house tooling fills the gap — inference from enterprise software build cycles at large banks",
    ],
    "hypothesis": [
      "Window size depends on how quickly tier-1 banks build internal infrastructure — could compress if large bank tech teams accelerate",
    ],
  },

  "trade-finance-compounder": {
    "claim_type": "inference",
    "facts": [
      "Trade credit: ₹9.85L Cr (Jan 2024) → ₹11.27L Cr (Jan 2025) → ₹13.09L Cr (Jan 2026) — +33% in 2 years",
      "2nd-largest services sub-sector by credit outstanding",
    ],
    "inferences": [
      "Invoice discounting, buyer-financed supply chains, and distributor credit are the primary instruments in this category — inferred from the operational structure of Trade financing",
      "Fintech platforms building supply chain finance have direct access to the fastest-compounding services sub-sector by absolute credit size",
    ],
  },

  # ── Section 5: Personal Loans ──────────────────────────────────────────────

  "gold-loans-structural-surge": {
    "claim_type": "inference",
    "facts": [
      "Gold Loans: ₹0.93L Cr (Mar 2024) → ₹2.06L Cr (Mar 2025, +121.1%) → ₹4.60L Cr (Mar 2026, +123.1%)",
      "Share of personal credit: 1.7% (Mar 2024) → 3.5% (Mar 2025) → 6.6% (Mar 2026)",
    ],
    "inferences": [
      "RBI Sep 2024 circular reclassified bullet-repayment gold loans from agri/business buckets to 'loans against gold jewellery' — stock effect, not new disbursement",
      "Gold prices rose ~30% in the period, expanding collateral value on existing books — a separate price-driven stock effect",
      "'Most of the 5× growth is reclassification plus price effect' — derived by recognising both effects are stock adjustments recognised by Mar 2026",
      "Specialised gold NBFCs (Manappuram, Muthoot, IIFL) own the operational capability — market structure inference requiring knowledge of the gold lending ecosystem",
    ],
  },

  "credit-card-collapse": {
    "claim_type": "inference",
    "facts": [
      "Credit Card Outstanding YoY: +13.0% Jan 2025 → +1.5% Jan 2026 → +3.5% FY26",
      "FY26 incremental: ₹10,094 Cr vs ₹27,350 Cr FY25 — under one-third the pace",
      "Consumer Durables: -1.0% FY25 → -5.3% FY26",
    ],
    "inferences": [
      "RBI Nov 2023 risk-weight increases on unsecured consumer lending are the structural binding constraint — requires knowledge of the circular",
      "'Policy-constrained not demand-constrained' characterisation requires the RBI circular as context — demand for unsecured credit remains; the constraint is regulatory capital cost",
      "UPI credit lines and BNPL absorbing displaced demand — inference from structural demand elasticity: displaced demand migrates to unregulated channels not captured in SIBC",
    ],
  },

  "vehicle-loans-accelerating": {
    "claim_type": "inference",
    "facts": [
      "Vehicle Loans YoY: +8.6% FY25 → +18.6% FY26",
      "₹5.61L Cr (Jan 2024) → ₹6.23L Cr (Mar 2025) → ₹7.39L Cr (Mar 2026)",
      "FY26 incremental: ₹1.16L Cr",
    ],
    "inferences": [
      "EV adoption, commercial fleet renewal, and two-wheeler financing cited as drivers — inference from macro auto sector data (SIAM volumes, EV policy) not in SIBC",
      "OEM captive NBFCs for personal vehicle side; TReDS and supply chain finance for component side — inference from market structure of auto lending ecosystem",
    ],
  },

  "consumer-durables-accelerating-decline": {
    "claim_type": "inference",
    "facts": [
      "Consumer Durables YoY: -2.4% Jan 2025, -1.0% FY25, -5.3% FY26",
      "Book declined: ₹23,445 Cr (Mar 2025) → ₹21,962 Cr (Mar 2026)",
      "Three consecutive periods of negative growth, accelerating",
    ],
    "inferences": [
      "Point-of-sale consumer durable finance being displaced by BNPL and embedded credit — requires knowledge of the BNPL market structure and product substitution dynamics",
      "'Structural decline not cyclical' inference is based on 3+ consecutive periods of negative growth plus the BNPL displacement mechanism",
      "Credit migrates off-SIBC rather than disappearing — inferred from total personal loan growth remaining positive while this category contracts",
    ],
  },

  "personal-loans-aggregate-hides-divergence": {
    "claim_type": "data",
    "facts": [
      "Personal Loans aggregate +16.2% YoY FY26",
      "Within: Gold Loans +123.1%, Vehicle Loans +18.6%, Credit Cards +3.5%, Consumer Durables -5.3%",
    ],
    "inferences": [
      "Weighted average of opposite directional trends makes the aggregate directionally misleading for product-level strategy",
      "RBI 2023 risk-weight tightening on unsecured credit is still working through the book — requires circular knowledge to explain the divergence pattern",
    ],
  },

  "gold-loans-reclassification-overstates-demand": {
    "claim_type": "inference",
    "facts": [
      "Gold loans grew 5× from Mar 2024 (₹0.93L Cr) to Mar 2026 (₹4.60L Cr)",
    ],
    "inferences": [
      "RBI Sep 2024 circular required bullet-repayment gold loans to migrate from agri/business categories to 'loans against gold jewellery' — requires knowledge of the circular",
      "Gold prices rose ~30% in the period, expanding collateral value on existing loan portfolios",
      "Both effects are one-time stock adjustments fully recognised by Mar 2026 — no ongoing flow inflation after this date",
    ],
    "hypothesis": [
      "Stress-test for a gold-price reversal >20% — LTV ratios on marginal gold loans may be aggressive if origination during the price peak was at elevated collateral values",
    ],
  },

  "other-personal-loans-opacity": {
    "claim_type": "data",
    "facts": [
      "'Other Personal Loans': ₹13.96L Cr (Jan 2024) → ₹15.11L Cr (Jan 2025) → ₹16.85L Cr (Jan 2026)",
      "+20.7% in 2 years — larger than Vehicle Loans and Education combined",
    ],
    "inferences": [
      "Likely includes salary advances, top-up home loans, and personal overdrafts — classification inference from typical retail loan product structures",
      "BSR-1 quarterly data from RBI provides the sub-classification required for meaningful analysis of this bucket",
    ],
  },

  "gold-loan-market-entry": {
    "claim_type": "inference",
    "facts": [
      "Gold Loans: ₹0.93L Cr (Mar 2024) → ₹4.60L Cr (Mar 2026)",
    ],
    "inferences": [
      "Gold NBFCs (Muthoot, Manappuram) have had market exclusivity for decades — market structure inference requiring knowledge of the gold lending competitive landscape",
      "Banks are structurally cheaper (lower cost of funds) — inference from bank vs NBFC funding cost differential in Indian credit markets",
      "Operational moat (assay, cash management, branch density) — not regulatory — is the real entry barrier; inferred from the absence of regulatory restrictions on bank gold lending",
    ],
  },

  "vehicle-ev-credit": {
    "claim_type": "inference",
    "facts": [
      "Vehicle loans: ₹5.61L Cr (Jan 2024) → ₹7.39L Cr (Mar 2026), +31.7% in 27 months",
    ],
    "inferences": [
      "EV sales crossed 20L units in FY25 — external market data (VAHAN, SIAM) used as context for the credit category growth",
      "Standard vehicle finance doesn't address battery degradation risk, EV residual values, or subsidy-linked EMI structures — product gap inference from EV economics",
    ],
    "hypothesis": [
      "First-mover advantage in EV-specific credit is 2–3 years wide — depends on competitive response timing and EV penetration rate",
      "Fleet EV lending (e-commerce, last-mile logistics) as highest-volume entry point — hypothesis about which segment has the best risk/volume tradeoff",
    ],
  },

  # ── Section 6: Priority Sector ─────────────────────────────────────────────

  "psl-msme-structural-acceleration": {
    "claim_type": "data",
    "facts": [
      "PSL Micro and Small: ₹19.74L Cr (Mar 2024) → ₹22.39L Cr (Mar 2025, +13.4%) → ₹29.0L Cr (Mar 2026, +29.5%)",
      "industryBySize Micro and Small: ₹7.98L Cr (Mar 2025) → ₹10.63L Cr (Mar 2026), +33.1%",
      "Both independent series point in the same direction",
    ],
    "inferences": [
      "PSL incentive structure (40% ANBC target) is compounding alongside the MSME formalisation wave — inference from the PSL regulatory framework",
      "Banks that built MSME origination infrastructure in FY24–25 are harvesting PSL credit at scale — derived from the acceleration timing vs bank-level capex cycles",
    ],
  },

  "psl-housing-anomalous-surge": {
    "claim_type": "inference",
    "facts": [
      "PSL Housing: ₹7.55L Cr (Mar 2024) → ₹7.47L Cr (Mar 2025, -1.1%) → ₹10.44L Cr (Mar 2026, +39.8%)",
      "personalLoans.Housing: +11.5% YoY at ₹30.1L Cr → ₹33.6L Cr",
    ],
    "inferences": [
      "RBI October 2024 PSL housing limit revision (metro: ₹35L → ₹45L; non-metro: ₹25L → ₹35L) is the direct cause — requires knowledge of the RBI circular",
      "Existing mortgages reclassified into the PSL bucket — not new originations — requires understanding of how PSL limit revisions trigger reclassification",
      "personalLoans.Housing at +11.5% is the correct new lending signal — a different series in the same report that is not affected by the PSL reclassification",
    ],
  },

  "export-credit-declining": {
    "claim_type": "inference",
    "facts": [
      "Export Credit PSL: ₹11,330 Cr (Mar 2024) → ₹11,805 Cr (Mar 2025, +4.2%) → ₹10,270 Cr (Feb 2026, -13.0% FY)",
    ],
    "inferences": [
      "Global trade uncertainty, rupee dynamics, and tighter underwriting are contributing — inference from macro context requiring external trade and FX data",
      "Pullback is risk appetite not demand — inference from India merchandise exports holding up while credit contracted; a divergence that implicates supply-side underwriting rather than demand destruction",
    ],
  },

  "psl-housing-reclassification": {
    "claim_type": "inference",
    "facts": [
      "PSL Housing growth: +39.8% YoY FY26 (Statement 6)",
      "personalLoans.Housing growth: +11.5% YoY (Statement 5) — the same underlying product category, different statement",
    ],
    "inferences": [
      "RBI October 2024 PSL housing limit revision reclassified existing mortgages into the PSL bucket — requires external circular knowledge",
      "₹2.97L Cr apparent addition in FY26 represents existing loans visible in a new column, not new originations",
      "SIBC presents this as +39.8% with no footnote — a data quality inference about the absence of disclosure in the source document",
    ],
  },

  "psl-totals-not-additive": {
    "claim_type": "inference",
    "facts": [
      "Weaker Sections: ₹20.32L Cr (Feb 2026) — a cross-cutting PSL sub-category",
    ],
    "inferences": [
      "Weaker Sections (SC/ST, small farmers, SHG members) appear simultaneously in Agriculture, MSME, and Housing rows — cross-cutting classification creates double-counting if summed",
      "Correct PSL total is 40% of ANBC per RBI PSL guidelines — not the arithmetic sum of category rows",
      "Any PSL analysis that sums the category rows will overstate the PSL book by the Weaker Sections overlap",
    ],
  },

  "renewable-energy-project-finance": {
    "claim_type": "inference",
    "facts": [
      "Renewable Energy PSL: ₹0.06L Cr (Mar 2024) → ₹0.10L Cr (Mar 2025, +78.3%) → ₹0.14L Cr (Feb 2026, +35.2% FY)",
      "₹0.14L Cr = 0.007% of ₹213.6L Cr total bank credit",
    ],
    "inferences": [
      "India needs ₹20–25L Cr of renewable energy investment by 2030 — NITI Aayog/IRENA/MNRE projection; not in SIBC",
      "No incumbent lender has built renewable energy project finance capabilities at scale — market structure observation requiring industry knowledge",
    ],
    "hypothesis": [
      "First-movers on DISCOM offtake risk underwriting, distributed solar, and battery storage finance will own this market for a decade — depends on regulatory evolution, grid integration, and DISCOM financial health",
    ],
  },

  "pslc-trading-tooling": {
    "claim_type": "inference",
    "facts": [
      "PSL Micro and Small Enterprises: +29.5% YoY in FY26",
    ],
    "inferences": [
      "PSLC trading on RBI's e-Kuber platform becomes more active as PSL books grow asymmetrically across banks — inferred from the mechanics of PSLC markets: asymmetric growth creates buyers and sellers",
      "Compliance tech for ANBC calculation, PSL gap forecasting, and PSLC trade timing is a specific, operational product need for mid-size banks",
    ],
  },

  # ── Section 7: Industry by Type ────────────────────────────────────────────

  "pli-capex-broadening-confirmed": {
    "claim_type": "inference",
    "facts": [
      "FY26 YoY: All Engineering +32.2% (₹3.17L Cr), Petroleum +32.5% (₹2.04L Cr), Basic Metal +19.4% (₹5.18L Cr), Chemicals +14.9%, Food Processing +14.0%, Vehicles & Parts +18.1%",
      "FY25 comparison: Engineering +22.0%, Petroleum +16.5%, Basic Metal +12.8% — every sector accelerated",
    ],
    "inferences": [
      "PLI capex has spread beyond electronics to Petroleum, Basic Metal, and Cement — requires knowledge of PLI scheme sectors approved by the government",
      "PSU banks underweight industrial term loans have under-priced FY27 upside — strategic inference from relative positioning vs the capex acceleration",
    ],
  },

  "gems-jewellery-gold-price-proxy": {
    "claim_type": "inference",
    "facts": [
      "Gems and Jewellery: ₹0.82L Cr (Feb 2024) → ₹0.83L Cr (Feb 2025) → ₹1.17L Cr (Feb 2026), +40.2% YoY",
      "Gold prices rose ~25–30% in the same period",
    ],
    "inferences": [
      "Jeweller working capital scales directly with gold inventory value — mechanistic inference from the structure of jewellery financing (inventory pledged at market value)",
      "At least 25pp of this growth is a gold price effect — computed from ~30% price rise applied to a working capital line that reflects current inventory value",
      "Real volume growth estimated at 10–15% — derived by subtracting the price effect from total 40% growth",
    ],
    "hypothesis": [
      "A 15–20% gold price retracement would compress working capital requirements and may trigger LTV covenant breaches on marginal loans originated at peak prices",
    ],
  },

  "infrastructure-decelerating": {
    "claim_type": "inference",
    "facts": [
      "Infrastructure: ₹13.37L Cr (Mar 2025) → est ₹14.63L Cr (Mar 2026), +9.5% YoY",
      "Largest industrial sub-sector at ₹14.9L Cr — barely expanding relative to its size",
    ],
    "inferences": [
      "Projects from the 2019–24 highway/metro supercycle are in operations, repaying loans rather than drawing new disbursements — inference from infrastructure project lifecycle and the government's stated project completion timelines",
      "Next capex wave (data centers, green hydrogen, semiconductor fabs) still 2–4 years from scale — inference from project pipeline status and capital commitment timelines",
    ],
    "hypothesis": [
      "Infrastructure credit growth recovery timing depends on when the next capex wave moves from planning to disbursement — estimated 2028–2030 window based on current project timelines",
    ],
  },

  "chemicals-petroleum-capex": {
    "claim_type": "inference",
    "facts": [
      "Chemicals +14.9% YoY (₹3.08L Cr at Mar 2026)",
      "Petroleum, Coal Products +32.5% YoY (₹2.04L Cr at Mar 2026)",
      "Both growing faster than the industry average of +15.0% in FY26",
    ],
    "inferences": [
      "India's specialty chemicals export push and refinery upgrade cycle are the structural drivers — inference from industry policy (PLI for specialty chemicals) and refinery capacity expansion announcements",
      "Longer tenure and larger ticket sizes than most industry sub-sectors — inference from the capital-intensive nature of chemical plant and refinery capex",
    ],
  },

  "infrastructure-sub-classification-absent": {
    "claim_type": "inference",
    "facts": [
      "'Infrastructure': ₹14.9L Cr (Mar 2026), +9.5% YoY — the single largest industrial sub-sector",
    ],
    "inferences": [
      "Infrastructure aggregates roads, power, telecom, railways, ports, and urban infra — each sub-type has different growth drivers, tenor, and credit quality",
      "+9.5% aggregate may mask contraction in some sub-types (e.g., highway repayments) and strong growth in others (e.g., data centers) — requires sub-classification not available in SIBC",
      "MCA filings, NITI Aayog project monitoring, or RBI BSR-1 provide the sub-sector breakdown required for meaningful analysis",
    ],
  },

  "industry-type-partition-not-exact": {
    "claim_type": "inference",
    "facts": [
      "Industry sub-types do not sum to the Industry total from the main sector view",
    ],
    "inferences": [
      "Some sub-sectors use different classification vintages within the same SIBC publication",
      "RBI uses a residual 'Other Industries' bucket that is not consistently sized across periods",
      "Different source tables within SIBC (Statements 4, 5, 6) have different reconciliation levels and date anchors",
    ],
  },

  "pli-supply-chain-finance": {
    "claim_type": "inference",
    "facts": [
      "All Engineering credit added ₹1.21L Cr in FY26",
    ],
    "inferences": [
      "PLI-approved anchor companies (electronics, defence, EV components) have 50–100 tier-2 suppliers — inference from the supply chain depth of PLI sectors",
      "Supply chain finance against anchor-validated invoices removes the need for individual MSME underwriting — inferred from the mechanics of reverse-factoring and anchor-led supply chain finance",
      "Banks that signed PLI anchors as current account clients in 2022–24 are positioned — inference from relationship banking: CA relationships precede credit relationships",
    ],
  },

  "basic-metal-capex-lending": {
    "claim_type": "inference",
    "facts": [
      "Basic Metal and Metal Product: +19.4% YoY FY26, at ₹5.18L Cr (Mar 2026)",
      "2nd-largest industrial sub-sector by credit outstanding",
    ],
    "inferences": [
      "India's steel capacity additions (JSW, SAIL, Tata Steel expansions) are the primary driver — requires knowledge of announced expansion plans in the steel sector",
      "Green steel transitions (DRI, EAF) will need project finance on a different risk model — inference from the technology shift underway in the global steel industry",
    ],
    "hypothesis": [
      "Banks that develop green steel underwriting (hydrogen-DRI, EAF economics, carbon credit structures) will lead this transition — still 2–3 years from mainstream; depends on green steel economics and regulatory incentives",
    ],
  },

}


# ── TypeScript serialiser ─────────────────────────────────────────────────────

def ts_string(s: str) -> str:
    """Escape a Python string for TypeScript."""
    return s.replace("\\", "\\\\").replace('"', '\\"')

def ts_string_array(items: list[str], indent: int) -> str:
    pad = " " * indent
    inner = f",\n{pad}".join(f'"{ts_string(x)}"' for x in items)
    return f"[\n{pad}{inner},\n{' ' * (indent - 2)}]"

def build_basis_ts(data: dict, base_indent: int) -> str:
    """
    Render claim_type + basis fields as TypeScript, indented at base_indent.
    """
    pad = " " * base_indent
    lines = []

    claim_type = data.get("claim_type", "data")
    lines.append(f'{pad}claim_type: "{claim_type}",')

    facts       = data.get("facts", [])
    inferences  = data.get("inferences", [])
    hypothesis  = data.get("hypothesis", [])

    arr_indent = base_indent + 4
    lines.append(f"{pad}basis: {{")
    lines.append(f"{pad}  facts:      {ts_string_array(facts, arr_indent)},")
    lines.append(f"{pad}  inferences: {ts_string_array(inferences, arr_indent)},")
    if hypothesis:
        lines.append(f"{pad}  hypothesis: {ts_string_array(hypothesis, arr_indent)},")
    lines.append(f"{pad}}},")

    return "\n".join(lines)


# ── Patcher ───────────────────────────────────────────────────────────────────

def patch_annotation(text: str, ann_id: str, basis_data: dict) -> tuple[str, bool]:
    """
    Find the annotation with the given id and insert claim_type + basis
    before the closing `}` of that annotation object.

    Looks for the pattern:
        id: "ann_id",
        ...
        effect: { ... },
      },

    and inserts before the closing `},`.
    """
    # Locate the id line
    id_pattern = re.compile(
        r'(id:\s*"' + re.escape(ann_id) + r'")',
    )
    m = id_pattern.search(text)
    if not m:
        return text, False

    # From the id line, find the annotation's closing `},`
    # We expect the annotation to end with `effect: { ... },\n      },`
    # Strategy: find the next `effect:` line after the id, then the next
    # standalone `},` on its own indented line.

    start = m.start()

    # Find `effect:` after the id
    effect_pat = re.compile(r'\n(\s+)effect\s*:')
    em = effect_pat.search(text, start)
    if not em:
        return text, False

    indent = em.group(1)  # e.g. "        " (8 spaces for annotation properties)

    # The annotation OBJECT's closing `},` is one indent level up (6 spaces here)
    # because the object is `{ id: ..., effect: ..., }` where `{` is at 6-space indent
    close_indent = indent[2:]   # strip 2 spaces: "        " → "      "
    close_pat = re.compile(r'\n' + re.escape(close_indent) + r'},')

    # Find the FIRST such closing after the effect line (within a reasonable window)
    cm = close_pat.search(text, em.end())
    if not cm:
        return text, False

    # Check basis already present — don't double-insert
    between = text[em.end():cm.start()]
    if "basis:" in between or "claim_type:" in between:
        return text, False

    # Build the insertion
    basis_ts = build_basis_ts(basis_data, len(indent))
    insertion = "\n" + basis_ts

    # Insert after the `effect: ...` closing, before the annotation `},`
    insert_pos = cm.start()
    new_text = text[:insert_pos] + insertion + text[insert_pos:]
    return new_text, True


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    dry_run = "--dry-run" in sys.argv

    print("backfill_sibc_basis.py — SIBC annotation basis backfill")
    print("=" * 56)

    if not ANN_FILE.exists():
        print(f"ERROR: {ANN_FILE} not found")
        sys.exit(1)

    text = ANN_FILE.read_text(encoding="utf-8")
    original = text

    patched   = 0
    skipped   = 0
    not_found = 0

    for ann_id, basis_data in BASIS.items():
        new_text, ok = patch_annotation(text, ann_id, basis_data)
        if ok:
            text = new_text
            patched += 1
            print(f"  ✓  {ann_id}")
        else:
            if f'id: "{ann_id}"' in text:
                skipped += 1
                print(f"  ↷  {ann_id}  (already has basis — skipped)")
            else:
                not_found += 1
                print(f"  ✗  {ann_id}  (NOT FOUND in file)")

    print(f"\n  Patched: {patched}  Skipped: {skipped}  Not found: {not_found}")

    if dry_run:
        print("\n  --dry-run: no files written")
        return

    if patched == 0:
        print("\n  Nothing to write — all annotations already have basis fields.")
        return

    ANN_FILE.write_text(text, encoding="utf-8")
    print(f"\n  Written: {ANN_FILE}")

    # Run promote_annotations.py to sync to web/lib/reports/rbi_sibc.ts
    promote = Path(__file__).parent / "promote_annotations.py"
    if promote.exists():
        print("\n  Running promote_annotations.py …")
        result = subprocess.run(
            ["python3", str(promote)],
            capture_output=True, text=True
        )
        print(result.stdout.strip())
        if result.returncode != 0:
            print("  WARNING: promote_annotations.py exited non-zero")
            print(result.stderr.strip())
    else:
        print(f"\n  NOTE: {promote} not found — run manually to sync to rbi_sibc.ts")


if __name__ == "__main__":
    main()
