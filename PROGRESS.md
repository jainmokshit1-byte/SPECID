# PROGRESS (v2)

Plan: [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md) · Product: [docs/SOLUTION.md](docs/SOLUTION.md) · Decisions: [docs/DECISIONS.md](docs/DECISIONS.md) · v1 history (Phases 1–4): [docs/history/PROGRESS_v1.md](docs/history/PROGRESS_v1.md)

**Branch:** `v2-go1` · **Now:** Go 1, chunk 1 · **Next WP:** see the first unchecked row below.

## Starting point (5 Oct 2026)

v1 Phases 1–4 done (gate G1, tag `gate-1`): pure engine (`core/`), schema v0.6 (26 tables), auth + RBAC + hash-chained audit, users, synthetic generator v0, CLI. 512 backend tests pass, `core/` coverage 98%. Seed-7 truth pairs: 897 of 2,166 true matches found, 1,265 INSUFFICIENT_DATA, 4 wrongly vetoed, 0 of 1,217 hard negatives merged. About half of the missing core values are in the text but not extracted (typos, face phrases, no category word).

## Go 1 · The complete product without heavy AI

| Chunk | WP | What | Status |
|---|---|---|---|
| 1 | 1.0 | Working rules (CLAUDE.md, PROGRESS.md), DEC entries, pgvector + migration 0002, drop torch/FAISS | done |
| 1 | 1.1 | Generator v1: procurement lines, stock on hand, price spread | |
| 1 | 1.2 | Typo-tolerant dictionary, face phrases, unresolvable values stay unknown | |
| 2 | 1.3 | Ingest: upload, SAP preset, UoM, quality report, health score | |
| 2 | 1.4 | Candidates: blocking, BM25, MPN; pair completeness | |
| 2 | 1.5 | Run engine: background job, progress, cancel, stats | |
| 2 | 1.13 | Egress guard + `/system/airgap` | |
| 3 | 1.6 | Frontend design system | |
| 3 | 1.7 | Screens S2, S3, S4 | |
| 4 | 1.8 | Review: queue, cluster review, pair modal, maker ≠ checker | |
| 4 | 1.9 | Consent, CNMC issuance, change notices | |
| 4 | 1.10 | Registry, exports, migration pack | |
| 5 | 1.11 | Search-before-create | |
| 5 | 1.12 | Look-alike Guard, dashboard v1 | |
| 5 | 1.14 | End-to-end proof, CLICK_TEST.md | |

## Log

| Date | WP | Result |
|---|---|---|
| 2026-10-05 | 1.0 | v2 docs + CLAUDE.md; pgvector image; migration 0002 (stock, HSN, vector(768) + HNSW); torch/FAISS removed (API image 683 MB); 519 backend tests pass (DEC-31, DEC-32) |
