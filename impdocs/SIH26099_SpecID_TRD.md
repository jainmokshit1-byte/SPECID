# TRD: SpecID Prototype
## Technical Requirements Document · PS SIH26099: AI-Driven Standardization and Harmonization of Material Codes Across CPSEs

| Field | Value |
|---|---|
| Document | Technical Requirements Document (TRD) for the SpecID **prototype** |
| Version / status | **v1.2** · 3 Oct 2026. v1.2 aligns with build decisions DEC-01 … DEC-27 (Phases 1–4): `CONSENT_MODE` and `GIT_COMMIT` settings, memory limits and the 3k demo set (DEC-09), normaliser fixed point (TR-MOD-01), `uom_canonical(raw, dictionary)`, `load_dictionary`, `cluster_with_blocked`, component names `SyntheticBadge` / `AirGapStatus`, air-gap wording, tooling files, TD-11 … TD-16. v1.1: v1.1: multi-CPSE consent (TR-MOD-32, TR-ALG-11), rulebook impact preview promoted to P0 with affected CNMCs and CPSEs (TR-ALG-10), change notices (TR-MOD-33, P1), schema v0.6, full route list from App Flow, production path (section 19) |
| Derived from | `SIH26099_SpecID_Prototype_PRD.md` **v0.6** (what to build) and `SIH26099_Research_Solution_PPT_Content.md` **v0.5** (why). This TRD says **how**. Companions: 03 App Flow, 04 UI/UX Design Brief, 05 Backend Schema (authoritative DDL), 06 Implementation Plan |
| PS owner | Ministry of Petroleum & Natural Gas · Chennai Petroleum Corporation Limited (CPCL) · Software · Smart Automation |
| Audience | The six-person build team (PRD 14.1 roles R1–R6) |
| Owner | [tech lead, R1] |

---

## 0. How to read this TRD

**Relationship to the PRD.** The PRD owns *requirements* (`FR-`, `NFR-`, `US-`), the decision policy (PRD 9.5), the schema (PRD Appendix E) and the reference code (PRD Appendix C). The TRD owns *technical design*: components, interfaces, data contracts, algorithms in implementable detail, deployment, performance budgets and test infrastructure. When the two disagree, raise it as a technical decision (section 17) and update the PRD; do not silently diverge.

**ID scheme.** `TR-<area>-<nn>` for technical requirements. Areas: `ARC` architecture · `MOD` modules · `DAT` data · `API` interfaces · `UI` frontend · `ALG` algorithms · `PRF` performance · `SEC` security · `OPS` deployment and operations · `TST` testing · `CI` build pipeline. `TD-nn` = technical decision. Every TR names the PRD requirement(s) it implements.

**Priority** follows the PRD: **P0** finale must · **P1** should · **P2** could.

**Integrity rules carried over.** Nothing in this TRD is a measured result. Performance figures are budgets tagged **[T]** (target). Version numbers are *minimums*; exact versions are frozen in a lockfile at T+0 (TR-OPS-03). Where a technical fact depends on a CPSE's systems (SAP fields, call points), it is marked *confirm with CPSE SAP team*.

**Words used precisely**

| Term | Meaning in this TRD |
|---|---|
| Spec | The derived specification of one material record: category, attributes, notes, residual tokens (PRD 9.4) |
| Pair | An unordered pair of records `(rec_a, rec_b)` with `rec_a < rec_b` (UUID order) |
| Run | One harmonisation run over one or more batches (PRD FR-505) |
| Registry | The set of issued CNMCs with their crosswalk rows |
| Guard | The egress guard (PRD 9.13.7) |

---

## 1. Purpose, scope and constraints

### 1.1 Purpose
Specify the technical design that delivers every **P0** requirement of PRD v0.5 inside a 36-hour finale on one laptop, offline, and leaves clean extension points for P1/P2 and the pilot.

### 1.2 In scope
Backend services and core library, database, REST API, web UI, evaluation harness, synthetic data generator, deployment (Docker Compose, air-gapped), test and CI infrastructure.

### 1.3 Out of scope (prototype)
Live SAP write-back, multi-tenant hardening, high availability, Kubernetes, SSO, fine-tuned transformers, federated matching (PRD 1.4).

### 1.4 Technical constraints

| ID | Constraint | Source | Consequence |
|---|---|---|---|
| C-01 | Runs on one 8-core / 16 GB laptop, Linux / macOS / Windows (WSL2) | PRD NFR-01, NFR-06 | Single API process; no external search engine; FAISS in memory |
| C-02 | **No outbound network at runtime** | PRD FR-1303, FR-1461–1463 | All models pre-downloaded; internal Compose network; egress guard |
| C-03 | 36-hour build, 6 people | PRD 14 | Boring, well-known libraries; no Celery, no Kafka, no custom infra |
| C-04 | Data at prototype stage is synthetic | PRD 10 | SYNTHETIC flag carried from batch to every response |
| C-05 | A score or model may never override a veto | PRD FR-602, NFR-04 | `decide()` is pure and rule-first; ML outputs are inputs to ranking only |
| C-06 | Decisions must be reproducible | PRD NFR-02 | Seeds everywhere; deterministic sort orders; model and template versions stored per run |
| C-07 | CPSE data is confidential | PRD 12 | Price and vendor aggregated cross-CPSE; no real data in repo, logs or screenshots |

### 1.5 PS capability → technical component map

| PS key capability | Main components (this TRD) | PRD requirements |
|---|---|---|
| 1 AI material matching & recommendation | `core/normalise`, `core/extract`, `services/candidates` (BM25 + FAISS + blocking), `core/decide` | FR-201–202, FR-301, FR-501–505, FR-601–611 |
| 2 Standardisation & classification | `core/classify` (rules + ML), `core/units` (UoM), `core/shortdesc`, `services/registry` | FR-205, FR-402, FR-405, FR-901 |
| 3 Duplicate / near-duplicate detection | Run modes, `core/radar`, `services/dashboard` | FR-505, FR-1401–1403, FR-1201 |
| 4 Common National Material Code | `core/cnmc`, `services/registry` (issuance transaction) | FR-901–903 |
| 5 Code mapping & migration | `services/registry`, `services/migration` | FR-903–907 |
| 6 Dashboard & analytics | `services/dashboard`, S0 | FR-1201, FR-1203 |
| 7 Audit trail & governance | `services/audit`, `services/consent` (multi-CPSE consent), `api/auth`, template versioning + impact preview, `services/notices` (P1) | FR-1301–1302, FR-401–404, FR-1451–1452, FR-1501–1513 |
| 8 SAP / ERP integration | `services/ingest` (SAP preset), `/search-before-create`, SAP-style exports, OpenAPI | FR-1001–1005, FR-905, FR-907 |

---

## 2. Architecture

### 2.1 Container view

```
                 laptop (host)
 ┌───────────────────────────────────────────────────────────────────────────┐
 │  browser ── http://127.0.0.1:8080 ──┐                                     │
 │                                     ▼                                     │
 │  network "frontend" (default)  ┌──────────┐                               │
 │  ─────────────────────────────►│   web    │ nginx: SPA files + /api proxy │
 │                                └────┬─────┘                               │
 │  network "backend" (internal: true, no route out)                         │
 │                                     ▼                                     │
 │                                ┌──────────┐   ┌──────────────────────┐    │
 │                                │   api    │──►│ db  PostgreSQL 16    │    │
 │                                │ FastAPI  │   └──────────────────────┘    │
 │                                │ + job    │   ┌──────────────────────┐    │
 │                                │   pool   │┄┄►│ ollama (profile llm, │    │
 │                                └──────────┘   │ P2, off by default)  │    │
 │                                 ▲ /models (read-only volume)          │    │
 └───────────────────────────────────────────────────────────────────────────┘
```

| ID | Requirement | PRD | Pri |
|---|---|---|---|
| TR-ARC-01 | Three always-on containers: `web`, `api`, `db`; `ollama` only under the Compose profile `llm` | 6.1, FR-306 | P0 |
| TR-ARC-02 | `api` and `db` attach **only** to network `backend` with `internal: true`; `web` attaches to `backend` and `frontend`; only `web` publishes a port, bound to `127.0.0.1` | FR-1462 | P0 |
| TR-ARC-03 | The API is a **single uvicorn worker** process. Long work runs in a `ProcessPoolExecutor` owned by that process (TR-MOD-30). Rationale: in-process state (egress counter, rate limiter, registry search index) stays consistent without Redis | 6.2, D-03 | P0 |
| TR-ARC-04 | Models (`all-MiniLM-L6-v2`, the category classifier) are mounted read-only at `/models`; nothing is downloaded at runtime | FR-1303, R-01 | P0 |
| TR-ARC-05 | Templates are YAML files mounted read-only at `/app/templates` and loaded into the `template` table at startup if their `(id, version)` is new | FR-401 | P0 |

### 2.2 Backend component view

```
backend/app/
├─ main.py            FastAPI app, lifespan: guard → settings → DB → templates → models → registry index
├─ settings.py        pydantic-settings, env-driven (Appendix C)
├─ security/          auth.py (JWT, bcrypt), rbac.py (role dependency), egress.py (EgressGuard)
├─ api/               one router per resource; thin: validate → call service → map to response
├─ core/              PURE functions, no I/O, no DB: normalise, units, classify, extract, templates,
│                     decide, cluster, cnmc, shortdesc, radar, substitute (P1)
├─ services/          I/O and orchestration: ingest, procurement, harmonise, candidates, registry,
│                     migration, search, review, dashboard, audit, exports, jobs
├─ eval/              generator, baselines, metrics, runner, report
├─ db/                models.py (SQLAlchemy 2.0), session.py, migrations/ (Alembic)
└─ schemas/           Pydantic v2 request/response models (Appendix F)
```

| ID | Requirement | Pri |
|---|---|---|
| TR-ARC-10 | `core/` has **no imports** from `services/`, `api/`, `db/` or any I/O library. Enforced by a test that inspects imports (TR-TST-12) | P0 |
| TR-ARC-11 | Every state-changing service function takes an open SQLAlchemy `Session` and writes its audit event **in the same transaction** (PRD invariant 4) | P0 |
| TR-ARC-12 | Routers contain no business logic; one service call per endpoint | P0 |

### 2.3 Key runtime sequences

**(a) Harmonisation run (PRD 6.4)**
```
POST /runs ─► api: insert run(QUEUED), audit ─► jobs.submit(run_id) ─► 202 {run_id}
worker process:
  1 status RUNNING
  2 load records of batch_ids without spec_record ─► normalise ─► classify ─► extract ─► COPY spec_record
  3 embeddings (if dense enabled) for new specs ─► store real[] ─► build per-category FAISS + BM25
  4 candidates = blocking ∪ BM25 top-k ∪ dense top-k ∪ MPN ; filter by mode ; dedupe
  5 decide each pair (memoised) ─► text_sim, lookalike, baseline flags ─► COPY pair_decision (batches of 5,000)
  6 constrained clustering ─► cluster, cluster_member, review_task
  7 stats JSON, status DONE, audit event
  progress: update run.stats.progress every ≤ 2 s (stage, done, total)
```

