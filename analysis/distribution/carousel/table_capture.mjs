// One table cut from the dashboard, and the check that a text's numbers are on it. Shared by the X
// posts (x/build_posts.mjs) and the LinkedIn carousels (build_set.mjs), so both hold to one rule.
import { shoot } from "./cdp.mjs";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const ROOT = new URL("../../../", import.meta.url).pathname;

// ── stored notes (e.g. the deflator a real-credit cell was net of) come from the sidecars ──
// `index` reads a past reading from `series_display` (−1 = latest, −13 = a year earlier on a
// monthly series), so a post can quote "a year ago" from the store, never from memory.
export function storedNote({ sidecar, cut, entity, column, field = "note", index }) {
  const t = JSON.parse(readFileSync(join(ROOT, "web/public/data", sidecar), "utf8"));
  const c = cut ? t.cuts[cut] : t;
  const p = entity === null ? c.total : c.parts.find((x) => x.entity === entity);
  const cell = p?.[column];
  const v = index === undefined ? cell?.[field] : cell?.series_display?.at(index);
  if (!v) throw new Error(`no stored ${field} for ${sidecar} › ${cut} › ${entity} › ${column}`);
  return v;
}

// ── the check: every number in a text is on what the reader is shown ──
const NUM = /[−-]?\d+(?:,\d{2,3})*(?:\.\d+)?/g;
export function untraced(text, shown) {
  const hay = shown.replace(/−/g, "-");
  return [...new Set((text.replace(/\b(?:https?:\/\/)?indiacreditlens\.com\S*/g, "").match(NUM) || []))]
    .map((n) => n.replace(/−/g, "-"))
    .filter((n) => !/^20\d\d$/.test(n))             // years are dates, not readings
    .filter((n) => !hay.includes(n.replace(/^-/, "")));
}

