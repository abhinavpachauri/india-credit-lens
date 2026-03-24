"use client";

import { useState, useMemo, useEffect } from "react";
import type { ChartPoint } from "@/lib/types";

type FilterMode = "topN" | "coverage" | "all";

interface IndustryFilterProps {
  absoluteData:      ChartPoint[];
  seriesNames:       string[];
  onFilteredSeries:  (names: string[]) => void;
}

export default function IndustryFilter({
  absoluteData, seriesNames, onFilteredSeries,
}: IndustryFilterProps) {
  const [mode, setMode]         = useState<FilterMode>("topN");
  const [topN, setTopN]         = useState(10);
  const [coverage, setCoverage] = useState(80);

  // Compute each series' share at the latest date
  const shares = useMemo(() => {
    const latestPt = absoluteData[absoluteData.length - 1];
    if (!latestPt) return {} as Record<string, number>;

    const total = seriesNames.reduce((s, n) => s + (Number(latestPt[n]) || 0), 0);
    const out: Record<string, number> = {};
    seriesNames.forEach((n) => {
      out[n] = total > 0 ? (Number(latestPt[n]) || 0) / total * 100 : 0;
    });
    return out;
  }, [absoluteData, seriesNames]);

  // Sort series by share descending
  const sortedNames = useMemo(
    () => [...seriesNames].sort((a, b) => (shares[b] ?? 0) - (shares[a] ?? 0)),
    [seriesNames, shares]
  );

  // Apply filter mode
  const filtered = useMemo(() => {
    if (mode === "all")  return sortedNames;
    if (mode === "topN") return sortedNames.slice(0, topN);
    let cumulative = 0;
    return sortedNames.filter((n) => {
      if (cumulative >= coverage) return false;
      cumulative += shares[n] ?? 0;
      return true;
    });
  }, [mode, topN, coverage, sortedNames, shares]);

  // Notify parent after render — useEffect avoids setState-during-render
  useEffect(() => {
    onFilteredSeries(filtered);
  }, [filtered]); // eslint-disable-line react-hooks/exhaustive-deps

  const coveredPct = filtered.reduce((s, n) => s + (shares[n] ?? 0), 0);

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
          max={seriesNames.length}
          value={topN}
          onChange={(e) => setTopN(Number(e.target.value))}
          className="w-16 px-2 py-1 rounded border text-xs"
          style={{
            background: "var(--bg-card)",
            border:     "1px solid var(--border-card)",
            color:      "var(--font)",
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
              border:     "1px solid var(--border-card)",
              color:      "var(--font)",
            }}
          />
          <span style={{ color: "var(--font-muted)" }}>%</span>
        </div>
      )}

      <span style={{ color: "var(--font-muted)" }}>
        Showing {filtered.length} of {seriesNames.length} types covering{" "}
        <strong>{coveredPct.toFixed(1)}%</strong> of Industry
      </span>
    </div>
  );
}