**(b) Review to CNMC issuance (one transaction, PRD 9.8)**
```
CHECKER POST /clusters/{id}/review {APPROVE}
  BEGIN
   assert maker_id != checker_id        (else 403)
   SELECT ... FOR UPDATE on cluster      (no double issuance)
   record consents: maker's CPSE (via MAKER_PROPOSAL), checker's CPSE (via CHECKER_CONFIRMATION)
   if consent_mode = ALL_PARTICIPANTS and some participating CPSE has no consent row:
       review_task.state = AWAITING_CONSENT ; audit ; COMMIT ; return   (issuance waits, sequence b2)
   nextval('cnmc_seq') ─► new_cnmc(seq)  (Luhn)
   canonical spec = union of member attrs ; short/long desc ; class path ; UNSPSC (if mapped)
   INSERT cnmc ; INSERT crosswalk × members (uom, uom_factor, relation, migration_action=NULL)
   UPDATE cluster status APPROVED ; review_task DONE
   audit_event (hash-chained)
  COMMIT ─► registry search index: add CNMC (in-memory, after commit)
```

**(b2) Multi-CPSE consent (PRD FR-1501–1504, P0)**
```
CHECKER of CPSE-C  POST /clusters/{id}/consent {CONSENT | DECLINE, reason}
  BEGIN
   assert user.cpse_id ∈ participating CPSEs and no consent row yet for that CPSE   (else 403 / 409)
   SELECT ... FOR UPDATE on review_task (state must be AWAITING_CONSENT)
   INSERT review_consent (via STEWARD) ; audit CONSENT_GIVEN / CONSENT_DECLINED
   if every participating CPSE has a row:
       members = records of CPSEs that consented
       if ≥ 2 members: issuance as in (b), crosswalk only for members ; else: cluster REJECTED (nothing to unify)
       declined CPSEs: dissent kept (review_consent DECLINE), change_notice CONSENT_DECLINED (P1)
       review_task.state = DONE
  COMMIT
```

**(c) Search-before-create**
```
POST /search-before-create {text, uom?, mpn?, cpse?}
 normalise ─► classify ─► extract ─► if category None: INSUFFICIENT_DATA "category not recognised"
 candidates from registry index: same category & DN ∪ BM25 top-20 ∪ dense top-20 ∪ MPN
 decide(query, cnmc_spec) for each ─► sort IDENTICAL, EQUIVALENT, INSUFFICIENT_DATA, NOT_EQUIVALENT
 recommended_action per PRD 9.11 ─► response (no DB write unless "create anyway", which audits a reason)
```

**(d) Supply attribute (P1, PRD 9.13.3)**: validate against value domain → `attribute_supply` row → update `spec_record.attrs` + `attr_meta[attr].tier = "USER"` → re-decide pairs of the record in the run → rebuild affected cluster(s) → audit → return changes. All in one transaction.

---

## 3. Technology stack

| Layer | Choice (minimum version) | Notes |
|---|---|---|
| Language | Python ≥ 3.11 | type hints everywhere |
| Web framework | FastAPI ≥ 0.110, uvicorn ≥ 0.29, python-multipart | uploads need python-multipart |
| Validation | Pydantic ≥ 2.6, pydantic-settings | |
| ORM / DB driver | SQLAlchemy ≥ 2.0, Alembic ≥ 1.13, psycopg ≥ 3.1 (`psycopg[binary]`) | psycopg 3 `COPY` for bulk inserts |
| Database | PostgreSQL 16 (`postgres:16-alpine`) | `gen_random_uuid()` built in |
| Text matching | rapidfuzz ≥ 3, rank-bm25 ≥ 0.2.2 | |
| Embeddings | sentence-transformers ≥ 2.6 with **CPU-only torch**; model `all-MiniLM-L6-v2` (384-d, Apache-2.0) | install torch from the PyTorch CPU wheel index to keep the image small (TD-05) |
| Vector search | faiss-cpu ≥ 1.7.4, `IndexFlatIP` on L2-normalised vectors (= cosine; exact, deterministic) | |
| ML | scikit-learn ≥ 1.4 (classifier, isotonic), joblib; LightGBM ≥ 4 (P1) | |
| Files | openpyxl (XLSX), charset-normalizer (encoding detection), PyYAML | |
| Auth | PyJWT ≥ 2.8, **bcrypt ≥ 4.1 used directly** | PRD lists passlib; passlib is unmaintained and warns with bcrypt 4.x (TD-04) |
| Logging | structlog (JSON) | |
| Tests | pytest, hypothesis, pytest-cov, httpx | |
| Lint | ruff, black, mypy (core/ only) | |
| Frontend | React 18, TypeScript 5, Vite 5, Tailwind 3, TanStack Query 5, React Router 6, Recharts 2, @tanstack/react-virtual, openapi-typescript | |
| Frontend tests | vitest; Playwright (P2) | |
| Containers | Docker Engine ≥ 24, Compose v2 | |

---

## 4. Module specifications: core (pure functions)

All signatures below are **contracts**. The reference implementation in PRD Appendix C already satisfies the core behaviour; production modules split it into files and add types.

### 4.1 Shared types (`core/types.py`)

```python
from dataclasses import dataclass, field
from typing import Literal, Any

Verdict = Literal["IDENTICAL", "EQUIVALENT", "NOT_EQUIVALENT", "INSUFFICIENT_DATA"]
Route   = Literal["AUTO_ELIGIBLE", "REVIEW", "NONE"]
Status  = Literal["MATCH", "PARTIAL", "CONFLICT", "MISSING_ONE", "MISSING_BOTH"]
Tier    = Literal["RULE", "ML", "NER", "LLM", "USER"]

@dataclass(frozen=True)
class AttrMeta:
    tier: Tier
    confidence: float            # rules = 1.0
    note: str | None = None      # conversion / inference, e.g. "4 IN = DN100"

@dataclass(frozen=True)
class Spec:
    category: str | None
    attrs: dict[str, Any]        # canonical values; None = not stated
    meta: dict[str, AttrMeta]    # per attribute
    residual: tuple[str, ...]    # tokens not consumed by any extractor
    mpn: str | None = None
    maker: str | None = None
    class_source: Literal["RULE", "ML", "NONE"] = "NONE"
    class_prob: float | None = None

@dataclass(frozen=True)
class EvidenceRow:
    attr: str; level: Literal["core", "ext"]; a: Any; b: Any; status: Status
    rule: str; rule_text: str; note_a: str | None; note_b: str | None

@dataclass(frozen=True)
class Decision:
    verdict: Verdict; route: Route; reasons: tuple[str, ...]
    evidence: tuple[EvidenceRow, ...]
    confidence: float | None     # heuristic p_rule in P0 (PRD 9.6); None for INSUFFICIENT_DATA
    template_version: int | None
```

### 4.2 Module contracts

| ID | Module | Public interface | Behaviour and invariants | PRD |
|---|---|---|---|---|
| TR-MOD-01 | `core/normalise.py` | `normalise(text: str, dictionary: Dictionary) -> str` | Ordered rules of PRD 9.2; expansions come from the versioned dictionary, not literals. Unicode NFKC first; non-printing characters removed. **The rules repeat until the output stops changing (max 8 passes)**, which makes the function **idempotent** (PRD 9.2, DEC-24); reaching the cap logs `normalise_max_passes_reached` with the input's SHA-256 only | FR-201–203 |
| TR-MOD-02 | `core/units.py` | `nps_to_dn(nps: str) -> int \| None`; `uom_canonical(raw: str, dictionary: Dictionary) -> tuple[str \| None, bool]` (value, ambiguous; aliases come from the versioned UOM dictionary, DEC-23); `hp_to_kw(hp: float) -> float` | Tables B.1 / B.2 of the PRD and the UoM alias table (Appendix I). Unknown sizes → `None`; ambiguous UoM (`MT`) → `(None, True)` | FR-202, FR-205 |
| TR-MOD-03 | `core/classify.py` | `classify(norm_text: str, model: CategoryModel \| None, threshold: float) -> tuple[str \| None, str, float \| None]` returns (category, source, probability) | Rules first (PRD Appendix C `CATS` order). If no rule fires and a model is loaded: predict; return the category only if `p ≥ threshold` (default 0.80), else `(None, "NONE", p)` | FR-402 |
| TR-MOD-04 | `core/extract.py` | `extract(text, mpn=None, maker=None, *, dictionary, model, threshold) -> Spec` | Normalise → classify → category extractor → residual tokens (minus stop words). Every conversion or inference recorded in `meta[attr].note` | FR-301–303, FR-307, FR-1431 |
| TR-MOD-05 | `core/templates.py` | `load_templates(dir) -> dict[str, Template]`; `load_dictionary(dir) -> Dictionary`; `Template` (Pydantic, the one definition; `schemas/jsonb.TemplateDefinition` is an alias) with `core`, `extended`, `tolerant`, `make`, `critical_default`, `value_domains`, `aliases`, `rule_text`, `substitutes` (P1), `class_path`, `unspsc` | Validation errors raise `TemplateError("<file>:<line>: <problem>")` and abort API startup (PRD 6.5); `/health` reports the loaded `{template_id: version}`. `rule_text` keys must be attributes of the template | FR-401, FR-405, FR-1432 |
| TR-MOD-06 | `core/decide.py` | `decide(a: Spec, b: Spec, templates: Mapping[str, Template], criticality: tuple[bool \| None, bool \| None] = (None, None)) -> Decision` | Exactly PRD 9.5 (including DEC-26: `IDENTICAL` only with MPN and manufacturer present on both sides, case-insensitive; unresolvable values are unknown, never a conflict). A missing template for the pair's category is a programming error (`KeyError`). **Pure and symmetric** (`decide(a,b).verdict == decide(b,a).verdict`). Criticality per item overrides the template default when given (PRD D-02). No ML input | FR-601–609, FR-611 |
| TR-MOD-07 | `core/cluster.py` | `constrained_clusters(n: int, edges: list[tuple[int,int,float]], conflict: Callable[[int,int], bool]) -> list[list[int]]` plus `cluster_with_blocked(...)` returning `BlockedEdge(i, j, score, reason ∈ {conflict, size cap})` | PRD 9.7. Edges sorted by (score desc, i, j) for determinism; the 200-member cap is checked before the conflict check. `conflict` is memoised by the caller | FR-701–703 |
| TR-MOD-08 | `core/cnmc.py` | `new_cnmc(seq: int) -> str`; `cnmc_valid(code: str) -> bool` | `NMC-` + 10 digits + Luhn digit | FR-902 |
| TR-MOD-09 | `core/shortdesc.py` | `short_desc(spec) -> str \| None`; `long_desc(spec) -> str` | ≤ 40 chars or `None` (never truncate); missing parts are left out, never printed as `None` (DEV-1); long-description order per PRD 9.9 | FR-901 |
| TR-MOD-10 | `core/radar.py` | `text_sim(a_norm, b_norm) -> float`; `lookalike_class(sim, verdict, hi, lo) -> str \| None` | token-set ratio / 100 on **normalised** text | FR-1401 |
| TR-MOD-11 | `core/baselines.py` | `b1(sim, tau) -> bool`; `b2(sim, raw_a, raw_b, tau) -> bool` | PRD 10.2b; numeric tokens from **raw** texts | FR-1411 |
| TR-MOD-12 | `core/confidence.py` | `p_rule(decision) -> float \| None` | `0.98 − 0.10 × ext_flags − 0.15 × residual_flag`, floor 0.50 | FR-607 |
| TR-MOD-13 | `core/substitute.py` (P1) | `substitute_direction(a, b, decision, template) -> Literal["A_FOR_B","B_FOR_A"] \| None` | Only for `NOT_EQUIVALENT`; every `CONFLICT` row must be covered by one SME rule in the same direction; otherwise `None` | FR-612 |