// ── capture one table, cut to the wanted rows and columns ──
export async function captureTable(page, spec, file, base) {
  const { send, evaluate } = page;
  await send("Page.navigate", { url: base + spec.path });
  await page.sleep(5000);
  for (const label of spec.clicks) {
    await evaluate(`(async () => {
      for (let i = 0; i < 40; i++) {
        const want = ${JSON.stringify(label)};
        let t = [...document.querySelectorAll('*')].find(e => e.childElementCount < 3 && e.textContent.trim() === want);
        // The innermost match: a row's cell and its expand button read the same, and only the button expands.
        for (let inner = t; inner; inner = [...inner.children].find(c => c.textContent.trim() === want)) t = inner;
        if (t) { t.click(); await new Promise(r => setTimeout(r, 1800)); return; }
        await new Promise(r => setTimeout(r, 250));
      }
      throw new Error('not found: ' + ${JSON.stringify(label)});
    })()`);
  }
  // `table_index`: an expanded row nests its sub-table inside the parent's (1 = that inner table).
  const r = await evaluate(`((cols, rows, highlight, total, width, nameWidth, tableIndex) => {
    for (const e of document.querySelectorAll('*')) {
      if (e.closest('table')) continue;
      const p = getComputedStyle(e).position;
      if (p === 'sticky' || p === 'fixed') e.style.visibility = 'hidden';
    }
    document.querySelectorAll('nextjs-portal').forEach(e => e.style.display = 'none');
    // The sticky first column draws its edge (shadow / pseudo-element) at its original offset;
    // once columns are hidden that edge cuts through the wrong column. Flatten it.
    const st = document.createElement('style');
    st.textContent = 'table td, table th { position: static !important; box-shadow: none !important; } table td::before, table td::after, table th::before, table th::after { display: none !important; }';
    document.head.appendChild(st);
    const table = document.querySelectorAll('table')[tableIndex];
    if (!table) throw new Error('no table ' + tableIndex + ' on the page');
    [...table.querySelectorAll('*')].filter(e => !e.childElementCount && e.textContent.trim() === 'ⓘ').forEach(e => e.style.display = 'none');
    const label = th => (th.childNodes[0]?.textContent ?? '').trim().toUpperCase();
    const heads = [...table.querySelectorAll('thead th')];
    const missing = cols.filter(c => !heads.some(th => label(th).startsWith(c)));
    if (missing.length) throw new Error('columns not on the table: ' + missing.join(', '));
    const wanted = heads.filter(th => cols.some(c => label(th).startsWith(c))).map(th => th.getBoundingClientRect());
    const hide = [...table.querySelectorAll('th, td')].filter(c => { const b = c.getBoundingClientRect(); const cx = (b.left + b.right) / 2;
      return !wanted.some(h => h.left <= cx && cx <= h.right); });
    hide.forEach(c => c.style.display = 'none');
    const found = [];
    // tBodies, not 'tbody tr': inside a nested table that selector also matches through the parent's tbody.
    [...table.tBodies[0].rows].forEach((tr, i) => {
      const name = tr.children[0].textContent.replace(/[▸▾ⓘ\\s]+/g, ' ').trim();
      const keep = (i === 0 && total) || rows.includes(name);
      if (!keep) tr.style.display = 'none'; else found.push(name);
      // Every cell gets a solid fill: something behind the table draws a column edge at its
      // pre-hiding offset, and only an opaque cell hides it (the highlighted rows already did).
      [...tr.children].forEach(c => { c.style.background = name === highlight ? '#fde8c8' : '#fffcf6'; });
      if (name === highlight) [...tr.children].forEach(c => { c.style.fontWeight = '700'; });
    });
    const lost = rows.filter(x => !found.includes(x));
    if (lost.length) throw new Error('rows not on the table: ' + lost.join(' | '));
    // Every ancestor: a nested table sits inside two scrollers, and either would clip it.
    for (let w = table.parentElement; w; w = w.parentElement) if (getComputedStyle(w).overflowX !== 'visible') w.style.overflowX = 'visible';
    // For X the canvas is wide and short, so rows must be short: no wrapping, tight padding.
    // The table grows sideways instead (width = what the cells need).
    table.style.width = 'auto'; table.style.minWidth = '0';
    table.querySelectorAll('td,th').forEach(c => { c.style.whiteSpace = 'nowrap'; c.style.paddingTop = '5px'; c.style.paddingBottom = '5px'; c.style.paddingLeft = '12px'; c.style.paddingRight = '12px'; });
    // A group heading row ('vs the real economy') spans columns that may now be hidden, so it no
    // longer sits over its columns: drop every heading row but the last.
    const headRows = [...table.querySelectorAll('thead tr')];
    headRows.slice(0, -1).forEach(tr => tr.style.display = 'none');
    headRows.at(-1).querySelectorAll('th').forEach(c => { c.style.background = '#fffcf6'; });
    // A width-limited table (a long name) may wrap its name column only: it has height to spare.
    if (nameWidth) [...table.querySelectorAll('tr')].forEach(tr => { const c = tr.children[0]; if (c) { c.style.whiteSpace = 'normal'; c.style.textAlign = 'left'; c.querySelectorAll('button').forEach(b => b.style.textAlign = 'left'); c.style.width = nameWidth + 'px'; c.style.minWidth = nameWidth + 'px'; } });
    table.scrollIntoView({ block: 'center' });
    const b = table.getBoundingClientRect();
    const td = [...table.tBodies[0].rows].find(tr => tr.style.display !== 'none').children[0];
    return { x: b.left + scrollX, y: b.top + scrollY, width: b.width, height: b.height,
             font: parseFloat(getComputedStyle(td).fontSize), text: table.innerText, found };
  })(${JSON.stringify(spec.cols)}, ${JSON.stringify(spec.rows)}, ${JSON.stringify(spec.highlight ?? null)}, ${spec.total !== false}, ${spec.width ?? 380}, ${spec.name_width ?? 0}, ${spec.table_index ?? 0})`);
  await page.sleep(400);
  await shoot(page, r, file);
  return r;
}
