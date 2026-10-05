// Sidebar model, 03 App Flow v1.2 section 3.1: five task items + Rules + Help, related screens
// are tabs inside an item. Pure data and functions so navigation rules can be tested with fixtures.
// Tabs carry the roles of App Flow 3.2 (sidebar visibility by role). P1 screens (S14, S15, S19)
// get their tab when they are built.

import { matchRoutes } from "react-router-dom";
import { BUILT_PATHS, type Role, SHELL_ROUTES } from "./routes";

export type NavItemId = "home" | "data" | "review" | "registry" | "results" | "rules" | "help";

export interface NavTab {
  label: string;
  path: string;
  /** Other route patterns that belong to this tab (detail pages). */
  also?: string[];
  /** Roles that see this tab (App Flow 3.2). */
  roles: readonly Role[];
}

export interface NavItem {
  id: NavItemId;
  label: string;
  tabs: NavTab[];
  /** Rules and Help sit at the bottom of the sidebar. */
  bottom?: boolean;
}

const ALL: Role[] = ["MAKER", "CHECKER", "ADMIN", "AUDITOR", "INTEGRATOR"];
const MCA: Role[] = ["MAKER", "CHECKER", "ADMIN"];
const MCAA: Role[] = ["MAKER", "CHECKER", "ADMIN", "AUDITOR"];

export const NAV_ITEMS: NavItem[] = [
  { id: "home", label: "Home", tabs: [{ label: "Home", path: "/", roles: MCAA }] },
  {
    id: "data",
    label: "Data",
    tabs: [
      { label: "Upload", path: "/upload", also: ["/batches/:batchId/quality"], roles: MCA },
      { label: "Matching runs", path: "/runs", also: ["/runs/new", "/runs/:runId"], roles: MCA },
    ],
  },
  {
    id: "review",
    label: "Review",
    tabs: [
      {
        label: "To review",
        path: "/review",
        also: ["/clusters/:clusterId", "/pairs/:pairId"],
        roles: ["MAKER", "CHECKER"],
      },
      { label: "Consents", path: "/consents", roles: ["CHECKER"] },
      { label: "Look-alikes", path: "/lookalikes", roles: MCAA },
    ],
  },
  {
    id: "registry",
    label: "Registry",
    tabs: [
      { label: "Codes", path: "/registry", also: ["/registry/:cnmc"], roles: ALL },
      { label: "Search", path: "/search", roles: ["MAKER", "CHECKER", "ADMIN", "INTEGRATOR"] },
      { label: "Exports", path: "/exports", roles: MCA },
      { label: "Change notices", path: "/notices", roles: ["MAKER", "CHECKER", "INTEGRATOR"] },
    ],
  },
  {
    id: "results",
    label: "Results",
    tabs: [
      { label: "Evaluation", path: "/evaluation", also: ["/evaluation/:evalId"], roles: MCAA },
    ],
  },
  {
    id: "rules",
    label: "Rules",
    bottom: true,
    tabs: [
      { label: "Rulebook", path: "/templates", also: ["/templates/:templateId"], roles: MCAA },
      { label: "Audit", path: "/audit", roles: ["ADMIN", "AUDITOR"] },
      { label: "Users", path: "/admin/users", roles: ["ADMIN"] },
    ],
  },
  {
    id: "help",
    label: "Help",
    bottom: true,
    tabs: [{ label: "About", path: "/about", roles: ALL }],
  },
];

export interface VisibleTab extends NavTab {
  built: boolean;
}

export interface VisibleItem extends Omit<NavItem, "tabs"> {
  tabs: VisibleTab[];
}

/** Items and tabs to show: only tabs the role may see (App Flow 3.2); unbuilt screens are hidden
 * unless the developer switch is on. */
export function visibleNav(
  showUnbuilt: boolean,
  role: Role,
  items: NavItem[] = NAV_ITEMS,
  built: ReadonlySet<string> = BUILT_PATHS,
): VisibleItem[] {
  return items
    .map((item) => ({
      ...item,
      tabs: item.tabs
        .map((t) => ({ ...t, built: built.has(t.path) }))
        .filter((t) => t.roles.includes(role) && (t.built || showUnbuilt)),
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
