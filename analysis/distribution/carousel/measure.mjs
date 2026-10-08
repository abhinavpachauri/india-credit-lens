import { launch } from "./cdp.mjs";
const DIR = new URL(".", import.meta.url).pathname;
const page = await launch(9355);
await page.send("Emulation.setDeviceMetricsOverride", { width: 1080, height: 1350, deviceScaleFactor: 1, mobile: false });
await page.send("Page.navigate", { url: "file://" + DIR + "slides.html" });
await page.sleep(2000);
console.log(await page.evaluate(`[...document.querySelectorAll('.slide')].map(s => { const sr = s.getBoundingClientRect(); const f = s.querySelector('.foot, .small:last-child'); const kids=[...s.children]; const last = kids[kids.length-1].getBoundingClientRect(); return s.id + ' room=' + Math.round(sr.bottom - 64 - last.bottom); }).join('  ')`));
page.close();
