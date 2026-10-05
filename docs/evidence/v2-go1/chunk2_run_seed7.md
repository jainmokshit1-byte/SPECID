# Chunk 2 evidence: upload and cross-CPSE run on the live stack (5 Oct 2026)

SYNTHETIC DATA. Written by the team that wrote the rules; optimistic by construction; not a
measure of performance on real CPSE data.

Driven through the API of the running stack (`docker compose`, pgvector Postgres 16, one worker):
three seed-7 files uploaded by meera / arjun / kavya, ingested with purchase history, then one
`CROSS_CPSE` run by meera.

| Step | Result |
|---|---|
| Ingest CPSE-A / B / C | 993 / 1,019 / 1,011 records, 0.3–0.4 s each, health score 99 each |
| Purchase history | 2,845 / 2,928 / 2,974 lines, 0 unmatched, 0 invalid |
| Run (3,023 records) | DONE in 11.2 s (read 987 ms, candidates 146 ms, decide 7,513 ms, cluster 72 ms) |
| Candidate pairs | 78,201 (channels: blocking 50,249, lexical 27,938, part number 277, dense 0) |
| Verdicts | IDENTICAL 157, EQUIVALENT 1,019, NOT_EQUIVALENT 70,932, INSUFFICIENT_DATA 6,093 |
| Clusters | 689 proposed, 0 blocked edges |
| Specs | 2,964 parsed, 59 without a recognised category |
| Egress guard | installed, `blocked_egress` 0 |

Automated checks in `backend/tests/api/test_runs.py` (small dataset, same code path): no hard
negative merged and no true pair vetoed, no cluster contains a vetoed pair, no same-CPSE pair in
a cross-CPSE run, every stored evidence row has a rule and rule text and no MISSING_BOTH row,
cancel and failure remove partial results, interrupted runs are failed at restart, and one test
runs the job in the real spawned worker process.
