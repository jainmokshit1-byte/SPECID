// S5 review queue, S6 cluster review (maker, checker, steward), S18 consents, S8 registry (WP1.8-1.10).

import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ClusterDetail } from "./api/review";
import { json, renderAt, signIn } from "./test-utils";

afterEach(() => {
  vi.restoreAllMocks();
  sessionStorage.clear();
  document.body.innerHTML = "";
});

const MEMBERS = [
  ["r1", "CPSE-A", "A0001", "VALVE GATE 4IN CL150 A216 WCB FLGD RF"],
  ["r2", "CPSE-B", "B0001", "GATE VALVE, 4 INCH, CLASS 150, ASTM A216 WCB, RAISED FACE FLANGED"],
  ["r3", "CPSE-C", "C0001", "GV 100NB 150# WCB RF FLANGED"],
].map(([id, cpse, code, text]) => ({
  record_id: id!,
  cpse: cpse!,
  legacy_code: code!,
  short_text: text!.slice(0, 40),
  long_text: text!,
  uom: "EA",
  manufacturer: null,
  mpn: null,
  annual_value: 1000,
  stock_qty: 0,
  category: "VALVE",
  attrs: {
    valve_type: "GATE",
    size_dn: 100,
    pressure_class: 150,
    body_material: "A216-WCB",
    end_connection: "FLANGED-RF",
    design_standard: id === "r1" ? null : null,
  },
  mapped_to: null,
}));

function cluster(patch: Partial<ClusterDetail> = {}): ClusterDetail {
  return {
    id: "c1",
    run_id: "run1",
    category: "VALVE",
    status: "PROPOSED",
    priority: 3000,
    cohesion: 0.98,
    flags: 0,
    critical: true,
    task: { id: "t1", state: "OPEN", proposed: null, made_by: null, checked_by: null },
    members: MEMBERS,
    pairs: [
      {
        id: "p1",
        rec_a: "r1",
        rec_b: "r2",
        verdict: "EQUIVALENT",
        route: "REVIEW",
        p_equiv: 0.98,
        text_sim: 0.62,
        lookalike: "HIDDEN_TWIN",
        reasons: ["critical class: maker-checker"],
        evidence: [
          {
            attr: "size_dn",
            level: "core",
            a: 100,
            b: 100,
            status: "MATCH",
            rule: "VALVE.size_dn",
            rule_text: "Compared as DN",
            note_a: "4 IN = DN100",
            note_b: null,
          },
          {
            attr: "design_standard",
            level: "ext",
            a: null,
            b: "API-600",
            status: "MISSING_ONE",
            rule: "VALVE.design_standard",
            rule_text: "Conflict vetoes",
            note_a: null,
            note_b: null,
          },
        ],
      },
    ],
    blocked: [],
    consents: [
      { cpse: "CPSE-A", decision: null, via: null, reason: null, by: null },
      { cpse: "CPSE-B", decision: null, via: null, reason: null, by: null },
      { cpse: "CPSE-C", decision: null, via: null, reason: null, by: null },
    ],
    decisions: [],
    proposal: {
      category: "VALVE",
      canonical_spec: {
        valve_type: "GATE",
        size_dn: 100,
        pressure_class: 150,
        body_material: "A216-WCB",
        end_connection: "FLANGED-RF",
      },
      short_desc_40: "VLV GATE 4IN CL150 A216-WCB FLGD RF",
      long_desc: "GATE VALVE, 4 IN (DN100), CLASS 150, ASTM A216 WCB, FLANGED RAISED FACE",
      class_path: ["PIPING", "VALVE", "GATE"],
      base_uom: "EA",
      variants: [],
    },
    cnmc: null,
    can: { propose: true, check: false, waiting_for_other_checker: false, consent: false },
    ...patch,
  };
}

