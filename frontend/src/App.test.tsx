import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { SHELL_ROUTES } from "./routes";

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

// App Flow 3.3 admin first-run checklist.
const FIRST_RUN_STEPS = ["Upload files", "Check quality", "Run matching", "Review", "Issue codes"];

const SIDEBAR_LABELS = ["Home", "Data", "Review", "Registry", "Results", "Rules", "Help"];

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

/** API stub. Default: /system/airgap answers 404 (not built yet), /health is unreachable. */
function mockApi(answers: { airgap?: object; health?: object } = {}) {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    if (url.includes("/system/airgap"))
      return answers.airgap
        ? new Response(JSON.stringify(answers.airgap), { status: 200 })
        : new Response("{}", { status: 404 });
    if (url.includes("/health") && answers.health)
      return new Response(JSON.stringify(answers.health), { status: 200 });
    return new Response("{}", { status: 503 });
  });
}

const HEALTH = {
  status: "ok",
  version: "0.1.0",
  git_commit: "abc1234",
  db: "ok",
  consent_mode: "ALL_PARTICIPANTS",
  embeddings_enabled: true,
  egress_guard: { enabled: true, installed: false },
};

function sidebarLabels() {
  const nav = screen.getByRole("navigation", { name: "Main" });
  return within(nav)
    .getAllByRole("link")
    .map((a) => a.textContent);
}

beforeEach(() => {
  sessionStorage.clear();
  mockApi();
});

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("route table", () => {
  it("matches 03 App Flow section 2 exactly", () => {
    expect(SHELL_ROUTES.map((r) => r.path).sort()).toEqual([...APP_FLOW_PATHS].sort());
  });
});

describe("app shell (v1.2)", () => {
  it.each(SHELL_ROUTES)("renders $screen $path inside the shell", async (r) => {
    renderAt(concrete(r.path));
    const h1s = screen.getAllByRole("heading", { level: 1 });
    expect(h1s).toHaveLength(1);
    expect(h1s[0]).toHaveTextContent(r.title);
    expect(screen.getByRole("navigation", { name: "Main" })).toBeInTheDocument();
    expect(screen.getByText("SYNTHETIC DATA")).toBeVisible();
    expect(await screen.findByText("Air-gap status unavailable")).toBeInTheDocument();
  });

  it("has no full-width ribbon, only the compact badge", () => {
    renderAt("/");
    expect(screen.queryByText(/SYNTHETIC DATA: results are optimistic/)).not.toBeInTheDocument();
    expect(screen.getByRole("note")).toHaveAccessibleName(
      "SYNTHETIC DATA: results on synthetic data are optimistic by construction",
    );
  });

  it("top bar shows the sidebar item as the page title", () => {
    renderAt("/clusters/x-1");
    expect(screen.getByRole("banner")).toHaveTextContent("Review");
  });

  it.each(["/", "/review", "/lookalikes"])("shows the run selector on run-scoped %s", (p) => {
    renderAt(p);
    expect(screen.getByLabelText("Run")).toBeDisabled();
  });

  it.each(["/registry", "/upload", "/templates", "/clusters/x-1"])(
    "hides the run selector on %s",
    (p) => {
      renderAt(p);
      expect(screen.queryByLabelText("Run")).not.toBeInTheDocument();
    },
  );

  it("user menu opens and offers the login page", async () => {
    renderAt("/");
    const trigger = screen.getByRole("button", { name: /Not signed in/ });
    fireEvent.keyDown(trigger, { key: "Enter" });
    expect(await screen.findByRole("menuitem", { name: "Go to login" })).toHaveAttribute(
      "href",
      "/login",
    );
  });

  it("renders login outside the shell and 404 for unknown routes", () => {
    renderAt("/login");
    expect(screen.queryByRole("navigation", { name: "Main" })).not.toBeInTheDocument();
    expect(screen.queryByText("SYNTHETIC DATA")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "SpecID" })).toBeInTheDocument();
    document.body.innerHTML = "";
    renderAt("/no-such-page");
    expect(screen.getByRole("heading", { name: "Page not found" })).toBeInTheDocument();
  });
});

