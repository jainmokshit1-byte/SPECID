// Token storage (App Flow 4.2): kept in memory and mirrored in sessionStorage so it survives a
// refresh but not closing the tab. Never localStorage.

const KEY = "specid.session";

export interface StoredSession {
  token: string;
  /** ISO 8601 expiry from POST /auth/login. */
  expiresAt: string;
}

let memory: StoredSession | null = null;

function expired(s: StoredSession): boolean {
  return Date.parse(s.expiresAt) <= Date.now();
}

export function getToken(): string | null {
  if (memory === null) {
    try {
      const raw = sessionStorage.getItem(KEY);
      memory = raw ? (JSON.parse(raw) as StoredSession) : null;
    } catch {
      memory = null;
    }
  }
  if (memory && expired(memory)) {
    clearSession();
    return null;
  }
  return memory?.token ?? null;
}

export function setSession(s: StoredSession): void {
  memory = s;
  try {
    sessionStorage.setItem(KEY, JSON.stringify(s));
  } catch {
    // storage blocked: the in-memory copy still works for this page
  }
}

export function clearSession(): void {
  memory = null;
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    // nothing stored
  }
}
