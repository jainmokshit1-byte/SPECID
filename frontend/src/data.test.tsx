// S2 Upload & mapping, S3 quality report, S4 runs (WP1.7) with a fake API.

import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Batch, BatchUploaded } from "./api/batches";
import type { Run } from "./api/runs";
import { firstRunStep } from "./pages/Home";
import { defaultSelection } from "./pages/NewRun";
import { stageSteps } from "./pages/RunConsole";
import { mappingProblems } from "./pages/Upload";
import { json, location, renderAt, signIn } from "./test-utils";

afterEach(() => {
  vi.restoreAllMocks();
  sessionStorage.clear();
  document.body.innerHTML = "";
});

const QUALITY = {
  rows: 993,
  empty_short_text: 0,
  short_text_over_40: 12,
  duplicate_legacy_codes: 2,
  completeness: { legacy_code: 1, short_text: 1, uom: 1, manufacturer: 0.4, plant: 1 },
  category_share: { VALVE: 0.4, FLANGE: 0.3, PIPE: 0.29, UNRECOGNISED: 0.01 },
  core_parse_rate: { VALVE: 0.81, FLANGE: 0.9, PIPE: 0.95 },
  uom_ambiguous: 1,
  rejected_rows: 3,
  uom_unknown: 0,
  skipped_unchanged: 0,
  health_score: 97,
  health_components: {
    descriptions: 1,
    unique_codes: 0.998,
    recognised_category: 0.99,
    spec_completeness: 0.9,
    uom_clean: 0.999,
  },
};

function batch(id: string, cpse: string, created: string, patch: Partial<Batch> = {}): Batch {
  return {
    id,
    cpse_code: cpse,
    filename: `cpse_${cpse.slice(-1)}.csv`,
    status: "INGESTED",
    row_count: 993,
    is_synthetic: true,
    column_mapping: { legacy_code: "legacy_code", short_text: "short_text" },
    quality: QUALITY,
    created_at: created,
    ...patch,
  };
}

function run(patch: Partial<Run> = {}): Run {
  return {
    id: "a724f4d3-a236-4a75-85d0-4d07028031c3",
    status: "DONE",
    mode: "CROSS_CPSE",
    batch_ids: ["b1", "b2"],
    config: {},
    stats: {
      progress: { stage: "done", done: 1, total: 1 },
      records: 3023,
      unclassified: 59,
      candidate_pairs: 78201,
      channels: { B: 50249, L: 27938, D: 0, M: 277 },
      verdicts: {
        IDENTICAL: 157,
        EQUIVALENT: 1019,
        NOT_EQUIVALENT: 70932,
        INSUFFICIENT_DATA: 6093,
      },
      clusters: 689,
      timings_ms: { read: 987, candidates: 146, decide: 7513, cluster: 72, total: 8846 },
      blocked_egress: 0,
    },
    error: null,
    started_by: "meera",
    started_at: "2026-10-05T13:00:00Z",
    finished_at: "2026-10-05T13:00:11Z",
    ...patch,
  };
}

describe("pure helpers", () => {
  it("mapping needs a code column and a description column, each target once", () => {
    expect(mappingProblems({ A: "legacy_code", B: "short_text" })).toEqual([]);
    expect(mappingProblems({ A: "legacy_code", B: "long_text" })).toEqual([]);
    expect(mappingProblems({ A: "short_text" })[0]).toMatch(/material code/);
    expect(mappingProblems({ A: "legacy_code", B: "" })[0]).toMatch(/description/);
    expect(mappingProblems({ A: "legacy_code", B: "short_text", C: "short_text" })).toEqual([
      "Two columns are set to “Short description”.",
    ]);
  });

  it("Home's step follows the data, never an invented count", () => {
    expect([
      firstRunStep(0, 0),
      firstRunStep(1, 0),
      firstRunStep(3, 0),
      firstRunStep(3, 1),
    ]).toEqual([0, 1, 2, 3]);
  });

  it("new run preselects the newest ingested file of each CPSE", () => {
    const list = [
      batch("a-old", "CPSE-A", "2026-10-01T00:00:00Z"),
      batch("a-new", "CPSE-A", "2026-10-05T00:00:00Z"),
      batch("b", "CPSE-B", "2026-10-02T00:00:00Z"),
      batch("c-up", "CPSE-C", "2026-10-03T00:00:00Z", { status: "UPLOADED" }),
    ];
    expect(defaultSelection(list, [])).toEqual(["a-new", "b"]);
    // a named batch is kept, the other CPSEs' newest are added
    expect(defaultSelection(list, ["a-old"])).toEqual(["a-old", "b"]);
  });

  it("stage steps carry counts and timings from the run", () => {
    const steps = stageSteps(run());
    expect(steps.map((s) => s.id)).toEqual(["read", "candidates", "decide", "cluster"]);
    expect(steps[0]!.detail).toBe("3,023 records · 987 ms");
    expect(steps[2]!.detail).toBe("78,201 decided · 7.5 s");
  });
});

