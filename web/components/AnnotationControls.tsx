"use client";

import type { LensType, AnnotationState } from "@/hooks/useAnnotation";

const LENS_CONFIG: Record<LensType, { label: string; color: string; bg: string }> = {
  insights:      { label: "Insights",     color: "#2563EB", bg: "#EFF6FF" },
  gaps:          { label: "Gaps",         color: "#D97706", bg: "#FFFBEB" },
  opportunities: { label: "Opportunities", color: "#16A34A", bg: "#F0FDF4" },
};

interface AnnotationControlsProps {
  counts:     AnnotationState["counts"];
  activeLens: AnnotationState["activeLens"];
  setLens:    AnnotationState["setLens"];
}

export default function AnnotationControls({
  counts, activeLens, setLens,
}: AnnotationControlsProps) {
  const lenses = (Object.keys(LENS_CONFIG) as LensType[]).filter(
    (l) => counts[l] > 0
  );

  if (lenses.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 mb-3">
      {lenses.map((lens) => {
        const { label, color, bg } = LENS_CONFIG[lens];
        const isActive = activeLens === lens;

        return (
          <button
            key={lens}
            onClick={() => setLens(lens)}
            className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-all"
            style={{
              background:  isActive ? color : bg,
              color:       isActive ? "#fff" : color,
              border:      `1px solid ${color}`,
              opacity:     1,
            }}
          >
            <span
              className="inline-block w-2 h-2 rounded-full"
              style={{ background: isActive ? "#fff" : color }}
            />
            {label} · {counts[lens]}
          </button>
        );
      })}
    </div>
  );
}
