# PROGRESS

Current phase: **Phase 2 · Database — done** (gate PASS, see below). Phase 1 done with 2 criteria PENDING; shell revised to the v1.2 minimal UI (DEC-10). Next: Phase 3 · Auth, RBAC and audit (awaiting approval of its plan).

Build mode: **preparation build** (before the finale). Scope locked to **PRD v0.5 P0**. Deviations: [docs/DECISIONS.md](docs/DECISIONS.md).

## Open questions

| ID | Question | Status / working assumption |
|---|---|---|
| Q-01 | Do the 2026 finale rules allow code written before the event? | **Open.** Treated as a preparation build |
| Q-02 | Finale duration, team size, venue hardware, internet | **Open.** Assume 36 h and a team of 6 |

## Standing decisions that affect later phases

- **Memory (DEC-09):** Docker stays at default memory (~8 GB). Demo dataset ≈ 3,000 records (`n_entities` ≈ 1,200, a parameter); evaluation preset `hard_negative_share = 0.5`; report the real *n* of hard negatives and its bound; performance budgets measured on 3k; auto-eligibility OFF; `mem_limit` api 4g / db 1g (applied); embedding batch 64; one job worker.
- **Navigation (DEC-10):** each phase adds the paths of the screens it builds to `BUILT_PATHS` in `frontend/src/routes.ts`; only then do they appear in the sidebar and tabs. Developer switch `?dev=1` (dev server only) shows the rest.
- **Template activation (DEC-04):** golden tests + ADMIN acknowledgement of the impact preview; no second ADMIN.
- **Seed and audit (DEC-11):** `make seed` writes no `audit_event` rows; the hash chain starts with the first real action in Phase 3.
- **Seed content (DEC-13):** gasket v1 is DRAFT; UNSPSC_MAP v1 is empty until a code is verified with a source note; `RunConfig` defaults arrive with `settings.RunDefaults` in Phase 5.

## Tasks added to later phases

### Phase 8 (in addition to the Implementation Plan's Phase 8 tasks)
- [ ] **Connect the API as `specid_app`** (Backend Schema Appendix B, §5.4; DEC-12): add an app DB password to `.env.example`, keep the owner URL for migrations and use the `specid_app` URL for requests, apply Appendix B after migrations, set `app.cpse_id` per request for the procurement RLS. Appendix B itself is already verified by `test_appendix_b_hardening_as_specid_app`

### Phase 7 (in addition to the Implementation Plan's Phase 7 tasks)
- [ ] **S17 About & honesty** (`/about`, P0, FR-1442; DEC-07): honesty text, evidence ladder, versions (app, templates, dictionary, models, commit), licences of bundled models and fonts. Built next to the S11 honesty panel; **both screens read the honesty text from one shared source** so the wording cannot drift

## Phase 1 · Setup

### Done
- Repository layout per TRD Appendix L; `.gitignore` (models, data, `.env`), `.gitattributes` (LF)
- `docker-compose.yml`, `frontend/nginx.conf`, both Dockerfiles as TRD Appendix A; `backend` network `internal: true`; additions DEC-02 (`GIT_COMMIT`) and DEC-09 (`mem_limit`)
- `.env.example` (TRD Appendix C + `CONSENT_MODE`, DEC-01)
- Backend skeleton: FastAPI, `/api/v1/health` (API-24; DB ping, model manifest, guard status, consent mode, git commit; 503 if DB unreachable), settings model (TRD Appendix D + DEC-01/02), structlog JSON logs with `X-Request-ID`, OpenAPI at `/api/v1/openapi.json`, CDN Swagger UI disabled (TD-08)
- Frontend skeleton: Vite 5 + React 18 + TS strict + Tailwind 3 with tokens from UI/UX brief §3/§9; fonts and icons bundled; app shell (SYNTHETIC ribbon, sidebar with the 7 groups of App Flow 3.1, top bar, air-gap footer); placeholder pages for all 25 shell routes of App Flow §2, `/login` outside the shell, 404
- Dependencies frozen: `backend/requirements.lock` (core), `requirements-ml.lock` (CPU torch 2.14.1+cpu, sentence-transformers, faiss-cpu), `requirements-dev.txt`, `frontend/package-lock.json` (TR-OPS-03)
- CI workflow (TRD Appendix G); local mirror `backend/scripts/ci_local.sh`; Makefile with every Appendix B target (unbuilt ones print their phase and exit 1)
- Tests: backend 3 (health 200, health 503 without DB, OpenAPI served / CDN docs off); frontend 30 at the time, now 61 after the v1.2 revision (route table equals App Flow §2, every route renders in the shell with ribbon and footer, no AIR-GAPPED claim before `/system/airgap`, login outside shell, 404)

### Gate: "Done when" criteria