describe("S2 upload & mapping", () => {
  const uploaded: BatchUploaded = {
    ...batch("new-1", "CPSE-A", "2026-10-05T10:00:00Z", { status: "UPLOADED", quality: null }),
    filename: "sap.csv",
    columns: ["MARA-MATNR", "MAKT-MAKTX", "MARA-MEINS", "NOTES"],
    suggested_mapping: {
      "MARA-MATNR": "legacy_code",
      "MAKT-MAKTX": "short_text",
      "MARA-MEINS": "uom",
    },
    preset: "SAP",
    sample_rows: [
      { "MARA-MATNR": "100001", "MAKT-MAKTX": "GATE VALVE 4IN", "MARA-MEINS": "NOS", NOTES: "x" },
    ],
    encoding: "utf-8",
    already_ingested: false,
  };

  it("uploads, shows the SAP preset and the suggested mapping, then ingests", async () => {
    const calls: { method: string; url: string; body?: unknown }[] = [];
    signIn("MAKER", {
      handle: (url, init) => {
        const method = init?.method ?? "GET";
        if (url.endsWith("/api/v1/batches") && method === "GET") return json([]);
        if (url.endsWith("/api/v1/batches") && method === "POST") {
          calls.push({ method, url });
          return json(uploaded, 201);
        }
        if (url.endsWith("/mapping")) {
          calls.push({ method, url, body: JSON.parse(String(init?.body)) });
          return json({ ...uploaded, status: "MAPPED" });
        }
        if (url.endsWith("/ingest")) {
          calls.push({ method, url });
          return json({ ...uploaded, status: "INGESTED", quality: QUALITY });
        }
        if (url.includes("/batches/new-1"))
          return json(batch("new-1", "CPSE-A", "2026-10-05T10:00:00Z"));
        return undefined;
      },
    });
    renderAt("/upload");
    expect(
      await screen.findByRole("heading", { level: 1, name: "Upload & mapping" }),
    ).toBeInTheDocument();
    expect(screen.getByText("CPSE-A")).toBeInTheDocument(); // a maker uploads for their own CPSE
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, {
      target: { files: [new File(["x"], "sap.csv", { type: "text/csv" })] },
    });
    fireEvent.click(screen.getByRole("button", { name: "Upload and read columns" }));
    expect(await screen.findByText(/SAP material-master columns detected/)).toBeInTheDocument();
    expect(screen.getByLabelText("Field for MARA-MATNR")).toHaveValue("legacy_code");
    expect(screen.getByLabelText("Field for NOTES")).toHaveValue("");
    expect(screen.getByText(/Mapping complete: 3 columns used/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Save & ingest" }));
    await waitFor(() => expect(location()).toBe("/batches/new-1/quality"));
    expect(calls.map((c) => c.url.split("/api/v1")[1])).toEqual([
      "/batches",
      "/batches/new-1/mapping",
      "/batches/new-1/ingest",
    ]);
    expect(calls[1]!.body).toEqual({
      column_mapping: {
        "MARA-MATNR": "legacy_code",
        "MAKT-MAKTX": "short_text",
        "MARA-MEINS": "uom",
      },
    });
  });

  it("blocks Save & ingest until a code and a description column are chosen", async () => {
    signIn("MAKER", {
      handle: (url, init) => {
        if (url.endsWith("/api/v1/batches") && (init?.method ?? "GET") === "GET") return json([]);
        if (url.endsWith("/api/v1/batches"))
          return json({ ...uploaded, suggested_mapping: {}, preset: null }, 201);
        return undefined;
      },
    });
    renderAt("/upload");
    const input = (await screen.findByText("Drop a CSV or Excel file here"))
      .closest("label")!
      .querySelector("input")!;
    fireEvent.change(input, { target: { files: [new File(["x"], "a.csv")] } });
    fireEvent.click(screen.getByRole("button", { name: "Upload and read columns" }));
    const save = await screen.findByRole("button", { name: "Save & ingest" });
    expect(save).toBeDisabled();
    expect(screen.getByText("Choose the column that holds the material code.")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Field for MARA-MATNR"), {
      target: { value: "legacy_code" },
    });
    fireEvent.change(screen.getByLabelText("Field for MAKT-MAKTX"), {
      target: { value: "short_text" },
    });
    expect(save).toBeEnabled();
  });

  it("rejects an unsupported file before uploading", async () => {
    signIn("MAKER", { handle: (u) => (u.endsWith("/api/v1/batches") ? json([]) : undefined) });
    renderAt("/upload");
    const input = (await screen.findByText("Drop a CSV or Excel file here"))
      .closest("label")!
      .querySelector("input")!;
    fireEvent.change(input, { target: { files: [new File(["x"], "a.pdf")] } });
    expect(await screen.findByText("Upload a .csv or .xlsx file.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Upload and read columns" })).toBeDisabled();
  });
});

