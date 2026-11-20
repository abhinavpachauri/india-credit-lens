import { describe, it, expect } from "vitest";
import { sortParts, type CutRow } from "./table";

const row = (entity: string, growth: number, extra: Partial<CutRow> = {}): CutRow => ({
  entity, size: { display: "", sort: 1 }, of_cut: null, of_book: null,
  growth: { display: `${growth}%`, sort: growth }, pace: null, new: null, ...extra,
});

describe("sortParts", () => {
  it("ranks growth above the minimum base first, and small-base banks after them", () => {
    const parts = [row("A", 10), row("Tiny", 3000, { small_base: true }), row("B", 20)];
    expect(sortParts(parts, "growth", "desc").map((p) => p.entity)).toEqual(["B", "A", "Tiny"]);
    expect(sortParts(parts, "growth", "asc").map((p) => p.entity)).toEqual(["A", "B", "Tiny"]);
  });

  it("leaves the small-base mark out of every other column's order", () => {
    const parts = [row("A", 10), row("Tiny", 3000, { small_base: true, size: { display: "", sort: 9 } })];
    expect(sortParts(parts, "size", "desc")[0].entity).toBe("Tiny");
  });

  it("keeps an indented line under its parent, sorted among its siblings", () => {
    const parts = [row("Industry", 15), row("Retail", 12), row("Housing", 5, { indent: 1 }),
                   row("Vehicle", 8, { indent: 1 }), row("Agriculture", 27)];
    expect(sortParts(parts, "growth", "desc").map((p) => p.entity))
      .toEqual(["Agriculture", "Industry", "Retail", "Vehicle", "Housing"]);
  });
});
