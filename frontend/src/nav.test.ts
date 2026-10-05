import { BUILT_PATHS } from "./routes";
import { describe, expect, it } from "vitest";
import { NAV_ITEMS, type NavItem, navLocation, routePatternOf, visibleNav } from "./nav";
import { type Role, SHELL_ROUTES } from "./routes";

const ALL: Role[] = ["MAKER", "CHECKER", "ADMIN", "AUDITOR", "INTEGRATOR"];

const FIXTURE: NavItem[] = [
  { id: "home", label: "Home", tabs: [{ label: "Home", path: "/", roles: ALL }] },
  {
    id: "review",
    label: "Review",
    tabs: [
      { label: "To review", path: "/review", roles: ["MAKER", "CHECKER"] },
      { label: "Consents", path: "/consents", roles: ["CHECKER"] },
    ],
  },
  {
    id: "help",
    label: "Help",
    bottom: true,
    tabs: [{ label: "About", path: "/about", roles: ALL }],
  },
];

describe("nav model (App Flow 3.1)", () => {
  it("has five task items, then Rules and Help at the bottom", () => {
    expect(NAV_ITEMS.map((i) => i.label)).toEqual([
      "Home",
      "Data",
      "Review",
      "Registry",
      "Results",
      "Rules",
      "Help",
    ]);
    expect(NAV_ITEMS.filter((i) => i.bottom).map((i) => i.label)).toEqual(["Rules", "Help"]);
  });

  it("every tab points at defined routes", () => {
    const paths = new Set(SHELL_ROUTES.map((r) => r.path));
    for (const item of NAV_ITEMS)
      for (const tab of item.tabs)
        for (const p of [tab.path, ...(tab.also ?? [])]) expect(paths).toContain(p);
  });

  it("every P0 route belongs to exactly one tab; P1 screens get theirs when built", () => {
    for (const r of SHELL_ROUTES) {
      const owners = NAV_ITEMS.flatMap((i) => i.tabs).filter(
        (t) => t.path === r.path || t.also?.includes(r.path),
      );
      expect(owners, r.path).toHaveLength(r.pri === "P0" || BUILT_PATHS.has(r.path) ? 1 : 0);
    }
  });
});

describe("visibleNav", () => {
  it("hides unbuilt tabs, and items left with no tab", () => {
    const v = visibleNav(false, "CHECKER", FIXTURE, new Set(["/", "/consents"]));
    expect(v.map((i) => i.label)).toEqual(["Home", "Review"]);
    expect(v[1]!.tabs.map((t) => t.label)).toEqual(["Consents"]);
  });

  it("developer switch shows everything and marks unbuilt tabs", () => {
    const v = visibleNav(true, "CHECKER", FIXTURE, new Set(["/"]));
    expect(v.map((i) => i.label)).toEqual(["Home", "Review", "Help"]);
    expect(v[1]!.tabs.map((t) => t.built)).toEqual([false, false]);
    expect(v[0]!.tabs[0]!.built).toBe(true);
  });

  it("never exceeds seven items", () => {
    for (const role of ALL) expect(visibleNav(true, role).length).toBeLessThanOrEqual(7);
  });
});

describe("routePatternOf / navLocation", () => {
  it.each([
    ["/", "/", "home"],
    ["/runs/new", "/runs/new", "data"],
    ["/runs/4F2A", "/runs/:runId", "data"],
    ["/clusters/7", "/clusters/:clusterId", "review"],
    ["/registry/NMC-00000001974", "/registry/:cnmc", "registry"],
    ["/admin/users", "/admin/users", "rules"],
  ])("%s → %s in %s", (url, pattern, item) => {
    expect(routePatternOf(url)).toBe(pattern);
    expect(navLocation(pattern)?.item.id).toBe(item);
  });

  it("unknown URL has no pattern and no item", () => {
    expect(routePatternOf("/nope")).toBeNull();
    expect(navLocation(null)).toBeNull();
  });
});

// App Flow 3.2, sidebar visibility by role: item -> visible tabs, with every screen built.
const APP_FLOW_3_2: Record<Role, Record<string, string[]>> = {
  MAKER: {
    Home: ["Home"],
    Data: ["Upload", "Matching runs"],
    Review: ["To review", "Look-alikes"],
    Registry: ["Codes", "Search", "Create material (SAP)", "Exports", "Change notices"],
    Results: ["Savings", "Evaluation"],
    Rules: ["Rulebook"],
    Help: ["About"],
  },
  CHECKER: {
    Home: ["Home"],
    Data: ["Upload", "Matching runs"],
    Review: ["To review", "Consents", "Look-alikes"],
    Registry: ["Codes", "Search", "Create material (SAP)", "Exports", "Change notices"],
    Results: ["Savings", "Evaluation"],
    Rules: ["Rulebook"],
    Help: ["About"],
  },
  ADMIN: {
    Home: ["Home"],
    Data: ["Upload", "Matching runs"],
    Review: ["Look-alikes"],
    Registry: ["Codes", "Search", "Create material (SAP)", "Exports"],
    Results: ["Savings", "Evaluation"],
    Rules: ["Rulebook", "Audit", "Users"],
    Help: ["About"],
  },
  AUDITOR: {
    Home: ["Home"],
    Review: ["Look-alikes"],
    Registry: ["Codes"],
    Results: ["Evaluation"],
    Rules: ["Rulebook", "Audit"],
    Help: ["About"],
  },
  INTEGRATOR: {
    Registry: ["Codes", "Search", "Create material (SAP)", "Change notices"],
    Help: ["About"],
  },
};

describe("role filtering (App Flow 3.2)", () => {
  const everything = new Set(NAV_ITEMS.flatMap((i) => i.tabs.map((t) => t.path)));

  it.each(ALL)("%s sees exactly the App Flow 3.2 items and tabs", (role) => {
    const got = Object.fromEntries(
      visibleNav(false, role, NAV_ITEMS, everything).map((i) => [
        i.label,
        i.tabs.map((t) => t.label),
      ]),
    );
    expect(got).toEqual(APP_FLOW_3_2[role]);
  });

  it("an INTEGRATOR sees two items: the registry side and Help", () => {
    expect(visibleNav(false, "INTEGRATOR", NAV_ITEMS, everything)).toHaveLength(2);
    expect(
      visibleNav(false, "INTEGRATOR").map((i) => [i.label, i.tabs.map((t) => t.label)]),
    ).toEqual([
      ["Registry", ["Codes", "Search", "Create material (SAP)", "Change notices"]],
      ["Help", ["About"]],
    ]);
  });

  it("the developer switch never shows a tab the role may not see", () => {
    const tabs = visibleNav(true, "MAKER").flatMap((i) => i.tabs.map((t) => t.label));
    expect(tabs).not.toContain("Consents");
    expect(tabs).not.toContain("Audit");
    expect(tabs).not.toContain("Users");
  });

  // App Flow 2 vs 3.2 disagree on /registry for INTEGRATOR (PROGRESS.md Q-03, before Phase 6).
  const KNOWN_CONFLICTS: Record<string, Role[]> = {}; // Q-03 resolved by DEC-19

  it("a tab never offers a route its role cannot open (except open question Q-03)", () => {
    for (const tab of NAV_ITEMS.flatMap((i) => i.tabs)) {
      const route = SHELL_ROUTES.find((r) => r.path === tab.path)!;
      const extra = tab.roles.filter((r) => !route.roles.includes(r));
      expect(extra, tab.path).toEqual(KNOWN_CONFLICTS[tab.path] ?? []);
    }
  });
});
