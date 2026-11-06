// Bank slides for a carousel (DISTRIBUTION_SPEC §17): a table of named banks, and one chart of market
// share. Rendered from the stored sidecars: every number is a stored display string and every line a
// stored series, so nothing here formats a number.
import { readFileSync } from "node:fs";
import { join } from "node:path";

const DATA = new URL("../../../web/public/data/", import.meta.url).pathname;
const STEP_POINTS = 2;              // a one-month share move this big is circled on the chart (§17.5)

const minus = (s) => String(s).replace(/-/g, "−");
const json = (f) => JSON.parse(readFileSync(join(DATA, f), "utf8"));
const metric = (m) => json(`atm_pos_banks/${m}-banks.json`);

function bankRow(doc, entity) {
  const p = doc.parts.find((x) => x.entity === entity);
  if (!p) throw new Error(`${entity} is not in ${doc.cut}`);
  return p;
}

function totalRow(cut, category) {
  const p = json("atm_pos_table.json").cuts[cut].parts.find((x) => x.entity === category);
  if (!p) throw new Error(`${category} is not in ${cut}`);
  return p;
}

function cell(p, field) {
  if (field === "year_ago") return minus(p.growth.series_display.at(-13));
  return minus(p[field].display);
}

// The months where a bank's share moved by STEP_POINTS or more.
function steps(p) {
  const s = p.of_cut.series, out = [];
  for (let i = 1; i < s.length; i++)
    if (s[i] != null && s[i - 1] != null && Math.abs(s[i] - s[i - 1]) >= STEP_POINTS) out.push(i);
  return out;
}

export const SCORE_CSS = `
  .score { width:100%; border-collapse:collapse; margin-top:26px; background:var(--card); border:2px solid var(--border); }
  .score th { font-size:28px; font-weight:700; letter-spacing:.03em; color:var(--muted); text-align:right; padding:14px 16px 12px; border-bottom:3px solid var(--accent); text-transform:uppercase; white-space:nowrap; }
  .score th:first-child, .score td:first-child, .score .group { text-align:left; }
  .score td { font-size:36px; text-align:right; padding:12px 16px; border-bottom:1px solid var(--border); white-space:nowrap; font-variant-numeric:tabular-nums; }
  .score tr.total td { font-weight:800; background:color-mix(in srgb, var(--accent) 10%, var(--card)); }
  .score td.group { font-size:30px; color:var(--muted); font-weight:600; }
  .chart { margin-top:26px; background:var(--card); border:2px solid var(--border); border-radius:24px; padding:18px; }
  .chart text { font-family:Geist,sans-serif; }
`;

export function renderScorecard(s, set) {
  const docs = {};
  const doc = (m) => (docs[m] ??= metric(m));
  const banks = s.banks ? s.banks.map((n) => set.banks.find((b) => b.name === n)) : set.banks;
  const heads = s.columns.map((c) => `<th>${c.head}</th>`).join("") + (s.show_group ? `<th class="group">Story</th>` : "");
  const totalCells = s.columns.map((c) => `<td>${cell(totalRow(set.category_cuts[c.metric], set.category), c.field)}</td>`).join("");
  const text = [totalCells];
  const rows = banks.map((b) => {
    const cells = s.columns.map((c) => `<td>${cell(bankRow(doc(c.metric), b.entity), c.field)}</td>`).join("");
    text.push(cells);
    return `<tr><td>${b.name}</td>${cells}${s.show_group ? `<td class="group">${b.group}</td>` : ""}</tr>`;
  });
  const html = `<table class="score"><thead><tr><th>Bank</th>${heads}</tr></thead><tbody>
    <tr class="total"><td>${set.category_label}</td>${totalCells}${s.show_group ? "<td></td>" : ""}</tr>${rows.join("")}</tbody></table>`;
  return { html, text: text.join(" ").replace(/<[^>]+>/g, " ") };
}

export function renderTrend(s, set) {
  const d = metric(s.metric);
  const months = d.periods.of_cut;
  const W = 860, H = s.height ?? 620, L = 96, R = 290, T = 26, B = 56;
  const lines = s.lines.map(({ name, colour }) => ({ name, colour, p: bankRow(d, set.banks.find((x) => x.name === name).entity) }));
  const hi = s.axis_max;
  const n = months.length;
  const x = (i) => L + (i * (W - L - R)) / (n - 1);
  const y = (v) => T + ((hi - v) * (H - T - B)) / hi;      // the axis starts at zero: a share is a size
  const parts = [];
  for (let g = 0; g <= hi; g += 10)
    parts.push(`<line x1="${L}" x2="${W - R}" y1="${y(g)}" y2="${y(g)}" stroke="${g ? "#e8ddd0" : "#7a6a55"}" stroke-width="${g ? 1.5 : 2}"/><text x="${L - 14}" y="${y(g) + 10}" text-anchor="end" font-size="28" fill="#7a6a55">${g}%</text>`);
  parts.push(`<text x="${x(0)}" y="${H - 14}" font-size="28" fill="#7a6a55">${months[0]}</text><text x="${x(n - 1)}" y="${H - 14}" text-anchor="end" font-size="28" fill="#2c1e0f" font-weight="700">${months[n - 1]}</text>`);

  // End labels sit in a column, spread apart so close lines stay readable.
  const ends = lines.map((l) => ({ ...l, want: y(l.p.of_cut.series.at(-1)) })).sort((a, b) => a.want - b.want);
  for (let i = 1; i < ends.length; i++) ends[i].want = Math.max(ends[i].want, ends[i - 1].want + 40);
  const text = [];
  for (const l of ends) {
    const v = l.p.of_cut.series;
    const pts = v.map((u, i) => (u == null ? null : `${x(i).toFixed(1)},${y(u).toFixed(1)}`)).filter(Boolean).join(" ");
    parts.push(`<polyline points="${pts}" fill="none" stroke="${l.colour}" stroke-width="4" stroke-linejoin="round"/>`);
    for (const i of steps(l.p).filter(() => (s.circle ?? []).includes(l.name)))
      parts.push(`<circle cx="${x(i).toFixed(1)}" cy="${y(v[i]).toFixed(1)}" r="8" fill="#fffcf5" stroke="#e05c5c" stroke-width="3"/>`);
    parts.push(`<text x="${x(n - 1) + 14}" y="${l.want + 10}" font-size="29" font-weight="800" fill="${l.colour}">${l.name} ${minus(l.p.of_cut.display)}</text>`);
    text.push(l.p.of_cut.display, l.p.of_cut.series_display[0]);
  }
  const svg = `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="${s.alt}">${parts.join("")}</svg>`;
  return { html: `<div class="chart">${svg}</div>`, text: text.join(" ") };
}