function api(detail: ClusterDetail, posts: { url: string; body: unknown }[], reply: unknown) {
  return (url: string, init: RequestInit | undefined) => {
    if (init?.method === "POST" && url.includes("/clusters/c1/")) {
      posts.push({ url: url.split("/api/v1")[1]!, body: JSON.parse(String(init.body)) });
      return json(reply);
    }
    if (url.endsWith("/clusters/c1")) return json(detail);
    return undefined;
  };
}

describe("S6 cluster review", () => {
  it("shows the records side by side, the proposed code and only the maker's actions", async () => {
    const posts: { url: string; body: unknown }[] = [];
    signIn("MAKER", {
      handle: api(cluster(), posts, { state: "MADE", cnmc: null, waiting_for: [] }),
    });
    renderAt("/clusters/c1");
    expect(await screen.findByText("VLV GATE 4IN CL150 A216-WCB FLGD RF")).toBeInTheDocument();
    expect(screen.getByText("35 / 40")).toBeInTheDocument();
    expect(screen.getByText("PIPING › VALVE › GATE")).toBeInTheDocument();
    expect(screen.getByText("GV 100NB 150# WCB RF FLANGED")).toBeInTheDocument();
    expect(screen.getByText(/Critical item/)).toBeInTheDocument();
    // consent strip: one chip per CPSE, with words, not only colours
    const strip = screen.getByRole("list", { name: "Consent of each CPSE" });
    expect(within(strip).getAllByText("waiting")).toHaveLength(3);
    // evidence shows the deciding row first, with its conversion note on the matching one
    expect(screen.getByText("1 of 2 attributes match · 1 decide the outcome")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Confirm/ })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Approve as one item/ }));
    expect(
      await screen.findByText("Proposal saved. A checker confirms it next."),
    ).toBeInTheDocument();
    expect(posts).toEqual([{ url: "/clusters/c1/propose", body: { decision: "APPROVE" } }]);
  });

  it("reject asks for a comment of at least 5 characters", async () => {
    const posts: { url: string; body: unknown }[] = [];
    signIn("MAKER", {
      handle: api(cluster(), posts, { state: "MADE", cnmc: null, waiting_for: [] }),
    });
    renderAt("/clusters/c1");
    fireEvent.click(await screen.findByRole("button", { name: /Reject/ }));
    const dialog = await screen.findByRole("dialog");
    const send = within(dialog).getByRole("button", { name: "Propose reject" });
    expect(send).toBeDisabled();
    fireEvent.change(within(dialog).getByLabelText(/Comment/), {
      target: { value: "Different trim" },
    });
    fireEvent.click(send);
    await waitFor(() =>
      expect(posts).toEqual([
        { url: "/clusters/c1/propose", body: { decision: "REJECT", comment: "Different trim" } },
      ]),
    );
  });

  it("a checker confirms; the result says who still has to consent", async () => {
    const posts: { url: string; body: unknown }[] = [];
    const made = cluster({
      task: { id: "t1", state: "MADE", proposed: "APPROVE", made_by: "meera", checked_by: null },
      can: { propose: false, check: true, waiting_for_other_checker: false, consent: false },
    });
    signIn("CHECKER", {
      handle: api(made, posts, { state: "AWAITING_CONSENT", cnmc: null, waiting_for: ["CPSE-C"] }),
    });
    renderAt("/clusters/c1");
    expect(await screen.findByText(/meera proposed/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Confirm and issue code/ }));
    expect(
      await screen.findByText("Confirmed. Waiting for consent from CPSE-C."),
    ).toBeInTheDocument();
    expect(posts[0]).toEqual({ url: "/clusters/c1/check", body: { action: "CONFIRM" } });
  });

  it("the CPSE-C steward consents and the national code is issued", async () => {
    const posts: { url: string; body: unknown }[] = [];
    const waiting = cluster({
      task: {
        id: "t1",
        state: "AWAITING_CONSENT",
        proposed: "APPROVE",
        made_by: "meera",
        checked_by: "arjun",
      },
      can: { propose: false, check: false, waiting_for_other_checker: false, consent: true },
    });
    signIn(
      "CHECKER",
      { handle: api(waiting, posts, { state: "DONE", cnmc: "NMC-00000000018", waiting_for: [] }) },
      { username: "kavya", display_name: "Kavya", cpse_code: "CPSE-C", cpse_id: "cpse-C" },
    );
    renderAt("/clusters/c1");
    fireEvent.click(await screen.findByRole("button", { name: "Consent for my CPSE" }));
    expect(await screen.findByText("National code NMC-00000000018 issued.")).toBeInTheDocument();
    expect(posts[0]).toEqual({ url: "/clusters/c1/consent", body: { decision: "CONSENT" } });
  });

  it("the maker of a proposal is told another checker must confirm it", async () => {
    signIn("CHECKER", {
      handle: api(
        cluster({
          task: {
            id: "t1",
            state: "MADE",
            proposed: "APPROVE",
            made_by: "arjun",
            checked_by: null,
          },
          can: { propose: false, check: false, waiting_for_other_checker: true, consent: false },
        }),
        [],
        {},
      ),
    });
    renderAt("/clusters/c1");
    expect(
      await screen.findByText("You made this proposal. Another checker must confirm it."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Confirm/ })).not.toBeInTheDocument();
  });
});