### 4.3 Category ML model (TR-MOD-03 detail)

| Item | Specification |
|---|---|
| Pipeline | `TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=2, sublinear_tf=True)` → `LogisticRegression(max_iter=2000, class_weight="balanced", random_state=7)` |
| Training data | Synthetic **train** split records (PRD 10.1) rendered in styles A–C, **with the category word removed** in 50% of samples so the model learns from technical context (`CL150 WCB RF`), plus a `NONE` class from generic non-template phrases |
| Labels | VALVE, PIPE, FLANGE, FASTENER, MOTOR, GASKET (P1), NONE |
| Artifact | `models/category_clf-v1.joblib` + `category_clf-v1.json` (training seed, data hash, label set, validation accuracy, abstention rate) |
| Abstention | `max(predict_proba) < 0.80` [T] or predicted `NONE` → no category |
| Acceptance | Reported, not gated: accuracy on validation records with the category word removed; abstention rate; the CABLE probe abstains on 100% (PRD E-5) |
| Safety | ML-assigned categories carry `class_source = "ML"`; the evidence card shows it; the decision rules are identical afterwards (a wrong category produces different templates, which yields `NOT_EQUIVALENT` or `INSUFFICIENT_DATA`, never a merge across categories) |

---

## 5. Module specifications: services (I/O and orchestration)

| ID | Service | Responsibilities | Key technical rules | PRD |
|---|---|---|---|---|
| TR-MOD-20 | `services/ingest.py` | Upload, encoding detection, header mapping suggestions, ingest, quality report | Encoding via charset-normalizer on the first 1 MB, fallbacks UTF-8 → cp1252 → latin-1. XLSX via openpyxl read-only mode, first sheet. Mapping suggestions from the header-synonym table and **SAP preset** (Appendix H). Idempotency key `(cpse_id, legacy_code, sha256(row_canonical))`. Rows inserted with `COPY`. Quality report computed in SQL after ingest | FR-101–106, FR-1005 |
| TR-MOD-21 | `services/procurement.py` | Procurement-history upload and aggregation | Vendor hashed with `sha256(cpse_salt ‖ vendor)` at ingest; raw vendor never stored. Aggregates per record: `annual_qty`, `annual_value` (last 12 months of data), `last_price`, `n_vendors`; written to `material_record.annual_value` if not supplied in the master file | FR-107, FR-104 |
| TR-MOD-22 | `services/candidates.py` | Candidate generation | Algorithm TR-ALG-01. Per-category indexes built once per run | FR-501–504 |
| TR-MOD-23 | `services/harmonise.py` | Run orchestration (sequence 2.3a) | Stage timings in `run.stats.timings_ms`; cancellation flag checked between batches of 1,000 pairs | FR-505–507 |
| TR-MOD-24 | `services/review.py` | Maker–checker state machine | States `OPEN → MADE → DONE`; transitions in Appendix F.3; `403` if the same user makes and checks | FR-801–807 |
| TR-MOD-25 | `services/registry.py` | CNMC issuance, crosswalk, merge, unmerge (P1) | Transaction 2.3b; `SELECT … FOR UPDATE` on the cluster; partial unique index guards double mapping (PRD Appendix E) | FR-901–906, FR-1481 |
| TR-MOD-26 | `services/migration.py` | Migration pack | Algorithm TR-ALG-08 | FR-907 |
| TR-MOD-27 | `services/search.py` | Registry search index and search-before-create | In-memory index of ACTIVE CNMC specs: per-category BM25 over canonical long text, one FAISS index, MPN dict. Built at startup; incremental add after each issuance commit; full rebuild on merge/unmerge | FR-1001–1003 |
| TR-MOD-28 | `services/dashboard.py` | Dashboard and demand panel | Pure SQL (Appendix J); every response carries `run_id`, `is_synthetic`, `computed_at` | FR-1201, FR-1203 |
| TR-MOD-29 | `services/audit.py` | Hash-chained audit | TR-ALG-09 | FR-1302 |
| TR-MOD-30 | `services/jobs.py` | Background execution | `ProcessPoolExecutor(max_workers=1, initializer=worker_init, initargs=(blocked_counter,))`. `worker_init` installs the egress guard in the child and opens its own DB engine. One run at a time (queue in DB by status) | 6.2 |
| TR-MOD-31 | `services/exports.py` | CSV / JSON / SAP-style exports, reports | **CSV formula-injection guard:** any cell starting with `=`, `+`, `-`, `@`, tab or CR is prefixed with `'`. UTF-8 with BOM for Excel compatibility | FR-905, FR-1443 |
| TR-MOD-32 | `services/consent.py` | Multi-CPSE consent | Sequence 2.3(b2) and TR-ALG-11; consent and issuance in one transaction; 403 if the user's CPSE is not participating; 409 if that CPSE already answered | FR-1501–1504 |
| TR-MOD-33 | `services/notices.py` (P1) | Per-CPSE change notices | Created inside the transaction of the change that causes them (issuance, merge, unmerge, decline, activation); `delta` = migration rows that changed since the CPSE's last acknowledged notice; acknowledge is idempotent | FR-1511–1513 |

---

## 6. Algorithms (implementable detail)

### TR-ALG-01 Candidate generation (P0)

```
inputs: specs S (records of the run), mode, k_bm25=20, k_dense=20, block_cap=2000
for each category c:
  R_c = records of category c (category None → no candidates; they surface in the quality report)
  # 1 blocking on (c, size_dn) when size_dn is known
  for each block B with |B| ≤ block_cap: add all pairs in B
  for each block B with |B| >  block_cap: treat its records as "unblocked" (step 2)
  # 2 lexical: BM25 over normalised text of R_c; for every record with unknown size_dn
  #   or in an oversized block, add its top-k_bm25 neighbours
  # 3 dense (if enabled): FAISS IndexFlatIP over normalised MiniLM vectors of R_c; top-k_dense for every record
  # 4 MPN: records sharing (upper(maker), upper(mpn)) → all pairs
union → order each pair (min uuid, max uuid) → dedupe
mode filter: CROSS_CPSE drops same-cpse pairs; WITHIN_CPSE drops cross-cpse pairs; BOTH keeps all
store channel bitmask per pair (B=1, L=2, D=4, M=8) in run stats for pair-completeness analysis
```

| ID | Requirement | Pri |
|---|---|---|
| TR-ALG-01a | **Blocking key is `(category, size_dn)`, not `(category, size_dn, class)`** (TD-03). Keeping rating near-misses (CL150 vs CL300) in the same block ensures they become candidates, so the veto, the Look-alike Guard (FR-1402) and the false-merge metric see them. Hard negatives never reached by any channel are counted and reported (PRD 10.2) | P0 |
| TR-ALG-01b | Deterministic: BM25 ties broken by record UUID; FAISS `IndexFlatIP` is exact | P0 |
| TR-ALG-01c | Embeddings are computed once per spec (batch size **64**, DEC-09; `normalize_embeddings=True`) and stored in `spec_record.embedding`; re-runs reuse them | P0 |

### TR-ALG-02 Decision (P0)
Implemented exactly as PRD 9.5 and Appendix C `decide`. Technical additions:
- Memoise by `(spec_id_a, spec_id_b, template_versions_hash)` in a per-run LRU (`maxsize=500_000`).
- Item criticality: `critical = csv_criticality if set else template.critical_default` (either side critical → critical).
- `reasons` ordering: conflicts, then missing core, then extended flags, then residual flag, then criticality.

### TR-ALG-03 Constrained clustering (P0)
PRD 9.7. Complexity guard: before merging groups G1, G2, the cross check costs |G1|×|G2| `decide` calls; cap groups at 200 members (larger merges are refused and logged as a blocked edge "size cap"), which keeps the worst case bounded on the synthetic data.

### TR-ALG-04 Look-alike classification and baselines (P0)
For every stored pair: `text_sim` (TR-MOD-10), `lookalike` class with run thresholds, and `baseline = {"b1": bool, "b2": bool}` computed with the τ values in the run config. In evaluation runs τ1 and τ2 are first tuned on the validation split: grid 0.50–0.99 step 0.01, maximise F1, ties → higher τ (PRD 10.2b).

### TR-ALG-05 Threshold selection for auto-eligibility (P1)
```
pairs P on validation with truth and confidence p; sort by p desc
for each distinct τ (from high to low):
   n = |{p ≥ τ}| , k = TP among them
   lb = wilson_lower(k, n, z=1.96)
   keep the smallest τ with lb ≥ P* (0.99) and n ≥ 400
if none: auto-eligibility OFF; report n needed
```

### TR-ALG-06 UoM harmonisation (P0)
`uom_canonical()` maps aliases (Appendix I). In the crosswalk: `uom` = CPSE's canonical UoM; `uom_factor` = quantity of CNMC base UoM per one CPSE unit. Base UoM of a CNMC = most frequent canonical UoM among members (ties → `EA`). Same UoM → factor 1. Different UoM with no known factor → `NULL` and a review flag "UoM factor needed" (never guessed).

### TR-ALG-07 Substitute candidates (P1)
After `decide` returns `NOT_EQUIVALENT`, call `substitute_direction`. A template rule has the form:
```yaml
substitutes:
  - attr: body_material
    may_replace: {from_family: "304", to_family: "316"}   # 316 may replace 304
    requires_equal: [valve_type, size_dn, pressure_class, end_connection]
    approved_by: "<SME name>"     # rule inactive without it
```
Rules without `approved_by` are ignored. Stored in `substitution` with status `PROPOSED`; never passed to clustering.

