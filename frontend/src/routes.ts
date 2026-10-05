// Route table: 03 App Flow v1.2 section 2 is authoritative (TRD TR-UI-01).
// `phase` = Implementation Plan phase that builds the screen (S17 assigned to Phase 7 by DECISIONS.md DEC-07);
// null = not scheduled.

export type Role = "MAKER" | "CHECKER" | "ADMIN" | "AUDITOR" | "INTEGRATOR";

export interface RouteDef {
  path: string;
  screen: string;
  title: string;
  purpose: string;
  roles: Role[];
  pri: "P0" | "P1";
  prd: string;
  phase: number | null;
}

const ALL: Role[] = ["MAKER", "CHECKER", "ADMIN", "AUDITOR", "INTEGRATOR"];
const MCA: Role[] = ["MAKER", "CHECKER", "ADMIN"];
const MCAA: Role[] = ["MAKER", "CHECKER", "ADMIN", "AUDITOR"];

export const LOGIN_ROUTE: RouteDef = {
  path: "/login",
  screen: "S1",
  title: "Login",
  purpose: "Username + password",
  roles: ALL,
  pri: "P0",
  prd: "FR-1301",
  phase: 3,
};

/** Every route rendered inside the app shell (sidebar, top bar, footer, ribbon). */
export const SHELL_ROUTES: RouteDef[] = [
  {
    path: "/",
    screen: "S0",
    title: "Home",
    purpose:
      "Duplicates per CPSE, data quality, cross-CPSE clusters, review backlog, top clusters, demand aggregation",
    roles: MCAA,
    pri: "P0",
    prd: "FR-1201, FR-1203",
    phase: 7,
  },
  {
    path: "/upload",
    screen: "S2",
    title: "Upload & mapping",
    purpose: "Upload a CPSE master file (and optional procurement history), map columns",
    roles: MCA,
    pri: "P0",
    prd: "FR-101–107, FR-1005",
    phase: 5,
  },
  {
    path: "/batches/:batchId/quality",
    screen: "S3",
    title: "Data-quality report",
    purpose: "Completeness, parse rate per category, long-text counts, ambiguous UoM",
    roles: MCA,
    pri: "P0",
    prd: "FR-103",
    phase: 5,
  },
  {
    path: "/runs",
    screen: "S4a",
    title: "Matching runs",
    purpose: "All runs with status and verdict mix; New run",
    roles: MCA,
    pri: "P0",
    prd: "FR-507",
    phase: 5,
  },
  {
    path: "/runs/new",
    screen: "S4b",
    title: "New run",
    purpose: "Pick batches, mode, options",
    roles: MCA,
    pri: "P0",
    prd: "FR-505",
    phase: 5,
  },
  {
    path: "/runs/:runId",
    screen: "S4c",
    title: "Run console",
    purpose: "Live progress, stage timings, stats, cancel",
    roles: MCA,
    pri: "P0",
    prd: "FR-507",
    phase: 5,
  },
  {
    path: "/review",
    screen: "S5",
    title: "Review queue",
    purpose: "Clusters sorted by priority with filters",
    roles: ["MAKER", "CHECKER"],
    pri: "P0",
    prd: "FR-801",
    phase: 6,
  },
  {
    path: "/clusters/:clusterId",
    screen: "S6",
    title: "Cluster review",
    purpose: "Records side by side, evidence card, actions",
    roles: MCAA,
    pri: "P0",
    prd: "FR-802–803",
    phase: 6,
  },
  {
    path: "/pairs/:pairId",
    screen: "S7",
    title: "Pair evidence",
    purpose: "Full-page version of the pair modal (deep link)",
    roles: MCAA,
    pri: "P0",
    prd: "FR-609",
    phase: 6,
  },
  {
    path: "/registry",
    screen: "S8a",
    title: "Registry",
    purpose: "CNMCs with search and filters",
    roles: ALL, // INTEGRATOR read-only (DEC-19)
    pri: "P0",
    prd: "FR-906",
    phase: 6,
  },
  {
    path: "/registry/:cnmc",
    screen: "S8b",
    title: "National code",
    purpose:
      "Canonical spec, class path, members, crosswalk, substitutes (P1), history, unmerge (P1)",
    roles: ALL, // INTEGRATOR read-only (DEC-19)
    pri: "P0",
    prd: "FR-901–907, FR-1481–1482",
    phase: 6,
  },
  {
    path: "/exports",
    screen: "S8c",
    title: "Exports",
    purpose: "Crosswalk (CSV / JSON / SAP-style) and migration packs per CPSE",
    roles: MCA,
    pri: "P0",
    prd: "FR-905, FR-907",
    phase: 6,
  },
  {
    path: "/search",
    screen: "S9",
    title: "Search before create",
    purpose: "Free-text check against the registry",
    roles: ["MAKER", "CHECKER", "ADMIN", "INTEGRATOR"],
    pri: "P0",
    prd: "FR-1001–1003",
    phase: 7,
  },
  {
    path: "/templates",
    screen: "S10a",
    title: "Rulebook",
    purpose: "Categories, versions, status",
    roles: ALL,
    pri: "P0",
    prd: "FR-401",
    phase: 7,
  },
  {
    path: "/templates/:templateId",
    screen: "S10b",
    title: "Template detail",
    purpose:
      "Core / extended / critical, rule texts, golden tests; ADMIN: YAML draft → golden tests → impact preview → activate",
    roles: ALL,
    pri: "P0",
    prd: "FR-401–405, FR-1451–1452",
    phase: 7,
  },
  {
    path: "/evaluation",
    screen: "S11a",
    title: "Evaluation",
    purpose: "Evaluation runs; New evaluation",
    roles: MCAA,
    pri: "P0",
    prd: "FR-1101–1106",
    phase: 7,
  },
  {
    path: "/evaluation/:evalId",
    screen: "S11b",
    title: "Evaluation report",
    purpose: "Safety headline, baseline scoreboard, honesty panel, tabs",
    roles: MCAA,
    pri: "P0",
    prd: "FR-1411–1413, FR-1441–1443",
    phase: 7,
  },
  {
    path: "/lookalikes",
    screen: "S13",
    title: "Look-alike Guard",
    purpose: "Look-alikes vetoed, hidden twins, chart",
    roles: MCAA,
    pri: "P0",
    prd: "FR-1401–1403",
    phase: 6,
  },
  {
    path: "/audit",
    screen: "S12",
    title: "Audit",
    purpose: "Filterable log, verify chain",
    roles: ["ADMIN", "AUDITOR"],
    pri: "P0",
    prd: "FR-1302",
    phase: 3,
  },
  {
    path: "/admin/users",
    screen: "S16",
    title: "Users",
    purpose: "Create users, set roles, reset passwords, API keys (P1)",
    roles: ["ADMIN"],
    pri: "P0",
    prd: "FR-1301, FR-1004",
    phase: 3,
  },
  {
    path: "/erp-sim",
    screen: "S14",
    title: "Create material (SAP simulation)",
    purpose: "Live duplicate check while typing",
    roles: ["MAKER", "CHECKER", "ADMIN", "INTEGRATOR"],
    pri: "P1",
    prd: "FR-1471",
    phase: 8,
  },
  {
    path: "/pooling",
    screen: "S15",
    title: "Savings & pooling",
    purpose: "Full list of CNMCs held by ≥ 2 CPSEs",
    roles: MCA,
    pri: "P1",
    prd: "FR-1491",
    phase: 8,
  },
  {
    path: "/about",
    screen: "S17",
    title: "About SpecID",
    purpose: "What the numbers mean, evidence ladder, versions, licences",
    roles: ALL,
    pri: "P0",
    prd: "FR-1442",
    phase: 7,
  },
  {
    path: "/consents",
    screen: "S18",
    title: "Consent queue",
    purpose:
      "Clusters waiting for my CPSE's consent; evidence card with my CPSE's records highlighted; Consent / Decline",
    roles: ["CHECKER"],
    pri: "P0",
    prd: "FR-1501–1504",
    phase: 6,
  },
  {
    path: "/notices",
    screen: "S19",
    title: "Change notices",
    purpose: "My CPSE's inbox of registry and rule changes; acknowledge; delta migration file",
    roles: ["MAKER", "CHECKER", "INTEGRATOR"],
    pri: "P1",
    prd: "FR-1511–1513",
    phase: 8,
  },
];

