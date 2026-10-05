// S12 Audit (App Flow 5.13, J7) and S16 Users (App Flow 5.15, DEC-14); sidebar after Phase 3.

import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { AuditEvent } from "./api/audit";
import { cursorBefore } from "./api/audit";
import { formatDateTime } from "./lib/format";
import { json, location, renderAt, sidebarLabels, signIn } from "./test-utils";

function event(id: number, patch: Partial<AuditEvent> = {}): AuditEvent {
  return {
    id,
    ts: "2026-10-03T04:49:00.123456+00:00",
    actor_id: "id-meera",
    actor: "meera",
    action: "LOGIN_SUCCEEDED",
    object_type: "app_user",
    object_id: "id-meera",
    before: null,
    after: { username: "meera", role: "MAKER" },
    prev_hash: id > 1 ? `h${id - 1}`.padEnd(64, "0") : null,
    hash: `h${id}`.padEnd(64, "0"),
    ...patch,
  };
}

describe("sidebar with Home, Data, Review, Registry, Audit and Users built", () => {
  it.each([
    ["ADMIN", ["Home", "Data", "Registry", "Rules"], ["Audit", "Users"]],
    ["AUDITOR", ["Home", "Registry", "Rules"], ["Audit"]],
    ["MAKER", ["Home", "Data", "Review", "Registry"], null],
    ["CHECKER", ["Home", "Data", "Review", "Registry"], null],
  ] as const)("%s sees %j", async (role, items, ruleTabs) => {
    signIn(role, {
      handle: (u) => (u.includes("/audit") ? json({ items: [], next_cursor: null }) : undefined),
    });
    renderAt(ruleTabs ? "/audit" : "/");
    expect(await sidebarLabels()).toEqual(items);
    await screen.findByRole("heading", { level: 1 });
    const section = screen.queryByRole("navigation", { name: "Section" });
    if (ruleTabs && ruleTabs.length > 1) {
      expect(
        within(section!)
          .getAllByRole("link")
          .map((t) => t.textContent),
      ).toEqual(ruleTabs);
    } else {
      expect(section).toBeNull(); // one visible tab → no tab bar (Rulebook not built yet)
    }
    if (ruleTabs) {
      fireEvent.click(within(screen.getByRole("navigation", { name: "Main" })).getByText("Rules"));
      await waitFor(() => expect(location()).toBe("/audit"));
    }
  });

  it("the AUDITOR's Next-step card opens S12", async () => {
    signIn("AUDITOR");
    renderAt("/");
    const card = await screen.findByRole("region", { name: "Next step" });
    expect(card).toHaveTextContent("Verify the audit chain");
    expect(within(card).getByRole("link", { name: "Open audit" })).toHaveAttribute(
      "href",
      "/audit",
    );
    expect(within(card).queryByRole("list")).not.toBeInTheDocument();
  });
});

