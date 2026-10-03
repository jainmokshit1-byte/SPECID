# 06 · Implementation Plan: SpecID Prototype
## Step-by-step build sequence · PS SIH26099

| Field | Value |
|---|---|
| Document | 06 of 6 · Implementation Plan (the exact order to build) |
| Version | v1.1 draft · 3 Oct 2026 (v1.1: multi-CPSE consent and rulebook impact preview built as P0 differentiators; change notices P1; competitive re-scan before the finale; upstream PRD fixes applied) |
| Source of truth above this | PRD v0.5 (scope tiers 1.6, differentiators 1.8, plan 14.3, cut order 14.4, demo 15) · TRD v1.1 · 03 App Flow v1.1 · 04 UI/UX Design Brief v1.1 · 05 Backend Schema (schema v0.6) · Competitive Review |
| Team | 6 people, roles R1–R6 (PRD 14.1) |
| Assumption to confirm | 36-hour software finale (PRD Q-02); whether code written before the finale is allowed (PRD Q-01) |

**How to use this plan.** Work phase by phase. A phase is finished only when **every** done criterion passes; the gate commands in section 6 are the proof. If a phase overruns, apply the decision points in section 7 instead of silently squeezing later phases. When an AI coding agent builds a step, brief it with the documents listed under *Inputs* for that phase (section 9 explains how).

---

## 1. Timeline at a glance

| Stage | When | Goal | Code allowed? |
|---|---|---|---|
| **A. Idea submission** | now → idea-PPT deadline (you reported 5 Oct; confirm with SPOC) | Submit the 6-slide PDF from the dossier's Part S | no code needed |
| **B. Preparation** | after shortlisting → finale | Validate rules with an engineer, set up laptops, rehearse; build assets **only if the rules allow** | depends on Q-01 |
| **C. Finale build** | T+0 → T+36 | Phases 1–11 below | yes |
| **D. After the finale** | pilot with CPSEs | L3 evaluation on real data (PRD 1.4 roadmap) | — |

```
T+0   2    4    6    8   10   12   14   16   18   20   22   24   26   28   30   32   34   36
P1 ██                                                                                          setup
P2  ███                                                                                        database
P3    ████                                                                                     auth + audit
P4    ████████████                                                                    G1@8     core engine
P5                   ████████████                                                     G2@14    data, runs, AI channels, air-gap
P6                               ████████████                                         G3@20    review, registry, migration, look-alikes
P7                                           ████████████                             G4@26    search, evaluation, dashboard, SAP
P8                                                       ████████                     G5@30    hardening + P1 (freeze)
P9 (UI polish, parallel lane R5/R6) ··················████████████████
P10                                                                  ████████                  bug fixing, offline runs
P11                                                                       ██████████  G6@36    package, rehearse, tag
```

---

## 2. Team lanes

| Role | Owns | Phases led | Backup |
|---|---|---|---|
| **R1** Tech lead / backend | repo, Docker, DB, auth, audit, registry, CI, air-gap | 1, 2, 3, parts of 5–6, 11 | R3 |
| **R2** NLP / rules | normaliser, extractors, templates, UoM, golden tests | 4, parts of 5, 8 | R3 |
| **R3** Matching / ML | decide, candidates (BM25, MiniLM/FAISS), clustering, classifier, search | 4, 5, 7 | R2 |
| **R4** Data / evaluation | synthetic generator, procurement history, metrics, baselines, reports, models | parts of 4–5, 7 | R3 |
| **R5** Frontend lead | design system, S6, S9, S13, S11 | 6, 7, 9 | R6 |
| **R6** Frontend / QA / demo | shell, S0, S2–S4, S8, S12, S16, tests, demo script | 6, 7, 9, 10, 11 | R5 |

**Working rules:** vertical slices behind the API contract (PRD section 8) · trunk-based with small branches · commit messages start with the requirement ID · integrate at every gate · nobody edits another lane's module without telling its owner.

---

## 3. Phase summary

