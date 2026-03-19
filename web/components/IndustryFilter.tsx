"use client";

import { useState, useMemo, useEffect } from "react";
import { CreditRow, buildSeries, uniqueDates } from "@/lib/data";

// Stable empty opts to avoid new-object-on-every-render
const EMPTY_OPTS = {};

type FilterMode = "topN" | "coverage" | "all";

interface IndustryFilterProps {
  rows: CreditRow[];
  allCodes: string[];
  labels: Record<string, string>;
  dataOpts?: { psl?: boolean; stmt?: string };
  onFilteredCodes: (codes: string[]) => void;
}

export default function IndustryFilter({
  rows, allCodes, labels, dataOpts = EMPTY_OPTS, onFilteredCodes
}: IndustryFilterProps) {
  const [mode, setMode]     = useState<FilterMode>("topN");
  const [topN, setTopN]     = useState(10);
  const [coverage, setCoverage] = useState(80);

  // Compute shares at latest date
  const shares = useMemo(() => {
    const dates   = uniqueDates(rows);
    const latest  = dates[dates.length - 1];
    const series  = buildSeries(rows, allCodes, labels, dataOpts);
    const latestPt = series[series.length - 1];
    if (!latestPt) return {} as Record<string, number>;

    const total = allCodes.reduce(
      (s, c) => s + (Number(latestPt[labels[c] ?? c]) || 0), 0
    );
    const out: Record<string, number> = {};
    allCodes.forEach((c) => {
      out[c] = total > 0 ? (Number(latestPt[labels[c] ?? c]) || 0) / total * 100 : 0;
    });
    return out;
  }, [rows, allCodes, labels, dataOpts]);

  const sortedCodes = useMemo(
    () => [...allCodes].sort((a, b) => (shares[b] ?? 0) - (shares[a] ?? 0)),
    [allCodes, shares]
  );

  const filtered = useMemo(() => {
    if (mode === "all") return sortedCodes;
    if (mode === "topN") return sortedCodes.slice(0, topN);
    // coverage mode
    let cumulative = 0;
    return sortedCodes.filter((c) => {
      if (cumulative >= coverage) return false;
      cumulative += shares[c] ?? 0;
      return true;
    });
  }, [mode, topN, coverage, sortedCodes, shares]);

  // Propagate changes after render — useEffect, not useMemo
  useEffect(() => {
    onFilteredCodes(filtered);
  }, [filtered]); // eslint-disable-line react-hooks/exhaustive-deps

  const coveredPct = filtered.reduce((s, c) => s + (shares[c] ?? 0), 0);

  return (
    <div
      className="flex flex-wrap items-center gap-3 mb-4 p-3 rounded-lg text-xs"
      style={{ background: "var(--bg-page)", border: "1px solid var(--border-card)" }}
    >
      {(["topN", "coverage", "all"] as FilterMode[]).map((m) => (
        <label key={m} className="flex items-center gap-1 cursor-pointer" style={{ color: "var(--font)" }}>
          <input
            type="radio"
            name="industry-filter"
            value={m}
            checked={mode === m}
            onChange={() => setMode(m)}
            className="accent-blue-500"
          />
          {m === "topN" ? "Top N" : m === "coverage" ? "≥ X% coverage" : "All"}
        </label>
      ))}

      {mode === "topN" && (
        <input
          type="number"
          min={1}
          max={allCodes.length}
          value={topN}
          onChange={(e) => setTopN(Number(e.target.value))}
          className="w-16 px-2 py-1 rounded border text-xs"
          style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border-card)",
            color: "var(--font)",
          }}
        />
      )}

      {mode === "coverage" && (
        <div className="flex items-center gap-1">
          <input
            type="number"
            min={1}
            max={100}
            value={coverage}
            onChange={(e) => setCoverage(Number(e.target.value))}
            className="w-16 px-2 py-1 rounded border text-xs"
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border-card)",
              color: "var(--font)",
            }}
          />
          <span style={{ color: "var(--font-muted)" }}>%</span>
        </div>
      )}

      <span style={{ color: "var(--font-muted)" }}>
        Showing {filtered.length} of {allCodes.length} types covering{" "}
        <strong>{coveredPct.toFixed(1)}%</strong> of Industry
      </span>
    </div>
  );
}
