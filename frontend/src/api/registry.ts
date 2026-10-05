// PRD API-15, 17, 18, 35, 38: registry, crosswalk, exports, migration packs, change notices.

import { getToken } from "../auth/session";
import { API_BASE, ApiError, type Problem, apiGet, apiPost } from "./client";

export interface CnmcRow {
  cnmc: string;
  category: string;
  short_desc_40: string | null;
  status: string;
  issued_at: string;
  codes: number;
  cpses: string[];
}

export interface CrosswalkRow {
  cpse: string;
  legacy_code: string;
  short_text: string;
  relation: string;
  status: string;
  uom: string | null;
  uom_factor: number | null;
  migration_action: string | null;
  annual_value: number | null;
  stock_qty: number | null;
  approved_at: string;
}

export interface CnmcDetail {
  cnmc: string;
  category: string;
  class_path: string[];
  unspsc: string | null;
  hsn: string | null;
  canonical_spec: Record<string, unknown>;
  spec_completeness: number | null;
  variants: { manufacturer: string | null; mpn: string | null }[];
  base_uom: string | null;
  short_desc_40: string | null;
  long_desc: string | null;
  status: string;
  source_cluster: string | null;
  issued_by: string | null;
  issued_at: string;
  crosswalk: CrosswalkRow[];
  history: {
    ts: string;
    action: string;
    actor: string | null;
    after: Record<string, unknown> | null;
  }[];
}

export interface Notice {
  id: string;
  cpse: string;
  kind: string;
  object_type: string;
  object_id: string;
  summary: string;
  delta: Record<string, unknown>[];
  created_at: string;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
}

export function listCnmc(params: Record<string, string | number | undefined>) {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== "") q.set(k, String(v));
  return apiGet<{ total: number; items: CnmcRow[] }>(`/cnmc?${q.toString()}`);
}

export const getCnmc = (code: string) => apiGet<CnmcDetail>(`/cnmc/${code}`);

export const listNotices = (cpse?: string) =>
  apiGet<{ cpse: string; unacknowledged: number; items: Notice[] }>(
    `/change-notices${cpse ? `?cpse=${encodeURIComponent(cpse)}` : ""}`,
  );
export const ackNotice = (id: string) => apiPost<{ id: string }>(`/change-notices/${id}/ack`);

/** Download a file from the API with the session token, then save it with its own name. */
export async function download(path: string, fallbackName: string): Promise<void> {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    let problem: Problem = { status: res.status, title: res.statusText };
    try {
      problem = { ...problem, ...((await res.json()) as Problem) };
    } catch {
      // not JSON
    }
    throw new ApiError(res.status, problem);
  }
  const name = /filename="([^"]+)"/.exec(res.headers.get("content-disposition") ?? "")?.[1];
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = name ?? fallbackName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export const MIGRATION_LABEL: Record<string, string> = {
  RETAIN: "Keep",
  BLOCK_FOR_NEW_PROCUREMENT: "Block new buying",
  PHASE_OUT_WHEN_STOCK_ZERO: "Phase out when stock is zero",
};

export const NOTICE_LABEL: Record<string, string> = {
  CNMC_ISSUED: "National code issued",
  CNMC_MERGED: "Codes merged",
  CROSSWALK_REMOVED: "Code removed",
  CONSENT_DECLINED: "Consent declined",
  TEMPLATE_ACTIVATED: "Rule changed",
};
