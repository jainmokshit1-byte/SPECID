import { screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SHELL_ROUTES } from "./routes";
import { HEALTH, mockApi, renderAt, sidebarLabels, signIn } from "./test-utils";

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

// App Flow 3.3 first-run checklist.
const FIRST_RUN_STEPS = ["Upload files", "Check quality", "Run matching", "Review", "Issue codes"];

const SIDEBAR_LABELS = ["Home", "Data", "Review", "Registry", "Results", "Rules", "Help"];

function concrete(path: string) {
  return path.replace(/:(\w+)/g, "x-$1");
}

beforeEach(() => {
  signIn("ADMIN");
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
    signIn(r.roles[0]!);
    renderAt(concrete(r.path));
    const h1s = await screen.findAllByRole("heading", { level: 1 });
    expect(h1s).toHaveLength(1);
    expect(h1s[0]).toHaveTextContent(r.title);
    expect(screen.getByRole("navigation", { name: "Main" })).toBeInTheDocument();
    expect(screen.getByText("SYNTHETIC DATA")).toBeVisible();
    expect(await screen.findByText("Air-gap status unavailable")).toBeInTheDocument();
  });

  it("has no full-width ribbon, only the compact badge", async () => {
    renderAt("/");
    await screen.findByRole("heading", { level: 1 });
    expect(screen.queryByText(/SYNTHETIC DATA: results are optimistic/)).not.toBeInTheDocument();
    expect(screen.getByRole("note")).toHaveAccessibleName(
      "SYNTHETIC DATA: results on synthetic data are optimistic by construction",
    );
  });

  it("top bar shows the sidebar item as the page title", async () => {
    renderAt("/clusters/x-1");
    expect(await screen.findByRole("banner")).toHaveTextContent("Review");
  });

  it.each(["/", "/lookalikes"])("shows the run selector on run-scoped %s", async (p) => {
    renderAt(p);
    expect(await screen.findByLabelText("Run")).toBeDisabled();
  });

  it.each(["/registry", "/upload", "/templates", "/clusters/x-1"])(
    "hides the run selector on %s",
    async (p) => {
      renderAt(p);
      await screen.findByRole("heading", { level: 1 });
      expect(screen.queryByLabelText("Run")).not.toBeInTheDocument();
    },
  );

  it("renders login outside the shell and 404 for unknown routes", async () => {
    sessionStorage.clear();
    mockApi(); // signed out
    renderAt("/login");
    expect(await screen.findByRole("heading", { name: "SpecID" })).toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: "Main" })).not.toBeInTheDocument();
    expect(screen.queryByText("SYNTHETIC DATA")).not.toBeInTheDocument();
    document.body.innerHTML = "";
    signIn("MAKER");
    renderAt("/no-such-page");
    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeInTheDocument();
  });
});

describe("navigation (every App Flow screen is built)", () => {
  it("a MAKER sees all seven items, none marked dev", async () => {
    signIn("MAKER");
    renderAt("/");
    expect(await sidebarLabels()).toEqual(SIDEBAR_LABELS);
    expect(screen.queryByText("dev")).not.toBeInTheDocument();
  });

  it("a CHECKER sees the three Review tabs on /review", async () => {
    signIn("CHECKER");
    renderAt("/review");
    await screen.findByRole("heading", { level: 1 });
    const tabs = within(screen.getByRole("navigation", { name: "Section" })).getAllByRole("link");
    expect(tabs.map((t) => t.textContent)).toEqual(["To review", "Consents", "Look-alikes"]);
    expect(tabs[0]).toHaveAttribute("aria-current", "page");
  });

  it("Results opens Savings first, with Evaluation as the second tab", async () => {
    signIn("MAKER");
    renderAt("/evaluation");
    expect(
      await screen.findByRole("heading", { level: 1, name: "Evaluation" }),
    ).toBeInTheDocument();
    const tabs = within(screen.getByRole("navigation", { name: "Section" })).getAllByRole("link");
    expect(tabs.map((t) => t.textContent)).toEqual(["Savings", "Evaluation"]);
  });
});

describe("developer switch adds nothing once every screen is built", () => {
  it("?dev=1 shows the same seven items with no dev marks", async () => {
    signIn("MAKER");
    renderAt("/?dev=1");
    expect(await sidebarLabels()).toEqual(SIDEBAR_LABELS);
  });

  it("is never on in a production (demo) build, whatever the URL or env", async () => {
    vi.stubEnv("DEV", false);
    vi.stubEnv("VITE_SHOW_UNBUILT", "true");
    signIn("MAKER");
    renderAt("/?dev=1");
    expect(await sidebarLabels()).toEqual(SIDEBAR_LABELS);
  });
});

describe("Home Next-step card (App Flow 3.3, DEC-16)", () => {
  it.each(["MAKER", "CHECKER", "ADMIN"] as const)(
    "%s sees the first-run checklist at step 1, no invented numbers",
    async (role) => {
      signIn(role);
      renderAt("/");
      const card = await screen.findByRole("region", { name: "Next step" });
      const steps = within(card).getAllByRole("listitem");
      expect(steps.map((s) => s.textContent)).toEqual(
        FIRST_RUN_STEPS.map((s, i) => `${i + 1}${s}`),
      );
      expect(steps[0]).toHaveAttribute("aria-current", "step");
      // with no ingested file the next step is S2, which is built: a real link
      expect(within(card).getByRole("link", { name: "Upload files" })).toHaveAttribute(
        "href",
        "/upload",
      );
      expect(card.textContent).not.toMatch(/\d+ (clusters|national codes)/);
    },
  );
});

describe("footer", () => {
  it("never claims Air-gapped before /system/airgap exists", async () => {
    renderAt("/");
    await screen.findByText("Air-gap status unavailable");
    expect(screen.queryByText(/Air-gapped/i)).not.toBeInTheDocument();
  });

  it("shows the air-gap counter in the fixed wording once the endpoint answers", async () => {
    signIn("ADMIN", { airgap: { blocked_egress_attempts: 0 }, health: HEALTH });
    renderAt("/");
    expect(await screen.findByText("Air-gapped · blocked attempts: 0")).toBeInTheDocument();
  });

  it("shows the consent mode from /health and no OFF tags when all is on", async () => {
    signIn("ADMIN", { health: HEALTH });
    renderAt("/");
    expect(await screen.findByText("Consent: all CPSEs")).toBeInTheDocument();
    expect(screen.queryByText("GUARD OFF")).not.toBeInTheDocument();
    expect(screen.queryByText("DENSE OFF")).not.toBeInTheDocument();
    expect(screen.queryByText(/abc1234/)).not.toBeInTheDocument();
  });

  it("flags GUARD OFF and DENSE OFF when /health says so", async () => {
    signIn("ADMIN", {
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
