// App Flow 3.3, 4.2–4.4: login, redirects, token storage, 401 handling, forced password change,
// No access panel, user menu, role homes.

import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Me } from "./api/client";
import { landingAfterLogin, roleHome } from "./auth/access";
import type { Role } from "./routes";
import { USERS, json, location, mockApi, renderAt, sidebarLabels, signIn } from "./test-utils";

const EXPIRES = () => new Date(Date.now() + 8 * 3600e3).toISOString();

/** Signed-out app whose login endpoint answers like the API. */
function loginApi(opts: { role?: Role; status?: number; me?: Partial<Me> } = {}) {
  const posts: { url: string; body: unknown; auth: string | null }[] = [];
  let signedIn = false;
  const spy = mockApi({
    handle: (url, init) => {
      const auth = new Headers(init?.headers).get("Authorization");
      if (init?.method === "POST")
        posts.push({ url, body: JSON.parse(String(init.body ?? "{}")), auth });
      if (url.endsWith("/auth/login")) {
        if (opts.status) return json({ title: "x", status: opts.status }, opts.status);
        signedIn = true;
        return json({
          access_token: "jwt-abc",
          token_type: "bearer",
          expires_at: EXPIRES(),
          role: opts.role ?? "MAKER",
          must_change_password: false,
        });
      }
      if (url.endsWith("/api/v1/me"))
        return signedIn && auth === "Bearer jwt-abc"
          ? json({ ...USERS[opts.role ?? "MAKER"], ...opts.me })
          : json({ status: 401 }, 401);
      return undefined;
    },
  });
  return { posts, spy };
}

async function submitLogin(username = "meera", password = "secret-password") {
  fireEvent.change(await screen.findByLabelText("Username"), { target: { value: username } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: password } });
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
}

describe("access rules", () => {
  it("role homes (App Flow 4.3)", () => {
    expect(roleHome("MAKER")).toBe("/");
    expect(roleHome("AUDITOR")).toBe("/");
    expect(roleHome("INTEGRATOR")).toBe("/search");
  });

  it.each([
    ["/audit", "AUDITOR", "/audit"],
    ["/audit?actor=meera", "ADMIN", "/audit?actor=meera"],
    ["/audit", "MAKER", "/"],
    ["/admin/users", "AUDITOR", "/"],
    ["//evil.example", "ADMIN", "/"],
    ["https://evil.example/", "ADMIN", "/"],
    ["/no-such-page", "ADMIN", "/"],
    [null, "INTEGRATOR", "/search"],
  ] as const)("next=%s for %s lands on %s", (next, role, want) => {
    expect(landingAfterLogin(next, role)).toBe(want);
  });
});

describe("auth flow (App Flow 4.2)", () => {
  it("any URL without a token goes to /login?next=<URL>", async () => {
    mockApi();
    renderAt("/audit?actor=meera");
    expect(await screen.findByRole("heading", { name: "SpecID" })).toBeInTheDocument();
    expect(location()).toBe("/login?next=%2Faudit%3Factor%3Dmeera");
  });

  it("a MAKER lands on Home; token in sessionStorage, never localStorage", async () => {
    const { posts } = loginApi({ role: "MAKER" });
    renderAt("/login");
    await submitLogin("meera", "secret-password");
    expect(await screen.findByRole("region", { name: "Next step" })).toBeInTheDocument();
    expect(location()).toBe("/");
    expect(posts[0]).toMatchObject({
      url: "/api/v1/auth/login",
      body: { username: "meera", password: "secret-password" },
      auth: null,
    });
    expect(sessionStorage.getItem("specid.session")).toContain("jwt-abc");
    expect(JSON.stringify({ ...localStorage })).not.toContain("jwt-abc");
  });

  it("goes to next when the role may open it", async () => {
    loginApi({ role: "AUDITOR" });
    renderAt("/login?next=%2Fabout");
    await submitLogin("auditor");
    await waitFor(() => expect(location()).toBe("/about"));
  });

  it("ignores next the role may not open and goes home", async () => {
    loginApi({ role: "MAKER" });
    renderAt("/login?next=%2Fadmin%2Fusers");
    await submitLogin();
    await waitFor(() => expect(location()).toBe("/"));
  });

  it("an INTEGRATOR lands on /search", async () => {
    loginApi({ role: "INTEGRATOR" });
    renderAt("/login");
    await submitLogin("erp");
    await waitFor(() => expect(location()).toBe("/search"));
    expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent(
      "Search-before-create",
    );
  });

  it.each([
    [401, "Wrong username or password"],
    [429, "Too many attempts, wait 1 minute"],
  ])("a %i stays on /login with the App Flow message", async (status, message) => {
    loginApi({ status });
    renderAt("/login");
    await submitLogin();
    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(location()).toBe("/login");
    expect(screen.getByLabelText("Password")).toHaveValue("");
    expect(sessionStorage.getItem("specid.session")).toBeNull();
  });

  it("an API 401 later signs out and returns to /login?next=<current URL>", async () => {
    sessionStorage.setItem(
      "specid.session",
      JSON.stringify({ token: "expired-on-server", expiresAt: EXPIRES() }),
    );
    mockApi({ me: null });
    renderAt("/templates");
    await waitFor(() => expect(location()).toBe("/login?next=%2Ftemplates"));
    expect(sessionStorage.getItem("specid.session")).toBeNull();
  });

  it("a token past its expiry is dropped before any call", async () => {
    sessionStorage.setItem(
      "specid.session",
      JSON.stringify({ token: "old", expiresAt: new Date(Date.now() - 1000).toISOString() }),
    );
    const spy = mockApi({ me: USERS.ADMIN });
    renderAt("/");
    await waitFor(() => expect(location()).toBe("/login?next=%2F"));
    expect(spy.mock.calls.map((c) => String(c[0]))).not.toContain("/api/v1/me");
  });

  it("sends the Bearer token on API calls", async () => {
    const spy = signIn("ADMIN");
    renderAt("/");
    await screen.findByRole("region", { name: "Next step" });
    const me = spy.mock.calls.find((c) => String(c[0]) === "/api/v1/me")!;
    expect(new Headers(me[1]?.headers).get("Authorization")).toBe("Bearer token-ADMIN");
  });
});