| # | Phase | Window | Lead | Depends on | Ends with |
|---|---|---|---|---|---|
| 0 | Preparation (stages A–B) | before T+0 | all | — | submitted PPT; ready laptops |
| 1 | Setup | T+0 – 2 | R1 | 0 | stack boots to login page; CI green |
| 2 | Database | T+0.5 – 3 | R1 | 1 | schema v0.5 migrated; seed loads |
| 3 | Auth, RBAC and audit | T+2 – 6 | R1 | 2 | login per role; audit chain verify |
| 4 | Core engine | T+2 – 8 | R2, R3, R4 | 1 | **G1** |
| 5 | Data, runs, AI channels, air-gap | T+8 – 14 | R3, R1, R2, R4, R6 | 2, 3, 4 | **G2** |
| 6 | Review, registry, migration, **multi-CPSE consent**, Look-alike Guard | T+14 – 20 | R5, R1, R3, R6 | 5 | **G3** |
| 7 | Search, evaluation, baselines, dashboard, SAP, **rulebook impact preview** | T+20 – 26 | R3, R4, R5, R6, R1, R2 | 6 | **G4** |
| 8 | Hardening and P1 features | T+26 – 30 | R2, R3, R4, R5 | 7 | **G5 feature freeze** |
| 9 | UI polish (parallel) | T+18 – 30 | R5, R6 | 6 | design checklist passes |
| 10 | Testing and bug fixing | T+30 – 34 | all | 8 | demo path passes offline twice |
| 11 | Packaging, deploy, rehearsal | T+30 – 36 | R1, R6 | 10 | **G6** tagged release |

---

## 4. Phases in detail

### Phase 0 · Preparation (before T+0)

**Goal:** arrive at the finale with decisions made, laptops ready, and nothing left to research.

**Stage A tasks (idea PDF, now)**
- [ ] Paste Part S of the dossier into the official template; fill Team ID and Team Name on all slides (dossier S0, S7)
- [ ] Apply each slide's cut list until body text fits at 11–12 pt; export PDF; check on a phone-sized screen
- [ ] Draw the Slide 3 flowchart in mermaid.live; optional "planned screen" mock of S13 (UI/UX brief section 10)
- [ ] Text-search the PDF for "first", "only", "best", "beats" (must be zero)
- [ ] Confirm the deadline and re-read the PS on the portal

**Stage B tasks (safe even if pre-written code is banned)**
- [ ] Get answers to PRD Q-01 (pre-written code), Q-02 (duration, team size, hardware, internet), Q-06 (laptop vs hosted demo)
- [ ] Review templates with a materials engineer: STD/XS limits, material families, critical defaults, substitution rules (PRD D-06, FR-612). Record changes in the template YAML text in the PRD
- [ ] Every laptop: Docker ≥ 24 with Compose v2, Python 3.11, Node 20, Git; WSL2 memory ≥ 10 GB on Windows (TRD TR-OPS-08)
- [ ] Pull images (`postgres:16-alpine`, `python:3.11-slim`, `node:20-alpine`, `nginx:1.27-alpine`); download `all-MiniLM-L6-v2` into `./models` and copy it to a USB stick
- [ ] Learn the stack: FastAPI + SQLAlchemy 2 tutorial (R1, R3), TanStack Query + Tailwind (R5, R6), rapidfuzz + rank-bm25 + FAISS basics (R3, R4)
- [ ] Paper or Figma wireframes for S6, S9, S11, S13 from the UI/UX brief
- [ ] Write and rehearse the 5-minute demo narration (PRD 15.1) against the slides
- [ ] **One week before the finale: re-run the Competitive Review scan** (`repos/analyze.py` approach) and update PRD 1.7–1.8 and Appendix G if any repo now shows consent, impact preview or bounded false-merge reporting
- [ ] Divide the golden-test writing: each of R2, R3, R4 drafts 20 case *descriptions* in plain text (format in TRD Appendix K)

**Only if Q-01 allows pre-built work:** repository skeleton, generator, extractors and golden tests, UI components. Otherwise keep PRD Appendices C and D as the specification and rebuild during Phases 4–5.

**Done when:** PDF submitted · Q-01/Q-02 answered · engineer review recorded · every laptop runs `docker run hello-world` and has the model files.

