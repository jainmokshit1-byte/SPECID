# SpecID

A governed national material registry for CPSEs (SIH 2026 · PS SIH26099). It turns ERP material records into verified specifications, decides IDENTICAL / EQUIVALENT / NOT_EQUIVALENT / INSUFFICIENT_DATA with an attribute veto, and issues one Common National Material Code (CNMC) per specification with a crosswalk to every CPSE legacy code.

**Status:** prototype under construction. See [PROGRESS.md](PROGRESS.md) for the current phase and [docs/DECISIONS.md](docs/DECISIONS.md) for deviations from the specification in [impdocs/](impdocs/).

**Honesty note:** all data in this repository is synthetic. Results on synthetic data are optimistic by construction and are not a measure of performance on real CPSE data.

## Requirements

Docker Engine ≥ 24 with Compose v2, git and GNU make. Python and Node run inside containers. On Windows run `make` from Git Bash or WSL.

## Start

```sh
cp .env.example .env      # then set local values
make up                   # builds and starts db, api, web
```

Open http://127.0.0.1:8080. API health: http://127.0.0.1:8080/api/v1/health. OpenAPI: `/api/v1/openapi.json`.

## Cloud demo (free)

Neon (database) + Render (API) + Netlify (web app), synthetic data only, one-click demo roles:
step by step in [docs/DEPLOY.md](docs/DEPLOY.md). The local stack above is the on-premise,
air-gapped build.

## Commands

| Command | Does |
|---|---|
| `make up` / `make down` | start / stop the stack |
| `make test` | the CI jobs (lint + tests, backend and frontend) in containers |
| `make lint` | ruff, black, mypy (core), eslint, prettier |
| `make doctor` | versions and `.env` check |
| `make offline-check` | air-gap checks (Phase 1: internal network only) |

Other targets from TRD Appendix B (`models`, `seed`, `demo-data`, `test-ml`, `eval`, `bench`, `snapshot`, `restore`, `purge-real`) print the phase that builds them.

## Layout

TRD Appendix L: `backend/app/{core,services,api,db,eval,security,schemas}`, `frontend/src`, `templates/`, `models/` (git-ignored), `data/`, `docs/`, `.github/workflows/`.