describe("S12 Audit", () => {
  function auditApi(opts: { items?: AuditEvent[]; verify?: object } = {}) {
    const urls: string[] = [];
    const spy = signIn("AUDITOR", {
      handle: (url) => {
        if (url.includes("/audit/verify"))
          return json(opts.verify ?? { ok: true, events: 1043, first_bad_id: null });
        if (url.includes("/api/v1/audit")) {
          urls.push(url);
          return json({ items: opts.items ?? [event(2), event(1)], next_cursor: null });
        }
        return undefined;
      },
    });
    return { urls, spy };
  }

  it("lists LOGIN_SUCCEEDED events with IST times; a row expands to before/after JSON", async () => {
    auditApi();
    renderAt("/audit");
    expect(await screen.findByRole("heading", { level: 1, name: "Audit" })).toBeInTheDocument();
    const table = await screen.findByRole("table");
    expect(within(table).getAllByText("LOGIN_SUCCEEDED")).toHaveLength(2);
    expect(within(table).getAllByText("03 Oct 2026, 10:19")).toHaveLength(2);
    fireEvent.click(screen.getByRole("button", { name: "Show details of event 2" }));
    expect(screen.getByText("After")).toBeInTheDocument();
    expect(screen.getByText(/"role": "MAKER"/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Hide details of event 2" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
  });

  it("Verify chain shows 'Chain intact (n events)'", async () => {
    auditApi();
    renderAt("/audit");
    await screen.findByRole("table");
    fireEvent.click(await screen.findByRole("button", { name: "Verify chain" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Chain intact (1,043 events)");
  });

  it("a broken chain shows the event id with a link to that row", async () => {
    const { urls } = auditApi({
      verify: { ok: false, events: 6, first_bad_id: 7 },
      items: [event(9), event(8), event(7)],
    });
    renderAt("/audit");
    fireEvent.click(await screen.findByRole("button", { name: "Verify chain" }));
    const banner = await screen.findByRole("alert");
    expect(banner).toHaveTextContent("Chain broken at event #7");
    fireEvent.click(within(banner).getByRole("link", { name: "Show event #7" }));
    await waitFor(() =>
      expect(decodeURIComponent(urls.at(-1)!)).toContain(`cursor=${cursorBefore(8)}`),
    );
    expect(
      await screen.findByRole("button", { name: "Hide details of event 7" }),
    ).toBeInTheDocument();
  });

  it("filters go to the query string and to the API; date range is IST days", async () => {
    const { urls } = auditApi();
    renderAt("/audit");
    await screen.findByRole("table");
    fireEvent.change(screen.getByLabelText("Action"), { target: { value: "LOGIN_FAILED" } });
    fireEvent.change(screen.getByLabelText("From (IST)"), { target: { value: "2026-10-03" } });
    await waitFor(() => expect(location()).toBe("/audit?action=LOGIN_FAILED&from=2026-10-03"));
    await waitFor(() => expect(urls.at(-1)).toContain("action=LOGIN_FAILED"));
    expect(decodeURIComponent(urls.at(-1)!)).toContain("since=2026-10-02T18:30:00.000Z");
  });

  it("empty states: no events, and no results for filters with Clear filters", async () => {
    auditApi({ items: [] });
    renderAt("/audit");
    expect(await screen.findByText("No events recorded.")).toBeInTheDocument();
    document.body.innerHTML = "";
    renderAt("/audit?action=RUN_DONE");
    expect(await screen.findByText("No results for these filters.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    await waitFor(() => expect(location()).toBe("/audit"));
  });

  it("a MAKER gets the No access panel and no API call for the log", async () => {
    const spy = signIn("MAKER");
    renderAt("/audit");
    expect(await screen.findByRole("alert")).toHaveTextContent("No access");
    expect(spy.mock.calls.map((c) => String(c[0])).some((u) => u.includes("/audit"))).toBe(false);
  });
});

describe("S16 Users", () => {
  const LIST = {
    items: [
      {
        id: "id-admin",
        username: "admin",
        display_name: "Admin",
        role: "ADMIN",
        cpse_id: null,
        cpse_code: null,
        is_active: true,
        must_change_password: false,
        last_login_at: "2026-10-03T04:49:00Z",
        created_at: "2026-10-03T04:00:00Z",
      },
      {
        id: "id-meera",
        username: "meera",
        display_name: "Meera",
        role: "MAKER",
        cpse_id: "c-a",
        cpse_code: "CPSE-A",
        is_active: true,
        must_change_password: false,
        last_login_at: null,
        created_at: "2026-10-03T04:00:00Z",
      },
    ],
    cpses: [
      { id: "c-a", code: "CPSE-A", name: "Synthetic CPSE-A" },
      { id: "c-b", code: "CPSE-B", name: "Synthetic CPSE-B" },
    ],
  };

  function usersApi(
    answer: (url: string, body: unknown) => Response | undefined = () => undefined,
  ) {
    const posts: { url: string; body: unknown }[] = [];
    signIn("ADMIN", {
      handle: (url, init) => {
        if (init?.method === "POST") {
          const body = JSON.parse(String(init.body ?? "{}"));
          posts.push({ url, body });
          return answer(url, body) ?? json({ ...LIST.items[1], must_change_password: true });
        }
        if (url.endsWith("/api/v1/users")) return json(LIST);
        return undefined;
      },
    });
    return posts;
  }

  it("lists users with role, CPSE, last login; no Disable on the admin's own row", async () => {
    usersApi();
    renderAt("/admin/users");
    const table = await screen.findByRole("table");
    const rows = within(table).getAllByRole("row");
    expect(rows[1]).toHaveTextContent("admin");
    expect(rows[1]).toHaveTextContent(formatDateTime("2026-10-03T04:49:00Z"));
    expect(rows[2]).toHaveTextContent("MAKER");
    expect(rows[2]).toHaveTextContent("CPSE-A");
    expect(rows[2]).toHaveTextContent("never");
    expect(screen.queryByRole("button", { name: "Disable admin" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Disable meera" })).toBeInTheDocument();
  });

  it("Add user posts the form and confirms", async () => {
    const posts = usersApi();
    renderAt("/admin/users");
    fireEvent.click(await screen.findByRole("button", { name: "Add user" }));
    const dialog = await screen.findByRole("dialog", { name: "Add user" });
    fireEvent.change(within(dialog).getByLabelText("Username"), { target: { value: "ravi" } });
    fireEvent.change(within(dialog).getByLabelText("Role"), { target: { value: "CHECKER" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Add user" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("Choose the CPSE");
    fireEvent.change(within(dialog).getByLabelText("CPSE"), { target: { value: "c-b" } });
    fireEvent.change(within(dialog).getByLabelText("Temporary password"), {
      target: { value: "temporary-pass-1" },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Add user" }));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "must change the temporary password at first login",
    );
    expect(posts).toEqual([
      {
        url: "/api/v1/users",
        body: {
          username: "ravi",
          display_name: null,
          role: "CHECKER",
          cpse_id: "c-b",
          temporary_password: "temporary-pass-1",
        },
      },
    ]);
  });

  it("shows the API's problem detail, e.g. a taken username", async () => {
    usersApi(() =>
      json({ title: "Username taken", detail: "The username 'meera' is taken.", status: 409 }, 409),
    );
    renderAt("/admin/users");
    fireEvent.click(await screen.findByRole("button", { name: "Add user" }));
    const dialog = await screen.findByRole("dialog", { name: "Add user" });
    fireEvent.change(within(dialog).getByLabelText("Username"), { target: { value: "meera" } });
    fireEvent.change(within(dialog).getByLabelText("CPSE"), { target: { value: "c-a" } });
    fireEvent.change(within(dialog).getByLabelText("Temporary password"), {
      target: { value: "temporary-pass-1" },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Add user" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "The username 'meera' is taken.",
    );
  });

  it("Reset password and Disable call their endpoints", async () => {
    const posts = usersApi();
    renderAt("/admin/users");
    fireEvent.click(await screen.findByRole("button", { name: "Reset password of meera" }));
    let dialog = await screen.findByRole("dialog", { name: "Reset password of meera" });
    fireEvent.change(within(dialog).getByLabelText("Temporary password"), {
      target: { value: "temporary-pass-2" },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Reset password" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Password of meera reset");
    fireEvent.click(screen.getByRole("button", { name: "Disable meera" }));
    dialog = await screen.findByRole("dialog", { name: "Disable meera?" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Disable user" }));
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("meera is disabled"));
    expect(posts.map((p) => p.url)).toEqual([
      "/api/v1/users/id-meera/reset-password",
      "/api/v1/users/id-meera/disable",
    ]);
    expect(posts[0]!.body).toEqual({ temporary_password: "temporary-pass-2" });
  });
});
