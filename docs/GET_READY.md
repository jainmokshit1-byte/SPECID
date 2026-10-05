# Get ready: everything you need to own this project

Read this once, top to bottom (about 30 minutes), then do the hands-on part in section 5 (about 30 minutes). After that you can explain the project, run it, and follow every step of `docs/NEXT_STEPS.md`.

---

## 1. Explain SpecID in 60 seconds (say this out loud until it is easy)

> "Big government companies buy the same valves, pipes and bolts, but each gives them different codes and descriptions. So nobody sees that they are buying the same thing, they can't buy together, and they each keep their own spare stock.
>
> SpecID reads every material description, turns it into a clean specification (size, pressure class, material and so on), and says whether two records are the same item. AI does the reading, and engineering rules check every value the AI reads. If the rules find one key difference, like a 150 versus 300 pressure class, the items are never merged, because that would be a safety risk. If something is unknown, we don't guess; we ask the company that owns the record.
>
> People approve each match, and every company whose code is involved must agree. Then one national code is issued, linked to all the old codes, and each company gets a migration file. From then on, if someone tries to create a duplicate in SAP, we warn them. And the dashboard shows the money: the same item bought at different prices, the combined demand, and idle stock that one company could give another. Everything runs offline, on the company's own machines."

---

## 2. Twenty words you need

