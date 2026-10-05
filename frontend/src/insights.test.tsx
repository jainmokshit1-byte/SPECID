// Go 1 chunk 5 + Go 2 screens with a fake API: dashboard, SAP simulation, evaluation, rulebook,
// demo sign-in and the cloud footer. Numbers here are fixtures, never product claims.

import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Dashboard, EvalRun, SearchResult } from "./api/insights";
import { formatInr } from "./lib/format";
import { HEALTH, json, location, mockApi, renderAt, signIn } from "./test-utils";

afterEach(() => {
  vi.restoreAllMocks();
  sessionStorage.clear();
  document.body.innerHTML = "";
});

const RUN_ID = "a724f4d3-a236-4a75-85d0-4d07028031c3";

const DASH: Dashboard = {
  run_id: RUN_ID,
  is_synthetic: true,
  computed_at: "2026-10-05T10:00:00Z",
  mode: "CROSS_CPSE",
  per_cpse: [
    {
      cpse: "CPSE-A",
      records: 1000,
      annual_spend: 5e6,
      health_score: 96,
      in_groups: 400,
      internal_duplicates: 12,
    },
    {
      cpse: "CPSE-B",
      records: 990,
      annual_spend: 4e6,
      health_score: 88,
      in_groups: 380,
      internal_duplicates: 3,
    },
  ],
  groups: { total: 410, cross_cpse: 300, three_plus: 120 },
  verdicts: { EQUIVALENT: 900, NOT_EQUIVALENT: 4000 },
  records: 1990,
  candidate_pairs: 9000,
  backlog: { OPEN: 400, MADE: 5, AWAITING_CONSENT: 2, DONE: 3 },
  issued: 3,
  by_category: [{ category: "VALVE", groups: 200, records: 800 }],
  top_groups: [
    {
      id: "c-1",
      category: "VALVE",
      priority: 9,
      state: "OPEN",
      sample_text: "GATE VLV 4IN 150# WCB",
      cpses: ["CPSE-A", "CPSE-B"],
      annual_spend: 250000,
    },
  ],
  money: {
    groups_with_prices: 150,
    total_price_gap: 1234567,
    pooled_annual_spend: 9e6,
    top_price_gaps: [
      {
        cluster_id: "c-1",
        category: "VALVE",
        state: "OPEN",
        sample_text: "GATE VLV 4IN 150# WCB",
        cnmc: null,
        lowest_price: 9000,
        price_gap: 42000,
        by_cpse: [
          { cpse: "CPSE-A", annual_qty: 10, avg_price: 9000 },
          { cpse: "CPSE-B", annual_qty: 10, avg_price: 13200 },
        ],
      },
    ],
    stock_sharing: {
      suggestions: 1,
      total_value: 66000,
      top: [
        {
          cluster_id: "c-1",
          category: "VALVE",
          sample_text: "GATE VLV 4IN 150# WCB",
          cnmc: null,
          holder: "CPSE-A",
          holder_code: "A-1",
          idle_stock: 5,
          buyer: "CPSE-B",
          buyer_code: "B-1",
          buyer_annual_qty: 10,
          transferable: 5,
          value_at_buyer_price: 66000,
        },
      ],
    },
    note: "Synthetic prices.",
  },
};

const RUN = {
  id: RUN_ID,
  status: "DONE",
  mode: "CROSS_CPSE",
  batch_ids: [],
  config: {},
  stats: null,
  error: null,
  started_by: null,
  started_at: "2026-10-05T09:00:00Z",
  finished_at: "2026-10-05T09:01:00Z",
};

describe("S0 dashboard", () => {
  it("shows the run's figures, price gaps and transfers, all from the API", async () => {
    signIn("MAKER", {
      handle: (u) => {
        if (u.endsWith("/api/v1/runs")) return json([RUN]);
        if (u.includes("/api/v1/dashboard")) return json(DASH);
        if (u.endsWith("/api/v1/batches")) return json([]);
        return undefined;
      },
    });
    renderAt("/");
    expect(await screen.findByText(formatInr(1234567))).toBeInTheDocument();
    expect(screen.getByText("Same item, different prices")).toBeInTheDocument();
    expect(screen.getByText(/holds 5 idle/)).toBeInTheDocument();
    expect(screen.getByLabelText("Run")).toHaveValue(RUN_ID);
    expect(screen.getByLabelText("Run")).toBeEnabled();
  });
});

