// Test helpers: render the app at a URL with a fake API (fetch stub) and an optional signed-in user.

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { vi } from "vitest";
import { App } from "./App";
import type { Me } from "./api/client";
import type { Role } from "./routes";

export const USERS: Record<Role, Me> = {
  MAKER: user("meera", "Meera", "MAKER", "CPSE-A"),
  CHECKER: user("arjun", "Arjun", "CHECKER", "CPSE-B"),
  ADMIN: user("admin", "Admin", "ADMIN", null),
  AUDITOR: user("auditor", "Auditor", "AUDITOR", null),
  INTEGRATOR: user("erp", "ERP integration", "INTEGRATOR", null),
};

function user(username: string, name: string, role: Role, cpse: string | null): Me {
  return {
    id: `id-${username}`,
    username,
    display_name: name,
    role,
    cpse_id: cpse ? `cpse-${cpse}` : null,
    cpse_code: cpse,
    must_change_password: false,
  };
}

export const HEALTH = {
  status: "ok",
  version: "0.1.0",
  git_commit: "abc1234",
  db: "ok",
  consent_mode: "ALL_PARTICIPANTS",
  embeddings_enabled: true,
  egress_guard: { enabled: true, installed: false },
};

type Handler = (url: string, init: RequestInit | undefined) => Response | undefined;

export interface Api {
  airgap?: object;
  health?: object;
  /** User returned by GET /me; null → 401. */
  me?: Me | null;
  /** Extra routes, tried first. */
  handle?: Handler;
}

export const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": status >= 400 ? "application/problem+json" : "application/json" },
  });

/** Stub fetch. Default: /system/airgap 404 (not built), /health unreachable, /me 401. */
export function mockApi(api: Api = {}) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = String(input);
    const custom = api.handle?.(url, init);
    if (custom) return custom;
    if (url.includes("/system/airgap"))
      return api.airgap ? json(api.airgap) : new Response("{}", { status: 404 });
    if (url.includes("/health") && api.health) return json(api.health);
    if (url.endsWith("/api/v1/me"))
      return api.me ? json(api.me) : json({ title: "Not signed in", status: 401 }, 401);
    return new Response("{}", { status: 503 });
  });
}

/** Pretend a login happened in this tab: a token in sessionStorage and /me answering `role`. */
export function signIn(role: Role, api: Omit<Api, "me"> = {}, patch: Partial<Me> = {}) {
  sessionStorage.setItem(
    "specid.session",
    JSON.stringify({
      token: `token-${role}`,
      expiresAt: new Date(Date.now() + 3600e3).toISOString(),
    }),
  );
  return mockApi({ ...api, me: { ...USERS[role], ...patch } });
}

/** Shows the router location so tests can assert redirects. */
// eslint-disable-next-line react-refresh/only-export-components -- test helper, never hot-reloaded
function LocationProbe() {
  const { pathname, search } = useLocation();
  return <div data-testid="location">{pathname + search}</div>;
}

export function renderAt(url: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[url]}>
        <App />
        <LocationProbe />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

export const location = () => screen.getByTestId("location").textContent;

export async function sidebarLabels() {
  const nav = await screen.findByRole("navigation", { name: "Main" });
  return within(nav)
    .queryAllByRole("link")
    .map((a) => a.textContent);
}
