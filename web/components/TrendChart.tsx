"use client";

import { useState, useMemo } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from "recharts";
import { formatCr, formatGrowth } from "@/lib/data";
import { pickColor } from "@/lib/theme";
import ChartLegend from "./ChartLegend";
import type { ChartPoint, AnnotationEffect } from "@/lib/types";

interface TrendChartProps {
  absoluteData:    ChartPoint[];
  growthData:      ChartPoint[];
  fyData:          ChartPoint[];
  seriesNames:     string[];
  pctLabel?:       string;
  visibleSeries?:  string[];          // optional subset — used by IndustryFilter
  highlightConfig?: AnnotationEffect | null;  // from active annotation
  preferredMode?:  "absolute" | "yoy" | "fy" | null; // annotation overrides radio
}

/** Compute per-series visual style based on active annotation. */
function seriesStyle(name: string, config: AnnotationEffect | null | undefined) {
  if (!config) return { opacity: 1, strokeWidth: 2, strokeDasharray: undefined };
  const highlighted = config.highlight?.includes(name) ?? false;
  const dimmed      = config.dim?.includes(name)       ?? false;
  const dashed      = config.dash?.includes(name)      ?? false;
  // Auto-fade anything not explicitly highlighted when a highlight set exists
  const autoFade    = (config.highlight?.length ?? 0) > 0 && !highlighted && !dimmed;
  return {
    opacity:          highlighted ? 1 : (dimmed || autoFade) ? 0.15 : 1,
    strokeWidth:      highlighted ? 3 : 2,
    strokeDasharray:  dashed ? "5 5" : undefined,
  };
}

type ViewMode = "absolute" | "yoy" | "fy";

export default function TrendChart({
  absoluteData, growthData, fyData = [], seriesNames,
  pctLabel = "% of Total", visibleSeries, highlightConfig, preferredMode,
}: TrendChartProps) {
  const [mode, setMode]     = useState<ViewMode>("absolute");

  // When an annotation specifies a preferredMode, use it — otherwise use radio state
  const effectiveMode: ViewMode = (preferredMode ?? mode) as ViewMode;
  const [hidden, setHidden] = useState<Set<string>>(new Set());

  // Which series to actually render
  const activeNames = useMemo(
    () => (visibleSeries ? seriesNames.filter((n) => visibleSeries.includes(n)) : seriesNames),
    [seriesNames, visibleSeries]
  );

  // Switch between absolute, YoY, and FY data based on effectiveMode
  const seriesData = useMemo(
    () => effectiveMode === "absolute" ? absoluteData
        : effectiveMode === "fy"       ? fyData
        :                                growthData,
    [effectiveMode, absoluteData, growthData, fyData]
  );

  // Proportional time axis: collect timestamps from current dataset
  const tsTicks = useMemo(
    () => (seriesData ?? []).map((p) => p._ts as number).filter((t) => typeof t === "number" && t > 0),
    [seriesData]
  );
  const tsDomain = useMemo(
    (): [number, number] =>
      tsTicks.length >= 2
        ? [tsTicks[0], tsTicks[tsTicks.length - 1]]
        : [0, 1],
    [tsTicks]
  );

  const legendItems = activeNames.map((name, i) => ({
    label:  name,
    color:  pickColor(name, i),
    active: !hidden.has(name),
  }));

  const toggleSeries = (name: string) =>
    setHidden((prev) => {
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });

  const formatY = (v: number) =>
    effectiveMode === "absolute" ? formatCr(v, 1) : `${v > 0 ? "+" : ""}${v.toFixed(1)}%`;

  // Custom tooltip — filters to highlighted series only when an annotation is active
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    const highlighted = highlightConfig?.highlight;
    const visible = highlighted?.length
      ? payload.filter((p: any) => highlighted.includes(p.dataKey))
      : payload;
    if (!visible.length) return null;
    return (
      <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-card)", borderRadius: 8, fontSize: 13, color: "var(--font)", padding: "10px 14px" }}>
        <p style={{ marginBottom: 4, fontWeight: 600 }}>
          {new Date(Number(label)).toLocaleDateString("en-IN", { month: "short", year: "numeric" })}
        </p>
        {visible.map((p: any) => (
          <p key={p.dataKey} style={{ color: p.color, margin: "2px 0" }}>
            {p.name}: {effectiveMode === "absolute" ? formatCr(Number(p.value) || 0) : formatGrowth(Number(p.value) || 0)}
          </p>
        ))}
      </div>
    );
  };

  const modeLabel: Record<ViewMode, string> = {
    absolute: "Absolute",
    yoy:      "YoY Growth",
    fy:       "FY Growth",
  };

  return (
    <div>
      {/* Mode toggle — hidden when annotation locks the mode */}
      <div className="flex flex-wrap gap-4 mb-3 text-sm">
        {preferredMode ? (
          <span style={{ color: "var(--font-muted)" }}>
            Showing: <strong style={{ color: "var(--font)" }}>{modeLabel[effectiveMode]}</strong>
          </span>
        ) : (
          <div className="flex items-center gap-3">
            {(["absolute", "yoy", "fy"] as ViewMode[]).map((m) => (
              <label key={m} className="flex items-center gap-1.5 cursor-pointer" style={{ color: "var(--font)" }}>
                <input
                  type="radio"
                  name={`mode-${activeNames[0] ?? "chart"}`}
                  value={m}
                  checked={effectiveMode === m}
                  onChange={() => setMode(m)}
                  className="accent-blue-500"
                />
                {modeLabel[m]}
              </label>
            ))}
          </div>
        )}
      </div>

      <ChartLegend items={legendItems} onToggle={toggleSeries} />

      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={seriesData} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" />
          <XAxis
            dataKey="_ts"
            type="number"
            domain={tsDomain}
            ticks={tsTicks}
            tickFormatter={(ts: number) =>
              new Date(ts).toLocaleDateString("en-IN", { month: "short", year: "numeric" })
            }
            tick={{ fontSize: 12, fill: "var(--font-muted)" }}
            tickLine={false}
          />
          <YAxis
            tickFormatter={formatY}
            tick={{ fontSize: 12, fill: "var(--font-muted)" }}
            tickLine={false}
            axisLine={false}
            width={96}
          />
          <Tooltip content={<CustomTooltip />} />
          {activeNames.map((name, i) => {
            if (hidden.has(name)) return null;
            const style = seriesStyle(name, highlightConfig);
            return (
              <Line
                key={name}
                type="monotone"
                dataKey={name}
                stroke={pickColor(name, i)}
                strokeWidth={style.strokeWidth}
                strokeDasharray={style.strokeDasharray}
                style={{ opacity: style.opacity }}
                dot={{ r: 4, strokeWidth: 1, opacity: style.opacity }}
                activeDot={{ r: 6 }}
                connectNulls={effectiveMode === "absolute"}
              />
            );
          })}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