---

### Phase 1 · Setup (T+0 – 2) · lead R1

**Goal:** an empty but running system that everyone can build on.

**Inputs:** TRD sections 2, 3, 12, Appendices A–C, L.

**Tasks**
- [ ] Create the repository with the layout in TRD Appendix L; add `.gitignore` (models, data, `.env`)
- [ ] `docker-compose.yml`, nginx config, both Dockerfiles exactly as TRD Appendix A; `internal: true` on `backend`
- [ ] `.env.example` (TRD Appendix C); each person copies it to `.env`
- [ ] Backend skeleton: FastAPI app with `/api/v1/health`, settings model (TRD Appendix D), structlog
- [ ] Frontend skeleton: Vite + React + TS + Tailwind with the tokens file from the UI/UX brief section 9; app shell (sidebar, top bar, footer, ribbon) with placeholder pages for every route in App Flow section 2
- [ ] Freeze dependencies: `requirements.lock`, `requirements-ml.lock` (CPU torch), `package-lock.json` (TRD TR-OPS-03)
- [ ] CI workflow (TRD Appendix G); Makefile targets as stubs (TRD Appendix B)
- [ ] Each laptop: `make up` succeeds (test on at least two operating systems; PRD R-08)
- [ ] Answer Q-01 and Q-02 finally; lock scope (PRD 1.6)

**Done when:** `http://127.0.0.1:8080` shows the shell with a working sidebar on two laptops · `/api/v1/health` returns 200 through nginx · CI is green on `main` · `docker network inspect specid_backend --format '{{.Internal}}'` prints `true`.

---

### Phase 2 · Database (T+0.5 – 3) · lead R1

**Goal:** the complete schema, migrations and seed data in place before any feature writes to it.

**Inputs:** Backend Schema Appendix A (DDL), sections 1, 11, 12, 13.

**Tasks**
- [ ] Alembic `0001_initial` = Backend Schema Appendix A (schema v0.6) verbatim; migrations run at API start (TRD TR-DAT-01)
- [ ] SQLAlchemy 2.0 models for all 26 tables; Pydantic schemas for the JSONB contracts (Backend Schema section 6)
- [ ] COPY helper for bulk inserts (TRD TR-DAT-03)
- [ ] `make seed`: CPSEs with salts, five demo users, templates and dictionaries from YAML (seed data section 12; synthetic data comes in Phase 4–5)
- [ ] Optional: app role `specid_app` from Backend Schema Appendix B (connect the API as that role)
- [ ] Test: constraint checks from Backend Schema section 15 as pytest cases

**Done when:** a fresh `make up && make seed` creates all tables · `pytest tests/integration/test_schema.py` passes (append-only audit, active-mapping uniqueness, maker ≠ checker, pair order, CNMC format).

---

### Phase 3 · Auth, RBAC and audit (T+2 – 6) · lead R1, UI R6

**Goal:** every later endpoint is born protected and audited.

**Inputs:** TRD 11 (TR-SEC-01–04, 12), TRD TR-ALG-09; App Flow section 4; Backend Schema section 5, 9.2.

**Tasks**
- [ ] `POST /auth/login`, `GET /me`; bcrypt cost 12; JWT HS256 8 h; login rate limit 5/min
- [ ] `require_role(...)` dependency; permission matrix encoded once and used by routers and tests
- [ ] Audit service: canonical JSON, advisory lock, SHA-256 chain; `GET /audit`, `GET /audit/verify`
- [ ] RFC 7807 error handler and typed service exceptions
- [ ] UI: login page, token in memory + sessionStorage, role home redirects, 401 → `/login?next=`, role-filtered sidebar (App Flow 3.2, 4.3, 4.4)
- [ ] UI: S12 Audit list + Verify button; S16 Users (create, reset, disable)

**Done when:** each demo user logs in and lands on the correct home · a MAKER calling an ADMIN endpoint gets 403 · tamper test (disable trigger as owner, edit a row) makes verify report that event id · `LOGIN_SUCCEEDED` events appear in S12.