| Word | Plain meaning |
|---|---|
| **CPSE** | Central Public Sector Enterprise: a company owned by the central government (ONGC, NTPC, SAIL, BHEL, …) |
| **Material master** | A company's list of every item it buys or stocks, one row per item: code, description, unit, group |
| **Material code / legacy code** | The company's own ID for an item (in SAP: `MATNR`). "Legacy" = the old code, before our national code |
| **SAP / ERP** | The big business software CPSEs run. SAP fields we use: `MATNR` (code), `MAKTX` (40-char short text), `MEINS` (unit), `MATKL` (material group) |
| **CNMC** | Common National Material Code: our one national code per real item, like `NMC-00000012345` (last digit is a check digit) |
| **Crosswalk** | The table linking each old company code to its national code |
| **Migration pack** | A file per company saying what to do with each old code: keep it, block it for new buying, or phase it out when stock reaches zero |
| **Specification / spec** | The key engineering facts of an item: type, size, pressure class, material, end connection |
| **Template** | Per category (valve, pipe, …) the list of attributes and which ones are "core" (must match) or "extended" |
| **Core attribute** | Must be known and equal on both sides for a match (for a valve: type, size, class, body material, end connection) |
| **Veto** | When a core attribute differs, the answer is NOT_EQUIVALENT, and nothing (score, ML, AI) can override it |
| **Verdicts** | `IDENTICAL` (same spec + same maker and part number), `EQUIVALENT` (same spec, any maker), `NOT_EQUIVALENT` (key difference), `INSUFFICIENT_DATA` ("can't tell": a key value is unknown) |
| **DN / NPS / NB** | Pipe size systems. `4 IN` (inches, NPS) = `100 NB` = `DN100`. The engine converts them |
| **Class (CL150, 150#)** | Pressure rating. CL300 holds about double the pressure of CL150. A classic look-alike trap |
| **Evidence card** | The table that shows, attribute by attribute, both values, MATCH/CONFLICT/unknown, the rule ID and any conversion note |
| **Blocking / candidates** | Instead of comparing every record with every other (millions of pairs), only compare likely pairs: same category and size, similar words, similar meaning |
| **BM25** | A classic keyword-search score (like a search engine) |
| **Embeddings + FAISS** | A small AI model turns text into numbers so "similar meaning" can be searched fast; FAISS is the fast search library |
| **LLM (local)** | A small language model running on our own machine (through Ollama), used only to read descriptions, never to decide |
| **Maker–checker** | One person proposes, a different person approves. The database itself blocks the same person doing both |
| **Hash-chained audit** | Every action is recorded; each record includes a fingerprint of the previous one, so any edit breaks the chain and is detected |
| **Golden tests** | Fixed example pairs with the correct answer. They must always pass and are never edited to make code pass |
| **Synthetic data** | Fake but realistic data our generator creates (3 CPSEs, about 3,000 records), with known correct answers |

---

## 3. How SpecID thinks: one real example

This is real output from the engine, already running on your laptop:

```
A: GATE VALVE 4IN CL150 WCB FLGD RF
B: VALVE,GATE,100NB,150#,A216 WCB,FLANGED

attribute        a           b          status    note
valve_type       GATE        GATE       MATCH
size_dn          100         100        MATCH     4 IN = DN100 · 100 NB = DN100
pressure_class   150         150        MATCH
body_material    A216-WCB    A216-WCB   MATCH     WCB -> A216-WCB
end_connection   FLANGED-RF  FLANGED-?  PARTIAL   (B does not say the flange face)

verdict INSUFFICIENT_DATA · reason: core attribute not verifiable: end_connection
```

What happened, step by step:
1. **Normalise:** `FLGD` became `FLANGED`, `150#` became `CL150`.
2. **Extract:** each text became a spec. Sizes in different systems (`4IN`, `100NB`) became the same `DN100`.
3. **Compare:** four core attributes match. B never says which flange face (RF = raised face, FF = flat face), and a raised-face and flat-face flange are not interchangeable.
4. **Decide:** so the engine refuses to guess: "can't tell, ask for the flange face of B". That is the "never guess" principle working.

Now the problem we found, in numbers (synthetic seed-7, 2,166 pairs that are truly the same item):
- 897 were correctly found (IDENTICAL or EQUIVALENT), **1,265 ended as "can't tell"**, 4 were wrongly vetoed.
- 0 of 1,217 look-alike traps were merged. The safety part works.
- Of the values missing in the "can't tell" cases, about **half are actually in the text** but the rules missed them (typos like `LFANGE`, `CLSAS`; phrases like `FLAT FACE`; no category word, like `25NB 300# WCB BW`). **That is the job for AI.** The other half are really not in the text. **That is the job for "ask, don't guess".**

---

## 4. The codebase map

```
SIHPS099/
├─ CLAUDE.md                 rules for AI coding agents (read section "Hard rules")
├─ PROGRESS.md               where the build stands, phase by phase
├─ docs/
│  ├─ SOLUTION.md            the final product design (v2)
│  ├─ NEXT_STEPS.md          the plan
│  ├─ GET_READY.md           this file
│  └─ DECISIONS.md           every design decision (DEC-01 … DEC-30)
├─ impdocs/                  your friend's full spec: PRD, TRD, App Flow, UI/UX, DB schema, plan, research
├─ templates/                valve.yaml, pipe.yaml, … (the rules per category) + dictionary.yaml, uom.yaml
├─ backend/
│  ├─ app/core/              THE ENGINE (pure Python, no database): normalise, units, extract, classify,
│  │                         decide, cluster, cnmc, shortdesc, radar (look-alikes), baselines
│  ├─ app/services/          business logic with the database: users, audit (more to come)
│  ├─ app/api/               HTTP endpoints (FastAPI): auth, users, audit, health
│  ├─ app/db/                tables (models.py), migration SQL, seed
│  ├─ app/security/          passwords, login tokens, roles/permissions, rate limit
│  ├─ app/eval/generator.py  synthetic data generator
│  ├─ app/cli.py             command line: generate, decide, extract
│  └─ tests/                 512 tests: unit, golden, property, reference, integration, api
├─ frontend/src/             React app: pages (Login, Home, Audit, Users built), components, routes.ts
├─ data/synthetic/           generated data (only manifest.json is kept in git)
├─ models/                   AI model files (empty until slice 3)
└─ docker-compose.yml        db + api + web (+ llm later)
```

Where to look for what:
- "Why did the engine say X?" → `backend/app/core/decide.py` and the template YAML.
- "Which roles can call which endpoint?" → `backend/app/security/permissions.py`.
- "What tables exist?" → `backend/app/db/models.py` (or `impdocs/SIH26099_SpecID_05_Backend_Schema.md`).
- "What screens are planned and how do they behave?" → `impdocs/SIH26099_SpecID_03_App_Flow.md`.

---

## 5. Hands-on (do these once, in PowerShell from `C:\Users\Asus\Desktop\SIHPS099`)

Docker Desktop must be running.

| # | Do | Command / action | You should see |
|---|---|---|---|
| 1 | Start the app | `docker compose up -d` | 3 containers running |
| 2 | Open it | browser → http://127.0.0.1:8080 | login page |
| 3 | Log in | user `admin`, password = `DEMO_PASSWORD` in `.env` | Home; sidebar shows Audit and Users |
| 4 | See the audit chain | Audit → **Verify chain** | "chain intact" and your login events |
| 5 | Try the engine on two texts | `docker compose exec api python -m app.cli decide --a "GATE VALVE 4IN CL150 WCB FLGD RF" --b "GATE VALVE 4IN CL300 WCB FLGD RF"` | `NOT_EQUIVALENT`, conflict on pressure_class |
| 6 | Same item, different words | `docker compose exec api python -m app.cli decide --a "GATE VALVE 4IN CL150 WCB FLGD RF" --b "VALVE,GATE,100NB,150#,A216 WCB,FLANGED,RF"` | `EQUIVALENT` (B now states the face) |
| 7 | See what the engine reads | `docker compose exec api python -m app.cli extract --text "PIPE SMLS 1-1/2IN SCH40 A53 GR.B"` | spec with DN40, schedule 40, A53-B |
| 8 | Run it on all synthetic data | `docker compose exec api sh -c "python -m app.cli generate --seed 7 --out /tmp/s7 && python -m app.cli decide --file /tmp/s7"` | the verdict table from section 3 |
| 9 | Run all backend tests | Git Bash: `sh backend/scripts/ci_local.sh backend` (about 3 minutes) | `512 passed` |
| 10 | Stop | `docker compose down` | — |

Try your own texts in steps 5–7: change the size, write `150#` instead of `CL150`, make a typo. Seeing what breaks is the fastest way to understand the engine.

---

## 6. House rules (from `CLAUDE.md`, in plain words)

1. The engine (`core/`) never talks to the database or web layer.
2. **Nothing may override a veto**: no score, no ML, no LLM.
3. Never edit golden tests to make code pass.
4. **Offline:** no internet calls, no CDN fonts, no cloud AI APIs.
5. Database changes only through migrations.
6. Every change of state writes an audit event.
7. Maker ≠ checker; a multi-CPSE code needs every CPSE's consent.
8. No real confidential CPSE data in the repo; synthetic data is always labelled.
9. No hand-typed result numbers in the UI; no "first / only / best / beats".
10. Secrets only in `.env`.

---

## 7. Questions judges will ask (short answers)

| Question | Answer |
|---|---|
| Where is the AI? | AI reads the text (typo correction, classifier, local LLM), and finds candidates by meaning (embeddings). Rules check what it reads, and people approve. The run console shows how much each layer did |
| Why not let the AI decide? | A model can't guarantee CL150 ≠ CL300. A wrong merge is a safety risk, so identity is decided by rules the CPSE engineers can read and change |
| What if data is missing? | We say "can't tell" and ask the CPSE that owns the record. We never fill in a value ourselves |
| How do you integrate with SAP? | SAP field import, a REST API that SAP calls before creating a material, SAP-style crosswalk and migration files. Writing back into SAP goes through each CPSE's own change process |
| How accurate is it? | On our synthetic set: [numbers from the evaluation page]. On a small real-text set: [numbers]. Real accuracy needs a pilot with 2–3 CPSEs |
| What stops one CPSE overwriting another's data? | Every CPSE whose code joins a national code must consent; declines are recorded |
| Does data leave the machine? | No. Everything, including the AI models, runs locally; the network has no internet route, and a counter shows blocked attempts |
| How does it scale to lakhs of records? | Blocking + search indexes mean we compare only likely pairs, not all pairs; the database and engine scale horizontally (production path is in the TRD, section 19) |
