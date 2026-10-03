import { useLocation } from "react-router-dom";

const KEY = "specid.showUnbuilt";

/** Developer-only switch that lists unbuilt screens in navigation, marked "dev" (docs/DECISIONS.md
 * DEC-10). On with `?dev=1` (kept for the browser tab; `?dev=0` turns it off) or
 * `VITE_SHOW_UNBUILT=true`. Both work only in the Vite dev server and tests: in a production build
 * (`npm run build`, the demo image) `import.meta.env.DEV` is false and this always returns false. */
export function useShowUnbuilt(): boolean {
  const { search } = useLocation();
  if (!import.meta.env.DEV) return false;
  if (import.meta.env.VITE_SHOW_UNBUILT === "true") return true;
  const dev = new URLSearchParams(search).get("dev");
  try {
    if (dev === "1") sessionStorage.setItem(KEY, "1");
    else if (dev === "0") sessionStorage.removeItem(KEY);
    return sessionStorage.getItem(KEY) === "1";
  } catch {
    return dev === "1";
  }
}