describe("S3 quality report", () => {
  it("shows the health score, its parts, categories and the next step", async () => {
    signIn("MAKER", {
      handle: (u) =>
        u.includes("/batches/b1") ? json(batch("b1", "CPSE-A", "2026-10-05T10:00:00Z")) : undefined,
    });
    renderAt("/batches/b1/quality");
    expect(await screen.findByRole("img", { name: "Health 97 of 100" })).toBeInTheDocument();
    expect(screen.getByText("Category recognised")).toBeInTheDocument();
    expect(screen.getByText("Valves")).toBeInTheDocument();
    expect(screen.getByText("Not recognised")).toBeInTheDocument();
    expect(screen.getByText("993")).toBeInTheDocument();
    const start = screen.getByRole("link", { name: "Start a run with this batch" });
    expect(start).toHaveAttribute("href", "/runs/new?batches=b1");
  });
});

describe("S4 runs", () => {
  it("lists runs with status and a verdict mix", async () => {
    signIn("MAKER", { handle: (u) => (u.endsWith("/api/v1/runs") ? json([run()]) : undefined) });
    renderAt("/runs");
    const link = await screen.findByRole("link", { name: "a724f4d3" });
    const row = link.closest("tr")!;
    expect(within(row).getByText("Done")).toBeInTheDocument();
    expect(within(row).getByText("3,023")).toBeInTheDocument();
    expect(within(row).getByText("11.0 s")).toBeInTheDocument();
  });

  it("the console shows the stages, verdict mix and pairs of a finished run", async () => {
    signIn("MAKER", {
      handle: (u) => {
        if (u.includes("/pairs"))
          return json({
            total: 1,
            items: [
              {
                id: "p1",
                rec_a: "r1",
                rec_b: "r2",
                cpse_a: "CPSE-A",
                code_a: "A1",
                text_a: "VALVE GATE 4IN CL150",
                cpse_b: "CPSE-B",
                code_b: "B1",
                text_b: "GATE VALVE, 4 INCH, CLASS 150",
                verdict: "EQUIVALENT",
                route: "REVIEW",
                p_equiv: 0.98,
                text_sim: 0.71,
                lookalike: "HIDDEN_TWIN",
                channels: 1,
                reasons: [],
              },
            ],
          });
        if (u.includes("/runs/a724")) return json(run());
        return undefined;
      },
    });
    renderAt("/runs/a724f4d3-a236-4a75-85d0-4d07028031c3");
    expect(
      await screen.findByRole("heading", { level: 1, name: "Run console" }),
    ).toBeInTheDocument();
    expect(await screen.findByText("Group same items")).toBeInTheDocument();
    expect(screen.getByText("689")).toBeInTheDocument();
    expect(await screen.findByText("GATE VALVE, 4 INCH, CLASS 150")).toBeInTheDocument();
    expect(screen.getByText("All key attributes match")).toBeInTheDocument();
    // the review queue is built: a real link to this run's groups
    expect(screen.getByRole("link", { name: "Open review queue" })).toHaveAttribute(
      "href",
      "/review?run=a724f4d3-a236-4a75-85d0-4d07028031c3",
    );
  });

  it("a failed run shows its error and Start again", async () => {
    signIn("MAKER", {
      handle: (u) =>
        u.includes("/runs/a724")
          ? json(
              run({
                status: "FAILED",
                error: "RuntimeError: boom",
                stats: { progress: { stage: "decide", done: 0, total: 9 } },
              }),
            )
          : undefined,
    });
    renderAt("/runs/a724f4d3-a236-4a75-85d0-4d07028031c3");
    expect(await screen.findByText(/failed during “decide”/)).toBeInTheDocument();
    expect(screen.getByText("RuntimeError: boom")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start again" })).toBeEnabled();
  });

  it("new run needs two CPSEs for an across-CPSE run", async () => {
    signIn("MAKER", {
      handle: (u) =>
        u.endsWith("/api/v1/batches")
          ? json([batch("a", "CPSE-A", "2026-10-05T00:00:00Z")])
          : undefined,
    });
    renderAt("/runs/new");
    expect(
      await screen.findByText("An across-CPSE run needs files from at least two CPSEs."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start run" })).toBeDisabled();
    fireEvent.click(screen.getByRole("radio", { name: /Within each CPSE/ }));
    expect(screen.getByRole("button", { name: "Start run" })).toBeEnabled();
  });
});
