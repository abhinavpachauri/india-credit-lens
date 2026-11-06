// Build one LinkedIn carousel from a spec: 1080x1350 slides, one PDF, and the post text.
//
//   node analysis/distribution/carousel/build_set.mjs analysis/distribution/carousel/sets/{set}.json [--base URL]
//
// Each slide is claim → evidence → change: a headline, the dashboard's own table cut to its rows,
// and a band saying what moved since last month. A point with no monthly change fails the build,
// because a carousel without it reads as a snapshot (the user's rule since the August sets).
// Every number on a slide or in the post must be on a table the set shows, or in a stored note.
import { launch, shoot } from "./cdp.mjs";
import { captureTable, storedNote, untraced } from "./table_capture.mjs";
import { renderScorecard, renderTrend, SCORE_CSS } from "./scorecard.mjs";
import { readFileSync, writeFileSync, mkdirSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";

const ROOT = new URL("../../../", import.meta.url).pathname;
const W = 1080, H = 1350, CAPTURE_SCALE = 3;
const SHOT_W = 860;                // the table's width on the slide: 920 of content, less the frame's padding
const MIN_TABLE_PX = 26;           // about 9px once LinkedIn shows the slide ~360px wide on a phone

const args = process.argv.slice(2);
const specPath = args.find((a) => a.endsWith(".json"));
const base = args.includes("--base") ? args[args.indexOf("--base") + 1] : "https://indiacreditlens.com";
if (!specPath) throw new Error("usage: build_set.mjs {set}.json [--base URL]");
const set = JSON.parse(readFileSync(specPath, "utf8"));
const out = join(ROOT, set.out_dir);
rmSync(out, { recursive: true, force: true });
mkdirSync(join(out, "shots"), { recursive: true });

const CSS = `
  :root { --page:#faf6ef; --card:#fffcf5; --border:#e4d9c8; --ink:#2c1e0f; --muted:#7a6a55;
          --red:#e05c5c; --purple:#a87fdb; --blue:#4e8ef7; --green:#2ca02c; --orange:#ff7f0e; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:var(--page); font-family:Geist,-apple-system,"Helvetica Neue",Arial,sans-serif; color:var(--ink); }
  .slide { width:${W}px; height:${H}px; background:var(--page); padding:76px 80px 64px; display:flex; flex-direction:column;
           overflow:hidden; border-top:14px solid var(--accent); break-after:page; }
  .slide > * { flex-shrink:0; }
  .kicker { font-size:32px; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); }
  .kicker b { color:var(--accent); }
  h1 { font-size:76px; line-height:1.08; font-weight:800; letter-spacing:-.02em; margin-top:28px; }
  h2 { font-size:60px; line-height:1.1; font-weight:800; letter-spacing:-.015em; margin-top:22px; }
  .fromto { display:flex; align-items:flex-end; gap:32px; margin-top:38px; }
  .big { font-size:108px; font-weight:800; letter-spacing:-.03em; line-height:1; white-space:nowrap; }
  .big.alert { color:var(--red); }
  .lab { font-size:32px; color:var(--muted); margin-top:12px; font-weight:500; }
  .arrow { font-size:80px; color:var(--muted); padding-bottom:58px; }
  .arrow.vs { font-size:44px; font-weight:600; padding-bottom:72px; }
  .body { font-size:40px; line-height:1.3; margin-top:26px; }
  .shot { background:var(--card); border:2px solid var(--border); border-radius:28px; padding:28px; box-sizing:border-box; margin-top:30px; box-shadow:0 10px 30px rgba(120,90,40,.10); }
  .shot img { display:block; width:${SHOT_W}px; height:auto; border-radius:12px; }
  .cap { font-size:30px; color:var(--muted); margin-top:18px; line-height:1.3; }
  .spacer { flex:1 1 auto !important; }
  .callout { font-size:40px; font-weight:700; line-height:1.25; padding:22px 30px; border-radius:20px; margin-top:24px;
             background:color-mix(in srgb, var(--accent) 14%, var(--card)); border-left:10px solid var(--accent); }
  .foot { display:flex; justify-content:space-between; align-items:baseline; font-size:30px; color:var(--muted); padding-top:18px; }
  .foot b { color:var(--ink); }
  .points { margin-top:70px; display:flex; flex-direction:column; gap:44px; }
  .point { display:flex; gap:34px; align-items:flex-start; }
  .num { flex:none; width:96px; height:96px; border-radius:50%; display:grid; place-items:center; font-size:50px; font-weight:800; color:#fff; background:var(--c); }
  .t { font-size:52px; font-weight:700; line-height:1.15; }
  .t span { display:block; font-size:38px; font-weight:500; color:var(--muted); margin-top:10px; }
  .rr { margin-top:54px; display:grid; grid-template-columns:320px 1fr; column-gap:36px; row-gap:30px; align-items:baseline; }
  .rr b { font-size:40px; color:var(--muted); font-weight:600; }
  .rr span { font-size:44px; font-weight:800; line-height:1.15; }
  .ask { font-size:46px; line-height:1.25; margin-top:54px; font-weight:600; }
`;

function slideHtml(s, i, shots) {
  const shot = shots[i];
  const n = set.slides.length;
  const foot = i === 0
    ? `<span>${set.sources} · ${n} slides</span><b>Swipe →</b>`
    : `<span>indiacreditlens.com</span><span>${s.source ?? set.sources}</span>`;
  const kicker = `<div class="kicker">${s.kicker}</div>`;
  if (s.kind === "cover")
    return `<section class="slide" id="s${i + 1}" style="--accent:var(--ink)">${kicker}<h1>${s.title}</h1>
      <div class="points">${s.points.map((p, j) => `<div class="point" style="--c:var(--${p.colour})"><div class="num">${j + 1}</div><div class="t">${p.head}<span>${p.sub}</span></div></div>`).join("")}</div>
      <div class="spacer"></div><div class="foot">${foot}</div></section>`;
  const rows = s.rows ? `<div class="rr">${s.rows.map(([a, b]) => `<b>${a}</b><span>${b}</span>`).join("")}</div>` : "";
  return `<section class="slide" id="s${i + 1}" style="--accent:var(--${s.accent})">${kicker}<h2>${s.title}</h2>
    ${s.from ? `<div class="fromto"><div><div class="big">${s.from[0]}</div><div class="lab">${s.from[1]}</div></div><div class="arrow${s.arrow ? "" : " vs"}">${s.arrow ? "→" : (s.joiner ?? "vs")}</div><div><div class="big${s.to_alert ? " alert" : ""}">${s.to[0]}</div><div class="lab">${s.to[1]}</div></div></div>` : ""}
    ${rows}
    ${s.body ? `<p class="body">${s.body}</p>` : ""}
    ${shot ? `<div class="shot"><img src="shots/${shot}">${s.cap ? `<div class="cap">${s.cap}</div>` : ""}</div>` : ""}
    ${s._html ?? ""}
    ${s.ask ? `<p class="ask">${s.ask}</p>` : ""}
    <div class="spacer"></div>
    ${s.change ? `<div class="callout">${s.change}</div>` : ""}
    <div class="foot">${foot}</div></section>`;
}

// ── capture every table, then check every number ──
const page = await launch(9412);
await page.send("Page.enable");
await page.send("Emulation.setDeviceMetricsOverride", { width: 420, height: 3000, deviceScaleFactor: CAPTURE_SCALE, mobile: true });
await page.send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "light" }] });

