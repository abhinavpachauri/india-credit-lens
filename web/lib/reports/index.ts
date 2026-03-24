// ── Report Registry ───────────────────────────────────────────────────────────
// Every report must be registered here.
// The type of REPORTS enforces that every entry satisfies the Report contract.

import { loadReport as loadRbiSibc } from "./rbi_sibc";
import type { Report } from "@/lib/types";

export const REPORTS: Record<string, () => Promise<Report>> = {
  rbi_sibc: loadRbiSibc,
  // crif_women:  loadCrifWomen,   ← add next report here
  // sidbi_msme:  loadSidbiMsme,
};
