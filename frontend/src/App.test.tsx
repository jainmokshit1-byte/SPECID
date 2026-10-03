import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { NAV_GROUPS, SHELL_ROUTES } from "./routes";

// Every route of 03 App Flow section 2 (shell routes; /login and * are tested separately).
const APP_FLOW_PATHS = [
  "/",
  "/upload",
  "/batches/:batchId/quality",
  "/runs",
  "/runs/new",
  "/runs/:runId",
  "/review",
  "/clusters/:clusterId",
  "/pairs/:pairId",
  "/registry",
  "/registry/:cnmc",
  "/exports",
  "/search",
  "/templates",
  "/templates/:templateId",
  "/evaluation",
  "/evaluation/:evalId",
  "/lookalikes",
  "/audit",
  "/admin/users",
  "/erp-sim",
  "/pooling",
  "/about",
  "/consents",
  "/notices",
];

function renderAt(url: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[url]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function concrete(path: string) {
  return path.replace(/:(\w+)/g, "x-$1");
}

beforeEach(() => {
  // No API in unit tests: /system/airgap answers 404 (not built yet), /health is unreachable.
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) =>
    String(input).includes("/system/airgap")
      ? new Response("{}", { status: 404 })
      : new Response("{}", { status: 503 }),
  );
});

describe("route table", () => {
  it("matches 03 App Flow section 2 exactly", () => {
    expect(SHELL_ROUTES.map((r) => r.path).sort()).toEqual([...APP_FLOW_PATHS].sort());
  });

  it("every sidebar item points at a defined route", () => {
    const paths = new Set(SHELL_ROUTES.map((r) => r.path));
    for (const g of NAV_GROUPS) for (const item of g.items) expect(paths).toContain(item.path);
  });
});

describe("app shell", () => {
  it.each(SHELL_ROUTES)("renders $screen $path inside the shell", async (r) => {
    renderAt(concrete(r.path));
    expect(screen.getByRole("heading", { level: 1, name: r.title })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Main" })).toBeInTheDocument();
    expect(
      screen.getByText(/SYNTHETIC DATA: results are optimistic by construction/),
    ).toBeVisible();
    expect(await screen.findByText("air-gap status: not available yet")).toBeInTheDocument();
  });

  it("never claims AIR-GAPPED before /system/airgap exists", async () => {
    renderAt("/");
    await screen.findByText("air-gap status: not available yet");
    expect(screen.queryByText(/AIR-GAPPED/)).not.toBeInTheDocument();
  });

  it("shows all seven sidebar groups", () => {
    renderAt("/");
    for (const g of [
      "Overview",
      "Data",
      "Review",
      "Registry",
      "Insight",
      "Governance",
      "Integration",
    ])
      expect(screen.getByText(g)).toBeInTheDocument();
  });

  it("renders login outside the shell and 404 for unknown routes", () => {
    renderAt("/login");
    expect(screen.queryByRole("navigation", { name: "Main" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "SpecID" })).toBeInTheDocument();
    cleanupAndRender("/no-such-page");
    expect(screen.getByRole("heading", { name: "Page not found" })).toBeInTheDocument();
  });
});

function cleanupAndRender(url: string) {
  document.body.innerHTML = "";
  renderAt(url);
}
