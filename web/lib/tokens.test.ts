import { describe, it, expect } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { FS, R, GLYPH, TEXT } from "./tokens";

// The scale that preceded this one lived in globals.css, declared itself mandatory, and had zero
// consumers — nothing failed when a component picked its own number instead, so fifteen font sizes
// and seven radii accumulated unnoticed. These tests are the part that was missing: a raw size
// anywhere outside tokens.ts is now a failing build, not a thing someone might spot in review.

const SURFACES = ["components", "app"];
// The OG image renders through Satori onto a 1200x630 canvas — a different medium with its own
// proportions, deliberately not on the page ladder.
const EXEMPT = ["app/opengraph-image.tsx"];

function tsxFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return tsxFiles(path);
    return path.endsWith(".tsx") && !EXEMPT.includes(path) ? [path] : [];
  });
}

const sources = SURFACES.flatMap(tsxFiles).map((path) => ({ path, text: readFileSync(path, "utf8") }));

describe("the type and radius ladders are the only source of sizes", () => {
  it("finds the surfaces it is meant to guard", () => {
    expect(sources.length).toBeGreaterThan(10);
  });

  it.each(["fontSize", "borderRadius"])("no raw %s outside tokens.ts", (prop) => {
    // A `${...}` is a token reference, and a bare 0 is not a choice off any scale — a corner that
    // is square is square at every step of the ladder. Everything else must name a token.
    const value = new RegExp(`${prop}:\\s*(\`[^\`]*\`|"[^"]*"|'[^']*'|[^,}\\n]+)`);
    const offenders = sources.flatMap(({ path, text }) =>
      text
        .split("\n")
        .map((line, n) => ({ line, n: n + 1, m: line.match(value) }))
        .filter(({ m }) => m && /(?<![.0-9])[0-9]+(\.[0-9]+)?/.test(
          m[1].replace(/\$\{[^}]*\}/g, "").replace(/\b0\b/g, ""),
        ))
        .map(({ line, n }) => `${path}:${n}  ${line.trim()}`),
    );
    expect(offenders).toEqual([]);
  });

  it("keeps the ladder a ladder — steps ascend, none repeat", () => {
    for (const scale of [Object.values(FS), Object.values(R)]) {
      const steps = scale as number[];
      expect(steps).toEqual([...steps].sort((a, b) => a - b));
      expect(new Set(steps).size).toBe(steps.length);
    }
  });

  it("keeps glyph sizes off the type ladder", () => {
    // A glyph is sized to sit beside text, not to be read as text. Letting one become a font step
    // is how a scale grows a rung no sentence will ever use.
    for (const size of Object.values(GLYPH)) {
      expect(Object.values(FS).filter((fs) => fs === size).length).toBeLessThanOrEqual(1);
    }
  });
});

describe("the information hierarchy (DASHBOARD_SPEC §22)", () => {
  // The Read surface is where the hierarchy lives. A heading-sized step picked directly
  // (FS.title / FS.section / FS.card) is a level chosen by eye: it is how the tiles, the rail
  // and the row chart each grew their own. Those steps reach a Read component only through TEXT.
  const read = sources.filter(({ path }) => path.startsWith(join("components", "read")));

  it("finds the Read components", () => {
    expect(read.length).toBeGreaterThan(4);
  });

  it("reaches heading sizes only through a TEXT level", () => {
    const offenders = read.flatMap(({ path, text }) =>
      text.split("\n")
        .map((line, n) => ({ line, n: n + 1 }))
        .filter(({ line }) => /FS\.(title|section|card)\b/.test(line))
        .map(({ line, n }) => `${path}:${n}  ${line.trim()}`));
    expect(offenders).toEqual([]);
  });

  it("orders the levels: each heading is larger than the one below it", () => {
    expect(TEXT.title.fontSize).toBeGreaterThan(TEXT.section.fontSize);
    expect(TEXT.section.fontSize).toBeGreaterThan(TEXT.item.fontSize);
    expect(TEXT.item.fontSize).toBeGreaterThan(TEXT.body.fontSize);
    expect(TEXT.body.fontSize).toBeGreaterThan(TEXT.meta.fontSize);
  });
});
