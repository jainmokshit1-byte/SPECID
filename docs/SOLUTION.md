# SpecID: the final solution (v2)

PS SIH26099 · "One Nation – One Material Code" · proposal dated 4 Oct 2026

This document is the **target product**: what we build, what users see, why it stands out, and how it is built. It keeps everything already built (engine, database, login, audit) and the specs in `impdocs/`, and changes three things: the **build order** (working slices first), the **role of AI** (visible and verified, not optional), and the **value story** (money, stock and duplicate prevention on screen). Where this differs from `impdocs/`, section 12 lists it.

---

## 1. The one-line idea

> **AI reads every material description, engineering rules check what the AI read, people approve, and every CPSE involved agrees. Then one national code is issued, linked to every old code.**

Our promise to a judge: **"Same specification → same code. Different specification → never the same code, no matter how similar the words look."**

---

## 2. The problem in one paragraph

CPSEs (ONGC, NTPC, SAIL, BHEL, …) buy the same valves, pipes, flanges, bolts and motors, but each names and codes them differently, and often codes the same item twice internally. So nobody sees common demand, each keeps its own spare stock, and data is dirty. The PS asks for an AI system that finds which items are the same, gives each real item one **Common National Material Code (CNMC)**, keeps a link to every old code, and lets people approve. The trap: `VALVE 4" CL150` and `VALVE 4" CL300` look 95% alike in text but are different items (the second takes double the pressure). Merging them is a safety risk.

---

## 3. Design principles (the rules we never break)

| # | Principle | What it means in practice |
|---|---|---|
| P1 | **Identity = specification, not words** | Two records match only if their key engineering attributes (size, pressure class, material, …) match |
| P2 | **AI proposes, rules verify, people decide** | AI reads text, suggests attributes, finds candidates. It can never override a rule veto or approve anything |
| P3 | **Never guess** | If a key attribute is unknown, the answer is "can't tell yet", plus exactly what to ask for and from whom |
| P4 | **Every value shows where it came from** | Each attribute is tagged RULE, AI-VERIFIED or PERSON (with a source note), and highlights the words in the original text it came from |
| P5 | **Every CPSE controls its own codes** | A national code that absorbs a CPSE's codes needs that CPSE's consent |
| P6 | **Nothing leaves the building** | Runs fully offline; AI models run locally; live counter of blocked outbound connections |
| P7 | **Honest numbers** | Every number comes from a run, is labelled SYNTHETIC or REAL-TEXT, and says what it does not mean |

---

## 4. The ten pillars (what makes the product)

All numbers and rupee amounts in the "user sees" examples are **illustrative only**; the real screens show numbers from runs. Status words below are honest. **"Not found"** = not found in the 41 public SIH26099 repos scanned on 3 Oct 2026 (Competitive Review). **"Parity"** = strong teams already have it; we build it well but never call it unique. **"Re-check"** = not part of that scan; verify before claiming.

### Pillar 1 · Spec Fingerprint ("Material DNA")
- **User sees:** every record turned into a clean spec card: `GATE · DN100 · CL150 · A216-WCB · FLANGED-RF`. Three differently worded records from three CPSEs show the **same fingerprint**, side by side.
- **Why:** this is the PS's "standardised description and technical attributes", and it makes "same item" visible to a non-engineer in one glance.
- **Status:** core already built (extractors, units, short/long description). Parity in idea; strong in execution.

### Pillar 2 · Verified AI Reader (the visible AI)
- **User sees:** a run report like "Rules read 61% of attributes, AI read another 18% (all verified), 21% still need a person". In the evidence card, an AI-read value has an **AI-VERIFIED** badge and the source words highlighted in the original text.
- **How it works (4 layers, cheapest first):**
  1. **Rules** (built): regex extractors + unit tables.
  2. **Typo-tolerant dictionary** (new, rules): fixes `LFANGE`, `PIEP`, `CLSAS`, `FLAT FACE`. Our measurement on seed-7: about half of the "can't tell" gaps are values that *are in the text* but the rules miss.
  3. **ML classifier** (planned): guesses the category when the text has no category word (`25NB 300# WCB BW` is a valve). Abstains when unsure.
  4. **Local LLM** (new, offline, small open model): reads only what layers 1–3 could not, returns attribute values **plus the exact text span** each came from.
