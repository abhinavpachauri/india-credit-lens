// ── Runtime Report Validator ──────────────────────────────────────────────────
// Catches content errors that TypeScript can't — e.g. annotation referencing
// a series name that doesn't exist in the section's seriesNames array.
// Call validateReport() in development; safe no-op in production.

import type { Report } from "@/lib/types";

export function validateReport(report: Report): string[] {
  const errors: string[] = [];

  report.sections.forEach((section) => {
    const validSeries = new Set(section.seriesNames);

    if (section.absoluteData.length === 0)
      errors.push(`[${section.id}] absoluteData is empty`);

    if (section.seriesNames.length === 0)
      errors.push(`[${section.id}] seriesNames is empty`);

    const allAnnotations = [
      ...section.annotations.insights,
      ...section.annotations.gaps,
      ...section.annotations.opportunities,
    ];

    allAnnotations.forEach((ann) => {
      const refs = [
        ...(ann.effect.highlight ?? []),
        ...(ann.effect.dim       ?? []),
        ...(ann.effect.dash      ?? []),
        ...(ann.effect.referenceDot ? [ann.effect.referenceDot.series] : []),
      ];

      refs.forEach((name) => {
        if (!validSeries.has(name))
          errors.push(
            `[${section.id}/${ann.id}] effect references unknown series: "${name}"`
          );
      });
    });
  });

  return errors;
}

/** Call in dev — logs errors and returns boolean. No-op in production. */
export function devValidate(report: Report): boolean {
  if (process.env.NODE_ENV !== "development") return true;
  const errors = validateReport(report);
  if (errors.length > 0) {
    console.warn(`[India Credit Lens] Report validation — ${errors.length} issue(s):`);
    errors.forEach((e) => console.warn("  •", e));
    return false;
  }
  return true;
}
