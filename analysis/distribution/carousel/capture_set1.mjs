// Capture the dashboard panels for the Set 1 carousel at phone width, 3x, light theme.
import { launch, shoot } from "./cdp.mjs";

const OUT = new URL(".", import.meta.url).pathname + "shots/";
const BASE = "http://localhost:3000";

// Runs in the page: open a tile, find a notable card by title, return the clip to capture.
const IN_PAGE = String.raw`
window.__icl = {
  sleep: (ms) => new Promise(r => setTimeout(r, ms)),
  hideChrome() {
    const s = document.createElement('style');
    s.textContent = 'nextjs-portal{display:none!important}';
    document.head.appendChild(s);
    // the sticky site header would overlay any card scrolled under it
    for (const e of document.querySelectorAll('*')) {
      const p = getComputedStyle(e).position;
      if (p === 'sticky' || p === 'fixed') e.style.visibility = 'hidden';
    }
  },
  async openTile(label) {
    for (let i = 0; i < 40; i++) {
      const tile = [...document.querySelectorAll('*')].find(e => e.childElementCount < 3 && e.textContent.trim() === label);
      if (tile) { tile.click(); await this.sleep(1200); return; }
      await this.sleep(250);
    }
    throw new Error('tile not found: ' + label);
  },
  clip(el, bottomEl, pad = 0) {
    const r = el.getBoundingClientRect();
    const b = bottomEl ? bottomEl.getBoundingClientRect().bottom + pad : r.bottom;
    return { x: r.left + scrollX, y: r.top + scrollY, width: r.width, height: b - r.top };
  },
  reveal(titlePrefix) {
    const t = [...document.querySelectorAll('span')].filter(e => e.textContent.trim().startsWith(titlePrefix)).pop();
    t.parentElement.parentElement.scrollIntoView({ block: 'center' });
  },
  card(titlePrefix) {
    const t = [...document.querySelectorAll('span')].filter(e => e.textContent.trim().startsWith(titlePrefix)).pop();
    if (!t) throw new Error('card not found: ' + titlePrefix);
    const card = t.parentElement.parentElement;
    // Crop just below the chart: the largest svg inside the card.
    const svgs = [...card.querySelectorAll('svg')].sort((a, b) => b.getBoundingClientRect().height - a.getBoundingClientRect().height);
    // The inner chart frame (bordered box holding legend + plot): the slide headline replaces the card title.
    let frame = svgs[0].parentElement;
    while (frame && frame !== card && !(parseFloat(getComputedStyle(frame).borderTopWidth) > 0 && parseFloat(getComputedStyle(frame).borderRadius) > 0)) frame = frame.parentElement;
    return this.clip(frame && frame !== card ? frame : card, svgs[0], 22);
  },
};`;

const page = await launch();
const { send, evaluate } = page;
await send("Page.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 420, height: 3000, deviceScaleFactor: 3, mobile: true });
await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "light" }] });

async function go(path) {
  await send("Page.navigate", { url: BASE + path });
  await page.sleep(3500);
  await evaluate(IN_PAGE);
  await evaluate("__icl.hideChrome()");
}

const shots = [
  { file: "2_size_growth.png", path: "/", tile: "Industry by Size", card: "Medium growing fastest" },
  { file: "4_card_growth.png", path: "/payments", tile: "Credit Card", card: "Credit card YoY growth hits" },
];
for (const s of shots) {
  await go(s.path);
  await evaluate(`__icl.openTile(${JSON.stringify(s.tile)})`);
  await evaluate(`__icl.reveal(${JSON.stringify(s.card)})`);
  await page.sleep(5000); // charts mount on scroll and animate in
  await evaluate("__icl.hideChrome()");
  // Freeze line charts in their fully drawn state (Recharts draws them in with a dash animation).
  await evaluate(`(() => { const st = document.createElement('style');
    st.textContent = '.recharts-curve{stroke-dasharray:none!important}'; document.head.appendChild(st); })()`);
  await page.sleep(400);
  const rect = await evaluate(`__icl.card(${JSON.stringify(s.card)})`);
  await shoot(page, rect, OUT + s.file);
  console.log(s.file, JSON.stringify(rect));
}

// A table cut down to the columns and rows the slide talks about, one row highlighted.
// Presentation only: the numbers are the dashboard's, untouched.
async function table(file, tile, cols, rows, highlight, tint) {
  await go("/");
  await evaluate(`__icl.openTile(${JSON.stringify(tile)})`);
  const rect = await evaluate(`((cols, rows, highlight, tint) => {
    const table = [...document.querySelectorAll('table')][0];
    const heads = [...table.querySelectorAll('thead th')].map(th => th.childNodes[0].textContent.trim().toUpperCase());
    const keep = heads.map(h => cols.some(c => h.startsWith(c)));
    for (const tr of table.querySelectorAll('tr'))
      [...tr.children].forEach((c, i) => { if (!keep[i]) c.style.display = 'none'; });
    for (const tr of table.querySelectorAll('tbody tr')) {
      const name = tr.children[0].textContent.replace(/[▸▾\\s]+/g, ' ').trim();
      if (!rows.includes(name)) tr.style.display = 'none';
      if (name === highlight) [...tr.children].forEach(c => { c.style.background = tint; c.style.fontWeight = '700'; });
    }
    let w = table.parentElement; while (w && getComputedStyle(w).overflowX === 'visible') w = w.parentElement;
    if (w) w.style.overflowX = 'visible';
    table.style.width = '340px'; table.style.minWidth = '0'; table.querySelectorAll('td,th').forEach(c => { c.style.whiteSpace = 'normal'; });
    table.scrollIntoView({ block: 'center' });
    return __icl.clip(table);
  })(${JSON.stringify(cols)}, ${JSON.stringify(rows)}, ${JSON.stringify(highlight)}, ${JSON.stringify(tint)})`);
  await page.sleep(500);
  await evaluate("__icl.hideChrome()");
  await shoot(page, rect, OUT + file);
  console.log(file, JSON.stringify(rect), );
}

if (process.env.ONLY_CHARTS) { page.close(); process.exit(0); }
await table("1_size_table.png", "Industry by Size", ["PART", "OF CUT", "GROWTH"],
  ["Industry", "Large", "Micro and Small", "Medium"], "Large", "#e3f2df");
await table("3_services_table.png", "Services", ["PART", "GROWTH", "NEW"],
  ["Services", "Non-Banking Financial Companies (NBFCs)", "Trade", "Other Services"],
  "Non-Banking Financial Companies (NBFCs)", "#efe6fa");
page.close();
