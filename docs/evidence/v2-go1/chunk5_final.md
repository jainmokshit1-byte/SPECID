# Chunk 5 + Go 2 evidence: final screens, evaluation, cloud rehearsal (5 Oct 2026)

SYNTHETIC DATA. Written by the team that wrote the rules; optimistic by construction; not a
measure of performance on real CPSE data.

## Screens (live stack, `docker compose`, screenshots in `screens/`)

Every App Flow route now renders a real page: `home`, `search`, `lookalikes`, `pooling`, `erp-sim`,
`evaluation`, `rulebook`, `rulebook-valve`, `about` (new), plus the chunk 3–4 screens.

## Evaluation, seed 7 (eval `eac2510c`, 1,200 entities, 3,355 records, test split 5,869 pairs)

| Method | Wrong merges on look-alikes | 95% upper bound | Precision | Same items found (strict) | Decided |
|---|---|---|---|---|---|
| SpecID | 0 of 321 | 0.93% | 100.00% | 61.2% | 88.2% |
| B1 text only (τ 0.99) | 18 of 321 | 8.69% | 35.25% | 29.0% | 100% |
| B2 text + numbers (τ 0.54) | 56 of 321 | 21.98% | 41.40% | 36.7% | 100% |

Can't tell: 181 true pairs (38.8%), 177 of them miss a key value in the text. Blocking reaches
97.7% of true pairs while comparing 2.39% of all pairs. All 248 of B1's wrong merges (any pair) were
"can't tell" for SpecID.

## Free-tier rehearsal (`deploy/render.Dockerfile`, `--memory=512m --cpus=0.1`)

Fresh pgvector database, `DATABASE_URL=postgresql://…` (Neon form), `DEMO_MODE=true`,
`DEMO_ENTITIES=400`, `JOB_MODE=thread`, `OFFLINE=false`, `AI_PROVIDER=off`.

| Check | Result |
|---|---|
| Port open (health answers) | 33 s |
| Demo data ready (ingest 3 CPSEs, run, 3 codes issued, evaluation) | 222 s |
| Peak memory | 219 MB of 512 MB, not OOM-killed, 0 restarts |
| Issued codes | NMC-00000000018, NMC-00000000026, NMC-00000000034 |

Found and fixed during the rehearsal: in demo mode the bootstrap thread started before the
templates were loaded, and the classifier trained before the port opened (minutes at 0.1 CPU).
Now the templates load first, and in demo mode the classifier trains in the background thread
(DEC-43).

## Not yet verified (needs the user's accounts / key)

- Real Neon, Render and Netlify deployment (docs/DEPLOY.md).
- Gemini reader and embeddings end to end (`AI_PROVIDER=gemini`), placeholder key until supplied.
