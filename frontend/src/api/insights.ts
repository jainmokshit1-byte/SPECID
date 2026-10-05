// PRD API-19 (search-before-create), API-25/26 (Look-alike Guard), API-31 (pooling), API-34
// (dashboard), API-22 (evaluation).

import type { Verdict } from "../lib/verdicts";
import { apiGet, apiPost } from "./client";
import type { EvidenceRow } from "./review";

export interface PriceGap {
  cluster_id: string;
  category: string | null;
  state: string | null;
  sample_text: string | null;
  cnmc: string | null;
  lowest_price: number;
  price_gap: number;
  by_cpse: { cpse: string; annual_qty: number; avg_price: number }[];
}

export interface StockMove {
  cluster_id: string;
  category: string | null;
  sample_text: string | null;
  cnmc: string | null;
  holder: string;
  holder_code: string;
  idle_stock: number;
  buyer: string;
  buyer_code: string;
  buyer_annual_qty: number;
  transferable: number;
  value_at_buyer_price: number;
}

export interface Money {
  groups_with_prices: number;
  total_price_gap: number;
  pooled_annual_spend: number;
  top_price_gaps: PriceGap[];
  stock_sharing: { suggestions: number; total_value: number; top: StockMove[] };
  note: string;
}

export interface Dashboard {
  run_id: string | null;
  empty?: boolean;
  is_synthetic: boolean;
  computed_at: string;
  mode: string;
  per_cpse: {
    cpse: string;
    records: number;
    annual_spend: number;
    health_score: number | null;
    in_groups: number;
    internal_duplicates: number;
  }[];
  groups: { total: number; cross_cpse: number; three_plus: number };
  verdicts: Partial<Record<Verdict, number>>;
  records: number;
  candidate_pairs: number;
  backlog: Record<string, number>;
  issued: number;
  by_category: { category: string; groups: number; records: number }[];
  top_groups: {
    id: string;
    category: string;
    priority: number | null;
    state: string;
    sample_text: string;
    cpses: string[];
    annual_spend: number;
  }[];
  money: Money;
}

export interface LookalikeItem {
  pair_id: string;
  verdict: Verdict;
  text_sim: number;
  category: string | null;
  a: { cpse: string; legacy_code: string; text: string };
  b: { cpse: string; legacy_code: string; text: string };
  decisive: EvidenceRow[];
}

export interface Lookalikes {
  run_id: string | null;
  kind: string;
  total: number;
  thresholds: { lookalike_min_sim: number | null; hidden_twin_max_sim: number | null };
  items: LookalikeItem[];
  histogram: { from: number; to: number; same: number; different: number; unknown: number }[];
  decisive_attributes: { attr: string; pairs: number }[];
}

export interface SearchCandidate {
  cnmc: string;
  short_desc_40: string | null;
  long_desc: string | null;
  cpses: string[];
  verdict: Verdict;
  reasons: string[];
  text_sim: number;
  missing: string[];
  conflicts: string[];
  evidence: EvidenceRow[];
}

export interface SearchResult {
  query: {
    category: string | null;
    class_source: string;
    attrs: Record<string, unknown>;
    repairs: string[];
  };
  candidates: SearchCandidate[];
  would_create_duplicate: boolean;
  recommended_action: "USE_EXISTING" | "SUPPLY_ATTRIBUTES" | "CREATE_NEW_ALLOWED";
  message: string;
  missing: string[];
}

const q = (run?: string | null) => (run ? `?run_id=${run}` : "");

export const getDashboard = (run?: string | null) => apiGet<Dashboard>(`/dashboard${q(run)}`);
export const getPooling = (run?: string | null) =>
  apiGet<Money & { run_id: string | null }>(`/pooling${q(run)}${run ? "&" : "?"}limit=50`);
export const getLookalikes = (kind: "vetoed" | "twins", run?: string | null) =>
  apiGet<Lookalikes>(`/radar/${kind === "vetoed" ? "lookalikes" : "hidden-twins"}${q(run)}`);
export const searchBeforeCreate = (text: string, mpn?: string, manufacturer?: string) =>
  apiPost<SearchResult>("/search-before-create", {
    text,
    mpn: mpn || undefined,
    manufacturer: manufacturer || undefined,
  });

// ---- evaluation
export interface MethodScore {
  tp: number;
  fp: number;
  fn: number;
  abstain: number;
  precision: number | null;
  recall_strict: number | null;
  recall_decided: number | null;
  coverage: number | null;
  false_merges: number;
  hard_negatives: number;
  false_merge_upper_95: number | null;
  tau?: number;
}

export interface EvalMetrics {
  honesty: string;
  config: Record<string, unknown>;
  dataset: Record<string, number>;
  blocking: {
    pair_completeness: number | null;
    reduction_ratio: number | null;
    hard_negatives_in_test: number;
    hard_negatives_not_reached: number;
  };
  methods: { specid: MethodScore; b1: MethodScore; b2: MethodScore };
  abstentions: { total: number; justified: number; rate: number };
  disagreements: Record<string, number>;
  per_category: Record<string, MethodScore>;
  timings_ms: Record<string, number>;
  error?: string;
}

export interface EvalRun {
  id: string;
  kind: string;
  seed: number | null;
  config: Record<string, unknown>;
  status: "QUEUED" | "RUNNING" | "DONE" | "FAILED";
  metrics: EvalMetrics | null;
  git_commit: string | null;
  created_at: string;
  created_by: string | null;
}

export const listEvals = () => apiGet<EvalRun[]>("/eval/runs");
export const getEval = (id: string) => apiGet<EvalRun>(`/eval/runs/${id}`);
export const startEval = (seed: number, n_entities = 1200) =>
  apiPost<EvalRun>("/eval/runs", { seed, n_entities, hard_negative_share: 0.5 });
