# Build plan: SpecID v2 in two goes

This is the plan Claude follows to build the whole product (`docs/SOLUTION.md`, told as a story in `docs/STORY.md`) in **two long, autonomous working sessions ("goes")**. It replaces the phase order of `impdocs/SIH26099_SpecID_06_Implementation_Plan.md`; the other `impdocs/` documents stay the detailed spec for screens, endpoints and tables.

- **Go 1 · The complete product without the heavy AI.** Upload → run → review → consent → national code → crosswalk and migration → registry, search, dashboard, look-alikes. At the end you can demo the whole PS story.
- **Go 2 · AI, money, proof and polish.** Local AI models, the verified AI reader, ask-don't-guess, savings and stock sharing, the SAP simulator, the evaluation page, the rulebook preview, polish and the demo snapshot.

Each go is long (many hours). Claude keeps working through context summaries, commits after each work package, and only stops for the reasons in section 4.

---

## 1. Ground rules during a go

1. Work on a branch (`v2-go1`, then `v2-go2`), one commit per work package (WP), message format `WP1.3: <what>`. **Never push** unless you say so.
2. After every WP: run the backend tests (`ci_local.sh backend`), the frontend tests, and that WP's own checks. A red test is fixed before moving on.
3. Keep every hard rule of `CLAUDE.md`: pure `core/`; nothing overrides a veto; golden tests never edited; offline at runtime; DB changes only by migration; audit event on every state change; maker ≠ checker; consent before issue; synthetic data labelled; no hand-typed result numbers; no "first/only/best/beats".
4. When a spec detail is unclear, pick the option that matches `impdocs/` most closely, log it in `docs/DECISIONS.md` (next DEC number), and continue. Don't stop for small questions.
5. Every new endpoint gets an RBAC row in `tests/api/test_rbac.py`; every new screen is added to `BUILT_PATHS`.
6. Proof of done is **command output and screenshots**, saved under `docs/evidence/v2-go1/` and `docs/evidence/v2-go2/`.
7. `PROGRESS.md` is updated at the end of every WP (one line) and at the end of each go (summary).

---

## 2. Go 1 · The complete product (without heavy AI)

