// API-23 `GET /audit`, `GET /audit/verify` and the Backend Schema 9.2 action catalogue.

export interface AuditEvent {
  id: number;
  ts: string;
  actor_id: string | null;
  actor: string | null;
  action: string;
  object_type: string;
  object_id: string;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  prev_hash: string | null;
  hash: string;
}

export interface AuditPage {
  items: AuditEvent[];
  next_cursor: string | null;
}

export interface VerifyResult {
  ok: boolean;
  events: number;
  first_bad_id: number | null;
}

/** Backend Schema 9.2, plus PASSWORD_CHANGED (DECISIONS.md DEC-15). */
export const AUDIT_ACTIONS = [
  "USER_CREATED",
  "USER_ROLE_CHANGED",
  "USER_DISABLED",
  "PASSWORD_RESET",
  "PASSWORD_CHANGED",
  "LOGIN_SUCCEEDED",
  "LOGIN_FAILED",
  "API_KEY_CREATED",
  "API_KEY_REVOKED",
  "BATCH_UPLOADED",
  "BATCH_MAPPED",
  "BATCH_INGESTED",
  "BATCH_PURGED",
  "PROCUREMENT_UPLOADED",
  "RUN_STARTED",
  "RUN_CANCELLED",
  "RUN_DONE",
  "RUN_FAILED",
  "REVIEW_PROPOSED",
  "REVIEW_CONFIRMED",
  "REVIEW_OVERTURNED",
  "CONSENT_GIVEN",
  "CONSENT_DECLINED",
  "CHANGE_NOTICE_CREATED",
  "CHANGE_NOTICE_ACKNOWLEDGED",
  "CNMC_ISSUED",
  "CNMC_MERGED",
  "CROSSWALK_REMOVED",
  "MIGRATION_ACTIONS_SET",
  "EXPORT_DOWNLOADED",
  "ATTRIBUTE_SUPPLIED",
  "SUBSTITUTE_APPROVED",
  "SUBSTITUTE_REJECTED",
  "SEARCH_CREATE_OVERRIDE",
  "TEMPLATE_DRAFTED",
  "TEMPLATE_IMPACT_PREVIEWED",
  "TEMPLATE_ACTIVATED",
  "DICTIONARY_ACTIVATED",
  "EVAL_STARTED",
  "EVAL_DONE",
  "AUDIT_VERIFIED",
] as const;

export const AUDIT_OBJECT_TYPES = [
  "app_user",
  "api_key",
  "upload_batch",
  "run",
  "review_task",
  "review_consent",
  "change_notice",
  "cnmc",
  "crosswalk",
  "export",
  "material_record",
  "substitution",
  "search",
  "template",
  "dictionary",
  "eval_run",
  "audit_event",
] as const;

/** Cursor that lists events older than `id`. TRD TR-API-04 defines the cursor as the base64 of
 * the last sort key (here the event id), as built by `services/audit.encode_cursor`. */
export function cursorBefore(id: number): string {
  return btoa(String(id)).replace(/\+/g, "-").replace(/\//g, "_");
}