describe("navigation hides unbuilt screens (default mode)", () => {
  it("lists only built items: Home", () => {
    renderAt("/");
    expect(sidebarLabels()).toEqual(["Home"]);
    expect(screen.queryByText("dev")).not.toBeInTheDocument();
  });

  it("an unbuilt screen still renders by URL but is not in the menu", () => {
    renderAt("/consents");
    expect(screen.getByRole("heading", { level: 1, name: "Consent queue" })).toBeInTheDocument();
    expect(sidebarLabels()).toEqual(["Home"]);
    expect(screen.queryByRole("navigation", { name: "Section" })).not.toBeInTheDocument();
  });
});

describe("developer switch shows unbuilt screens, marked dev", () => {
  it("?dev=1 lists all seven items and the Review tabs", () => {
    renderAt("/review?dev=1");
    expect(sidebarLabels()).toEqual(["Home", ...SIDEBAR_LABELS.slice(1).map((l) => `${l}dev`)]);
    const tabs = within(screen.getByRole("navigation", { name: "Section" })).getAllByRole("link");
    expect(tabs.map((t) => t.textContent)).toEqual([
      "To reviewdev",
      "Consentsdev",
      "Look-alikesdev",
    ]);
    expect(tabs[0]).toHaveAttribute("aria-current", "page");
  });

  it("?dev=1 stays on while navigating in the same tab; ?dev=0 turns it off", () => {
    renderAt("/?dev=1");
    fireEvent.click(within(screen.getByRole("navigation", { name: "Main" })).getByText("Registry"));
    expect(screen.getByRole("heading", { level: 1, name: "Registry" })).toBeInTheDocument();
    expect(sidebarLabels()).toHaveLength(7);
    document.body.innerHTML = "";
    renderAt("/?dev=0");
    expect(sidebarLabels()).toEqual(["Home"]);
  });

  it("VITE_SHOW_UNBUILT=true lists all seven items", () => {
    vi.stubEnv("VITE_SHOW_UNBUILT", "true");
    renderAt("/");
    expect(sidebarLabels()).toHaveLength(7);
  });

  it("is never on in a production (demo) build, whatever the URL or env", () => {
    vi.stubEnv("DEV", false);
    vi.stubEnv("VITE_SHOW_UNBUILT", "true");
    renderAt("/?dev=1");
    expect(sidebarLabels()).toEqual(["Home"]);
  });
});

describe("Home", () => {
  it("shows the Next-step card with the first-run checklist at step 1", () => {
    renderAt("/");
    const card = screen.getByRole("region", { name: "Next step" });
    const steps = within(card).getAllByRole("listitem");
    expect(steps.map((s) => s.textContent)).toEqual(FIRST_RUN_STEPS.map((s, i) => `${i + 1}${s}`));
    expect(steps[0]).toHaveAttribute("aria-current", "step");
    // S2 is not built yet, so the primary button cannot lead to a placeholder.
    expect(within(card).getByRole("button", { name: "Upload files" })).toBeDisabled();
  });
});

describe("footer", () => {
  it("never claims Air-gapped before /system/airgap exists", async () => {
    renderAt("/");
    await screen.findByText("Air-gap status unavailable");
    expect(screen.queryByText(/Air-gapped/i)).not.toBeInTheDocument();
  });

  it("shows the air-gap counter in the fixed wording once the endpoint answers", async () => {
    mockApi({ airgap: { blocked_egress_attempts: 0 }, health: HEALTH });
    renderAt("/");
    expect(await screen.findByText("Air-gapped · blocked attempts: 0")).toBeInTheDocument();
  });

  it("shows the consent mode from /health and no OFF tags when all is on", async () => {
    mockApi({ health: HEALTH });
    renderAt("/");
    expect(await screen.findByText("Consent: all CPSEs")).toBeInTheDocument();
    expect(screen.queryByText("GUARD OFF")).not.toBeInTheDocument();
    expect(screen.queryByText("DENSE OFF")).not.toBeInTheDocument();
    expect(screen.queryByText(/abc1234/)).not.toBeInTheDocument();
  });

  it("flags GUARD OFF and DENSE OFF when /health says so", async () => {
    mockApi({
      health: {
        ...HEALTH,
        embeddings_enabled: false,
        egress_guard: { enabled: false, installed: false },
      },
    });
    renderAt("/");
    expect(await screen.findByText("GUARD OFF")).toBeInTheDocument();
    expect(screen.getByText("DENSE OFF")).toBeInTheDocument();
  });
});