| WP | What gets built | Main files | Done when |
|---|---|---|---|
| **1.0 Setup** | Branch; update `CLAUDE.md` (docs/ v2 is the source of truth for order and scope); DEC entries for SOLUTION §12 changes; Postgres image with pgvector; migration `0002` (`material_record.stock_qty`, `cnmc.hsn`, 768-dim `vector` columns for embeddings); drop torch / sentence-transformers / FAISS from the image | `CLAUDE.md`, `docs/DECISIONS.md`, `backend/app/db/migrations/versions/0002_*`, `models.py`, `docker-compose.yml`, `Dockerfile` | migration up on a fresh DB; schema tests green |
| **1.1 Generator v1** | Synthetic files also get procurement lines (date, qty, price, plant) and stock on hand; price spread per entity; same seed → same hash | `app/eval/generator.py`, tests | 3 CPSE files + procurement + stock generated; hash stable |
| **1.2 Typo-tolerant dictionary** | Fuzzy repair of known engineering words (`LFANGE`, `PIEP`, `CLSAS`, `INDUCTINO`); face phrases (`RAISED FACE` → RF, `FLAT FACE` → FF, `RING TYPE JOINT` → RTJ); unknown values stay unknown, never a conflict (Phase 4 findings a, b) | `core/normalise.py`, `templates/dictionary.yaml`, DEV entries in conformance | golden 25/25 still green; re-measured "can't tell" rate lower; 0 hard negatives merged |
| **1.3 Ingest** | Upload CSV/XLSX, encoding detection, header auto-mapping incl. SAP preset, UoM aliases, idempotent re-upload, quality report + health score; procurement upload | `services/ingest.py`, `api/uploads.py`, `schemas/` | API test: 3 files in → records + report; re-upload adds nothing |
| **1.4 Candidates** | Blocking on (category, size), BM25 keyword channel, MPN channel; channel bitmask per pair; pair-completeness measured on truth | `services/candidates.py` | ≥ 95% of true pairs reached on seed-7 (measured and logged) |
| **1.5 Run engine** | Background worker: extract → candidates → decide → COPY pairs → cluster → look-alikes + baselines → stats; progress every ≤ 2 s; cancel; `AUTO_ELIGIBLE` stored as REVIEW | `services/runs.py`, `services/jobs.py`, `api/runs.py` | a CROSS_CPSE run on 3k records finishes < 10 min with stats |
| **1.6 Frontend kit** | Design-system components: VerdictBadge, EvidenceCard, RulePopover, DataTable, SyntheticBadge, NextStepCard, ConsentStrip, AirGapStatus, charts with table fallback | `frontend/src/components/` | component tests green |
| **1.7 Screens: upload, quality, runs** | S2 upload & mapping, S3 quality report + health score, S4 run list / new run / live console | `frontend/src/pages/` | browser: upload 3 files → run → DONE (screenshots) |
| **1.8 Review** | Review service (state machine, maker ≠ checker 403), S5 queue, S6 cluster review (hero), S7 pair modal | `services/review.py`, `api/review.py`, pages | maker proposes, own-confirm blocked in UI + API |
| **1.9 Consent + issue** | Consent service (ALL_PARTICIPANTS / NONE), S18 inbox, CNMC issuance (sequence, Luhn, canonical spec, 40-char text, long text, class path, base UoM, crosswalk rows), change notices + S19 | `services/consent.py`, `services/registry.py`, `services/notices.py` | 3-CPSE cluster waits for CPSE-C, issued on last consent; decline recorded |
| **1.10 Registry & exports** | S8 registry list + CNMC detail, crosswalk CSV/JSON/SAP-style (CSV-injection guard), per-CPSE migration pack | `api/registry.py`, `api/exports.py`, pages | files download and re-import cleanly |
| **1.11 Search-before-create** | Registry search index + `POST /search-before-create` (p95 ≤ 1 s), S9 | `services/search.py` | known valve → USE_EXISTING |
| **1.12 Look-alike Guard + dashboard v1** | S13 look-alikes with the differing attribute highlighted; S0 dashboard: duplicates per CPSE, health, backlog, top clusters | pages, `api/dashboard.py` | panels filled from the run, no typed numbers |
| **1.13 Egress guard + air-gap** | `security/egress.py` in API and worker, `/system/airgap`, footer counter | `security/egress.py` | Wi-Fi off: demo path works; counter 0 |
| **1.14 Go-1 end-to-end proof** | Automated end-to-end test (API) of the full story; headless-browser screenshots of every built screen; PROGRESS summary | `tests/e2e/`, `docs/evidence/v2-go1/` | story passes twice in a row; all tests green |

**Your check after Go 1 (about 30 minutes):** follow `docs/evidence/v2-go1/CLICK_TEST.md`, which Claude writes. It walks you through 3 browser windows (meera, arjun, kavya) from upload to national code issued.

---

## 3. Go 2 · AI, money, proof and polish

