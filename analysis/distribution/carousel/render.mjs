// Render each slide to a 1080x1350 PNG and all six to one PDF (LinkedIn document post).
import { launch } from "./cdp.mjs";
import { writeFileSync, mkdirSync } from "node:fs";
const DIR = new URL(".", import.meta.url).pathname;
mkdirSync(DIR + "out", { recursive: true });
const page = await launch(9354);
const { send, evaluate } = page;
await send("Page.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 1080, height: 1350, deviceScaleFactor: 1, mobile: false });
await send("Page.navigate", { url: "file://" + DIR + "slides.html" });
await page.sleep(2500);
console.log("fonts:", await evaluate("document.fonts.check('700 40px Geist')"));
await evaluate("document.body.style.background = '#faf6ef'");
const rects = await evaluate(`[...document.querySelectorAll('.slide')].map(s => { const r = s.getBoundingClientRect(); return { id: s.id, x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height }; })`);
// overflow check: any element poking outside its slide?
console.log("overflow:", await evaluate(`[...document.querySelectorAll('.slide')].map(s => { const sr = s.getBoundingClientRect(); const bad = [...s.querySelectorAll('*')].filter(e => { const r = e.getBoundingClientRect(); return r.width && (r.right > sr.right - 40 || r.bottom > sr.bottom - 20); }).map(e => e.className || e.tagName); return s.id + ':' + (bad.slice(0,4).join(',') || 'ok'); })`));
for (const r of rects) {
  const { data } = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true, clip: { x: r.x, y: r.y, width: r.w, height: r.h, scale: 1 } });
  writeFileSync(`${DIR}out/${r.id}.png`, Buffer.from(data, "base64"));
}
await evaluate(`(() => { const st = document.createElement('style'); st.textContent = '@page{size:1080px 1350px;margin:0} body{background:#faf6ef} .slide{margin:0;break-after:page}'; document.head.appendChild(st); })()`);
const { data } = await send("Page.printToPDF", { printBackground: true, preferCSSPageSize: true });
writeFileSync(DIR + "out/set3_carousel.pdf", Buffer.from(data, "base64"));
console.log("done", rects.map(r => r.id + " " + r.w + "x" + r.h).join(" | "));
page.close();