### TR-ALG-08 Migration pack (P0)
For each CPSE c and each ACTIVE CNMC with ≥ 1 active crosswalk row from c:
```
members_c = active crosswalk rows of c for this CNMC
survivor  = argmax over members_c of (annual_value or 0, spec_completeness, -legacy_code lexical)  # deterministic
action(survivor)          = RETAIN
action(other, stock > 0)  = PHASE_OUT_WHEN_STOCK_ZERO      # stock / open orders known from FR-107 data
action(other, otherwise)  = BLOCK_FOR_NEW_PROCUREMENT
```
Write `migration_action` back to the crosswalk rows (audited). Output columns: `cpse, legacy_code, legacy_short_text, cnmc, cnmc_short_desc_40, relation, survivor, recommended_action, uom, uom_factor, stock_known, note`. Header note in the file: *recommendations; apply through your own master-data process (for SAP typically a material status such as MARA-MSTAE; confirm with your SAP team)*.

### TR-ALG-09 Audit hash chain (P0)
```
canonical(e) = json.dumps({actor_id, action, object_type, object_id, before, after, ts}, sort_keys=True,
                          separators=(",", ":"), ensure_ascii=False, default=str)
in the caller's transaction:
   SELECT pg_advisory_xact_lock(4242)                 # serialise appends
   prev = SELECT hash FROM audit_event ORDER BY id DESC LIMIT 1
   hash = sha256((prev or "GENESIS") + canonical(e)).hexdigest()
   INSERT audit_event(..., prev_hash=prev, hash=hash)
verify: stream rows by id, recompute, report the first mismatching id
```
`ts` is set in Python (UTC, microseconds) and stored as given, so the hash is recomputable.

### TR-ALG-10 Rulebook impact preview (P0 since v1.1)
1. ADMIN creates a DRAFT by editing the template YAML as text (validated by the `Template` Pydantic model; PRD FR-403).
2. Load stored specs of the chosen run's pairs (cap 200,000; uniform sample with seed 7 beyond that), call `decide(a, b, templates=draft)` (pure, TR-MOD-06), compare `(verdict, route)` with the stored values.
3. Join changed pairs to `cluster_member` and `crosswalk` to count **affected clusters, ACTIVE CNMCs and CPSEs**; a CNMC whose members would now be `NOT_EQUIVALENT` or `INSUFFICIENT_DATA` is flagged "needs re-review".
4. Run the draft's golden tests. Return transition counts, affected CNMCs per CPSE, the first 50 changes and the golden result; cache the result on the DRAFT (`template.definition._preview`).
5. Activation (PRD FR-1452) requires passing golden tests **and** an acknowledgement of the latest preview; it never edits stored decisions — CNMCs flagged in step 3 go back to the review queue and (P1) generate change notices (TR-MOD-33).
Only policy fields are previewable; extractor or dictionary changes need re-extraction (PRD 9.13.6). Budget [T]: ≤ 60 s for 250k stored pairs.

### TR-ALG-11 Multi-CPSE consent (P0)
- Participating CPSEs = distinct `material_record.cpse_id` of the cluster members.
- Implicit consents: maker's CPSE (on proposal), checker's CPSE (on confirmation). A CPSE with no user in the flow needs a steward (CHECKER with that `cpse_id`).
- `consent_mode` setting: `ALL_PARTICIPANTS` (default) or `NONE` (single-CPSE pilot); shown in the footer and written into every issuance audit event.
- A decline is final for that task; the CPSE's records stay unmapped and the pair set is not re-proposed to that CPSE until a template version or a supplied attribute changes (stored as `review_consent` DECLINE, checked by the queue builder).
- The queue for a steward (`GET /consents?cpse=`) lists tasks in `AWAITING_CONSENT` that lack its CPSE, oldest first.

---

## 7. Data design

### 7.1 Schema
The authoritative DDL is **doc 05 Backend Schema, Appendix A (schema v0.6: 58 statements, 26 tables, executed and constraint-tested on PostgreSQL 16)**, managed by Alembic (`db/migrations/0001_initial.py` generated from it).

| ID | Requirement | Pri |
|---|---|---|
| TR-DAT-01 | Migrations are the only way to change the schema; `alembic upgrade head` runs at API startup before templates load | P0 |
| TR-DAT-02 | UUIDs generated in Python (`uuid.uuid4()`) for bulk-inserted rows so pairs can be ordered and referenced before insert; server default kept for ad-hoc rows | P0 |
| TR-DAT-03 | Bulk writes (`material_record`, `spec_record`, `pair_decision`, `cluster_member`) use psycopg 3 `COPY … FROM STDIN` in batches of 5,000 rows | P0 |
| TR-DAT-04 | Every query on `pair_decision` filters by `run_id` (indexed). No cross-run joins on hot paths | P0 |
| TR-DAT-05 | `evidence` JSONB omits `MISSING_BOTH` rows on write to save space; the API re-adds them as a count | P0 |
| TR-DAT-06 | Add index `material_record (batch_id)` and `spec_record (category, ((attrs->>'size_dn')))` for blocking queries | P0 |

### 7.2 JSONB contracts

**`spec_record.attrs` / `attr_meta`**
```json
{"attrs": {"valve_type": "GATE", "size_dn": 100, "pressure_class": 150, "body_material": "A216-WCB",
           "end_connection": "FLANGED-RF", "design_standard": null, "trim": null},
 "attr_meta": {"valve_type": {"tier": "RULE", "confidence": 1.0, "note": "GV = GATE"},
               "size_dn": {"tier": "RULE", "confidence": 1.0, "note": "4 IN = DN100"}},
 "class": {"source": "RULE", "prob": null, "class_path": ["PIPING", "VALVE", "GATE"]}}
```

**`run.config`** (stored verbatim; every key has a default in `settings.RunDefaults`)
```json
{"mode": "CROSS_CPSE", "seed": 7, "bm25_k": 20, "dense_enabled": true, "dense_k": 20, "block_cap": 2000,
 "classifier_threshold": 0.80, "lookalike_min_sim": 0.85, "hidden_twin_max_sim": 0.75,
 "tau_b1": null, "tau_b2": null, "templates": {"valve": 1, "pipe": 1, "flange": 1, "fastener": 1, "motor": 1},
 "dictionary_version": 1, "uom_table_version": 1, "embedding_model": "all-MiniLM-L6-v2",
 "classifier_model": "category_clf-v1", "git_commit": "<sha>"}
```

**`run.stats`**
```json
{"progress": {"stage": "decide", "done": 120000, "total": 186000},
 "records": 10230, "specs_parsed": 9871, "unclassified": 359, "classified_by_ml": 214,
 "candidate_pairs": 186000, "channels": {"B": 140000, "L": 61000, "D": 58000, "M": 3100},
 "verdicts": {"IDENTICAL": 0, "EQUIVALENT": 0, "NOT_EQUIVALENT": 0, "INSUFFICIENT_DATA": 0},
 "clusters": 0, "blocked_edges": 0, "timings_ms": {"extract": 0, "embed": 0, "candidates": 0,
 "decide": 0, "cluster": 0, "write": 0}, "blocked_egress": 0}
```
(Numbers above illustrate the shape only; they are not results.)

**`pair_decision.evidence`**: array of `EvidenceRow` (section 4.1), exactly as PRD section 8 example.

**`upload_batch.quality`**: `{rows, empty_short_text, short_text_over_40, duplicate_legacy_codes, completeness: {field: share}, category_share: {cat: share}, core_parse_rate: {cat: share}, uom_ambiguous}`.

### 7.3 Sizing [T]

| Object | Prototype volume | Estimate |
|---|---|---|
| `material_record` | ~3k (demo, DEC-09); ~10k by parameter | < 20 MB |
| `spec_record` incl. 384-d `real[]` embedding | ~3k (≤ 10k) | ≈ 8 MB (≈ 25 MB at 10k) |
| `pair_decision` | ≤ 20 neighbours per record per channel → ≤ ~250k pairs | evidence ≈ 1 KB after TR-DAT-05 → ≈ 250–400 MB before TOAST compression |
| Registry | ~5k CNMC, ~10k crosswalk | < 20 MB |

If `pair_decision` exceeds 500 MB on a team laptop, store evidence only for pairs that are not `NOT_EQUIVALENT` with `text_sim < 0.5` and recompute on demand (the decision is pure).

### 7.4 Data retention and hygiene
Synthetic only in the repo (`data/synthetic/` is generated, git-ignored except `manifest.json`). Real CPSE files live outside the repo directory, are mounted at run time, and `make purge-real` drops their batches (`ON DELETE CASCADE`). Logs never contain descriptions unless `LOG_LEVEL=DEBUG`.

---

## 8. API technical specification

### 8.1 Conventions

