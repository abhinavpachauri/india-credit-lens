"use client";

import type { LensType, AnnotationState } from "@/hooks/useAnnotation";

const LENS_CONFIG: Record<LensType, { label: string; color: string; bg: string }> = {
  insights:      { label: "Insights",      color: "#2563EB", bg: "#EFF6FF" },
  gaps:          { label: "Gaps",          color: "#D97706", bg: "#FFFBEB" },
  opportunities: { label: "Opportunities", color: "#16A34A", bg: "#F0FDF4" },
};

interface AnnotationControlsProps {
  counts:     AnnotationState["counts"];
  activeLens: AnnotationState["activeLens"];
  setLens:    AnnotationState["setLens"];
  onExplore:  () => void;
}

export default function AnnotationControls({
  counts, activeLens, setLens, onExplore,
}: AnnotationControlsProps) {
  const lenses = (Object.keys(LENS_CONFIG) as LensType[]).filter(
    (l) => counts[l] > 0
  );

  if (lenses.length === 0) return null;

  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex flex-wrap gap-2">
        {lenses.map((lens) => {
          const { label, color, bg } = LENS_CONFIG[lens];
          const isActive = activeLens === lens;

          return (
            <button
              key={lens}
              onClick={() => setLens(lens)}
              className="px-3 py-1.5 rounded-full text-xs font-semibold transition-all"
              style={{
                background:  isActive ? color : bg,
                color:       isActive ? "#fff" : color,
                border:      `1.5px solid ${color}`,
                cursor:      "pointer",
              }}
            >
              {label} {counts[lens]}
            </button>
          );
        })}
      </div>

      {activeLens ? (
        <button
          onClick={onExplore}
          className="text-xs ml-3 whitespace-nowrap shrink-0 px-3 py-1.5 rounded-full font-medium"
          style={{
            color:      "var(--font)",
            border:     "1.5px solid var(--border-card)",
            background: "var(--bg-card)",
            cursor:     "pointer",
          }}
        >
          Explore data ↗
        </button>
      ) : (
        <span
          className="text-xs ml-3 whitespace-nowrap shrink-0"
          style={{ color: "var(--font-muted)" }}
        >
          ← tap to analyse
        </span>
      )}
    </div>
  );
}
