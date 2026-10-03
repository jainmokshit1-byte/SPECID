# CLAUDE.md — SpecID (SIH 2026 · PS SIH26099)

You are building **SpecID**, a governed national material registry for CPSEs: it turns ERP material records into verified specifications, decides IDENTICAL / EQUIVALENT / NOT_EQUIVALENT / INSUFFICIENT_DATA with an attribute veto, and issues one Common National Material Code (CNMC) per specification with a crosswalk to every CPSE legacy code.

## Source of truth: `impdocs/` (read before coding, never edit without asking)

| Read for | File |
|---|---|
| What to build, requirement IDs (FR-, NFR-, US-, SF-) | `impdocs/SIH26099_SpecID_Prototype_PRD.md` (v0.5) |
| How to build: stack, modules, algorithms, compose, CI | `impdocs/SIH26099_SpecID_TRD.md` (v1.1) |
| Every route, button, redirect, empty/error state | `impdocs/SIH26099_SpecID_03_App_Flow.md` |
| Colours, fonts, components, layouts | `impdocs/SIH26099_SpecID_04_UI_UX_Design_Brief.md` |
| Database: the ONLY DDL (Appendix A, schema v0.6) | `impdocs/SIH26099_SpecID_05_Backend_Schema.md` |
| Build order, phases, done criteria, gates | `impdocs/SIH26099_SpecID_06_Implementation_Plan.md` |
| Why / pitch / competitors (context only) | `impdocs/SIH26099_Research_Solution_PPT_Content.md`, `impdocs/SIH26099_SpecID_Competitive_Review.md` |

Precedence when documents disagree: Backend Schema (for the database) > TRD (for technical choices) > PRD (for requirements) > others. **If they contradict each other, stop and ask; do not guess.**

## How to work

- Build **one phase of the Implementation Plan at a time**, in order. Do only the tasks of the current phase. A phase is done only when its "Done when" criteria pass; show the evidence (command output).
- Before each phase: read the phase's *Inputs* sections, then present a short plan (files to create, tests to write) and wait for approval.
- After each task: run tests, then commit with the requirement ID first, e.g. `FR-602: veto on core conflict`.
- At the end of a phase: update `PROGRESS.md` (phase, what is done, what is pending, known issues, gate result).
- Never invent screens, tables, columns, endpoints or rules that are not in the docs. If something is missing, propose the doc change first.

## Hard rules (never break)

1. `core/` is pure: no imports from `services/`, `api/`, `db/`, FastAPI, SQLAlchemy or psycopg (TRD TR-ARC-10).
2. **No score, ML model or LLM may override a veto** (PRD FR-602, NFR-04). `decide()` stays deterministic and symmetric.
3. Never edit golden tests to make them pass; fix the code or ask.
4. **Offline at runtime:** no CDN links, no web fonts, no telemetry, no runtime downloads, no hosted LLM APIs (TRD TR-SEC-05/06, TR-UI-07). Fonts and icons are bundled.
5. Database changes only through Alembic migrations that match Backend Schema Appendix A.
6. Every state-changing action writes an audit event in the same transaction.
7. Maker ≠ checker; a multi-CPSE cluster gets a CNMC only after every participating CPSE consents (PRD FR-1501).
8. No real CPSE data in the repo, logs or fixtures. Synthetic data is always flagged and shown with the SYNTHETIC ribbon.
9. Never hard-code result numbers in UI text or reports; numbers come from runs. Never write "first", "only", "best", "beats" in UI or docs (NFR-14).
10. Secrets only in `.env` (never committed); `.env.example` has placeholders.

## Stack (TRD section 3)

Backend: Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, psycopg 3, PostgreSQL 16, rapidfuzz, rank-bm25, sentence-transformers (CPU torch) + faiss-cpu, scikit-learn, PyJWT, bcrypt, structlog, pytest + hypothesis.
Frontend: React 18, TypeScript (strict), Vite, Tailwind (tokens from UI/UX brief §9), TanStack Query, React Router, Radix UI, lucide-react, Recharts.
Runtime: Docker Compose — `web` (nginx), `api`, `db`; network `backend` is `internal: true` (TRD Appendix A).

## Repository layout

Follow TRD Appendix L exactly (`backend/app/{core,services,api,db,eval,security,schemas}`, `frontend/src`, `templates/`, `models/`, `data/`, `docs/`, `.github/workflows/`). Keep `impdocs/` untouched.

## Commands (Makefile, TRD Appendix B)

`make up` · `make down` · `make seed` · `make test` · `make test-ml` · `make eval SEED=7` · `make lint` · `make snapshot` · `make restore` · `make offline-check`

## Current phase

See `PROGRESS.md`. If it does not exist, the current phase is **Phase 1 · Setup**.
