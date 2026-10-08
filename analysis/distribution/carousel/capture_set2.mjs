// Capture the dashboard tables for the Set 2 carousel at phone width, 3x, light theme.
// Each table is cut down to the columns and rows the slide talks about, one row highlighted.
// Presentation only: every number is the dashboard's own.
import { launch, shoot } from "./cdp.mjs";

const OUT = new URL(".", import.meta.url).pathname + "shots/";
const BASE = "http://localhost:3000";
const page = await launch(9391);
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

async function capture({ file, path, clicks, cols, rows, highlight, tint, width = 340, total = true }) {
  await send("Page.navigate", { url: BASE + path });
  await page.sleep(3500);
  for (const c of clicks) await click(c);
  const rect = await evaluate(`((cols, rows, highlight, tint, width, total) => {
    for (const e of document.querySelectorAll('*')) {
      if (e.closest('table')) continue;                        // sticky first columns stay
      const p = getComputedStyle(e).position;
      if (p === 'sticky' || p === 'fixed') e.style.visibility = 'hidden';
    }
    document.querySelectorAll('nextjs-portal').forEach(e => e.style.display = 'none');
    const table = document.querySelectorAll('table')[0];
    // Tables can have grouped two-row headers, so match by position: a cell is kept when it
    // sits under a wanted header. Decide everything first, then hide (hiding moves things).
    const label = th => (th.childNodes[0]?.textContent ?? '').trim().toUpperCase();
    const wantedHeads = [...table.querySelectorAll('thead th')]
      .filter(th => cols.some(c => label(th).startsWith(c))).map(th => th.getBoundingClientRect());
    const cells = [...table.querySelectorAll('th, td')];
    const hide = cells.filter(c => { const r = c.getBoundingClientRect(); const cx = (r.left + r.right) / 2;
      return !wantedHeads.some(h => h.left <= cx && cx <= h.right); });
    hide.forEach(c => c.style.display = 'none');
    const body = [...table.querySelectorAll('tbody tr')];
    const found = [];
    body.forEach((tr, i) => {
      const name = tr.children[0].textContent.replace(/[▸▾\\s]+/g, ' ').trim();
      const wanted = (i === 0 && total) || rows.includes(name);   // the first row is the table's own total
      if (!wanted) tr.style.display = 'none'; else found.push(name);
      if (name === highlight) [...tr.children].forEach(c => { c.style.background = tint; c.style.fontWeight = '700'; });
    });
    let w = table.parentElement; while (w && getComputedStyle(w).overflowX === 'visible') w = w.parentElement;
    if (w) w.style.overflowX = 'visible';
    table.style.width = width + 'px'; table.style.minWidth = '0';
    table.querySelectorAll('td,th').forEach(c => { c.style.whiteSpace = 'normal'; });
    table.scrollIntoView({ block: 'center' });
    const r = table.getBoundingClientRect();
    return { x: r.left + scrollX, y: r.top + scrollY, width: r.width, height: r.height, found };
  })(${JSON.stringify(cols)}, ${JSON.stringify(rows)}, ${JSON.stringify(highlight)}, ${JSON.stringify(tint)}, ${width}, ${total})`);
  await page.sleep(500);
  await shoot(page, rect, OUT + file);
  console.log(file, Math.round(rect.width) + "x" + Math.round(rect.height), rect.found.join(" / "));
}

await capture({
  file: "1_cards_by_bank.png", path: "/payments", clicks: ["Credit Card", "bank (63)"],
  cols: ["PART", "OF CUT", "GROWTH"],
  rows: ["HDFC BANK LTD", "STATE BANK OF INDIA", "ICICI BANK LTD", "AXIS BANK LTD", "IDFC FIRST BANK LTD", "FEDERAL BANK LTD"],
  highlight: "FEDERAL BANK LTD", tint: "#e3ecfd",
});
await capture({
  file: "2_pos_value_by_category.png", path: "/payments", clicks: ["Credit Card", "POS Transactions"],
  cols: ["PART", "GROWTH", "NEW"],
  rows: ["Private Sector Banks", "Public Sector Banks", "Foreign Banks", "Small Finance Banks"],
  highlight: "Public Sector Banks", tint: "#e3ecfd", total: false,
});
await capture({
  file: "3_upi_qr_by_bank.png", path: "/payments", clicks: ["Digital Infrastructure", "UPI QR Codes", "bank (63)"],
  cols: ["PART", "SIZE", "OF CUT"],
  rows: ["YES BANK LTD", "AXIS BANK LTD", "INDUSIND BANK LTD"],
  highlight: "YES BANK LTD", tint: "#fdf0dc",
});
await capture({
  file: "4_personal_loans.png", path: "/", clicks: ["Personal Loans"],
  cols: ["PART", "OF CUT", "GROWTH", "NEW"],
  rows: ["Housing (Including Priority Sector Housing)", "Loans against gold jewellery",
         "Advances against Fixed Deposits (Including FCNR (B), NRNR Deposits etc.)"],
  highlight: "Loans against gold jewellery", tint: "#fdecd9", width: 360,
});
await capture({
  file: "5_fd_loans.png", path: "/", clicks: ["Personal Loans"],
  cols: ["PART", "GROWTH", "PACE"], width: 360,
  rows: ["Advances against Fixed Deposits (Including FCNR (B), NRNR Deposits etc.)"],
  highlight: "Advances against Fixed Deposits (Including FCNR (B), NRNR Deposits etc.)", tint: "#fdecd9", total: false,
});
page.close();
