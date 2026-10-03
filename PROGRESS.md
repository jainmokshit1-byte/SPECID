# PROGRESS

Current phase: **Phase 1 · Setup — done** (2 criteria PENDING, see below). Next: Phase 2 · Database (awaiting approval of its plan).

Build mode: **preparation build** (before the finale). Scope locked to **PRD v0.5 P0**. Deviations: [docs/DECISIONS.md](docs/DECISIONS.md).

## Open questions

| ID | Question | Status / working assumption |
|---|---|---|
| Q-01 | Do the 2026 finale rules allow code written before the event? | **Open.** Treated as a preparation build |
| Q-02 | Finale duration, team size, venue hardware, internet | **Open.** Assume 36 h and a team of 6 |
| DEC-07 | Which phase builds S17 About & honesty (P0, not scheduled in the plan)? | **Open.** Proposal: Phase 7 |

## Standing decisions that affect later phases

- **Memory (DEC-09):** Docker stays at default memory (~8 GB). Demo dataset ≈ 3,000 records (`n_entities` ≈ 1,200, a parameter); evaluation preset `hard_negative_share = 0.5`; report the real *n* of hard negatives and its bound; performance budgets measured on 3k; auto-eligibility OFF; `mem_limit` api 4g / db 1g (applied); embedding batch 64; one job worker.
- **Template activation (DEC-04):** golden tests + ADMIN acknowledgement of the impact preview; no second ADMIN.

## Phase 1 · Setup

### Done
- Repository layout per TRD Appendix L; `.gitignore` (models, data, `.env`), `.gitattributes` (LF)
- `docker-compose.yml`, `frontend/nginx.conf`, both Dockerfiles as TRD Appendix A; `backend` network `internal: true`; additions DEC-02 (`GIT_COMMIT`) and DEC-09 (`mem_limit`)
- `.env.example` (TRD Appendix C + `CONSENT_MODE`, DEC-01)
- Backend skeleton: FastAPI, `/api/v1/health` (API-24; DB ping, model manifest, guard status, consent mode, git commit; 503 if DB unreachable), settings model (TRD Appendix D + DEC-01/02), structlog JSON logs with `X-Request-ID`, OpenAPI at `/api/v1/openapi.json`, CDN Swagger UI disabled (TD-08)
- Frontend skeleton: Vite 5 + React 18 + TS strict + Tailwind 3 with tokens from UI/UX brief §3/§9; fonts and icons bundled; app shell (SYNTHETIC ribbon, sidebar with the 7 groups of App Flow 3.1, top bar, air-gap footer); placeholder pages for all 25 shell routes of App Flow §2, `/login` outside the shell, 404
- Dependencies frozen: `backend/requirements.lock` (core), `requirements-ml.lock` (CPU torch 2.14.1+cpu, sentence-transformers, faiss-cpu), `requirements-dev.txt`, `frontend/package-lock.json` (TR-OPS-03)
- CI workflow (TRD Appendix G); local mirror `backend/scripts/ci_local.sh`; Makefile with every Appendix B target (unbuilt ones print their phase and exit 1)
- Tests: backend 3 (health 200, health 503 without DB, OpenAPI served / CDN docs off); frontend 30 (route table equals App Flow §2, every route renders in the shell with ribbon and footer, no AIR-GAPPED claim before `/system/airgap`, login outside shell, 404)

### Gate: "Done when" criteria

| Criterion | Result | Evidence |
|---|---|---|
| `http://127.0.0.1:8080` shows the shell with a working sidebar | PASS on this laptop (Windows 11, Docker 29.8.1) | All 26 App Flow routes (+ an unknown path, which renders the 404 page) return 200 through nginx `try_files`; headless Chromium at 1366×768 rendered the shell and clicking sidebar "Consents" opened S18 with the item highlighted: [shell-dashboard.png](docs/evidence/phase1/shell-dashboard.png), [shell-consents.png](docs/evidence/phase1/shell-consents.png). Fonts loaded locally (Inter 400/500/600, JetBrains Mono 400); 0 requests to non-local hosts |
| … on two laptops / two OSes | **PENDING** | only one machine available |
| `/api/v1/health` returns 200 through nginx | PASS | `curl -i 127.0.0.1:8080/api/v1/health` → `HTTP/1.1 200 OK`, `{"status":"ok","git_commit":"2401cd2","db":"ok","models":null,"templates":null,"egress_guard":{"enabled":true,"installed":false},"consent_mode":"ALL_PARTICIPANTS",...}`; `docker compose ps`: api and db healthy |
| CI green on `main` | **PENDING** (no GitHub remote yet). Local run of the same jobs in the same images: PASS | `make test` (backend: ruff ✔, black ✔, pytest 3 passed, coverage gate passed; frontend: eslint + prettier ✔, vitest 30 passed, tsc + vite build ✔). Note: the coverage gate is vacuous until `core/` has code (0 statements = 100%) |
| `docker network inspect specid_backend --format '{{.Internal}}'` prints `true` | PASS | Prints `true` (`specid_frontend` prints `false`); api and db attach only to `specid_backend`, web to both; from inside `api`, a connection to 1.1.1.1 fails with `Network is unreachable`; `make offline-check` passes its network part and says PARTIAL for the Phase 5 counter check |

### Pending / known issues
- Two-laptop check and GitHub CI run (above).
- `make` on Windows must run from Git Bash (needs `sh`); the WinGet `make` is on the user PATH only in new shells.
- `npm ci` warns that eslint 9.39 and recharts 2.x are past their support windows; versions follow TRD section 3 (Recharts 2) and are frozen. Revisit only if a problem appears.
- React Router prints v7 future-flag warnings in tests (harmless).
- At 1366×768 the sidebar scrolls to reach the Integration group (fine for now; stage mode and collapse come in Phase 9).
- Sidebar badges, role filtering, run selector, user menu: later phases (DEC-05).
- JetBrains Mono glyph check (`O0o l1I| 5S 8B` at 13 px, UI/UX brief 3.3) to be confirmed visually in Phase 9.