const problems = [];
const shots = {};
const everything = [];
for (const [i, s] of set.slides.entries()) {
  const where = `slide ${i + 1}`;
  let shown = (s.notes ?? []).map(storedNote).join(" \n ");
  if (s.kind === "scorecard" || s.kind === "trend") {
    const r = (s.kind === "scorecard" ? renderScorecard : renderTrend)(s, set);
    s._html = r.html;
    shown += " \n " + r.text;
  }
  if (s.table) {
    const name = `${i + 1}.png`;
    try {
      const r = await captureTable(page, s.table, join(out, "shots", name), base);
      shots[i] = name;
      shown += " \n " + r.text;
      const px = r.font * SHOT_W / r.width;
      if (px < MIN_TABLE_PX) problems.push(`${where}: table text ${px.toFixed(0)}px on the slide (min ${MIN_TABLE_PX})`);
    } catch (e) { problems.push(`${where}: ${e.message.slice(0, 200)}`); }
  }
  if (s.kind !== "cover" && !s.change && !s.rows) problems.push(`${where}: no monthly change`);
  const words = [s.title, s.from?.[0], s.to?.[0], s.body, s.change, s.ask, ...(s.rows ?? []).flat()].filter(Boolean).join(" \n ");
  const loose = untraced(words.replace(/<[^>]+>/g, ""), shown);
  if (loose.length) problems.push(`${where}: numbers not shown or stored: ${loose.join(", ")}`);
  everything.push(shown);
}
const postLoose = untraced(set.post, everything.join(" \n "));
if (postLoose.length) problems.push(`post text: numbers not in the set: ${postLoose.join(", ")}`);

// ── render ──
const html = `<!doctype html><html><head><meta charset="utf-8"><title>${set.title}</title>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>${CSS}${SCORE_CSS}</style></head><body>${set.slides.map((s, i) => slideHtml(s, i, shots)).join("\n")}</body></html>`;
writeFileSync(join(out, "slides.html"), html);
writeFileSync(join(out, "post.md"), set.post.trim() + "\n");

await page.send("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: 1, mobile: false });
await page.send("Page.navigate", { url: "file://" + join(out, "slides.html") });
await page.sleep(2500);
const overflow = await page.evaluate(`[...document.querySelectorAll('.slide')].flatMap((s, i) => { const b = s.getBoundingClientRect();
  return [...s.querySelectorAll('*')].filter(e => { const r = e.getBoundingClientRect(); return r.width && (r.right > b.right - 40 || r.bottom > b.bottom - 20); }).slice(0, 1).map(e => 'slide ' + (i + 1) + ': ' + (e.className || e.tagName)); })`);
overflow.forEach((o) => problems.push(`overflows its frame, ${o}`));
const rects = await page.evaluate(`[...document.querySelectorAll('.slide')].map(s => { const r = s.getBoundingClientRect(); return { id: s.id, x: r.left + scrollX, y: r.top + scrollY }; })`);
for (const r of rects) {
  const { data } = await page.send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true, clip: { x: r.x, y: r.y, width: W, height: H, scale: 1 } });
  writeFileSync(join(out, `slide_${r.id.slice(1)}.png`), Buffer.from(data, "base64"));
}
await page.evaluate(`(() => { const st = document.createElement('style'); st.textContent = '@page{size:${W}px ${H}px;margin:0}'; document.head.appendChild(st); })()`);
const { data } = await page.send("Page.printToPDF", { printBackground: true, preferCSSPageSize: true });
writeFileSync(join(out, `${set.file}_carousel_${set.slides.length}slides.pdf`), Buffer.from(data, "base64"));
page.close();

console.log(problems.length ? "✗ " + problems.join("\n✗ ") : `✓ ${set.file}: ${set.slides.length} slides, every number traced`);
process.exit(problems.length ? 1 : 0);
