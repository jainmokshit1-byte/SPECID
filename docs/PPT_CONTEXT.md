# PPT context: SpecID (SIH 2026 · PS SIH26099)

Everything a slide needs, in slide order. Put it into the team's template. Rules for every slide:
- Numbers come only from the **Numbers** section (each has a source and a reproduce command). Label
  them "synthetic data" where they are.
- Never write "first", "only", "best", "beats", and never claim real-world savings or accuracy.
- Screenshots are in `docs/evidence/v2-go1/screens/` (light theme, 1440×900).

---

## Slide 1 · Title

- **SpecID**: one national code for every real material, decided by engineering rules, approved
  by people, agreed by every CPSE involved.
- PS SIH26099 · AI-powered National Unified Material Master for CPSEs · team name, institute
- Prototype link: `https://<your-site>.netlify.app` (demo buttons on the login page)

## Slide 2 · The problem (one valve)

Three CPSEs, three codes, three texts, one valve:

| CPSE | Code | Text in its ERP |
|---|---|---|
| CPSE-A | 10004521 | `GATE VLV 4" CL150 WCB FLGD RF` |
| CPSE-B | MAT-77812 | `Valve, Gate, 100 NB, 150#, Cast Steel A216 WCB, Flanged RF` |
| CPSE-C | V/GT/0093 | `GATE VALVE DN100 CLASS 150 WCB RAISED FACE` |

Result: duplicate buying, no pooled demand, idle stock in one CPSE while another buys, no national
view. (Illustrative example from docs/STORY.md.)

## Slide 3 · Why text matching is not enough

- Same item, different words: `4"` = `4 IN` = `100 NB` = `DN100`; `150#` = `CL150`.
- Different items, almost the same words: `CL150` vs `CL300` is one character apart and a
  **safety** difference. Text similarity merges them; SpecID's veto blocks them.
- Screenshot: `lookalikes.png` (Look-alike Guard: similarity histogram + blocked pairs with the
  deciding attribute).

## Slide 4 · Our solution in one picture

```
ERP files ─► read & clean ─► specification (DNA) ─► compare: veto → can't tell → same
 (3 CPSEs)    (rules + AI,       per record            ─► groups ─► maker ─► checker ─► every
              AI values checked                                     CPSE consents ─► National code
              against the text)                                     + crosswalk + migration pack
```

Four answers per pair: **Identical · Equivalent · Not equivalent (veto) · Can't tell (ask)**.

## Slide 5 · The ten pillars (pick 6 for the slide)

1. Spec Fingerprint: every record becomes a typed specification.
2. Verified AI Reader: AI proposes a value only with the words it came from; rules check it.
3. Safety Veto + Look-alike Guard: a conflict on a must-match attribute blocks the merge, always.
4. Ask, don't guess: missing key values go to the CPSE that owns the record.
5. Federated consent: a national code is issued only after every CPSE involved agrees.
6. Savings & stock sharing: price gaps for the same item, idle stock to transfer before buying.
7. Duplicate firewall in SAP: search-before-create while the user types (S14).
8. Glass-box proof: evidence card per pair, hash-chained audit, seeded evaluation with bounds.
9. Governed rulebook: rules visible to every role, changed only through review.
10. Material master health score per CPSE.

## Slide 6 · Demo flow (matches the live link)

| # | Screen | Say |
|---|---|---|
| 1 | Home dashboard (`home.png`) | "Three CPSEs; same item groups, price gaps, idle stock." |
| 2 | Run console (`run-console.png`) | "Rules, then AI, then people. Every AI value is checked." |
| 3 | Cluster review (`cluster-maker.png`) | "Different words, same specification; every value shows its source." |
| 4 | Look-alike Guard (`lookalikes.png`) | "Text says same, specification says no." |
| 5 | Consent (`consents.png`, `cluster-steward.png`) | "A national code changes three organisations' data, so each agrees." |
| 6 | National code (`cnmc-detail.png`) | "Crosswalk to every legacy code, migration pack per CPSE." |
| 7 | SAP create (`erp-sim.png`) | "New duplicates are stopped while typing." |
| 8 | Savings (`pooling.png`) | "Price gap and transfer-before-buying, from purchase history." |
| 9 | Evaluation (`evaluation.png`) | "Reproducible, seeded, labelled synthetic, with an honesty panel." |

## Slide 7 · Results (synthetic data, reproducible)

Use the **Numbers** table below. Suggested headline: "On seeded synthetic data, SpecID made
**k of n** wrong merges on look-alike pairs (95% upper bound **x%**); a text-only baseline made
**m**." Always show the honesty line: "Synthetic data written by the team that wrote the rules;
optimistic by construction; not a measure of performance on real CPSE data."

## Slide 8 · PS coverage

