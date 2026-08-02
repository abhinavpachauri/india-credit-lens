"use client";

// A piece of UI state that survives across visits — localStorage-backed, same pattern as the
// AppShell's `icl-dark`. Used for read-mode's sticky page mode and depth ladder (decision 2).
import { useEffect, useState } from "react";

export function usePersistent<T>(key: string, initial: T): [T, (v: T) => void] {
  const [value, setValue] = useState<T>(initial);

  // Read once on mount (client only — SSR has no localStorage).
  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(key);
      if (raw != null) setValue(JSON.parse(raw) as T);
    } catch {
      /* ignore malformed / unavailable storage */
    }
  }, [key]);

  const set = (v: T) => {
    setValue(v);
    try {
      window.localStorage.setItem(key, JSON.stringify(v));
    } catch {
      /* ignore quota / unavailable storage */
    }
  };

  return [value, set];
}
