// Build a batch of X posts: one text + one 1600x900 image per day (DISTRIBUTION_SPEC §16).
//
//   node analysis/distribution/x/build_posts.mjs analysis/distribution/x/batches/{batch}.json [--base URL]
//
// The image is the dashboard's own table, cut down to the rows and columns the post talks about,
// composed on a 16:9 canvas. 16:9 because X shows a single image uncropped at that ratio on both
// phone and desktop. Readability is measured, not assumed: the table's text size on the canvas is
// computed from the capture and reported as it will look on a ~390px-wide phone timeline image.
// A post whose table text would be smaller than PHONE_MIN_PX there fails.
//
// Every number in the post text must appear in what the image shows, or in a stored cell note the
// batch names (`notes`). The browser never formats a number; this check holds the post to that.
import { launch, shoot } from "../carousel/cdp.mjs";
import { readFileSync, writeFileSync, mkdirSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";

const ROOT = new URL("../../../", import.meta.url).pathname;
const W = 1600, H = 900, PAD = 52, CAPTURE_SCALE = 3;
const PHONE_W = 390, PHONE_MIN_PX = 9;               // a phone timeline image is ~390px wide
const MAX_CHARS = 280, URL_CHARS = 23;               // X counts any link as 23 characters

const args = process.argv.slice(2);
const batchPath = args.find((a) => a.endsWith(".json"));
const base = args.includes("--base") ? args[args.indexOf("--base") + 1] : "https://indiacreditlens.com";
if (!batchPath) throw new Error("usage: build_posts.mjs {batch}.json [--base URL]");
const batch = JSON.parse(readFileSync(batchPath, "utf8"));
const outRoot = join(ROOT, batch.out_dir);

// ── stored notes (e.g. the deflator a real-credit cell was net of) come from the sidecars ──
// `index` reads a past reading from `series_display` (−1 = latest, −13 = a year earlier on a
// monthly series), so a post can quote "a year ago" from the store, never from memory.
function storedNote({ sidecar, cut, entity, column, field = "note", index }) {
  const t = JSON.parse(readFileSync(join(ROOT, "web/public/data", sidecar), "utf8"));
  const c = cut ? t.cuts[cut] : t;
  const p = entity === null ? c.total : c.parts.find((x) => x.entity === entity);
  const cell = p?.[column];
  const v = index === undefined ? cell?.[field] : cell?.series_display?.at(index);
  if (!v) throw new Error(`no stored ${field} for ${sidecar} › ${cut} › ${entity} › ${column}`);
  return v;
}

// ── the post-text checks ──
function postLength(text) {
  return text.replace(/\b(?:https?:\/\/)?indiacreditlens\.com\S*/g, "x".repeat(URL_CHARS)).length;
}
const NUM = /[−-]?\d+(?:,\d{2,3})*(?:\.\d+)?/g;
function untraced(text, shown) {
  const hay = shown.replace(/−/g, "-");
  return [...new Set((text.replace(/\b(?:https?:\/\/)?indiacreditlens\.com\S*/g, "").match(NUM) || []))]
    .map((n) => n.replace(/−/g, "-"))
    .filter((n) => !/^20\d\d$/.test(n))             // years are dates, not readings
    .filter((n) => !hay.includes(n.replace(/^-/, "")));
}

// ── capture one table, cut to the wanted rows and columns ──
async function captureTable(page, spec, file) {
  const { send, evaluate } = page;
  await send("Page.navigate", { url: base + spec.path });
  await page.sleep(5000);
  for (const label of spec.clicks) {
    await evaluate(`(async () => {
      for (let i = 0; i < 40; i++) {
        const t = [...document.querySelectorAll('*')].find(e => e.childElementCount < 3 && e.textContent.trim() === ${JSON.stringify(label)});
        if (t) { t.click(); await new Promise(r => setTimeout(r, 1800)); return; }
        await new Promise(r => setTimeout(r, 250));
      }
      throw new Error('not found: ' + ${JSON.stringify(label)});
    })()`);
  }
  const r = await evaluate(`((cols, rows, highlight, total, width, nameWidth) => {
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
    const table0 = document.querySelectorAll('table')[0];
    if (table0) [...table0.querySelectorAll('*')].filter(e => !e.childElementCount && e.textContent.trim() === 'ⓘ').forEach(e => e.style.display = 'none');
    const table = document.querySelectorAll('table')[0];
    if (!table) throw new Error('no table on the page');
    const label = th => (th.childNodes[0]?.textContent ?? '').trim().toUpperCase();
    const heads = [...table.querySelectorAll('thead th')];
    const missing = cols.filter(c => !heads.some(th => label(th).startsWith(c)));
    if (missing.length) throw new Error('columns not on the table: ' + missing.join(', '));
    const wanted = heads.filter(th => cols.some(c => label(th).startsWith(c))).map(th => th.getBoundingClientRect());
    const hide = [...table.querySelectorAll('th, td')].filter(c => { const b = c.getBoundingClientRect(); const cx = (b.left + b.right) / 2;
      return !wanted.some(h => h.left <= cx && cx <= h.right); });
    hide.forEach(c => c.style.display = 'none');
    const found = [];
    [...table.querySelectorAll('tbody tr')].forEach((tr, i) => {
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
    let w = table.parentElement; while (w && getComputedStyle(w).overflowX === 'visible') w = w.parentElement;
    if (w) w.style.overflowX = 'visible';
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
    if (nameWidth) [...table.querySelectorAll('tr')].forEach(tr => { const c = tr.children[0]; if (c) { c.style.whiteSpace = 'normal'; c.style.width = nameWidth + 'px'; c.style.minWidth = nameWidth + 'px'; } });
    table.scrollIntoView({ block: 'center' });
    const b = table.getBoundingClientRect();
    const td = table.querySelector('tbody tr:not([style*="none"]) td');
    return { x: b.left + scrollX, y: b.top + scrollY, width: b.width, height: b.height,
             font: parseFloat(getComputedStyle(td).fontSize), text: table.innerText, found };
  })(${JSON.stringify(spec.cols)}, ${JSON.stringify(spec.rows)}, ${JSON.stringify(spec.highlight ?? null)}, ${spec.total !== false}, ${spec.width ?? 380}, ${spec.name_width ?? 0})`);
  await page.sleep(400);
  await shoot(page, r, file);
  return r;
}

// ── compose the 1600x900 card ──
function cardHtml(post, tables) {
  // Several tables stack, each with the full width: side by side they fell to ~7px on a phone.
  const n = tables.length, gap = 28;
  const areaW = W - 2 * PAD;
  const areaH = H - 2 * PAD - 112 /* brand + title */ - 50 /* footer */ - (n > 1 ? n * 44 + gap * (n - 1) : 0);
  // One scale for every table on the card, so stacked tables read at one size.
  const s = Math.min(areaW / Math.max(...tables.map((t) => t.width)), areaH / tables.reduce((a, t) => a + t.height, 0));
  const items = tables.map((t) => `
    <figure>${n > 1 ? `<figcaption>${t.caption}</figcaption>` : ""}
      <img src="${t.file}" style="width:${Math.round(t.width * s)}px;height:${Math.round(t.height * s)}px"></figure>`).join("");
  return { s, html: `<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin: 0; }
  body { width: ${W}px; height: ${H}px; background: #faf6ef; font-family: Geist, -apple-system, Helvetica, sans-serif; color: #1c1917; }
  .card { width: ${W}px; height: ${H}px; padding: ${PAD}px; display: flex; flex-direction: column; }
  .brand { font-size: 26px; font-weight: 600; letter-spacing: .06em; color: #78716c; text-transform: uppercase; }
  h1 { font-size: 50px; font-weight: 800; line-height: 1.1; letter-spacing: -.01em; margin-top: 10px; }
  .tables { flex: 1; display: flex; flex-direction: column; gap: ${gap}px; align-items: center; justify-content: center; }
  figure { display: flex; flex-direction: column; align-items: flex-start; gap: 8px; }
  figcaption { font-size: 30px; font-weight: 700; color: #44403c; }
  img { border-radius: 14px; border: 2px solid #e7e0d4; background: #fff; }
  .foot { display: flex; justify-content: space-between; font-size: 24px; color: #78716c; }
  .foot b { color: #1c1917; }
</style></head><body><div class="card">
  <div class="brand">India Credit Lens · ${post.image.kicker}</div>
  <h1>${post.image.title}</h1>
  <div class="tables">${items}</div>
  <div class="foot"><span>${post.image.source}</span><b>indiacreditlens.com</b></div>
</div></body></html>` };
}

// ── run ──
const page = await launch(9411);
await page.send("Page.enable");
await page.send("Emulation.setDeviceMetricsOverride", { width: 420, height: 3000, deviceScaleFactor: CAPTURE_SCALE, mobile: true });
await page.send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "light" }] });

