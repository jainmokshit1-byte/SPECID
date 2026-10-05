// Theme and stage mode (UI/UX brief 2): light by default, dark by choice or by the system, and
// "stage mode" for projectors (root font 115 %). Stored per browser; `?stage=1` turns stage on.

import { useCallback, useEffect, useState } from "react";

export type ThemePref = "light" | "dark" | "system";

const THEME_KEY = "specid.theme";
const STAGE_KEY = "specid.stage";

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // private window or blocked storage: the setting lasts for this page only
  }
}

function systemDark(): boolean {
  return (
    typeof window !== "undefined" && !!window.matchMedia?.("(prefers-color-scheme: dark)").matches
  );
}

export function applyAppearance(theme: ThemePref, stage: boolean): void {
  const root = document.documentElement;
  const dark = theme === "dark" || (theme === "system" && systemDark());
  root.classList.toggle("dark", dark);
  root.classList.toggle("stage", stage);
}

export function initialTheme(): ThemePref {
  const v = read(THEME_KEY);
  return v === "dark" || v === "system" ? v : "light";
}

export function initialStage(): boolean {
  if (
    typeof window !== "undefined" &&
    new URLSearchParams(window.location.search).get("stage") === "1"
  )
    return true;
  return read(STAGE_KEY) === "1";
}

/** Current appearance and setters; applies the classes on <html>. */
export function useAppearance() {
  const [theme, setThemeState] = useState<ThemePref>(initialTheme);
  const [stage, setStageState] = useState<boolean>(initialStage);

  useEffect(() => {
    applyAppearance(theme, stage);
    if (theme !== "system" || !window.matchMedia) return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => applyAppearance(theme, stage);
    mq.addEventListener?.("change", onChange);
    return () => mq.removeEventListener?.("change", onChange);
  }, [theme, stage]);

  const setTheme = useCallback((t: ThemePref) => {
    write(THEME_KEY, t);
    setThemeState(t);
  }, []);
  const setStage = useCallback((s: boolean) => {
    write(STAGE_KEY, s ? "1" : "0");
    setStageState(s);
  }, []);
  return { theme, setTheme, stage, setStage };
}
