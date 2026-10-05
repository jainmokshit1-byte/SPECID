# CLAUDE.md — SpecID (SIH 2026 · PS SIH26099)

You are building **SpecID**, a governed national material registry for CPSEs. It turns ERP material records into verified specifications, decides IDENTICAL / EQUIVALENT / NOT_EQUIVALENT / INSUFFICIENT_DATA with an attribute veto, and issues one Common National Material Code (CNMC) per specification with a crosswalk to every CPSE legacy code. Goal: a production-grade, organisation-friendly product with a standout UI, built for PS SIH26099.

## Source of truth (v2, from 5 Oct 2026)

| Read for | File |
|---|---|
| **What the product is, scope, pillars, changes from v1** | `docs/SOLUTION.md` |
| **Build order: goes, chunks, work packages (WP), done checks** | `docs/BUILD_PLAN.md` |
| Where the build stands, next WP | `PROGRESS.md` |
| Detailed requirements (FR-, NFR-, SF-), API shapes, algorithms | `impdocs/SIH26099_SpecID_Prototype_PRD.md`, `impdocs/SIH26099_SpecID_TRD.md` |
| Screens, routes, buttons, empty/error states | `impdocs/SIH26099_SpecID_03_App_Flow.md` |
| Colours, fonts, components, layouts | `impdocs/SIH26099_SpecID_04_UI_UX_Design_Brief.md` |
| Database | the migrations in `backend/app/db/migrations/versions/` (0001 = Backend Schema Appendix A verbatim) |
| Plain-language story, onboarding | `docs/STORY.md`, `docs/GET_READY.md` |

Precedence: `docs/SOLUTION.md` + `docs/BUILD_PLAN.md` > migrations (database) > TRD > PRD > other `impdocs/`. `impdocs/` is kept as the detailed v1 spec and is not edited; where v2 differs, `docs/DECISIONS.md` says so. `impdocs/SIH26099_SpecID_06_Implementation_Plan.md` is history (replaced by `docs/BUILD_PLAN.md`).

## How to work

- Work through `docs/BUILD_PLAN.md` **work package by work package**, in order, without stopping for approval between WPs. One commit per WP: `WP1.3: <what>` (requirement IDs in the body when useful).
- After every WP: run the backend tests (`sh backend/scripts/ci_local.sh backend`), the frontend tests when frontend changed, and the WP's own done check. Fix red before moving on. Add one line to `PROGRESS.md`.
- Small unclear details: choose what matches `impdocs/` most closely, log it in `docs/DECISIONS.md` (next DEC number), continue.
- **Stop and ask only** for: a destructive action (deleting data or volumes, rewriting git history, force push), Docker or a download failing after two fixes, a conflict between a hard rule and a feature, or the laptop not running the local LLM fast enough. Never push unless the user says so.
- New endpoint → `require(Action.X)` + a row in `ENDPOINTS` in `backend/tests/api/test_rbac.py`. New screen → add its path to `BUILT_PATHS` in `frontend/src/routes.ts`.
- Evidence (command output, screenshots) goes in `docs/evidence/v2-go1/` or `docs/evidence/v2-go2/`.
- Reference conformance: `backend/tests/reference/specid_ref.py` stays byte-identical to PRD Appendix C; `core/` may differ from it only through a named DEV entry in `DEVIATIONS` (`tests/reference/test_conformance.py`) with a DEC row and a narrow predicate.

## Hard rules (never break)

1. `core/` is pure: no imports from `services/`, `api/`, `db/`, `ai/`, FastAPI, SQLAlchemy, psycopg or HTTP clients.
2. **No score, ML model or LLM may override a veto or produce a verdict.** `decide()` stays deterministic and symmetric. An LLM may only *propose* attribute values with a source span; a value is used only if it passes the grounding check (span in the text, value in the template domain, the rule parser reads the span the same way). Classifier output abstains below its threshold.
3. Never edit golden tests to make them pass; fix the code or ask. New golden cases go in new entries or files.
4. **Offline at runtime (on-premise build):** no CDN links, no web fonts, no telemetry, no runtime downloads, no hosted LLM APIs. Fonts and icons are bundled. The one exception is the **hosted cloud demo** (`DEMO_MODE=true`, synthetic data only), which may use the Gemini provider (`AI_PROVIDER=gemini`, DEC-41/43); the egress guard still blocks every other host, and the footer must say "Cloud demo", never "Air-gapped".
5. Database changes only through Alembic migrations in `backend/app/db/migrations/versions/`; `models.py` must match the migrated DB (`test_models_match_db.py`).
6. Every state-changing action writes an audit event in the same transaction.
7. Maker ≠ checker; a multi-CPSE cluster gets a CNMC only after every participating CPSE consents (`CONSENT_MODE=ALL_PARTICIPANTS`).
8. No real confidential CPSE data in the repo, logs or fixtures. Synthetic data is always flagged and shown with the SYNTHETIC DATA badge. A real public-text test set lives only in a git-ignored folder.
9. Never hard-code result numbers in UI text or reports; numbers come from runs. Never write "first", "only", "best", "beats" in UI text or user-facing docs (NFR-14).
10. Secrets only in `.env` (never committed); `.env.example` has placeholders.

## Stack

- **Backend:** Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, psycopg 3, PostgreSQL 16 **with pgvector**, rapidfuzz, rank-bm25, scikit-learn, PyJWT, bcrypt, structlog, pytest + hypothesis.
- **AI (local, via Ollama):** reader `granite4.1:3b` (Apache-2.0; comparison `qwen2.5:3b-instruct`), embeddings `nomic-embed-text` (768 dimensions, stored in pgvector). No torch / sentence-transformers / FAISS. With Ollama unavailable, the app runs rules-only and says "AI reader off".
- **Frontend:** React 18, TypeScript (strict), Vite, Tailwind (tokens from the UI/UX brief §9), TanStack Query + Table, React Router, Radix UI, lucide-react, Recharts, Framer Motion; typed API client generated from OpenAPI.
- **Runtime:** Docker Compose — `web` (nginx), `api`, `db` (+ `llm` for the air-gapped demo); network `backend` is `internal: true`. During development the API may use the host's Ollama (`docker-compose.dev.yml`).

## Repository layout

`backend/app/{core,ai,services,api,db,eval,security,schemas}` · `frontend/src` · `templates/` · `models/` · `data/` · `docs/` · `.github/workflows/`. `core/` = pure engine; `ai/` = Ollama clients, classifier, grounding check; `services/` = business logic with the DB; `api/` = thin HTTP layer.

## Commands

Windows has no `make` by default; every target has a `docker compose` equivalent.

| Make (Git Bash / WSL / Linux) | Plain equivalent |
|---|---|
| `make up` / `make down` | `docker compose up -d --build` / `docker compose down` |
| `make seed` | `docker compose exec api python -m app.db.seed` |
| `make demo-data` | `docker compose exec api python -m app.cli generate --seed 7 --out data/synthetic/seed-7` |
| `make test` | `sh backend/scripts/ci_local.sh all` |
| `make lint` | `sh backend/scripts/ci_local.sh lint` |
| `make offline-check` | `docker network inspect specid_backend --format '{{.Internal}}'` |
| engine on one pair | `docker compose exec api python -m app.cli decide --a "<text>" --b "<text>"` |

## Current position

See `PROGRESS.md` (next WP first).
