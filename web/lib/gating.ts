/**
 * Single switch for the /opportunities access gate.
 *
 * Default (unset) → OPEN (public). Decided 2026-06-13: at <10 visitors/day, gating
 * content works against the reach/positioning goal, so /opportunities is public for now.
 *
 * To RE-GATE later (e.g. once there's a paid tier / traction): set
 * `NEXT_PUBLIC_GATE_OPPORTUNITIES=true` (in web/.env.local for local, or a Vercel env
 * var for prod) and restart. All Clerk wiring (proxy.ts, Header, OpportunityTeaser) is
 * preserved and reads this flag — nothing to re-add.
 * Note: NEXT_PUBLIC_* vars are read at build/start, so restart after changing it.
 */
export const OPPORTUNITIES_GATED =
  process.env.NEXT_PUBLIC_GATE_OPPORTUNITIES === "true";
