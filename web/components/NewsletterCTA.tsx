"use client";

// ── NewsletterCTA ──────────────────────────────────────────────────────────────
// Single-tap Substack subscribe link. No iframe, no form.
// variant="banner"  — full-width strip (between sections, page top/bottom)
// variant="inline"  — compact card-width strip (below a chart)

const SUBSCRIBE_URL = "https://indiacreditlens.substack.com/subscribe";

interface NewsletterCTAProps {
  variant?: "banner" | "inline";
}

export default function NewsletterCTA({ variant = "banner" }: NewsletterCTAProps) {
  if (variant === "inline") {
    return (
      <div
        className="flex items-center justify-between gap-3 px-4 py-3 rounded-lg text-sm mt-3"
        style={{ background: "var(--bg-card)", border: "1px solid var(--border-card)" }}
      >
        <p style={{ color: "var(--font-muted)" }}>
          <span className="mr-1">📬</span>
          Monthly digest — what moved in Indian credit and why
        </p>
        <a
          href={SUBSCRIBE_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs font-semibold whitespace-nowrap px-3 py-1.5 rounded-full flex-shrink-0"
          style={{ background: "#4e8ef7", color: "#fff", textDecoration: "none" }}
        >
          Get it free →
        </a>
      </div>
    );
  }

  // banner
  return (
    <div
      className="w-full flex flex-col sm:flex-row items-center justify-between gap-4 px-6 py-5 rounded-xl"
      style={{
        background:   "var(--bg-card)",
        border:       "1px solid var(--border-card)",
        borderLeft:   "4px solid #4e8ef7",
      }}
    >
      <div className="text-center sm:text-left">
        <p className="text-sm font-semibold" style={{ color: "var(--font)" }}>
          India Credit Intelligence — monthly, free
        </p>
        <p className="text-sm mt-0.5" style={{ color: "var(--font-muted)" }}>
          Credit supply shifts, payment trends, and what it means for lenders — straight to your inbox
        </p>
      </div>
      <a
        href={SUBSCRIBE_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="text-sm font-semibold px-5 py-2.5 rounded-full whitespace-nowrap flex-shrink-0 transition-opacity hover:opacity-90"
        style={{ background: "#4e8ef7", color: "#fff", textDecoration: "none" }}
      >
        Get it free →
      </a>
    </div>
  );
}
