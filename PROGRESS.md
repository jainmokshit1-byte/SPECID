# PROGRESS (v2)

Plan: [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md) · Product: [docs/SOLUTION.md](docs/SOLUTION.md) · Decisions: [docs/DECISIONS.md](docs/DECISIONS.md) · v1 history (Phases 1–4): [docs/history/PROGRESS_v1.md](docs/history/PROGRESS_v1.md)

**Branch:** `v2-go1` · **Now:** Go 1, chunk 5 (search-before-create, Look-alike Guard, dashboard, end-to-end proof next) · chunks 1–4 done 5 Oct · Known issue: motor type `AC` vs `AC-IND` still conflicts (DEC-34).

## Starting point (5 Oct 2026)

v1 Phases 1–4 done (gate G1, tag `gate-1`): pure engine (`core/`), schema v0.6 (26 tables), auth + RBAC + hash-chained audit, users, synthetic generator v0, CLI. 512 backend tests pass, `core/` coverage 98%. Seed-7 truth pairs: 897 of 2,166 true matches found, 1,265 INSUFFICIENT_DATA, 4 wrongly vetoed, 0 of 1,217 hard negatives merged. About half of the missing core values are in the text but not extracted (typos, face phrases, no category word).

## Go 1 · The complete product without heavy AI

| Chunk | WP | What | Status |
|---|---|---|---|
| 1 | 1.0 | Working rules (CLAUDE.md, PROGRESS.md), DEC entries, pgvector + migration 0002, drop torch/FAISS | done |
| 1 | 1.1 | Generator v1: procurement lines, stock on hand, price spread | done |
| 1 | 1.2 | Typo-tolerant dictionary, face phrases, unresolvable values stay unknown | done |
| 2 | 1.3 | Ingest: upload, SAP preset, UoM, quality report, health score | done |
| 2 | 1.4 | Candidates: blocking, BM25, MPN; pair completeness | done |
| 2 | 1.5 | Run engine: background job, progress, cancel, stats | done |
| 2 | 1.13 | Egress guard + `/system/airgap` | done |
| 3 | 1.6 | Frontend design system | done |
| 3 | 1.7 | Screens S2, S3, S4 | done |
| 4 | 1.8 | Review: queue, cluster review, pair modal, maker ≠ checker | done |
| 4 | 1.9 | Consent, CNMC issuance, change notices | done |
| 4 | 1.10 | Registry, exports, migration pack | done |
| 5 | 1.11 | Search-before-create | |
| 5 | 1.12 | Look-alike Guard, dashboard v1 | |
| 5 | 1.14 | End-to-end proof, CLICK_TEST.md | |

## Log

| Date | WP | Result |
|---|---|---|
| 2026-10-05 | 1.0 | v2 docs + CLAUDE.md; pgvector image; migration 0002 (stock, HSN, vector(768) + HNSW); torch/FAISS removed (API image 683 MB); 519 backend tests pass (DEC-31, DEC-32) |
| 2026-10-05 | 1.1 | Generator v1: 8,747 synthetic purchase lines, stock, annual qty/value; codes, texts and truth files identical to v0 (DEC-33) |
| 2026-10-05 | 1.2 | Dictionary v2: spelling repair (DEV-6), face phrases, STD/XS without size unknown (DEV-7), migration 0003; seed-7: true matches found 897 → 1,344, can't-tell 1,265 → 822, false vetoes 4 → 0, false merges 0; 564 backend tests (DEC-34) |
| 2026-10-05 | 1.3 | Ingest: /batches upload, mapping suggestions (SAP preset), ingest with specs, quality report + health score, purchase history (DEC-35) |
| 2026-10-05 | 1.4 | Candidates: blocking + BM25 + MPN (+dense hook); seed-7 reach 98.1% of categorised true pairs at k=200 (DEC-36) |
| 2026-10-05 | 1.13 | Egress guard (blocks and counts, shared counter), /system/airgap, health reports it truthfully |
| 2026-10-05 | 1.5 | Run engine: worker process, progress, cancel, pairs API, clusters; seed-7 3,023 records DONE in 11.2 s, 716 backend tests (DEC-37) |
| 2026-10-05 | 1.6 | Design system: buttons, cards, badges, meters, health ring, stepper, states, drop zone, logo; light/dark/system + stage mode (DEC-38) |
| 2026-10-05 | 1.7 | Screens S2 upload & mapping, S3 quality, S4 runs / new run / live console; Home follows the data; 127 frontend tests (DEC-38) |
| 2026-10-05 | 1.8–1.10 | Review → maker/checker → multi-CPSE consent → CNMC issuance → registry, exports, migration pack, change notices; live demo flow issued NMC-00000000018; backend 818, frontend 135 tests (DEC-39, DEC-40) |