describe("forced password change (App Flow 4.2)", () => {
  it("appears when must_change_password is true and cannot be dismissed", async () => {
    signIn("CHECKER", {}, { must_change_password: true });
    renderAt("/");
    const dialog = await screen.findByRole("dialog", { name: "Change password" });
    expect(within(dialog).queryByRole("button", { name: "Close" })).not.toBeInTheDocument();
    expect(within(dialog).queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();
    fireEvent.keyDown(dialog, { key: "Escape" });
    expect(screen.getByRole("dialog", { name: "Change password" })).toBeInTheDocument();
  });

  it.each(["MAKER", "CHECKER", "ADMIN", "AUDITOR", "INTEGRATOR"] as const)(
    "never appears for demo user %s when SEED_DEMO_USERS=true (flag off from the API)",
    async (role) => {
      signIn(role); // seed sets must_change_password = not SEED_DEMO_USERS
      renderAt(roleHome(role));
      await screen.findByRole("heading", { level: 1 });
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    },
  );

  it("posts /me/password, reloads the user and closes", async () => {
    let forced = true;
    const posts: unknown[] = [];
    sessionStorage.setItem("specid.session", JSON.stringify({ token: "t", expiresAt: EXPIRES() }));
    mockApi({
      handle: (url, init) => {
        if (url.endsWith("/me/password")) {
          posts.push(JSON.parse(String(init?.body)));
          forced = false;
          return new Response(null, { status: 204 });
        }
        if (url.endsWith("/api/v1/me"))
          return json({ ...USERS.MAKER, must_change_password: forced });
        return undefined;
      },
    });
    renderAt("/");
    const dialog = await screen.findByRole("dialog", { name: "Change password" });
    fireEvent.change(within(dialog).getByLabelText("Current password"), {
      target: { value: "temporary-pass-1" },
    });
    fireEvent.change(within(dialog).getByLabelText("New password"), {
      target: { value: "short" },
    });
    fireEvent.change(within(dialog).getByLabelText("Repeat new password"), {
      target: { value: "short" },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Change password" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("at least 10 characters");
    for (const label of ["New password", "Repeat new password"])
      fireEvent.change(within(dialog).getByLabelText(label), {
        target: { value: "my-own-password-1" },
      });
    fireEvent.click(within(dialog).getByRole("button", { name: "Change password" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(posts).toEqual([
      { current_password: "temporary-pass-1", new_password: "my-own-password-1" },
    ]);
  });
});

describe("No access (App Flow 4.4)", () => {
  it("a MAKER opening /admin/users stays on the URL and sees the panel", async () => {
    signIn("MAKER");
    renderAt("/admin/users");
    expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent("Users");
    const panel = screen.getByRole("alert");
    expect(panel).toHaveTextContent("No access");
    expect(panel).toHaveTextContent("The MAKER role cannot open this page");
    expect(within(panel).getByRole("link", { name: "Go to your home page" })).toHaveAttribute(
      "href",
      "/",
    );
    expect(location()).toBe("/admin/users");
  });

  it("an INTEGRATOR opening Home is offered /search", async () => {
    signIn("INTEGRATOR");
    renderAt("/");
    const panel = await screen.findByRole("alert");
    expect(within(panel).getByRole("link")).toHaveAttribute("href", "/search");
    expect(await sidebarLabels()).toEqual([]); // DEC-16: nothing built for INTEGRATOR yet
  });
});

describe("user menu (App Flow 3.3)", () => {
  it("shows name, role and CPSE; Change password; Logout clears the token", async () => {
    signIn("MAKER");
    renderAt("/");
    const trigger = await screen.findByRole("button", { name: /Meera/ });
    fireEvent.keyDown(trigger, { key: "Enter" });
    const menu = await screen.findByRole("menu");
    expect(menu).toHaveTextContent("Meera");
    expect(menu).toHaveTextContent("MAKER · CPSE-A");
    expect(within(menu).getByRole("menuitem", { name: "Change password" })).toBeInTheDocument();
    fireEvent.click(within(menu).getByRole("menuitem", { name: "Logout" }));
    await waitFor(() => expect(location()).toBe("/login"));
    expect(sessionStorage.getItem("specid.session")).toBeNull();
  });

  it("an ADMIN has no CPSE", async () => {
    signIn("ADMIN");
    renderAt("/");
    fireEvent.keyDown(await screen.findByRole("button", { name: /Admin/ }), { key: "Enter" });
    const menu = await screen.findByRole("menu");
    expect(menu).toHaveTextContent("ADMIN");
    expect(menu).not.toHaveTextContent("CPSE");
  });

  it("Change password opens a dialog that can be cancelled", async () => {
    signIn("CHECKER");
    renderAt("/");
    fireEvent.keyDown(await screen.findByRole("button", { name: /Arjun/ }), { key: "Enter" });
    fireEvent.click(await screen.findByRole("menuitem", { name: "Change password" }));
    const dialog = await screen.findByRole("dialog", { name: "Change password" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });
});
