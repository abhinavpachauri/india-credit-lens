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
| 8 | Bank-wise variables (public access) | Statistics › Performance Indicators | quarterly · Mar 2002 | Per-bank analytics (STRATEGY future bet) | Wide, per bank |
| 9 | SCB select aggregates (deposits, credit, investments, CD ratio) | Statistics › Assets & Liabilities | fortnightly · 1997 | The funding side: deposit growth vs credit growth | Small |
| 10 | Household financial assets and liabilities | Bulletin 52A, 52B | quarterly · Jun 2018 | Household borrowing from banks, NBFCs, HFCs together | Small |
| 11 | Quarterly BSR-2 (deposits) | rbi.org.in, SectionID 382 | quarterly | Deposit mix by type and region | Medium |

Tier 3 is context, taken when a test needs it: PLFS monthly unemployment and wages (MoSPI API,
household income → retail credit); ASUSE quarterly (informal enterprises → MSME); Survey of
Professional Forecasters; NPAs and CRAR (annual); MSP and PDS procurement (annual); Industry-wise
deployment from 2007 (Bulletin 16 / Handbook 169; a different bank set before 2019, so not SIBC history).

## Settled here, so not reopened

- **DBIE is not a SIBC history source** (user, 2026-10-10). The New Format table (Jan 2019–Jun 2026)
  matches SIBC except September (~1%); the Old Format covers a different bank set. SIBC history
  comes from release files the user provides.
- WALR is not on DBIE; it is only in release #1. Quarterly BSR-1 is not a DBIE time series; it is
  release #7.
- The two rbi.org.in releases (#1, #7) list PDF attachments; whether an Excel file comes with
  them is checked on the first download.
