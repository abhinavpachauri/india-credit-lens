"use client";

// ── EmailGate ──────────────────────────────────────────────────────────────────
// Overlay modal rendered on top of the Cytoscape canvas.
// Dismissed permanently (localStorage) once user submits email.
// Email submits to Substack subscribe endpoint.

interface Props {
  onUnlocked: () => void;
}

const SUBSTACK_URL = "https://indiacreditlens.substack.com";

export default function EmailGate({ onUnlocked }: Props) {
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form  = e.currentTarget;
    const email = (form.elements.namedItem("email") as HTMLInputElement).value.trim();
    if (!email) return;

    // Open Substack subscribe page — Substack doesn't support direct API subscribe
    // from third-party domains without their embed widget.
    // We open in new tab and mark locally as unlocked.
    window.open(`${SUBSTACK_URL}?email=${encodeURIComponent(email)}`, "_blank");
    localStorage.setItem("icl-graph-unlocked", "true");
    onUnlocked();
  };

  return (
    <div
      className="absolute inset-0 flex items-center justify-center z-10"
      style={{
        background:   "rgba(0,0,0,0.55)",
        backdropFilter: "blur(3px)",
        borderRadius: "6px",
      }}
    >
      <div
        className="mx-4 p-8 rounded-lg max-w-sm w-full text-center"
        style={{ background: "var(--bg-card)", border: "1px solid var(--border-card)" }}
      >
        <div className="text-2xl mb-3">🕸️</div>
        <h3
          className="font-semibold text-base mb-2"
          style={{ color: "var(--font)" }}
        >
          Explore the full system
        </h3>
        <p
          className="text-sm mb-5 leading-relaxed"
          style={{ color: "var(--font-muted)" }}
        >
          Hover nodes, filter by tier, follow causal chains across all{" "}
          {/* node count from model */}
          30 nodes. Free — via Substack.
        </p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <input
            name="email"
            type="email"
            required
            placeholder="you@company.com"
            className="w-full px-4 py-2 rounded text-sm"
            style={{
              background:  "var(--bg-page)",
              border:      "1px solid var(--border-card)",
              color:       "var(--font)",
              outline:     "none",
            }}
          />
          <button
            type="submit"
            className="w-full py-2 rounded text-sm font-semibold"
            style={{ background: "#1E3A5F", color: "#ffffff" }}
          >
            Explore →
          </button>
        </form>

        <p
          className="text-xs mt-4"
          style={{ color: "var(--font-muted)" }}
        >
          Free. No spam. Unsubscribe anytime.
        </p>
      </div>
    </div>
  );
}
