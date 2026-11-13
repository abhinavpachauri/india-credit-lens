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

## Other finance: probed 2026-10-26 (four tables, read in the browser pane)

The grid's "other finance" kind applies on 52 SIBC lines (industry, infrastructure, NBFCs/HFCs/PFIs,
CRE, shipping, aviation). What each candidate actually holds:

| Table | Holds | By sector? | Range | Verdict |
|---|---|---|---|---|
| **ECB registrations** (Bulletin 38) | number and amount (US$ mn), maturity, margin; monthly | **Yes**: agriculture, manufacturing, infrastructure (transport, energy, water, communication, social & commercial, mining & refinery, other), construction, services, financial (banks, **NBFCs** by type, FIs, MFIs), others | "Monthly (New Format)" 2019-20 → 2025-26; "Monthly (Revised Format)" Apr 2024 → Aug 2026 (adds agriculture and construction); an older format before | **Use.** The only line-level other-finance series: covers the credit history from Oct 2021 once the two formats are joined on their overlap (2024-25 onwards). Registrations are intentions, lumpy by deal: needs a trailing sum |
| **Commercial paper** (Bulletin 29) | outstanding, issued in the fortnight, min/max rate; fortnightly | **No**, totals only | Jun 2011 → Oct 2026 | System level only (large industry, NBFCs as a whole) |
| **Flow of resources to the commercial sector** (Bulletin 18(a)) | non-food bank credit beside equity, bonds, REITs/InvITs, CP, HFC and NBFC credit (net of bank borrowing), AIFIs, ECB, ADR/GDR, short-term foreign credit, FDI | **No**, by instrument | 2023-24 → Mar 2026; **financial-year-to-date cumulative**, rows Oct–Mar only, some components quarterly (repeated three months) | **Context, not a test series**: the best picture of where firms raise money, too patchy for monthly tests |
| **New capital issues** (Bulletin 31) | equity (public, rights) and **public** bond issues; number and amount | **No** | 1990 → Aug 2026 | Skip: private placements, the bulk of corporate bonds, are not in it |

Access: DBIE cannot be scripted; each table opens in the SAP BusinessObjects viewer, which exports
to Excel (the user downloads, as for SIBC). Corporate bond issuance by sector is not on DBIE (SEBI).

### ECB borrower lists: probed 2026-11-13 (go/no-go before building)

**The better ECB source is not DBIE but RBI's monthly borrower list**
(`www.rbi.org.in/Scripts/ECBView.aspx`, one XLSX + PDF per month, 2017 → Sep 2026 plus archives,
~25-28 KB each). Every row is one registration: borrower, **economic sector in NIC wording**, amount
(US$), **purpose** (working capital, on-lending, refinancing of rupee loans…), maturity, lender
category. Layout is stable over Oct 2025 – Sep 2026 (sheet `ECB-FCCB`, a title row naming the month,
sections "General Permission"/"Automatic route" and "Approval"); sector labels vary in punctuation
(83 raw labels), so a reader needs a label map that fails loud on a new one.

*Access:* the listing page answers a script; the file host (`rbidocs`) drops scripted connections
(curl exit 56, urllib `RemoteDisconnected`). Not worked around (source_fetch: never present as a
browser). The editor's Chrome downloads them; 12 files took one batch.

*What the 12 months hold:* 1,585 registrations, **US$ 61.9 bn** (US$ 2.2 bn Oct 2025 → 7-8 bn a month
Jul–Sep 2026). Financial services US$ 25.9 bn (42%: NBFCs and PFIs, e.g. Muthoot US$ 600 mn, REC, HUDCO),
power US$ 9.3 bn, refining 2.9, air transport 2.8. **Refinancing of rupee loans** (the direct
bank-to-ECB substitution) is US$ 5.4 bn in 56 deals, mostly financial services (2.8) and power (1.4).

*The check (rule declared before matching):* last year's 58 unexplained SIBC moves, 37 on lines where
firms can borrow abroad (hand map SIBC line → NIC sectors, PFIs by borrower name; probe only). A
falling move "matches" when that sector's ECB in the move month or the one before is ≥ 3× its
monthly median and ≥ 25% of the ₹ shift the move implies (gap change × the line a year earlier; ₹88
per US$ assumed). Rises are not tested (substitution predicts falls).
- **3 of 16 falling moves match (19%); the same rule on every other month matches 25%.** As a
  monthly timing driver, ECB is **not better than chance** on this year.
- One match carries the mechanism itself: **Shipping −20.2 pts (Sep 2026) beside The Shipping
  Corporation of India, US$ 100.4 mn, "Refinancing of Rupee Loans"** (₹884 cr against ~₹1,929 cr
  implied). Shipping Jun 2026 (Avana Logistek US$ 80 mn) and Computer Software Jan 2026 (Microsoft
  India US$ 727 mn, working capital) match on timing only.

*Verdict (user, 2026-11-13: "use as evidence"; built the same day as `core/ecb_evidence.py`, sector
map `ontology/evidence/sibc__rbi_ecb.json`, saved months `sources/ecb/raw/`, step 3b of the
`s4-source` skill):* **do not build ECB as a driver series now.** Use the borrower
list as **evidence for a sourced cause**: when a line has a large unexplained fall, a refinancing
deal in its sector that month is an official, verbatim row (`rbi.org.in`), the S4 kind of source.
Revisit as a driver with more history (the files go back to 2017). Commercial paper stays context.
Probe scripts and the 12 files are scratch, not committed.

 (onboarding paused)

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
