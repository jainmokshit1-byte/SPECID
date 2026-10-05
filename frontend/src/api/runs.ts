// PRD API-07 to API-09: harmonisation runs.

import type { Verdict } from "../lib/verdicts";
import { apiGet, apiPost } from "./client";

export type RunMode = "CROSS_CPSE" | "WITHIN_CPSE" | "BOTH";
export type RunStatus = "QUEUED" | "RUNNING" | "CANCELLING" | "CANCELLED" | "DONE" | "FAILED";

export interface RunStats {
  progress?: { stage: string; done: number; total: number };
  records?: number;
  specs_parsed?: number;
  unclassified?: number;
  classified_by_ml?: number;
  candidate_pairs?: number;
  channels?: Partial<Record<"B" | "L" | "D" | "M", number>>;
  verdicts?: Partial<Record<Verdict, number>>;
  clusters?: number;
  blocked_edges?: number;
  timings_ms?: Record<string, number>;
  blocked_egress?: number;
  ai_provider?: string | null;
  ai_records_asked?: number | null;
  ai_values_accepted?: number | null;
  ai_values_rejected?: number | null;
  dense_pairs?: number | null;
}

export interface Run {
  id: string;
  status: RunStatus;
  mode: RunMode;
  batch_ids: string[];
  config: Record<string, unknown>;
  stats: RunStats | null;
  error: string | null;
  started_by: string | null;
  started_at: string;
  finished_at: string | null;
}

export interface Pair {
  id: string;
  rec_a: string;
  rec_b: string;
  cpse_a: string;
  code_a: string;
  text_a: string;
  cpse_b: string;
  code_b: string;
  text_b: string;
  verdict: Verdict;
  route: string;
  p_equiv: number | null;
  text_sim: number | null;
  lookalike: "LOOKALIKE_VETOED" | "HIDDEN_TWIN" | null;
  channels: number;
  reasons: string[];
}

export interface PairPage {
  total: number;
  items: Pair[];
}

export const ACTIVE: RunStatus[] = ["QUEUED", "RUNNING", "CANCELLING"];

export const MODE_LABEL: Record<RunMode, string> = {
  CROSS_CPSE: "Across CPSEs",
  WITHIN_CPSE: "Within each CPSE",
  BOTH: "Both",
};

export const MODE_HINT: Record<RunMode, string> = {
  CROSS_CPSE: "Finds the same item held by different CPSEs: the national-code case.",
  WITHIN_CPSE: "Finds duplicate codes inside each CPSE's own master.",
  BOTH: "Both at once.",
};

export const CHANNEL_LABEL: Record<string, string> = {
  B: "Same category and size",
  L: "Similar wording",
  D: "Similar meaning (AI)",
  M: "Same maker part number",
};

export const listRuns = () => apiGet<Run[]>("/runs");
export const getRun = (id: string) => apiGet<Run>(`/runs/${id}`);
export const startRun = (
  batch_ids: string[],
  mode: RunMode,
  options: Record<string, unknown> = {},
) => apiPost<Run>("/runs", { batch_ids, mode, options });
export const cancelRun = (id: string) => apiPost<Run>(`/runs/${id}/cancel`);

export function listPairs(id: string, params: Record<string, string | number | undefined>) {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== "") q.set(k, String(v));
  return apiGet<PairPage>(`/runs/${id}/pairs?${q.toString()}`);
}

export function durationMs(run: Run, now: number = Date.now()): number | null {
  const start = Date.parse(run.started_at);
  if (!Number.isFinite(start)) return null;
  const end = run.finished_at ? Date.parse(run.finished_at) : now;
  return Math.max(0, end - start);
}

export function formatDuration(ms: number | null): string {
  if (ms === null) return "–";
  if (ms < 1000) return `${ms} ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)} s`;
  return `${Math.floor(s / 60)} min ${Math.round(s % 60)} s`;
}
