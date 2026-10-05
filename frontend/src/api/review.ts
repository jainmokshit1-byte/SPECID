// PRD API-10 to API-13, API-37: review queue, cluster review, pair evidence, consent.

import type { Verdict } from "../lib/verdicts";
import { apiGet, apiPost } from "./client";

export type TaskState = "OPEN" | "MADE" | "AWAITING_CONSENT" | "DONE";
export type Stage = "to_propose" | "to_check" | "awaiting_consent" | "done";

export interface QueueItem {
  id: string;
  category: string | null;
  priority: number | null;
  cohesion: number | null;
  flags: number;
  critical: boolean;
  status: string;
  state: TaskState;
  proposed: string | null;
  made_by: string | null;
  members: number;
  cpses: string[];
  sample_text: string | null;
  updated_at: string;
}

export interface EvidenceRow {
  attr: string;
  level: "core" | "ext";
  a: unknown;
  b: unknown;
  status: "MATCH" | "PARTIAL" | "CONFLICT" | "MISSING_ONE";
  rule: string;
  rule_text: string;
  note_a: string | null;
  note_b: string | null;
}

export interface ClusterMember {
  record_id: string;
  cpse: string;
  legacy_code: string;
  short_text: string;
  long_text: string | null;
  uom: string | null;
  manufacturer: string | null;
  mpn: string | null;
  annual_value: number | null;
  stock_qty: number | null;
  category: string | null;
  attrs: Record<string, unknown>;
  mapped_to: string | null;
}

export interface ClusterPair {
  id: string;
  rec_a: string;
  rec_b: string;
  verdict: Verdict;
  route: string;
  p_equiv: number | null;
  text_sim: number | null;
  lookalike: string | null;
  reasons: string[];
  evidence: EvidenceRow[];
}

export interface Consent {
  cpse: string;
  decision: "CONSENT" | "DECLINE" | null;
  via: string | null;
  reason: string | null;
  by: string | null;
}

export interface ClusterDetail {
  id: string;
  run_id: string;
  category: string | null;
  status: string;
  priority: number | null;
  cohesion: number | null;
  flags: number;
  critical: boolean;
  task: {
    id: string;
    state: TaskState;
    proposed: string | null;
    made_by: string | null;
    checked_by: string | null;
  };
  members: ClusterMember[];
  pairs: ClusterPair[];
  blocked: {
    rec_a: string;
    rec_b: string;
    blocking_a: string;
    blocking_b: string;
    reason: string;
  }[];
  consents: Consent[];
  decisions: { at: string; by: string; role: string; decision: string; comment: string | null }[];
  proposal: {
    category: string | null;
    canonical_spec: Record<string, unknown>;
    short_desc_40: string | null;
    long_desc: string | null;
    class_path: string[];
    base_uom: string | null;
    variants: [string | null, string | null][];
  };
  cnmc: string | null;
  can: { propose: boolean; check: boolean; waiting_for_other_checker: boolean; consent: boolean };
}

export interface Outcome {
  state: TaskState;
  cnmc: string | null;
  waiting_for: string[];
}

export interface PairCard {
  id: string;
  run_id: string;
  verdict: Verdict;
  route: string;
  p_equiv: number | null;
  text_sim: number | null;
  lookalike: string | null;
  baseline: { b1: boolean; b2: boolean; tau1: number; tau2: number } | null;
  channels: number;
  reasons: string[];
  evidence: EvidenceRow[];
  template_version: number | null;
  category: string | null;
  a: PairSide;
  b: PairSide;
}

export interface PairSide {
  record_id: string;
  cpse: string;
  legacy_code: string;
  short_text: string;
  long_text: string | null;
  manufacturer: string | null;
  mpn: string | null;
}

export interface ConsentItem {
  cluster_id: string;
  category: string | null;
  waiting_since: string;
  proposed_by: string | null;
  confirmed_by: string | null;
  members: number;
  my_codes: string[];
  sample_text: string | null;
}

export function listClusters(params: Record<string, string | number | undefined>) {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== "") q.set(k, String(v));
  return apiGet<{ total: number; items: QueueItem[] }>(`/clusters?${q.toString()}`);
}

export const getCluster = (id: string) => apiGet<ClusterDetail>(`/clusters/${id}`);
export const getPair = (id: string) => apiGet<PairCard>(`/pairs/${id}`);
export const consentQueue = () => apiGet<{ total: number; items: ConsentItem[] }>("/consents");

export const propose = (id: string, decision: string, comment?: string) =>
  apiPost<Outcome>(`/clusters/${id}/propose`, { decision, comment });
export const check = (id: string, action: "CONFIRM" | "OVERTURN", comment?: string) =>
  apiPost<Outcome>(`/clusters/${id}/check`, { action, comment });
export const answerConsent = (id: string, decision: "CONSENT" | "DECLINE", reason?: string) =>
  apiPost<Outcome>(`/clusters/${id}/consent`, { decision, reason });

/** Attribute names in plain words for the evidence and the spec cards. */
export const ATTR_LABEL: Record<string, string> = {
  valve_type: "Type",
  flange_type: "Type",
  fastener_type: "Type",
  motor_type: "Type",
  gasket_type: "Type",
  size_dn: "Size (DN)",
  pressure_class: "Pressure class",
  body_material: "Body material",
  material: "Material",
  winding_material: "Winding material",
  end_connection: "Ends",
  face: "Face",
  schedule: "Schedule",
  process: "Process",
  thread: "Thread",
  length_mm: "Length (mm)",
  strength: "Strength",
  head: "Head",
  coating: "Coating",
  power_kw: "Power (kW)",
  poles: "Poles",
  rpm: "Speed (rpm)",
  voltage: "Voltage",
  design_standard: "Design standard",
  trim: "Trim",
  end_finish: "End finish",
  filler: "Filler",
  ip: "Protection",
  mounting: "Mounting",
};

export const STATE_LABEL: Record<TaskState, string> = {
  OPEN: "To propose",
  MADE: "To check",
  AWAITING_CONSENT: "Waiting for consent",
  DONE: "Done",
};
