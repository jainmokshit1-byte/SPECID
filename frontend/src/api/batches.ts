// PRD API-03 to API-06, API-33: uploads, mapping, ingest, quality report, purchase history.

import { apiGet, apiPost, apiPut, apiUpload } from "./client";

export const FIELDS = [
  "legacy_code",
  "short_text",
  "long_text",
  "uom",
  "mat_group",
  "manufacturer",
  "mpn",
  "plant",
  "criticality",
  "annual_value",
  "annual_qty",
  "stock_qty",
] as const;
export type Field = (typeof FIELDS)[number];

/** Plain words for each target field (UI/UX brief 1.4 rule 5). */
export const FIELD_LABEL: Record<Field, string> = {
  legacy_code: "Material code",
  short_text: "Short description",
  long_text: "Long description",
  uom: "Unit of measure",
  mat_group: "Material group",
  manufacturer: "Manufacturer",
  mpn: "Maker part number",
  plant: "Plant",
  criticality: "Critical item",
  annual_value: "Annual value (₹)",
  annual_qty: "Annual quantity",
  stock_qty: "Stock on hand",
};

export interface BatchQuality {
  rows: number;
  empty_short_text: number;
  short_text_over_40: number;
  duplicate_legacy_codes: number;
  completeness: Record<string, number>;
  category_share: Record<string, number>;
  core_parse_rate: Record<string, number>;
  uom_ambiguous: number;
  rejected_rows: number;
  uom_unknown: number;
  skipped_unchanged: number;
  health_score: number | null;
  health_components: Record<string, number>;
}

export interface Batch {
  id: string;
  cpse_code: string;
  filename: string;
  status: string;
  row_count: number | null;
  is_synthetic: boolean;
  column_mapping: Record<string, string> | null;
  quality: BatchQuality | null;
  created_at: string;
}

export interface BatchUploaded extends Batch {
  columns: string[];
  suggested_mapping: Record<string, string>;
  preset: string | null;
  sample_rows: Record<string, string>[];
  encoding: string | null;
  already_ingested: boolean;
}

export interface ProcurementResult {
  lines: number;
  unmatched: number;
  invalid: number;
  duplicates: number;
}

export const listBatches = () => apiGet<Batch[]>("/batches");
export const getBatch = (id: string) => apiGet<Batch>(`/batches/${id}`);

export function uploadBatch(file: File, opts: { cpse?: string; synthetic: boolean }) {
  const form = new FormData();
  form.append("file", file);
  form.append("is_synthetic", String(opts.synthetic));
  if (opts.cpse) form.append("cpse", opts.cpse);
  return apiUpload<BatchUploaded>("/batches", form);
}

export const saveMapping = (id: string, mapping: Record<string, string>) =>
  apiPut<Batch>(`/batches/${id}/mapping`, { column_mapping: mapping });

export const ingestBatch = (id: string) => apiPost<Batch>(`/batches/${id}/ingest`);

export function uploadProcurement(id: string, file: File) {
  const form = new FormData();
  form.append("file", file);
  return apiUpload<ProcurementResult>(`/batches/${id}/procurement`, form);
}

/** Health components in plain words, in display order. */
export const HEALTH_LABEL: Record<string, string> = {
  descriptions: "Descriptions present",
  unique_codes: "Unique material codes",
  recognised_category: "Category recognised",
  spec_completeness: "Key attributes read",
  uom_clean: "Units of measure clear",
};

export const CATEGORY_LABEL: Record<string, string> = {
  VALVE: "Valves",
  PIPE: "Pipes",
  FLANGE: "Flanges",
  FASTENER: "Fasteners",
  MOTOR: "Motors",
  GASKET: "Gaskets",
  UNRECOGNISED: "Not recognised",
};