---

### Phase 4 · Core engine (T+2 – 8) · leads R2 (rules), R3 (decide), R4 (generator)

**Goal:** the pure decision engine works from the command line on synthetic data. This is the heart of the product.

**Inputs:** PRD 9.2–9.10, Appendices A–D; TRD section 4; golden format TRD Appendix K.

**Tasks**
- [ ] R2 `core/normalise.py` with the versioned dictionary; `core/units.py` (NPS→DN, STD/XS rules, HP→kW, UoM aliases)
- [ ] R2 `core/extract.py` for VALVE, PIPE, FLANGE (then FASTENER, MOTOR in Phase 5) with conversion notes on every attribute
- [ ] R2 `core/templates.py` loading YAML incl. `rule_text`; startup fails on invalid YAML
- [ ] R3 `core/types.py`, `core/decide.py` (veto → unknown-state → route), `core/confidence.py`, `core/cluster.py`, `core/cnmc.py`, `core/shortdesc.py`
- [ ] R3 `core/radar.py` (`text_sim`, `lookalike_class`) and `core/baselines.py`
- [ ] R4 `eval/generator.py` v0: seeded, styles A–C, hard negatives, truth files, manifest with hashes (PRD 10.1)
- [ ] R2+R3+R4 golden YAML: the 12 dossier pairs + 13 edge cases from PRD Appendix D = 25 cases
- [ ] R3 architecture test: `core/` imports nothing from services, API or DB (TRD TR-TST-12)
- [ ] CLI `python -m app.cli decide --file data/synthetic/seed-7` prints the verdict mix

**Done when (Gate G1, T+8):** 25 golden tests pass · symmetry and veto property tests pass · every evidence row has `rule` and `rule_text` · the CLI prints a verdict mix on generator output · `pytest -m "not ml"` green in CI.

**Agent prompt for this phase:** *"Using PRD sections 9.2–9.10 and TRD section 4 as the source of truth, implement `core/decide.py` with the exact signature in TRD 4.2 (TR-MOD-06). Make the golden tests in `tests/golden/*.yaml` pass. Do not add any ML or scoring that can change a verdict."*

---

### Phase 5 · Data, runs, AI channels, air-gap (T+8 – 14)

**Goal:** a full harmonisation run starts from the UI, uses the AI channels, and the air-gap proof is live.

**Inputs:** TRD 5 (TR-MOD-20–23, 30), TR-ALG-01–03, 4.3, TR-SEC-05–06; App Flow 5.2–5.4; PRD FR-101–107, FR-205, FR-402, FR-503.

**Tasks**
- [ ] R1 ingest service: upload (CSV/XLSX, encoding detection), mapping suggestions incl. **SAP preset** (TRD Appendix H), idempotent ingest, quality report
- [ ] R4 procurement-history upload and aggregation (FR-107), vendor hashing; generator adds synthetic procurement lines
- [ ] R2 FASTENER and MOTOR extractors; **UoM harmonisation** in ingest (FR-205)
- [ ] R4 + R3 `make models`: train the **ML category classifier** on the train split (TRD 4.3); add the fallback to `classify()`
- [ ] R3 candidate generation: blocking `(category, size_dn)`, BM25, **MiniLM + FAISS**, MPN; mode filters; channel bitmask (TRD TR-ALG-01)
- [ ] R3 harmonise orchestration in the job pool: extract → embed → candidates → decide → COPY pairs → cluster → stats; progress every ≤ 2 s; cancel
- [ ] R3 store `text_sim`, `lookalike`, baseline flags per pair (SF-1)
- [ ] R1 **egress guard** in API and worker initializer; `/system/airgap`; footer counter (SF-7)
- [ ] R6 UI: S2 upload & mapping, S3 quality report, S4 runs list / new run / run console
- [ ] R5 UI: design-system components (VerdictBadge, EvidenceCard, RulePopover, DataTable, SyntheticRibbon, AirGapFooter) per UI/UX brief section 6

