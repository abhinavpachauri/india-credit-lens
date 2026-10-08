// Capture the dashboard tables for the Set 2 carousel at phone width, 3x, light theme.
// Each table is cut down to the columns and rows the slide talks about, one row highlighted.
// Presentation only: every number is the dashboard's own.
import { launch, shoot } from "./cdp.mjs";

const OUT = new URL(".", import.meta.url).pathname + "shots/";
const BASE = "http://localhost:3000";
const page = await launch(9396);
const { send, evaluate } = page;
await send("Page.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 420, height: 3000, deviceScaleFactor: 3, mobile: true });
await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "light" }] });

const click = (label) => evaluate(`(async () => {
  for (let i = 0; i < 40; i++) {
    const t = [...document.querySelectorAll('*')].find(e => e.childElementCount < 3 && e.textContent.trim() === ${JSON.stringify(label)});
    if (t) { t.click(); await new Promise(r => setTimeout(r, 1500)); return; }
    await new Promise(r => setTimeout(r, 250));
  }
  throw new Error('not found: ' + ${JSON.stringify(label)});
})()`);

async function capture({ file, path, clicks, cols, rows, highlight, tint, width = 340, total = true, expand = null, tableIndex = 0 }) {
  await send("Page.navigate", { url: BASE + path });
  await page.sleep(3500);
  for (const c of clicks) await click(c);
  if (expand) await evaluate(`(async () => {
    const tr = [...document.querySelectorAll('table')[0].querySelectorAll('tbody tr')].find(tr => tr.children[0].textContent.includes(${JSON.stringify(expand)}));
    (tr.querySelector('button') || tr.children[0]).click(); await new Promise(r => setTimeout(r, 1500)); })()`);
  const rect = await evaluate(`((cols, rows, highlight, tint, width, total, tableIndex) => {
    for (const e of document.querySelectorAll('*')) {
      if (e.closest('table')) continue;                        // sticky first columns stay
      const p = getComputedStyle(e).position;
      if (p === 'sticky' || p === 'fixed') e.style.visibility = 'hidden';
    }
    document.querySelectorAll('nextjs-portal').forEach(e => e.style.display = 'none');
    const table = document.querySelectorAll('table')[tableIndex];
    // Header rows can carry a spanning group heading ("vs the real economy") above the leaf
    // headings. Body cells line up with the leaf headings (colSpan 1), so map by index;
    // group headings are always hidden. Only this table's own rows, never a nested table's.
    const label = th => (th.childNodes[0]?.textContent ?? '').trim().toUpperCase();
    const headRows = [...table.querySelectorAll(':scope > thead > tr')];
    const leaf = [...headRows.at(-1).children];                 // the last header row holds the leaf headings
    const keep = leaf.map(th => cols.some(c => label(th).startsWith(c)));
    headRows.slice(0, -1).forEach(tr => tr.style.display = 'none');   // group-heading rows above it
    leaf.forEach((th, i) => { if (!keep[i]) th.style.display = 'none'; });
    for (const tr of table.querySelectorAll(':scope > tbody > tr'))
      [...tr.children].forEach((c, i) => { if (!keep[i]) c.style.display = 'none'; });
    const body = [...table.querySelectorAll(':scope > tbody > tr')];
    const found = [];
    body.forEach((tr, i) => {
      const name = tr.children[0].textContent.replace(/[▸▾\\s]+/g, ' ').trim();
      const wanted = (i === 0 && total) || rows.some(r => name.startsWith(r));   // the first row is the table's own total
      if (!wanted) tr.style.display = 'none'; else found.push(name);
      if (highlight && name.startsWith(highlight)) [...tr.children].forEach(c => { c.style.background = tint; c.style.fontWeight = '700'; });
    });
    let w = table.parentElement; while (w && getComputedStyle(w).overflowX === 'visible') w = w.parentElement;
    if (w) w.style.overflowX = 'visible';
    table.style.width = width + 'px'; table.style.minWidth = '0';
    table.querySelectorAll('td,th').forEach(c => { c.style.whiteSpace = 'normal'; });
    table.scrollIntoView({ block: 'center' });
    const r = table.getBoundingClientRect();
    return { x: r.left + scrollX, y: r.top + scrollY, width: r.width, height: r.height, found };
  })(${JSON.stringify(cols)}, ${JSON.stringify(rows)}, ${JSON.stringify(highlight)}, ${JSON.stringify(tint)}, ${width}, ${total}, ${tableIndex})`);
  await page.sleep(500);
  await shoot(page, rect, OUT + file);
  console.log(file, Math.round(rect.width) + "x" + Math.round(rect.height), rect.found.join(" / "));
}

const RED = "#fbe3e1";
await capture({
  file: "1_petroleum.png", path: "/", clicks: ["Industry by Type"],
  cols: ["PART", "GROWTH", "REAL CREDIT", "OUTPUT"], rows: ["Petroleum, Coal"], highlight: "Petroleum, Coal",
  tint: RED, total: false, width: 380,
});
await capture({
  file: "2_gems.png", path: "/", clicks: ["Industry by Type"],
  cols: ["PART", "GROWTH", "REAL CREDIT"], rows: ["Gems and Jewellery"], highlight: "Gems and Jewellery",
  tint: RED, total: false, width: 340,
});
await capture({
  file: "3_power.png", path: "/", clicks: ["Industry by Type"], expand: "Infrastructure", tableIndex: 1,
  cols: ["PART", "GROWTH", "REAL CREDIT", "OUTPUT"], rows: ["Power"], highlight: "Power",
  tint: RED, total: false, width: 320,
});
await capture({
  file: "4_main_real.png", path: "/", clicks: ["Main Sectors"],
  cols: ["PART", "REAL CREDIT", "OUTPUT"], rows: ["Services", "Industry", "Agriculture"], highlight: null,
  tint: "", total: false, width: 360,
});
await capture({
  file: "5_card_debt.png", path: "/", clicks: ["Personal Loans"],
  cols: ["PART", "GROWTH", "REAL CREDIT"], rows: ["Credit Card Outstanding"], highlight: "Credit Card Outstanding",
  tint: "#fdecd9", total: false, width: 360,
});
page.close();
