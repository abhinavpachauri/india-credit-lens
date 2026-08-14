/**
 * Single switch for the Layer 2 (deeper reading) access gate.
 *
 * It used to hide a whole route. It now hides the DEEP RUNG of the depth ladder, which is a
 * better seam in both directions: the reader reaches the subject they already care about and
 * finds another layer of it, rather than being told about a section they cannot open — and the
 * gate follows the architecture's own L1/L2/L3 depth rather than a URL invented for it.
 *
 * Default (unset) → OPEN (public). Decided 2026-06-13: at <10 visitors/day, gating content
 * works against the reach/positioning goal.
 *
 * To gate later (a paid tier): set `NEXT_PUBLIC_GATE_OPPORTUNITIES=true` (web/.env.local, or a
 * Vercel env var) and restart. NEXT_PUBLIC_* is read at build/start, so a restart is required.
 */
export const OPPORTUNITIES_GATED =
  process.env.NEXT_PUBLIC_GATE_OPPORTUNITIES === "true";
