import { describe, it, expect } from "vitest";
import {
  uniqueDates,
  rowsForCodes,
  childrenOf,
  buildSeries,
  buildGrowthSeries,
  latestValue,
  formatCr,
  formatGrowth,
  formatDate,
  type CreditRow,
} from "./data";

// ── Fixture builder ──────────────────────────────────────────────────────────
// Minimal CreditRow with sensible defaults; override only what a test cares about.
function row(p: Partial<CreditRow>): CreditRow {
  return {
    report_date: "2026-01-30",
    statement: "1",
    code: "1",
    sector: "Agriculture",
    level: 1,
    is_priority_sector_memo: false,
    parent_code: "",
    parent_statement: "1",
    date: "2025-12-31",
    outstanding_cr: 100,
    source_date: "",
    ...p,
  };
}

// Two sectors over three month-ends. code "1" Agriculture; code "2" Industry.
// 1: Dec2024=100, Mar2025=110, Dec2025=130   2: Dec2024=200, Mar2025=220, Dec2025=242
const LABELS = { "1": "Agriculture", "2": "Industry" };
const ROWS: CreditRow[] = [
  row({ code: "1", sector: "Agriculture", date: "2024-12-31", outstanding_cr: 100 }),
  row({ code: "1", sector: "Agriculture", date: "2025-03-31", outstanding_cr: 110 }),
  row({ code: "1", sector: "Agriculture", date: "2025-12-31", outstanding_cr: 130 }),
  row({ code: "2", sector: "Industry", date: "2024-12-31", outstanding_cr: 200 }),
  row({ code: "2", sector: "Industry", date: "2025-03-31", outstanding_cr: 220 }),
  row({ code: "2", sector: "Industry", date: "2025-12-31", outstanding_cr: 242 }),
];

describe("uniqueDates", () => {
  it("returns sorted, de-duplicated dates", () => {
    expect(uniqueDates(ROWS)).toEqual(["2024-12-31", "2025-03-31", "2025-12-31"]);
  });
});

describe("rowsForCodes", () => {
  it("filters by code and excludes PSL memo rows by default", () => {
    const psl = row({ code: "1", date: "2025-12-31", is_priority_sector_memo: true });
    const out = rowsForCodes([...ROWS, psl], ["1"]);
    expect(out).toHaveLength(3);
    expect(out.every((r) => r.code === "1" && !r.is_priority_sector_memo)).toBe(true);
  });
});

describe("childrenOf", () => {
  it("collects child codes + labels for a parent", () => {
    const kids = childrenOf(
      [
        row({ code: "2.1", sector: "MSME", parent_code: "2" }),
        row({ code: "2.2", sector: "Large", parent_code: "2" }),
        row({ code: "1.1", sector: "Crop", parent_code: "1" }),
      ],
      "2",
    );
    expect(kids.codes.sort()).toEqual(["2.1", "2.2"]);
    expect(kids.labels).toEqual({ "2.1": "MSME", "2.2": "Large" });
  });
});

describe("buildSeries", () => {
  it("emits one labelled point per date with values keyed by sector label", () => {
    const s = buildSeries(ROWS, ["1", "2"], LABELS);
    expect(s).toHaveLength(3);
    expect(s[2].Agriculture).toBe(130);
    expect(s[2].Industry).toBe(242);
    // _ts is set for chart sorting
    expect(s[2]._ts).toBe(new Date("2025-12-31").getTime());
  });
});

describe("buildGrowthSeries — YoY", () => {
  it("compares to the same month one calendar year prior", () => {
    const s = buildGrowthSeries(ROWS, ["1", "2"], LABELS, "yoy");
    // Only Dec 2025 has a Dec 2024 comparison; Mar 2025 has no Mar 2024 → skipped.
    expect(s).toHaveLength(1);
    expect(s[0].Agriculture).toBe(30.0); // 130/100 - 1
    expect(s[0].Industry).toBe(21.0); // 242/200 - 1
  });
});

describe("buildGrowthSeries — FY", () => {
  it("compares to the previous March month-end (start of the fiscal year)", () => {
    const s = buildGrowthSeries(ROWS, ["1", "2"], LABELS, "fy");
    // Dec 2025 → Mar 2025; Mar 2025 → Mar 2024 (absent) → skipped.
    expect(s).toHaveLength(1);
    expect(s[0].Agriculture).toBe(18.2); // 130/110 - 1 = 18.18 → 18.2
    expect(s[0].Industry).toBe(10.0); // 242/220 - 1
  });

  it("returns [] when fewer than two dates exist", () => {
    expect(buildGrowthSeries([row({ date: "2025-12-31" })], ["1"], LABELS, "yoy")).toEqual([]);
  });
});

describe("latestValue", () => {
  it("returns the value at the latest date for a code", () => {
    expect(latestValue(ROWS, "1")).toBe(130);
    expect(latestValue(ROWS, "2")).toBe(242);
  });
  it("returns null for an unknown code", () => {
    expect(latestValue(ROWS, "999")).toBeNull();
  });
});

describe("formatCr", () => {
  it("scales to L Cr / Th Cr / Cr by magnitude", () => {
    expect(formatCr(130000)).toBe("₹1.30 L Cr");
    expect(formatCr(5000)).toBe("₹5.00 Th Cr");
    expect(formatCr(130)).toBe("₹130 Cr");
    expect(formatCr(null)).toBe("—");
  });
});

describe("formatGrowth", () => {
  it("signs positive growth and renders one decimal", () => {
    expect(formatGrowth(30)).toBe("+30.0%");
    expect(formatGrowth(-5)).toBe("-5.0%");
    expect(formatGrowth(0)).toBe("0.0%");
    expect(formatGrowth(null)).toBe("—");
  });
});

describe("formatDate", () => {
  it("renders 'Mon YYYY' and empty string for empty input", () => {
    expect(formatDate("2025-12-31")).toMatch(/Dec 2025/);
    expect(formatDate("")).toBe("");
  });
});
