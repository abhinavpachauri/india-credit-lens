import { defineConfig } from "vitest/config";

// Unit tests for the pure data-derivation functions in lib/ (no DOM, no fetch).
// These mirror the Python deterministic-core tests (analysis/tests/) on the web side:
// the chart/insight numbers the dashboard renders must derive correctly from inputs.
export default defineConfig({
  test: {
    environment: "node",
    include: ["lib/**/*.test.ts"],
  },
});