/** Screens whose real page exists. Only these appear in navigation (App Flow 3.1, UI/UX brief
 * 1.4 rule 6); every other route still renders its placeholder by URL. Each phase adds its paths. */
export const BUILT_PATHS: ReadonlySet<string> = new Set([
  "/",
  "/login",
  "/audit",
  "/admin/users",
  // Go 1 chunk 3 (WP1.7): S2, S3, S4
  "/upload",
  "/batches/:batchId/quality",
  "/runs",
  "/runs/new",
  "/runs/:runId",
  // Go 1 chunk 4 (WP1.8-1.10): review, consent, registry, exports, change notices
  "/review",
  "/clusters/:clusterId",
  "/pairs/:pairId",
  "/consents",
  "/registry",
  "/registry/:cnmc",
  "/exports",
  "/notices",
  // Go 1 chunk 5 + Go 2: insights, SAP simulation, evaluation, about
  "/search",
  "/lookalikes",
  "/pooling",
  "/erp-sim",
  "/evaluation",
  "/evaluation/:evalId",
  "/about",
  "/templates",
  "/templates/:templateId",
]);

/** Pages that show the run selector in the top bar (App Flow 3.3). */
export const RUN_SCOPED_PATHS: ReadonlySet<string> = new Set([
  "/",
  "/review",
  "/lookalikes",
  "/pooling",
]);
