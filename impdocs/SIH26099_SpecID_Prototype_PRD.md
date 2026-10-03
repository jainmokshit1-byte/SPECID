# PRD: SpecID Prototype (MVP)
## PS SIH26099: AI-Driven Standardization and Harmonization of Material Codes Across CPSEs

| Field | Value |
|---|---|
| Document | Product Requirements Document for the **prototype** |
| Version / status | **v0.6** · 3 Oct 2026. **v0.6 aligns the PRD with the build decisions DEC-01 to DEC-27 (Phases 1–4, see 17.3):** about 3,000 demo records (DEC-09), normaliser runs to a fixed point (9.2), IDENTICAL rule clarified (9.5), unresolvable values are unknown (9.5), long-description order (9.9), generator rules (10.1), five user endpoints (8), SYNTHETIC DATA badge and air-gap wording (11.2, FR-1463, FR-1491), template activation by one ADMIN (12), dense channel P0 (6.2/6.3), production deviations from Appendix C listed (C.1). v0.5: **Re-positioned after measuring the public landscape:** 45 public SIH26099 repos found, 41 cloned and inspected (companion *Competitive Review*). Most v0.2 "signature features" already exist in strong public repos, so they are now **parity features**; three governance features not found in any inspected repo become the differentiators: **multi-CPSE consent (SF-11, P0)**, **rulebook impact preview (SF-6, now P0)**, **per-CPSE change notices (SF-12, P1)**, plus **bounded false-merge reporting (SF-5)**. Also fixes items found while writing docs 02–06: blocking key (FR-501), auth library (6.3), run statuses (FR-507), schema moved to doc 05 (v0.6), screens S16–S19. v0.4: aligned with the official PS. v0.3: consistency review. v0.2: landscape and signature features |
| Product | **SpecID** (working title) |
| PS owner | Ministry of Petroleum & Natural Gas · Department: **Chennai Petroleum Corporation Limited (CPCL)** · Category Software · Theme Smart Automation · sectors named in the PS: Oil & Gas, Power, Steel, Mining, Heavy Engineering |
| Companion files | `SIH26099_Research_Solution_PPT_Content.md` (research dossier and 6-slide idea PPT; references such as *A4.3* point into it) · `SIH26099_SpecID_TRD.md` (02, technical design) · `SIH26099_SpecID_03_App_Flow.md` · `SIH26099_SpecID_04_UI_UX_Design_Brief.md` · `SIH26099_SpecID_05_Backend_Schema.md` (authoritative DDL) · `SIH26099_SpecID_06_Implementation_Plan.md` · `SIH26099_SpecID_Competitive_Review.md` (measured comparison with 41 public repos) |
| Target | SIH 2026 software-edition prototype. Plan assumes a **36-hour** finale and a **team of 6**; confirm both (Q-02) |
| Owner | [team lead] |

---

## 0. How to use this PRD

