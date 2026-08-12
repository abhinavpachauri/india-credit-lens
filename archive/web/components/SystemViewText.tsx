"use client";

// ── SystemViewText ─────────────────────────────────────────────────────────────
// Always-visible text layer rendered below the graph canvas.
// Never gated — visible to all users and search-engine crawlers.
// Structured semantic HTML for indexability.

import {
  SUBSYSTEMS,
  NODE_MAP,
  NODE_STYLE,
  MODEL_META,
  type Subsystem,
  type NodeTier,
} from "@/lib/system_model_data";
import { ANNOTATIONS } from "@/lib/reports/rbi_sibc";

const OUTCOME_ICON: Record<string, string> = {
  opportunity: "✅",
  pressure:    "⚠️",
  gap:         "🔍",
};

const ALL_ANNOTATIONS = Object.values(ANNOTATIONS).flatMap((sec) => [
  ...sec.insights,
  ...sec.gaps,
  ...sec.opportunities,
]);

function findAnnotation(annotationIds: string[]) {
  for (const id of annotationIds) {
    const ann = ALL_ANNOTATIONS.find((a) => a.id === id);
    if (ann?.body) return ann;
  }
  return null;
}

function SubsystemBlock({ sub }: { sub: Subsystem }) {
  const driverNodes  = sub.drivers.map((id) => NODE_MAP[id]).filter(Boolean);
  const sectorNodes  = sub.sectors.map((id) => NODE_MAP[id]).filter(Boolean);
  const outcomeNodes = sub.outcomes.map((id) => NODE_MAP[id]).filter(Boolean);

  return (
    <section className="mb-10">
      {/* Subsystem heading */}
      <h3
        className="text-base font-semibold mb-3 pl-3"
        style={{ borderLeft: "3px solid #1E3A5F", color: "var(--font)" }}
      >
        {sub.label}
      </h3>

      {/* Driver context */}
      {driverNodes.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {driverNodes.map((d) => (
            <span
              key={d.id}
              className="text-xs px-3 py-1 rounded"
              style={{ background: NODE_STYLE.driver.bg, color: NODE_STYLE.driver.fg }}
            >
              {d.label}
            </span>
          ))}
        </div>
      )}

      {/* Sector stats */}
      {sectorNodes.length > 0 && (
        <div className="flex flex-wrap gap-4 mb-4">
          {sectorNodes.map((s) => (
            <div key={s.id}>
              <span
                className="text-lg font-bold"
                style={{ color: NODE_STYLE.sector.fg }}
              >
                {s.stat ?? ""}
              </span>
              <span
                className="text-sm ml-2"
                style={{ color: "var(--font-muted)" }}
              >
                {s.label}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Outcome nodes */}
      {outcomeNodes.length > 0 && (
        <div className="flex flex-col gap-3">
          {outcomeNodes.map((o) => {
            const tier      = (o.tier ?? "gap") as NodeTier;
            const icon      = OUTCOME_ICON[tier] ?? "•";
            const style     = NODE_STYLE[tier];
            const ann       = findAnnotation(o.annotation_ids ?? []);
            const bodyText  = ann?.body ?? o.description ?? "";
            const implText  = ann?.implication ?? "";
            return (
              <div
                key={o.id}
                className="pl-4 py-3 text-sm"
                style={{
                  borderLeft: `3px solid ${style.border}`,
                  background: "var(--bg-card)",
                }}
              >
                <div
                  className="font-semibold mb-1"
                  style={{ color: style.fg === "#ffffff" ? "var(--font)" : style.fg }}
                >
                  {icon} {o.label}
                </div>
                {bodyText && (
                  <p className="leading-relaxed" style={{ color: "var(--font-muted)" }}>
                    {bodyText}
                  </p>
                )}
                {implText && (
                  <p
                    className="mt-1 italic text-xs leading-relaxed"
                    style={{ color: "var(--font-muted)" }}
                  >
                    {implText}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

export default function SystemViewText() {
  return (
    <div className="mt-10 pt-8" style={{ borderTop: "1px solid var(--border-card)" }}>
      <h2
        className="text-xs font-semibold uppercase tracking-widest mb-6"
        style={{ color: "var(--font-muted)" }}
      >
        {MODEL_META.period} · {SUBSYSTEMS.length} causal stories ·{" "}
        {MODEL_META.report_name}
      </h2>

      {SUBSYSTEMS.map((sub) => (
        <SubsystemBlock key={sub.id} sub={sub} />
      ))}
    </div>
  );
}
