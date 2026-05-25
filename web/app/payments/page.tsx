"use client";

import { useEffect, useState } from "react";
import { loadAtmPosData } from "@/lib/atm_pos_data";
import type { AtmPosRow } from "@/lib/atm_pos_data";
import Header            from "@/components/Header";
import AtmPosGroupSection from "@/components/AtmPosGroupSection";
import NewsletterCTA      from "@/components/NewsletterCTA";

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

        {/* Newsletter CTA — top */}
        <div className="mb-8">
          <NewsletterCTA variant="banner" />
        </div>

        {GROUPS.map((group) => (
          <AtmPosGroupSection key={group} group={group} rows={rows} />
        ))}

        {/* Newsletter CTA — bottom */}
        <div className="mt-10 mb-2">
          <NewsletterCTA variant="banner" />
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