| Criterion | Result | Evidence |
|---|---|---|
| `http://127.0.0.1:8080` shows the shell with a working sidebar | PASS on this laptop (Windows 11, Docker 29.8.1) | All 26 App Flow routes (+ an unknown path, which renders the 404 page) return 200 through nginx `try_files`; headless Chromium at 1366×768 rendered the shell and clicking sidebar "Consents" opened S18 with the item highlighted: [shell-dashboard.png](docs/evidence/phase1/shell-dashboard.png), [shell-consents.png](docs/evidence/phase1/shell-consents.png). Fonts loaded locally (Inter 400/500/600, JetBrains Mono 400); 0 requests to non-local hosts |
| … on two laptops / two OSes | **PENDING** | only one machine available |
| `/api/v1/health` returns 200 through nginx | PASS | `curl -i 127.0.0.1:8080/api/v1/health` → `HTTP/1.1 200 OK`, `{"status":"ok","git_commit":"2401cd2","db":"ok","models":null,"templates":null,"egress_guard":{"enabled":true,"installed":false},"consent_mode":"ALL_PARTICIPANTS",...}`; `docker compose ps`: api and db healthy |
| CI green on `main` | **PENDING** (no GitHub remote yet). Local run of the same jobs in the same images: PASS | `make test` (backend: ruff ✔, black ✔, pytest 3 passed, coverage gate passed; frontend: eslint + prettier ✔, vitest 30 passed, tsc + vite build ✔). Note: the coverage gate is vacuous until `core/` has code (0 statements = 100%) |
| `docker network inspect specid_backend --format '{{.Internal}}'` prints `true` | PASS | Prints `true` (`specid_frontend` prints `false`); api and db attach only to `specid_backend`, web to both; from inside `api`, a connection to 1.1.1.1 fails with `Network is unreachable`; `make offline-check` passes its network part and says PARTIAL for the Phase 5 counter check |

### Phase 1 revision: v1.2 minimal shell (DEC-10)

Done (App Flow v1.2 §3.1–3.3, §4.3; UI/UX brief v1.2 §1.4, §4, §6, §7.1):
- Sidebar: 5 task items + Rules + Help with tabs inside items; unbuilt screens hidden from navigation (only Home is built), every URL still renders; dev-only switch `?dev=1` / `VITE_SHOW_UNBUILT=true` marks unbuilt items "dev" and is compiled out of the production build
- Top bar: section title, SYNTHETIC DATA badge (ribbon removed), run selector on `/`, `/review`, `/lookalikes` only, user menu
- Slim 24 px footer: "Consent: all CPSEs" (FR-1504) left; air-gap status right ("Air-gap status unavailable" until Phase 5, then "Air-gapped · blocked attempts: n"); GUARD OFF / DENSE OFF tags
- Home: PageHeader + Next-step card (first-run checklist, step 1 current, "Upload files" disabled with reason until S2); PageHeader on every page; Tabs component
- Tests: frontend 61 (was 30): route table, every route in the shell with one h1 + badge + footer, default nav shows Home only, `?dev=1` and `VITE_SHOW_UNBUILT` show all 7 items marked dev, production mode ignores both, run selector scope, user menu, Home card, footer wording and OFF tags; `nav.test.ts` with fixture configs. `sh backend/scripts/ci_local.sh frontend`: lint ✔, 61 passed, build ✔
- Evidence (Chrome headless, 1366×768, `web` rebuilt): [shell-v12-home.png](docs/evidence/phase1/shell-v12-home.png), [shell-v12-unbuilt-route.png](docs/evidence/phase1/shell-v12-unbuilt-route.png) (`/consents` by URL renders, not in the menu). `grep showUnbuilt dist/assets/*.js` → 0 matches. The v1.1 screenshots stay as history

### Pending / known issues
- Two-laptop check and GitHub CI run (above).
- `make` on Windows must run from Git Bash (needs `sh`); the WinGet `make` is on the user PATH only in new shells.
- `npm ci` warns that eslint 9.39 and recharts 2.x are past their support windows; versions follow TRD section 3 (Recharts 2) and are frozen. Revisit only if a problem appears.
- React Router prints v7 future-flag warnings in tests (harmless).
- Sidebar collapse to 56 px icons and stage mode: Phase 9.
- Sidebar badges (Review, Consents), role filtering, a working run selector, user menu entries, breadcrumbs: later phases (DEC-05, DEC-10).
- Doc alignment owed (DEC-10): PRD 11.2/§15/FR-1463/FR-1491, UI/UX brief §4/§6 footer, TRD TR-UI-04 names.
- JetBrains Mono glyph check (`O0o l1I| 5S 8B` at 13 px, UI/UX brief 3.3) to be confirmed visually in Phase 9.

## Phase 2 · Database

