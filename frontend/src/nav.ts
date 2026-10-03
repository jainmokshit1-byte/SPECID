// Sidebar model, 03 App Flow v1.2 section 3.1: five task items + Rules + Help, related screens
// are tabs inside an item. Pure data and functions so navigation rules can be tested with fixtures.
// Role filtering (App Flow 3.2) is added with auth in Phase 3. P1 screens (S14, S15, S19) get
// their tab when they are built.

import { matchRoutes } from "react-router-dom";
import { BUILT_PATHS, SHELL_ROUTES } from "./routes";

export type NavItemId = "home" | "data" | "review" | "registry" | "results" | "rules" | "help";

export interface NavTab {
  label: string;
  path: string;
  /** Other route patterns that belong to this tab (detail pages). */
  also?: string[];
}

export interface NavItem {
  id: NavItemId;
  label: string;
  tabs: NavTab[];
  /** Rules and Help sit at the bottom of the sidebar. */
  bottom?: boolean;
}

export const NAV_ITEMS: NavItem[] = [
  { id: "home", label: "Home", tabs: [{ label: "Home", path: "/" }] },
  {
    id: "data",
    label: "Data",
    tabs: [
      { label: "Upload", path: "/upload", also: ["/batches/:batchId/quality"] },
      { label: "Matching runs", path: "/runs", also: ["/runs/new", "/runs/:runId"] },
    ],
  },
  {
    id: "review",
    label: "Review",
    tabs: [
      { label: "To review", path: "/review", also: ["/clusters/:clusterId", "/pairs/:pairId"] },
      { label: "Consents", path: "/consents" },
      { label: "Look-alikes", path: "/lookalikes" },
    ],
  },
  {
    id: "registry",
    label: "Registry",
    tabs: [
      { label: "Codes", path: "/registry", also: ["/registry/:cnmc"] },
      { label: "Search", path: "/search" },
      { label: "Exports", path: "/exports" },
    ],
  },
  {
    id: "results",
    label: "Results",
    tabs: [{ label: "Evaluation", path: "/evaluation", also: ["/evaluation/:evalId"] }],
  },
  {
    id: "rules",
    label: "Rules",
    bottom: true,
    tabs: [
      { label: "Rulebook", path: "/templates", also: ["/templates/:templateId"] },
      { label: "Audit", path: "/audit" },
      { label: "Users", path: "/admin/users" },
    ],
  },
  { id: "help", label: "Help", bottom: true, tabs: [{ label: "About", path: "/about" }] },
];

export interface VisibleTab extends NavTab {
  built: boolean;
}

export interface VisibleItem extends Omit<NavItem, "tabs"> {
  tabs: VisibleTab[];
}

/** Items and tabs to show. Unbuilt screens are hidden unless the developer switch is on. */
export function visibleNav(
  showUnbuilt: boolean,
  items: NavItem[] = NAV_ITEMS,
  built: ReadonlySet<string> = BUILT_PATHS,
): VisibleItem[] {
  return items
    .map((item) => ({
      ...item,
      tabs: item.tabs
        .map((t) => ({ ...t, built: built.has(t.path) }))
        .filter((t) => t.built || showUnbuilt),
    }))
    .filter((item) => item.tabs.length > 0);
}

/** Route pattern of a concrete URL path, ranked like the router (`/runs/new` before `/runs/:runId`). */
export function routePatternOf(pathname: string): string | null {
  const m = matchRoutes(
    SHELL_ROUTES.map((r) => ({ path: r.path })),
    pathname,
  );
  return m?.[0]?.route.path ?? null;
}

/** The item and tab a route pattern belongs to, if any. */
export function navLocation(
  pattern: string | null,
  items: NavItem[] = NAV_ITEMS,
): { item: NavItem; tab: NavTab } | null {
  if (pattern === null) return null;
  for (const item of items)
    for (const tab of item.tabs)
      if (tab.path === pattern || tab.also?.includes(pattern)) return { item, tab };
  return null;
}