describe("S14 SAP simulation", () => {
  it("flags an existing national code while the user types", async () => {
    const result: SearchResult = {
      query: { category: "VALVE", class_source: "RULE", attrs: {}, repairs: [] },
      candidates: [
        {
          cnmc: "NMC-00000000018",
          short_desc_40: "GATE VLV 4IN CL150 WCB FLGD RF",
          long_desc: null,
          cpses: ["CPSE-A", "CPSE-B"],
          verdict: "EQUIVALENT",
          reasons: [],
          text_sim: 0.9,
          missing: [],
          conflicts: [],
          evidence: [],
        },
      ],
      would_create_duplicate: true,
      recommended_action: "USE_EXISTING",
      message: "Use the existing code.",
      missing: [],
    };
    signIn("INTEGRATOR", {
      handle: (u) => (u.includes("/search-before-create") ? json(result) : undefined),
    });
    renderAt("/erp-sim");
    fireEvent.change(await screen.findByLabelText("Material Description"), {
      target: { value: "GATE VALVE 4IN 150# WCB FLGD RF" },
    });
    expect(
      await screen.findByText("⚠ This material already exists in the national registry."),
    ).toBeInTheDocument();
    expect(screen.getByText("31 / 40")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Use SpecID description" }));
    expect(screen.getByLabelText("Material Description")).toHaveValue(
      "GATE VLV 4IN CL150 WCB FLGD RF",
    );
  });
});

describe("S11b evaluation report", () => {
  const score = (fm: number, tp: number) => ({
    tp,
    fp: fm,
    fn: 10,
    abstain: 5,
    precision: tp / (tp + fm),
    recall_strict: 0.6,
    recall_decided: 0.9,
    coverage: 0.7,
    false_merges: fm,
    hard_negatives: 500,
    false_merge_upper_95: fm === 0 ? 0.006 : 0.1,
    tau: 0.8,
  });
  const ev: EvalRun = {
    id: "e-1",
    kind: "SYNTHETIC",
    seed: 7,
    config: {},
    status: "DONE",
    git_commit: "abc1234",
    created_at: "2026-10-05T10:00:00Z",
    created_by: null,
    metrics: {
      honesty: "",
      config: {},
      dataset: {},
      blocking: {
        pair_completeness: 0.98,
        reduction_ratio: 0.99,
        hard_negatives_in_test: 500,
        hard_negatives_not_reached: 0,
      },
      methods: { specid: score(0, 300), b1: score(40, 320), b2: score(12, 310) },
      abstentions: { total: 100, justified: 90, rate: 0.2 },
      disagreements: { b1_merged_specid_vetoed: 40 },
      per_category: { VALVE: score(0, 100) },
      timings_ms: {},
    },
  };

  it("leads with wrong merges and their bound, then the honesty panel", async () => {
    signIn("CHECKER", { handle: (u) => (u.endsWith("/eval/runs/e-1") ? json(ev) : undefined) });
    renderAt("/evaluation/e-1");
    expect(await screen.findByText("Wrong merges: 0 of 500 look-alike pairs")).toBeInTheDocument();
    expect(screen.getByText(/95% upper bound 0.60%/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "What these numbers do not mean" })).toBeVisible();
  });
});

describe("S10 rulebook", () => {
  it("lists categories with what must match and opens a template", async () => {
    signIn("AUDITOR", {
      handle: (u) => {
        if (u.endsWith("/api/v1/templates"))
          return json([
            {
              id: "valve",
              category: "VALVE",
              version: 1,
              status: "ACTIVE",
              critical_default: true,
              core: ["valve_type", "pressure_class"],
              extended: [],
              rules: 1,
            },
          ]);
        return undefined;
      },
    });
    renderAt("/templates");
    const card = (await screen.findByText("Valves")).closest("a")!;
    expect(within(card).getByText("Safety-critical: always two people")).toBeInTheDocument();
    fireEvent.click(card);
    await waitFor(() => expect(location()).toBe("/templates/valve"));
  });
});

describe("demo sign-in and cloud footer (DEC-42)", () => {
  it("shows one button per demo role when the API is in demo mode", async () => {
    sessionStorage.clear();
    let asked: unknown;
    mockApi({
      health: { ...HEALTH, demo_mode: true, demo_status: "ready", ai_provider: "gemini" },
      handle: (u, init) => {
        if (u.endsWith("/auth/demo-login")) {
          asked = JSON.parse(String(init?.body));
          return json({ title: "Not ready", status: 404 }, 404);
        }
        return undefined;
      },
    });
    renderAt("/login");
    const maker = await screen.findByRole("button", { name: /Maker/ });
    await waitFor(() => expect(maker).toBeEnabled());
    fireEvent.click(maker);
    expect(await screen.findByText(/still preparing its data/)).toBeInTheDocument();
    expect(asked).toEqual({ username: "meera" });
  });

  it("hides the demo buttons outside demo mode", async () => {
    sessionStorage.clear();
    mockApi({ health: HEALTH });
    renderAt("/login");
    await screen.findByRole("heading", { name: "SpecID" });
    expect(screen.queryByText("Demo: sign in as")).not.toBeInTheDocument();
  });

  it("never says air-gapped on the online cloud demo", async () => {
    signIn("MAKER", {
      health: { ...HEALTH, demo_mode: true, ai_provider: "gemini" },
      airgap: { mode: "ONLINE", blocked_egress_attempts: 0 },
    });
    renderAt("/about");
    expect(await screen.findByText(/Cloud demo · AI: Gemini/)).toBeInTheDocument();
    expect(screen.queryByText(/Air-gapped/)).not.toBeInTheDocument();
  });
});