describe("S5 queue, S18 consents, S8 registry", () => {
  it("the queue lists groups by priority with their CPSEs", async () => {
    signIn("MAKER", {
      handle: (u) =>
        u.includes("/clusters?")
          ? json({
              total: 1,
              items: [
                {
                  id: "c1",
                  category: "VALVE",
                  priority: 3000,
                  cohesion: 0.98,
                  flags: 1,
                  critical: true,
                  status: "PROPOSED",
                  state: "OPEN",
                  proposed: null,
                  made_by: null,
                  members: 3,
                  cpses: ["CPSE-A", "CPSE-B", "CPSE-C"],
                  sample_text: "VALVE GATE 4IN CL150",
                  updated_at: "2026-10-05T10:00:00Z",
                },
              ],
            })
          : undefined,
    });
    renderAt("/review");
    const link = await screen.findByRole("link", { name: /VALVE GATE 4IN CL150/ });
    expect(link).toHaveAttribute("href", "/clusters/c1");
    expect(screen.getByRole("tab", { name: "To propose" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("the consent queue shows my CPSE's codes waiting for an answer", async () => {
    signIn("CHECKER", {
      handle: (u) =>
        u.endsWith("/consents")
          ? json({
              total: 1,
              items: [
                {
                  cluster_id: "c1",
                  category: "VALVE",
                  waiting_since: "2026-10-05T10:00:00Z",
                  proposed_by: "meera",
                  confirmed_by: "arjun",
                  members: 3,
                  my_codes: ["C0001"],
                  sample_text: "VALVE GATE 4IN CL150",
                },
              ],
            })
          : undefined,
    });
    renderAt("/consents");
    expect(await screen.findByText("C0001")).toBeInTheDocument();
    expect(screen.getByText("meera / arjun")).toBeInTheDocument();
  });

  it("an INTEGRATOR can read the registry (DEC-19)", async () => {
    signIn("INTEGRATOR", {
      handle: (u) =>
        u.includes("/cnmc?")
          ? json({
              total: 1,
              items: [
                {
                  cnmc: "NMC-00000000018",
                  category: "VALVE",
                  short_desc_40: "VLV GATE 4IN CL150",
                  status: "ACTIVE",
                  issued_at: "2026-10-05T10:00:00Z",
                  codes: 3,
                  cpses: ["CPSE-A", "CPSE-B", "CPSE-C"],
                },
              ],
            })
          : undefined,
    });
    renderAt("/registry");
    expect(await screen.findByRole("link", { name: "NMC-00000000018" })).toHaveAttribute(
      "href",
      "/registry/NMC-00000000018",
    );
    expect(screen.getByText("1 national code")).toBeInTheDocument();
  });
});
