// API client for /api/v1. Sends the Bearer token, parses RFC 7807 problems (TRD TR-API-03) and
// reports a 401 so the app can send the user to /login?next= (App Flow 4.4). Response types will
// be generated from OpenAPI (TRD TR-UI-02, `npm run gen:api`) once the API settles.

import { clearSession, getToken } from "../auth/session";

export const API_BASE = "/api/v1";

/** Fired on any 401 except from the login call itself. */
export const UNAUTHORIZED_EVENT = "specid:unauthorized";

export interface Problem {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  errors?: { loc: string[]; msg: string }[];
}

export class ApiError extends Error {
  readonly status: number;
  readonly problem: Problem;

  constructor(status: number, problem: Problem) {
    super(problem.detail || problem.title || `HTTP ${status}`);
    this.status = status;
    this.problem = problem;
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const form = body instanceof FormData;
  if (body !== undefined && !form) headers["Content-Type"] = "application/json";
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : form ? body : JSON.stringify(body),
  });
  if (!res.ok) {
    let problem: Problem = { status: res.status, title: res.statusText };
    try {
      problem = { ...problem, ...((await res.json()) as Problem) };
    } catch {
      // not JSON
    }
    if (res.status === 401 && path !== "/auth/login") {
      clearSession();
      window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
    }
    throw new ApiError(res.status, problem);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const apiGet = <T>(path: string) => request<T>("GET", path);
export const apiPost = <T>(path: string, body?: unknown) => request<T>("POST", path, body ?? {});
export const apiPut = <T>(path: string, body: unknown) => request<T>("PUT", path, body);
/** multipart/form-data upload (the browser sets the boundary). */
export const apiUpload = <T>(path: string, form: FormData) => request<T>("POST", path, form);

/** API-24 GET /health (subset used by the shell). */
export interface Health {
  status: string;
  version: string;
  git_commit: string;
  db: string;
  consent_mode: string;
  embeddings_enabled: boolean;
  egress_guard: { enabled: boolean; installed: boolean };
  demo_mode?: boolean;
  demo_status?: "off" | "preparing" | "ready" | "failed" | null;
  ai_provider?: string;
  ai_ready?: boolean;
  classifier?: boolean;
}

/** API-32 GET /system/airgap. */
export interface AirGap {
  mode?: string;
  egress_guard?: { enabled: boolean; installed: boolean };
  blocked_egress_attempts: number;
}

/** API-01 POST /auth/login. */
export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_at: string;
  role: string;
  must_change_password: boolean;
}

/** API-02 GET /me. */
export interface Me {
  id: string;
  username: string;
  display_name: string | null;
  role: import("../routes").Role;
  cpse_id: string | null;
  cpse_code: string | null;
  must_change_password: boolean;
}