**Done when (Gate G2, T+14):** in the browser, upload three synthetic CPSE files → quality reports → start a CROSS_CPSE run → it reaches DONE with progress shown · `run.stats` shows all four channels used · the footer reads `AIR-GAPPED · blocked attempts: 0` · `make test-ml` passes on one laptop.

**Decision point (T+14):** if the run takes more than 10 minutes on 10k records, switch the demo dataset to 3k records now (PRD R-11) and keep going.

---

### Phase 6 · Review, registry, migration, Look-alike Guard (T+14 – 20)

**Goal:** a maker and a checker turn a cluster into a national code with a full trail, and the Look-alike Guard shows what text matching would get wrong.

**Inputs:** App Flow 5.5–5.8, 5.12, J2, J4; TRD TR-MOD-24–26, TR-ALG-06, 08; Backend Schema 10; UI/UX brief 7.2, 7.3, 7.6, 7.7.

**Tasks**
- [ ] R1 review service (state machine, maker ≠ checker 403), CNMC issuance transaction (sequence, Luhn, canonical spec, class path, base UoM, crosswalk rows, audit)
- [ ] R1 crosswalk export CSV/JSON/**SAP-style**; CSV injection guard (TRD TR-MOD-31)
- [ ] R3 + R1 **migration pack** per CPSE (TRD TR-ALG-08); `GET /exports/migration-pack`
- [ ] R3 radar endpoints API-25, API-26
- [ ] R5 S5 review queue and **S6 cluster review** (hero screen, keyboard keys), pair modal (S7)
- [ ] R6 S8 registry list and CNMC detail, S8c exports
- [ ] R5 **S13 Look-alike Guard** with the differing token highlighted and the chart
- [ ] R1 **multi-CPSE consent** (differentiator, P0): `services/consent.py`, `review_consent` writes, `AWAITING_CONSENT` state, issuance on the last consent, decline with reason (TRD 2.3 b2, TR-ALG-11; PRD FR-1501–1504)
- [ ] R6 **S18 consent queue** and the **ConsentStrip** in S6 (UI/UX brief 6, 7.5b); seed user `kavya` (CHECKER, CPSE-C)
- [ ] R3 test T-S7 (TRD TR-TST-15)

**Done when (Gate G3, T+20):** maker proposes and checker confirms a 3-CPSE cluster → it waits for CPSE-C → the CPSE-C steward consents → CNMC issued → crosswalk export and migration pack download · the same user cannot confirm their own proposal (UI hides it, API returns 403) · `/audit/verify` passes · S13 lists look-alikes with decisive attributes.

**Decision point (T+20 – 22):** if G3 is not met by T+22, switch to the **minimum viable demo path** (PRD 14.4) and move every remaining P1 item to "not built".

---

### Phase 7 · Search, evaluation, baselines, dashboard, SAP integration (T+20 – 26)

**Goal:** every PS key capability is visible, and the numbers are honest.

**Inputs:** App Flow 5.1, 5.9, 5.11; TRD TR-MOD-27–28, TR-ALG-04–05, Appendix J; PRD 10.2, 10.2b, 9.13.5.

**Tasks**
- [ ] R3 registry search index + `POST /search-before-create` (p95 ≤ 1 s target); R5 **S9**
- [ ] R4 evaluation runner: splits, metrics with Wilson / rule-of-three, **baselines B1 / B2 tuned on validation**, disagreement table, style-D and adversarial presets, Markdown/JSON report with the honesty text and git commit
- [ ] R5 **S11** evaluation report in the fixed order with the **honesty panel**
- [ ] R6 **S0 dashboard** (duplicates per CPSE, quality, cross-CPSE clusters, backlog, top clusters) and the **demand-aggregation panel** using TRD Appendix J
- [ ] R1 `/api/v1/openapi.json` served; Swagger assets local or docs disabled (TRD TR-API-01); SAP preset tested with a sample SAP-style extract
- [ ] R2 golden tests ≥ 40
- [ ] R2 + R3 **rulebook impact preview** (differentiator, P0): YAML draft validation, `decide(..., templates=draft)` over stored pairs, affected CNMCs per CPSE, golden-test gate, acknowledged activation (TRD TR-ALG-10; PRD FR-403–404, FR-1451–1452)
- [ ] R5 S10 draft editor + **ImpactPreviewTable** (UI/UX brief 7.5c); test T-S8 (TRD TR-TST-16)

**Done when (Gate G4, T+26):** the demo draft rule shows non-zero transitions and affected CNMCs, and activation is blocked until golden tests pass · S11 shows a seed-7 SYNTHETIC run with false merges *k* of *n* and the bound, B1 / B2 / SpecID side by side, honesty panel visible · S9 returns USE_EXISTING for a known valve · S0 shows all panels for the run · a SAP-style extract ingests with no manual mapping.

---

### Phase 8 · Hardening and P1 features (T+26 – 30)

**Goal:** make the P0 path robust, then add P1 features in the agreed order. **Feature freeze at T+30.**

**Tasks (hardening first)**
- [ ] R2, R3 property tests T-P1…T-P6 and T-S1…T-S6 green; golden tests ≥ 60, every template covered (PRD 13.2)
- [ ] R4 style-D holdout written blind by someone who has not read the extractors; adversarial set; results shown separately
- [ ] R2 residual-token guard tuned on validation only

**Then P1, in this order (stop at T+30 wherever you are):**
1. [ ] SF-3 ask-don't-guess: supply-attribute API + S6 drawer (strongest demo moment)
2. [ ] SF-12 per-CPSE change notices + S19 inbox + delta CSV (TRD TR-MOD-33)
3. [ ] SF-8 ERP create-material simulator (S14)
4. [ ] SF-9 unmerge with reason (S8b)
5. [ ] FR-612 substitute candidates (only if an engineer approved at least one rule in Phase 0)
6. [ ] SF-10 pooling page, gasket template, bulk approve, cannot-link memory
7. [ ] LightGBM scorer and calibration: only if every gate so far was met on time

**Done when (Gate G5, T+30):** all P0 signature features (SF-1, 2, 4, 5, 7) demonstrable · ≥ 60 golden tests pass · tag `gate-5`; after this only bug fixes merge.

---

### Phase 9 · UI polish (parallel, T+18 – 30) · R5, R6

**Goal:** every screen on the demo path looks like the design brief and handles every state.

**Tasks**
- [ ] Loading, empty and error states for every list (App Flow section 8)
- [ ] Stage mode (`?stage=1`) and the 1366 × 768 check for the demo path (UI/UX brief 2, 4)
- [ ] Keyboard shortcuts on S5/S6 (P1) and visible focus rings
- [ ] Charts with table fallbacks on S0, S11, S13
- [ ] Banned-words search over `frontend/src` (TRD TR-TST-13)
- [ ] Fonts and icons load with the network off

**Done when:** the design checklist in UI/UX brief section 11 is fully ticked.

---

### Phase 10 · Testing and bug fixing (T+30 – 34) · all

**Goal:** the demo path never fails.

**Tasks**
- [ ] Run the full demo path (App Flow 6, "Demo path") on two laptops, Wi-Fi **off**, three times each
- [ ] `make bench` and record stage timings (they are targets, not results)
- [ ] Fix only bugs on the demo path or in data integrity; log everything else as "known issue"
- [ ] Integration test green: CSV → run → approve → CNMC → crosswalk → migration pack → search

**Done when:** demo path passes offline twice in a row on both laptops · no open bug on the demo path.

---

### Phase 11 · Packaging, deploy and rehearsal (T+30 – 36) · lead R1, demo R6

**Goal:** a tagged release, a restorable snapshot and a rehearsed team.

**Tasks**
- [ ] `make snapshot` after a clean seed + run + a few issued CNMCs + one evaluation; copy to both laptops and a USB stick
- [ ] Record a backup screen video of the full demo; phone screenshots of S6, S9, S11, S13
- [ ] Capture slide screenshots per UI/UX brief section 10 (if a later round uses slides)
- [ ] README: setup, `make` targets, demo users, honesty note
- [ ] Four browser profiles prepared on the demo laptop: maker (CPSE-A), checker (CPSE-B), steward (CPSE-C), admin
- [ ] Three full rehearsals with timing (PRD 15.1) and the judge Q&A (dossier Appendix A, items 1–16)
- [ ] Tick PRD checklist 13.4 completely; tag `gate-6`; stop updating laptops

**Done when (Gate G6, T+36):** tagged release · checklist 13.4 complete · snapshot restores in under 2 minutes · every team member can run the demo alone.

---

## 5. Hour-by-hour lanes

| Window | R1 | R2 | R3 | R4 | R5 | R6 |
|---|---|---|---|---|---|---|
| T+0–2 | repo, compose, CI | template YAML review | decide skeleton | generator skeleton | Vite + tokens | app shell |
| T+2–4 | DB migration, seed | normaliser, units | decide + evidence | generator v0 | components start | login, redirects |
| T+4–6 | auth, RBAC, audit | valve/pipe/flange | cluster, cnmc, shortdesc | golden cases | EvidenceCard, Verdict | S12, S16 |
| T+6–8 | error model, COPY helper | golden fixes | radar, baselines | truth files, manifest | RulePopover, DataTable | S2 layout |
| **G1** | | | | | | |
| T+8–11 | ingest + SAP preset | fastener, motor, UoM | candidates (BM25, FAISS) | procurement, classifier training | Ribbon, Footer | S2, S3 |
| T+11–14 | egress guard, airgap API | dictionary versioning | harmonise job | classifier eval | S4 console | S4 lists |
| **G2** | | | | | | |
| T+14–17 | review service, issuance | golden ≥ 30 | radar API | metrics module | S5, S6 | S8 list/detail |
| T+17–20 | **consent service** | edge cases | migration pack, T-S7 | baselines tuning | S13 | **S18 + ConsentStrip** |
| **G3** | | | | | | |
| T+20–23 | OpenAPI, SAP sample | golden ≥ 40, **YAML draft validation** | search index + API, **impact preview** | eval runner | S9, **S10 preview UI** | S0 dashboard |
| T+23–26 | perf fixes | residual guard | search perf | report export | S11 | demand panel |
| **G4** | | | | | | |
| T+26–30 | P1 SF-12 notices | property tests, style D | P1 SF-3 supply | adversarial set | P1 S14 | polish, states, S19 (P1) |
| **G5 freeze** | | | | | | |
| T+30–34 | bugs, snapshot | bugs | bugs | bench | bugs | offline runs |
| T+34–36 | tag, laptops | rehearse | rehearse | rehearse | rehearse | lead rehearsal |

---

## 6. Gate checklists (commands are the proof)

| Gate | Time | Commands / checks | Pass condition |
|---|---|---|---|
| G1 | T+8 | `make test`; `python -m app.cli decide --file data/synthetic/seed-7` | 25 golden + property tests green; verdict mix printed; rule IDs present |
| G2 | T+14 | upload 3 files in UI; start run; `curl 127.0.0.1:8080/api/v1/system/airgap` | run DONE; 4 channels in stats; `blocked_egress_attempts: 0` |
| G3 | T+20 | maker propose → checker confirm → **CPSE-C consent**; download crosswalk and migration pack; S12 verify | CNMC issued only after consent; files download; chain intact; S13 non-empty |
| G4 | T+26 | `make eval SEED=7`; S11; S9 query; S0; **S10 impact preview of the demo draft** | report with bound + B1/B2/SpecID + honesty panel; USE_EXISTING; dashboard panels filled; preview shows transitions and blocks activation until golden tests pass |
| G5 | T+30 | `make test`; `make test-ml`; count golden cases | ≥ 60 golden; all P0 SF demonstrable; tag `gate-5` |
| G6 | T+36 | `make restore`; demo path offline ×3; checklist 13.4 | all pass; tag `gate-6` |

---

## 7. Decision points and cut rules

| When | Question | If "no" |
|---|---|---|
| T+2 | Does `make up` work on every laptop? | the failing laptop becomes a frontend-only machine pointing at a teammate's API |
| T+8 (G1) | 25 golden tests green? | R4 joins R2/R3 on the engine until green; Phase 5 starts late, UI continues against mocks |
| T+14 (G2) | Run ≤ 10 min on 10k records? | demo on 3k records; snapshot the run |
| T+14 | Dense channel working offline? | turn it off (blocking + BM25 still meet the flow); footer shows `DENSE OFF`; keep the ML classifier as the visible AI |
| T+22 | G3 met? | switch to the minimum viable demo path (PRD 14.4); no P1 at all |
| T+26 | G4 met? | P1 limited to SF-3 only |
| T+30 | anything still unfinished? | it is not in the demo; never show a half-working screen (PRD 15.2) |

**Never cut** (PRD 14.4): **multi-CPSE consent, rulebook impact preview, bounded false-merge number** (the differentiators), veto, unknown-state, rule-cited evidence, maker–checker, SYNTHETIC ribbon, safety scoreboard + honesty panel, baseline scoreboard, Look-alike Guard, air-gap proof, audit chain. Since v0.4 the PS key capabilities also stay: dashboard (tables if charts are late), migration pack, SAP-style export.

---

## 8. Overall done criteria

The prototype is finished when all of these hold:
1. Every *Expected Solution* bullet of the PS is demonstrable on screen (PRD 1.12 compliance matrix).
2. The three differentiators (multi-CPSE consent, rulebook impact preview, bounded false-merge number) work on the demo path.
3. The 5-minute demo path runs offline three times in a row on two laptops (PRD SC-7).
4. ≥ 60 golden tests and all property tests pass on the release tag (PRD SC-2, SC-3).
5. The evaluation page shows false merges *k* of *n* with a bound, both baselines and the honesty panel, all labelled SYNTHETIC (PRD SC-4, SC-10, SC-8).
6. Audit verification passes; maker ≠ checker is enforced in UI, API and database.
7. The footer shows AIR-GAPPED with 0 blocked attempts after the demo path (PRD SC-11).
8. No banned words anywhere (PRD NFR-14).
9. A snapshot, a backup video and screenshots exist on two devices.

---

## 9. Working with AI coding agents

**Briefing order** (paste or attach at the start of every agent session): PRD → TRD → App Flow → UI/UX Design Brief → Backend Schema → this plan, then say: *"These six documents are the source of truth. Build only what the current phase lists. If something is unclear or contradictory, stop and ask; do not invent screens, tables or rules."*

**Per-task prompt pattern**
```
Phase <n>, task: <one checkbox from this plan>.
Requirements: <IDs, e.g. FR-1001–1003, TR-MOD-27, App Flow 5.9>.
Constraints: follow TRD section <x>; use tokens from UI/UX brief section 3; schema from Backend Schema Appendix A only.
Done when: <the phase's done criterion that this task contributes to>.
Write tests first for core/ code; do not modify golden tests to make them pass.
```

**Guardrails for agents**
- Never change `core/decide.py` without running the golden and property tests.
- Never add a network call, CDN link or telemetry (air-gap, TRD TR-SEC-05–06).
- Never write numbers into UI copy or reports by hand; they come from runs.
- Never create a table or column outside an Alembic migration that matches Backend Schema.
- Review every agent diff on `core/`, `services/registry.py` and `services/audit.py` by a human before merging.

---

## 10. Upstream updates (applied in PRD v0.5)

| Update | Where | Status |
|---|---|---|
| Blocking key is `(category, size_dn)`; class is not a blocking key | PRD FR-501 | applied |
| Auth library: `bcrypt` directly, not passlib | PRD 6.3 Auth row | applied |
| Schema moved to doc 05 (schema v0.6, 58 statements, 26 tables); PRD Appendix E points there | PRD Appendix E, sections 0 and 7 | applied |
| Screens S16 Users, S17 About, S18 Consents, S19 Change notices | PRD 11.1 | applied |
| Run statuses CANCELLING / CANCELLED | PRD FR-507 | applied |
| Re-positioning after the 41-repo scan; SF-11 consent and SF-6 impact preview in P0; SF-12 in P1 | PRD 1.7–1.11, Appendix G | applied |

*End of Implementation Plan.*