### Done
- **T1 `0001_initial`** (TR-DAT-01): `backend/app/db/migrations/versions/0001_initial.sql` is Backend Schema Appendix A (schema v0.6) byte for byte. `test_sql_file_equals_appendix_a` compares it with `impdocs/` on every run. The API lifespan runs `alembic upgrade head` first (`app/db/migrate.py`). `0001` has no downgrade (§13)
- **T2 models and contracts**: `app/db/models.py` has the 26 SQLAlchemy 2.0 models. `test_models_match_db.py` checks columns, types, nullability, primary keys and foreign keys of every table against the migrated DB. `app/schemas/jsonb.py` has one Pydantic model per §6 JSONB contract (`CONTRACTS`, `DICTIONARY_CONTENT`). Evidence rows require `rule` and `rule_text` and exclude `MISSING_BOTH` (TR-DAT-05). Audit diffs reject secret keys
- **T3 COPY helper** (TR-DAT-03): `app/db/copy.py` `copy_rows()` uses psycopg 3 `COPY … FROM STDIN` in batches of 5,000 inside the caller's transaction. Values are adapted by the column's DB type (dict/list → jsonb, list → arrays)
- **T4 `make seed`**: `templates/{valve,pipe,flange,fastener,motor,gasket}.yaml` = PRD Appendix A (checked by a test). `templates/uom.yaml` = TRD Appendix I. `templates/dictionary.yaml` = abbreviations (PRD 9.2 rule 9), header synonyms (TRD H.1) and an empty UNSPSC map. `app/db/seed.py`:
  - CPSE-A/B/C (synthetic names, "Oil & Gas", 64-hex random salt)
  - meera MAKER/A, arjun CHECKER/B, kavya CHECKER/C, admin, auditor, erp INTEGRATOR, all with bcrypt hashes of `DEMO_PASSWORD`; `must_change_password = not SEED_DEMO_USERS`
  - 5 templates ACTIVE plus gasket DRAFT; 4 dictionaries v1 ACTIVE
  - safe to run again; writes no audit rows (DEC-11)
- **T5 §15 checks** (`tests/integration/test_schema.py`, 25 cases): consent from the maker's and checker's CPSEs; decline needs a reason (≥ 5 chars); one consent per CPSE; change-notice acknowledgement needs a time; audit UPDATE, DELETE and TRUNCATE rejected; audit hash unique; CNMC format (5 bad forms), MERGED needs a survivor, short description ≤ 40; second active mapping rejected, removal needs who, when and why, then the code can be remapped; maker ≠ checker; one task per cluster; pair order and per-run uniqueness; `cannot_link` order; one ACTIVE template/dictionary version; source note ≥ 5; re-ingest blocked by content hash; the 4 TRD Appendix J queries run with expected results; Appendix B as `specid_app` (own CPSE's rows only, aggregate returns both CPSEs, DELETE on `audit_event` → permission denied)
- `ci_local.sh` mounts `impdocs/` and `templates/` read-only so the verbatim checks and seed tests run (on GitHub CI they come from the checkout)
- Test totals: backend **109 passed** (was 3), 0 skipped. Frontend unchanged (61). `BUILT_PATHS` unchanged (no screens in this phase)

### Gate: "Done when" criteria

| Criterion | Result | Evidence |
|---|---|---|
| A fresh `make up && make seed` creates all tables | PASS | `docker compose down -v` (the old volume had 0 tables), then `make up` → api log `Running upgrade -> 0001_initial`, `migrations_applied`; api healthy. `make seed` → `{"added": {"cpse": 3, "app_user": 6, "template": 6, "dictionary": 4}}`; a second `make seed` → all 0. psql: 26 tables (+ `alembic_version` = `0001_initial`), users and roles as above, 0 audit events. `curl 127.0.0.1:8080/api/v1/health` → `HTTP/1.1 200 OK`, `"db":"ok"`, `"templates":null` (DEC-05, until Phase 4) |
| `pytest tests/integration/test_schema.py` passes (append-only audit, active-mapping uniqueness, maker ≠ checker, pair order, CNMC format) | PASS | `25 passed in 3.96s` on a throwaway PostgreSQL 16; full `sh backend/scripts/ci_local.sh backend`: ruff ✔, black ✔, `109 passed`, coverage gate passed (still vacuous: `core/` is empty until Phase 4) |

### Pending / known issues
- **Never point the backend test suite at the stack's database.** The integration fixture drops and recreates schema `public`. CI and `ci_local.sh` use throwaway containers.
- `/health` reports `templates: null` until the Phase 4 loader exists (DEC-05). The SYNTHETIC DATA badge stays always on (DEC-10). No synthetic batches exist until Phases 4–5.
- The API connects as the DB owner until Phase 8 (DEC-12).
- `change_notice.delta` has no shape in §6 yet. A Pydantic model will be added with SF-12 (P1).
- Starlette prints a deprecation warning about `httpx` in the TestClient (harmless; versions frozen).
