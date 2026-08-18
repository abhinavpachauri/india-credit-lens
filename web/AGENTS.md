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

## Design Language System (DLS)

Shared components live in `web/components/dls/`. Both the SIBC and Payments pages use
these — any change here affects both.

### InsightCard (`dls/InsightCard.tsx`)
Renders a single insight / gap / opportunity card.

```tsx
<InsightCard
  type="insight"          // "insight" | "gap" | "opportunity" — drives colour + badge
  title="..."
  body="..."
  implication="..."       // optional — "For lenders" section
  chain={["Step 1", ...]} // optional — inference expand toggle
  activeIndex={0}
  total={3}
  onNext={...}
  onPrev={...}
/>
```

- `key={activeIndex}` on the **parent** resets internal `showChain` expand state on navigation
- Touch swipe: left → next, right → prev
- `TYPE_COLOR` export drives all type-specific colours across SIBC and Payments

### InsightCTAStrip (`dls/InsightCTAStrip.tsx`)
Entry / exit strip above a chart section.

- Entry mode: count summary + animated headline ticker + "tap to explore →" CTA
- Active mode: "← Exit insights · X of Y"
- Ticker cycles internally — callers do not manage ticker state

```tsx
<InsightCTAStrip
  items={flat.map(a => ({ type: a.type, title: a.title }))}
  counts={{ insight: 3, gap: 1, opportunity: 0 }}
  isActive={isActive}
  activeIdx={activeIdx}
  total={total}
  onEnter={enter}
  onExit={exit}
/>
```

---

## SIBC page pattern (`SectionWithAnnotations.tsx`)

Data source: `useSectionInsights(section)` hook — flattens insights / gaps / opportunities
into a single navigable list. Exposes `ins.flat`, `ins.current`, `ins.enter`, `ins.exit`,
`ins.next`, `ins.prev`, `ins.highlightConfig`.

Structural order (always) — mirrors payments exactly:
1. Section heading (icon + `text-sm font-bold` title)
2. `<InsightCTAStrip>` (if insights exist)
3. `<InsightCard key={ins.activeIdx}>` (if active)
4. Controls card (hidden in insights mode) — tab buttons + chart-mode radios + IndustryFilter
5. `<SectionCard accentColor={...} bare>` wrapping chart only

**No global TabBar.** Tab state (`trend` / `distribution`) and chart-mode state
(`trendMode`: absolute/yoy/fy · `distMode`: absolute/pct) are local to each section.
`TrendChart` and `DistributionChart` receive `mode` as a prop — they no longer own it.

Controls card (same style as payments):
- Tab buttons: 📈 Trend · 📊 Distribution
- Radios (right of divider): change based on active tab
  - Trend:        Absolute · YoY % · FY Cumul.
  - Distribution: ₹ Crore  · % Share
- IndustryFilter row: only for `section.filterable === true`

`SectionCard bare` skips the internal title header — heading is rendered above the card.

Inference chain: `chain={ins.current.basis?.inferences}` — sourced from `basis.inferences`
on the annotation. Check 2d (validate_annotation_basis.py) enforces this is non-empty.

---

## Payments page pattern (`AtmPosGroupSection.tsx`)

Data source: `atm_pos_insights.json` loaded via `loadAtmPosInsights()`, filtered by
`filterInsights(allInsights, group, mode)`.

Structural order (always):
1. Group heading (icon + `text-sm font-bold` sentence-case title — unified with SIBC)
2. `<InsightCTAStrip>` (if insights exist)
3. `<InsightCard key={activeIdx}>` (if active)
4. Controls panel (mode / tab / chart-mode / top-N / chips / bank selector)
5. Card grid — `<AtmPosSectionCard>` per section

Inference chain: `chain={activeInsight.reasoning?.chain}` — sourced from `reasoning.chain`
on the insight object. Stage 4d enforces this has ≥ 2 steps.

### AtmPosSectionCard (`AtmPosSectionCard.tsx`)
Uses `SectionCard bare` + `accentColor` from `GROUP_ACCENT[group]` in `atm_pos_data.ts`:

```
cc    → #4e8ef7  (blue)
dc    → #2ca02c  (green)
infra → #f0912a  (orange)
```

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
| `TYPE_COLOR` (from InsightCard) | Insight type badge + card border + ticker text |
| `SEC_COLORS[]` | SIBC section card left-border accents (index from `section.accentIndex`) |
| `GROUP_ACCENT` (from atm_pos_data.ts) | Payments group card left-border accents |

---

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
