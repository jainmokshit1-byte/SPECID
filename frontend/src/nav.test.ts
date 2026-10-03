import { describe, expect, it } from "vitest";
import { NAV_ITEMS, type NavItem, navLocation, routePatternOf, visibleNav } from "./nav";
import { SHELL_ROUTES } from "./routes";

const FIXTURE: NavItem[] = [
  { id: "home", label: "Home", tabs: [{ label: "Home", path: "/" }] },
  {
    id: "review",
    label: "Review",
    tabs: [
      { label: "To review", path: "/review" },
      { label: "Consents", path: "/consents" },
    ],
  },
  { id: "help", label: "Help", bottom: true, tabs: [{ label: "About", path: "/about" }] },
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
      expect(owners, r.path).toHaveLength(r.pri === "P0" ? 1 : 0);
    }
  });
});

describe("visibleNav", () => {
  it("hides unbuilt tabs, and items left with no tab", () => {
    const v = visibleNav(false, FIXTURE, new Set(["/", "/consents"]));
    expect(v.map((i) => i.label)).toEqual(["Home", "Review"]);
    expect(v[1]!.tabs.map((t) => t.label)).toEqual(["Consents"]);
  });

  it("developer switch shows everything and marks unbuilt tabs", () => {
    const v = visibleNav(true, FIXTURE, new Set(["/"]));
    expect(v.map((i) => i.label)).toEqual(["Home", "Review", "Help"]);
    expect(v[1]!.tabs.map((t) => t.built)).toEqual([false, false]);
    expect(v[0]!.tabs[0]!.built).toBe(true);
  });

  it("never exceeds seven items", () => {
    expect(visibleNav(true).length).toBeLessThanOrEqual(7);
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
