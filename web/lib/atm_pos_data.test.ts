import { describe, it, expect } from "vitest";
import {
  formatAtmValue,
  getTopNBanks,
  buildQoQValue,
  type AtmPosSeries,
  type ChartPoint,
} from "./atm_pos_data";

describe("formatAtmValue — count / transactions", () => {
  it("scales to B / M / K and leaves small counts raw", () => {
    expect(formatAtmValue(1_500_000_000, "transactions")).toBe("1.5B");
    expect(formatAtmValue(5_000_000, "transactions")).toBe("5.0M");
    expect(formatAtmValue(3_200, "count")).toBe("3.2K");
    expect(formatAtmValue(500, "count")).toBe("500");
  });
});

describe("formatAtmValue — rs_thousands → crore", () => {
  it("divides by 10,000 then scales to L Cr / Cr", () => {
    expect(formatAtmValue(2_000_000_000, "rs_thousands")).toBe("₹2.0 L Cr"); // cr = 200,000
    expect(formatAtmValue(50_000_000, "rs_thousands")).toBe("₹5,000 Cr"); // cr = 5,000
    expect(formatAtmValue(50_000, "rs_thousands")).toBe("₹5.0 Cr"); // cr = 5
  });
});

// 3 banks, 2 periods. Top-N reads the LATEST period (index 1).
const SERIES: AtmPosSeries = {
  _meta: { pipeline: "atm_pos", periods: ["2025-11-30", "2025-12-31"], entity_count: 3, metric_count: 2 },
  entities: [
    { name: "HDFC", category: "Private" },
    { name: "SBI", category: "Public" },
    { name: "ICICI", category: "Private" },
  ],
  series: {
    credit_cards: { total: [23, 100], entity: [[10, 20], [5, 50], [8, 30]] },
    debit_cards: { total: [6, 9], entity: [[1, 2], [2, 3], [3, 4]] },
  },
};

describe("getTopNBanks", () => {
  it("ranks banks by the latest-period value of a single metric", () => {
    // latest credit_cards: HDFC 20, SBI 50, ICICI 30
    expect(getTopNBanks(SERIES, "credit_cards", 2)).toEqual(["SBI", "ICICI"]);
    expect(getTopNBanks(SERIES, "credit_cards", 3)).toEqual(["SBI", "ICICI", "HDFC"]);
  });
  it("sums across metrics when given an array", () => {
    // latest cc+dc: HDFC 22, SBI 53, ICICI 34
    expect(getTopNBanks(SERIES, ["credit_cards", "debit_cards"], 1)).toEqual(["SBI"]);
  });
});

// Two fiscal quarters of Total points: FY2025-Q3 (Oct–Dec 2025) then FY2025-Q4 (Jan–Feb 2026).
const pt = (iso: string, total: number): ChartPoint => ({
  date: iso,
  _ts: new Date(iso).getTime(),
  Total: total,
});
const QPTS = [
  pt("2025-10-31", 100),
  pt("2025-11-30", 110),
  pt("2025-12-31", 120),
  pt("2026-01-31", 130),
  pt("2026-02-28", 140),
];

describe("buildQoQValue", () => {
  it("stock metric: compares the last point of each of the two latest quarters", () => {
    // Q3 last = 120, Q4 last = 140 → +16.7%
    expect(buildQoQValue(QPTS, "count")).toBe(16.7);
  });
  it("flow metric: compares the SUM of each quarter", () => {
    // Q3 sum = 330, Q4 sum = 270 → -18.2%
    expect(buildQoQValue(QPTS, "transactions")).toBe(-18.2);
  });
  it("returns null with fewer than two quarters of data", () => {
    expect(buildQoQValue([pt("2025-12-31", 120)], "count")).toBeNull();
    expect(buildQoQValue([], "count")).toBeNull();
  });
});
