// Minimal API client for /api/v1. Response types will be generated from OpenAPI (TRD TR-UI-02,
// `npm run gen:api`) once endpoints beyond /health exist.

export const API_BASE = "/api/v1";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { headers: { Accept: "application/json" } });
  if (!res.ok) throw new ApiError(res.status, `${res.status} ${res.statusText}`);
  return (await res.json()) as T;
}

/** API-24 GET /health (subset used by the shell). */
export interface Health {
  status: string;
  version: string;
  git_commit: string;
  db: string;
  consent_mode: string;
  embeddings_enabled: boolean;
}

/** API-32 GET /system/airgap (built in Phase 5). */
export interface AirGap {
  blocked_egress_attempts: number;
}