| WP | What gets built | Main files | Done when |
|---|---|---|---|
| **2.0 Models via Ollama** | `make models`: make sure `granite4.1:3b`, `qwen2.5:3b-instruct`, `nomic-embed-text` are present (already on this laptop); write `models/manifest.json` with digests and licences; `llm` container for the air-gapped demo sharing the model folder; dev override to the host Ollama | `Makefile`, `backend/scripts/models.py`, `docker-compose*.yml` | with Wi-Fi off, the models answer from disk |
| **2.1 Category classifier** | char n-gram classifier trained on the train split; abstains below threshold; `class_source = ML` | `ai/classifier.py`, `core/classify.py` hook | records with no category word get classified; tests |
| **2.2 Meaning search** | `nomic-embed-text` embeddings stored in pgvector as the 4th candidate channel; S4 shows all four channels | `ai/embeddings.py`, `services/candidates.py` | pair completeness re-measured; channel stats show "dense" |
| **2.3 LLM bake-off** | Try 2–3 small open models on a fixed sample: speed per record on this laptop (CPU, then GPU if possible), share of correct and grounded values; pick one; record the result | `docs/evidence/v2-go2/llm_bakeoff.md` | a model chosen with measured numbers, or the layer marked OFF |
| **2.4 Verified AI reader** | LLM reads only gaps left by layers 1–3; returns value + span; grounding check (span exists, value in domain, rule parser agrees); cache by content hash; provenance in `attr_meta`; AI-VERIFIED badge and source highlighting in S6/S7; run console "rules / AI / person" split | `ai/llm_reader.py`, `ai/grounding.py`, pages | property test: invented values always rejected; "can't tell" rate lower; **0 hard negatives merged** |
| **2.5 Ask, don't guess** | Question routed to the owning CPSE's inbox; answer with source note (≥ 5 chars) → re-decide → cluster updated | `services/questions.py`, S18 tab, S6 drawer | can't-tell pair flips after an answer |
| **2.6 Money** | Savings & stock-sharing service: price spread per CNMC, pooled demand, price gap, idle-stock transfer suggestions; S0 panels + S15 pooling page | `services/savings.py`, pages | panels filled from data; wording says "gap", never "saving achieved" |
| **2.7 ERP integration** | API keys for INTEGRATOR; S14 SAP "Create Material" simulator with live duplicate warning; OpenAPI served locally; HSN on CNMC from a verified table | `api/keys.py`, S14 page | typing a duplicate of an issued code shows the warning |
| **2.8 Evaluation** | Eval runner: splits, metrics, false merges k of n with Wilson / rule-of-three bound, baselines B1/B2 tuned on validation, report Markdown/JSON; S11 + honesty panel; S17 About (shared honesty text) | `eval/runner.py`, `eval/metrics.py`, pages | `make eval SEED=7` writes a report; S11 shows it |
| **2.9 Real-text test** | Load your labelled real-text file (if provided) from a git-ignored folder; separate REAL-TEXT section in S11 | `eval/realtext.py` | shown if the file exists; hidden with an explanation if not |
| **2.10 Rulebook + impact preview** | S10 template list + draft editor; YAML validation; `decide(..., templates=draft)` over stored pairs; affected CNMCs per CPSE; golden-test gate; acknowledged activation | `services/rulebook.py`, S10 | the demo draft shows transitions; activation blocked until golden green |
| **2.11 Golden tests to 60+** | New cases for every template (incl. AI-reader and typo cases) | `tests/golden/` (new files only) | ≥ 60 golden green |
| **2.12 Polish** | Loading / empty / error states, 1366×768, stage mode, focus rings, banned-words test, fonts offline, "stay signed in" toast | pages | design checklist (UI/UX brief §11) ticked |
| **2.13 Demo kit** | `make snapshot` / `make restore` (< 2 min); demo script; README; 4 browser profiles guide; final screenshots for the PPT team | `Makefile`, `README.md`, `docs/DEMO.md` | restore + full demo offline 3× in a row |

**Your check after Go 2 (about 45 minutes):** follow `docs/DEMO.md` exactly as you would on stage, with Wi-Fi off.

---

## 4. When Claude stops during a go (and only then)

| Stop reason | What you'll be asked |
|---|---|
| Docker isn't running or a container won't start after 2 fixes | restart Docker Desktop / approve a fix |
| A download fails (Go 2, WP 2.0) | check the internet connection, or choose a smaller model |
| An action is destructive (deleting data, rewriting git history, removing volumes) | yes or no |
| A real conflict between the safety rules and a feature | which wins |
| The laptop can't run the LLM fast enough on CPU or GPU | keep the AI reader OFF, or pick a smaller model |

Everything else is decided, logged in `docs/DECISIONS.md`, and reported at the end of the go.

---

## 5. Risks to the plan

| Risk | Plan |
|---|---|
| A go runs out of time or context | Each WP is committed; the next session resumes from `PROGRESS.md` at the next WP |
| LLM too slow on this laptop | Only gaps go to the LLM; cache; GPU try; else the layer is labelled OFF and the demo uses rules + classifier + embeddings |
| Your friend pushes to `main` meanwhile | Claude works on a branch; merging is done with you at the end |
| Docker memory too low | `.wslconfig` raised to 10 GB before Go 2 |
| The finale bans pre-written code (Q-01) | The build becomes the rehearsed reference; the docs stay the spec |
