"use client";

// The page-level Read ⇄ Explore switch (DASHBOARD_SPEC.md §11). Read is the curated three-tier
// view; Explore is the full dashboard, unchanged. A lens toggle, not a fork — both read the same
// data. Sticky via the caller's usePersistent.

export default function ModeToggle({
  mode, setMode,
}: { mode: "read" | "explore"; setMode: (m: "read" | "explore") => void }) {
  return (
    <div
      className="inline-flex rounded-full p-0.5 mb-5"
      style={{ background: "var(--bg-card)", border: "1px solid var(--border-card)" }}
      role="tablist"
      aria-label="Dashboard mode"
    >
      {(["read", "explore"] as const).map((m) => (
        <button
          key={m}
          role="tab"
          aria-selected={mode === m}
          onClick={() => setMode(m)}
          className="text-sm font-medium px-4 py-1.5 rounded-full transition-colors"
          style={{
            background: mode === m ? "#4e8ef7" : "transparent",
            color: mode === m ? "#fff" : "var(--font-muted)",
          }}
        >
          {m === "read" ? "Read" : "Explore"}
        </button>
      ))}
    </div>
  );
}
