# Source catalogue: what exists beyond our four pipelines

> Explored once, so the portals need not be revisited (user, 2026-10-10). Captured 2026-10-10
> from RBI DBIE (in Chrome), rbi.org.in release pages, and the MoSPI/eSankhyiki API. The full DBIE
> listing, 398 tables with frequency and range, is `dbie_catalogue.tsv` beside this file.
> Standing rule (DECISIONS): every source is its own pipeline in the engine; only lending data
> gets a dashboard page; context data is `kind: reference` and feeds L2 relationship tests.

## How each portal can be read

| Portal | Scripted? | Route that works |
|---|---|---|
| DBIE `data.rbi.org.in` | No. An Angular app on an internal gateway with encoded payloads (do not build on it); `rbidocs` resets curl (exit 56); old `dbie.rbi.org.in` fails its certificate (exit 60) | Chrome: open the table → SAP BusinessObjects viewer → Export to Excel. Menus need a full mouse-event sequence. Or the user downloads, as for SIBC |
| rbi.org.in release pages | Listing pages yes; attachments sit on `rbidocs` (blocked) | The user downloads the release file |
| MoSPI `api.mospi.gov.in` | Yes (`pipelines/mospi/mospi_api.py`) | Already used for IIP, WPI, NAS, CPI. Also answers: `plfs/*`, `asuse/*`, `hces/*`, `energy/*`, `asi/*`, `cpialrl/*`, `rbi/*` (indicator lists in the eSankhyiki bundle) |

eSankhyiki's `rbi/` section is **external sector only** (39 indicators: trade, BoP, forex,
external debt, NRI deposits). It is not a scripted back door to RBI credit data.

## Shortlist, ranked by what it would explain

Tier 1 explains moves the coverage count leaves open (Aug 2026: food credit, loans against FDs,
other industries, fertiliser; history: 128 of 176 unexplained), as L2 relationship tests.

| # | Table | Where | Freq · from | What it explains | Kind |
|---|---|---|---|---|---|
| 1 | **Lending & Deposit Rates of SCBs** (WALR fresh/outstanding, by bank group and loan type; term deposit rates) | rbi.org.in release, SectionID 369 | monthly | The price of credit per SIBC sector: housing, vehicle, personal, MSME. Rates → volumes, with lag | reference |
| 2 | **Select Economic Indicators** (repo, SDF, MSF, MCLR, base rate, term deposit and savings rates, call, T-bill, G-sec) | Bulletin Table 1 | monthly · Dec 2010 | Policy transmission; loans against FDs vs the deposit rate | reference |
| 3 | **Advances for public food procurement** | Statistics › Sectoral | monthly · Jan 2005 | Food credit directly (the line is that advance) | reference |
| 4 | **Flow of resources to the commercial sector** (bank vs CP, bonds, ECB, NBFC, equity) | Bulletin 18(a), 18(b) | monthly · Mar 2023 | Substitution: industry credit falling while firms borrow elsewhere | reference |
| 5 | Commercial Paper; ECB; New capital issues | Bulletin 29, 38, 31 | monthly · 2011 / 2004 / 1990 | The parts of #4 with longer history | reference |
| 6 | Gold and silver price, Mumbai | Bulletin 21 | monthly · Apr 1990 | Gold loans against the collateral price (WPI jewellery test was null; this is the direct price) | reference |

Tier 2 is net-new lending data: each would be a pipeline **with a page**.

| # | Table | Where | Freq · from | Why it matters | Cost |
|---|---|---|---|---|---|
| 7 | **Quarterly BSR-1** (credit by occupation, bank group, population group, interest-rate band, state) | rbi.org.in, SectionID 354; annual district-level on DBIE (2010–2026) | quarterly | Who borrows at what rate, where. The deepest lending view RBI publishes | Three measures per entity (accounts, limit, outstanding); occupation taxonomy overlaps SIBC without matching |
| 8 | **Bank-wise variables (public access)**, opened 2026-10-11, see below | Statistics › Performance Indicators | quarterly · Mar 2002 | **Per-bank, RBI-standardised:** the nearest thing India has to a US Call Report | Wide (8 tabs × every SCB × domestic/overseas/global) |
| 9 | SCB select aggregates (deposits, credit, investments, CD ratio) | Statistics › Assets & Liabilities | fortnightly · 1997 | The funding side: deposit growth vs credit growth | Small |
| 10 | Household financial assets and liabilities | Bulletin 52A, 52B | quarterly · Jun 2018 | Household borrowing from banks, NBFCs, HFCs together | Small |
| 11 | Quarterly BSR-2 (deposits) | rbi.org.in, SectionID 382 | quarterly | Deposit mix by type and region | Medium |

Tier 3 is context, taken when a test needs it: PLFS monthly unemployment and wages (MoSPI API,
household income → retail credit); ASUSE quarterly (informal enterprises → MSME); Survey of
Professional Forecasters; NPAs and CRAR (annual); MSP and PDS procurement (annual); Industry-wise
deployment from 2007 (Bulletin 16 / Handbook 169; a different bank set before 2019, so not SIBC history).

## Per-bank quarterly variables: opened 2026-10-11

