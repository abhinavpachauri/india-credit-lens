"use client";

import { useEffect, useState } from "react";
import { loadAtmPosData }    from "@/lib/atm_pos_data";
import { useAppShell }       from "@/components/AppShell";
import AtmPosGroupSection    from "@/components/AtmPosGroupSection";
import NewsletterCTA         from "@/components/NewsletterCTA";
import type { AtmPosSeries }   from "@/lib/atm_pos_data";

const GROUPS = ["cc", "dc", "infra"] as const;

export default function PaymentsPage() {
  const { setHeaderMetric } = useAppShell();
  const [rows, setRows]     = useState<AtmPosSeries | null>(null);

  useEffect(() => {
    setHeaderMetric(null, "Mar 2026");
    loadAtmPosData().then(setRows);
  }, [setHeaderMetric]);

  if (!rows) {
    return (
      <div
        className="flex items-center justify-center min-h-[60vh] text-sm"
        style={{ color: "var(--font-muted)" }}
      >
        Loading data…
      </div>
    );
  }

  return (
    <main className="max-w-6xl mx-auto px-3 sm:px-4 py-6">
      {GROUPS.map((group) => (
        <AtmPosGroupSection key={group} group={group} rows={rows} />
      ))}

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
  );
}