| PS asks for | SpecID |
|---|---|
| AI matching across CPSEs | Candidate search (blocking, keywords, part number, meaning) + verified AI reader + rule engine |
| Duplicates / near / equivalent | Four verdicts; within-CPSE and cross-CPSE runs; Look-alike Guard |
| Standard descriptions | Canonical spec, 40-character SAP text, long text, UoM harmonisation |
| Classification | Rules → in-app classifier → AI; class path; UNSPSC / HSN |
| Common National Material Code | CNMC with Luhn check digit, issued after approval and consent |
| Old → new code mapping | Crosswalk row per legacy code, UoM factor |
| Migration | Migration pack per CPSE, change notices |
| Approval workflow | Review queue, maker ≠ checker, multi-CPSE consent, ask-don't-guess |
| Dashboard | Duplicates, health, price gaps, stock sharing, backlog |
| Audit & governance | Hash-chained audit with verify, read-only rulebook, consent |
| SAP / ERP | SAP column preset on upload, REST API, SAP-style create-screen check, SAP-ready exports |

## Slide 9 · Architecture & tech

```
Browser (React 18, TypeScript, Tailwind, Recharts)
   │  /api
FastAPI (Python 3.11) ── pure core engine (normalise · extract · decide · cluster · CNMC)
   │                  ── AI layer (in-app classifier; optional Gemini reader + embeddings)
PostgreSQL 16 + pgvector ── 26+ tables, hash-chained audit, crosswalk, consent
```

Two deployments, same code:
- **Cloud demo** (the link): Netlify + Render + Neon, synthetic data, optional Gemini.
- **On-premise, air-gapped** (for CPSEs): Docker Compose on the CPSE's own server, internal-only
  network, local models (e.g. Ollama), egress guard counting blocked outbound attempts. No CPSE data
  leaves the building.

Quality: 900+ backend tests (golden, property-based, API, RBAC matrix), 140+ frontend tests, typed
end to end, CI on every change.

## Slide 10 · Safety & governance (why a ministry can trust it)

- No score or AI model can override a veto (tested).
- Maker ≠ checker, enforced in the service and in the database.
- Every state change writes an audit event in the same transaction; the chain can be verified.
- AI values need the source words and must pass the rulebook; rejected values are counted on screen.
- Real data path is offline by design; the cloud demo shows "Cloud demo", never "Air-gapped".

## Slide 11 · Impact & rollout

- Pilot: 2–3 CPSEs, one category (valves), on-premise; measure with their own reviewed samples.
- Scale: add categories by adding rulebook templates (YAML, reviewed), not code.
- Integrate: SAP preset for upload, REST API for search-before-create in the ERP create screen.
- Impact is shown per run (price gap, transfers, duplicates), never claimed in advance.

## Slide 12 · Team & thanks

---

## Numbers (fill the slides only from here)

| Number | Value | Source | Reproduce |
|---|---|---|---|
| Records in the local demo run | 3,023 (CPSE-A 993 · B 1,019 · C 1,011), health score 99 each | Home dashboard, run 15632efb | upload the seed-7 files, cross-CPSE run |
| Run time, 3,023 records | 11.2 s on a laptop | `docs/evidence/v2-go1/chunk2_run_seed7.md` | same |
| Candidate pairs | 78,201 | same | same |
| Verdict mix | IDENTICAL 157 · EQUIVALENT 1,019 · NOT_EQUIVALENT 70,932 · CAN'T TELL 6,093 | same | same |
| Same-item groups across CPSEs | 689 (170 held by all 3 CPSEs) | Home dashboard | same |
| Price gap, same item bought by ≥ 2 CPSEs | ₹5,22,03,067 over 398 items (synthetic prices) | Home dashboard | same |
| Idle stock to share | ₹7,14,52,487 in 195 transfer suggestions (synthetic) | Home dashboard | same |
| Look-alike pairs blocked | 6,938 pairs at ≥ 85% text similarity blocked by the specification | Review → Look-alikes | same |
| **Evaluation, seed 7: wrong merges** | **SpecID 0 of 321** look-alike pairs (95% upper bound 0.93%) · text-only B1 18 of 321 · text + numbers B2 56 of 321 | Results → Evaluation, eval eac2510c | `make eval SEED=7` (1,200 entities, 3,355 records) |
| Evaluation: precision | SpecID 100.00% · B1 35.25% · B2 41.40% | same | same |
| Evaluation: same items found (strict recall) | SpecID 61.2% · B1 29.0% · B2 36.7% | same | same |
| Evaluation: "can't tell" | 38.8% of true pairs (181); 177 of those 181 miss a key value in the text, so asking is right | same | same |
| Evaluation: blocking | 97.7% of true pairs reached while comparing 2.39% of all pairs | same | same |
| Where B1 went wrong | all 248 of B1's wrong merges (any pair) were "can't tell" for SpecID, i.e. sent to a person | same | same |
| Cloud demo on the free tier | port open in 33 s, demo data ready in 222 s, peak 219 MB of 512 MB (0.1 CPU rehearsal) | rehearsal 5 Oct 2026 | `docs/DEPLOY.md` |
| Tests | 915+ backend, 141 frontend, all passing | CI | `make test` |

Honesty line for every results slide: *Synthetic data written by the team that wrote the rules;
optimistic by construction; not a measure of performance on real CPSE data. Zero observed wrong
merges is reported with its 95% upper bound, never as "never".*

## Screenshots to use

`docs/evidence/v2-go1/screens/`: home, run-console, cluster-maker, cluster-steward, consents,
cnmc-detail, lookalikes, erp-sim, pooling, evaluation, rulebook, about, login-demo.