*"Variables to be published Bank and Bank Group wise (For Public Access)"*, DBIE › Statistics ›
Financial Sector › Banking – Performance Indicators. Quarterly, Mar 2002 – Jun 2026, read in Chrome
(SAP BusinessObjects viewer; prompts: reporting periods, bank names, unit). It tests the strategy
claim that India has no per-institution, standardised, quarterly filing: **for the core of a
Call Report, it does.**

- **Every scheduled commercial bank by name**: public, private (HDFC, ICICI, Axis, Kotak, Bandhan,
  …), foreign, with bank-group totals. The scan read 73+ names before truncating.
- **Every figure split into domestic / overseas / global operations.** That answers the
  "RBI is domestic, banks report global" reconciliation trap at the source.
- **Eight tabs:** Major Balance Sheet Items · Capital Adequacy · Asset Quality · Profitability ·
  Performance Indicators · **Major Sectoral** · Priority / Non-priority Break-up · Infrastructure
  Financing.
- **Major Sectoral, per bank, domestic:** gross advances, gross NPAs and GNPA ratio for food
  credit, non-food credit, **Agriculture, Industry, Services, Retail Loans**. These are RBI's own
  four sectors, so per-bank lines need no bank-segment crosswalk at that depth.
  Example, Bank of Baroda, Sep 2024: gross advances ₹9,38,883 Cr; agriculture ₹1,44,510 Cr (GNPA
  5.30%), industry ₹2,20,809 Cr (1.61%), services ₹3,00,879 Cr (2.70%), retail ₹2,45,438 Cr.
- **What it does not have:** anything below the four sectors (no housing, gold, NBFC lending
  per bank). That depth still lives only in investor presentations and Pillar 3 disclosures.
- **Not yet checked:** how it exports (Excel, as other DBIE reports do), whether later quarters
  restate earlier ones, and whether Σ banks reconciles to SIBC's sector totals (SIBC covers
  "select" banks; this covers all SCBs).

## Lending & Deposit Rates: probed 2026-10-10 (onboarding paused)

Four releases probed (`MLDRSCB{30062026,31072026E,31082026ENG,30092026ENG}.xlsx`, user download).
Onboarding is paused until the user decides the kind (reference or primary with a page), the
source order, and which tables to carry.

- **Excel with 9 tables, and every file holds the full history:**

  | Table | Contents | From |
  |---|---|---|
  | T1 | Lending rate (WALR) on outstanding loans, by bank group | Feb 2012 |
  | T2 | WALR on new loans | Sep 2014 |
  | T3 | Term deposit rate, outstanding deposits | Mar 2013 |
  | T4 | Term deposit rate, new deposits | Mar 2020, then Jan 2021 on |
  | T5 | One-year MCLR per bank (99 banks) | Apr 2016 |
  | T6 | Group MCLR as min, max and median | Apr 2016 |
  | T7 | Floating-rate loan shares by benchmark (base rate, MCLR, EBLR, others) | Sep 2019, quarterly |
  | T8, T9 | **WALR by sector**, outstanding and new loans | Apr 2020 |

- **Lag:** the release at the end of month M carries WALR and deposit rates for M−1, and MCLR for M.
- **Revisions exist; snapshot saving is needed, latest release wins.**
  - The latest month moves 0.01–0.04 pp in the next release.
  - The Sep 2026 file revised five months of T4 public-sector-bank rates, by up to 0.06 pp.
  - T7 "Others" re-rounds by ±0.01 so each row sums to 100.
  - All four files say "Data are provisional".
- **Precision varies across releases** (2 decimals in one, 15 in the next), so revision diffs
  compare at 2 decimals. Across the four files there were 467 / 428 / 45 changed cells; 9 / 3 / 37
  of them were real revisions.
- **Dates are labels, not days.**
  - Month-start until Dec 2020, month-end after, with stray days (28 Mar 2023; 2–9 in T2 in 2024).
  - Some months are text: "July-2023" in T2 and T3, "Jan-2024" in T6.
  - T5's column headers mix dates with "May-2016" and "Sept-2016".
  - None of these are gaps.
- **No printed growth to check against** (the values are levels). The internal checks available
  are T7 rows summing to 100 and T6 min ≤ median ≤ max.
- **Notes to carry forward:**
  - "Data from July 2023 onwards include the impact of the merger of a non-bank with a bank"
    (the HDFC merger), in T1 and T3.
  - The SCB column is RBI's weighted aggregate. Its weights are not published, so the groups
    cannot rebuild it.
- **Join to SIBC sectors:**
  - Exact name match: Agriculture, Industry (Large), Infrastructure, Trade, Professional Services,
    Education, Vehicle, Housing, Other Personal Loans.
  - Judgment calls: "MSMEs" may include services MSMEs, where SIBC's Micro and Small + Medium is
    industry only; and "Rupee Export Credit" vs SIBC's Export Credit.

## Settled here, so not reopened

- **DBIE is not a SIBC history source** (user, 2026-10-10). The New Format table (Jan 2019–Jun 2026)
  matches SIBC except September (~1%); the Old Format covers a different bank set. SIBC history
  comes from release files the user provides.
- WALR is not on DBIE; it is only in release #1. Quarterly BSR-1 is not a DBIE time series; it is
  release #7.
- The two rbi.org.in releases (#1, #7) list PDF attachments; whether an Excel file comes with
  them is checked on the first download.