- **The guardrail (why it is safe):** an AI value is accepted only if (a) the span really exists in the record's text, (b) the value is in the template's allowed list, (c) the rule parser, run on that span alone, gives the same value. Otherwise it is dropped and the attribute stays unknown. The AI **never sees the other record and never gives a verdict**; `decide()` stays the same deterministic rule engine.
- **Why:** answers "where is the AI?" and fixes our biggest weakness (58% of true matches are "can't tell" on seed-7) without risking a false merge.
- **Status:** grounded, rule-verified LLM extraction: **re-check** (not in the scan's patterns). Hosted-LLM use was found in 6 repos; ours is local and verified.

### Pillar 3 · Safety Veto + Look-alike Guard
- **User sees:** a screen of pairs that **look alike** in text (similarity ≥ 0.85) but are different items, each with the one attribute that differs, highlighted (`CL150` vs `CL300`).
- **Why:** this is the safety story. A text-only matcher would merge these.
- **Status:** engine built (veto, radar). Screen to build. **Parity.**

### Pillar 4 · Ask, Don't Guess
- **User sees:** for a "can't tell" pair, a card: "Missing: end connection face of CPSE-B's record B0000412. Ask CPSE-B." The question lands in **CPSE-B's inbox**; their steward answers with a source note ("datasheet DS-114 p.2"); the pair is re-decided instantly.
- **Why:** the other half of the "can't tell" gap is information that is simply not in the text. No AI can (or should) invent it. This turns "can't tell" into a workflow, not a dead end.
- **Status:** table `attribute_supply` exists. Asking-and-re-deciding is **parity** (one repo); routing the question to the owning CPSE's inbox is **re-check**.

### Pillar 5 · Federated Consent + Change Notices
- **User sees:** a 3-CPSE cluster is approved by a maker and a checker, then shows **"waiting for CPSE-C consent"**. CPSE-C's steward consents, and only then is the CNMC issued. A decline keeps CPSE-C's code out, with the reason on the dashboard. Each affected CPSE gets a **change notice** with its old codes, new codes and a migration file.
- **Why:** a national code changes several organisations' master data. This is what makes it a *national* registry and not one team's tool.
- **Status:** consent and change notices: **not found** in the 41 repos. Our lead differentiator. Tables exist.

### Pillar 6 · Savings & Stock-Sharing Engine
- **User sees** for each CNMC, from procurement history and stock:
  - **Price spread:** "CPSE-A pays ₹18,400, CPSE-B ₹23,100, CPSE-C ₹21,000 for the same valve."
  - **Pooled demand:** "312 units/year across 3 CPSEs. At the lowest price paid, the gap is ₹X lakh." (shown as a gap, not as a promised saving)
  - **Stock sharing:** "CPSE-B plans to buy 20; CPSE-A holds 55 idle. Transfer before buying."
- **Why:** the PS's expected impact is mostly money (demand aggregation, inventory, procurement cost). This puts it on screen in rupees.
- **Status:** pooled demand and surplus transfer exist in some repos (**parity**); price-spread per national code with honest gap wording: **re-check**. Needs a small schema addition (stock quantity).

### Pillar 7 · Duplicate Firewall (SAP/ERP integration)
- **User sees:** a mock **SAP "Create Material"** screen. As a CPSE user types `GATE VLV 4IN 150# WCB`, a warning appears: "This already exists as NMC-…, used by 3 CPSEs. Use it." Behind it, a REST API with API keys and OpenAPI spec, which a real SAP system calls the same way.
- **Plus:** SAP-field import preset (MATNR, MAKTX, MEINS, MATKL), SAP-style crosswalk export and a per-CPSE **migration pack** (keep / block for new buying / phase out when stock is zero).
- **Why:** cleaning old duplicates is half the job; stopping new ones is the other half. This answers "SAP/ERP integration" with something you can see working.
- **Status:** search-before-create and SAP-style files are **parity**. The visible create-screen plug-in is strong in a demo.

### Pillar 8 · Glass-Box Proof
- **User sees** an Evaluation page:
  - Results on our **synthetic** set (labelled SYNTHETIC): correct merges, wrong merges (*k* of *n*, with a 95% upper bound), "can't tell" rate.
  - Two simple text baselines on the **same pairs**, so the gain is visible.
  - A **real-text test**: a small set of real public material descriptions (for example from public tender documents), labelled by hand by someone who did not write the rules. Results shown separately as REAL-TEXT.
  - A plain "what these numbers do not mean" panel.
- **Why:** almost every team reports numbers on data they generated themselves. A real-text test is a credibility jump.
- **Status:** baselines and synthetic P/R are **parity**; the statistical bound was **not found**; a real-text test is **re-check**.

### Pillar 9 · Governed Rulebook (impact preview)
- **User sees:** an admin drafts a rule change ("make design standard a key attribute for valves") and sees before activating: "40 past decisions change, 3 national codes in 2 CPSEs affected." Activation stays blocked until all golden tests pass.
- **Status:** `impact_preview()` already exists in the engine. **Not found** in the 41 repos.

### Pillar 10 · Material Master Health Score
- **User sees:** a score per CPSE (completeness of key attributes, internal duplicate rate, unit errors, missing makers), with a drill-down to the worst records and a trend after each run.
- **Why:** gives each CPSE's leadership one number to improve; drives adoption.
- **Status:** data-quality reports are common (**parity**); a cross-CPSE scorecard is **re-check**.

**Where we are different, in one sentence for the stage:** *"Others match text. We govern a national registry: verified AI reading, every CPSE consenting to its own codes, rule changes previewed before they happen, and duplicates stopped at creation, all offline."*

---

## 5. Users and what each one does

| Role (demo user) | Who in real life | Main jobs | Home screen |
|---|---|---|---|
| **Maker** (meera, CPSE-A) | Material master data steward | Upload extracts, start runs, review clusters, propose national codes, answer questions | Review queue |
| **Checker** (arjun, CPSE-B) | Senior steward of another CPSE | Second check of proposals; cannot check own proposal | Review queue (to check) |
| **CPSE steward** (kavya, CPSE-C) | Steward of a participating CPSE | Consent or decline, answer attribute questions, read change notices, download migration files | CPSE inbox |
| **Admin** (admin) | National registry cell | Users, rulebook, impact preview, settings | Dashboard |
| **Procurement head / leadership** (auditor login, read-only) | Procurement or management | Dashboard, savings, stock sharing, health scores | Dashboard |
| **Auditor** (auditor) | Internal audit / vigilance | Audit log, verify chain | Audit |
| **ERP integration** (erp) | SAP team | API keys, search-before-create, exports | API / Search |

### The main journey (what happens to one valve)

1. **Upload:** each CPSE uploads its material master extract (CSV/Excel, or SAP field names auto-mapped). The system shows a quality report and health score.
2. **Run:** one click starts matching across CPSEs. Live progress: reading (rules → AI) → finding candidates → deciding → grouping.
3. **Results:** groups of records that are the same item ("clusters"), plus look-alikes that were blocked, plus "can't tell" pairs with the question to ask.
4. **Review:** the maker opens a cluster, sees the spec fingerprints and the evidence card, and proposes a national code.
5. **Check:** a checker from another CPSE confirms.
6. **Consent:** every CPSE in the cluster consents in its inbox.
7. **Issue:** the CNMC is issued with a standard description (40-char SAP short text + long text), class, HSN/UNSPSC, and a crosswalk row per old code.
8. **Migrate:** each CPSE downloads its migration pack and gets a change notice.
9. **Prevent:** next week, someone at CPSE-B tries to create the same valve in SAP. The firewall warns them.
10. **Save:** the dashboard shows the price spread, pooled demand and idle stock for that CNMC.

---

## 6. Screens (final list)

IDs follow `impdocs/` App Flow; **new** marks screens or panels added by this document.

| ID | Screen | Pillar |
|---|---|---|
| S0 | Dashboard: duplicates per CPSE, health scores, savings & stock-sharing panels (**new panels**), backlog | 6, 10 |
| S2 | Upload & column mapping (SAP preset) | 7 |
| S3 | Quality report + health score (**new score**) | 10 |
| S4 | Runs: list, new run, live console with "rules / AI / person" split (**new split**) | 2 |
| S5 | Review queue | 4 |
| S6 | Cluster review (hero screen): fingerprints, evidence card with source highlighting and AI-VERIFIED badges (**new badges**), consent strip | 1, 2, 5 |
| S7 | Pair detail (evidence card) | 1, 2 |
| S8 | Registry (national codes), code detail with crosswalk, exports, migration pack | 7 |
| S9 | Search-before-create | 7 |
| S10 | Rulebook + impact preview | 9 |
| S11 | Evaluation: synthetic + real-text (**new section**), baselines, honesty panel | 8 |
| S12 | Audit log + verify | – |
| S13 | Look-alike Guard | 3 |
| S14 | SAP "Create Material" simulator | 7 |
| S15 | Pooling & stock sharing | 6 |
| S16 | Users | – |
| S17 | About & honesty | 8 |
| S18 | CPSE inbox: consents + questions (**questions are new**) | 4, 5 |
| S19 | Change notices | 5 |

---

## 7. The 5-minute demo

| Time | What we show | What we say |
|---|---|---|
| 0:00 | Dashboard: 3 CPSEs, duplicate counts, health scores, ₹ price spread on one valve | "Three CPSEs buy this valve under three codes, at three prices." |
| 0:30 | Run console: rules → AI → person split | "AI reads the messy text. Every AI value is checked against the words it came from." |
| 1:00 | Cluster review: three texts, one fingerprint; evidence card with a highlighted source span and `4 IN = DN100` | "Different words, same specification. Every value shows its source and its rule." |
| 1:30 | Look-alike Guard: CL150 vs CL300 blocked | "Text says same. Specification says no. A wrong merge here is a safety risk." |
| 1:50 | "Can't tell" pair → question to CPSE-B → answer → re-decided | "We don't guess. We ask the CPSE that owns the record." |
| 2:15 | Maker proposes → checker confirms → **waiting for CPSE-C** → CPSE-C consents → CNMC issued + migration pack | "A national code changes three organisations' data, so each one agrees." |
| 3:05 | SAP create screen: typing a duplicate → warning | "And new duplicates are stopped at the moment of creation." |
| 3:30 | Savings & stock sharing for the new CNMC | "Pooled demand, the price gap, and idle stock to transfer before buying." |
| 3:55 | Evaluation: synthetic + real-text, baselines, honesty panel | "These are reproducible numbers, labelled for what they are." |
| 4:30 | Wi-Fi off, footer counter 0 | "No CPSE data leaves the machine. The AI runs here too." |

Optional if time: rulebook impact preview (Pillar 9).

---

## 8. PS coverage

| PS expected-solution bullet | Answer | Pillars / screens |
|---|---|---|
| AI-based matching across CPSEs | Verified AI Reader + candidate search (keywords + meaning) + rule engine | 1, 2 · S4, S6 |
| Duplicate, near-duplicate, equivalent | Four verdicts; within-CPSE and cross-CPSE runs; look-alikes; substitutes (one-way, P1) | 1, 3 · S5, S6, S13 |
| Standardised descriptions and attributes | Canonical spec, 40-char SAP text, long text, unit/UoM harmonisation | 1 · S6, S8 |
| Intelligent classification | Rules → ML classifier → LLM; class path; UNSPSC + HSN | 2 · S3, S8 |
| Common National Material Code | CNMC with check digit, issued after approval + consent | 5 · S8 |
| Mapping old codes to the national code | Crosswalk row per legacy code with UoM factor | 7 · S8 |
| Legacy rationalisation & migration | Migration pack per CPSE; change notices | 5, 7 · S8, S19 |
| Validation & approval workflow | Review queue, maker–checker, consent, ask-don't-guess | 4, 5 · S5, S6, S18 |
| Dashboard & analytics | Duplicates, health, savings, stock sharing, backlog | 6, 10 · S0, S15 |
| Audit trail & governance | Hash-chained audit (built), rulebook preview, consent | 5, 9 · S10, S12 |
| SAP/ERP integration | SAP import preset, REST API + keys, create-screen firewall, SAP-style exports | 7 · S2, S9, S14 |

All 8 key capabilities and all expected-impact lines map to the table above. Impact numbers are shown from runs, never claimed as real-world results.

---

## 9. Developer view: architecture

```
Browser (React)  ──HTTP──▶  nginx (web)  ──▶  FastAPI (api)  ──▶  PostgreSQL 16 (db)
                                                │
                                                ├─ core/        pure engine: normalise, extract, decide, cluster, cnmc   [BUILT]
                                                ├─ services/    ingest, runs, review, consent, registry, savings, search
                                                ├─ ai/          classifier, Ollama clients (reader, embeddings), grounding check
                                                ├─ jobs         one background worker, progress in the run table
                                                └─ security/    JWT, RBAC, audit, egress guard                            [mostly BUILT]
                                                │
                                         Ollama (llm)  granite4.1:3b + nomic-embed-text, internal network only
All containers on an internal Docker network with no internet route (already configured).
```

### 9.1 Run pipeline (one click → results)

| Stage | What happens | Module | Status |
|---|---|---|---|
| 1 Ingest | parse CSV/XLSX, map columns (SAP preset), UoM aliases, content hash, COPY into `material_record` | `services/ingest.py` | new |
| 2 Normalise | dictionary expansion, NFKC, fixed point | `core/normalise.py` | built |
| 3 Read (4 layers) | rules → typo dictionary → ML classifier → LLM (only for gaps), with grounding check | `core/extract.py`, `ai/` | rules built; rest new |
| 4 Candidates | blocking on (category, size), BM25 keywords, nomic-embed-text embeddings in pgvector, MPN match | `services/candidates.py` | new |
| 5 Decide | veto → unknown → route; evidence rows with rule IDs | `core/decide.py` | built |
| 6 Cluster | constrained clustering (no conflict inside a cluster) | `core/cluster.py` | built |
| 7 Store & stats | COPY pairs, clusters, look-alikes, baselines, channel stats | `services/runs.py` | new |

### 9.2 The AI stack and its guardrails

| Component | Model (local, licence) | Used for | Can it change a verdict? |
|---|---|---|---|
| Typo-tolerant dictionary | rapidfuzz on a word list (no model) | `LFANGE`→`FLANGE`, `FLAT FACE`→`FF` | No: it changes text before the rules read it; golden tests guard it |
| Category classifier | scikit-learn char n-grams, trained on the train split | category when no keyword | No: abstains below threshold; `decide()` still needs core attributes |
| Semantic candidates | `nomic-embed-text` via Ollama (Apache-2.0, 768 dims) stored in pgvector | finding pairs worth comparing | No: only proposes pairs |
| LLM reader | `granite4.1:3b` via Ollama (Apache-2.0; comparison `qwen2.5:3b-instruct`). Probe on 5 Oct: about 1.5 s per record on the laptop GPU, 100% of returned spans present in the text, but some values under the wrong attribute name, so the rule re-parse check is required | values the rules missed, with spans | No: values must pass the grounding check; it never sees the pair |

**Grounding check (code contract):** `verify(record_text, attr, value, span) -> bool` returns true only if `span` is a substring of the normalised text, `value` is in the template's value domain, and `extract(span)` for that attribute yields `value`. Rejected values are logged and counted in run stats.

**Speed plan:** the LLM runs only on records with gaps after layers 1–3, results are cached by content hash, and the demo uses a pre-computed run snapshot. Throughput is measured on this laptop before we commit to a model; if CPU is too slow, the GPU (RTX 3050 Ti, 4 GB) can be passed through to Docker, or the LLM layer is switched off and the badge says "AI READER OFF".

### 9.3 Data model changes (one new migration `0002`)

| Change | Why |
|---|---|
| `material_record.stock_qty numeric` (nullable, ≥ 0) | stock sharing (Pillar 6) |
| `cnmc.hsn text` (nullable, verified-table rule like UNSPSC) | Indian classification (Pillar 1/8) |
| `spec_record.attr_meta` keeps `{source: RULE|AI|PERSON, span: [start,end], model: …}` per attribute (no DDL change, JSONB contract update) | Pillar 2 provenance |
| `review_task` / inbox gets an attribute-question type, or a small `attribute_question` table (decide in slice 3) | Pillar 4 routing |

Everything else uses the existing 26 tables.

### 9.4 API groups

Auth/users/audit (built) · uploads + mapping · runs (start, progress, cancel, stats) · pairs + evidence · clusters + review + consent · questions (ask, answer) · registry + crosswalk + exports + migration pack · search-before-create (API key) · dashboard, savings, health · rulebook + impact preview · evaluation · system (health, air-gap). Endpoint names follow PRD section 8 where they exist there.

### 9.5 Hardware budget (this laptop: i7-11800H 8 cores, 16 GB RAM, RTX 3050 Ti 4 GB)

| Container | Memory |
|---|---|
| db | 1 GB |
| api (no torch; embeddings come from Ollama) | 1–2 GB |
| llm (Ollama, 3B model, 4-bit; mostly on the 4 GB GPU) | 2–3 GB |
| web | < 0.2 GB |

Docker currently has 8 GB. Recommended: raise WSL2 memory to 10 GB in `%UserProfile%\.wslconfig`.

### 9.6 Quality and testing

- Keep everything that exists: 512 backend tests, 25 golden cases, property tests, reference conformance, architecture test (`core/` stays pure), CI.
- New per slice: API tests for every endpoint (RBAC table), one end-to-end test per slice (upload → … → result), golden cases grow to ≥ 60 (every template).
- AI layer tests: the grounding check rejects invented values (property test with random spans); the LLM is mocked in CI; the real model is tested by a `make test-ml` target.
- Before the finale: the demo path runs offline 3 times in a row from a snapshot.

---

## 10. What we will not claim

- No real-world accuracy, savings or ROI numbers. Savings are shown as **price gaps on synthetic data**.
- Never "first", "only", "best", "beats" (on screen, slides or stage).
- No claim that an AI decides identity; it reads and proposes.
- Uniqueness only for what the scan supports (consent, change notices, impact preview, statistical bound), worded as "not found in the 41 public repos we inspected on 3 Oct 2026". Pillars marked **re-check** are verified by a fresh scan before being called different.

---

## 11. Risks and answers

| Risk | Answer |
|---|---|
| LLM too slow on CPU | Only gaps go to the LLM; cache; GPU pass-through; snapshot for the demo; can be switched off |
| LLM invents a value | Grounding check (span must exist, value in domain, rule parser agrees); never sees the pair |
| Scope too big | Slices in order; after slice 2 the core demo is complete; later slices only add |
| Judges: "too rule-based" | Run console shows the AI share; S11 shows what each layer contributed |
| Judges: "numbers are on your own data" | Real-text test set labelled by an outsider, shown separately |
| Demo laptop fails | Snapshot + second laptop + recorded video |
| Pre-written code not allowed at the finale (open question Q-01) | Ask the SPOC now; if not allowed, this build becomes the rehearsed reference and the docs stay the spec |

---

## 12. Changes from `impdocs/` (to approve, then log as DEC entries)

| # | Change | impdocs today |
|---|---|---|
| C1 | Build in vertical slices (section "Next steps") | 11 horizontal phases |
| C2 | Local LLM reader in P0, with the grounding check | P2, off by default |
| C3 | Typo-tolerant dictionary layer | not planned (Phase 5 had dictionary v2 phrases only) |
| C4 | Ask-don't-guess (SF-3) P0, questions routed to the owning CPSE's inbox | P1, no routing |
| C5 | ERP create simulator (SF-8) and pooling (SF-10) P0; stock sharing and price spread added | P1, no stock |
| C6 | Health score per CPSE | quality report only |
| C7 | HSN field next to UNSPSC | suggested in the Competitive Review, not scheduled |
| C8 | Real-text test set | not planned (style-D synthetic holdout only) |
| C9 | Schema migration `0002` (section 9.3) | schema v0.6 |
| C10 | Lighter process: gates become slice "works end to end" checks; DEC entries only for design changes | heavy gates and evidence per phase |
