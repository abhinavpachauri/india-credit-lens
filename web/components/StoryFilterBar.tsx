"use client";

// ── StoryFilterBar ─────────────────────────────────────────────────────────────
// Subsystem preset filter buttons.
// "All" clears the filter; individual story buttons highlight that subsystem
// in the Cytoscape graph and show the contextual Substack CTA.

import { SUBSYSTEMS } from "@/lib/system_model_data";

interface Props {
  active:   string | null;  // subsystem id or null (= all)
  onChange: (id: string | null) => void;
}

export default function StoryFilterBar({ active, onChange }: Props) {
  const btnBase = "px-3 py-1.5 text-xs font-medium rounded transition-colors whitespace-nowrap";

  return (
    <div className="flex flex-wrap gap-2 mb-4">
      {/* All button */}
      <button
        onClick={() => onChange(null)}
        className={btnBase}
        style={{
          background:  active === null ? "#1E3A5F" : "var(--bg-card)",
          color:       active === null ? "#ffffff"  : "var(--font-muted)",
          border:      `1px solid ${active === null ? "#1E3A5F" : "var(--border-card)"}`,
        }}
      >
        All stories
      </button>

      {/* One button per subsystem */}
      {SUBSYSTEMS.map((sub) => {
        const isActive = active === sub.id;
        return (
          <button
            key={sub.id}
            onClick={() => onChange(isActive ? null : sub.id)}
            className={btnBase}
            style={{
              background: isActive ? "#0F766E"          : "var(--bg-card)",
              color:      isActive ? "#ffffff"           : "var(--font-muted)",
              border:     `1px solid ${isActive ? "#0F766E" : "var(--border-card)"}`,
            }}
          >
            {sub.label}
            {sub.newsletter && (
              <span
                className="ml-1.5 text-xs opacity-70"
                title="Featured in newsletter"
              >
                ✉
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
