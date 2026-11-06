// Bank scorecard slides (DISTRIBUTION_SPEC §17): a table of named banks with a trend on each row,
// and a full chart of market share. Rendered from the stored sidecars: every number is a stored
// display string and every line a stored series, so the browser formats nothing.
import { readFileSync } from "node:fs";
import { join } from "node:path";

const DATA = new URL("../../../web/public/data/", import.meta.url).pathname;
const STEP_POINTS = 2;              // a one-month share move this big is marked (§17.5)

const minus = (s) => String(s).replace(/-/g, "−");
const json = (f) => JSON.parse(readFileSync(join(DATA, f), "utf8"));
const metric = (m) => json(`atm_pos_banks/${m}-banks.json`);

function bankRow(doc, entity) {
  const p = doc.parts.find((x) => x.entity === entity);
  if (!p) throw new Error(`${entity} is not in ${doc.cut}`);
  return p;
}

// The category's own row, for comparison. It has only growth-window history, so it carries no trend.
function totalRow(cut, category) {
  const p = json("atm_pos_table.json").cuts[cut].parts.find((x) => x.entity === category);
  if (!p) throw new Error(`${category} is not in ${cut}`);
  return p;
}

function cell(p, field) {
  if (field === "change") {
    const g = p.growth.series_display;
    return `${minus(g.at(-2))} → ${minus(g.at(-1))}`;
  }
  return minus(p[field].display);
}

// The months where a bank's share moved by STEP_POINTS or more.
function steps(p, months) {
  const s = p.of_cut.series, out = [];
  for (let i = 1; i < s.length; i++)
    if (s[i] != null && s[i - 1] != null && Math.abs(s[i] - s[i - 1]) >= STEP_POINTS) out.push({ i, month: months[i] });
  return out;
}

function sparkline(p, marks, w = 165, h = 44) {
  const s = p.of_cut.series;
  const known = s.filter((v) => v != null);
  const lo = Math.min(...known), hi = Math.max(...known), span = hi - lo || 1;
  const x = (i) => 6 + (i * (w - 12)) / (s.length - 1);
  const y = (v) => 5 + ((hi - v) * (h - 10)) / span;
  const pts = s.map((v, i) => (v == null ? null : `${x(i).toFixed(1)},${y(v).toFixed(1)}`)).filter(Boolean).join(" ");
  const last = s.length - 1;
  const dots = marks.map((m) => `<circle cx="${x(m.i).toFixed(1)}" cy="${y(s[m.i]).toFixed(1)}" r="5.5" fill="#fffcf5" stroke="#e05c5c" stroke-width="3"/>`).join("");
  return `<svg viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" aria-hidden="true"><polyline points="${pts}" fill="none" stroke="#2c1e0f" stroke-width="3" stroke-linejoin="round"/>${dots}<circle cx="${x(last).toFixed(1)}" cy="${y(s[last]).toFixed(1)}" r="5" fill="#2c1e0f"/></svg>`;
}

const SCORE_CSS = `
  .score { width:100%; border-collapse:collapse; margin-top:26px; background:var(--card); border:2px solid var(--border); }
  .score th { font-size:26px; font-weight:700; letter-spacing:.03em; color:var(--muted); text-align:right; padding:14px 14px 12px; border-bottom:3px solid var(--accent); text-transform:uppercase; white-space:nowrap; }
  .score th:first-child, .score td:first-child { text-align:left; }
  .score td { font-size:31px; text-align:right; padding:9px 12px; border-bottom:1px solid var(--border); white-space:nowrap; font-variant-numeric:tabular-nums; }
  .score tr.total td { font-weight:800; background:color-mix(in srgb, var(--accent) 10%, var(--card)); }
  .score tr.hi td { font-weight:800; background:#fde8c8; }
  .score .tr { display:flex; align-items:center; justify-content:flex-end; gap:10px; }
  .score .first { font-size:26px; color:var(--muted); font-weight:500; }
  .flag { font-size:28px; color:var(--muted); margin-top:16px; line-height:1.3; }
  .flag i { display:inline-block; width:18px; height:18px; border-radius:50%; border:3px solid #e05c5c; margin-right:8px; vertical-align:-1px; }
  .chart { margin-top:26px; background:var(--card); border:2px solid var(--border); border-radius:24px; padding:18px; }
  .chart text { font-family:Geist,sans-serif; }
`;
export { SCORE_CSS };

