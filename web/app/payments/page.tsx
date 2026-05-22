"use client";

import { useEffect, useState } from "react";
import { loadAtmPosData } from "@/lib/atm_pos_data";
import type { AtmPosRow } from "@/lib/atm_pos_data";
import Header            from "@/components/Header";
import AtmPosGroupSection from "@/components/AtmPosGroupSection";

const GROUPS = ["cc", "dc", "infra"] as const;

export default function PaymentsPage() {
  const [rows, setRows] = useState<AtmPosRow[] | null>(null);
  const [dark, setDark] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem("icl-dark");
    if (saved === "true") setDark(true);
  }, []);

  const toggleDark = () =>
    setDark((d) => {
      localStorage.setItem("icl-dark", String(!d));
      return !d;
    });

  useEffect(() => {
    loadAtmPosData().then(setRows);
  }, []);

  if (!rows) {
    return (
      <div
        data-dark={dark}
        className="flex items-center justify-center min-h-screen text-sm"
        style={{ background: "var(--bg-page)", color: "var(--font-muted)" }}
      >
        Loading data…
      </div>
    );
  }

  return (
    <div data-dark={dark} style={{ background: "var(--bg-page)", minHeight: "100vh" }}>
      <Header
        totalBankCredit={null}
        latestDate="Mar 2026"
        darkMode={dark}
        onToggleDark={toggleDark}
      />

      <main className="max-w-6xl mx-auto px-3 sm:px-4 py-6">

        {/* Substack CTA — top */}
        <div className="mb-8 flex flex-col items-center gap-2">
          <p className="text-sm font-medium" style={{ color: "var(--font-muted)" }}>
            Monthly credit intelligence, free — get it in your inbox
          </p>
          <iframe
            src="https://indiacreditlens.substack.com/embed"
            width="100%"
            height="320"
            style={{
              maxWidth:     "480px",
              border:       "1px solid #EEE",
              background:   "white",
              borderRadius: "0.5rem",
            }}
            frameBorder={0}
            scrolling="no"
          />
        </div>

        {GROUPS.map((group) => (
          <AtmPosGroupSection key={group} group={group} rows={rows} />
        ))}

        {/* Substack CTA — bottom */}
        <div className="mt-10 mb-2 flex flex-col items-center gap-2">
          <p className="text-sm font-medium" style={{ color: "var(--font-muted)" }}>
            Enjoyed the data? Get the analysis behind it in your inbox
          </p>
          <iframe
            src="https://indiacreditlens.substack.com/embed"
            width="100%"
            height="320"
            style={{
              maxWidth:     "480px",
              border:       "1px solid #EEE",
              background:   "white",
              borderRadius: "0.5rem",
            }}
            frameBorder={0}
            scrolling="no"
          />
        </div>

        <footer
          className="mt-6 pb-8 text-center text-xs"
          style={{ color: "var(--font-muted)" }}
        >
          Source: Reserve Bank of India · ATM / POS Card Statistics · Latest: Mar 2026
        </footer>
      </main>
    </div>
  );
}
