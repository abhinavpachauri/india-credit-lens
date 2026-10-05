<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

---

# India Credit Lens — Web Context

Next.js 16.2 App Router · React 19 · TypeScript · Tailwind CSS 4 · Recharts

---

## App Shell (shared across all pages)

`AppShell` (`web/components/AppShell.tsx`) is mounted once in `layout.tsx` and wraps every page.

It owns:
- **Dark mode state** (persisted in `localStorage` key `icl-dark`)
- **`<Header>`** — rendered once; never duplicated in page files
- The outermost `data-dark` / `bg-page` div

Pages opt in via `useAppShell()`:
```tsx
const { dark, setHeaderMetric } = useAppShell();
// Push page-specific data into the shared header:
setHeaderMetric(report.totalBankCredit, report.latestDate);
// Clear on pages that don't have a credit metric:
setHeaderMetric(null, "Mar 2026");
```

**Rule:** Never instantiate `<Header>` in a page file. Never manage dark mode in a page file.

---

## Read mode — the primary surface (all three dashboards)

Spec: `analysis/DASHBOARD_SPEC.md` §15–§20. `/` (SIBC) and `/payments` open in **Read**, with a
`ModeToggle` to **Explore** (charts with their controls, below). `/nbfc` has no Explore
mode.

| Piece | File | Role |
|---|---|---|
| Shell | `components/read/ReadModeShell.tsx` | pipeline-agnostic navigation: tiles → dimension → cell chart; each close pops **one** level; owns Esc |
| Primitives | `components/read/parts.tsx` | `DimensionCard`, `RailItem`, `StateBand`, `CutTable`, `CutRowList`, `CellPanel`, `ReadCard` |
| Adapters | `components/read/{Sibc,Atm,Nbfc}ReadMode.tsx` | one per pipeline: declare dimensions, map sidecars into the shell's model, render the chart |
| Data | `lib/table.ts`, `lib/state.ts`, `lib/planes.ts` | typed readers for the sidecars `{pipeline}_table.json`, `_state.json`, `_planes.json` |
| Deep view | `components/read/DeepReading.tsx` | **disabled** (`DEEP_ENABLED = false` in the shell) while Layer 1 is being got right |

Rules:
- **The browser never formats a number.** State-band sentences, table cells and cell readings
  arrive as rendered strings from Python; a component only places them.
- One `Pipeline` type (declared in `lib/opportunities.ts`), imported, never retyped as a union.
- A new pipeline = a manifest + an adapter that declares its dimensions (NBFC's is ~70 lines).
- Payments bank breakouts are fetched on open from `public/data/atm_pos_banks/*.json`.

---

## Explore mode — charts only (since 2026-10-05)

**Read is the authoritative surface for insights.** Explore shows each section's chart with the
controls Read lacks; it carries no insight cards (DASHBOARD_SPEC §18, DECISIONS). The step-through
pieces it used (`InsightCTAStrip`, `InsightCard`, `useSectionInsights`, `useAnnotation`,
`filterInsights`) were removed with it.

### SIBC (`SibcExploreSection.tsx`)

1. Section heading (icon + `text-sm font-bold` title)
2. Controls card: 📈 Trend · 📊 Distribution, then radios that change with the tab
   (Trend: Absolute · YoY % · FY Cumul.; Distribution: ₹ Crore · % Share), and `IndustryFilter`
   for `section.filterable === true`
3. `<SectionCard accentColor={...} bare>` wrapping the chart

Tab state and chart mode are local to each section; `TrendChart` / `DistributionChart` take `mode`
as a prop. Their `highlightConfig` / `preferredMode` props are used by Read's card charts.

### Payments (`AtmPosGroupSection.tsx`)

1. Group heading (icon + sentence-case title)
2. Controls panel: By Type · Individual · Top N, Trend / Distribution, chart-mode radios, top-N
   selector, series chips, bank search
3. Card grid: `<AtmPosSectionCard>` per section, accent from `GROUP_ACCENT[group]` in
   `atm_pos_data.ts` (cc `#4e8ef7`, dc `#2ca02c`, infra `#f0912a`)

`atm_pos_insights.json` (`loadAtmPosInsights`) is read by Read mode only.

---

## Card shell (`SectionCard.tsx`)

Single shared card shell used by both SIBC and Payments.

```tsx
<SectionCard accentColor="#4e8ef7" bare>
  {/* your content */}
</SectionCard>
```

- `bare=true` — omit the internal title header (used when heading is rendered externally)
- `accentColor` — drives `borderLeft: 4px solid` and the optional header tint

---

## Colour system (`lib/theme.ts`)

| Export | Used for |
|---|---|
| `pickColor(label, index)` | Chart series lines/bars — NAMED_COLORS first, D3_PALETTE fallback |
| `SEC_COLORS[]` | SIBC section card left-border accents (index from `section.accentIndex`) |
| `GROUP_ACCENT` (from atm_pos_data.ts) | Payments group card left-border accents |

---

## Information hierarchy (`TEXT` in `lib/tokens.ts`, DASHBOARD_SPEC §22)

Every Read surface uses five levels: `TEXT.title` (L1, one per screen) · `TEXT.section` (L2, with a
grey subline) · `TEXT.item` (L3) · `TEXT.lead` / `TEXT.body` · `TEXT.meta`. Order inside a section
is claim → evidence → reference; every chart uses the one frame (view label, `SectionCard`, legend
chips); captions are triaged (caveat visible, definitions on hover, notes folded). A test fails a
heading-sized `FS` step used directly in `components/read/`. Run the §22.6 checklist on any new
surface.

## Type and radius scale (`lib/tokens.ts`)

Sizes come from `FS` / `R` / `GLYPH`. Never write a raw number — `lib/tokens.test.ts` fails the
build on any literal `fontSize` or `borderRadius` outside that module, because the scale this one
replaced lived in `globals.css`, declared itself mandatory, had no consumers, and quietly grew to
fifteen font sizes (five of them half-points) and seven radii.

| Step | px | Role |
|---|---|---|
| `FS.micro` | 10 | Uppercase role labels, disclosure carets, tiny badges |
| `FS.meta` | 11 | Coverage lines, chart axis ticks, depth hints |
| `FS.label` | 12 | Uppercase group headers, chain markers, chart legends |
| `FS.note` | 13 | Card meta, chip labels, eyebrows, chart tooltips |
| `FS.body` | 14 | Body text, controls, breadcrumbs, rail rows |
| `FS.lead` | 15 | Read-card titles, chain steps |
| `FS.card` | 16 | Dimension titles, detail body, CTA strip |
| `FS.section` | 18 | Section headers (explore mode) |
| `FS.title` | 24 | The detail pane's title — one per screen |
| `R.sm` / `R.md` / `R.lg` | 4 / 8 / 12 | Badges / cards+chips / panels (`rounded-full` unchanged) |
| `GLYPH.arrow` / `GLYPH.dimension` | 20 / 24 | Chip-strip arrows, dimension emoji — sized beside text, not as text |

Reach for the **role**, not the pixel value. Adding a step is a design decision — make it in
`tokens.ts`, in the open, or not at all. `app/opengraph-image.tsx` is exempt: Satori renders it on
a 1200×630 canvas, a different medium with its own proportions.

---

## Mobile-first rules

All new components must be mobile-ready by default:
- No `truncate` on text that can wrap — use `line-clamp-2` via `-webkit-box` instead
- Min heights on animated containers so they don't collapse
- Touch swipe handlers on cards that support prev/next navigation
- Test at 375px viewport width before marking work done