| ID | Requirement | Pri |
|---|---|---|
| TR-API-01 | Base path `/api/v1`; OpenAPI 3.1 at `/api/v1/openapi.json`; Swagger UI at `/api/v1/docs` (served offline: FastAPI's default UI loads assets from a CDN, so mount the swagger-ui files locally or disable it) | P0 |
| TR-API-02 | Auth: `Authorization: Bearer <JWT>` (HS256, `exp` 8 h, claims `sub`, `role`, `cpse_id`); INTEGRATOR may use `X-API-Key` (stored as SHA-256) | P0 |
| TR-API-03 | Errors: RFC 7807 `application/problem+json` with `type`, `title`, `status`, `detail`, `instance`, and `errors[]` for validation | P0 |
| TR-API-04 | Pagination: `limit` (default 50, max 500) + opaque `cursor` (base64 of the last sort key) | P0 |
| TR-API-05 | Long operations return `202` with a `Location` header to poll (`/runs/{id}`, `/eval/runs/{id}`) | P0 |
| TR-API-06 | Every response that contains data from a synthetic batch has `"is_synthetic": true` at the top level | P0 |
| TR-API-07 | Request size: 50 MB for uploads (enforced by nginx and by FastAPI streaming check), 64 KB for JSON bodies | P0 |
| TR-API-08 | Rate limits (in-process token bucket): login 5/min per username; `search-before-create` 60/min per API key (FR-1004, P1) | P0/P1 |
| TR-API-09 | Idempotency: `POST /batches/{id}/ingest` and `POST /runs` accept `Idempotency-Key`; a repeat within 24 h returns the original response | P1 |

### 8.2 Endpoint catalogue
The full list (API-01 … API-38) and examples are in PRD section 8. Technical notes per group:

| Group | Endpoints | Technical notes |
|---|---|---|
| Auth | API-01, API-02 | Constant-time password check; generic error message on failure |
| Batches | API-03–06, API-33 | Upload streams to a temp file in a container volume, then parses; mapping saved per CPSE in `upload_batch.column_mapping` and copied as default for the next batch of that CPSE |
| Runs | API-07–10 | Progress from `run.stats.progress`; cancel sets `run.status = CANCELLING` read by the worker |
| Review | API-11–14 | Queue sorted by `priority desc, id`; cluster detail includes members, pairs, evidence, blocked edges |
| Consent | API-37 | Steward queue filtered by the caller's CPSE; consent action shares the issuance transaction (TR-MOD-32) |
| Change notices (P1) | API-38 | Inbox per CPSE; delta CSV streamed with the formula-injection guard |
| Registry | API-15–18, API-30, API-35 | Exports stream (`StreamingResponse`) |
| Search | API-19 | Must not write unless `create_anyway=true` with `reason` |
| Templates | API-20, 21, 29 | YAML ↔ JSON; DRAFT versions only from ADMIN |
| Evaluation | API-22, 27 | Report as Markdown and JSON with the honesty-panel text (FR-1442) |
| Audit | API-23 | `verify` streams in chunks of 10,000 rows |
| Radar | API-25, 26 | Served from `pair_decision` with the partial index on `lookalike` |
| Dashboard | API-34 | SQL in Appendix J |
| System | API-24, API-32 | `/health` checks DB connectivity and model presence; `/system/airgap` returns counter, network mode and guard status |

### 8.3 Key schemas
See Appendix F for the Pydantic models of `Decision`, `SearchRequest/Response`, `ReviewRequest`, `RunCreate`, `MigrationRow`, `DashboardSummary`.

---

## 9. Frontend technical specification

| ID | Requirement | Pri |
|---|---|---|
| TR-UI-01 | SPA routes exactly as **03 App Flow section 2** (that table is authoritative): `/login`, `/`, `/upload`, `/batches/:id/quality`, `/runs`, `/runs/new`, `/runs/:id`, `/review`, `/clusters/:id`, `/pairs/:id`, `/registry`, `/registry/:cnmc`, `/exports`, `/search`, `/templates`, `/templates/:id`, `/evaluation`, `/evaluation/:id`, `/lookalikes`, `/audit`, `/admin/users`, `/consents` (S18), `/about`; P1: `/erp-sim`, `/pooling`, `/notices` (S19) | P0 |
| TR-UI-02 | API types generated from OpenAPI with `openapi-typescript` (`npm run gen:api`); no hand-written response types | P0 |
| TR-UI-03 | Server state only through TanStack Query. Query keys `['runs', id]`, `['clusters', filters]`, … Run progress uses `refetchInterval: 2000` until status is terminal | P0 |
| TR-UI-04 | Shared components: `VerdictBadge` (colour + icon + text), `EvidenceCard` (rows, rule popover, conversion notes, collapsed MISSING_BOTH), `SyntheticBadge` (top bar, not dismissible), `AirGapStatus` (footer; polls `/system/airgap` every 10 s; grey "Air-gap status unavailable" when unreadable), `RulePopover`, `ProblemAlert` (renders RFC 7807), `DataTable` (virtualised with @tanstack/react-virtual for > 200 rows) | P0 |
| TR-UI-05 | Role-aware rendering from `/me`: makers never see Confirm; checkers never see Propose on their own proposals; the server still enforces (TR-SEC-03) | P0 |
| TR-UI-06 | Accessibility: verdicts never by colour alone; keyboard shortcuts (P1) with an overlay; focus visible; contrast ≥ 4.5:1 | P0 |
| TR-UI-07 | Monospace font for descriptions and codes; all fonts self-hosted (no Google Fonts at runtime, C-02) | P0 |
| TR-UI-08 | Charts (Recharts) only on S0, S11, S13; each chart has a table fallback | P0 |
| TR-UI-09 | Build output is static files served by nginx with an SPA fallback (`try_files $uri /index.html`) | P0 |
| TR-UI-10 | S14 mock ERP form: debounce 300 ms, cancel in-flight requests with `AbortController`, 40-character counter | P1 |

---

## 10. Performance requirements and budgets [T]

Measured on the reference laptop (8 cores, 16 GB) with the bundled seed-7 dataset (**~3k records**, 3 CPSEs; DEC-09: Docker at default memory, `api` 4 GB, `db` 1 GB). Budgets written for 10k are upper bounds; the 3k run must meet them.

| ID | Stage | Budget [T] | Technique |
|---|---|---|---|
| TR-PRF-01 | Ingest + quality report (3 files) | ≤ 30 s | COPY, SQL aggregates |
| TR-PRF-02 | Normalise + classify + extract 10k | ≤ 30 s | Pure Python, compiled regex at import |
| TR-PRF-03 | Embeddings 10k (MiniLM, CPU) | ≤ 120 s first run; 0 s on re-run | batch 64 (DEC-09); stored vectors; `torch.set_num_threads(cores)` |
| TR-PRF-04 | Candidate generation | ≤ 60 s | per-category indexes; numpy |
| TR-PRF-05 | `decide` + text_sim + baselines for ≤ 250k pairs | ≤ 150 s | memo; rapidfuzz C implementation; batch processing |
| TR-PRF-06 | Write pairs | ≤ 60 s | COPY batches of 5,000 |
| TR-PRF-07 | Clustering | ≤ 30 s | union-find + memoised conflict checks; group cap 200 |
| TR-PRF-08 | **End-to-end run** | **≤ 10 min** (PRD NFR-01) | sum of the above with margin |
| TR-PRF-09 | Search-before-create p95 with ~5k CNMCs | ≤ 1 s (PRD NFR-01b) | in-memory index; one embedding call (~tens of ms on CPU) |
| TR-PRF-10 | List endpoints, 100 rows | ≤ 200 ms server time (NFR-01c) | keyset pagination; indexes |
| TR-PRF-11 | Review queue for a 10k-record run | ≤ 2 s (FR-801) | priority index on `cluster (run_id, status, priority)` |

**Fallback if a budget is missed (PRD R-11):** reduce the demo dataset to 3k records; load a pre-computed run snapshot (TR-OPS-07).

---

## 11. Security requirements

| ID | Requirement | PRD | Pri |
|---|---|---|---|
| TR-SEC-01 | Passwords hashed with bcrypt, cost 12; minimum length 10; demo users only from `.env` | FR-1301, FR-1304 | P0 |
| TR-SEC-02 | JWT HS256 with a secret of ≥ 32 random bytes from env; startup fails if missing or short | FR-1301 | P0 |
| TR-SEC-03 | RBAC as a FastAPI dependency `require_role(*roles)` on every router; permission matrix of PRD section 2 encoded as a table and tested per endpoint | 2, FR-1301 | P0 |
| TR-SEC-04 | Separation of duties enforced in the service layer (maker ≠ checker; ADMIN cannot review); unit tested | FR-803 | P0 |
| TR-SEC-05 | **Egress guard** installed at the very start of `main.py` *and* in every job worker (`initializer`); counter is a `multiprocessing.Value('i')` shared with workers; allow-list = loopback + `DB_HOST` + `OLLAMA_HOST` when the llm profile is on. Scope note: libraries that open sockets in C (libpq inside psycopg) bypass it; the internal network is the real guarantee (PRD 9.13.7) | FR-1461–1463 | P0 |
| TR-SEC-06 | `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` and `SENTENCE_TRANSFORMERS_HOME=/models` set in the API image, so libraries never try to reach the Hugging Face hub | FR-1303 | P0 |
| TR-SEC-07 | CORS allows only the web origin; security headers set by nginx (`X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options: DENY`, a CSP with `default-src 'self'`) | NFR-07 | P0 |
| TR-SEC-08 | SQL only through SQLAlchemy bound parameters; no string-built SQL except the static queries in Appendix J | NFR-07 | P0 |
| TR-SEC-09 | Uploads: extension and magic-byte check (CSV/XLSX only), size cap, parsed in a temp dir, deleted after ingest | FR-101 | P0 |
| TR-SEC-10 | Exported CSVs neutralise formula injection (TR-MOD-31) | FR-905 | P0 |
| TR-SEC-11 | Cross-CPSE screens expose only aggregates of price and vendor (FR-104); per-record price visible only to users of the owning CPSE | FR-104, FR-107 | P0 |
| TR-SEC-12 | Logs: no passwords, tokens, API keys; request ids in every log line | 12 | P0 |
| TR-SEC-13 | API keys shown once at creation, stored hashed, revocable | FR-1004 | P1 |

---

## 12. Deployment and operations

| ID | Requirement | PRD | Pri |
|---|---|---|---|
| TR-OPS-01 | `docker compose up -d` starts the stack from a clean clone after `make models` and `cp .env.example .env`; Compose file in Appendix A | NFR-06 | P0 |
| TR-OPS-02 | Start order by health checks: `db` healthy → `api` (runs migrations, loads templates and models, then reports healthy) → `web` | 6.1 | P0 |
| TR-OPS-03 | Dependencies frozen at T+0: `backend/requirements.lock` (core, no torch), `backend/requirements-ml.lock` (CPU torch, sentence-transformers, faiss-cpu), `frontend/package-lock.json`. Images built and models fetched **while online**; after that the demo needs no network | C-02, R-01 | P0 |
| TR-OPS-04 | `make models` (online, once) saves `all-MiniLM-L6-v2` to `./models/all-MiniLM-L6-v2` and trains `category_clf-v1` from the seed-7 synthetic train split; writes SHA-256 of every model file to `models/manifest.json`, checked at API startup | FR-503, FR-402 | P0 |
| TR-OPS-05 | `make seed` creates CPSEs (CPSE-A, CPSE-B, CPSE-C), demo users per role **including a CHECKER for each CPSE (meera A maker, arjun B checker, kavya C checker)** so the consent scene works, templates, and the seed-7 synthetic dataset | 14.6, FR-1501 | P0 |
| TR-OPS-06 | Image size budget: API ≤ 2.5 GB [T] (CPU torch), web ≤ 60 MB, DB stock image | C-01 | P1 |
| TR-OPS-07 | `make snapshot` = `pg_dump -Fc` of a database with a finished run and issued CNMCs; `make restore` = `pg_restore --clean`; snapshot file kept on two laptops and a USB stick | 15.2 | P0 |
| TR-OPS-08 | Windows hosts: WSL2 memory set to ≥ 10 GB in `.wslconfig`; the repo lives inside the WSL filesystem (bind-mount performance) | NFR-06, R-08 | P0 |
| TR-OPS-09 | Observability: structlog JSON to stdout; `X-Request-ID` generated by nginx and logged by the API; `/api/v1/health` returns DB status, model hashes, template versions, guard status, git commit | NFR-11 | P0 |
| TR-OPS-10 | Feature flags only through env (`EMBEDDINGS_ENABLED`, `LLM_ENABLED`, `AUTO_ELIGIBLE_ENABLED`, `EGRESS_GUARD_ENABLED`); the footer shows any flag that weakens the demo story (guard off, dense off) | 6.5, R-16 | P0 |

**Air-gap demo procedure (PRD 15.1, 4:25):** footer shows `Air-gapped · blocked attempts: 0` → `docker network inspect specid_backend --format '{{.Internal}}'` prints `true` → switch Wi-Fi off → run search-before-create → counter still 0.

---

## 13. Testing requirements

| ID | Level | Scope and technique | Gate | PRD |
|---|---|---|---|---|
| TR-TST-01 | Unit | Every `core/` function; table-driven; ≥ 70% line coverage on `core/` | CI | NFR-08 |
| TR-TST-02 | Golden | YAML files under `tests/golden/<category>.yaml` (format in Appendix K); ≥ 10 pairs per P0 template, ≥ 60 in total by T+30; each case asserts verdict, optional route, optional decisive attribute | CI | 13.2 |
| TR-TST-03 | Property | hypothesis strategies generating specs from template value domains: T-P1 veto, T-P2 no conflict in clusters, T-P3 symmetry, T-P4 idempotent normaliser, T-P5 short text length; `max_examples=500` in CI, 5,000 nightly | CI | 13.3 |
| TR-TST-04 | Signature features | T-S1 … T-S6 of the PRD, ported from PRD Appendix D | CI | 13.3 |
| TR-TST-05 | API contract | FastAPI `TestClient` against a Postgres service; one test per endpoint per role (allowed / forbidden) generated from the permission matrix | CI | FR-1301 |
| TR-TST-06 | Integration | CSV → run → clusters → approve (maker, then checker) → CNMC → crosswalk → migration pack → search-before-create returns `USE_EXISTING` | CI (≤ 2k records) | G1 |
| TR-TST-07 | Determinism | Generator: same seed → identical SHA-256 of every file. Run: same seed + config → identical sorted `(rec_a, rec_b, verdict, route)` list | CI | NFR-02 |
| TR-TST-08 | Evaluation maths | Wilson interval and rule-of-three against hand-computed values; baseline tuning on a 12-pair fixture gives the PRD T-S1 counts | CI | FR-1104 |
| TR-TST-09 | Audit | Tamper test: update one `audit_event.after` with raw SQL → `/audit/verify` reports that id | CI | FR-1302 |
| TR-TST-10 | Air-gap | T-S5 unit test; plus `make offline-check`: start the stack, run the demo API script, assert `/system/airgap.blocked_egress_attempts == 0` | pre-demo | FR-1461–1463 |
| TR-TST-11 | Performance | `scripts/bench_run.py` times each stage on seed 7 and prints the TR-PRF table; `scripts/bench_search.py` sends 500 queries and prints p50 / p95 | G4 gate | NFR-01 |
| TR-TST-12 | Architecture | Test that parses imports in `app/core/**` and fails if any import `app.services`, `app.api`, `app.db`, `sqlalchemy`, `psycopg`, `fastapi` | CI | TR-ARC-10 |
| TR-TST-13 | Claims | Text search over `frontend/src`, report templates and `docs/` for "first", "only", "best", "novel algorithm", "beats" | pre-demo | NFR-14 |
| TR-TST-14 | Frontend | vitest for `EvidenceCard`, `VerdictBadge`, formatters; Playwright demo path (P2) | CI | 13.1 |
| TR-TST-15 | Consent | T-S7: 3-CPSE cluster stays `AWAITING_CONSENT` until the CPSE-C steward answers; decline excludes CPSE-C records; a user of a non-participating CPSE gets 403; `consent_mode=NONE` issues immediately | CI | FR-1501–1504 |
| TR-TST-16 | Impact preview | T-S4/T-S8: unchanged template → zero transitions; promoting `design_standard` to core → the expected transitions and affected CNMCs; activation blocked while golden tests fail | CI | FR-1451–1452 |

**Test data rule:** tests use only generated synthetic data or hand-written strings. No CPSE data in fixtures.

---

## 14. Build pipeline (CI)

| ID | Requirement | Pri |
|---|---|---|
| TR-CI-01 | GitHub Actions on every push and pull request (Appendix G): backend lint (ruff, black --check), unit + golden + property + API tests against a `postgres:16-alpine` service, coverage gate on `core/`; frontend lint, vitest, build | P0 |
| TR-CI-02 | ML-dependent tests (embeddings, FAISS) are marked `@pytest.mark.ml` and run locally with `make test-ml`, because CI does not download models | P0 |
| TR-CI-03 | Each gate (PRD 14.3) is a git tag `gate-1` … `gate-6`; the demo is built from the `gate-6` tag | P0 |
| TR-CI-04 | Commit messages start with the requirement ID (`FR-602: …`, `TR-ALG-01: …`) | P0 |

---

## 15. Coding standards

- Python: ruff (rules E, F, I, B, UP), black (line length 100), mypy `--strict` on `app/core`. No `print` outside scripts.
- Pure core: no global mutable state except compiled regexes and constant tables.
- Every template-driven value (aliases, rule texts, value domains, UoM aliases, header synonyms) lives in versioned data files, not code.
- Errors: services raise typed exceptions (`NotFound`, `Forbidden`, `Conflict`, `Invalid`); one handler maps them to RFC 7807.
- TypeScript: `strict: true`; ESLint + Prettier; no `any` in API code.
- Naming: database `snake_case`; API JSON `snake_case`; TypeScript types generated, not renamed.
- Definition of done: PRD 14.8, plus "TR ID in the commit and a test named after it".

---

## 16. Technical risks

| ID | Risk | L / I | Mitigation | PRD link |
|---|---|---|---|---|
| TR-R1 | MiniLM embedding of 10k texts too slow on an older laptop | M / M | Stored embeddings; pre-computed snapshot; dense channel can be switched off without breaking the run (blocking + BM25 remain) | R-01, R-11 |
| TR-R2 | Docker Desktop / WSL2 memory pressure with torch loaded | M / M | `.wslconfig` ≥ 10 GB; one uvicorn worker; worker pool of 1 | R-08 |
| TR-R3 | `pair_decision` grows too large | M / M | TR-DAT-05; fallback in 7.3; demo on 3k records | R-11 |
| TR-R4 | ML classifier assigns a wrong category with high probability | M / M | Rules run first; ML only as fallback; `class_source` shown; wrong category cannot merge across categories | R-04 |
| TR-R5 | Hash-chain contention under concurrent writes | L / L | Advisory lock is per transaction; prototype write rate is low | — |
| TR-R6 | Swagger UI or fonts try to load from a CDN during the offline demo | M / L | TR-API-01, TR-UI-07; `make offline-check` | R-16 |
| TR-R7 | Lockfile drift between laptops | M / M | One lockfile, images built from it, `make doctor` prints versions | R-07 |
| TR-R8 | Internal network blocks something needed at runtime (for example time sync in containers) | L / M | Containers use host time; nothing else is needed at runtime | — |

---

## 17. Technical decisions

| ID | Decision | Rationale | PRD impact |
|---|---|---|---|
| TD-01 | One uvicorn worker + one-process `ProcessPoolExecutor` | Consistent in-process state, no Redis/Celery | none (refines 6.2) |
| TD-02 | FAISS `IndexFlatIP` (exact) instead of an approximate index | ≤ 50k vectors; exact search is fast enough and deterministic | none |
| TD-03 | Blocking key `(category, size_dn)` without pressure class | Keeps rating near-misses in the candidate set so the veto and Look-alike Guard act on them | Applied in PRD v0.5 (FR-501) |
| TD-04 | `bcrypt` package directly, not passlib | passlib is unmaintained and warns with bcrypt ≥ 4 | Applied in PRD v0.5 (6.3) |
| TD-05 | CPU-only torch; ML dependencies in a separate lockfile | Image size, CI speed, offline reliability | none |
| TD-06 | UUIDs generated in Python for bulk rows | Pairs can be ordered and referenced before insert | none |
| TD-07 | Evidence JSON omits `MISSING_BOTH` rows | Storage; the UI collapses them anyway | none |
| TD-08 | Swagger UI assets served locally (or docs disabled) | FastAPI's default docs page loads assets from a CDN | none |
| TD-09 | ML category classifier is a fallback after rules, never first | Deterministic behaviour on known phrasing; ML adds coverage without changing golden results | consistent with FR-402 |
| TD-10 | Consent is recorded per CPSE in its own table, not as extra review decisions | One row per (task, CPSE) lets the database enforce "each CPSE answers once" and keeps reasons for declines | PRD v0.5 FR-1501 |
| TD-11 | PRD Appendix C is copied verbatim to `tests/reference/specid_ref.py` (a test checks it equals the PRD block); `tests/reference/test_conformance.py` compares `core/` with it under an allowlist DEV-1 … DEV-5 (PRD C.1) | The reference opens sockets, so it stays out of `core/`; the allowlist makes every deviation visible | PRD C.1 |
| TD-12 | Golden and property tests are committed red, in their own commit, before any `core/` code; `git diff <that commit> -- tests/golden` must stay empty | Proof that no golden test was edited to pass | PRD 13.2 |
| TD-13 | `core.supply_attribute` only needs a non-empty source note; the 5-character minimum is the DB CHECK on `attribute_supply.source_note` plus a 422 in the SF-3 service | Appendix D passes `"x"`; keeps `core/` faithful to the reference | none |
| TD-14 | Hypothesis profiles: 500 examples in CI, 5,000 with `HYPOTHESIS_PROFILE=nightly` | CI time | none |
| TD-15 | mypy strict on `core/`; PyYAML stubs skipped through a per-module override for `yaml` only | `types-PyYAML` is not in the frozen lock | none |
| TD-16 | The audit hash canonicalises `ts` as ISO 8601 UTC with microseconds; failed logins commit `LOGIN_FAILED` before the 401; the JWT role is not trusted (user reloaded per request) | Chain recomputes in any DB time zone; disabled users lose access at once | none |

**Open technical questions**

| ID | Question | Owner |
|---|---|---|
| OQ-T1 | ~~Exact hardware of each team laptop — 10k or 3k records~~ **Resolved (DEC-09): 3k records, Docker default memory** | R1 |
| OQ-T2 | Does the venue allow an external screen + HDMI only, or also a second laptop on the same switch (offline LAN demo)? | R6 |
| OQ-T3 | Will CPSE sample files include long texts (SAP READ_TEXT) and procurement history? Affects FR-107 and the SAP preset | R1 via SPOC (PRD Q-12) |

---

## 18. Traceability

| PRD requirement group | TR IDs | Modules | Tests |
|---|---|---|---|
| FR-101–107 Ingestion, procurement | TR-MOD-20, 21; TR-SEC-09, 11; TR-API-07 | services/ingest, services/procurement | TR-TST-05, 06 |
| FR-201–205 Normalisation, UoM | TR-MOD-01, 02; TR-ALG-06 | core/normalise, core/units | TR-TST-01, 03 |
| FR-301–307 Extraction | TR-MOD-04 | core/extract | TR-TST-01, 02 |
| FR-401–405 Templates, classification | TR-MOD-03, 05; 4.3 | core/classify, core/templates | TR-TST-01, 02 |
| FR-501–507 Candidates and runs | TR-MOD-22, 23, 30; TR-ALG-01 | services/candidates, harmonise, jobs | TR-TST-06, 07, 11 |
| FR-601–612 Equivalence engine | TR-MOD-06, 12, 13; TR-ALG-02, 05, 07 | core/decide, confidence, substitute | TR-TST-02, 03, 04 |
| FR-701–703 Clustering | TR-MOD-07; TR-ALG-03 | core/cluster | TR-TST-03 |
| FR-801–807 Review | TR-MOD-24; TR-SEC-04; TR-UI-05 | services/review | TR-TST-05, 06 |
| FR-901–907 Registry, migration | TR-MOD-08, 09, 25, 26, 31; TR-ALG-08 | core/cnmc, services/registry, migration, exports | TR-TST-06 |
| FR-1001–1005 Search, integration | TR-MOD-27; TR-API-01, 08; Appendix H | services/search, ingest (SAP preset) | TR-TST-06, 11 |
| FR-1101–1107 Evaluation | TR-ALG-04, 05 | eval/* | TR-TST-07, 08 |
| FR-1201–1203 Dashboard | TR-MOD-28; Appendix J | services/dashboard | TR-TST-05 |
| FR-1301–1304 Security, audit | TR-SEC-01–13; TR-ALG-09 | security/*, services/audit | TR-TST-05, 09 |
| FR-1401–1491 Signature features | TR-MOD-10, 11; TR-ALG-04, 10; TR-SEC-05; TR-UI-04 | core/radar, baselines, security/egress | TR-TST-04, 10, 16 |
| FR-1501–1513 Consent and change notices | TR-MOD-32, 33; TR-ALG-11 | services/consent, services/notices | TR-TST-15 |
| NFR-01–14 | TR-PRF-01–11; TR-OPS-*; TR-TST-13 | — | TR-TST-11, 13 |

---

## 19. Production path (from prototype to an industry deployment)

The prototype is deliberately single-laptop. This section lists what a pilot or production deployment needs; none of it is in the 36-hour scope.

| Area | Prototype | Production requirement |
|---|---|---|
| Identity | local users, JWT | SSO with the CPSE's identity provider (OIDC/SAML, e.g. Keycloak or the CPSE directory); MFA for ADMIN and CHECKER; joiner-mover-leaver process |
| Availability | one container each | PostgreSQL with streaming replica and point-in-time recovery; API behind a load balancer with ≥ 2 instances; job workers separated (Celery/Prefect) with a durable queue |
| Backup and DR | `pg_dump` snapshot | daily base backup + WAL archiving; tested restore; documented RPO/RTO agreed with the registry owner |
| Scale | ~3k demo records (≤ 10k by parameter), FAISS in memory | 10⁶+ records: pgvector or OpenSearch, partitioned `pair_decision`, incremental runs per CPSE upload |
| Security assurance | internal checks | independent VAPT before go-live; secure-SDLC (dependency scanning, SBOM, signed images); secrets in a vault; follow CERT-In directions for incident reporting and log retention applicable to the hosting organisation |
| Privacy | synthetic only | user accounts are personal data: apply the Digital Personal Data Protection Act, 2023 obligations (notice, purpose limitation, retention); procurement data stays CPSE-scoped (optional RLS, doc 05 §5.4) |
| Accessibility | WCAG 2.1 AA target | align with the Government of India web guidelines (GIGW) if the registry is exposed as a government web application |
| Hosting | laptop, air-gapped | on-premises at a CPSE or a government-approved cloud, as decided by MoPNG / the registry owner; network isolation retained |
| ERP integration | files + REST | per-CPSE adapters (SAP extraction, write-back of CNMC through the CPSE's master-data change process), certified with each SAP team |
| Governance | consent per CPSE, versioned rules | a registry council (CPSE material stewards + central owner), SLA for consent responses, dispute escalation, published rule-change calendar |
| Operations | logs to stdout | metrics and alerting (run failures, consent backlog, override rates, drift), on-call ownership, quarterly recalibration on reviewer labels |
| Evidence | L2 synthetic | L3 pilot: 500–1,000 expert-labelled pairs per category group, inter-annotator agreement, false-merge bound reported per category |

# APPENDICES

## Appendix A: `docker-compose.yml`

```yaml
name: specid

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: specid
      POSTGRES_PASSWORD: ${DB_PASSWORD:?set DB_PASSWORD in .env}
      POSTGRES_DB: specid
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U specid -d specid"]
      interval: 5s
      timeout: 3s
      retries: 20
    mem_limit: 1g                          # DEC-09
    networks: [backend]

  api:
    build: ./backend
    env_file: .env
    environment:
      DATABASE_URL: postgresql+psycopg://specid:${DB_PASSWORD}@db:5432/specid
      DB_HOST: db
      MODEL_DIR: /models
      TEMPLATE_DIR: /app/templates
      GIT_COMMIT: ${GIT_COMMIT:-unknown}   # exported by `make up` (DEC-02)
    mem_limit: 4g                          # DEC-09: Docker at default memory
    volumes:
      - ./models:/models:ro
      - ./templates:/app/templates:ro
      - ./data:/app/data
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3)"]
      interval: 10s
      timeout: 5s
      retries: 30
    networks: [backend]

  web:
    build: ./frontend
    ports:
      - "127.0.0.1:8080:80"
    depends_on:
      api:
        condition: service_healthy
    networks: [backend, frontend]

  ollama:                      # P2, off unless: docker compose --profile llm up
    image: ollama/ollama
    profiles: [llm]
    volumes:
      - ./models/ollama:/root/.ollama
    networks: [backend]

networks:
  backend:
    internal: true             # no route to the internet (FR-1462)
  frontend: {}

volumes:
  pgdata: {}
```

**`frontend/nginx.conf`**
```nginx
server {
  listen 80;
  client_max_body_size 50m;
  add_header X-Content-Type-Options nosniff always;
  add_header X-Frame-Options DENY always;
  add_header Referrer-Policy no-referrer always;
  add_header Content-Security-Policy "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'" always;

  root /usr/share/nginx/html;

  location /api/ {
    proxy_pass http://api:8000;
    proxy_set_header X-Request-ID $request_id;
    proxy_set_header Host $host;
    proxy_read_timeout 120s;
  }
  location / {
    try_files $uri /index.html;
  }
}
```

**`backend/Dockerfile`**
```dockerfile
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 SENTENCE_TRANSFORMERS_HOME=/models
WORKDIR /app
COPY requirements.lock requirements-ml.lock ./
RUN pip install --no-cache-dir -r requirements.lock \
 && pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements-ml.lock
COPY app ./app
COPY alembic.ini ./
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

**`frontend/Dockerfile`**
```dockerfile
FROM node:20-alpine AS build
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/dist /usr/share/nginx/html
```

## Appendix B: `Makefile` targets

| Target | Does |
|---|---|
| `make models` | (online, once) download MiniLM to `./models`, train `category_clf-v1`, write `models/manifest.json` |
| `make up` / `make down` | `GIT_COMMIT=$(git rev-parse --short HEAD) docker compose up -d --build` / `docker compose down` |
| `make seed` | CPSEs, demo users, templates, seed-7 synthetic data |
| `make demo-data` (`SEED=7` default) | regenerate `data/synthetic/seed-<n>` files and manifest (`n_entities` 1,200 → about 3k records) |
| `make test` / `make test-ml` | CI test set via `backend/scripts/ci_local.sh` (ruff, black, pytest on a throwaway Postgres; never against the stack's DB) / ML-dependent tests |
| `make eval SEED=7` | evaluation run + Markdown/JSON report |
| `make bench` | TR-TST-11 scripts |
| `make offline-check` | TR-TST-10 |
| `make snapshot` / `make restore` | TR-OPS-07 |
| `make doctor` | print tool, library, model and template versions; check `.env` |
| `make lint` | ruff, black --check, mypy core, eslint |
| `make purge-real` | delete non-synthetic batches (7.4) |

## Appendix C: `.env.example`

```dotenv
# local demo only - never commit a real .env
DB_PASSWORD=change-me-locally
JWT_SECRET=replace-with-at-least-32-random-bytes-0000000000
JWT_EXPIRE_MIN=480
OFFLINE=true
EGRESS_GUARD_ENABLED=true
EMBEDDINGS_ENABLED=true
CONSENT_MODE=ALL_PARTICIPANTS
LLM_ENABLED=false
AUTO_ELIGIBLE_ENABLED=false
CLASSIFIER_THRESHOLD=0.80
SEED_DEMO_USERS=true
DEMO_PASSWORD=change-me-too
LOG_LEVEL=INFO
CORS_ORIGIN=http://127.0.0.1:8080
```

## Appendix D: Settings model (`app/settings.py`, outline)

```python
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    db_host: str = "db"
    jwt_secret: str = Field(min_length=32)
    jwt_expire_min: int = 480
    offline: bool = True
    egress_guard_enabled: bool = True
    embeddings_enabled: bool = True
    consent_mode: Literal["ALL_PARTICIPANTS", "NONE"] = "ALL_PARTICIPANTS"   # DEC-01
    git_commit: str = "unknown"                                              # DEC-02
    llm_enabled: bool = False
    auto_eligible_enabled: bool = False
    classifier_threshold: float = 0.80
    model_dir: str = "/models"
    template_dir: str = "/app/templates"
    cors_origin: str = "http://127.0.0.1:8080"
    log_level: str = "INFO"
```

## Appendix E: Run configuration defaults
See 7.2 `run.config`. Defaults live in `settings.RunDefaults`; the API merges request options over them and stores the merged result.

## Appendix F: Key Pydantic schemas

```python
from pydantic import BaseModel, Field
from typing import Literal, Any

class EvidenceRowOut(BaseModel):
    attr: str; level: Literal["core", "ext"]; a: Any; b: Any
    status: Literal["MATCH", "PARTIAL", "CONFLICT", "MISSING_ONE", "MISSING_BOTH"]
    rule: str; rule_text: str; note_a: str | None = None; note_b: str | None = None

class DecisionOut(BaseModel):
    verdict: Literal["IDENTICAL", "EQUIVALENT", "NOT_EQUIVALENT", "INSUFFICIENT_DATA"]
    route: Literal["AUTO_ELIGIBLE", "REVIEW", "NONE"]
    reasons: list[str]; evidence: list[EvidenceRowOut]
    confidence: float | None; confidence_label: Literal["heuristic", "calibrated"] = "heuristic"
    missing_both_count: int = 0

class RunCreate(BaseModel):
    batch_ids: list[str] = Field(min_length=1)
    mode: Literal["CROSS_CPSE", "WITHIN_CPSE", "BOTH"] = "CROSS_CPSE"
    options: dict[str, Any] = {}

class SearchRequest(BaseModel):
    text: str = Field(min_length=3, max_length=1000)
    uom: str | None = None; mpn: str | None = None; manufacturer: str | None = None; cpse: str | None = None

class SearchCandidate(BaseModel):
    cnmc: str; short_desc_40: str | None; verdict: str; reasons: list[str]; evidence: list[EvidenceRowOut]

class SearchResponse(BaseModel):
    query: dict[str, Any]; would_create_duplicate: bool
    recommended_action: Literal["USE_EXISTING", "SUPPLY_ATTRIBUTES", "CREATE_NEW_ALLOWED"]
    best_match: str | None; attributes_to_supply: list[str] = []; candidates: list[SearchCandidate]
    is_synthetic: bool

class ReviewRequest(BaseModel):
    decision: Literal["APPROVE", "REJECT", "SPLIT", "NEEDS_INFO"]
    comment: str | None = Field(default=None, max_length=2000)
    split_groups: list[list[str]] | None = None

class MigrationRow(BaseModel):
    cpse: str; legacy_code: str; legacy_short_text: str; cnmc: str; cnmc_short_desc_40: str | None
    relation: Literal["IDENTICAL", "EQUIVALENT"]; survivor: bool
    recommended_action: Literal["RETAIN", "BLOCK_FOR_NEW_PROCUREMENT", "PHASE_OUT_WHEN_STOCK_ZERO"]
    uom: str | None; uom_factor: float | None; stock_known: bool; note: str | None = None

class DashboardSummary(BaseModel):
    run_id: str; is_synthetic: bool; computed_at: str
    records_per_cpse: dict[str, int]; redundant_within_cpse: dict[str, int]
    cross_cpse_clusters: int; verdict_mix: dict[str, int]; quality_score: dict[str, float]
    review_backlog: int; top_clusters: list[dict[str, Any]]
```

**F.3 Review state machine**

| From | Actor | Action | To | Notes |
|---|---|---|---|---|
| OPEN | MAKER | APPROVE / REJECT / SPLIT / NEEDS_INFO | MADE | proposal stored |
| MADE | CHECKER (≠ maker) | confirm | DONE or AWAITING_CONSENT | APPROVE → issuance if every participating CPSE has consented, else AWAITING_CONSENT; REJECT → cannot-link pairs (P1) |
| AWAITING_CONSENT | CHECKER of a missing CPSE | consent / decline | AWAITING_CONSENT or DONE | DONE when the last CPSE answers; issuance for consenting CPSEs (TR-ALG-11) |
| MADE | CHECKER (≠ maker) | overturn | OPEN | comment required |
| MADE | same user as maker | any | — | HTTP 403 |

## Appendix G: GitHub Actions workflow (`.github/workflows/ci.yml`)

```yaml
name: ci
on: [push, pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: specid
          POSTGRES_PASSWORD: specid
          POSTGRES_DB: specid
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U specid"
          --health-interval 5s --health-timeout 3s --health-retries 20
    env:
      DATABASE_URL: postgresql+psycopg://specid:specid@localhost:5432/specid
      DB_HOST: localhost
      JWT_SECRET: ci-only-secret-0123456789abcdef0123456789
      EMBEDDINGS_ENABLED: "false"
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.lock -r requirements-dev.txt
      - run: ruff check . && black --check .
      - run: pytest -m "not ml" --cov=app/core --cov-fail-under=70

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: npm ci
      - run: npm run lint
      - run: npm test -- --run
      - run: npm run build
```

## Appendix H: Column mapping presets

**H.1 Header synonyms (generic CSV)**

| Target field | Header synonyms (case-insensitive, punctuation ignored) |
|---|---|
| `legacy_code` | material code, material no, item code, mat code, code, matnr |
| `short_text` | short text, description, material description, item description, maktx |
| `long_text` | long text, long description, specification, purchase text |
| `uom` | uom, unit, base unit, meins |
| `mat_group` | material group, category, matkl |
| `manufacturer` | manufacturer, make, mfr, mfrnr |
| `mpn` | part number, mpn, mfr part no, mfrpn |
| `plant` | plant, werks, location |
| `criticality` | criticality, critical, abc |
| `annual_value` | annual value, consumption value, annual spend |

**H.2 SAP material-master preset (FR-1005)**. *Confirm table and field names with each CPSE's SAP team.*

| SAP source | SpecID field |
|---|---|
| MARA-MATNR | `legacy_code` |
| MAKT-MAKTX (language of the extract) | `short_text` |
| Long text from a READ_TEXT export (text object MATERIAL, purchase order text or basic data text) | `long_text` |
| MARA-MEINS | `uom` |
| MARA-MATKL | `mat_group` |
| MARA-MFRNR | `manufacturer` |
| MARA-MFRPN | `mpn` |
| MARC-WERKS | `plant` |

**H.3 Procurement-history file (FR-107)**: `legacy_code, po_date (ISO 8601), qty, uom, unit_price, currency, vendor, plant`. Vendor is hashed at ingest (TR-MOD-21).

## Appendix I: UoM alias table v1 (FR-205)

| Canonical | Aliases | Note |
|---|---|---|
| `EA` | EA, NO, NOS, NO., PC, PCS, EACH, NUMBER, UNIT | count |
| `M` | M, MTR, MTRS, METRE, METER, METRES, METERS | length |
| `KG` | KG, KGS, KILOGRAM | mass |
| `L` | L, LTR, LITRE, LITER | volume |
| `SET` | SET, SETS | count of sets |
| `PR` | PR, PAIR | pairs |
| *(ambiguous)* | MT | metre or metric tonne → flagged, never mapped |

Versioned in `templates/uom.yaml`; extensions go through the admin dictionary workflow (FR-203).

## Appendix J: Dashboard SQL (FR-1201, FR-1203)

Parameters use SQLAlchemy `text()` binding (`:name`).

```sql
-- J.1 records per CPSE in a run
SELECT c.code, count(*) AS records
FROM material_record m
JOIN cpse c ON c.id = m.cpse_id
WHERE m.batch_id = ANY(:batch_ids)
GROUP BY c.code
ORDER BY c.code;

-- J.2 redundant records within each CPSE: for every cluster, members of one CPSE minus one
SELECT c.code, sum(greatest(t.n - 1, 0)) AS redundant_records
FROM (
  SELECT cl.id, m.cpse_id, count(*) AS n
  FROM cluster cl
  JOIN cluster_member cm ON cm.cluster_id = cl.id
  JOIN material_record m ON m.id = cm.record_id
  WHERE cl.run_id = :run_id AND cl.status IN ('PROPOSED', 'APPROVED')
  GROUP BY cl.id, m.cpse_id
) t
JOIN cpse c ON c.id = t.cpse_id
GROUP BY c.code;

-- J.3 clusters spanning two or more CPSEs
SELECT count(*) AS cross_cpse_clusters
FROM (
  SELECT cl.id
  FROM cluster cl
  JOIN cluster_member cm ON cm.cluster_id = cl.id
  JOIN material_record m ON m.id = cm.record_id
  WHERE cl.run_id = :run_id AND cl.status IN ('PROPOSED', 'APPROVED')
  GROUP BY cl.id
  HAVING count(DISTINCT m.cpse_id) >= 2
) x;

-- J.4 demand aggregation across CPSEs (aggregates only, FR-104)
WITH q AS (
  SELECT record_id, sum(qty) AS qty_12m
  FROM procurement_line
  WHERE po_date > (SELECT max(po_date) FROM procurement_line) - interval '12 months'
  GROUP BY record_id
)
SELECT x.cnmc,
       k.short_desc_40,
       count(DISTINCT x.cpse_id) AS cpses,
       sum(coalesce(m.annual_value, 0)) AS combined_annual_value,
       sum(q.qty_12m * x.uom_factor) AS combined_qty_base_uom,
       bool_or(q.qty_12m IS NOT NULL AND x.uom_factor IS NULL) AS qty_incomplete
FROM crosswalk x
JOIN cnmc k ON k.cnmc = x.cnmc AND k.status = 'ACTIVE'
JOIN material_record m ON m.id = x.record_id
LEFT JOIN q ON q.record_id = x.record_id
WHERE x.status = 'ACTIVE'
GROUP BY x.cnmc, k.short_desc_40
HAVING count(DISTINCT x.cpse_id) >= :min_cpses
ORDER BY combined_annual_value DESC
LIMIT :limit;
```
Redundant share per CPSE = J.2 / J.1. Labels on S0 say "proposed + approved clusters of run *X*" so a proposed duplicate is never presented as a confirmed one.

## Appendix K: Golden test file format

```yaml
# tests/golden/valve.yaml
template: valve
cases:
  - a: "VALVE GATE 4IN CL150 A216 WCB FLGD RF"
    b: "VALVE GATE 4IN CL300 A216 WCB FLGD RF"
    expected_verdict: NOT_EQUIVALENT
    decisive: pressure_class
    note: near-miss on class
  - a: "VALVE GATE 4IN CL150 A216 WCB FLGD RF"
    b: "GV 100NB 150# WCB RF FLANGED"
    expected_verdict: EQUIVALENT
    expected_route: REVIEW          # critical class
    note: unit and abbreviation conversion
  - a: "VALVE GATE 4IN CL150 WCB FLANGED"
    b: "VALVE GATE 4IN CL150 WCB FLANGED RF"
    expected_verdict: INSUFFICIENT_DATA
    note: face missing on one side
```
Coverage per template (PRD 13.2): ≥ 3 near-miss pairs, ≥ 3 equivalent pairs with different wording or units, ≥ 2 `INSUFFICIENT_DATA`, ≥ 1 flagged pair.

## Appendix L: Repository layout (extends PRD 14.5)

```
specid/
├─ docker-compose.yml · Makefile · .env.example · .gitattributes (LF) · README.md · CLAUDE.md · PROGRESS.md
├─ backend/
│  ├─ Dockerfile · requirements*.in (pip-compile sources) · requirements.lock · requirements-ml.lock · requirements-dev.txt · pyproject.toml (ruff/black/pytest/mypy) · alembic.ini
│  ├─ app/ (main.py settings.py security/ api/ core/ services/ eval/ db/ schemas/)
│  ├─ app/cli.py (`python -m app.cli generate | decide --file DIR | decide --a --b | extract --text`)
│  ├─ scripts/ (ci_local.sh fetch_models.py train_classifier.py bench_run.py bench_search.py offline_check.py)
│  └─ tests/ (unit/ golden/ property/ reference/ api/ integration/ eval/ arch/)
├─ frontend/ (Dockerfile nginx.conf src/{pages,components,api,hooks})
├─ templates/ (valve.yaml pipe.yaml flange.yaml fastener.yaml motor.yaml gasket.yaml uom.yaml dictionary.yaml)
├─ models/ (git-ignored; manifest.json committed)
├─ data/ (synthetic/ generated; fixtures/)
├─ impdocs/ (source documents; never edited by the build)
├─ docs/ (DECISIONS.md demo-script.md)
└─ .github/workflows/ci.yml
```

*End of TRD.*
