# SIBC Skeleton Profile
> Pipeline-specific structural profile for the SIBC system model.
> Consumed by the skeleton emission procedure in `analysis/SYSTEM_MODEL_SPEC.md` §6.
> This file is the ONLY place SIBC-specific structure lives. The spec stays generic.

**Pipeline:** `sibc`
**Source CSV:** `web/public/data/rbi_sibc_consolidated.csv`
**Structural nodes (latest period):** 86

---

## 1. Column → structural-role mapping

| Spec role | CSV column |
|-----------|-----------|
| `partition` | `statement` |
| `code` | `code` |
| `level` | `level` |
| `parent_ref` | `parent_code` (within same `statement`; see note) |
| `reclass_flag` | `is_priority_sector_memo` |

**Notes:**
- Identity key is `(statement, code)` — code strings collide across statements (e.g. `Statement 1` `2.1` = Micro & Small vs `Statement 2` `2.1` = Mining & Quarrying).
- `parent_code` resolves within the same `statement`, except the `parent_statement` column already records the parent's statement explicitly — use `(parent_statement, parent_code)` when present.
- Roots: `I` (Bank Credit), `II` (Food Credit), `III` (Non-food Credit) — all `Statement 1`, empty `parent_code`, `is_priority_sector_memo = False`.

---

## 2. Decomposition labels (cosmetic aliases of partition values)

| `statement` value | `decomposition` label |
|-------------------|----------------------|
| `Statement 1` | `by_size` (for Industry code `2` children); `primary` for all other parents |
| `Statement 2` | `by_type` (Industry code `2` children only) |

Only Industry (`2`) has alternate decompositions. All other parents have a single decomposition (`primary`).

---

## 3. Reclassification target map (authored)

PSL memo rows (`is_priority_sector_memo = True`, codes `i`–`x`) re-slice credit already counted in the primary tree, under different thresholds/definitions. The CSV does not store the target — it is authored here and is stable.

| PSL code | PSL sector | `reclassifies` → target `(statement, code)` | `basis` |
|----------|-----------|---------------------------------------------|---------|
| `i` | Agriculture | `(Statement 1, 1)` Agriculture | PSL agriculture uses eligibility caps; primary tree is all agriculture credit |
| `ii` | Micro & Small Enterprises | `(Statement 1, 2.1)` Micro & Small | PSL MSME uses turnover-based (June 2020) definition; Industry-by-size uses a different size basis — different populations |
| `iii` | Medium Enterprises | `(Statement 1, 2.2)` Medium | Same MSME definitional mismatch as `ii` |
| `iv` | Housing | `(Statement 1, 4.2)` Housing | PSL housing applies loan-ceiling thresholds (metro/non-metro); primary tree is all housing credit |
| `v` | Educational Loans | `(Statement 1, 4.6)` Education | PSL education applies an amount cap |
| `vi` | Renewable Energy | `(Statement 2, 2.18)` Infrastructure | PSL renewable maps to a subset of by-type infrastructure/power; not a clean 1:1 |
| `vii` | Social Infrastructure | `null` | PSL-native classification; no single primary-tree node |
| `viii` | Export Credit | `null` | PSL-native; export credit is not a separate primary-tree node |
| `ix` | Others | `null` | PSL-native residual |
| `x` | Weaker Sections (incl. net PSLC- SF/MF) | `null` | PSL-native cross-cutting classification |

All reclassification entities carry `additive: false`.

---

## 4. Artifact skip rules

- Skip rows with empty `code` (e.g. `Statement 2` header row "Industries (2.1 to 2.19)", `level = -1`).
- Use only the latest `report_date` for structural emission (the structure is stable across periods; values are not part of the skeleton).

---

## 5. Emitted tree (reference — 86 nodes)

```
Bank Credit (I) [root]
├── Food Credit (II) [root-level sibling; I = II + III]
└── Non-food Credit (III) [root-level sibling]
    ├── Agriculture (1)
    ├── Industry (2)  ── alternate decompositions ──
    │   ├── by_size (Statement 1):  2.1 Micro&Small · 2.2 Medium · 2.3 Large
    │   └── by_type (Statement 2):  2.1 Mining · 2.2 Food Processing (→2.2.1 Sugar, 2.2.2 Edible Oils, 2.2.3 Tea, 2.2.4 Others)
    │                               2.3 Beverage/Tobacco · 2.4 Textiles (→2.4.1 Cotton, 2.4.2 Jute, 2.4.3 Man-Made, 2.4.4 Other)
    │                               2.5 Leather · 2.6 Wood · 2.7 Paper · 2.8 Petroleum
    │                               2.9 Chemicals (→2.9.1 Fertiliser, 2.9.2 Drugs/Pharma, 2.9.3 Petro Chem, 2.9.4 Others)
    │                               2.10 Rubber/Plastics · 2.11 Glass · 2.12 Cement
    │                               2.13 Basic Metals (→2.13.1 Iron&Steel, 2.13.2 Other Metal)
    │                               2.14 All Engineering (→2.14.1 Electronics, 2.14.2 Others)
    │                               2.15 Vehicles · 2.16 Gems/Jewellery · 2.17 Construction
    │                               2.18 Infrastructure (→2.18.1 Power, .2 Telecom, .3 Roads, .4 Airports, .5 Ports, .6 Railways, .7 Other)
    │                               2.19 Other Industries
    ├── Services (3)
    │   ├── 3.1 Transport · 3.2 Computer Software · 3.3 Tourism · 3.4 Shipping · 3.5 Aviation
    │   ├── 3.6 Professional Services · 3.7 Trade (→3.7.1 Wholesale, 3.7.2 Retail) · 3.8 CRE
    │   ├── 3.9 NBFCs (→3.9.1 HFCs, 3.9.2 PFIs) · 3.10 Other Services
    └── Personal Loans (4)
        └── 4.1 Consumer Durables · 4.2 Housing · 4.3 FD Advances · 4.4 Share Advances
            4.5 Credit Cards · 4.6 Education · 4.7 Vehicle · 4.8 Gold · 4.9 Other

PSL reclassification lens (additive:false):
    i Agriculture · ii MSME · iii Medium · iv Housing · v Education
    vi Renewable · vii Social Infra · viii Export · ix Others · x Weaker Sections
```

---

## 6. L1 signal-coverage note

Many of these 86 structural nodes have **no L1 signal** in `registry.json` (e.g. most `Statement 2` level-3 leaves: Sugar, Tea, Jute Textiles, Airports, Railways, Fertiliser, etc.). The skeleton-vs-`registry.json` diff is the input to a future L1 signal-gap audit — it tells us which structural nodes we currently cannot measure.