- **IDs** make everything traceable: `US-` user story · `FR-` functional requirement · `NFR-` non-functional · `D-` decision · `Q-` open question · `T-` test group. **Priorities:** **P0** must be in the finale demo · **P1** should · **P2** could.
- **Integrity rules carried over from the dossier:** no fake results; evidence tags **[L]** literature, **[M]** measured, **[T]** target (not a result); every screen that shows evaluation numbers carries a **SYNTHETIC** badge.
- **Terms** (CNMC, identity-critical attributes, crosswalk, evidence ladder) are defined in the dossier glossary (its Appendix C).
- **Appendices hold tested reference material** ("specification by example"): category templates (A), seed tables (B), reference code (C), tests (D), PostgreSQL schema (E), traceability (F).
- **What was actually verified while writing this PRD:** (1) the schema (now in doc 05, v0.6) was executed on PostgreSQL 16 and its safety constraints were tested; (2) the templates in Appendix A match the policy and the rule texts in the reference code exactly; (3) the reference code in Appendix C passes the tests in Appendix D (12 golden pairs, 13 edge cases, route and flag checks, a 1,500-pair property smoke test, CNMC check-digit tests, clustering, and the signature-feature functions: cited decisions, two text baselines, look-alike guard, ask-don't-guess, rulebook impact preview). **These are spec self-checks, not evaluation results.** They prove the spec is internally consistent, not that it works on real CPSE data.
- **Rules check before you copy any code (Q-01):** I have not verified whether the 2026 finale rules allow code written before the event. If they do not, use Appendices C and D only as a specification and write your own implementation during the finale.

---

## 1. Product overview

### 1.1 Problem (short)
Each CPSE codes the same item differently. Text similarity cannot tell a CL150 valve from a CL300 valve (near-miss pairs scored 0.95 against 0.65 for true equivalents on 12 hand-built pairs [M], dossier A4.3). A wrong merge is a safety risk; a missed duplicate is idle capital. Full problem, evidence and landscape are in the dossier (A1–A5).

### 1.2 Product statement
> SpecID is a web application and API that ingests CPSE material-master extracts, converts every record into a verified specification, decides whether two records are **identical, equivalent, different or undecidable**, and lets human reviewers approve **one national material code (CNMC) per specification** with a crosswalk to every legacy code.

### 1.3 Prototype goals

| ID | Goal |
|---|---|
| G1 | Demonstrate the **end-to-end flow** on two or three synthetic CPSE catalogues: ingest → harmonise → review → CNMC + crosswalk → search-before-create |
| G2 | Make the **decision policy visible**: four verdicts, hard veto, evidence card, explicit "we don't know" |
| G3 | Produce an **honest, reproducible evaluation** on a seeded synthetic near-miss benchmark, with false-merge rate, confidence bounds and evidence-level labels |
| G4 | Run **offline on a laptop** (`docker compose up`) so the demo survives bad venue Wi-Fi |
| G5 | Be **ready for real CPSE data**: mapping wizard, editable templates, no hard-coded demo assumptions |
| G6 | Supply screenshots and a working demo for **Slide 3 ("working prototype")** of the idea PPT |
| G7 | **Look different, honestly:** build the P0 features of 1.8: the **parity set done well** and the **differentiators not found in 41 public SIH26099 repos** (multi-CPSE consent, rulebook impact preview, bounded false-merge reporting), so a judge can *see* the difference within five minutes, without any overclaim |
| G8 | **Cover the PS in full:** every *Expected Solution* bullet and all 8 *Key Capabilities* of SIH26099 map to a P0 requirement, a screen and a slide (compliance matrix 1.12) |

### 1.4 Non-goals (for the prototype)
- Production-scale throughput, high availability, multi-tenant hardening.
- Live SAP/ERP write-back. The prototype integrates through an SAP-field import preset, the search-before-create API and SAP-style migration files (FR-1005, FR-905, FR-907); write-back is a pilot step done through each CPSE's own master-data change process.
- A full UNSPSC / eCl@ss / MESC crosswalk for every category. The prototype maps only its templated categories, from a verified mapping table (FR-405).
- Fine-tuned transformer matchers; federated or privacy-preserving matching.
- Any accuracy, savings or ROI claim on real data. No real CPSE data in the public repo.

### 1.5 Success criteria for the prototype (targets **[T]**, not results)

| ID | Criterion |
|---|---|
| SC-1 | The full flow completes on the bundled synthetic dataset (**about 3,000 records**, 3 CPSEs; DEC-09) in ≤ 10 minutes on an 8-core / 16 GB laptop with Docker at its default memory. The generator scales to about 10k records by parameter, but the demo and every reported number use the 3k set |
| SC-2 | 100% of golden tests pass (target ≥ 60 pairs by T+30, covering every template) |
| SC-3 | Property tests hold: no cluster contains an identity-critical conflict; verdicts are symmetric; a veto is never overridden |
| SC-4 | The Evaluation page shows metrics from the seeded synthetic run with a SYNTHETIC badge, the false-merge count out of *n* hard negatives, and the rule-of-three upper bound |
| SC-5 | Search-before-create answers in ≤ 1 s (p95) against a registry of about 5k CNMCs |
| SC-6 | A reviewer can approve a cluster in ≤ 3 interactions and always sees the evidence card |
| SC-7 | The 5-minute demo script (section 15.1; 3-minute cut without the *opt.* scenes) runs end-to-end offline, three times in a row |
| SC-8 | No screen, report or slide presents synthetic results as real-world accuracy |
| SC-9 | **Look-alike Guard** lists, for the bundled seeded run, every hard-negative pair that text similarity ≥ 0.85 would have merged and SpecID vetoed, each with its decisive attribute (target ≥ 20 pairs listed) |
| SC-10 | **Baseline scoreboard** is computed for the seeded run with both baselines (B1, B2) next to SpecID, thresholds tuned on validation only |
| SC-11 | **Air-gap proof:** the demo path works with the network disabled, and the footer shows the blocked-egress counter at 0 |
| SC-12 | Every evidence row shows its rule ID, and every conversion (`4 IN = DN100`) is annotated |
| SC-13 | **Multi-CPSE consent:** a cluster spanning three CPSEs cannot receive a CNMC until a steward of each participating CPSE has consented; a decline leaves that CPSE's records unmapped, with the reason recorded and shown on the dashboard |
| SC-14 | **Rulebook impact preview:** before any template change is activated, the ADMIN sees how many stored decisions of the latest run would change verdict or route, and activation is blocked until the golden tests pass |

### 1.6 Scope tiers

| Tier | Contents |
|---|---|
| **P0 (finale must)** | CSV upload + mapping wizard + data-quality report · rule-based normaliser, extractors and templates for **valve, pipe, flange, fastener, motor** · rule-first classification with an ML fallback, class path and UNSPSC mapping (FR-402, FR-405) · UoM harmonisation (FR-205) · optional procurement-history upload (FR-107) · category/size blocking + BM25 + MiniLM/FAISS semantic channel · veto/unknown-state decision engine with evidence cards · constrained clustering · review queue + cluster view + maker–checker · CNMC issuance + crosswalk + CSV/JSON/SAP-style export + per-CPSE migration pack (FR-907) · SAP import preset (FR-1005) · analytics dashboard with duplicate, quality and demand panels (FR-1201, FR-1203) · search-before-create API + sandbox · seeded synthetic generator + evaluation page · JWT + RBAC + hash-chained audit log · offline docker compose · **differentiators P0: multi-CPSE consent (SF-11), rulebook impact preview with golden-test gate (SF-6), bounded safety scoreboard + honesty panel (SF-5)** · **parity P0: Look-alike Guard (SF-1), baseline scoreboard (SF-2), cited decisions (SF-4), air-gap proof (SF-7)** |
| **P1 (should)** | Gasket template · substitute candidates for functional equivalence (FR-612) · LightGBM scorer + calibration + threshold selection · bulk approve with forced sample · cannot-link memory · unknown-token miner · style-holdout evaluation · **P1: per-CPSE change notices (SF-12), ask-don't-guess loop (SF-3), ERP create-material simulator (SF-8), reversible merges (SF-9), pooling view (SF-10)** |
| **P2 (could)** | spaCy NER tier · local LLM extractor/advisor (Ollama) · public-benchmark adapter · impact calculator · cable template · Playwright UI tests · Celery |
| **Out** | See 1.4 |

---

### 1.7 Existing solutions and what is missing

Summary of the dossier (A2, A3, Appendix D). Source IDs `[S#]` are the dossier's reference IDs. Limitations are **inferences from public documentation, not tests of those products.**

| Family | Examples | What they do | Limitation relevant to this PS |
|---|---|---|---|
| ERP-native duplicate check | SAP MDG duplicate check [S3] | Similarity score with configurable thresholds inside one SAP landscape | Score on descriptions; practitioners report false positives when only descriptions are compared; single-enterprise scope |
| AI MDM and harmonisation platforms | Verdantis [S4], Palantir AIP Material Harmonization [S5], Sievo [S6], SPARETECH [S7], Verusen / Automa [S8] | Cleanse, deduplicate, harmonise, recommend similar materials | Enterprise-scoped, vendor-hosted, commercial. Public pages do not describe an engineering-attribute veto, an explicit "unknown" verdict, calibrated precision or false-merge reporting, or a neutral cross-company registry |
| Standards and taxonomies | UNSPSC [S12], eCl@ss, Shell MESC [S10], CFIHOS [S11] | Classification, licensed catalogue, property libraries | A category is not an identity; MESC is licensed and single-owner; CFIHOS targets equipment handover |
| Research | WDC Products [S13], LLM matching [S14], real material-master studies [S16, S17] | Benchmarks and methods | Consumer-product benchmarks; strong LLM results use hosted APIs; industrial datasets are private; text-only matchers lose precision on near-miss negatives |
| Public SIH26099 prototypes | **45 repos found, 41 cloned and inspected on 3 Oct 2026** (Competitive Review) | 14 have ≥ 10k lines of code; 22 have test files; the strongest (SAMAN, Tulya, SamePart, MaretialIQ, NUMM, KAM185/OneCode-AI, mkhanamm) implement attribute vetoes, planted hard negatives, baselines on the same candidates, insufficient-evidence verdicts, offline or air-gapped modes (one with an egress guard), hash-chained audit, substitutes, SAP-style migration with rollback, and measured P/R on synthetic data | Not found in any of the 41: **consent from every CPSE whose code joins a national code**, **preview of a rule change's effect on stored decisions**, **per-CPSE change notices**, **false-merge counts with a statistical bound**. Method: code and docs searched by keyword, then the strongest repos read by hand; "not found" is not proof of absence |

**Missing across the landscape (dossier A3; v0.5 note: in the 41 public SIH26099 repos, G2–G7 are now widely addressed — the open space is cross-CPSE governance, see 1.8):** G1 neutral cross-CPSE registry · G2 attribute veto plus explicit unknown · G3 precision-first reporting with false-merge rate · G4 per-decision evidence · G5 cross-CPSE prevention at creation · G6 sovereign, on-prem AI · G7 open evaluation protocol.

### 1.8 Parity features and differentiators (re-measured in v0.5)

SpecID is **not a new matching algorithm.** It is a *decision policy + neutral registry + governance protocol + evidence discipline*.

**What the v0.5 measurement changed.** In v0.2 the signature features were judged against READMEs. In v0.5 the team cloned 41 public SIH26099 repositories and searched their code and documents (Competitive Review). Several strong teams already ship look-alike lists, baselines, insufficient-evidence verdicts, ask-and-re-decide loops, egress guards, hash-chained ledgers, substitutes and migration with rollback. Those features stay in SpecID because the PS and the safety story need them, but they are **parity**: we build them well and never call them unique. The differentiation now comes from what none of the 41 repos showed: **governing a national registry across CPSEs that do not report to each other.** Every national code changes several CPSEs' master data, so SpecID makes those CPSEs *consent*, lets the rulebook owner *see the consequences of a rule change before it happens*, and *tells each CPSE what changed for it*. It also states its safety number the way a regulator would read it: false merges *k of n with a 95% bound*.

| ID | Feature | What a judge sees | Status in the 41 public repos (measured 3 Oct 2026) | Role | Pri | FRs | Effort **[T]** |
|---|---|---|---|---|---|---|---|
| SF-11 | **Multi-CPSE consent** | A valve cluster spans CPSE-A, B, C. Maker and checker approve, the card shows "waiting for CPSE-C consent"; the CPSE-C steward consents and only then the CNMC is issued. A decline keeps CPSE-C's code out, with the reason on the dashboard | Not found | **Differentiator** | **P0** | FR-1501–1504 | ≈ 5 h |
| SF-6 | **Rulebook impact preview** | ADMIN drafts "move design_standard to core" → sees "12 stored decisions change EQUIVALENT → INSUFFICIENT_DATA, 3 CNMCs affected in 2 CPSEs" + golden-test result → only then can activate | Not found (one repo shows rules-vs-model difference per pair, not a change preview) | **Differentiator** | **P0** (was P1) | FR-1451–1452, FR-403–404 | ≈ 6 h |
| SF-5 | **Bounded safety scoreboard + honesty panel** | "False merges: k of n hard negatives, 95% upper bound …" (Wilson / rule of three), abstentions, coverage, and what the numbers do not mean | Honest synthetic labelling and P/R tables are common; **no statistical bound on the false-merge count found** | **Differentiator** (the bound) | P0 | FR-1441–1443 | ≈ 3 h |
| SF-12 | **Per-CPSE change notices** | After an issuance, merge, unmerge or rule activation, each affected CPSE gets a notice listing its legacy codes and the new actions, with a delta migration file to acknowledge | Not found (a few repos mention propagation in docs only) | Differentiator | P1 | FR-1511–1513 | ≈ 4 h |
| SF-1 | Look-alike Guard | Pairs a text matcher would merge, vetoed, with the decisive attribute | Present (e.g. Tulya lists hard-key vetoes on near-identical text) | Parity | P0 | FR-1401–1403 | ≈ 4 h |
| SF-2 | Baseline scoreboard | B1 and B2 against SpecID on the same pairs | Present (Tulya: four baselines on the same candidates; SAMAN, mkhanamm: baselines) | Parity | P0 | FR-1411–1413 | ≈ 6 h |
| SF-4 | Cited decisions | Rule ID + rule text + conversion notes (`4 IN = DN100`) on every evidence row | Rule-based explanations common; conversion notes on evidence rows not found by search | Parity+ | P0 | FR-1431–1432 | ≈ 3 h |
| SF-7 | Air-gap proof | Footer counter, internal network, Wi-Fi off on stage | Present (SamePart has an egress guard; SAMAN, NUMM document air-gapped deployment) | Parity | P0 | FR-1461–1463 | ≈ 3 h |
| SF-3 | Ask, don't guess | Supply a missing value with a source note → re-decided | Present (SamePart: the reviewer answers and the pair is re-decided) | Parity | P1 | FR-1421–1423 | ≈ 5 h |
| SF-8 | ERP create-material simulator | Mock create form with live duplicate warning | Search-before-create common | Parity | P1 | FR-1471 | ≈ 4 h |
| SF-9 | Reversible merges | Unmerge with reason | Present (SAMAN rollback, KAM185 supersession) | Parity | P1 | FR-1481–1482 | ≈ 4 h |
| SF-10 | Pooling view | CNMCs held by ≥ 2 CPSEs with combined value | Present (NUMM pooled demand, Tulya pooling scenarios) | Parity | P1 | FR-1491 | ≈ 3 h |

Effort totals **[T]**: P0 features ≈ 30 hours (was 19), P1 ≈ 20 hours, spread over the team; see R-18 and the Implementation Plan for how the extra 11 hours are absorbed. "Not found" means not found by keyword search plus manual reading of the strongest repos on 3 Oct 2026; repositories change, so **re-run the Competitive Review scan before the finale**.

### 1.9 Gap-closure matrix

| Gap | Prototype answer | Signature features | Requirements | Where the judge sees it |
|---|---|---|---|---|
| G1 neutral cross-CPSE registry | CNMC registry and crosswalk; **consent from every participating CPSE**; change notices per CPSE; pooling view | SF-11, SF-12, SF-10, SF-9 | FR-901–906, FR-1501–1504, FR-1511–1513, FR-1481, FR-1491 | S6, S8, S15, S18, S19 |
| G2 attribute veto and explicit unknown | Four-verdict policy; ask-don't-guess loop; look-alike guard | SF-1, SF-3 | FR-601–606, FR-1401, FR-1421 | S6, S13 |
| G3 precision-first reporting | Safety scoreboard; baselines on the same run | SF-2, SF-5 | FR-1411, FR-1441 | S11 |
| G4 per-decision evidence | Cited decisions with conversion notes | SF-4 | FR-609, FR-1431 | S6, S7 |
| G5 cross-CPSE prevention | Search-before-create API; ERP simulator | SF-8 | FR-1001–1003, FR-1471 | S9, S14 |
| G6 sovereign, on-prem AI | Air-gap proof | SF-7 | FR-1461–1463 | Footer, demo step |
| G7 open evaluation protocol | Seeded generator, style-holdout, adversarial set, honesty panel | SF-5 | FR-1101–1106, FR-1442 | S11 |
| G8 governed rule changes (new in v0.5) | Draft → golden tests → impact preview over stored decisions → acknowledged activation → change notices | SF-6, SF-12 | FR-403–404, FR-1451–1452, FR-1511 | S10, S19 |

### 1.10 How we look different in a demo, and how to word it

| Aspect | Strong public SIH26099 prototypes (measured, 41 repos) | SpecID demo |
|---|---|---|
| Matching safety | Attribute vetoes and planted hard negatives are common | Same, plus the Look-alike Guard screen (parity) |
| Missing data | Insufficient-evidence verdicts in several; one asks and re-decides | Same: `INSUFFICIENT_DATA` + ask-don't-guess (parity) |
| Results | P/R/F1 tables on synthetic data, some with baselines | Same, plus **false merges *k of n* with a 95% bound** and an honesty panel (**differentiator**) |
| Governance of one decision | Maker–checker, hash-chained ledger, rollback | Same (parity) |
| **Governance across CPSEs** | Not found: a code spanning CPSEs is approved by the reviewing team only | **Every participating CPSE consents; declines are recorded (SF-11)** |
| **Rule changes** | Not found: rules change without a preview of their effect on past decisions | **Impact preview + golden-test gate before activation (SF-6)**; change notices per CPSE (SF-12, P1) |
| Deployment | Offline / air-gapped in several; one egress guard | Air-gap proof with a live counter (parity) |

**Wording rules (use them in the PPT and on stage)**
- Say: "a governed national registry", "every CPSE consents to its own codes", "you see a rule change's consequences before it happens", "false merges k of n with a bound", "numbers we can reproduce".
- Do **not** say: "first", "only", "novel algorithm", "beats SAP / Verdantis / other teams", "no other team does X". If needed: "we did not find this in the 41 public SIH26099 repositories we inspected on 3 Oct 2026".
- If asked "what is unique?", answer with the three governance things you can **show**: multi-CPSE consent, rulebook impact preview, and the bounded safety number. Then show the parity set working well.
- Keep Slide 2 ("Innovation and uniqueness") of the idea PPT in sync with this list. The claims register is Appendix G.

### 1.11 Where each signature feature appears in the idea PPT

The companion dossier (v0.3, Part S) was updated to show the differentiators on the slides, not only in this PRD.

| Signature feature | Idea PPT slide | How it appears | Demo scene (15.1) |
|---|---|---|---|
| SF-11 Multi-CPSE consent | Slide 2 uniqueness table (first row); flowchart step 7 | "each CPSE whose code joins a national code must consent" | 2:15 |
| SF-6 Rulebook impact preview | Slide 2 uniqueness table; Slide 4 risk row | "see a rule change's effect on past decisions before it happens" | 3:05 |
| SF-1 Look-alike Guard | Slide 2 table; Slide 3 mock screen + red veto node in the flowchart | "lists pairs a text matcher would merge and names the one attribute that differs" | 0:30 |
| SF-2 Baseline scoreboard + SF-5 safety headline | Slide 2 table; Slide 3 validation bullet; Slide 4 risk row | "false merges *k* of *n* with a 95% bound, next to two text baselines" | 3:40 |
| SF-4 Cited decisions | Slide 2 table; flowchart step 2 | "every row names its rule and conversion (`4 IN = DN100`)" | 1:15 |
| SF-3 Ask, don't guess | Slide 2 table; flowchart loop from INSUFFICIENT_DATA | "reviewer supplies the value with its source → re-decided" | 2:15 *(opt.)* |
| SF-7 Air-gap proof | Slide 2 table; Slide 3 deploy row; Slide 5 sovereignty tile | "isolated network + live blocked-egress counter, Wi-Fi off on stage" | 4:25 |
| Substitutes linked, never merged (FR-612, P1; answers the PS's "functionally equivalent") | Slide 2 table; flowchart veto node | "one-way, engineer-approved (316 may replace 304, not the reverse)" | spoken at 1:50 if not built |
| G1 neutral registry (SF-9, SF-10) | Slide 2 table last row; Slide 5 procurement bullet | "one CNMC + crosswalk, open-source, on-prem" | 2:45 |

SF-3 is P1 in this PRD but appears on Slide 2 because it is the clearest expression of the INSUFFICIENT_DATA verdict; if it is not built, the demo still shows the verdict and its "what to ask for" reasons (FR-603, US-08).

### 1.12 PS compliance matrix (official SIH26099 text)

Every *Expected Solution* bullet of the PS, the requirements that answer it, where it is shown, and its priority. **No bullet is left at P1 or lower.**

| PS expected-solution bullet | SpecID answer | Requirements | Screen | Idea PPT | Pri |
|---|---|---|---|---|---|
| AI-based matching of material descriptions and specifications across CPSEs | NLP normalisation + attribute extraction; lexical (BM25) and semantic (MiniLM + FAISS) candidates; attribute-level decision with veto | FR-201–202, FR-301, FR-501–505, FR-601–611 | S4, S6 | Slides 2, 3 | P0 |
| Identification of duplicate, near-duplicate and equivalent materials | Four verdicts; `WITHIN_CPSE` and `CROSS_CPSE` runs; terminology map 1.13; Look-alike Guard and hidden twins | FR-505, FR-601–605, FR-1401–1403 | S5, S6, S13 | Slide 2 | P0 |
| Automated standardisation of material descriptions and technical attributes | Canonical spec per CNMC; 40-character SAP text and long description generated from the spec; unit and UoM harmonisation | FR-202, FR-205, FR-901, 9.8–9.9 | S6, S8 | Slide 2 | P0 |
| Intelligent classification and categorisation | Rules first, ML classifier (char n-gram, abstains when unsure) as fallback; class path group → category → subtype; UNSPSC commodity from a verified table | FR-402, FR-405 | S3, S8 | Slides 2, 3 | P0 |
| Generation / recommendation of a Common National Material Code | Non-significant CNMC with Luhn check digit, issued only after maker–checker approval | FR-901–902 | S8 | Slide 2 | P0 |
| Mapping of existing CPSE material codes to the common national code | Crosswalk row per legacy code, with UoM factor; unique active mapping | FR-903, FR-205 | S8 | Slide 2 | P0 |
| Legacy material code rationalisation and migration support | Per-CPSE migration pack: retain / block for new procurement / phase out when stock is zero, with survivor and UoM factor | FR-907, FR-904 | S8 | Slides 2, 3 | P0 |
| User validation and approval workflow for AI recommendations | Review queue, evidence card, maker–checker, needs-info, (P1) ask-don't-guess | FR-801–807, FR-1421–1423 | S5, S6 | Slide 2 | P0 |
| Dashboard for material master analytics and duplicate detection | Duplicate rate per CPSE and category, data quality, backlog, top clusters by value, demand aggregation across CPSEs | FR-1201, FR-1203 | S0 | Slides 2, 5 | P0 |
| Audit trail and governance for material master changes | Hash-chained audit log, versioned templates, role separation, rule impact preview (SF-6), **multi-CPSE consent (SF-11)** | FR-1301–1302, FR-401, FR-1451–1452 | S10, S12 | Slide 2 | P0 |
| Integration capability with SAP/ERP systems | SAP-field import preset, REST API with OpenAPI spec, search-before-create, SAP-style crosswalk and migration files; (P1) mock create-material screen | FR-1005, FR-1001–1004, FR-905, FR-907, FR-1471 | S2, S9, S14 | Slides 2, 3 | P0 |

**PS inputs.** The PS names *material codes, descriptions, specifications, technical parameters and historical procurement data*. The first four are covered by FR-101–102 and FR-301; procurement history is FR-107 (optional, because the decision on identity never depends on price or vendor).

**PS expected impact → where it is measured.** One Nation – One Common Material Code (CNMC registry, S8) · fewer duplicate codes (dashboard duplicate rate, S0) · better data quality (quality report S3, `spec_completeness`) · inventory visibility (dashboard demand panel; stock in the migration pack) · lower procurement cost through demand aggregation (FR-1203) · inter-CPSE identification (cross-CPSE clusters) · faster procurement and specification finalisation (search-before-create, S9) · data-driven decisions (exports) · common procurement and strategic sourcing (demand panel, pooling view SF-10). **None of these is claimed as a measured result**; the pilot KPIs (dossier B11) measure them.

### 1.13 Terminology map: PS words to SpecID verdicts

| PS term | SpecID meaning | How it is shown |
|---|---|---|
| Identical | Same specification **and** same manufacturer + MPN | `IDENTICAL` |
| Duplicate | Two records of one CPSE that are `IDENTICAL` or `EQUIVALENT` | `WITHIN_CPSE` run; dashboard "duplicates" |
| Near-duplicate | Records that are `EQUIVALENT` but worded differently, or that only differ by a flagged item (extended attribute stated on one side, unexplained token) | `EQUIVALENT` with flags → review; hidden twins on S13 |
| Functionally equivalent | Interchangeable **both ways**: same identity-critical specification, any make → `EQUIVALENT`, merged under one CNMC. Usable **one way only** (for example a 316 stainless item replacing a 304 one in the same dimensions) → **substitute candidate**, linked, never merged | `EQUIVALENT`; substitute link (FR-612) |
| Not equivalent | An identity-critical attribute differs | `NOT_EQUIVALENT` (veto) |
| *(not in the PS)* | Cannot be decided from the data | `INSUFFICIENT_DATA` with the attribute to ask for |


---

## 2. Users and roles

| Persona | Role in system | What they need |
|---|---|---|
| **Meera**, stores engineer | MAKER | Review proposals fast; see exactly which attribute matches, conflicts or is missing |
| **Arjun**, CPSE material steward | CHECKER | Final approval; confidence that nothing unsafe is merged; clear reasons |
| **Governance admin** (central council) | ADMIN | Own templates, dictionaries, thresholds, users; cannot review clusters (separation of duties) |
| **Integrator** (ERP team) | INTEGRATOR | A stable API for search-before-create and crosswalk lookup |
| **Auditor** | AUDITOR | Read-only trail; tamper check |
| **Procurement analyst** | MAKER (read) | Look up a CNMC and see every CPSE's legacy code (P1 demand view) |
| **Judge** (demo persona) | any | Understand the flow in five minutes (three if cut), offline |

**Permission matrix**

| Action | MAKER | CHECKER | ADMIN | AUDITOR | INTEGRATOR |
|---|---|---|---|---|---|
| Upload, map, ingest batches | ✔ | ✔ | ✔ | – | – |
| Start harmonisation / evaluation runs | ✔ | ✔ | ✔ | – | – |
| View clusters, pairs, evidence cards | ✔ | ✔ | ✔ | ✔ | – |
| Propose review decision | ✔ | – | – | – | – |
| Confirm / overturn a proposal | – | ✔ | – | – | – |
| Issue CNMC (after confirmation) | system | system | – | – | – |
| View registry and crosswalk | ✔ | ✔ | ✔ | ✔ | ✔ (API) |
| Search-before-create | ✔ | ✔ | ✔ | – | ✔ (API) |
| Edit templates, dictionaries, thresholds | – | – | ✔ | – | – |
| View audit log / verify chain | – | – | ✔ | ✔ | – |
| Manage users | – | – | ✔ | – | – |
| View Look-alike Guard, baselines, air-gap status | ✔ | ✔ | ✔ | ✔ | – |
| Supply a missing attribute (P1) | ✔ | ✔ | – | – | – |
| Preview a rulebook change (P0, SF-6) | – | – | ✔ | – | – |
| Unmerge a record from a CNMC (P1) | – | ✔ | – | – | – |

---

## 3. User stories

| ID | As a… | I want to… | So that… | Pri | FRs |
|---|---|---|---|---|---|
| US-01 | Maker | upload a CPSE CSV and map its columns with suggestions | data enters without code changes | P0 | FR-101–103 |
| US-02 | Maker | see a data-quality report before running | I know what will be undecidable and why | P0 | FR-103 |
| US-03 | Maker | run harmonisation across CPSEs and watch progress | I know when results are ready | P0 | FR-505, FR-507 |
| US-04 | Maker | open a review queue sorted by priority and filter it | I review the most valuable clusters first | P0 | FR-801 |
| US-05 | Maker | open a cluster and see records side by side with an attribute-by-attribute evidence card | I can judge in seconds | P0 | FR-802, 609 |
| US-06 | Maker | propose approve / reject / split / needs-info with a comment | my judgement is recorded | P0 | FR-803 |
| US-07 | Checker | confirm or overturn a proposal, and be blocked from confirming my own | maker–checker holds | P0 | FR-803 |
| US-08 | Checker | see why a pair is INSUFFICIENT_DATA and what to ask for | I can request the missing attribute | P0 | FR-603 |
| US-09 | Checker | bulk-approve non-critical, flag-free clusters with a forced random sample for review | routine items do not clog the queue | P1 | FR-807 |
| US-10 | Admin | view templates with their golden tests (edit in P1) | rules are transparent and governed | P0/P1 | FR-401, 403, 404 |
| US-11 | Admin | set target precision and thresholds | the auto-eligible policy is explicit | P1 | FR-608 |
| US-12 | Integrator | send a free-text description and get candidates and a recommended action in ≤ 1 s | duplicates are stopped at creation | P0 | FR-1001–1003 |
| US-13 | Integrator | export the crosswalk as CSV/JSON/SAP-style | legacy systems can be updated | P0/P1 | FR-905 |
| US-14 | Procurement analyst | look up a CNMC and see all CPSE legacy codes | demand can be aggregated | P1 | FR-906, 1201 |
| US-15 | Auditor | read the audit log and verify the hash chain | tampering is detectable | P0 | FR-1302 |
| US-16 | Any user | see at all times that data is SYNTHETIC | no one mistakes demo data for real | P0 | FR-106, 1103 |
| US-17 | Team | generate seeded synthetic data and run evaluation reproducibly | results can be re-created | P0 | FR-1101–1102 |
| US-18 | Team | see false-merge count with confidence bound and abstention rate | safety is quantified honestly | P0 | FR-1102, 1104 |
| US-19 | Maker | reject a cluster and have the system remember it as cannot-link | the same mistake is not proposed again | P1 | FR-805 |
| US-20 | Admin | review unknown tokens from a batch | the abbreviation dictionary grows safely | P1 | FR-204 |
| US-21 | Judge | watch the demo offline | the idea is clear even without internet | P0 | NFR-05, section 15 |
| US-22 | Judge / Maker | see pairs that a text-only matcher would merge but SpecID vetoed, with the differing attribute | I understand the risk SpecID removes | P0 | FR-1401–1403 |
| US-23 | Judge / Team | see text-only and text + numbers baselines next to SpecID on the same run | the comparison is fair and visible | P0 | FR-1411–1413 |
| US-24 | Maker | supply a missing attribute with a source note and see the pair re-decided | undecidable pairs get resolved safely | P1 | FR-1421–1423 |
| US-25 | Checker / Auditor | see which rule and which conversion produced each comparison | I can audit a decision in seconds | P0 | FR-1431–1432 |
| US-26 | Admin | preview how a template change would alter stored verdicts before activating it | rule changes do not cause silent regressions across CPSEs | P0 | FR-403–404, FR-1451–1452 |
| US-27 | Judge / Integrator | verify that the prototype is air-gapped | data sovereignty is demonstrated, not claimed | P0 | FR-1461–1463 |
| US-28 | Integrator / Judge | try a mock create-material form that warns of duplicates as I type | I see prevention in an ERP-like context | P1 | FR-1471 |
| US-29 | Checker | unmerge a record from a CNMC with a reason | merges are reversible and auditable | P1 | FR-1481–1482 |
| US-30 | Procurement analyst | see CNMCs held by several CPSEs with combined annual value | joint-buying candidates are visible | P1 | FR-1491 |
| US-31 | CPSE steward (CHECKER of a participating CPSE) | consent to or decline a national code that would absorb my CPSE's legacy codes | no other organisation changes my master data without my agreement | P0 | FR-1501–1504 |
| US-32 | CPSE steward | receive a notice listing my legacy codes affected by a registry or rule change, with a delta migration file | my ERP team can act and acknowledge | P1 | FR-1511–1513 |

---

## 4. Functional requirements

Priorities: **P0** finale must · **P1** should · **P2** could. "AC" = acceptance criterion. Terms such as *core*, *extended*, *verdict* and *route* are defined in section 9.

### M1. Ingestion and mapping

| ID | Requirement | Pri | Acceptance criterion |
|---|---|---|---|
| FR-101 | Upload CSV or XLSX (≤ 50 MB, ≤ 200k rows) per CPSE; detect encoding (UTF-8, Latin-1, Windows-1252) | P0 | Bundled files upload; row count shown; a Latin-1 sample shows no garbled characters |
| FR-102 | Column-mapping wizard with suggestions from header synonyms. Required: `legacy_code` and at least one of `short_text` / `long_text`. Optional: `uom`, `mat_group`, `manufacturer`, `mpn`, `plant`, `criticality`, `annual_value` | P0 | Mapping saved per CPSE and pre-applied next time; missing required field blocks ingest |
| FR-103 | Data-quality report per batch: field completeness, duplicate legacy codes, empty descriptions, short text > 40 chars, share of records per recognised category, share with all core attributes parsed | P0 | Shown before any run; numbers reconcile with a SQL count |
| FR-104 | Sensitive-field filter: configured columns dropped or hashed at ingest. Price and vendor from procurement history (FR-107) stay inside the owning CPSE's scope; cross-CPSE screens show aggregates only | P1 | Filtered columns never reach the database; no cross-CPSE screen shows another CPSE's unit price or vendor |
| FR-105 | Idempotent re-ingest by (cpse, legacy_code, content hash) | P1 | Re-uploading a file creates no duplicates |
| FR-106 | Batch flag `is_synthetic`; SYNTHETIC badge on every page showing data from such a batch | P0 | Badge visible on all screens in section 11 |
| FR-107 | Optional **procurement-history** upload per CPSE (`legacy_code, po_date, qty, uom, unit_price, vendor, plant`; vendor hashed at ingest), aggregated per record into annual quantity, annual value, last price and number of vendors. Used for review priority, the dashboard demand panel and the migration pack; **never used to decide identity** | P0 | Aggregates reconcile with SQL; a run without the file still works (priority falls back to 1) |

### M2. Normalisation

| ID | Requirement | Pri | Acceptance criterion |
|---|---|---|---|
| FR-201 | Deterministic, idempotent normaliser (reference: Appendix C `normalise`) | P0 | `normalise(normalise(x)) == normalise(x)` on all test strings |
| FR-202 | Canonicalise size, class, schedule and units: inch / NB / DN → DN (table B.1); `150#`, `CLASS 150`, `CL 150` → `CL150`; `STD` / `XS` mapped to a schedule **only** within the size limits in B.2; HP → kW | P0 | One unit test per rule; non-standard sizes yield *unknown*, never a guess |
| FR-203 | Admin-editable abbreviation dictionary, versioned | P1 | A change creates a new version; each run stores the version used |
| FR-204 | Unknown-token miner: most frequent tokens not consumed by any extractor, per batch | P1 | Admin sees tokens with counts and example descriptions |
| FR-205 | **UoM harmonisation:** versioned alias table (`EA` ← EA, NO, NOS, PC, PCS, EACH; `M` ← M, MTR, METRE, METER; `KG` ← KG, KGS; `L` ← L, LTR; `SET`). Ambiguous codes (for example `MT`, metre or metric tonne) are flagged, never guessed. A UoM difference never vetoes identity; the crosswalk stores each CPSE's UoM and the factor to the CNMC base UoM (for example pipe in M vs EA of 6 m needs a reviewer-supplied factor) | P0 | Unit test per alias; `MT` is flagged; crosswalk export carries `uom` and `uom_factor` |

### M3. Attribute extraction

| ID | Requirement | Pri | Acceptance criterion |
|---|---|---|---|
| FR-301 | Tier-1 rule extractors for VALVE, PIPE, FLANGE, FASTENER, MOTOR (reference: Appendix C) | P0 | All golden strings parse to the expected attributes |
| FR-302 | Each attribute stored with value, source tier, confidence (rules = 1.0) | P0 | `spec_record.attr_meta` populated |
| FR-303 | Keep residual tokens per record; compare *technical* residual (digits or watch-list words) across a pair | P0 | A pair differing only by `NACE` is flagged and routed to REVIEW |
| FR-304 | GASKET template and extractor | P1 | Both gasket golden pairs pass |
| FR-305 | Tier-2 spaCy NER trained on silver labels, used only where Tier 1 left a core attribute empty | P2 | Tier-2 values never override Tier-1; confidence < 1 |
| FR-306 | Tier-3 local LLM extractor, JSON-schema constrained, **off by default** | P2 | Off: no network or GPU call; on: invalid JSON is rejected |
| FR-307 | Unrecognised category → `INSUFFICIENT_DATA`, never guessed | P0 | Golden case `SOMETHING ELSE 123` |

### M4. Templates and classification

| ID | Requirement | Pri | Acceptance criterion |
|---|---|---|---|
| FR-401 | Versioned templates (schema in Appendix A): core, extended, tolerant, make, critical default, value domains, aliases, rules | P0 | Loaded at startup; each run stores template versions |
| FR-402 | Category classification: **rules first** (category words); where no rule fires, an **ML classifier** (char n-gram TF-IDF + logistic regression, trained on the synthetic train split) proposes a category and **abstains** below a probability threshold (default 0.80 **[T]**), which gives `INSUFFICIENT_DATA` | P0 | All golden strings classified by rules; on validation records with the category word removed, accuracy and abstention rate reported; a CABLE probe abstains (E-5) |
| FR-403 | Template editor: view (P0); **create a DRAFT version by editing the template YAML as text (P0)**, structured form editor (P1) | P0 | A DRAFT cannot be used in a run |
| FR-404 | Golden tests attached to each template; activation blocked unless they pass | P0 | A failing test blocks activation and shows a readable diff |
| FR-405 | **Class path and UNSPSC:** each CNMC carries `class_path` (group → category → subtype, for example PIPING → VALVE → GATE) and an optional UNSPSC commodity code from a mapping table that the team fills **only from the official UNSPSC browser** (no code is written from memory); unverified entries stay empty | P0 | S8 shows the class path; every UNSPSC code in the table has a source note |

### M5. Candidate generation and runs

| ID | Requirement | Pri | Acceptance criterion |
|---|---|---|---|
| FR-501 | Blocking by **(category, DN)**. Pressure class is deliberately **not** a blocking key, so rating near-misses (CL150 vs CL300) become candidates and are vetoed visibly (TRD TD-03) | P0 | Pair completeness vs synthetic ground truth is displayed (target ≥ 0.98 **[T]**); hard negatives not reached by any channel are counted |
| FR-502 | Records with unknown blocking keys are matched through BM25 top-k (k = 20, configurable) within category | P0 | Records without size still receive candidates |
| FR-503 | Dense channel: MiniLM embeddings + FAISS top-k over normalised text | P0 | Switchable per run; works offline with a pre-downloaded model |
| FR-504 | Exact MPN + manufacturer match adds candidate pairs | P0 | Same MPN across CPSEs always becomes a candidate |
| FR-505 | Run modes `CROSS_CPSE`, `WITHIN_CPSE`, `BOTH` | P0 | In `CROSS_CPSE` no pair has both records in one CPSE |
| FR-506 | In evaluation runs, compute pair completeness and reduction ratio vs ground truth | P0 | Values appear in the evaluation report |
| FR-507 | Run console: start (batches, mode, options), progress, stats, cancel. Run statuses `QUEUED`, `RUNNING`, `CANCELLING`, `CANCELLED`, `DONE`, `FAILED` | P0 | Progress refreshes at least every 2 s; cancel stops within 10 s |

### M6. Equivalence engine

| ID | Requirement | Pri | Acceptance criterion |
|---|---|---|---|
| FR-601 | Per-attribute statuses `MATCH`, `PARTIAL`, `CONFLICT`, `MISSING_ONE`, `MISSING_BOTH` (section 9.5) | P0 | Unit tests per status |
| FR-602 | **Veto:** any `CONFLICT` on a core or extended attribute → `NOT_EQUIVALENT`; no score or LLM output can change it | P0 | Property test T-P1 |
| FR-603 | **Unknown-state:** a core attribute `PARTIAL` or missing → `INSUFFICIENT_DATA`, with reasons naming the attributes | P0 | Golden cases for generic-vs-specific material and missing face |
| FR-604 | `IDENTICAL` vs `EQUIVALENT` decided by equal MPN and manufacturer (case-insensitive) | P0 | Unit test |
| FR-605 | Routing: `AUTO_ELIGIBLE` only if no flags **and** class non-critical; otherwise `REVIEW` | P0 | Golden route cases |
| FR-606 | Residual-token guard (see FR-303) | P0 | As FR-303 |
| FR-607 | Heuristic confidence `p_rule` (9.6) labelled "confidence (heuristic)"; P1 calibrated probability replaces it | P0 / P1 | Label differs by mode |
| FR-608 | Threshold selection: smallest τ_auto whose Wilson lower bound of precision on the validation split ≥ P\* (default 0.99). A 0.99 bound needs about 380 error-free pairs above τ, so require ≥ 400; otherwise auto-eligibility stays off | P1 | Report shows τ_auto, bound and count |
| FR-609 | Evidence card JSON for every decision (section 9.10), **including rule IDs and conversion notes (FR-1431)** | P0 | Schema validated in API tests; every row has `rule` |
| FR-610 | Local LLM advisor for the uncertain band; output displayed and logged only | P2 | Verdict and route unchanged by the advisor in all tests |
| FR-611 | Symmetry: `decide(a, b)` and `decide(b, a)` return the same verdict | P0 | Property test T-P3 |
| FR-612 | **Substitute candidates (functional equivalence, one way):** a template may define SME-approved substitution rules (attribute, direction, conditions), for example a 316-family material may replace a 304-family one with all other core attributes equal. A `NOT_EQUIVALENT` pair whose every conflict is covered by such a rule is stored as `B may substitute A`. Substitutes are **never clustered or merged**, need an engineer's approval with a reason, and appear on the CNMC page. Rule sets are **empty by default**: for example a CL300 gate valve is *not* a drop-in for CL150 because face-to-face length and flange drilling differ | P1 | Unit test: a covered conflict gives a one-way link; an uncovered conflict gives none; clustering ignores substitute links |

### M7. Clustering

| ID | Requirement | Pri | Acceptance criterion |
|---|---|---|---|
| FR-701 | Constrained agglomerative clustering (9.7): never join two groups if any member pair would be `NOT_EQUIVALENT` | P0 | Property test T-P2 |
| FR-702 | Priority = (sum of `annual_value`, or 1) × (1 + 0.5 × number of flags); cohesion = mean pair confidence | P0 | Queue ordering test |
| FR-703 | When a conflict blocks a join, store the blocked edge so the reviewer sees "why not merged" | P1 | Visible in cluster view |

### M8. Review and governance

| ID | Requirement | Pri | Acceptance criterion |
|---|---|---|---|
| FR-801 | Review queue with filters (category, CPSE, flags, verdict mix, critical) sorted by priority | P0 | Queue for the 3k-record demo run loads in ≤ 2 s |
| FR-802 | Cluster view per wireframe S6 (side-by-side records, evidence card, proposed CNMC text) | P0 | Matches section 11 |
| FR-803 | Maker–checker: MAKER proposes; CHECKER confirms or overturns; the same user cannot do both steps on a cluster (HTTP 403) | P0 | API test |
| FR-804 | Keyboard shortcuts (A / R / S / N, J / K, ?) | P1 | Shortcut help overlay |
| FR-805 | Reject stores *cannot-link* pairs applied in later runs | P1 | A rejected pair is not re-proposed |
| FR-806 | Export approved and rejected decisions as labelled pairs (JSONL) for retraining | P1 | File validates against a schema |
| FR-807 | Bulk approve for `AUTO_ELIGIBLE` clusters of non-critical classes; the system forces a random 10% sample into manual review | P1 | Sample rate configurable and logged |

### M9. Registry and crosswalk

| ID | Requirement | Pri | Acceptance criterion |
|---|---|---|---|
| FR-901 | On final approval, issue a CNMC with canonical spec, 40-char short description and long description (9.9) | P0 | Short text ≤ 40 chars, or flagged for manual abbreviation |
| FR-902 | CNMC format `NMC-` + 10-digit sequence + Luhn check digit; sequence from a DB sequence | P0 | Tests T-C |
| FR-903 | One crosswalk row per member record; unique (cpse, legacy_code) | P0 | Mapping a legacy code twice fails with a clear message |
| FR-904 | `MERGED` / `DEPRECATED` lifecycle with pointer to the survivor; never delete | P1 | History preserved |
| FR-905 | Export crosswalk as CSV, JSON and **SAP-style CSV** (legacy code, CNMC, 40-char description, UoM, UoM factor) | P0 | Round-trip test |
| FR-906 | CNMC detail page: canonical spec, members, history from the audit log | P0 | Matches section 11 |
| FR-907 | **Migration pack per CPSE** (rationalisation support): one CSV per CPSE with legacy code and description, CNMC and its short text, relation, survivor flag, **recommended action** (`RETAIN` for the survivor · `BLOCK_FOR_NEW_PROCUREMENT` · `PHASE_OUT_WHEN_STOCK_ZERO`), UoM factor, and stock / open orders when known. Actions are recommendations; the CPSE applies them through its own master-data process (in SAP typically a material status such as cross-plant status MARA-MSTAE; confirm with the CPSE SAP team) | P0 | One file per CPSE; every active crosswalk row appears once; exactly one `RETAIN` per CNMC per CPSE |

### M10. Search-before-create

| ID | Requirement | Pri | Acceptance criterion |
|---|---|---|---|
| FR-1001 | `POST /search-before-create`: parse query, retrieve candidates from the registry, run `decide`, return sorted candidates with evidence | P0 | Contract test; ≤ 1 s p95 on about 5k CNMCs **[T]** |
| FR-1002 | Response includes `would_create_duplicate`, `recommended_action`, and for `INSUFFICIENT_DATA` candidates the attributes to supply | P0 | Contract test |
| FR-1003 | Sandbox UI (S9) | P0 | Matches section 11 |
| FR-1004 | API-key auth for INTEGRATOR with rate limit (default 60 requests/min) | P1 | 429 beyond the limit |
| FR-1005 | **SAP/ERP integration preset:** a saved column mapping for SAP material-master extracts (MARA-MATNR → `legacy_code`, MAKT-MAKTX → `short_text`, long text from a READ_TEXT export → `long_text`, MARA-MEINS → `uom`, MARA-MATKL → `mat_group`, MARA-MFRNR → `manufacturer`, MARA-MFRPN → `mpn`, MARC-WERKS → `plant`); an OpenAPI document for all INTEGRATOR endpoints. Pilot step (documented, not built): call search-before-create from the CPSE's material-creation workflow; field names and the call point are confirmed with each CPSE's SAP team | P0 | A sample SAP-style extract ingests with no manual mapping; `/openapi.json` served |

### M11. Synthetic data and evaluation

| ID | Requirement | Pri | Acceptance criterion |
|---|---|---|---|
| FR-1101 | Seeded generator (CLI and UI) per section 10.1 | P0 | Same seed + config → byte-identical files (hash check) |
| FR-1102 | Evaluation runner computing the metrics in 10.2, stored with config and seed | P0 | Report reproducible from the stored config |
| FR-1103 | SYNTHETIC badge, evidence-ladder panel, **honesty panel (FR-1442)** and the note "optimistic by construction" on the page and in exported reports | P0 | Visible; present in the exported MD/JSON |
| FR-1104 | Wilson intervals for proportions; rule-of-three bound when zero errors are observed | P0 | Unit tests on the formulas |
| FR-1105 | Ablation switches: text-only, + attributes, + veto, + calibrated/advisor | P1 | One table, one row per switch |
| FR-1106 | Style-holdout evaluation: one CPSE style written by a team member who has not seen the extractors | P1 | Reported separately from the development styles |
| FR-1107 | Public-benchmark adapter (Abt-Buy, Amazon-Google, Walmart-Amazon) in text-only mode | P2 | Runs on files downloaded by the user |

### M12. Dashboard

| ID | Requirement | Pri | Acceptance criterion |
|---|---|---|---|
| FR-1201 | **Analytics dashboard (S0)**: records per CPSE; duplicates within each CPSE and cross-CPSE equivalents (counts and share, by category); data-quality score per CPSE (completeness, parse rate); verdict mix; review backlog and throughput; top 10 clusters by annual value. Every figure is computed from a stored run and labelled with its run and SYNTHETIC badge | P0 | Numbers reconcile with SQL; badge visible |
| FR-1203 | **Demand aggregation panel** (P0-lite of SF-10): CNMCs held by ≥ 2 CPSEs with combined annual quantity and value from FR-107; CSV export. Shows aggregates only (FR-104) | P0 | Matches SQL aggregation; empty state explains that procurement history was not uploaded |
| FR-1202 | Impact calculator with inputs S, d (from run), a, c. **No default rupee values** | P2 | Empty until the user enters S |

### M13. Security and audit

| ID | Requirement | Pri | Acceptance criterion |
|---|---|---|---|
| FR-1301 | JWT login (8 h expiry), bcrypt password hashes, RBAC per section 2 | P0 | API tests per role |
| FR-1302 | Append-only audit event for every state-changing action; `hash = SHA-256(prev_hash ‖ canonical JSON of the event)`; `GET /audit/verify` recomputes the chain | P0 | Editing any row makes verify fail |
| FR-1303 | Offline mode: no outbound network calls at runtime (embedding model and LLM local) | P0 | Test with the network disabled |
| FR-1304 | Secrets from environment; demo users documented only in `.env.example` | P0 | No secrets in the repo |


### M14. Signature features (the differentiators, section 1.8)

| ID | SF | Requirement | Pri | Acceptance criterion |
|---|---|---|---|---|
| FR-1401 | SF-1 | For every candidate pair store `text_sim` = token-set ratio of the **normalised** texts (0–1) and `lookalike` ∈ {`LOOKALIKE_VETOED`, `HIDDEN_TWIN`, none} per section 9.13.1 | P0 | Unit test T-S2; columns present in `pair_decision` |
| FR-1402 | SF-1 | Look-alike Guard screen S13 and APIs API-25 / API-26: ranked lists, each item with both texts, `text_sim`, verdict and the **decisive attribute** with its rule ID; chart of text similarity against verdict | P0 | For the bundled seeded run the list is non-empty and every `LOOKALIKE_VETOED` item has a `CONFLICT` row |
| FR-1403 | SF-1 | Thresholds `lookalike_min_sim` (default 0.85) and `hidden_twin_max_sim` (default 0.75) are run options; defaults are **[T]** and are tuned on the validation split only | P0 | Values stored in the run config |
| FR-1411 | SF-2 | Evaluation runs compute two text-only baselines on the **same candidate pairs and split**: B1 (token-set ≥ τ1) and B2 (token-set ≥ τ2 **and** equal numeric tokens), per section 10.2b | P0 | Unit test T-S1 on a tiny fixture |
| FR-1412 | SF-2 | Baseline scoreboard (S11 tab): false merges on hard negatives, equivalents found, coverage, and the disagreement table (merged by B1 but vetoed by SpecID, found by SpecID but missed by B1 / B2) | P0 | Matches the example in section 8 |
| FR-1413 | SF-2 | **Fairness rules:** τ1 and τ2 are tuned on the validation split only; both baselines are always shown, even if one looks bad for SpecID on a metric; the page states that the baselines are simple and are not state-of-the-art matchers | P0 | Text present; τ tuned-on field = `validation` |
| FR-1421 | SF-3 | `POST /records/{id}/supply-attribute` stores the value with a mandatory `source_note` in `attribute_supply`, marks it `supplied by user` in the spec, re-decides all pairs of that record in the run, and writes an audit event in the same transaction | P1 | Unit test T-S3; response lists changed verdicts |
| FR-1422 | SF-3 | In S6, each `INSUFFICIENT_DATA` row has an inline "supply value" control; after saving, the evidence card refreshes | P1 | Demo scene works |
| FR-1423 | SF-3 | Supplied values carry a visible badge and are never merged silently with extracted values; a supplied value can still produce `CONFLICT` | P1 | Test: conflicting supply gives `NOT_EQUIVALENT` |
| FR-1431 | SF-4 | Every evidence row carries `rule` (ID such as `VALVE.pressure_class`), `rule_text`, and `note_a` / `note_b` for conversions and inferences (`4 IN = DN100`, `WCB -> A216-WCB`, `STD = SCH40 (DN150 <= 250)`, `implied by A106`) | P0 | Unit test T-S6 |
| FR-1432 | SF-4 | `rule_text` comes from the template (`rule_text` map, Appendix A); S6 shows it in a popover; clicking opens the template in S10 | P0 | Rule text in the UI equals the YAML text |
| FR-1441 | SF-5 | Evaluation headline is **false merges k of n hard negatives with the 95% upper bound**, then abstentions (justified and other) and coverage; precision and F1 are secondary | P0 | Matches wireframe S11 |
| FR-1442 | SF-5 | **Honesty panel** on S11 and in exports: "synthetic and optimistic by construction"; what the numbers do not mean; evidence ladder; the style-holdout and adversarial results shown separately; known weaknesses listed (extraction misses, abstentions) | P0 | Text present in UI and in the exported MD |
| FR-1443 | SF-5 | Every exported report repeats the headline, the label and the git commit | P0 | Export test |
| FR-1451 | SF-6 | `POST /templates/{id}/versions/{v}/impact-preview` re-decides the stored pairs of a chosen run under a DRAFT template and returns the pairs whose verdict or route would change | P0 | Unit test T-S4; counts shown in S10 |
| FR-1452 | SF-6 | Activation requires: golden tests pass **and** the ADMIN acknowledges the impact summary; both are written to the audit log | P0 | Activation blocked otherwise |
| FR-1461 | SF-7 | **Egress guard:** a socket-level guard in the API process blocks every connection except loopback and the configured database host, and counts blocked attempts | P0 | Unit test T-S5 |
| FR-1462 | SF-7 | The Compose network of `api` and `db` is `internal: true` (no route to the internet); the demo includes `docker network inspect` showing it | P0 | Compose file reviewed; check in checklist 13.4 |
| FR-1463 | SF-7 | `GET /system/airgap` returns mode, network setting and `blocked_egress_attempts`; the footer of every page shows "Air-gapped · blocked attempts: n" (grey "Air-gap status unavailable" when the endpoint cannot be read) | P0 | Footer visible; counter is 0 after the demo path |
| FR-1471 | SF-8 | S14 "Create material (mock ERP)": description field with live search-before-create (debounce 300 ms), 40-character counter, warning banner on `USE_EXISTING`, and a button that fills the SpecID 40-character description | P1 | Demo scene works |
| FR-1481 | SF-9 | `POST /cnmc/{cnmc}/unmerge` marks the crosswalk row `REMOVED` with mandatory reason, removes the record from the CNMC, writes an audit event; the unique-active-mapping index frees the legacy code | P1 | Test: legacy code can be re-mapped after unmerge |
| FR-1482 | SF-9 | CNMC history (S8) lists merges and unmerges with actor and reason | P1 | Visible |
| FR-1491 | SF-10 | S15 lists CNMCs with crosswalk rows from ≥ 2 CPSEs, sorted by combined `annual_value`; CSV export; SYNTHETIC DATA badge when applicable | P1 | Matches SQL aggregation |
| FR-1501 | SF-11 | A cluster whose members come from **more than one CPSE** reaches CNMC issuance only after a **consent** is recorded for every participating CPSE. The maker's proposal counts as consent for the maker's CPSE and the checker's confirmation for the checker's CPSE; every other participating CPSE needs a consent from one of its own CHECKER users | P0 | Unit test: 3-CPSE cluster with maker in A and checker in B stays `AWAITING_CONSENT` until a CPSE-C checker consents; issuance happens in that transaction |
| FR-1502 | SF-11 | A steward may **decline** with a mandatory reason. The CNMC is then issued for the remaining CPSEs (if ≥ 2 records remain) and the declined CPSE's records stay unmapped; the decline is stored as a *dissent* and listed on the dashboard; the same pair is not re-proposed to that CPSE without a new rule version or a new attribute | P0 | Test: decline by CPSE-C → CNMC maps only A and B records; dissent row exists; audit event written |
| FR-1503 | SF-11 | **Consent queue** (S18) for each steward: clusters waiting for their CPSE, with the evidence card, the records of their CPSE highlighted, and Consent / Decline actions | P0 | Demo scene works with three browser profiles |
| FR-1504 | SF-11 | Consent rules are configurable per deployment (`consent_mode`: `ALL_PARTICIPANTS` default, `NONE` for single-CPSE pilots); the active mode is shown in the footer and stored in each issuance's audit event | P0 | Mode visible; audit payload contains it |
| FR-1511 | SF-12 | Every issuance, merge, unmerge, decline and template activation creates one **change notice per affected CPSE** listing its affected legacy codes, the CNMC and the recommended migration action | P1 | Test: unmerge creates exactly one notice for the owning CPSE |
| FR-1512 | SF-12 | **Change-notice inbox** (S19) per CPSE with acknowledge action and a **delta migration file** (only rows that changed since the last acknowledged notice) | P1 | Delta file contains only changed rows |
| FR-1513 | SF-12 | Template activation (FR-1452) attaches the impact-preview result to the notices of the CPSEs whose mapped codes are affected | P1 | Notice shows the transition counts |

---

## 5. Non-functional requirements

| ID | Area | Requirement | Target | How verified |
|---|---|---|---|---|
| NFR-01 | Performance | Harmonise about 3,000 records (3 CPSEs) end to end (DEC-09) | ≤ 10 min on 8-core / 16 GB CPU, Docker default memory (`api` 4 GB, `db` 1 GB limits) **[T]** | Timed run in CI-like environment |
| NFR-01b | Performance | Search-before-create latency | p95 ≤ 1 s with about 5k CNMCs **[T]** | Load script |
| NFR-01c | Performance | List views | ≤ 200 ms server time for 100 rows **[T]** | API timing logs |
| NFR-02 | Determinism | Same seed and config give identical outputs (excluding timestamps and UUIDs) | exact | Hash comparison |
| NFR-03 | Explainability | Every verdict has an evidence card and at least one reason code | 100% | Schema test |
| NFR-04 | Safety | No code path lets a score or LLM output override a veto | 0 exceptions | Property test T-P1, code review |
| NFR-05 | Offline / air-gap | Runs with no internet after setup; embedding model pre-downloaded; **proven** by the egress guard (FR-1461) and the internal Compose network (FR-1462) | works; blocked-egress counter = 0 on the demo path | Network-off test; unit test T-S5 |
| NFR-06 | Portability | `docker compose up` works on Linux, macOS, Windows (WSL2) | works | Smoke test on two OSes |
| NFR-07 | Security | RBAC enforced server-side; bcrypt; CORS restricted; audit tamper-evidence | as stated | API tests |
| NFR-08 | Maintainability | Type hints, ruff + black, ≥ 70% line coverage on `core/` **[T]** | CI gate | Coverage report |
| NFR-09 | Usability | Review in ≤ 3 interactions; verdicts shown by **colour + icon + text** (not colour alone) | as stated | Heuristic walkthrough |
| NFR-10 | Data hygiene | Demo data synthetic only; any real CPSE data stays out of the repo and logs | 0 real rows in repo | Repo scan |
| NFR-11 | Observability | Structured JSON logs, `/health`, run stats | present | Manual check |
| NFR-12 | Evaluation integrity | Every metric shown carries its data source label and evidence level | 100% | UI review |
| NFR-13 | Baseline fairness | Baseline thresholds tuned on validation only; both baselines always shown; same candidates and split as SpecID | as stated | Review of the eval runner; FR-1413 |
| NFR-14 | Claims discipline | No slide, screen or export says "first", "only" or "best"; comparisons are limited to the two built-in baselines | 0 occurrences | Text search before the demo |

---

## 6. System architecture

### 6.1 Components (MVP)

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Browser: React 18 + TypeScript + Vite + Tailwind + TanStack Query          │
│ Upload · Review · Registry · Search-before-create · Evaluation · Audit     │
└───────────────────────────────────┬────────────────────────────────────────┘
                                    │ HTTPS, JSON (JWT)
┌───────────────────────────────────▼────────────────────────────────────────┐
│ FastAPI app (Python 3.11)                                                  │
│  api/       routers · auth · RBAC · validation (Pydantic)                  │
│  core/      normalise · extract · templates · decide · cluster · cnmc      │
│  services/  ingest · harmonise · registry · search · audit · eval          │
│  jobs       ProcessPoolExecutor (no Celery in the MVP)                     │
└───────────────┬─────────────────────────────────────┬──────────────────────┘
                │ SQL                                 │ in-process / local
┌───────────────▼──────────────┐     ┌────────────────▼──────────────────────┐
│ PostgreSQL 16                │     │ Optional (P1/P2), all local           │
│ records · specs · pairs ·    │     │ MiniLM+FAISS · LightGBM · Ollama LLM  │
│ clusters · CNMC · crosswalk  │     └───────────────────────────────────────┘
│ audit hash chain             │
└──────────────────────────────┘
```

**Air-gap (SF-7).** `api` and `db` sit on a Compose network with `internal: true` (no route out). `web` (nginx: static files + reverse proxy) is attached to both that network and a default network that publishes one port to localhost, and never initiates outbound traffic. Inside the API process an **egress guard** refuses every connection and name lookup except loopback and the database host, and counts the attempts (section 9.13.7).

### 6.2 MVP simplifications against the full design (dossier B3 / B7)

| Full design | MVP choice | Why |
|---|---|---|
| Celery / Prefect workers | FastAPI background task + `ProcessPoolExecutor` | One less service to break at 3 a.m. |
| pgvector / OpenSearch | FAISS in memory (**P0** dense channel, 1.6) and `rank_bm25`; vectors stored as `real[]` | No extension setup; enough for about 10k–50k records |
| Keycloak SSO | Local users + JWT + bcrypt | Offline demo |
| Kubernetes | Docker Compose (api, web, db; optional ollama) | Single-laptop demo |
| LightGBM + calibration | **P0 rule-based decision** + heuristic confidence; LightGBM in P1 | The rules already carry the safety logic; ML only improves ranking and thresholds |
| Local LLM extractor / advisor | P2, off by default | Flaky on venue hardware; never required for the demo |

### 6.3 Technology choices

| Layer | Choice |
|---|---|
| Backend | Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.0 + Alembic, uvicorn |
| Database | PostgreSQL 16 (Docker) using the schema in Appendix E |
| NLP and matching | rapidfuzz, rank_bm25; sentence-transformers `all-MiniLM-L6-v2` and `faiss-cpu` (**P0**; **pre-download the model**, see R-01; embedding batch size 64, DEC-09); spaCy (P2) |
| ML (P1) | LightGBM, scikit-learn (`IsotonicRegression`) |
| Optional LLM (P2) | Any local instruct model served by Ollama (e.g. an 8B-class model); JSON-schema constrained output |
| Frontend | React 18, TypeScript, Vite, Tailwind, TanStack Query, React Router, Recharts |
| Auth | PyJWT, **bcrypt** used directly (passlib is unmaintained and warns with bcrypt ≥ 4; TRD TD-04) |
| Tests | pytest, hypothesis, pytest-cov; vitest for UI utilities; Playwright (P2) |
| DevOps | Docker Compose, Makefile, GitHub Actions (lint + tests) |

### 6.4 Key sequences

**Harmonisation run**
1. `POST /runs` → run row `QUEUED` → background job starts.
2. For every record without a `spec_record`: normalise → classify → extract → store attributes, confidence, residual tokens.
3. Candidate generation (FR-501–505) → candidate pairs.
4. For each pair: `decide` → bulk-insert `pair_decision` (COPY or `executemany`, never row by row).
5. Constrained clustering (9.7) → `cluster`, `cluster_member`, `review_task`.
6. Update run stats, write an audit event, set status `DONE`.

**Search-before-create**
1. `POST /search-before-create` with free text (+ optional UoM, MPN, CPSE).
2. Normalise and extract the query; if the category is unknown → return `INSUFFICIENT_DATA` with "category not recognised".
3. Retrieve registry candidates: same category, DN and class when known, plus BM25 top-k on canonical text.
4. Run `decide(query, candidate)` for each; sort `IDENTICAL` → `EQUIVALENT` → `INSUFFICIENT_DATA` → `NOT_EQUIVALENT`.
5. Return candidates, `would_create_duplicate`, `recommended_action`, and for `INSUFFICIENT_DATA` the attributes the requester should add.

### 6.5 Failure handling and fallbacks

| Failure | Behaviour |
|---|---|
| Embedding model missing or blocked | Dense channel disabled; run continues with blocking + BM25; banner shows "dense channel off" |
| LLM unavailable or slow (> 5 s) | Advisor skipped; verdicts unaffected |
| Job crashes mid-run | Run marked `FAILED`; partial rows are tied to the run id and can be deleted; no registry changes happen inside a run |
| Template fails to load | Startup aborts with the failing file and line |

---

## 7. Data model

The authoritative DDL is in **doc 05 Backend Schema, Appendix A (schema v0.6: 26 tables, executed and constraint-tested on PostgreSQL 16)**. Appendix E of this PRD now only points there.

| Entity | Purpose | Key points |
|---|---|---|
| `cpse`, `app_user` | Organisations and users | Role check constraint: MAKER, CHECKER, ADMIN, AUDITOR, INTEGRATOR |
| `upload_batch` | One uploaded file | `is_synthetic` flag, saved column mapping, quality JSON |
| `material_record` | One ERP row | Unique per (cpse, legacy_code, batch); `raw` keeps the original row |
| `template` | Versioned category policy | Primary key (id, version); status DRAFT / ACTIVE / RETIRED |
| `spec_record` | Derived specification | `attrs` JSONB, `attr_meta` (tier, confidence), `residual` tokens, optional embedding |
| `run` | One harmonisation run | Config JSON, stats JSON, status |
| `pair_decision` | Verdict for a candidate pair | `rec_a < rec_b` check; unique per run; evidence JSONB; `text_sim`, `baseline` (B1/B2 flags) and `lookalike` class for SF-1 / SF-2 |
| `cluster`, `cluster_member` | Proposed groups | `needs_review`, `priority`, status PROPOSED / APPROVED / REJECTED / SPLIT |
| `review_task`, `review_decision` | Maker–checker workflow | Decision APPROVE / REJECT / SPLIT / NEEDS_INFO with role |
| `cnmc` | National material code | `^NMC-[0-9]{11}$`, 40-char short description check, `merged_into` pointer |
| `crosswalk` | Legacy code → CNMC | Unique **active** (cpse_id, legacy_code) through a partial index; `status` ACTIVE / REMOVED with who, when, why (SF-9); relation IDENTICAL or EQUIVALENT; `uom`, `uom_factor`, `migration_action` (FR-905, FR-907) |
| `attribute_supply` | Values supplied by reviewers (SF-3) | record, attribute, value, mandatory source note, who, when |
| `review_consent` | One consent or decline per participating CPSE per review task (SF-11) | task, CPSE, user, decision CONSENT / DECLINE, reason |
| `change_notice` | Per-CPSE notices of registry and rule changes (SF-12) | CPSE, kind, object, summary, delta rows, acknowledged by / at |
| `cannot_link`, `blocked_edge` | Rejected pairs (FR-805) and why groups were not merged (FR-703) | |
| `dictionary`, `api_key`, `idempotency_key` | Versioned lookup tables (FR-203, FR-205, FR-405); integrator keys (FR-1004); repeat-safe POSTs | |
| `procurement_line` | Procurement history (FR-107) | record, date, quantity, UoM, unit price, hashed vendor, plant; aggregated per record |
| `substitution` | One-way substitute links (FR-612) | from record, to record, rule, status PROPOSED / APPROVED / REJECTED, approver, reason |
| `audit_event` | Hash-chained log | `prev_hash`, `hash`; append-only |
| `eval_run` | Evaluation runs | kind SYNTHETIC / PUBLIC / PILOT; seed; metrics JSON |

**Invariants to enforce in code and tests:** (1) a legacy code maps to at most one **active** CNMC; (2) a cluster never contains an identity-critical conflict; (3) no `cnmc` row without its crosswalk rows; (4) every state change has an audit event in the same transaction.

---

## 8. API specification

**Conventions:** base path `/api/v1` · JSON · `Authorization: Bearer <jwt>` (INTEGRATOR may use `X-API-Key`) · cursor pagination (`limit`, `cursor`) · errors as RFC 7807 `application/problem+json` · timestamps in ISO 8601 UTC.

| ID | Method and path | Role | Purpose |
|---|---|---|---|
| API-01 | `POST /auth/login` | any | Returns `{access_token, role}` |
| API-02 | `GET /me` | any | Current user and role |
| API-03 | `POST /batches` (multipart: file, cpse_id, is_synthetic) | MAKER+ | Upload; returns `batch_id`, columns, suggested mapping |
| API-04 | `PUT /batches/{id}/mapping` | MAKER+ | Save column mapping |
| API-05 | `POST /batches/{id}/ingest` | MAKER+ | Start ingest (202); idempotent |
| API-06 | `GET /batches/{id}` and `/batches/{id}/quality` | MAKER+ | Status and data-quality report |
| API-07 | `POST /runs` `{batch_ids, mode, options}` | MAKER+ | Start harmonisation (202) |
| API-08 | `GET /runs/{id}` | MAKER+ | Status, progress, stats; `POST /runs/{id}/cancel` |
| API-09 | `GET /runs/{id}/pairs?verdict=&route=&category=` | MAKER+ | Pair decisions |
| API-10 | `GET /pairs/{id}` | MAKER+ | One evidence card |
| API-11 | `GET /clusters?run_id=&status=&category=&needs_review=&sort=priority` | MAKER+ | Review queue |
| API-12 | `GET /clusters/{id}` | MAKER+ | Members, evidence, blocked edges |
| API-13 | `POST /clusters/{id}/review` | MAKER / CHECKER | Maker proposes; checker confirms or overturns |
| API-14 | `POST /clusters/bulk-approve` (P1) | CHECKER | Bulk approve with forced sample |
| API-15 | `GET /cnmc`, `GET /cnmc/{cnmc}` | MAKER+, INTEGRATOR | Registry |
| API-16 | `POST /cnmc/{cnmc}/merge` (P1) | CHECKER | Merge into survivor |
| API-17 | `GET /crosswalk?cnmc=&cpse=&legacy_code=` | MAKER+, INTEGRATOR | Crosswalk lookup |
| API-18 | `GET /exports/crosswalk?format=csv\|json\|sap_csv` | MAKER+, INTEGRATOR | Export |
| API-19 | `POST /search-before-create` | MAKER+, INTEGRATOR | Duplicate check at creation |
| API-20 | `GET /templates`, `GET /templates/{id}` | any | Templates |
| API-21 | `POST /templates/{id}/versions`, `/versions/{v}/test`, `/versions/{v}/activate` (P1) | ADMIN | Template lifecycle |
| API-22 | `POST /eval/runs`, `GET /eval/runs/{id}`, `GET /eval/runs/{id}/report.md` | MAKER+ | Evaluation |
| API-23 | `GET /audit`, `GET /audit/verify` | ADMIN, AUDITOR | Audit trail and chain check |
| API-24 | `GET /health` | none | Liveness |
| API-25 | `GET /radar/lookalikes?run_id=&min_sim=&limit=` | MAKER+, AUDITOR | SF-1: pairs text similarity would merge but SpecID vetoed, with the decisive attribute |
| API-26 | `GET /radar/hidden-twins?run_id=&max_sim=&limit=` | MAKER+, AUDITOR | SF-1: different wording, same specification |
| API-27 | `GET /eval/runs/{id}/baselines` | MAKER+, AUDITOR | SF-2: B1, B2 and SpecID side by side, plus disagreements |
| API-28 | `POST /records/{id}/supply-attribute` (P1) | MAKER, CHECKER | SF-3: supply a missing attribute with a source note; returns changed verdicts |
| API-29 | `POST /templates/{id}/versions/{v}/impact-preview` | ADMIN | SF-6: which stored pairs would change under a draft template |
| API-30 | `POST /cnmc/{cnmc}/unmerge` (P1) | CHECKER | SF-9: remove a record from a CNMC with a reason |
| API-31 | `GET /pooling?min_cpses=2&sort=annual_value` (P1) | MAKER+ | SF-10: CNMCs held by several CPSEs |
| API-32 | `GET /system/airgap` | any | SF-7: mode, network setting, `blocked_egress_attempts` |
| API-33 | `POST /batches/{id}/procurement` | MAKER+ | FR-107: upload procurement history for a batch |
| API-34 | `GET /dashboard?run_id=` and `GET /dashboard/demand?min_cpses=2` | MAKER+ | FR-1201, FR-1203 |
| API-35 | `GET /exports/migration-pack?cpse=` | MAKER+, INTEGRATOR | FR-907 |
| API-36 | `GET /cnmc/{cnmc}/substitutes` (P1) | MAKER+ | FR-612 |
| API-37 | `GET /consents?cpse=` · `POST /clusters/{id}/consent` `{decision: CONSENT\|DECLINE, reason}` | CHECKER of a participating CPSE | SF-11: consent queue and action |
| API-38 | `GET /change-notices?cpse=` · `POST /change-notices/{id}/ack` · `GET /change-notices/{id}/delta.csv` (P1) | MAKER+, INTEGRATOR (read) | SF-12 |
| API-39 | `GET /users` (also returns `cpses` for the Add-user modal) · `POST /users` | ADMIN | S16: list and create users; MAKER and CHECKER need a CPSE (DEC-14) |
| API-40 | `POST /users/{id}/reset-password` | ADMIN | Sets `must_change_password`; audit `PASSWORD_RESET` |
| API-41 | `POST /users/{id}/disable` | ADMIN | Not one's own account; audit `USER_DISABLED` |
| API-42 | `POST /me/password` | any signed-in user | Self-service and forced change; audit `PASSWORD_CHANGED` (DEC-15) |

**Example: evidence card (`GET /pairs/{id}`)**. Generated by the reference code in Appendix C.

```json
{
 "verdict": "EQUIVALENT",
 "route": "REVIEW",
 "reasons": [
  "critical class: maker-checker"
 ],
 "evidence": [
  {
   "attr": "valve_type",
   "a": "GATE",
   "b": "GATE",
   "status": "MATCH",
   "rule": "VALVE.valve_type",
   "note_b": "GV = GATE"
  },
  {
   "attr": "size_dn",
   "a": 100,
   "b": 100,
   "status": "MATCH",
   "rule": "VALVE.size_dn",
   "note_a": "4 IN = DN100",
   "note_b": "100 NB = DN100"
  },
  {
   "attr": "pressure_class",
   "a": 150,
   "b": 150,
   "status": "MATCH",
   "rule": "VALVE.pressure_class"
  },
  {
   "attr": "body_material",
   "a": "A216-WCB",
   "b": "A216-WCB",
   "status": "MATCH",
   "rule": "VALVE.body_material",
   "note_b": "WCB -> A216-WCB"
  },
  {
   "attr": "end_connection",
   "a": "FLANGED-RF",
   "b": "FLANGED-RF",
   "status": "MATCH",
   "rule": "VALVE.end_connection"
  }
 ],
 "rule_text_examples": {
  "VALVE.size_dn": "Compared as DN; inch and NB converted by table B.1; non-standard sizes stay unknown",
  "VALVE.body_material": "Same family and same spec; generic vs specific is PARTIAL",
  "VALVE.end_connection": "FLANGED with no face is PARTIAL against a specific face"
 },
 "omitted": "rows with status MISSING_BOTH (design_standard, trim)"
}
```

**Example: `POST /search-before-create` response** (evidence trimmed for length; produced by the reference code; CNMC values are illustrative).

```json
{
 "query": {
  "text": "gate valve 4 inch class 150 ASTM A216 WCB flanged RF",
  "category": "VALVE",
  "parsed": {
   "valve_type": "GATE",
   "size_dn": 100,
   "pressure_class": 150,
   "body_material": "A216-WCB",
   "end_connection": "FLANGED-RF",
   "design_standard": null,
   "trim": null
  }
 },
 "would_create_duplicate": true,
 "recommended_action": "USE_EXISTING",
 "best_match": "NMC-00000001974",
 "candidates": [
  {
   "cnmc": "NMC-00000001974",
   "short_desc_40": "VLV GATE 4IN CL150 A216-WCB FLGD RF",
   "verdict": "EQUIVALENT",
   "reasons": [
    "critical class: maker-checker"
   ],
   "evidence": [
    {
     "attr": "valve_type",
     "a": "GATE",
     "b": "GATE",
     "status": "MATCH",
     "rule": "VALVE.valve_type"
    },
    {
     "attr": "size_dn",
     "a": 100,
     "b": 100,
     "status": "MATCH",
     "rule": "VALVE.size_dn",
     "note_a": "4 IN = DN100",
     "note_b": "4 IN = DN100"
    },
    {
     "attr": "pressure_class",
     "a": 150,
     "b": 150,
     "status": "MATCH",
     "rule": "VALVE.pressure_class"
    }
   ]
  },
  {
   "cnmc": "NMC-00000004127",
   "short_desc_40": "VLV GATE 4IN CL150 A216-WCB FLGD ?",
   "verdict": "INSUFFICIENT_DATA",
   "reasons": [
    "core attribute not verifiable: end_connection"
   ],
   "evidence": [
    {
     "attr": "end_connection",
     "a": "FLANGED-RF",
     "b": "FLANGED-?",
     "status": "PARTIAL",
     "rule": "VALVE.end_connection"
    }
   ]
  },
  {
   "cnmc": "NMC-00000003111",
   "short_desc_40": "VLV GATE 4IN CL300 A216-WCB FLGD RF",
   "verdict": "NOT_EQUIVALENT",
   "reasons": [
    "conflict: pressure_class"
   ],
   "evidence": [
    {
     "attr": "pressure_class",
     "a": 150,
     "b": 300,
     "status": "CONFLICT",
     "rule": "VALVE.pressure_class"
    }
   ]
  }
 ]
}
```

**Example: review decision** (`POST /clusters/{id}/review`, request then response)

```json
{
 "decision": "APPROVE",
 "comment": "Specs checked against vendor datasheet",
 "split_groups": null
}
```

```json
{
 "cluster_id": "3b1c0c5e-7e0f-4c8e-9a52-2f1d6a9a0c11",
 "task_state": "MADE",
 "next_step": "CHECKER_REQUIRED",
 "audit_event_id": 1042
}
```

**Example: error (RFC 7807)**

```json
{
 "type": "https://specid.local/problems/forbidden",
 "title": "Maker cannot also check",
 "status": 403,
 "detail": "The same user cannot perform both the MAKER and CHECKER step on one cluster."
}
```

**Example: evaluation run.** Metric values are `null` on purpose; they are computed at run time and never pre-filled.

```json
{
 "kind": "SYNTHETIC",
 "seed": 7,
 "label": "SYNTHETIC - optimistic by construction",
 "status": "DONE",
 "config": {
  "entities": 4000,
  "cpse_styles": [
   "A",
   "B",
   "C"
  ],
  "hard_negative_share": 0.3
 },
 "metrics": {
  "hard_negatives": null,
  "false_merges": null,
  "false_merge_upper_95": null,
  "auto_eligible_precision": null,
  "auto_eligible_precision_wilson_lb": null,
  "pair_completeness": null,
  "reduction_ratio": null,
  "abstention_rate": null,
  "bcubed_precision": null,
  "bcubed_recall": null
 },
 "note": "values are computed at run time; null here on purpose"
}
```

**Example: Look-alike Guard (`GET /radar/lookalikes` and `/hidden-twins`, combined).** Built by the reference code from the hand-built pairs of dossier A4.3; a real run lists its own pairs.

```json
{
 "run_id": "7d3f0b64-0a61-4d34-9d0e-6f6d2f1b8a10",
 "thresholds": {
  "lookalike_min_sim": 0.85,
  "hidden_twin_max_sim": 0.75
 },
 "source": "illustration built from the 12 hand-built pairs; a real run lists its own pairs",
 "lookalikes_vetoed": {
  "count": 6,
  "items": [
   {
    "text_a": "VALVE GATE 4IN CL150 A216 WCB FLGD RF",
    "text_b": "VALVE GATE 4IN CL300 A216 WCB FLGD RF",
    "text_sim": 0.95,
    "verdict": "NOT_EQUIVALENT",
    "class": "LOOKALIKE_VETOED",
    "decisive": {
     "attr": "pressure_class",
     "a": 150,
     "b": 300,
     "rule": "VALVE.pressure_class"
    }
   },
   {
    "text_a": "PIPE SMLS 6IN SCH40 A106 GR.B",
    "text_b": "PIPE SMLS 6IN SCH80 A106 GR.B",
    "text_sim": 0.97,
    "verdict": "NOT_EQUIVALENT",
    "class": "LOOKALIKE_VETOED",
    "decisive": {
     "attr": "schedule",
     "a": "40",
     "b": "80",
     "rule": "PIPE.schedule"
    }
   }
  ]
 },
 "hidden_twins": {
  "count": 2,
  "items": [
   {
    "text_a": "BOLT HEX M16X80 GR8.8 ZN",
    "text_b": "BOLT, HEX HD, M16 X 80, 8.8, ZINC",
    "text_sim": 0.73,
    "verdict": "EQUIVALENT",
    "class": "HIDDEN_TWIN"
   }
  ]
 }
}
```

**Example: baseline scoreboard (`GET /eval/runs/{id}/baselines`).** Values are `null` on purpose; they are computed at run time.

```json
{
 "run_id": "…",
 "label": "SYNTHETIC - optimistic by construction",
 "split": "test",
 "tau_tuned_on": "validation split (max F1)",
 "baselines": {
  "b1_text_only": {
   "definition": "token_set_ratio of normalised texts >= tau",
   "tau": null,
   "false_merges_on_hard_negatives": null,
   "hard_negatives": null,
   "equivalents_found": null,
   "equivalents_total": null,
   "coverage": null
  },
  "b2_text_plus_numbers": {
   "definition": "b1 AND numeric tokens of both texts are equal",
   "tau": null,
   "false_merges_on_hard_negatives": null,
   "hard_negatives": null,
   "equivalents_found": null,
   "equivalents_total": null,
   "coverage": null
  },
  "specid": {
   "definition": "veto -> unknown-state -> verdict (section 9.5)",
   "false_merges_on_hard_negatives": null,
   "hard_negatives": null,
   "equivalents_found": null,
   "equivalents_total": null,
   "coverage": null,
   "abstentions_justified": null,
   "abstentions_other": null
  }
 },
 "disagreements": {
  "merged_by_b1_vetoed_by_specid": null,
  "of_which_truth_not_equivalent": null,
  "found_by_specid_missed_by_b1": null,
  "found_by_specid_missed_by_b2": null
 },
 "note": "values are computed at run time; null here on purpose"
}
```

**Example: ask, don't guess (`POST /records/{id}/supply-attribute`, request then response).** The change list is produced by the reference code.

```json
{
 "attr": "end_connection",
 "value": "FLANGED-RF",
 "source_note": "datasheet D-123"
}
```

```json
{
 "record_id": "5c0e2c1e-0a5b-4d0a-8a8e-2f4f7a1d9b33",
 "provenance": "supplied by user: datasheet D-123",
 "affected_pairs": 1,
 "changes": [
  {
   "pair_id": "a41b7c0a-6c1d-4f2f-9b5e-0c7d1e2f3a44",
   "old": "INSUFFICIENT_DATA",
   "new": "EQUIVALENT"
  }
 ],
 "audit_event_id": 1043
}
```

**Example: rulebook impact preview (illustrative, 3 stored pairs).** Produced by the reference code.

```json
{
 "template": "valve",
 "draft_version": 2,
 "change": "design_standard moved from extended to core",
 "illustration": "3 stored pairs",
 "pairs_checked": 3,
 "changed": [
  {
   "pair": 0,
   "old": "EQUIVALENT",
   "new": "INSUFFICIENT_DATA",
   "old_route": "REVIEW",
   "new_route": "REVIEW"
  }
 ],
 "golden_tests": {
  "passed": null,
  "failed": null
 },
 "activation_allowed": null
}
```

---

## 9. Core logic specifications

### 9.1 Pipeline

| Stage | Input → output | Module | FRs |
|---|---|---|---|
| Ingest | CSV → `material_record` | `services/ingest` | 101–106 |
| Normalise | text → normalised text | `core/normalise` | 201–204 |
| Classify + extract | normalised text → category, attributes, residual tokens | `core/extract` | 301–307, 401–402 |
| Candidates | records → pairs | `services/harmonise` | 501–507 |
| Decide | pair → verdict, route, reasons, evidence | `core/decide` | 601–611 |
| Cluster | pairs → clusters | `core/cluster` | 701–703 |
| Review | cluster → decision | `api/review` | 801–807 |
| Register | approved cluster → CNMC + crosswalk | `services/registry` | 901–906 |
| Prevent | free text → candidates | `services/search` | 1001–1004 |
| Look-alike class and baselines | pair + verdict → class; text-only verdicts | `core/radar`, `eval/baselines` | 1401–1403, 1411–1413 |

### 9.2 Normaliser (ordered rules)

| # | Rule | Example (in → out) |
|---|---|---|
| 1 | Upper-case | `gate valve` → `GATE VALVE` |
| 2 | Quote marks → ` IN `; strip `, ; ( )` | `4"` → `4 IN` |
| 3 | `/` before a letter becomes a space (fractions keep their slash) | `SS316/GRAF` → `SS316 GRAF`; `1/2` unchanged |
| 4 | `4IN`, `4 INCH`, `4 INCHES` → `4 IN` | `4INCH` → `4 IN` |
| 5 | `DN100` and `100NB` → `100 NB` | `DN100` → `100 NB` |
| 6 | `150#`, `CLASS 150`, `CL 150` → `CL150` | `150#` → `CL150` |
| 7 | `SCH 40`, `SCHEDULE 40`, `SCH.40` → `SCH40` (also `STD`, `XS`, `XXS`) | `SCH 40` → `SCH40` |
| 8 | `GR.B`, `GRADE B`, `GR B` → `GRB`; `GR8.8` unchanged | `GRADE B` → `GRB` |
| 9 | Whole-word expansions: `SMLS`→`SEAMLESS`, `FLGD`→`FLANGED`, `WND`→`WOUND`, `GRAF`→`GRAPHITE`, `HD`→`HEAD`, `FLG`→`FLANGE` | `FLGD RF` → `FLANGED RF` |
| 10 | Collapse whitespace | |

The expansion list is a **versioned dictionary** (FR-203); the code in Appendix C is the v1 seed.

**Fixed point (DEC-24).** One pass of rules 1–10 is not idempotent on every input (`1/2 #` → `1/CL2` → `1 CL2`; `GR.ADE B` → `GRADE B` → `GRB`). Production `normalise` therefore **repeats rules 1–10, in this order, until the output stops changing (max 8 passes)**; if the cap is ever reached it returns the last result and logs a warning with the input's SHA-256, never the text. This is what makes FR-201 / T-P4 (`normalise(normalise(x)) == normalise(x)`) hold. Measured on the 3k seed: at most 2 passes.

**Face phrases (dictionary v2, Phase 5).** Style B text (10.1) writes `RAISED FACE`, `FLAT FACE`, `RING TYPE JOINT`, which the v1 rules do not read, so those pairs abstain. Dictionary v2 adds the whole-phrase expansions `RAISED FACE`→`RF`, `FLAT FACE`→`FF`, `RING TYPE JOINT`→`RTJ` (applied before rule 9). Because Appendix C stays the v1 oracle, this is logged as an allowlisted deviation that applies only to texts containing one of these phrases.

### 9.3 Size and unit canonicalisation
- Sizes map to **DN** through table B.1. Anything not in the table (for example `7 IN`) becomes *unknown* and is never guessed.
- A bare `100 MM` is **not** accepted as a size (it could be outside diameter or DN); it stays as a technical residual token, so the pair becomes `INSUFFICIENT_DATA`.
- `STD` → `40` only for DN ≤ 250; `XS` → `80` only for DN ≤ 200 (B.2). **SME must verify these limits.** `STD` / `XS` with no known size, or outside these limits, cannot be resolved and is **unknown** (see 9.5, *unresolvable values*), never compared as a raw word.
- `HP` → kW at 0.7457; kW values compare within 1%; rpm within 5%.

### 9.4 Templates and extraction

| Category | Core attributes | Extended | Special rules |
|---|---|---|---|
| VALVE | valve_type, size_dn, pressure_class, body_material, end_connection | design_standard, trim | `GV`/`GLV`/`CV`/`BV` expand to type; `WCB` → `A216-WCB`; `FLANGED` with no face → `FLANGED-?` |
| PIPE | size_dn, schedule, material, process | end_finish | `A106` implies `SEAMLESS`; `A106` with no grade → `A106-?` |
| FLANGE | flange_type, size_dn, pressure_class, face, material | – | `WN` / `WELD NECK`, `SO`, `BLIND`, `LJ`, `SW`, `THRD` |
| FASTENER | fastener_type, thread, length_mm, strength | head, coating | For `NUT`, `length_mm` is dropped; `A193 B7` and `A194 2H` consumed as strength |
| MOTOR | motor_type, power_kw, poles | rpm, voltage, ip, mounting | `AC` + (`SQ` / `IND` / `INDUCTION`) → `AC-IND`; HP converted |
| GASKET (P1) | gasket_type, size_dn, pressure_class, winding_material, filler | – | Spiral-wound only in v1 |

Machine-readable definitions: Appendix A. Policy: *core* attributes must be known and equal on both sides; *extended* attributes veto when both are known and different, and flag the pair when only one side states them; *tolerant* and *make* attributes never veto. Safety-critical default (`critical_default`) comes from the template and can be overridden per item through the CSV `criticality` column.

### 9.5 Decision policy (this section refines dossier B3 and B5; see D-01)

**Attribute statuses**

| Status | Meaning |
|---|---|
| `MATCH` | Equal after canonicalisation (or equal within the numeric tolerance) |
| `PARTIAL` | Same family but one side is less specific (for example `SS316` vs `A182-F316`; `FLANGED-?` vs `FLANGED-RF`) |
| `CONFLICT` | Both known and different |
| `MISSING_ONE` | One side states it, the other is silent |
| `MISSING_BOTH` | Neither side states it |

**Material comparison:** equal codes → `MATCH`. Different *family* (carbon steel, 316, 304, …) → `CONFLICT`. Same family, one generic and one specific → `PARTIAL`. Same family, both specific and different (for example `A105` vs `A216-WCB`) → `CONFLICT`.

**Verdict and route**

| Condition (checked in this order) | Verdict | Route |
|---|---|---|
| Either category unrecognised | `INSUFFICIENT_DATA` | `REVIEW` |
| Categories differ | `NOT_EQUIVALENT` | `NONE` |
| Any core or extended attribute `CONFLICT` | `NOT_EQUIVALENT` (**veto**) | `NONE` |
| Any core attribute `PARTIAL`, `MISSING_ONE` or `MISSING_BOTH` | `INSUFFICIENT_DATA` | `REVIEW` (enrichment) |
| All core `MATCH`, and extended `PARTIAL` / `MISSING_ONE`, or technical residual tokens differ | `EQUIVALENT` or `IDENTICAL` | `REVIEW`, flags listed |
| All core `MATCH`, class is critical | `EQUIVALENT` or `IDENTICAL` | `REVIEW` (maker–checker) |
| All core `MATCH`, no flags, class non-critical | `EQUIVALENT` or `IDENTICAL` | `AUTO_ELIGIBLE` |

`IDENTICAL` applies when MPN and manufacturer are **both present on both sides** and equal, compared case-insensitively after trimming spaces; otherwise `EQUIVALENT` on the same route with the same reasons (DEC-26). The check runs only after the veto and the unknown-state have passed, so an equal MPN never skips the veto, and failing the check never makes a pair `NOT_EQUIVALENT`.

**Unresolvable values are unknown, not conflicts.** A veto needs two *known, canonical* values. A value the extractor cannot map to the attribute's canonical domain — `STD` / `XS` without a known size, a misspelled closed-domain word such as `INDUCTINO`, a size not in table B.1 — is recorded as unknown (`MISSING_ONE` / `MISSING_BOTH`, with a note such as `STD needs a size`), so the pair goes to `INSUFFICIENT_DATA` → `REVIEW`, never to `NOT_EQUIVALENT`. Found on the 3k seed in Phase 4 (4 true matches vetoed, safe direction); fixed in Phase 5 as an allowlisted deviation from Appendix C.

```
 categories differ? ──yes──► NOT_EQUIVALENT
        │no
        ▼
 any CONFLICT (core or extended)? ──yes──► NOT_EQUIVALENT      (hard veto, no override)
        │no
        ▼
 any core PARTIAL / MISSING? ──yes──► INSUFFICIENT_DATA → REVIEW (ask for the attribute)
        │no
        ▼
 flags (extended unverified, residual tokens differ) or critical class? ──yes──► EQUIVALENT / IDENTICAL → REVIEW
        │no
        ▼
 EQUIVALENT / IDENTICAL → AUTO_ELIGIBLE
```

### 9.6 Confidence and scoring
- **P0 heuristic confidence** (shown as "confidence (heuristic)", not a probability): for `EQUIVALENT` and `IDENTICAL`, `p_rule = 0.98 − 0.10 × (number of extended flags) − 0.15 × (1 if technical residual differs else 0)`, floor 0.50. `NOT_EQUIVALENT` shows 0.00; `INSUFFICIENT_DATA` shows none.
- **P1 calibrated model:** LightGBM on pair features, isotonic calibration on a validation split, thresholds by FR-608.
  - *Features:* per-attribute status counts (core and extended), residual-difference count, token-set ratio, Jaro–Winkler, BM25 score, embedding cosine, MPN equality, UoM equality, category.
  - *Training data:* synthetic train split plus reviewer decisions (FR-806). **Split by entity**, with an *unseen* hold-out of attribute combinations and one category.
  - **The scorer never overrides the veto or the unknown-state**; it only ranks pairs and sets auto-eligibility among pairs that already passed the rules.

### 9.7 Clustering
1. Take pairs with verdict `EQUIVALENT` or `IDENTICAL`; sort by confidence, highest first.
2. Start with singleton groups. For each pair, if the two records are in different groups and **no pair across the two groups would be `NOT_EQUIVALENT`** (checked with `decide`, memoised), merge the groups; otherwise record the blocked edge.
3. Cluster priority = (sum of `annual_value`, or 1) × (1 + 0.5 × number of flags in its pairs); cohesion = mean confidence of its edges.
4. Reference: `constrained_clusters` in Appendix C. Test: three valves where A~B and B~C individually but A and C conflict (`API 600` vs `API 6D`) never end up in one cluster.

### 9.8 CNMC and crosswalk
- **Format:** `NMC-` + 10-digit sequence + 1 Luhn check digit (non-significant on purpose; dossier B6). Example: `NMC-00012345674`.
- **Issuance is one database transaction:** checker confirms → `nextval('cnmc_seq')` → insert `cnmc` → insert one `crosswalk` row per member → mark cluster `APPROVED` → write the audit event. Rolling back leaves no partial state.
- **Canonical spec:** union of the known attributes across members (no conflicts exist by construction). `variants` lists the (manufacturer, MPN) pairs seen. `spec_completeness` = known attributes / (core + extended).
- **Merge:** a later merge sets `status = MERGED` and `merged_into`; crosswalk rows are re-pointed; history stays in the audit log.

### 9.9 Descriptions (short and long)
- **Short (≤ 40 characters, SAP-ready):** token order per category as in the reference `short_desc`. If the result exceeds 40 characters, the function returns *none* and the item is flagged for manual abbreviation (never silently truncated).

| Category | Example output (from the reference code) | Length |
|---|---|---|
| VALVE | `VLV GATE 4IN CL150 A216-WCB FLGD RF` | 35 |
| PIPE | `PIPE SMLS 6IN SCH40 A106-B` | 26 |
| FLANGE | `FLG WN 4IN CL150 RF A105` | 24 |
| FASTENER | `BOLT HEX M16X80 8.8 ZN` | 22 |
| MOTOR | `MOTOR AC IND 100KW 4P` | 21 |
| GASKET | `GASKET SPW 4IN CL150 SS316 GRAPH` | 32 |

- **Long description:** full words, comma-separated, in a fixed order per category (DEC-25); missing attributes are left out, nothing is generated.

| Category | Order |
|---|---|
| VALVE | `<type> VALVE`, size `4 IN (DN100)`, `CLASS n`, `ASTM <body>`, end (`FLANGED RAISED FACE` …), design standard, trim |
| PIPE | process, size, `SCH n`, material, end finish |
| FLANGE | `<type> FLANGE`, size, class, face, material |
| FASTENER | `<head> <type>`, `M16 X 80 MM`, `GRADE g`, coating |
| MOTOR | `AC INDUCTION MOTOR`, `n KW`, `n POLE`, `n RPM`, `n V`, IP, mounting |
| GASKET | `SPIRAL WOUND GASKET`, size, class, winding material, `<filler> FILLER` |

  Example: `GATE VALVE, 4 IN (DN100), CLASS 150, ASTM A216 WCB, FLANGED RAISED FACE`.
- **Short description with a missing value:** the part is left out (never `None`, `CLNone` or `?IN`); if nothing is left, the function returns *none* (DEC-21, DEV-1).

### 9.10 Evidence card
Fields: `verdict`, `route`, `reasons[]`, and `evidence[]` with `attr`, `level` (core / ext), `a`, `b`, `status`, **`rule`** (ID such as `VALVE.size_dn`), **`rule_text`**, and **`note_a` / `note_b`** (conversions and inferences such as `4 IN = DN100`, `WCB -> A216-WCB`, `supplied by user: datasheet D-123`). The UI renders one row per attribute with icon + colour + text, a popover for the rule, and collapses `MISSING_BOTH` rows. See the example in section 8.

### 9.11 Search-before-create
Algorithm in 6.4. Response ordering: `IDENTICAL`, `EQUIVALENT`, `INSUFFICIENT_DATA`, `NOT_EQUIVALENT`. `recommended_action` is `USE_EXISTING` when an `IDENTICAL` or `EQUIVALENT` candidate exists, `SUPPLY_ATTRIBUTES` when only `INSUFFICIENT_DATA` candidates exist (with the attribute list), otherwise `CREATE_NEW_ALLOWED`. Creating despite a `USE_EXISTING` hint requires a reason, which is written to the audit log.

### 9.12 Optional local LLM advisor (P2, off by default)
- **Input:** the evidence card of an uncertain pair. **Output (JSON schema enforced):** `{"advice": "LIKELY_EQUIVALENT | LIKELY_DIFFERENT | UNSURE", "rationale": "...", "attributes_to_check": ["..."]}`.
- **Constraints:** temperature 0; timeout 5 s; invalid JSON discarded; output displayed and logged only. **It cannot change a verdict or route** (NFR-04).

### 9.13 Signature feature specifications

**9.13.1 Look-alike Guard (SF-1)**
- `text_sim(a, b)` = rapidfuzz `token_set_ratio` of `normalise(a)` and `normalise(b)`, divided by 100. It is computed for every candidate pair when the decision is made and stored.
- **Classes:** `LOOKALIKE_VETOED` when the verdict is `NOT_EQUIVALENT` and `text_sim ≥ lookalike_min_sim` (default 0.85); `HIDDEN_TWIN` when the verdict is `EQUIVALENT` or `IDENTICAL` and `text_sim ≤ hidden_twin_max_sim` (default 0.75). Defaults are **[T]**, tuned on the validation split, and stored in the run config.
- **Decisive attribute:** every `CONFLICT` row of the pair in template order (core first), each with its rule ID.
- **Ranking:** look-alikes by `text_sim` descending (most dangerous first); hidden twins by `text_sim` ascending.
- **Screen S13:** two lists plus a chart (x = `text_sim` 0–1, y = verdict band ✔ / ? / ✖, colour = class); a click opens the evidence card; CSV export.
- Reference: `text_sim`, `lookalike_class` (Appendix C). On the 12 hand-built pairs the reference code lists 6 look-alikes and 2 hidden twins **[M, illustrative]**.

**9.13.2 Baselines (SF-2).** Definitions, tuning and fairness rules are in section 10.2b. Reference: `baseline_b1`, `baseline_b2`.

**9.13.3 Ask, don't guess (SF-3)**
1. An `INSUFFICIENT_DATA` reason names the attributes that block the decision.
2. The reviewer supplies a value and a **mandatory source note** (at least 5 characters). The value is validated against the template's value domain (for example `face` ∈ {RF, FF, RTJ}); invalid → HTTP 422.
3. The system writes an `attribute_supply` row, updates the spec with provenance (`tier = USER`, badge shown), re-decides the record's pairs in that run, rebuilds only the affected cluster, and writes an audit event in the same transaction.
4. A supplied value **cannot override a veto**: if it creates a conflict the verdict becomes `NOT_EQUIVALENT`. It never skips maker–checker approval.
Reference: `supply_attribute`.

**9.13.4 Cited decisions (SF-4).** Rule IDs have the form `CATEGORY.attribute`, are stable across template versions, and the evidence stores the template version used. Conversions and inferences are recorded as notes while extracting: inch/NB → DN, material aliases, `STD`/`XS` → schedule, spec-implied attributes (`A106` → `SEAMLESS`), HP → kW, `ZN` → `ZINC`, valve-type abbreviations. `rule_text` lives in the template YAML (Appendix A) and is compared with the code in a test.

**9.13.5 Safety scoreboard and honesty panel (SF-5).** Fixed layout, top to bottom: (1) headline **false merges *k* of *n* hard negatives, 95% upper bound** (rule of three when *k* = 0); (2) abstentions split into justified and other, coverage; (3) the baseline scoreboard (SF-2); (4) style-holdout and adversarial results, separately; (5) the **honesty panel** with fixed copy: *synthetic data written by the team that wrote the rules, optimistic by construction · not a measure of performance on real CPSE data (needs the L3 pilot) · baselines are simple, stronger learned matchers exist and are not compared here · abstentions count as misses in strict recall*; (6) the ten most frequent extraction misses (residual tokens) as known weaknesses; (7) the unseen-category probe result (E-5).

**9.13.6 Rulebook impact preview (SF-6)**
1. Input: run, template, draft version.
2. For each stored pair of the run (cap 200k; sample beyond that) call `decide(a, b, templates=draft)` on the stored specs and compare `(verdict, route)` with the stored values.
3. Return transition counts (for example `EQUIVALENT → INSUFFICIENT_DATA: 12`) and the first 50 changed pairs; run the draft's golden tests.
4. Activation needs passing golden tests **and** the ADMIN's acknowledgment (both audited).
5. **Limit:** only *policy* changes (core/extended membership, tolerances, critical flag) are previewable. Extractor or dictionary changes need re-extraction, which this preview does not cover; the screen says so.
Reference: `decide(..., templates=)`, `impact_preview`.

**9.13.7 Air-gap proof (SF-7)**
- **Egress guard** (reference `EgressGuard`): at API start, wrap socket connect, connect_ex and `getaddrinfo`. Allowed: loopback and configured hosts (the database). Anything else raises `PermissionError` and increments a counter exposed by `/system/airgap`.
- **Honest scope:** the guard is defence in depth inside one process. It only sees connections made through Python's `socket` module; native libraries that open sockets in C (for example **libpq** under psycopg, or libcurl) bypass it, so the database connection is not actually checked by the allow-list and a C-level leak would not be counted. The network-level guarantee is the Compose `internal: true` network plus the stage step of switching Wi-Fi off. On stage, say "guard + isolated network", never "the counter proves nothing can leak".
- **Compose pattern:** `api` and `db` on `backend` (`internal: true`); `web` on `backend` and on a default network with one published port.
- **Test T-S5:** a connection to `203.0.113.1` (TEST-NET-3) and a lookup of `example.com` are both blocked and counted; loopback and `localhost` still work.
- **Demo:** footer counter at 0 → `docker network inspect` shows `"Internal": true` → Wi-Fi off → run search-before-create.

---

## 10. Synthetic data and evaluation

> **Honesty rule.** The generator and the extraction rules are written by the same team, so results on synthetic data are **optimistic by construction**. They show that the pipeline behaves as designed, not how it performs on real CPSE data. Every page and report that shows them says so (FR-1103).

### 10.1 Synthetic generator

**Configuration (all values are defaults; every one is a parameter stored with the run)**

| Parameter | Default | Meaning |
|---|---|---|
| `seed` | 7 | Random seed; same seed + config → identical files |
| `n_entities` | **1,200** | Distinct base specifications; with hard-negative neighbours and duplicates this gives **about 3,000 records** (seed 7: 3,023 records from 1,499 entities). DEC-09; 4,000 gives about 10k if memory allows |
| `category_mix` | valve 25%, pipe 25%, flange 20%, fastener 20%, motor 10% | P0 categories |
| `cpses` | 3 styles: A, B, C | One style profile per CPSE |
| `presence` | in 1 / 2 / 3 CPSEs with 0.4 / 0.4 / 0.2 | Where each entity appears |
| `within_dup_rate` | 0.10 | Extra duplicate record inside the same CPSE |
| `hard_negative_share` | 0.30 (evaluation preset **0.5**, DEC-09) | Share of entities that get a "neighbour" differing in exactly one core attribute (never the category word) |
| `drop_ext_rate` | 0.30 | Chance an extended attribute is not written |
| `drop_core_rate` | 0.05 | Chance a core attribute is not written (creates justified `INSUFFICIENT_DATA`) |
| `typo_rate` | 0.02 per token | Character typo |
| `make_rate` | 0.40 | Record carries manufacturer + MPN |

**Style profiles**

| Style | Description | Examples |
|---|---|---|
| A (SAP-like) | ≤ 40 characters, heavy abbreviations, `IN`, `CL150`, truncation at 40 | `VALVE GATE 4IN CL150 A216 WCB FLGD RF` |
| B (descriptive) | Full words, `INCH`, `CLASS`, comma-separated | `GATE VALVE, 4 INCH, CLASS 150, ASTM A216 WCB, RAISED FACE FLANGED` |
| C (metric / NB) | `NB`/`DN`, `#`, word-order variants, `ZN` / `ZINC PLATED` | `GV 100NB 150# WCB RF FLANGED` |
| D (holdout, FR-1106) | Written by a team member who has **not seen** the extractors | evaluated separately |

**Value domains** (from standards enumerations; SME review required, dossier A4.1 row 9)

| Category | Domain |
|---|---|
| VALVE | type {gate, globe, check, ball}; DN from table B.1; class {150, 300, 600}; body {A216-WCB, A351-CF8M}; end {FLANGED-RF, BW} |
| PIPE | DN; schedule {40, 80, STD, XS}; material {A106-B, A53-B}; process {SEAMLESS, WELDED} |
| FLANGE | type {WN, SO, BLIND}; DN; class {150, 300, 600}; face {RF, FF}; material {A105, A182-F316} |
| FASTENER | type {BOLT, STUD, NUT}; thread {M12–M30}; length 20–200 mm; strength {8.8, 10.9, B7, 2H}; coating {ZINC, HDG, none} |
| MOTOR | power {kW list}; poles {2, 4, 6, 8}; rpm consistent with poles at 50 Hz; voltage {415, 690 V} |

**Generator consistency rules (DEC-27).** Truth values are always canonical: pipe schedules are stored canonical for their size (`STD` = SCH40 up to DN250, `XS` = SCH80 up to DN200), so a neighbour never "differs" only in how the same schedule is written; A106-B pipe is always seamless; bolts 8.8/10.9, studs B7, nuts 2H; motors are AC induction with rpm matching poles at 50 Hz. Style A cuts at 40 characters and records any core attribute it cut in `dropped_core`. Typos swap two adjacent letters in alphabetic words of 4+ letters, never digits. Makers are `SYNTH-MAKER-nn`, MPNs `SX-…`. Tests: truth schedules canonical for their size; no hard-negative pair with complete text is ever merged.

**Outputs per run:** `cpse_A.csv`, `cpse_B.csv`, `cpse_C.csv` (columns: `legacy_code, short_text, long_text, uom, mat_group, manufacturer, mpn, plant, criticality, annual_value`) · `truth_entities.csv` (record → entity, category, canonical attributes, `dropped_core`, `neighbour_of`, `split`) · `truth_pairs.csv` (pair → `EQUIVALENT` or `NOT_EQUIVALENT_HARD`) · `manifest.json` (seed, config, SHA-256 of every file; no timestamp, so the same seed gives byte-identical files). Files go to `data/synthetic/seed-<n>/`.

**Splits:** by entity: train 60% / validation 20% / test 20%. Rules and thresholds may be tuned **only** on train and validation. The test split is evaluated once before the final report. For P1 ML training, hold out whole attribute combinations (for example `BLIND` flanges and 8-pole motors) in the test split only.

**Realism sources (optional).** Free-text phrasing can be enriched with public tender item descriptions after a legal check. Not required for the MVP.

### 10.2 Metrics

Definitions over candidate pairs. *Positive verdict* = `EQUIVALENT` or `IDENTICAL`.

| Metric | Definition |
|---|---|
| TP / FP | Truth equivalent and positive verdict / truth not-equivalent and positive verdict |
| FN | Truth equivalent and verdict `NOT_EQUIVALENT` |
| Abstain (justified / unjustified) | Truth equivalent and verdict `INSUFFICIENT_DATA`; *justified* if the generator dropped a core attribute for that record |
| Precision | TP / (TP + FP) |
| Recall (strict) | TP / (TP + FN + abstentions on truth-equivalent pairs) |
| Recall (decided) | TP / (TP + FN) |
| Coverage | decided pairs / candidate pairs |
| **False-merge rate on hard negatives** | FP among hard-negative pairs / hard-negative pairs present among candidates. Also report the count not reached by blocking |
| Pair completeness (blocking) | truth-equivalent pairs inside candidates / all truth-equivalent pairs |
| Reduction ratio | 1 − candidates / (N(N−1)/2) |
| Auto-eligible precision and share | Precision among `AUTO_ELIGIBLE` pairs; share of positive pairs that are auto-eligible |
| Cluster quality | B-cubed precision and recall against truth entity groups |
| Extraction | Exact-match precision / recall / F1 per core attribute and category |
| Calibration (P1) | Reliability curve and expected calibration error |
| Review load | Clusters routed to `REVIEW` / all clusters |

**Statistics.** Wilson 95% interval for proportions with *k* successes out of *n*, *z* = 1.96: centre = (k/n + z²/2n) / (1 + z²/n); half-width = z·√((k/n)(1 − k/n)/n + z²/4n²) / (1 + z²/n). When **zero** errors are observed in *n* trials, report the **rule-of-three upper bound ≈ 3/n** (n = 1,000 → about 0.3%), never "0%".

### 10.2b Baselines and the scoreboard (SF-2)

Purpose: show, on the **same data**, what a simple text-based approach does next to SpecID. The baselines are deliberately simple and **fair**: they use the *normalised* text (so abbreviations and `150#` / `CL150` are already harmonised in their favour).

| Method | Definition |
|---|---|
| **B1: text only** | Positive when `token_set_ratio(normalise(a), normalise(b)) / 100 ≥ τ1` |
| **B2: text + numbers** | Positive when the same similarity is `≥ τ2` **and** the sorted lists of numeric tokens of the two raw texts are equal (a common guard against `CL150` vs `CL300`) |
| **SpecID** | Section 9.5 |

**Fairness rules (FR-1413, NFR-13)**
1. τ1 and τ2 are tuned **separately**, on the **validation** split, to maximise F1; the **test** split is evaluated once.
2. Same candidate pairs, same split, same truth for all three methods.
3. Both baselines are always shown, even if one looks poor for SpecID on some metric (SpecID abstains on missing core attributes, so its coverage can be lower).
4. The page states that stronger learned matchers exist; published text-only matchers reach F1 0.64–0.89 on WDC Products and lose precision on near-miss negatives (dossier A2.3, [S13]). The comparison here is **not** against them.

**Scoreboard columns:** false merges on hard negatives (*k* of *n*) · equivalents found (strict) · coverage · and the **disagreement table**: (a) merged by B1 but vetoed by SpecID, with how many of those were truly different; (b) found by SpecID but missed by B1; (c) found by SpecID but missed by B2; (d) abstained by SpecID but decided by a baseline, with whether the baseline was right.

**What the 12 hand-built pairs show [M, illustrative]:** at τ1 = 0.85, B1 merges all 6 look-alikes and finds 2 of 6 equivalents; at τ2 = 0.55, B2 merges none but also finds only 2 of 6 (every pair that needs a unit conversion, such as `4IN` against `100NB`, fails its numeric test); SpecID returns 0 false merges and 6 of 6. **SpecID's rules were written with these pairs in view, so this is a unit-test illustration, not evidence.** The honest comparison is the seeded run, the style-D holdout and the adversarial set.

### 10.3 Acceptance targets on the synthetic test split **[T, not results]**

| ID | Target |
|---|---|
| E-1 | Zero false merges among the hard negatives of the seeded run (with ≥ 1,000 the upper bound is ≈ 0.3%; on the 3k set the report states the real *n* and its rule-of-three bound, DEC-09). If not reached: list every failure, fix rules, re-run on validation, then re-test once |
| E-2 | Pair completeness ≥ 0.98 |
| E-3 | Auto-eligible precision, Wilson lower bound ≥ 0.99 (only if auto-eligibility is switched on; needs about 380 error-free auto-eligible pairs) |
| E-4 | Core-attribute extraction F1 ≥ 0.90 per category on development styles |
| E-5 | **Unseen-category probe:** for a category without a template (for example `CABLE`), 100% of pairs return `INSUFFICIENT_DATA` (the system abstains rather than guesses) |
| E-6 | Style D (holdout) and the **adversarial set** (typo 0.08, drop_core 0.15) are reported separately; lower numbers are expected and must be shown |
| E-7 | On the test split, SpecID's false merges on hard negatives are **≤ the lower of B1's and B2's**. Expected by construction; if not met, say so on the scoreboard |
| E-8 | **Look-alike Guard coverage:** every hard negative with `text_sim ≥ 0.85` that SpecID vetoes appears on S13 (no silent drops); target ≥ 20 listed items for the bundled seed |

### 10.4 Reports
Each run exports JSON and Markdown containing: SYNTHETIC label · seed and config · git commit · template and dictionary versions · headline metrics with intervals · **baseline scoreboard and disagreement table** · **Look-alike Guard summary (counts and top items)** · verdict-versus-truth confusion matrix · per-category table · ablation table (P1) · top-20 false merges, false negatives and abstentions with evidence cards · the honesty-panel text and the evidence-ladder statement (*L2 synthetic; L3 requires CPSE pilot data*).

---

## 11. UI and UX specification

### 11.1 Screens

| ID | Screen | Purpose and key elements | Roles | FRs |
|---|---|---|---|---|
| S0 | Overview | Counts per CPSE and category, verdict mix, cross-CPSE clusters, backlog | all | 1201 |
| S1 | Login | Username, password | all | 1301 |
| S2 | Upload and mapping | File drop, detected columns, suggested mapping, SYNTHETIC checkbox | MAKER+ | 101, 102, 106 |
| S3 | Data-quality report | Completeness bars, parse rate per category, long-text counts | MAKER+ | 103 |
| S4 | Run console | Pick batches, mode, options; progress bar; stats; cancel | MAKER+ | 505, 507 |
| S5 | Review queue | Filterable table sorted by priority; flags and critical badges | MAKER, CHECKER | 801 |
| S6 | Cluster review | Side-by-side records, evidence card **with rule popovers and conversion notes**, proposed CNMC text, actions; inline "supply value" on `INSUFFICIENT_DATA` rows (P1) | MAKER, CHECKER | 802, 803, 1421–1423, 1431–1432 |
| S7 | Pair evidence | Modal evidence card from any pair link | MAKER+ | 609 |
| S8 | Registry | CNMC list and detail with crosswalk and history | MAKER+ | 906 |
| S9 | Search-before-create | Free-text box, parsed spec, ranked candidates, recommended action | MAKER+, INTEGRATOR | 1003 |
| S10 | Templates (rulebook) | View core / extended / critical per category, rule texts and golden tests; YAML draft, golden tests and **impact preview** (P0) | all; edit ADMIN | 401–404, 1451–1452 |
| S11 | Evaluation | Run generator and evaluation; **safety headline, baseline scoreboard, honesty panel**, ablations, confusion matrix; SYNTHETIC badge | MAKER+ | 1101–1106, 1411–1413, 1441–1443 |
| S12 | Audit | Filterable log; "verify chain" button | ADMIN, AUDITOR | 1302 |
| S13 | **Look-alike Guard** | Look-alikes vetoed and hidden twins, chart of text similarity against verdict, decisive attribute with rule ID | MAKER+, AUDITOR | 1401–1403 |
| S14 | Create material (mock ERP), P1 | Description box with live duplicate check, 40-character counter, "use SpecID description" | MAKER+, INTEGRATOR | 1471 |
| S15 | Pooling view, P1 | CNMCs held by several CPSEs with combined annual value | MAKER+ | 1491 |
| S16 | Users | Create users, roles, reset passwords, API keys (P1) | ADMIN | 1301, 1004 |
| S17 | About & honesty | Evidence ladder, honesty text, versions, licences | all | 1442 |
| S18 | **Consent queue** | Clusters waiting for my CPSE's consent; evidence; Consent / Decline | CHECKER of the CPSE | 1501–1504 |
| S19 | Change notices, P1 | Per-CPSE inbox; acknowledge; delta migration file | MAKER+, INTEGRATOR | 1511–1513 |
| Footer | Air-gap indicator (all pages) | "Air-gapped · blocked attempts: n" from `/system/airgap`, plus "Consent: all CPSEs" | all | 1463, 1504 |

### 11.2 Visual language
- **Verdicts** use colour **and** icon **and** text: `EQUIVALENT` / `IDENTICAL` green ✔ · `NOT_EQUIVALENT` red ✖ · `INSUFFICIENT_DATA` amber ? · flags ⚠ outline · `AUTO_ELIGIBLE` blue "auto" tag · `REVIEW` grey tag.
- A **SYNTHETIC DATA badge** in the top bar of every page that shows data (not dismissible; its tooltip says "results are optimistic by construction"). Login shows no data and has no badge (DEC-10).
- Footer: "Air-gapped · blocked attempts: n" with a green dot, and a muted "Consent: all CPSEs".
- Dense, table-first layout; monospace for descriptions so characters (`l`, `1`, `I`, `0`, `O`) are distinguishable.

### 11.3 Wireframes (text)

**S6 Cluster review**
```
┌ Cluster 4F2A · VALVE · 3 records · 3 CPSEs · priority 0.82 ─────────────── [SYNTHETIC] ┐
│ Verdict: EQUIVALENT   Route: REVIEW (critical class: maker–checker)                    │
│ Flags: ⚠ design_standard unverified                                                    │
├──────────────────────────┬──────────────────────────┬──────────────────────────────────┤
│ CPSE-A  100234           │ CPSE-B  77-4410          │ CPSE-C  VLV-00918                │
│ VALVE GATE 4IN CL150     │ GATE VALVE, 4 INCH,      │ GV 100NB 150# WCB RF             │
│ A216 WCB FLGD RF         │ CLASS 150, ASTM A216     │ FLANGED                          │
├──────────────────────────┴──────────────────────────┴──────────────────────────────────┤
│ EVIDENCE   attribute        A            B            status / conversion note         │
│             valve_type       GATE         GATE         ✔ MATCH   (GV = GATE)           │
│             size_dn          100          100          ✔ MATCH   (4 IN = DN100)        │
│             pressure_class   150          150          ✔ MATCH                         │
│             body_material    A216-WCB     A216-WCB     ✔ MATCH   (WCB -> A216-WCB)     │
│             end_connection   FLANGED-RF   FLANGED-RF   ✔ MATCH                         │
│             design_standard  API-600      (silent)     ⚠ UNVERIFIED   [rule ▸]         │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Proposed CNMC text: VLV GATE 4IN CL150 A216-WCB FLGD RF      (35 / 40 chars)           │
│ [A] Approve   [R] Reject   [S] Split…   [N] Needs info      Comment: ________          │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

**S9 Search-before-create**
```
Description [ gate valve 4 inch class 150 ASTM A216 WCB flanged RF      ]  UoM [EA]  [Check]
Parsed  VALVE · GATE · DN100 · CL150 · A216-WCB · FLANGED-RF · design_standard —
Result  ⚠ DUPLICATE RISK: 1 EQUIVALENT candidate           recommended: USE_EXISTING
 1  NMC-00000001974  VLV GATE 4IN CL150 A216-WCB FLGD RF       ✔ EQUIVALENT      [evidence ▸]
 2  NMC-00000004127  VLV GATE 4IN CL150 A216-WCB FLANGED       ? INSUFFICIENT (end_connection)
 3  NMC-00000003111  VLV GATE 4IN CL300 A216-WCB FLGD RF       ✖ NOT_EQUIVALENT (pressure_class)
[ Use NMC-00000001974 ]   [ Create new… (reason required) ]
```

**S11 Evaluation** (all values are filled at run time; none are pre-written)
```
EVALUATION   [SYNTHETIC: optimistic by construction]   seed 7 · 3 CPSEs · N records
Evidence ladder   L0 literature ✔   L1 public proxies ○   L2 synthetic ● (this page)   L3 CPSE pilot ○
┌ Safety headline ───────────────────────────────────────────────────────────────────┐
│ False merges on hard negatives: k / n        95% upper bound: …                    │
│ Abstentions: justified … / other …     Coverage: …     Pair completeness: …        │
└────────────────────────────────────────────────────────────────────────────────────┘
┌ Baseline scoreboard (same pairs, same split, tau tuned on validation) ─────────────┐
│                       false merges   equivalents found   coverage                  │
│ B1 text only          …              …                  …                          │
│ B2 text + numbers     …              …                  …                          │
│ SpecID                …              …                  …                          │
│ Disagreements: merged by B1 but vetoed by SpecID … (truly different …)             │
│                found by SpecID but missed by B1 …   missed by B2 …                 │
└────────────────────────────────────────────────────────────────────────────────────┘
┌ Honesty panel ─────────────────────────────────────────────────────────────────────┐
│ Synthetic data written by the team that wrote the rules: optimistic by design.     │
│ Not a measure of performance on real CPSE data (needs the L3 pilot).               │
│ Baselines are simple; stronger learned matchers exist and are not compared here.   │
│ Abstentions count as misses in strict recall.                                      │
└────────────────────────────────────────────────────────────────────────────────────┘
[ Style D & adversarial ] [ Ablations ] [ Confusion matrix ] [ Per category ] [ Failures ] [ Export MD/JSON ]
```

**S13 Look-alike Guard** (the example rows come from the 12 hand-built pairs; a real run shows its own)
```
LOOK-ALIKE GUARD   run 4F2A   [SYNTHETIC]    look-alike ≥ 0.85 · hidden twin ≤ 0.75
┌ What a text-only matcher would have merged (SpecID vetoed) ─────────────────────────┐
│ sim   A                                   B                         decisive        │
│ 0.97  PIPE SMLS 6IN SCH40 A106 GR.B       PIPE SMLS 6IN SCH80 …     ✖ schedule 40≠80│
│ 0.95  VALVE GATE 4IN CL150 A216 WCB …     VALVE GATE 4IN CL300 …    ✖ class 150≠300 │
│ 0.90  FLANGE WN 4IN CL150 RF A105         FLANGE WN 4IN CL150 …     ✖ material      │
├ Hidden twins: different wording, same specification ────────────────────────────────┤
│ 0.73  BOLT HEX M16X80 GR8.8 ZN            BOLT, HEX HD, M16 X 80…   ✔ EQUIVALENT    │
└─────────────────────────────────────────────────────────────────────────────────────┘
Chart: x = text similarity 0–1 · y = verdict band ✔ / ? / ✖ · click a dot → evidence card
Footer: Air-gapped · blocked attempts: 0
```

### 11.4 Interaction rules
- Review actions: `A` approve, `R` reject, `S` split, `N` needs info, `J` / `K` next / previous, `?` help (P1).
- A maker never sees "Confirm" buttons; a checker never sees "Propose" on a cluster they proposed.
- Empty, loading and error states are designed for every list; errors show the problem-details `title` and `detail`.

---

## 12. Security, governance and data handling

| Topic | Requirement |
|---|---|
| Authentication | Local users, bcrypt hashes, JWT with 8 h expiry; INTEGRATOR may use an API key (hashed at rest) |
| Authorisation | Server-side RBAC per section 2; **separation of duties:** maker ≠ checker on a cluster; ADMIN cannot review |
| Audit chain | `hash = SHA-256(prev_hash ‖ canonical_json(event))`, canonical JSON = sorted keys, no whitespace. `GET /audit/verify` recomputes from the first event; any edit or deletion breaks the chain at that row |
| Data classification | CPSE data is confidential. The demo uses synthetic data only; real data never enters the repo, logs or screenshots |
| Network | No outbound calls at runtime (FR-1303); models and the optional LLM are local. **Egress guard** in the API process (loopback and database only, blocked attempts counted) plus an `internal: true` Compose network (FR-1461–1463) |
| Template governance | Propose (DRAFT) → impact preview (SF-6, P0) → golden tests must pass → the ADMIN acknowledges the impact preview and activates; both steps audited → versions are immutable; runs record the version used. No second ADMIN is required (DEC-04); a four-eyes activation is a production option (TRD §19) |
| Secrets | Environment variables; `.env.example` lists demo users and passwords **for local use only** |
| Logging | Structured JSON; no passwords or tokens; descriptions are logged only in debug mode |

---

## 13. Test plan

### 13.1 Levels

| Level | What | Tool | Gate |
|---|---|---|---|
| Unit | Normaliser, size/unit rules, extractors, compare, decide, CNMC, short text, clustering | pytest | CI blocks merge on failure |
| Golden | Pairs with expected verdict (and route) per template | pytest, YAML/CSV fixtures | **≥ 10 pairs per P0 template and ≥ 60 in total by T+30** |
| Property | See 13.3 | hypothesis | CI |
| API contract | Request/response schemas, RBAC, error format | pytest + httpx | CI |
| Integration | CSV → run → clusters → approve → CNMC → crosswalk → search | pytest with Postgres container | CI nightly and before demo |
| Evaluation | Formula tests (Wilson, rule-of-three), metrics on a tiny hand-labelled fixture | pytest | CI |
| Determinism | Generator output hash stable for a seed | pytest | CI |
| Offline | Full demo path with the network disabled | manual + script | Before demo |
| UI | Demo path checklist (P0); Playwright (P2) | manual / Playwright | Before demo |

### 13.2 Golden tests
Seed set: the 12 near-miss / equivalent pairs of dossier A4.3 plus 13 edge cases are in Appendix D. File format for new cases: `a`, `b`, `expected_verdict`, optional `expected_route`, `note`. Required coverage per template: ≥ 3 near-miss pairs (one per core attribute), ≥ 3 equivalent pairs with different wording or units, ≥ 2 `INSUFFICIENT_DATA` pairs, ≥ 1 flagged pair.

### 13.3 Property tests

| ID | Property |
|---|---|
| T-P1 | If any extracted core or extended attribute is in `CONFLICT`, the verdict is `NOT_EQUIVALENT` regardless of confidence, advisor output or flags |
| T-P2 | No cluster contains a pair whose verdict is `NOT_EQUIVALENT` |
| T-P3 | `decide(a, b)` and `decide(b, a)` have the same verdict |
| T-P4 | Normaliser is idempotent |
| T-C | CNMC check digit detects every single-digit error and every adjacent transposition except `09` / `90` |
| T-P5 | `short_desc` returns ≤ 40 characters or none |
| T-P6 | Re-ingesting the same file creates no new `material_record` rows |
| T-S1 | Baselines B1 and B2 on a tiny hand-labelled fixture return the expected counts (reference: the 12 hand-built pairs give B1 6 false merges and 2 of 6 found; B2 0 and 2 of 6) |
| T-S2 | Look-alike classes: `LOOKALIKE_VETOED` only for `NOT_EQUIVALENT` with `text_sim ≥ hi`; `HIDDEN_TWIN` only for equivalent verdicts with `text_sim ≤ lo` |
| T-S3 | Supplying a missing attribute re-decides the pair with provenance; a conflicting supplied value gives `NOT_EQUIVALENT`; the source note is mandatory |
| T-S4 | Impact preview lists exactly the pairs whose `(verdict, route)` change under a draft template; with an unchanged template it lists none |
| T-S5 | Egress guard blocks and counts a connection to `203.0.113.1` and a lookup of `example.com`; loopback and `localhost` still work |
| T-S6 | Every evidence row has a `rule` ID and `rule_text`; conversions carry notes; `rule_text` equals the template YAML text |
| T-S7 | Multi-CPSE consent: no CNMC for a multi-CPSE cluster until every participating CPSE consented; a decline excludes that CPSE's records and records a dissent; a single-CPSE cluster needs no extra consent |
| T-S8 | Impact preview lists exactly the stored decisions whose `(verdict, route)` change, plus the CNMCs and CPSEs affected (extends T-S4) |

### 13.4 Demo-readiness checklist
- [ ] `docker compose up` on a clean machine reaches the login page
- [ ] Seed script loads users, templates, synthetic data and a pre-run snapshot
- [ ] All golden and property tests pass on the demo commit
- [ ] The demo path in section 15 runs three times offline
- [ ] SYNTHETIC DATA badge visible on every data screen
- [ ] Air-gap: `docker network inspect` shows `"Internal": true`; the demo path works with Wi-Fi off; the footer counter reads 0
- [ ] Look-alike Guard lists ≥ 20 items for the bundled seed; the baseline scoreboard shows B1, B2 and SpecID with the honesty panel
- [ ] A 3-CPSE cluster shows "waiting for CPSE-C consent" and issues the CNMC only after the CPSE-C steward consents
- [ ] Impact preview of the demo draft rule shows non-zero transitions and activation is blocked until golden tests pass
- [ ] Competitive Review scan re-run in the week before the finale; claims re-checked
- [ ] Text search finds no "first", "only" or "best" on any screen, export or slide (NFR-14)
- [ ] Backup: DB snapshot, recorded screen video, screenshots for Slide 3

---

## 14. Delivery plan

### 14.1 Team and ownership (6 people)

| Role | Owns | Main modules | Backup |
|---|---|---|---|
| **R1** Tech lead / backend | API, DB, auth, audit chain, Docker, CI | `api/`, `db/`, `services/ingest`, `registry`, `audit` | R3 |
| **R2** NLP / rules | Normaliser, extractors, templates, golden tests | `core/normalise`, `core/extract`, `templates/` | R3 |
| **R3** Matching / ML | Blocking, `decide`, clustering, thresholds, (P1) scorer | `core/decide`, `core/cluster`, `services/harmonise` | R2 |
| **R4** Data / evaluation | Generator, metrics, evaluation runner and reports | `eval/` | R3 |
| **R5** Frontend lead | Design system, S5, S6, S9 | `frontend/` | R6 |
| **R6** Frontend / QA / demo | S0, S2–S4, S8, S11, S12, UI tests, docs, demo script | `frontend/`, `tests/`, `docs/` | R5 |

Rule: **vertical slices.** Each person delivers working end-to-end increments behind the agreed API contract (section 8), not isolated layers.

### 14.2 Before the finale

| Task | Safe even if pre-written code is banned (Q-01)? | Output |
|---|---|---|
| Finalise this PRD, scope tiers and roles | Yes | Signed-off PRD |
| Review templates and equivalence rules with a materials engineer (D-06) | Yes | Corrected Appendix A and B |
| Draw wireframes for S6, S9, S11 (paper or Figma) | Yes (design, not code) | Wireframes |
| Install Docker, Python 3.11, Node; pull images; download the embedding model; test offline | Yes (tooling) | Verified laptops |
| Learn the stack (FastAPI, React, TanStack Query) | Yes | Team readiness |
| Write and rehearse the demo narrative against the slides | Yes | Script v1 |
| Generator, extractors, golden tests, UI components | **Only if the rules allow it** | Pre-built assets |

### 14.3 The 36-hour plan (T = hours from start)

| Window | Goal | Who | Gate (exit criterion) |
|---|---|---|---|
| T+0 – 2 | Kickoff: repo, compose, CI, seed users; answer Q-01 and Q-02; lock scope | all | `docker compose up` shows login; CI green |
| T+2 – 8 | Core v0: normaliser **with conversion notes**, extractors (valve, pipe, flange), template loader with **rule texts**, `decide`; generator v0; DB + ingest API; UI skeleton + S2 | R2, R3, R4, R1, R5, R6 | **G1 (T+8):** a CLI run on generator output prints the verdict mix; 25 golden tests pass; evidence rows carry rule IDs (SF-4) |
| T+8 – 14 | Blocking + BM25 + **dense channel**, **ML category fallback**, **UoM table**, procurement-history ingest, clustering, persistence, run API; **store `text_sim` and the `lookalike` class (SF-1)**; S3, S4; fastener and motor extractors; **egress guard + internal Compose network (SF-7)** | R3, R1, R6, R2 | **G2 (T+14):** end-to-end run from the UI on synthetic data; footer shows "Air-gapped · blocked attempts: 0" |
| T+14 – 20 | Review queue (S5), cluster view (S6) with rule popovers, maker–checker, CNMC issuance, crosswalk, exports, audit chain; **Look-alike Guard S13 (SF-1)**, **multi-CPSE consent (SF-11) + S18 consent queue** | R5, R1, R3, R6 | **G3 (T+20):** approve a cluster → CNMC → crosswalk export; audit verify passes; S13 lists look-alikes |
| T+20 – 26 | Search-before-create (API + S9), evaluation runner + S11, **baselines B1 / B2 + scoreboard (SF-2) + honesty panel (SF-5)**, **S0 dashboard** (duplicate, quality and demand panels), S8, **migration pack + SAP-style export + SAP import preset**; golden tests ≥ 40; **rulebook impact preview + YAML draft + golden gate (SF-6)** | R3, R4, R5, R6 | **G4 (T+26):** S11 shows a seeded SYNTHETIC run: false merges *k* of *n* with bound, B1 / B2 / SpecID side by side |
| T+26 – 30 | Hardening: property tests T-S1…T-S6, style D + adversarial set, residual-guard tuning; **P1 signature features in this order: SF-3 ask-don't-guess, SF-12 change notices, SF-8 ERP simulator, SF-9, SF-10**; gasket (P1); LightGBM only if all gates are met | R2, R3, R4, R5, R6 | **G5 (T+30): FEATURE FREEZE**; ≥ 60 golden tests; all P0 signature features demonstrable |
| T+30 – 34 | Bug fixes only; DB snapshot; screenshots; backup video; README; slide screenshots | all | Demo path passes offline twice |
| T+34 – 36 | Three rehearsals; tag release; stop updating laptops | all | **G6:** tagged release and checklist 13.4 fully ticked |

### 14.4 Cut order if behind
1. LLM advisor / extractor · 2. Dense channel (MiniLM + FAISS; P0 since v0.4, cut only if the model cannot be loaded, 6.5) · 3. LightGBM and calibration · 4. SF-10 pooling view · 5. SF-9 reversible merges · 6. SF-8 ERP simulator · 7. SF-12 change notices · 8. Bulk approve · 9. Gasket template · 10. Impact calculator · 11. SAP-style export. **SF-3 ask-don't-guess is the last P1 item to cut** because it is the strongest demo moment.

**P0 items that may be simplified (not cut) if behind:** XLSX upload and encoding detection → UTF-8 CSV only · mapping-wizard suggestions → manual dropdowns · S0 dashboard → tables without charts (all panels kept, FR-1201 is a PS key capability) · run cancel → omitted · S3 quality report → table without charts · S13 chart → lists only · JWT login → seeded users with a role switcher (keep server-side RBAC checks) · CSV + JSON export → CSV only.

**Minimum viable demo path** (switch to it if G3 slips past T+22): pre-loaded synthetic snapshot → S13 Look-alike Guard → S6 cluster with rule popovers → approve (maker, then checker) → S8 CNMC + crosswalk → S9 search-before-create → S11 scoreboard + honesty panel → footer air-gap. Everything else is optional.

**Never cut:** **multi-CPSE consent (SF-11)**, **rulebook impact preview (SF-6)**, veto, unknown-state, evidence card **with rule citations (SF-4)**, maker–checker, SYNTHETIC DATA badge, evaluation page with the **safety scoreboard and honesty panel (SF-5)**, **baseline scoreboard (SF-2)**, **Look-alike Guard (SF-1)**, **air-gap proof (SF-7)**, audit chain. These are the story of "why SpecID looks different".

### 14.5 Repository layout
```
specid/
├─ README.md · docker-compose.yml · Makefile · .env.example
├─ backend/
│  ├─ app/
│  │  ├─ main.py · settings.py · auth.py
│  │  ├─ api/        (routers per API-xx)
│  │  ├─ core/       (normalise.py extract.py decide.py cluster.py cnmc.py shortdesc.py templates.py)
│  │  ├─ services/   (ingest.py harmonise.py registry.py search.py audit.py)
│  │  ├─ eval/       (generator.py metrics.py runner.py report.py)
│  │  └─ db/         (models.py, migrations/)
│  └─ tests/         (golden/ unit/ property/ api/ integration/)
├─ templates/        (valve.yaml pipe.yaml flange.yaml fastener.yaml motor.yaml gasket.yaml)
├─ frontend/         (src/pages, src/components, src/api)
├─ data/             (synthetic/ fixtures/)
├─ docs/             (PRD.md, dossier.md, demo-script.md)
└─ .github/workflows/ci.yml
```

### 14.6 Environment and commands

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://specid:${DB_PASSWORD}@db:5432/specid` | Database (psycopg 3 driver; password from `.env`) |
| `DB_PASSWORD` | *(set locally)* | Database password |
| `JWT_SECRET` | *(set locally)* | Token signing |
| `JWT_EXPIRE_MIN` | `480` | 8 h expiry |
| `OFFLINE` | `true` | Block outbound calls |
| `EMBEDDINGS_ENABLED` | `true` | Dense channel (P0) |
| `CONSENT_MODE` | `ALL_PARTICIPANTS` | Consent rule (FR-1504; `NONE` only for tests); shown in the footer |
| `GIT_COMMIT` | from `git rev-parse --short HEAD` (`make up`) | Shown by `/health` and in reports |
| `MODEL_DIR` | `./models` | Pre-downloaded embedding model |
| `LLM_ENABLED` | `false` | Local LLM (P2) |
| `SEED_DEMO_USERS` | `true` | Create demo users (local only) |

`make up` · `make down` · `make seed` · `make demo-data` (`SEED=7` default; writes `data/synthetic/seed-7`) · `python -m app.cli decide --file data/synthetic/seed-7` · `make test` · `make eval SEED=7` · `make lint` · `make snapshot`

### 14.7 Git and CI
Trunk-based development, short-lived branches, commit messages prefixed with the requirement ID (for example `FR-602: veto on core conflict`). CI on every push: ruff, black --check, pytest (unit, golden, property, API), coverage report. After T+24, merge on green CI without waiting for review. Tag every gate (`gate-1` … `gate-6`).

### 14.8 Definition of done (per story)
Code + tests (unit and, where relevant, golden or property) · RBAC enforced · audit event written in the same transaction · SYNTHETIC DATA badge present where data appears · no TODO on a P0 path · requirement ID in the commit · demo path still passes.

---

## 15. Demo plan

### 15.1 Five-minute script (scenes marked *opt.* are dropped for a 3-minute slot)

| Time | Screen | Action | Say |
|---|---|---|---|
| 0:00–0:30 | S0 dashboard | Duplicates per CPSE; open one cross-CPSE cluster: three spellings of one valve | "Three CPSEs, one valve, three codes. One Nation – One Material Code starts here." |
| 0:30–1:05 | S13 Look-alike Guard | CL150 vs CL300, SCH40 vs SCH80 vetoed with the decisive attribute | "Text says these are the same. The specification says no." |
| 1:05–1:30 | S6 + rule popover | Decisive row → rule text and `4 IN = DN100` | "Every row cites its rule." |
| 1:30–1:50 *opt.* | S6 | Hidden twin `4IN CL150` = `100NB 150#`; or ask-don't-guess if built | "Different words, same specification." |
| 1:50–2:45 | S6 → **S18** → S8 | Maker proposes, checker (CPSE-B) confirms → card says **"waiting for CPSE-C consent"** → switch to the CPSE-C steward → Consent → CNMC issued, crosswalk + migration pack | "A national code changes three organisations' data, so each of them agrees. Nobody overwrites another CPSE's master." |
| 2:45–3:30 | **S10 impact preview** | Draft "move design_standard to core" → preview: transitions, CNMCs and CPSEs affected → golden tests → Activate blocked/allowed | "Before a national rule changes, you see exactly which past decisions it would change." |
| 3:30–3:45 *opt.* | S9 | Search-before-create hits the new CNMC | "And new duplicates are stopped at creation." |
| 3:45–4:30 | S11 | False merges *k of n* with the 95% bound, two baselines, honesty panel | "This is a bounded number on synthetic data, and we say what it does not mean." |
| 4:30–5:00 | Footer + Wi-Fi off | Counter 0, internal network, search still works | "No CPSE data leaves the machine." |

### 15.2 If something fails

| Failure | Fallback |
|---|---|
| Docker or DB will not start | Restore the pre-built DB snapshot; start the API only; as last resort play the recorded video |
| Run is slow | Use the pre-run snapshot of the run (note the shortcut aloud) |
| Dense channel or LLM errors | They are off by default; the demo never depends on them |
| Laptop dies | Second laptop with the same snapshot; phone screenshots of S6, S9, S11, S13 |
| Wi-Fi-off scene fails | Show the footer counter, the `internal: true` network and the unit test output instead |
| A P1 feature is not ready | Skip its scene (marked *opt.*); never show a half-working screen |

### 15.3 What to say about results
1. "We have a working prototype and a reproducible synthetic benchmark. We show it as synthetic, because real CPSE data is not available to us yet."
2. "Published studies on related tasks give the expected range (slide 4). We target them and report where we fall short."
3. "A pilot with two or three CPSEs is how we get real numbers."

Judge questions and prepared answers: dossier Appendix A.

### 15.4 If a judge asks "what is unique here?"
Answer with what can be **shown**: (1) **every participating CPSE consents** before a national code absorbs its codes, (2) **a rule change shows its effect on past decisions before activation**, (3) **false merges are reported as k of n with a bound**. Then: "Vetoes, look-alike lists, baselines, offline mode and audit chains are things several strong teams also build; we built them carefully. What we did not find in the 41 public repos we inspected is governance across CPSEs — and that is what a national registry needs." (Claims register: Appendix G.)

---

## 16. Risks (prototype-specific)

| ID | Risk | L / I | Mitigation | Owner |
|---|---|---|---|---|
| R-01 | Embedding model cannot be downloaded at the venue | M / M | Pre-download and copy `MODEL_DIR`; dense channel off by default; banner when off | R3 |
| R-02 | Finale rules forbid pre-written code | M / H | Resolve Q-01 early; treat Appendices C and D as specification only; plan the build inside the 36 h | R1 |
| R-03 | Time overrun | H / H | Gates, cut order (14.4), feature freeze at T+30 | R1 |
| R-04 | Extractors miss unseen phrasing | H / M | Residual-token guard; `INSUFFICIENT_DATA`; unknown-token miner; style D test; show abstentions honestly | R2 |
| R-05 | Synthetic results look "too good" | H / M | Honesty rule; style D and adversarial set; label every number; never claim real-world accuracy | R4 |
| R-06 | A false merge appears during the demo | L / H | Golden near-miss tests; critical classes always maker–checker; rehearsed answer: "this is why the checker exists" | R3 |
| R-07 | Merge conflicts and integration drift | M / M | API contract first; vertical slices; integrate at every gate; CI | R1 |
| R-08 | Docker problems on a team laptop | M / M | Test on two OSes in the first 2 hours; DB snapshot and run script as fallback | R1 |
| R-09 | Template rules wrong (STD/XS limits, material families) | M / H | SME review (D-06); rules live in YAML, not code; golden tests per rule | R2 |
| R-10 | Scope creep into LLM or embeddings | H / M | P2 items off by default; cut order | R1 |
| R-11 | Run slower than NFR-01 or out of memory | M / M | **Applied (DEC-09):** demo uses about 3k records, `mem_limit` api 4 GB / db 1 GB, embedding batch 64, one worker; memoise `decide`; tighter blocking | R3 |
| R-12 | UI takes longer than planned | M / M | Build S6 and S9 first; other screens are plain tables | R5 |
| R-13 | Real CPSE data arrives late or in an odd format | M / L | Mapping wizard + quality report; demo stays on synthetic data | R6 |
| R-14 | Judges call the baselines a straw man | M / M | Fair design (normalised text, B2 numeric guard, τ tuned separately on validation, both always shown); say plainly that stronger learned matchers exist and are not compared | R4 |
| R-15 | A judge points to a team or product that already does one of the signature features | M / M | Wording rules (1.10): "differentiated combination", never "first"; answer with the combination and the reproducible numbers | R6 |
| R-16 | Egress guard breaks legitimate local calls (database, tests), or a judge notes that C-level libraries bypass it | M / M | Allow-list loopback and the database host; unit test T-S5; guard can be disabled only by an explicit setting that the footer reflects; state the scope plainly (9.13.7) and rely on the `internal: true` network as the real guarantee | R1 |
| R-18 | P0 is too large for 36 h (core pipeline, ≈ 30 h of P0 features, RBAC, audit) | H / H | SF-11 and SF-6 reuse existing parts (review state machine; `decide(..., templates=draft)`); apply the P0 simplification list; if G3 slips past T+22 switch to the minimum viable demo path (14.4) — consent and impact preview stay in it | R1 |
| R-19 | Judges ask "where is the AI?" because the decision is rule-based | M / H | Show the split plainly: AI for classification (FR-402), semantic search (FR-503), extraction long tail and ranking (P1/P2); rules only where a wrong merge is a safety risk. Say "AI proposes, engineering rules and people decide" | R6 |
| R-20 | Public SIH26099 repos are more mature than our build (several ≥ 20k lines with tests and measured results) | H / M | Do not compete on breadth; win on the governance differentiators and on rigour; never claim parity features as unique; re-run the scan before the finale | R1, R6 |
| R-17 | Signature features push the build beyond 36 hours | H / H | P0 signature features cost about 30 h in total (1.8) and are scheduled before T+26; P1 ones follow the cut order; feature freeze at T+30 | R1 |

---

## 17. Decisions and open questions

### 17.1 Decision log

| ID | Decision | Rationale |
|---|---|---|
| D-01 | **Core / extended attribute policy.** Core attributes must be known and equal. Extended attributes veto when both sides state different values, flag the pair when only one side states them, and are silent when neither does. *This refines dossier B3 / B5, which said any identity-critical attribute missing on either side gives `INSUFFICIENT_DATA`.* | Real descriptions routinely omit trim, standard or voltage; the strict rule would make nearly every pair undecidable. Update B3 text to match |
| D-02 | Criticality default comes from the template; the CSV `criticality` column overrides it per item | Criticality is an item property in real CPSEs |
| D-03 | No Celery in the MVP | Fewer moving parts |
| D-04 | P0 shows a *heuristic* confidence; P1 shows a calibrated probability; the label differs | Do not present a heuristic as a probability |
| D-05 | CNMC is non-significant: `NMC-` + 10 digits + Luhn check digit | Stable IDs; typo detection |
| D-06 | STD / XS schedule limits, class aliases and material families need SME verification before the demo | Domain correctness |
| D-07 | `IDENTICAL` requires equal MPN and manufacturer; otherwise `EQUIVALENT` | Make-independence of the spec level |
| D-08 | Unknown or non-standard sizes and bare `MM` are never guessed | Safety |
| D-09 | Baselines B1 and B2 use **normalised** text, are tuned separately on validation only, and are always shown | A fair comparison; avoids a straw man |
| D-10 | P0: SF-11, SF-6, SF-5 (differentiators) and SF-1, SF-2, SF-4, SF-7 (parity); P1: SF-12, SF-3, SF-8, SF-9, SF-10 | Measured landscape (Competitive Review) |
| D-11 | Uniqueness is worded as a *differentiated combination*, never "first" or "best" | Honesty; judges may know other work |
| D-12 | Positioning: "governed national registry" — governance across CPSEs is the differentiator; matching safety is parity | 41-repo scan, 3 Oct 2026 |
| D-13 | Consent rule `ALL_PARTICIPANTS`: maker's and checker's CPSEs count as consented; others need their own CHECKER | Minimal extra steps for 2-CPSE clusters; real consent for ≥ 3 |
| D-14 | Appendix C stays the verbatim oracle; production `core/` may differ only through an allowlist of named deviations, each with a test that fails on any other difference (C.1) | Keeps specification-by-example honest while fixing defects |
| D-15 | An unresolvable value is unknown, never a conflict (9.5) | A veto must rest on two known values |
| D-16 | Demo and reported numbers use about 3,000 synthetic records (DEC-09) | Fits Docker's default memory on the team's laptops |

### 17.3 Build decisions folded into v0.6

The build keeps `docs/DECISIONS.md` (DEC-01 …). v0.6 of this PRD absorbs these:

| DEC | Where in this PRD |
|---|---|
| DEC-01, 02, 03 | 14.6 (`CONSENT_MODE`, `GIT_COMMIT`, `DATABASE_URL`, `EMBEDDINGS_ENABLED=true`) |
| DEC-04 | 12 (one ADMIN activates after impact preview + golden tests) |
| DEC-06a/b/c | 6.2, 6.3 (dense P0), §2 matrix (impact preview P0), R-17 (≈ 30 h) |
| DEC-09 | SC-1, NFR-01, 10.1 (`n_entities` 1,200), E-1, 6.3 (batch 64) |
| DEC-10 | 11.2, 11.1 footer, 13.4, 14.4, 14.8, FR-1463, FR-1491 (badge, air-gap wording) |
| DEC-14, 15 | 8 (API-39 … API-42) |
| DEC-21, 24, 26 | 9.2, 9.5, 9.9, C.1 |
| DEC-25, 27 | 9.9 (long description), 10.1 (generator rules, files) |
| Phase 4 findings | 9.2 face phrases, 9.3 / 9.5 unresolvable values (Phase 5) |

### 17.2 Open questions

| ID | Question | Why it matters | How to resolve |
|---|---|---|---|
| Q-01 | Do the 2026 finale rules allow code written before the event? | Decides how Appendices C and D may be used | Official rules / college SPOC |
| Q-02 | Finale duration, team size, venue hardware and internet | Schedule and offline needs | Portal / SPOC |
| Q-03 | Will CPSE sample data be provided, in what format, and may it be shown? | L3 evidence, mapping wizard | PS owner via SPOC |
| Q-04 | Can a materials engineer review templates and rules? | R-09 | College / CPSE contact |
| Q-05 | Typical ERP extract format at CPSEs (for example SAP MARA / MAKT exports) | Mapping defaults | CPSE IT contact |
| Q-06 | Is the demo expected on a laptop or a hosted URL? | Deployment | Rules / SPOC |
| Q-07 | Licence of the embedding model and whether it may be bundled | Compliance | Model card |
| Q-08 | Is a working prototype needed at the idea-evaluation stage, before the finale? | Changes the timeline | Portal / SPOC |
| Q-09 | Does the name SpecID clash with an existing product or repo? | Branding | Quick search before the finale |
| Q-10 | Are live comparisons against other tools expected by judges? | We compare only against our own two baselines | Ask the SPOC; otherwise keep the current scope |
| Q-11 | Can the idea PPT (due before the finale) show *planned* screens? | Slide 3 is stronger with a mock of S13 than with text only | Use a mock clearly labelled "planned screen"; replace with a real screenshot later |
| Q-12 | Will the CPSE sample include procurement history and SAP field names? | FR-107, FR-1005 defaults | PS owner (CPCL) via SPOC |

---

# APPENDICES

## Appendix A: Category templates (machine-readable)

One YAML document per category. Verified to match `TEMPLATES` and `RULE_TEXT` in the reference code (core, extended, critical default and the rule texts cited on the evidence card are identical).

```yaml
# SpecID category templates (machine-readable policy). One YAML document per category.
# core = must be known and equal on both sides; extended = veto if both known and different,
# flag for review if known on one side only; tolerant/make never veto.
# rule_text = the sentences cited on the evidence card (must equal RULE_TEXT in the reference code).
id: valve
version: 1
category: VALVE
critical_default: true            # pressure-containing: always maker-checker
core: [valve_type, size_dn, pressure_class, body_material, end_connection]
extended: [design_standard, trim]
tolerant: [paint, packaging]
make: [manufacturer, model, mpn]
value_domains:
  valve_type: [GATE, GLOBE, CHECK, BALL, BUTTERFLY]
  pressure_class: [150, 300, 600, 900, 1500, 2500]
  end_connection: [FLANGED-RF, FLANGED-FF, FLANGED-RTJ, BW, SW, THRD]
rule_text:
  size_dn: "Compared as DN; inch and NB converted by table B.1; non-standard sizes stay unknown"
  body_material: "Same family and same spec; generic vs specific is PARTIAL"
  end_connection: "FLANGED with no face is PARTIAL against a specific face"
aliases:
  valve_type: {GV: GATE, GLV: GLOBE, CV: CHECK, BV: BALL}
  body_material: {WCB: A216-WCB, WCC: A216-WCC, CF8M: A351-CF8M}
rules:
  - "FLANGED without a face -> FLANGED-? (PARTIAL against a specific face, so INSUFFICIENT_DATA)"
---
id: pipe
version: 1
category: PIPE
critical_default: true
core: [size_dn, schedule, material, process]
extended: [end_finish]
tolerant: [marking, coating]
make: [manufacturer, heat_no]
value_domains:
  process: [SEAMLESS, WELDED]
rule_text:
  size_dn: "Compared as DN; inch and NB converted by table B.1; non-standard sizes stay unknown"
  schedule: "STD = SCH40 only for DN <= 250; XS = SCH80 only for DN <= 200"
  material: "Same family and same spec; generic vs specific is PARTIAL"
  process: "A106 implies SEAMLESS"
implied:
  - {when: "material starts with A106", set: {process: SEAMLESS}}
rules:
  - "STD = SCH40 only when DN <= 250 (NPS <= 10); XS = SCH80 only when DN <= 200 (NPS <= 8). SME must verify"
  - "A106 without a grade letter -> A106-? (PARTIAL against A106-B)"
---
id: flange
version: 1
category: FLANGE
critical_default: true
core: [flange_type, size_dn, pressure_class, face, material]
extended: []
tolerant: [paint]
make: [manufacturer]
rule_text:
  size_dn: "Compared as DN; inch and NB converted by table B.1; non-standard sizes stay unknown"
  material: "Same family and same spec; generic vs specific is PARTIAL"
value_domains:
  flange_type: [WN, SO, BLIND, LJ, SW, THRD]
  face: [RF, FF, RTJ]
rules:
  - "Generic stainless (SS316) vs a specific spec (A182-F316): same family -> PARTIAL -> INSUFFICIENT_DATA"
---
id: fastener
version: 1
category: FASTENER
critical_default: false           # may be AUTO_ELIGIBLE unless the item is flagged critical in the CSV
core: [fastener_type, thread, length_mm, strength]
extended: [head, coating]
tolerant: [packaging]
make: [manufacturer, mpn]
value_domains:
  fastener_type: [BOLT, STUD, NUT, SCREW]
  strength: ["4.6", "5.6", "8.8", "10.9", "12.9", "B7", "2H"]
rules:
  - "For NUT, length_mm is not applicable and is dropped from core"
---
id: motor
version: 1
category: MOTOR
critical_default: true
core: [motor_type, power_kw, poles]
extended: [rpm, voltage, ip, mounting]
tolerant: [paint]
make: [manufacturer, model, mpn]
rule_text:
  power_kw: "Equal within 1% (HP converted at 0.7457 kW/HP)"
  rpm: "Equal within 5%"
rules:
  - "power_kw equal within 1% (HP converted at 0.7457 kW/HP); rpm equal within 5%"
  - "Voltage, frame, mounting, IP and Ex are identity-critical in practice but often missing: extended level means 'known on one side only' -> REVIEW"
---
id: gasket
version: 1
category: GASKET
critical_default: true
core: [gasket_type, size_dn, pressure_class, winding_material, filler]
extended: []
tolerant: [packaging]
make: [manufacturer]
rule_text:
  size_dn: "Compared as DN; inch and NB converted by table B.1; non-standard sizes stay unknown"
  winding_material: "Same family and same spec; generic vs specific is PARTIAL"
value_domains:
  gasket_type: [SPIRAL-WOUND]
  filler: [GRAPHITE, PTFE]
```

## Appendix B: Seed tables

**B.1 NPS (inch) to DN (mm)**

| NPS | 1/2 | 3/4 | 1 | 1-1/4 | 1-1/2 | 2 | 2-1/2 | 3 | 4 | 5 | 6 | 8 | 10 | 12 | 14 | 16 | 18 | 20 | 24 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DN | 15 | 20 | 25 | 32 | 40 | 50 | 65 | 80 | 100 | 125 | 150 | 200 | 250 | 300 | 350 | 400 | 450 | 500 | 600 |

**B.2 Schedule, class and speed rules (SME to verify, D-06)**

| Rule | Value |
|---|---|
| `STD` equals `SCH40` | only for DN ≤ 250 (NPS ≤ 10) |
| `XS` equals `SCH80` | only for DN ≤ 200 (NPS ≤ 8) |
| Pressure classes accepted | 150, 300, 600, 900, 1500, 2500 |
| Bolt strength classes accepted | 4.6, 5.6, 8.8, 10.9, 12.9; stud / nut grades `B7`, `2H` |
| Synchronous speed at 50 Hz | 2 poles 3000 rpm · 4 poles 1500 · 6 poles 1000 · 8 poles 750 (rated rpm is slightly lower, hence the 5% tolerance) |

**B.3 Material canonical codes and families (reference code `MAT` and `family`)**

| Written as | Canonical | Family | Generic? |
|---|---|---|---|
| `A216 WCB`, `WCB` | `A216-WCB` | CS | no |
| `A216 WCC`, `WCC` | `A216-WCC` | CS | no |
| `A105` | `A105` | CS | no |
| `A106 GR.B`, `A106B` | `A106-B` | CS | no |
| `A106` (no grade) | `A106-?` | CS | **yes** |
| `A53 GR.B` | `A53-B` | CS | no |
| `A182 F316`, `F316` | `A182-F316` | 316 | no |
| `A351 CF8M`, `CF8M` | `A351-CF8M` | 316 | no |
| `SS316`, `316SS` | `SS316` | 316 | **yes** |
| `A182 F304`, `F304` | `A182-F304` | 304 | no |
| `A351 CF8`, `CF8` | `A351-CF8` | 304 | no |
| `SS304`, `304SS` | `SS304` | 304 | **yes** |

Two *specific* codes of the same family but different spec (for example `A182-F316` forged vs `A351-CF8M` cast) are a **CONFLICT**; a generic code against a specific one of the same family is **PARTIAL**.

## Appendix C: Reference implementation (tested specification by example)

`backend/app/core/specid_ref.py`: Python 3.10+, standard library only except `text_sim` (needs `rapidfuzz`). Not production code. Sections 1–5 are the core pipeline; section 6 holds the signature features (cited decisions, baselines, look-alike guard, ask-don't-guess, impact preview); section 7 is the egress guard.

```python
"""specid_ref.py - reference implementation (specification by example) for the SpecID MVP.
Not production code. Python 3.10+. Standard library only, except text_sim() which needs rapidfuzz (baselines, look-alike guard)."""
import copy
import ipaddress
import re
import socket

# ---------- tables ----------
NPS_DN = {"1/2": 15, "3/4": 20, "1": 25, "1-1/4": 32, "1-1/2": 40, "2": 50, "2-1/2": 65, "3": 80, "4": 100,
          "5": 125, "6": 150, "8": 200, "10": 250, "12": 300, "14": 350, "16": 400, "18": 450, "20": 500, "24": 600}
DN_NPS = {v: k for k, v in NPS_DN.items()}
CLASSES = {150, 300, 600, 900, 1500, 2500}
STOP = {"ASTM", "TYPE", "FOR", "OF", "AND", "WITH", "TO", "THE", "A", "ON"}
WATCH = {"NACE", "LTCS", "CRYO", "CRYOGENIC", "BELLOWS", "SOUR", "HIC", "ATEX", "IECEX", "FIRESAFE", "FIREPROOF", "EPOXY", "LINED"}

def take(rx, t):
    m = re.search(rx, t)
    return (m, t[:m.start()] + " " + t[m.end():]) if m else (None, t)

def note(a, key, text):
    """Record a conversion or inference so the evidence card can show it (provenance)."""
    if text: a.setdefault("_notes", {})[key] = text

# ---------- 1. normalise ----------
def normalise(t):
    t = t.upper()
    t = re.sub(r'["\u201c\u201d]', " IN ", t)
    t = re.sub(r"[,;()]", " ", t)
    t = re.sub(r"/(?=[A-Z])", " ", t)                            # SS316/GRAF -> SS316 GRAF (fractions keep their slash)
    t = re.sub(r"(\d)\s*(?:INCHES|INCH|IN)\b", r"\1 IN", t)       # 4IN, 4 INCH -> 4 IN
    t = re.sub(r"\bDN\s*(\d+)\b", r"\1 NB", t)                    # DN100 -> 100 NB
    t = re.sub(r"(\d)\s*NB\b", r"\1 NB", t)
    t = re.sub(r"(\d+)\s*#", r"CL\1", t)                          # 150# -> CL150
    t = re.sub(r"\bCLASS\s*(\d+)", r"CL\1", t)
    t = re.sub(r"\bCL\s+(\d+)", r"CL\1", t)
    t = re.sub(r"\bSCH(?:EDULE)?\.?\s*(\d+S?|STD|XS|XXS)\b", r"SCH\1", t)
    t = re.sub(r"\bGR(?:ADE)?\.?\s*([A-Z0-9][A-Z0-9.]*)", r"GR\1", t)   # GR.B / GRADE B -> GRB
    for a, b in (("SMLS", "SEAMLESS"), ("FLGD", "FLANGED"), ("WND", "WOUND"), ("GRAF", "GRAPHITE"), ("HD", "HEAD"), ("FLG", "FLANGE")):
        t = re.sub(rf"\b{a}\b", b, t)
    return re.sub(r"\s+", " ", t).strip()

# ---------- 2. attribute extractors (Tier 1: rules) ----------
def take_size(t):
    m, t2 = take(r"\b((?:\d+[- ])?\d+/\d+|\d+)\s*IN\b", t)
    if m:
        nps = m.group(1).replace(" ", "-"); dn = NPS_DN.get(nps)
        return dn, t2, (f"{nps} IN = DN{dn}" if dn else f"{nps} IN is not a standard size")
    m, t2 = take(r"\b(\d+)\s*NB\b", t)
    if m:
        dn = int(m.group(1)); ok = dn in DN_NPS
        return (dn if ok else None), t2, (f"{dn} NB = DN{dn}" if ok else f"{dn} NB is not a standard size")
    return None, t, None

def take_class(t):
    m, t2 = take(r"\bCL(\d{3,4})\b", t)
    return ((int(m.group(1)) if int(m.group(1)) in CLASSES else None), t2) if m else (None, t)

MAT = [(r"\bA216\s*(WCB|WCC)\b", "A216-{0}"), (r"\b(WCB|WCC)\b", "A216-{0}"),
       (r"\bA351\s*(CF8M|CF8)\b", "A351-{0}"), (r"\b(CF8M|CF8)\b", "A351-{0}"),
       (r"\bA182\s*F\s*(304L?|316L?|321|347)\b", "A182-F{0}"), (r"\bF(304L?|316L?|321|347)\b", "A182-F{0}"),
       (r"\bA105\b", "A105"), (r"\bA106\s*(?:GR)?\s*([ABC])\b", "A106-{0}"), (r"\bA106\b", "A106-?"),
       (r"\bA53\s*(?:GR)?\s*([AB])\b", "A53-{0}"),
       (r"\bSS\s*(304L?|316L?|321|347)\b", "SS{0}"), (r"\b(304L?|316L?|321|347)\s*SS\b", "SS{0}")]

def take_material(t):
    for rx, fmt in MAT:
        m, t2 = take(rx, t)
        if m:
            code = fmt.format(*m.groups()); written = m.group(0).replace(" ", "")
            return code, t2, (None if written.startswith(code.split("-")[0]) else f"{m.group(0)} -> {code}")
    return None, t, None

def ex_valve(t):
    a = {}
    m, t = take(r"\b(GATE|GLOBE|CHECK|BALL|BUTTERFLY)\b", t)
    if m: a["valve_type"] = m.group(1)
    else:
        m, t = take(r"\b(GV|GLV|CV|BV)\b", t)
        a["valve_type"] = {"GV": "GATE", "GLV": "GLOBE", "CV": "CHECK", "BV": "BALL"}[m.group(1)] if m else None
        if m: note(a, "valve_type", f"{m.group(1)} = {a['valve_type']}")
    a["size_dn"], t, n = take_size(t); note(a, "size_dn", n); a["pressure_class"], t = take_class(t)
    a["body_material"], t, n = take_material(t); note(a, "body_material", n)
    fl, t = take(r"\bFLANGED\b", t); face, t = take(r"\b(RF|FF|RTJ)\b", t)
    if fl or face: a["end_connection"] = "FLANGED-" + (face.group(1) if face else "?")
    else:
        m, t = take(r"\b(BW|SW|SCRD|THRD|NPT)\b", t)
        a["end_connection"] = {"BW": "BW", "SW": "SW"}.get(m.group(1), "THRD") if m else None
    m, t = take(r"\bAPI\s*(600|602|603|6D|608|594)\b", t); a["design_standard"] = "API-" + m.group(1) if m else None
    m, t = take(r"\bTRIM\s*([A-Z0-9]+)\b", t); a["trim"] = m.group(1) if m else None
    return a, t

def ex_pipe(t):
    a = {}
    a["size_dn"], t, n = take_size(t); note(a, "size_dn", n)
    m, t = take(r"\bSCH(\d+S?|STD|XS|XXS)\b", t)
    if not m: m, t = take(r"\b()(STD|XS|XXS)\b", t); s = m.group(2) if m else None   # bare STD / XS / XXS
    else: s = m.group(1)
    dn = a["size_dn"]
    if s == "STD" and dn and dn <= 250: s = "40"; note(a, "schedule", f"STD = SCH40 (DN{dn} <= 250)")   # SME to verify
    if s == "XS" and dn and dn <= 200: s = "80"; note(a, "schedule", f"XS = SCH80 (DN{dn} <= 200)")     # SME to verify
    a["schedule"] = s
    a["material"], t, n = take_material(t); note(a, "material", n)
    m, t = take(r"\b(SEAMLESS|ERW|WELDED)\b", t)
    p = {"SEAMLESS": "SEAMLESS", "ERW": "WELDED", "WELDED": "WELDED"}[m.group(1)] if m else None
    if p is None and (a["material"] or "").startswith("A106"): p = "SEAMLESS"; note(a, "process", "implied by A106")   # spec-implied
    a["process"] = p
    m, t = take(r"\b(PE|BE|PBE|TBE)\b", t); a["end_finish"] = m.group(1) if m else None
    return a, t

def ex_flange(t):
    a = {}
    typ = None
    for rx, v in ((r"\bWELD\s*NECK\b|\bWN\b", "WN"), (r"\bSLIP\s*-?\s*ON\b|\bSO\b", "SO"), (r"\bBLIND\b|\bBL\b", "BLIND"),
                  (r"\bLAP\s*JOINT\b|\bLJ\b", "LJ"), (r"\bSOCKET\s*WELD\b|\bSW\b", "SW"), (r"\bTHREADED\b|\bTHRD\b|\bSCRD\b", "THRD")):
        m, t = take(rx, t)
        if m: typ = v; break
    a["flange_type"] = typ
    a["size_dn"], t, n = take_size(t); note(a, "size_dn", n); a["pressure_class"], t = take_class(t)
    m, t = take(r"\b(RF|FF|RTJ)\b", t); a["face"] = m.group(1) if m else None
    a["material"], t, n = take_material(t); note(a, "material", n)
    return a, t

def ex_fastener(t):
    a = {}
    m, t = take(r"\b(STUD|NUT|BOLT|SCREW)\b", t); a["fastener_type"] = m.group(1) if m else None
    m, t = take(r"\bM(\d{1,2})\s*X\s*(\d{1,3})\b", t)
    if m: a["thread"], a["length_mm"] = "M" + m.group(1), int(m.group(2))
    else:
        m, t = take(r"\bM(\d{1,2})\b", t); a["thread"] = "M" + m.group(1) if m else None; a["length_mm"] = None
    m, t = take(r"\b(?:A19[34]\s*)?(?:GR)?(4\.6|5\.6|8\.8|10\.9|12\.9|B7|2H)\b", t); a["strength"] = m.group(1) if m else None
    m, t = take(r"\b(HEX|SOCKET|CSK)\b", t); a["head"] = m.group(1) if m else None; _, t = take(r"\bHEAD\b", t)
    m, t = take(r"\b(ZN|ZINC|HDG|PTFE|GALV\w*)\b", t)
    a["coating"] = ("ZINC" if m.group(1) in ("ZN", "ZINC") else m.group(1)) if m else None; _, t = take(r"\bPLATED\b", t)
    if m and m.group(1) == "ZN": note(a, "coating", "ZN = ZINC")
    return a, t

def ex_motor(t):
    a = {}
    ind = bool(re.search(r"\b(INDUCTION|IND|SQ|SQUIRREL)\b", t)); ac = bool(re.search(r"\bAC\b", t))
    a["motor_type"] = "AC-IND" if (ind and ac) else ("AC" if ac else None)
    for w in ("AC", "INDUCTION", "IND", "SQ", "SQUIRREL", "CAGE"): _, t = take(rf"\b{w}\b", t)
    m, t = take(r"\b(\d+(?:\.\d+)?)\s*KW\b", t)
    if m: a["power_kw"] = float(m.group(1))
    else:
        m, t = take(r"\b(\d+(?:\.\d+)?)\s*HP\b", t); a["power_kw"] = round(float(m.group(1)) * 0.7457, 1) if m else None
        if m: note(a, "power_kw", f"{m.group(1)} HP = {a['power_kw']} kW")
    m, t = take(r"\b(\d{1,2})\s*(?:P|POLES?)\b", t); a["poles"] = int(m.group(1)) if m else None
    m, t = take(r"\b(\d{3,4})\s*RPM\b", t); a["rpm"] = int(m.group(1)) if m else None
    m, t = take(r"\b(\d{3,4})\s*V\b", t); a["voltage"] = int(m.group(1)) if m else None
    m, t = take(r"\bIP\s*(\d{2})\b", t); a["ip"] = "IP" + m.group(1) if m else None
    m, t = take(r"\b(B3|B5|B35|V1)\b", t); a["mounting"] = m.group(1) if m else None
    a["ex"] = a["frame"] = None
    return a, t

def ex_gasket(t):
    a = {}
    m, t = take(r"\bSPIRAL\s*WOUND\b|\bSPIRAL\b", t); a["gasket_type"] = "SPIRAL-WOUND" if m else None
    a["size_dn"], t, n = take_size(t); note(a, "size_dn", n); a["pressure_class"], t = take_class(t)
    a["winding_material"], t, n = take_material(t); note(a, "winding_material", n)
    m, t = take(r"\b(GRAPHITE|PTFE)\b", t); a["filler"] = m.group(1) if m else None
    return a, t

CATS = [("VALVE", r"\bVALVE\b|\bGV\b|\bGLV\b|\bBV\b", ex_valve), ("GASKET", r"\bGASKET\b", ex_gasket), ("FLANGE", r"\bFLANGE\b", ex_flange),
        ("PIPE", r"\bPIPE\b", ex_pipe), ("FASTENER", r"\b(BOLT|STUD|NUT|SCREW)\b", ex_fastener), ("MOTOR", r"\bMOTOR\b", ex_motor)]

def extract(text, mpn=None, maker=None):
    t = normalise(text)
    for cat, rx, fn in CATS:
        if re.search(rx, t):
            if cat != "FASTENER": _, t = take(r"\b(VALVE|GASKET|FLANGE|PIPE|MOTOR)\b", t)
            attrs, t = fn(t)
            notes = attrs.pop("_notes", {})
            toks = [x for x in re.findall(r"[A-Z0-9][A-Z0-9.\-]*", t) if x not in STOP]
            return {"category": cat, "attrs": attrs, "notes": notes, "residual": toks, "mpn": mpn, "maker": maker}
    return {"category": None, "attrs": {}, "notes": {}, "residual": re.findall(r"[A-Z0-9][A-Z0-9.\-]*", t), "mpn": mpn, "maker": maker}

# ---------- 3. templates and decision ----------
TEMPLATES = {
 "VALVE":    dict(core=["valve_type", "size_dn", "pressure_class", "body_material", "end_connection"], ext=["design_standard", "trim"], critical=True),
 "PIPE":     dict(core=["size_dn", "schedule", "material", "process"], ext=["end_finish"], critical=True),
 "FLANGE":   dict(core=["flange_type", "size_dn", "pressure_class", "face", "material"], ext=[], critical=True),
 "FASTENER": dict(core=["fastener_type", "thread", "length_mm", "strength"], ext=["head", "coating"], critical=False),
 "MOTOR":    dict(core=["motor_type", "power_kw", "poles"], ext=["rpm", "voltage", "ip", "mounting"], critical=True),
 "GASKET":   dict(core=["gasket_type", "size_dn", "pressure_class", "winding_material", "filler"], ext=[], critical=True)}

_MAT_TEXT = "Same family and same spec; generic vs specific is PARTIAL"
RULE_TEXT = {"size_dn": "Compared as DN; inch and NB converted by table B.1; non-standard sizes stay unknown",
             "schedule": "STD = SCH40 only for DN <= 250; XS = SCH80 only for DN <= 200",
             "material": _MAT_TEXT, "body_material": _MAT_TEXT, "winding_material": _MAT_TEXT,
             "process": "A106 implies SEAMLESS", "power_kw": "Equal within 1% (HP converted at 0.7457 kW/HP)",
             "rpm": "Equal within 5%", "end_connection": "FLANGED with no face is PARTIAL against a specific face"}

def rule(cat, attr, level):
    """Every comparison cites the rule that produced it (shown on the evidence card)."""
    default = "Must match" if level == "core" else "Conflict vetoes; a value stated on one side only flags the pair"
    return {"id": f"{cat}.{attr}", "text": RULE_TEXT.get(attr, default)}

def family(code):
    if code.startswith("A182-F"): return code[6:]
    if code.startswith("SS"): return code[2:]
    if code == "A351-CF8M": return "316"
    if code == "A351-CF8": return "304"
    if code.startswith(("A216", "A105", "A106", "A53")): return "CS"
    return code

def compare(name, x, y):
    if x is None and y is None: return "MISSING_BOTH"
    if x is None or y is None: return "MISSING_ONE"
    if x == y: return "MATCH"
    if name in ("material", "body_material", "winding_material"):
        if family(x) != family(y): return "CONFLICT"
        gx, gy = x.endswith("?") or x.startswith("SS"), y.endswith("?") or y.startswith("SS")
        return "PARTIAL" if gx != gy else "CONFLICT"            # one generic, one specific, same family
    if name == "end_connection":
        if x.startswith("FLANGED") and y.startswith("FLANGED") and "?" in (x[-1], y[-1]): return "PARTIAL"
        return "CONFLICT"
    if name == "power_kw": return "MATCH" if abs(x - y) <= 0.01 * max(x, y) else "CONFLICT"
    if name == "rpm": return "MATCH" if abs(x - y) <= 0.05 * max(x, y) else "CONFLICT"
    return "CONFLICT"

def decide(A, B, templates=None):
    """Veto -> unknown-state -> verdict. Returns verdict, route, reasons, evidence card.
    `templates` lets a draft rulebook be previewed without activating it."""
    if A["category"] is None or B["category"] is None:
        return dict(verdict="INSUFFICIENT_DATA", route="REVIEW", reasons=["category not recognised"], evidence=[])
    if A["category"] != B["category"]:
        return dict(verdict="NOT_EQUIVALENT", route="NONE", reasons=["category differs"], evidence=[])
    T = (templates or TEMPLATES)[A["category"]]
    core = [c for c in T["core"] if not (A["attrs"].get("fastener_type") == "NUT" and c == "length_mm")]
    ev, conflicts, missing, flags = [], [], [], []
    for level, names in (("core", core), ("ext", T["ext"])):
        for n in names:
            s = compare(n, A["attrs"].get(n), B["attrs"].get(n)); r = rule(A["category"], n, level)
            ev.append(dict(attr=n, level=level, a=A["attrs"].get(n), b=B["attrs"].get(n), status=s,
                           rule=r["id"], rule_text=r["text"], note_a=A.get("notes", {}).get(n), note_b=B.get("notes", {}).get(n)))
            if s == "CONFLICT": conflicts.append(n)
            elif level == "core" and s in ("MISSING_ONE", "MISSING_BOTH", "PARTIAL"): missing.append(n)
            elif level == "ext" and s in ("MISSING_ONE", "PARTIAL"): flags.append(n + " unverified")
    tech = lambda r: {x for x in r if any(c.isdigit() for c in x) or x in WATCH}
    diff = tech(A["residual"]) ^ tech(B["residual"])
    if diff: flags.append("unexplained tokens: " + " ".join(sorted(diff)))
    if conflicts: return dict(verdict="NOT_EQUIVALENT", route="NONE", reasons=["conflict: " + ", ".join(conflicts)], evidence=ev)
    if missing: return dict(verdict="INSUFFICIENT_DATA", route="REVIEW", reasons=["core attribute not verifiable: " + ", ".join(missing)], evidence=ev)
    same_make = A["mpn"] and A["mpn"] == B["mpn"] and (A["maker"] or "").upper() == (B["maker"] or "").upper()
    if T["critical"]: flags.append("critical class: maker-checker")
    return dict(verdict="IDENTICAL" if same_make else "EQUIVALENT", route="REVIEW" if flags else "AUTO_ELIGIBLE", reasons=flags, evidence=ev)

# ---------- 4. constrained clustering (no cluster may contain a conflict) ----------
def constrained_clusters(n, edges, conflict):
    """edges: [(i, j, score)] for EQUIVALENT/IDENTICAL pairs; conflict(i, j) -> True if verdict would be NOT_EQUIVALENT."""
    parent, members = list(range(n)), {i: {i} for i in range(n)}
    def find(x):
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for i, j, s in sorted(edges, key=lambda e: -e[2]):
        ri, rj = find(i), find(j)
        if ri != rj and not any(conflict(a, b) for a in members[ri] for b in members[rj]):
            parent[rj] = ri; members[ri] |= members.pop(rj)
    return sorted(map(sorted, members.values()))

# ---------- 5. CNMC id (non-significant, Luhn check digit) and 40-char SAP short text ----------
def luhn_digit(body):
    total = 0
    for i, ch in enumerate(reversed(body)):
        d = int(ch) * (2 if i % 2 == 0 else 1)
        total += d - 9 if d > 9 else d
    return (10 - total % 10) % 10

def new_cnmc(seq): body = f"{seq:010d}"; return f"NMC-{body}{luhn_digit(body)}"
def cnmc_valid(c): m = re.fullmatch(r"NMC-(\d{10})(\d)", c); return bool(m) and luhn_digit(m.group(1)) == int(m.group(2))

def short_desc(S, limit=40):
    a, c = S["attrs"], S["category"]; inch = lambda: DN_NPS.get(a.get("size_dn"), "?") + "IN"
    parts = {"VALVE": ["VLV", a.get("valve_type"), inch(), f"CL{a.get('pressure_class')}", a.get("body_material"), (a.get("end_connection") or "").replace("FLANGED-", "FLGD ")],
             "PIPE": ["PIPE", {"SEAMLESS": "SMLS", "WELDED": "ERW"}.get(a.get("process")), inch(), f"SCH{a.get('schedule')}", a.get("material")],
             "FLANGE": ["FLG", a.get("flange_type"), inch(), f"CL{a.get('pressure_class')}", a.get("face"), a.get("material")],
             "FASTENER": [a.get("fastener_type"), a.get("head"), f"{a.get('thread')}X{a.get('length_mm')}" if a.get("length_mm") else a.get("thread"), a.get("strength"), {"ZINC": "ZN"}.get(a.get("coating"), a.get("coating"))],
             "MOTOR": ["MOTOR", a.get("motor_type", "").replace("-", " "), f"{a.get('power_kw'):g}KW" if a.get("power_kw") else None, f"{a.get('poles')}P"],
             "GASKET": ["GASKET", "SPW", inch(), f"CL{a.get('pressure_class')}", a.get("winding_material"), (a.get("filler") or "")[:5]]}[c]
    s = " ".join(p for p in parts if p)
    return s if len(s) <= limit else None          # None -> abbreviate further or route to a human


# ---------- 6. signature features: baselines, look-alike guard, ask-don't-guess, rule-impact preview ----------
def text_sim(x, y):
    """Token-set similarity of the NORMALISED texts: a deliberately fair text-only baseline. Needs rapidfuzz."""
    from rapidfuzz import fuzz
    return fuzz.token_set_ratio(normalise(x), normalise(y)) / 100

def numeric_tokens(t): return sorted(re.findall(r"\d+(?:\.\d+)?", t.upper()))
def baseline_b1(x, y, tau): return text_sim(x, y) >= tau                                   # text only
def baseline_b2(x, y, tau): return text_sim(x, y) >= tau and numeric_tokens(x) == numeric_tokens(y)   # text + numbers must agree

def lookalike_class(sim, verdict, hi=0.85, lo=0.75):
    """Near-Miss Radar: LOOKALIKE_VETOED = text says 'same', SpecID vetoed; HIDDEN_TWIN = text says 'different', SpecID says equivalent."""
    if verdict == "NOT_EQUIVALENT" and sim >= hi: return "LOOKALIKE_VETOED"
    if verdict in ("EQUIVALENT", "IDENTICAL") and sim <= lo: return "HIDDEN_TWIN"
    return None

def supply_attribute(S, attr, value, source):
    """Ask-don't-guess loop: a reviewer supplies a missing attribute; provenance is kept; the pair is then re-decided."""
    return {**S, "attrs": {**S["attrs"], attr: value}, "notes": {**S.get("notes", {}), attr: f"supplied by user: {source}"}}

def impact_preview(pairs, new_templates):
    """Rulebook impact preview: which stored pairs would change verdict or route under a draft template set."""
    out = []
    for i, (a, b) in enumerate(pairs):
        old, new = decide(a, b), decide(a, b, new_templates)
        if (old["verdict"], old["route"]) != (new["verdict"], new["route"]):
            out.append(dict(pair=i, old=old["verdict"], new=new["verdict"], old_route=old["route"], new_route=new["route"]))
    return out


# ---------- 7. air-gap proof: egress guard (defence in depth; the network-level guarantee is the internal Compose network) ----------
class EgressGuard:
    """Refuse every outbound connection and name lookup except loopback and explicitly allowed hosts (for example the database); count the attempts."""
    def __init__(self, allowed=()):
        self.allowed, self.blocked, self._orig = set(allowed) | {"localhost"}, 0, None
    def _check(self, host):
        try: ok = ipaddress.ip_address(host).is_loopback
        except ValueError: ok = False
        if not (ok or host in self.allowed):
            self.blocked += 1
            raise PermissionError(f"egress blocked: {host}")
    def install(self):
        g, self._orig = self, (socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo)
        def connect(sock, address): g._check(address[0]); return g._orig[0](sock, address)
        def connect_ex(sock, address): g._check(address[0]); return g._orig[1](sock, address)
        def getaddrinfo(host, *a, **k): g._check(host); return g._orig[2](host, *a, **k)
        socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo = connect, connect_ex, getaddrinfo
    def uninstall(self):
        socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo = self._orig
```

### C.1 Production deviations from this reference (allowlist)

The code block above is copied byte-for-byte to `backend/tests/reference/specid_ref.py` and must not be edited. `tests/reference/test_conformance.py` compares production `core/` with it and fails on any difference except these, each scoped by a predicate and proven by a planted-difference test:

| DEV | Production behaviour | Applies only when |
|---|---|---|
| DEV-1 | `short_desc` leaves out missing parts (no `None`, `CLNone`, `?IN`, no crash on a missing `motor_type`); empty → none | The reference raises or prints a missing value |
| DEV-2 | The NUT rule drops `length_mm` when **either** side is a nut (symmetric evidence) | Side B is the nut and side A is not; verdict and route stay equal |
| DEV-3 | Unicode NFKC and removal of non-printing characters first (TRD TR-MOD-01) | The input has a non-ASCII or non-printing character |
| DEV-4 | Rules repeat until the output stops changing, max 8 passes (9.2) | The reference itself is not idempotent on the input; then `core/` equals the reference on the reference's fixed point |
| DEV-5 | `IDENTICAL` needs MPN and manufacturer present on both sides, case-insensitive (9.5) | A manufacturer is missing, or MPN / manufacturer differ only in case or spaces |
| *planned (Phase 5)* | Face phrases (`RAISED FACE` → `RF` …), unresolvable values are unknown (9.5) | Logged as new DEV entries when built |

## Appendix D: Tests for the reference implementation

`backend/tests/test_specid_ref.py`: plain asserts, run with `python test_specid_ref.py` (no pytest needed).

```python
import random, re
from specid_ref import *

E = extract
def V(a, b, **kw):
    r = decide(E(a), E(b)); r2 = decide(E(b), E(a))
    assert r["verdict"] == r2["verdict"], ("asymmetric verdict", a, b, r["verdict"], r2["verdict"])   # symmetry property
    return r

# ---- 1. golden pairs (the 12 illustrative pairs from the dossier, A4.3) ----
NOT = [("VALVE GATE 4IN CL150 A216 WCB FLGD RF", "VALVE GATE 4IN CL300 A216 WCB FLGD RF"),
       ("PIPE SMLS 6IN SCH40 A106 GR.B", "PIPE SMLS 6IN SCH80 A106 GR.B"),
       ("BOLT HEX M16X80 GR8.8 ZN", "BOLT HEX M16X90 GR8.8 ZN"),
       ("FLANGE WN 4IN CL150 RF A105", "FLANGE WN 4IN CL150 RF A182 F316"),
       ("MOTOR AC SQ 100KW 1500RPM 4P", "MOTOR AC SQ 110KW 1500RPM 4P"),
       ("GASKET SPIRAL WND 4IN CL150 SS316/GRAF", "GASKET SPIRAL WND 4IN CL300 SS316/GRAF")]
EQV = [("VALVE GATE 4IN CL150 A216 WCB FLGD RF", "GV 100NB 150# WCB RF FLANGED"),
       ("PIPE SMLS 6IN SCH40 A106 GR.B", "PIPE 150NB SCH 40 A106 GRADE B SEAMLESS"),
       ("BOLT HEX M16X80 GR8.8 ZN", "BOLT, HEX HD, M16 X 80, 8.8, ZINC"),
       ("FLANGE WN 4IN CL150 RF A105", "WELD NECK FLANGE 100NB 150# RF ASTM A105"),
       ("MOTOR AC SQ 100KW 1500RPM 4P", "AC INDUCTION MOTOR SQ CAGE 100 KW 4 POLE 1500 RPM"),
       ("GASKET SPIRAL WND 4IN CL150 SS316/GRAF", "SPIRAL WOUND GASKET 100NB 150# 316SS GRAPHITE")]
for a, b in NOT: assert V(a, b)["verdict"] == "NOT_EQUIVALENT", (a, b, V(a, b))
for a, b in EQV: assert V(a, b)["verdict"] == "EQUIVALENT", (a, b, V(a, b))
print("golden pairs: 12/12 pass")

# ---- 2. extra behaviour cases ----
cases = [
 ("PIPE 6IN STD A106 GR B SEAMLESS", "PIPE SMLS 150NB SCH40 A106B", "EQUIVALENT"),            # STD = SCH40 up to NPS 10
 ("PIPE 12IN STD A106B", "PIPE 12IN SCH40 A106B", "NOT_EQUIVALENT"),                           # STD != SCH40 at NPS 12 (SME to verify)
 ("FLANGE WN 4IN CL150 RF SS316", "FLANGE WN 4IN CL150 RF A182 F316", "INSUFFICIENT_DATA"),  # generic vs specific material
 ("VALVE GATE 4IN CL150 WCB FLANGED", "VALVE GATE 4IN CL150 WCB FLANGED RF", "INSUFFICIENT_DATA"),  # face unknown on one side
 ("VALVE GATE 4IN CL150 WCB FLANGED RF", "VALVE GLOBE 4IN CL150 WCB FLANGED RF", "NOT_EQUIVALENT"),
 ("VALVE GATE 4IN CL150 WCB FLANGED RF", "FLANGE WN 4IN CL150 RF A105", "NOT_EQUIVALENT"),
 ("NUT HEX M20 2H", "HEX NUT M20 A194 2H", "EQUIVALENT"),
 ("STUD BOLT M20X120 B7 PTFE", "STUD M20 X 120 A193 B7 PTFE", "EQUIVALENT"),
 ("MOTOR AC IND 125HP 4P", "MOTOR AC SQ 93KW 4 POLE", "EQUIVALENT"),                          # HP -> kW within 1%
 ("MOTOR AC SQ 100KW 4P", "MOTOR AC SQ 100KW 6P", "NOT_EQUIVALENT"),
 ("PIPE 7IN SCH40 A106B", "PIPE 7IN SCH40 A106B", "INSUFFICIENT_DATA"),                       # non-standard size is not guessed
 ("SOMETHING ELSE 123", "SOMETHING ELSE 123", "INSUFFICIENT_DATA"),                           # unknown category
 ("VALVE GATE 4IN CL150 WCB FLANGED RF API 600", "VALVE GATE 4IN CL150 WCB FLANGED RF API 6D", "NOT_EQUIVALENT"),
]
for a, b, exp in cases:
    r = V(a, b); assert r["verdict"] == exp, (a, b, exp, r["verdict"], r["reasons"])
print("extra cases:", len(cases), "pass")

r = V("VALVE GATE 4IN CL150 WCB FLANGED RF API 600", "VALVE GATE 4IN CL150 WCB FLANGED RF")
assert r["verdict"] == "EQUIVALENT" and r["route"] == "REVIEW" and any("design_standard unverified" in x for x in r["reasons"])
r = V("VALVE GATE 4IN CL150 WCB FLANGED RF NACE", "VALVE GATE 4IN CL150 WCB FLANGED RF")
assert r["verdict"] == "EQUIVALENT" and r["route"] == "REVIEW" and any("NACE" in x for x in r["reasons"])   # residual-token guard
r = V("NUT HEX M20 2H", "HEX NUT M20 A194 2H"); assert r["route"] == "AUTO_ELIGIBLE"                  # non-critical class
a = E("PUMP BOLT M16X80 8.8", mpn="X-1", maker="ACME"); b = E("BOLT M16X80 8.8", mpn="X-1", maker="Acme")
assert decide(a, b)["verdict"] == "IDENTICAL"
print("route/flag/identical checks pass")

# ---- 3. property: an extracted core/ext CONFLICT never yields EQUIVALENT/IDENTICAL; verdict symmetric ----
random.seed(7)
SIZES = [(2, "DN50"), (3, "DN80"), (4, "DN100"), (6, "DN150"), (8, "DN200")]; CL = [150, 300, 600]; GR = [("A216 WCB", "WCB"), ("A351 CF8M", "CF8M")]
def render(e, st):
    full, short = e["g"]
    s = [f"VALVE GATE {e['i']}IN CL{e['c']} {full} FLGD RF", f"GV {e['d'][2:]}NB {e['c']}# {short} RF FLANGED",
         f"GATE VALVE, {e['i']} INCH, CLASS {e['c']}, ASTM {full}, RAISED FACE FLANGED"][st]
    return s[:40] if st < 2 else s
viol = 0
for _ in range(1500):
    i, d = random.choice(SIZES); e = {"i": i, "d": d, "c": random.choice(CL), "g": random.choice(GR)}
    n = dict(e); f = random.choice("icg")
    if f == "i": n["i"], n["d"] = random.choice([s for s in SIZES if s[0] != i])
    elif f == "c": n["c"] = random.choice([c for c in CL if c != e["c"]])
    else: n["g"] = random.choice([g for g in GR if g != e["g"]])
    st = random.randrange(3)
    r = decide(E(render(e, st)), E(render(n, st)))
    viol += r["verdict"] in ("EQUIVALENT", "IDENTICAL")
assert viol == 0, viol
print("property test: hard negatives never EQUIVALENT (1500 generated pairs, smoke test only)")

# ---- 4. CNMC ----
random.seed(1)
for _ in range(500):
    c = new_cnmc(random.randrange(10**10)); assert cnmc_valid(c)
    body = c[4:14]; chk = c[14]
    for p in range(10):
        for dgt in "0123456789":
            if dgt != body[p]: assert not cnmc_valid("NMC-" + body[:p] + dgt + body[p + 1:] + chk)      # every single-digit error caught
    for p in range(9):
        if body[p] != body[p + 1] and {body[p], body[p + 1]} != {"0", "9"}:
            assert not cnmc_valid("NMC-" + body[:p] + body[p + 1] + body[p] + body[p + 2:] + chk)       # adjacent swaps caught (except 09/90)
print("CNMC check digit: single-digit errors and adjacent swaps detected;", new_cnmc(1234567))

# ---- 5. 40-char short descriptions ----
for t in ["VALVE GATE 4IN CL150 A216 WCB FLGD RF", "PIPE SMLS 6IN SCH40 A106 GR.B", "FLANGE WN 4IN CL150 RF A105",
          "BOLT HEX M16X80 GR8.8 ZN", "MOTOR AC SQ 100KW 1500RPM 4P", "GASKET SPIRAL WND 4IN CL150 SS316/GRAF"]:
    s = short_desc(E(t)); assert s and len(s) <= 40; print(f"  {len(s):2d} chars  {s}")

# ---- 6. constrained clustering: A~B and B~C are individually fine, but A vs C conflict ----
recs = [E("VALVE GATE 4IN CL150 WCB FLANGED RF API 600"), E("VALVE GATE 4IN CL150 WCB FLANGED RF"), E("VALVE GATE 4IN CL150 WCB FLANGED RF API 6D")]
conflict = lambda i, j: decide(recs[i], recs[j])["verdict"] == "NOT_EQUIVALENT"
edges = [(0, 1, 0.9), (1, 2, 0.8)]
assert all(decide(recs[i], recs[j])["verdict"] == "EQUIVALENT" for i, j, _ in edges) and conflict(0, 2)
print("clusters:", constrained_clusters(3, edges, conflict), "(never all three together)")
assert constrained_clusters(3, edges, conflict) != [[0, 1, 2]]
# ---- 7. signature features: cited decisions, baselines, look-alike guard, ask-don't-guess, rule-impact preview ----
import copy
r = V(*EQV[0]); rows = {e["attr"]: e for e in r["evidence"]}
assert rows["size_dn"]["note_a"] == "4 IN = DN100" and rows["size_dn"]["note_b"] == "100 NB = DN100"
assert rows["body_material"]["note_b"] == "WCB -> A216-WCB" and rows["body_material"]["note_a"] is None
assert all(e["rule"].startswith("VALVE.") and e["rule_text"] for e in r["evidence"])          # every row cites a rule
print("evidence card: conversions and rule citations present")

fp1 = sum(baseline_b1(a, b, 0.85) for a, b in NOT); tp1 = sum(baseline_b1(a, b, 0.85) for a, b in EQV)
fp2 = sum(baseline_b2(a, b, 0.55) for a, b in NOT); tp2 = sum(baseline_b2(a, b, 0.55) for a, b in EQV)
assert (fp1, tp1, fp2, tp2) == (6, 2, 0, 2)
print(f"12 hand-built pairs: B1 text-only (0.85) -> {fp1} false merges, {tp1}/6 equivalents found | "
      f"B2 text+numbers (0.55) -> {fp2} false merges, {tp2}/6 found | SpecID -> 0 false merges, 6/6 found (its rules were written with these pairs in view)")

cls = [lookalike_class(text_sim(a, b), V(a, b)["verdict"]) for a, b in NOT + EQV]
assert cls.count("LOOKALIKE_VETOED") == 6 and cls.count("HIDDEN_TWIN") == 2
print("look-alike guard: 6 look-alikes vetoed, 2 hidden twins")

A = E("VALVE GATE 4IN CL150 WCB FLANGED"); B = E("VALVE GATE 4IN CL150 WCB FLANGED RF")
assert decide(A, B)["verdict"] == "INSUFFICIENT_DATA"
A2 = supply_attribute(A, "end_connection", "FLANGED-RF", "datasheet D-123")
r2 = decide(A2, B); assert r2["verdict"] == "EQUIVALENT"
assert [e["note_a"] for e in r2["evidence"] if e["attr"] == "end_connection"] == ["supplied by user: datasheet D-123"]
assert decide(supply_attribute(A, "end_connection", "FLANGED-FF", "x"), B)["verdict"] == "NOT_EQUIVALENT"   # a supplied value can still conflict
print("ask-don't-guess: supplying the missing face turns INSUFFICIENT_DATA into EQUIVALENT, with provenance")

pairs = [(E("VALVE GATE 4IN CL150 WCB FLANGED RF API 600"), E("VALVE GATE 4IN CL150 WCB FLANGED RF")),
         (E("PIPE 6IN SCH40 A106B"), E("PIPE SMLS 6IN SCH40 A106 GRB")), (E("BOLT HEX M16X80 8.8"), E("BOLT HEX M16X80 8.8 ZN"))]
draft = copy.deepcopy(TEMPLATES); draft["VALVE"]["core"].append("design_standard"); draft["VALVE"]["ext"].remove("design_standard")
ch = impact_preview(pairs, draft)
assert len(ch) == 1 and (ch[0]["old"], ch[0]["new"]) == ("EQUIVALENT", "INSUFFICIENT_DATA")
assert decide(*pairs[0], templates=TEMPLATES)["verdict"] == decide(*pairs[0])["verdict"]
print("rulebook impact preview: promoting design_standard to core changes 1 of 3 stored pairs")

# ---- 8. air-gap proof: the egress guard blocks and counts outbound attempts, allows loopback and the database host ----
import socket, threading
g = EgressGuard(allowed={"db"}); g.install()
try:
    for target in (lambda: socket.create_connection(("203.0.113.1", 80), timeout=1),      # TEST-NET-3: never routable
                   lambda: socket.getaddrinfo("example.com", 80)):
        try: target(); raise AssertionError("egress was not blocked")
        except PermissionError: pass
    assert g.blocked == 2
    srv = socket.socket(); srv.bind(("127.0.0.1", 0)); srv.listen(1)
    threading.Thread(target=lambda: srv.accept()[0].close(), daemon=True).start()
    socket.create_connection(("127.0.0.1", srv.getsockname()[1]), timeout=1).close()      # loopback is allowed
    socket.getaddrinfo("localhost", 80)
    assert g.blocked == 2
finally:
    g.uninstall()
print("egress guard: 2 outbound attempts blocked and counted, loopback allowed")

print("ALL TESTS PASS")
```

**Output of the run used while writing this PRD** (a spec self-check, not an evaluation):

```text
golden pairs: 12/12 pass
extra cases: 13 pass
route/flag/identical checks pass
property test: hard negatives never EQUIVALENT (1500 generated pairs, smoke test only)
CNMC check digit: single-digit errors and adjacent swaps detected; NMC-00012345674
  35 chars  VLV GATE 4IN CL150 A216-WCB FLGD RF
  26 chars  PIPE SMLS 6IN SCH40 A106-B
  24 chars  FLG WN 4IN CL150 RF A105
  22 chars  BOLT HEX M16X80 8.8 ZN
  21 chars  MOTOR AC IND 100KW 4P
  32 chars  GASKET SPW 4IN CL150 SS316 GRAPH
clusters: [[0, 1], [2]] (never all three together)
evidence card: conversions and rule citations present
12 hand-built pairs: B1 text-only (0.85) -> 6 false merges, 2/6 equivalents found | B2 text+numbers (0.55) -> 0 false merges, 2/6 found | SpecID -> 0 false merges, 6/6 found (its rules were written with these pairs in view)
look-alike guard: 6 look-alikes vetoed, 2 hidden twins
ask-don't-guess: supplying the missing face turns INSUFFICIENT_DATA into EQUIVALENT, with provenance
rulebook impact preview: promoting design_standard to core changes 1 of 3 stored pairs
egress guard: 2 outbound attempts blocked and counted, loopback allowed
ALL TESTS PASS
```

## Appendix E: PostgreSQL schema

**Moved.** The authoritative DDL is **doc 05 Backend Schema, Appendix A (schema v0.6)**: 26 tables, executed on PostgreSQL 16 with constraint, trigger and row-level-security tests. Keeping one copy prevents the PRD and the schema document from drifting apart. Changes since the v0.4 schema are listed in doc 05, section 1.1.

## Appendix F: Traceability

| Goal / criterion | Requirements | Tests / evidence |
|---|---|---|
| G1 end-to-end flow | FR-101–103, 201, 301, 401–402, 501–507, 601–609, 701–702, 801–803, 901–903, 1001–1003 | Integration test; demo path (section 15) |
| G2 visible decision policy | FR-601–606, 609, 802 | Golden tests; T-P1, T-P3; Appendix D |
| G3 honest evaluation | FR-1101–1104, 106 | Determinism test; formula tests; SC-4, SC-8 |
| G4 offline demo | FR-1303; NFR-05, NFR-06 | Offline test; checklist 13.4 |
| G5 real-data readiness | FR-102, 103, 203, 401, 403 | Mapping test with an unseen CSV layout |
| G6 slide material | Sections 11, 15 | Screenshots of S6, S9, S11 |
| SC-2 golden tests | FR-404, 13.2 | ≥ 60 pairs; every template covered |
| SC-3 properties | FR-602, 611, 701; NFR-04 | T-P1–T-P6, T-C |
| SC-5 search latency | FR-1001; NFR-01b | Load script |
| G7 / SC-9 Look-alike Guard (SF-1) | FR-1401–1403 | T-S2; S13; demo scene 0:30 |
| G8 PS compliance | FR-107, FR-205, FR-402, FR-405, FR-503, FR-612, FR-905, FR-907, FR-1005, FR-1201, FR-1203 | Compliance matrix 1.12; demo scenes 0:00 and 2:45 |
| SC-10 baseline scoreboard (SF-2) | FR-1411–1413; NFR-13 | T-S1; S11; demo scene 3:40 |
| SC-12 cited decisions (SF-4) | FR-609, FR-1431–1432 | T-S6; S6; demo scene 1:15 |
| Honesty (SF-5) | FR-1103, FR-1441–1443; NFR-12, NFR-14 | Export test; S11 |
| SC-11 air-gap proof (SF-7) | FR-1461–1463; NFR-05 | T-S5; checklist 13.4; demo scene 4:25 |
| SF-3 ask-don't-guess (P1) | FR-1421–1423 | T-S3; demo scene 2:15 |
| SF-6 rulebook impact preview (**P0**) | FR-403–404, FR-1451–1452 | T-S4, T-S8; S10; demo scene 2:45 |
| SF-11 multi-CPSE consent (P0) | FR-1501–1504 | T-S7; S18; demo scene 1:50 |
| SF-12 change notices (P1) | FR-1511–1513 | API tests; S19 |
| SF-8 / SF-9 / SF-10 (P1) | FR-1471; FR-1481–1482; FR-1491 | API tests; S14; S8; S15 |

## Appendix G: Claims register (what we may say, and the evidence for each)

| Claim (wording to use) | Evidence we can show | Evidence level | Do **not** say |
|---|---|---|---|
| "Text similarity alone cannot separate look-alikes from equivalents." | Look-alike Guard on the seeded run; 12 hand-built pairs [M]; published corner-case results [L, S13] | L1 / L2 | "Text matching is useless" |
| "SpecID vetoes look-alikes and explains why." | S13 plus evidence cards with rule IDs; golden and property tests | L2 | "Zero errors" (say *k* of *n* with the bound) |
| "When data is missing SpecID says so and asks." | `INSUFFICIENT_DATA` cases; ask-don't-guess scene (P1); unseen-category probe E-5 | L2 | "It handles any description" |
| "Every decision cites a rule and shows its conversions." | Evidence rows (FR-1431); T-S6 | L2 | "Fully explainable AI" |
| "False merges: *k* of *n* hard negatives (95% upper bound …) on synthetic data." | Safety headline; seed, config and commit in the export | L2, **synthetic** | Any figure presented as real-world accuracy |
| "On the same data, two simple baselines do X and SpecID does Y." | Baseline scoreboard (FR-1411–1413) | L2, synthetic | "Beats other tools" or "beats state of the art" |
| "No CPSE data leaves the machine." | Internal Compose network; egress counter 0; Wi-Fi-off demo; T-S5 | Demonstrated, single process plus network setup | "Impossible to leak" |
| "Every CPSE whose codes join a national code consents; a rule change shows its effect before activation; false merges are k of n with a bound." | SF-11, SF-6, SF-5 on screen; T-S7, T-S8 | Demonstrated (L2) | "Only we do this" — say "not found in the 41 public SIH26099 repos we inspected on 3 Oct 2026" |
| "Vetoes, baselines, offline mode and audit chains are built carefully." | SF-1, SF-2, SF-4, SF-7 | L2 | "Unique" — these are parity features |
| "Expected range from published studies on related tasks." | Dossier B9 anchors [L] | L0 | "Our results" |

*End of file.*