export function renderScorecard(s, set) {
  const docs = {};
  const doc = (m) => (docs[m] ??= metric(m));
  const banks = s.banks ? set.banks.filter((b) => s.banks.includes(b.name)) : set.banks;
  const heads = s.columns.map((c) => `<th>${c.head}</th>`).join("") + (s.trend ? `<th>${s.trend_head ?? "Share trend"}</th>` : "");

  const totalCells = s.columns.map((c) => `<td>${cell(totalRow(set.category_cuts[c.metric], set.category), c.field)}</td>`).join("");
  const text = [totalCells];
  const flags = [];
  const rows = banks.map((b) => {
    const cells = s.columns.map((c) => `<td>${cell(bankRow(doc(c.metric), b.entity), c.field)}</td>`).join("");
    text.push(cells);
    let trend = "";
    if (s.trend) {
      const d = doc(s.trend), p = bankRow(d, b.entity);
      const marks = steps(p, d.periods.of_cut);
      if (marks.length) flags.push(`${b.name} ${marks.map((m) => m.month).join(", ")}`);
      trend = `<td><div class="tr"><span class="first">${minus(p.of_cut.series_display[0])}</span>${sparkline(p, marks)}</div></td>`;
      text.push(p.of_cut.series_display[0]);
    }
    return `<tr class="${s.highlight === b.name ? "hi" : ""}"><td>${b.name}</td>${cells}${trend}</tr>`;
  });

  const flag = s.trend && flags.length
    ? `<p class="flag"><i></i>A one-month share jump of ${STEP_POINTS}+ points: ${flags.join("; ")}.</p>`
    : (s.note ? `<p class="flag">${s.note}</p>` : "");
  const html = `<table class="score"><thead><tr><th>Bank</th>${heads}</tr></thead><tbody>
    <tr class="total"><td>${set.category_label}</td>${totalCells}${s.trend ? "<td></td>" : ""}</tr>${rows.join("")}</tbody></table>${flag}`;
  return { html, text: text.join(" ").replace(/<[^>]+>/g, " ") };
}

export function renderTrend(s, set) {
  const d = metric(s.metric);
  const months = d.periods.of_cut;
  const W = 860, H = 620, L = 96, R = 290, T = 26, B = 56;
  const lines = s.lines.map(({ name, colour }) => {
    const b = set.banks.find((x) => x.name === name);
    return { name, colour, p: bankRow(d, b.entity) };
  });
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
    const s0 = l.p.of_cut.series;
    const pts = s0.map((v, i) => (v == null ? null : `${x(i).toFixed(1)},${y(v).toFixed(1)}`)).filter(Boolean).join(" ");
    parts.push(`<polyline points="${pts}" fill="none" stroke="${l.colour}" stroke-width="4" stroke-linejoin="round"/>`);
    for (const m of steps(l.p, months))
      parts.push(`<circle cx="${x(m.i).toFixed(1)}" cy="${y(s0[m.i]).toFixed(1)}" r="8" fill="#fffcf5" stroke="#e05c5c" stroke-width="3"/>`);
    parts.push(`<text x="${x(n - 1) + 14}" y="${l.want + 10}" font-size="29" font-weight="800" fill="${l.colour}">${l.name} ${minus(l.p.of_cut.display)}</text>`);
    text.push(l.p.of_cut.display, l.p.of_cut.series_display[0]);
  }
  const svg = `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="${s.alt}">${parts.join("")}</svg>`;
  const html = `<div class="chart">${svg}</div>`;
  return { html, text: text.join(" ") };
}