const report = [];
for (const post of batch.posts) {
  const dir = join(outRoot, `${post.date}_${post.slug}`);
  mkdirSync(dir, { recursive: true });
  const problems = [];
  const tables = [];
  for (const [i, spec] of post.image.tables.entries()) {
    const file = join(dir, `table${i + 1}.png`);
    try {
      const r = await captureTable(page, spec, file);
      tables.push({ ...r, file, caption: spec.caption ?? "" });
    } catch (e) { problems.push(`table ${i + 1}: ${e.message.slice(0, 200)}`); }
  }
  const notes = (post.notes || []).map(storedNote);
  const shown = [post.image.title, ...tables.map((t) => t.text), ...notes].join(" \n ");
  const len = postLength(post.text);
  if (len > MAX_CHARS) problems.push(`text is ${len} characters (max ${MAX_CHARS})`);
  const loose = untraced(post.text, shown);
  if (loose.length) problems.push(`numbers not on the image or a stored note: ${loose.join(", ")}`);
  const titleLoose = untraced(post.image.title, tables.map((t) => t.text).join(" ") + notes.join(" "));
  if (titleLoose.length) problems.push(`title numbers not in the table: ${titleLoose.join(", ")}`);

  let phonePx = null;
  if (tables.length === post.image.tables.length) {
    const { s, html } = cardHtml(post, tables);
    const htmlFile = join(dir, "card.html");
    writeFileSync(htmlFile, html);
    // Table text on the canvas = its CSS size x (displayed width / CSS width); then onto a phone.
    phonePx = Math.min(...tables.map((t) => t.font * s)) * (PHONE_W / W);
    if (phonePx < PHONE_MIN_PX) problems.push(`table text ${phonePx.toFixed(1)}px on a phone (min ${PHONE_MIN_PX})`);
    await page.send("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: 1, mobile: false });
    await page.send("Page.navigate", { url: "file://" + htmlFile });
    await page.sleep(2500);
    const overflow = await page.evaluate(`[...document.querySelectorAll('.card *')].filter(e => { const r = e.getBoundingClientRect(); return r.width && (r.right > ${W} - ${PAD} + 2 || r.bottom > ${H} - ${PAD} + 2); }).map(e => e.tagName).slice(0, 4)`);
    if (overflow.length) problems.push(`card overflows its frame: ${overflow.join(",")}`);
    await shoot(page, { x: 0, y: 0, width: W, height: H }, join(dir, "card.png"));
    // A day's folder holds what gets posted: post.txt and card.png. The captures were steps.
    for (const t of tables) rmSync(t.file, { force: true });
    rmSync(htmlFile, { force: true });
    await page.send("Emulation.setDeviceMetricsOverride", { width: 420, height: 3000, deviceScaleFactor: CAPTURE_SCALE, mobile: true });
  }
  writeFileSync(join(dir, "post.txt"), post.text + "\n");
  report.push({ post: `${post.date}_${post.slug}`, chars: len, phone_table_px: phonePx && +phonePx.toFixed(1), ok: !problems.length, problems });
  console.log(`${problems.length ? "✗" : "✓"} ${post.date} ${post.slug}  ${len} chars · table text ${phonePx ? phonePx.toFixed(1) : "?"}px on a phone${problems.length ? "\n    " + problems.join("\n    ") : ""}`);
}
writeFileSync(join(outRoot, "build_report.json"), JSON.stringify(report, null, 1));
page.close();
process.exit(report.every((r) => r.ok) ? 0 : 1);
