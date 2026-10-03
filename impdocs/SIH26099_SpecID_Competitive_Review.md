# Competitive Review and Readiness Audit: SpecID
## PS SIH26099 · measured comparison with public SIH26099 repositories and existing solutions

| Field | Value |
|---|---|
| Document | Companion review to the six project documents (PRD v0.5, TRD v1.1, 03 App Flow v1.1, 04 UI/UX Design Brief v1.1, 05 Backend Schema v0.6, 06 Implementation Plan v1.1) and the research/PPT dossier v0.5 |
| Date of scan | 3 Oct 2026 (IST) |
| Scope | 45 public SIH26099 GitHub repositories found; **41 cloned and inspected**; commercial and standards solutions summarised from the dossier |
| Bottom line | SpecID's matching-safety features are **parity**, not unique: strong public prototypes already have them. SpecID's real differentiation is **governance of a national registry across CPSEs** — multi-CPSE consent, rulebook impact preview, bounded false-merge reporting, per-CPSE change notices — none of which was found in the 41 repositories. All six documents were updated to say this |

---

## 1. Method

1. **Discovery.** The 36 repositories in dossier Appendix E, plus web searches for "SIH26099", "26099 material code", "CNMC", "One Nation One Material Code" and "unified material master CPSE". 9 new repositories were found (45 in total). GitHub's search API was not available from the analysis environment, so the list may still be incomplete.
2. **Collection.** Every repository was shallow-cloned; 4 could not be cloned (private, renamed or deleted) and 1 was empty.
3. **Automated scan.** All code files (Python, TypeScript/JavaScript, SQL, YAML, notebooks, …) and documents (Markdown, text) were searched with case-insensitive patterns per capability, separating **matches in code** from **matches only in documents**. Lock files, `node_modules`, build output and virtual environments were skipped.
4. **Manual verification.** For the strongest repositories and for every capability that SpecID claims as a differentiator, matching lines were read in context (README claims, source files, tests).
5. **Limits.** A keyword hit is an *upper bound* (a mention, a comment, a CSS class may match); "not found" means not found by these patterns plus manual reading, **not proof of absence**. Repositories change daily: **re-run the scan before any later round** (section 10).

---

## 2. Inventory of the 41 inspected repositories

"✔" = the capability's keywords appear in **code** (not only in docs). Sorted by code size.

| # | Repository | Code lines | Test files | Veto | Unknown verdict | Baselines | Offline / air-gap | Hash audit | Crosswalk | SAP | Embeddings | Hosted LLM API | Last commit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | [Prashant-thakur77/SAMAN](https://github.com/Prashant-thakur77/SAMAN) | 67,497 | 80 | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | 2026-09-29 |
| 2 | [materialiq03-byte/MaretialIQ](https://github.com/materialiq03-byte/MaretialIQ) | 55,125 | 39 | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | · | ✔ | · | 2026-09-27 |
| 3 | [Procoder1234556/national-unified-material-master](https://github.com/Procoder1234556/national-unified-material-master) | 48,659 | 10 | ✔ | · | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | 2026-09-27 |
| 4 | [tapomay2006-boop/MATRIQ_26](https://github.com/tapomay2006-boop/MATRIQ_26) | 46,886 | 26 | ✔ | ✔ | ✔ | ✔ | · | ✔ | ✔ | ✔ | · | 2026-09-24 |
| 5 | [sanjaygoud05/NMC-AI](https://github.com/sanjaygoud05/NMC-AI) | 41,735 | 27 | ✔ | ✔ | ✔ | ✔ | · | ✔ | ✔ | ✔ | ✔ | 2026-09-29 |
| 6 | [rohinish-singh/OneMate](https://github.com/rohinish-singh/OneMate) | 23,349 | 31 | ✔ | ✔ | ✔ | ✔ | · | · | · | ✔ | · | 2026-09-04 |
| 7 | [AnanthuNarashimman/SamePart](https://github.com/AnanthuNarashimman/SamePart) | 22,771 | 11 | ✔ | ✔ | ✔ | ✔ | ✔ | · | ✔ | ✔ | ✔ | 2026-09-30 |
| 8 | [Narayana-1723/26099_SIH](https://github.com/Narayana-1723/26099_SIH) | 22,658 | 16 | ✔ | · | ✔ | ✔ | ✔ | · | ✔ | ✔ | · | 2026-09-30 |
| 9 | [aditya-dixitt/Tulya](https://github.com/aditya-dixitt/Tulya) | 17,695 | 20 | ✔ | · | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | · | 2026-10-02 |
| 10 | [kishore-390/Material-Code](https://github.com/kishore-390/Material-Code) | 17,341 | 18 | ✔ | · | · | ✔ | · | ✔ | ✔ | ✔ | · | 2026-09-29 |
| 11 | [Mahdiya-Tech/MatiSync](https://github.com/Mahdiya-Tech/MatiSync) | 13,882 | 3 | · | ✔ | · | · | ✔ | ✔ | ✔ | ✔ | · | 2026-09-29 |
| 12 | [mkhanamm/SIH_cpse-material-master](https://github.com/mkhanamm/SIH_cpse-material-master) | 13,606 | 13 | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | · | ✔ | · | 2026-09-21 |
| 13 | [Siripurapu-VighnaChaitanya/MaterialSync](https://github.com/Siripurapu-VighnaChaitanya/MaterialSync) | 12,656 | 5 | ✔ | ✔ | ✔ | ✔ | ✔ | · | ✔ | ✔ | · | 2026-09-29 |
| 14 | [Harshal350/SIH---26099](https://github.com/Harshal350/SIH---26099) | 10,809 | 0 | ✔ | ✔ | · | ✔ | · | · | · | ✔ | · | 2026-09-26 |
| 15 | [Rutuja-131005/MATRA-Material-Alignment-Reconciliation-Assistants](https://github.com/Rutuja-131005/MATRA-Material-Alignment-Reconciliation-Assistants) | 9,147 | 0 | ✔ | · | ✔ | ✔ | · | · | ✔ | ✔ | ✔ | 2026-09-29 |
| 16 | [Chandermani-web/SIH_26099](https://github.com/Chandermani-web/SIH_26099) | 9,122 | 0 | · | ✔ | ✔ | · | · | ✔ | ✔ | ✔ | · | 2026-09-29 |
| 17 | [scalptrader2k7/samanvay](https://github.com/scalptrader2k7/samanvay) | 8,225 | 31 | ✔ | · | · | ✔ | ✔ | ✔ | ✔ | · | · | 2026-09-30 |
| 18 | [DaggupatiChandraSekhar/cpse-national-unified-material-master](https://github.com/DaggupatiChandraSekhar/cpse-national-unified-material-master) | 7,477 | 0 | · | ✔ | ✔ | · | ✔ | · | ✔ | · | · | 2026-09-29 |
| 19 | [Chirantan112/SIH-26099](https://github.com/Chirantan112/SIH-26099) | 7,345 | 23 | ✔ | · | · | ✔ | · | ✔ | ✔ | ✔ | ✔ | 2026-09-08 |
| 20 | [muhammad-hashim-khan/material-harmonization](https://github.com/muhammad-hashim-khan/material-harmonization) | 7,146 | 0 | ✔ | ✔ | · | · | · | · | ✔ | ✔ | · | 2026-09-21 |
| 21 | [Siddharth-sde/SIH](https://github.com/Siddharth-sde/SIH) | 7,045 | 6 | ✔ | · | ✔ | ✔ | · | ✔ | ✔ | ✔ | · | 2026-09-11 |
| 22 | [shindesiddhant-415/SIH-2026-PS26099](https://github.com/shindesiddhant-415/SIH-2026-PS26099) | 6,257 | 6 | ✔ | · | · | · | · | · | · | ✔ | · | 2026-09-28 |
| 23 | [KAM185/OneCode-AI](https://github.com/KAM185/OneCode-AI) | 5,891 | 19 | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | · | 2026-09-30 |
| 24 | [Amarnath2007/EkMat-](https://github.com/Amarnath2007/EkMat-) | 5,632 | 4 | · | · | ✔ | · | · | ✔ | ✔ | ✔ | · | 2026-09-19 |
| 25 | [Janvi-kapoor/MAITRI-MDM-SIH26099](https://github.com/Janvi-kapoor/MAITRI-MDM-SIH26099) | 5,546 | 0 | ✔ | · | · | ✔ | · | · | ✔ | · | · | 2026-09-30 |
| 26 | [ashishh-pingale/ScrewIT](https://github.com/ashishh-pingale/ScrewIT) | 5,154 | 0 | ✔ | · | · | · | · | ✔ | ✔ | ✔ | · | 2026-09-10 |
| 27 | [Varunsai1930/SIH](https://github.com/Varunsai1930/SIH) | 4,235 | 0 | ✔ | ✔ | ✔ | ✔ | · | ✔ | ✔ | ✔ | · | 2026-09-28 |
| 28 | [SyedAsif7/sih-numm-ps26099](https://github.com/SyedAsif7/sih-numm-ps26099) | 4,213 | 0 | · | ✔ | ✔ | · | · | ✔ | ✔ | · | · | 2026-09-29 |
| 29 | [Adeptaadi/SIH_26099](https://github.com/Adeptaadi/SIH_26099) | 4,206 | 14 | ✔ | · | ✔ | · | · | · | · | ✔ | · | 2026-08-31 |
| 30 | [sih26099/frontend-2.0](https://github.com/sih26099/frontend-2.0) | 4,186 | 0 | ✔ | ✔ | · | ✔ | · | ✔ | ✔ | ✔ | · | 2026-09-22 |
| 31 | [Vishal-saravanan2507/SIH26099-material-harmonization](https://github.com/Vishal-saravanan2507/SIH26099-material-harmonization) | 3,566 | 6 | ✔ | · | · | ✔ | · | · | · | ✔ | · | 2026-09-15 |
| 32 | [sih26099/frontend](https://github.com/sih26099/frontend) | 3,447 | 0 | ✔ | ✔ | · | ✔ | · | ✔ | · | ✔ | · | 2026-09-15 |
| 33 | [Ankus0001h/Unimaster](https://github.com/Ankus0001h/Unimaster) | 2,774 | 0 | · | · | · | · | · | ✔ | · | ✔ | · | 2026-10-03 |
| 34 | [sih26099/backend](https://github.com/sih26099/backend) | 2,591 | 2 | ✔ | ✔ | · | ✔ | · | ✔ | ✔ | ✔ | · | 2026-09-20 |
| 35 | [nihal-kumar01/SIH26099-material-code-engine](https://github.com/nihal-kumar01/SIH26099-material-code-engine) | 2,283 | 0 | ✔ | ✔ | · | · | · | · | · | ✔ | · | 2026-09-27 |
| 36 | [Solanki-Jatin/SIH26099-material-code-engine](https://github.com/Solanki-Jatin/SIH26099-material-code-engine) | 1,996 | 0 | ✔ | ✔ | · | · | · | · | · | ✔ | · | 2026-09-28 |
| 37 | [sarveshmuthuvel/SIH26099](https://github.com/sarveshmuthuvel/SIH26099) | 1,904 | 0 | · | · | · | · | · | · | · | · | · | 2026-08-24 |
| 38 | [srushtiks12/material-code-hormaonization](https://github.com/srushtiks12/material-code-hormaonization) | 784 | 0 | · | · | · | · | · | ✔ | · | ✔ | · | 2026-09-13 |
| 39 | [amrit978/Prototype](https://github.com/amrit978/Prototype) | 375 | 0 | · | · | · | · | · | · | · | · | · | 2026-09-06 |
| 40 | [kAarjav/SIH-26100](https://github.com/kAarjav/SIH-26100) | 201 | 0 | · | · | · | · | · | · | · | · | · | 2026-09-27 |
| 41 | [om-bhope11/Matiq-Ai-Harmonization-](https://github.com/om-bhope11/Matiq-Ai-Harmonization-) | 0 | 0 | · | · | · | · | · | · | · | · | · | 2026-09-28 |

Total inspected: 41 repositories, about 535,000 lines of code and configuration.

### 2.1 Aggregate picture

| Capability (keywords in code) | Repos of 41 | Reading |
|---|---|---|
| Embeddings / vector search | 33 | table stakes |
| Attribute veto / hard constraints / safety gates | 30 | table stakes |
| SAP fields or SAP-style export | 25 | table stakes |
| Offline / on-prem / air-gap | 24 | common |
| Legacy-code crosswalk | 23 | table stakes |
| Explicit unknown / insufficient-evidence / needs-info | 21 | common |
| Baselines | 20 | common (strongest: several baselines on the same candidates) |
| Hash-chained or tamper-evident audit | 12 | common in strong repos |
| Hosted LLM APIs (OpenAI, Gemini, Groq, …) | 6 | sovereignty weakness for those teams |
| Repos with ≥ 10,000 lines | 14 | several mature builds |
| Repos with test files | 22 | about half test their code |
| README quoting precision/recall/F1/accuracy percentages | 7 | most label their data as synthetic |

---

## 3. The strongest public prototypes (verified by reading)

| Repository | What it already does (from its README and code) | What this means for SpecID |
|---|---|---|
| **Prashant-thakur77/SAMAN** (≈ 67k lines, 80 test files) | Offline, no cloud; rules-based **veto layer overrides any score**; a person decides grey-band pairs; **hash-chained ledger**; measured on a 12,000-row five-CPSE synthetic estate (pairwise P 0.997 / R 0.960, B-cubed F1 0.991, veto precision on planted traps 1.000) with a naive exact-text baseline; two-way ERP **migration with dry run and rollback**; UNSPSC/HSN; learned pairwise model; SAP integration paths; **engineer-approved substitutes**; restricted-mode **privacy-preserving record linkage** | The most complete competitor. SpecID cannot win on breadth; it must show governance SAMAN does not show |
| **aditya-dixitt/Tulya** (≈ 18k lines) | "AI proposes → engineering evidence decides → hard conflicts veto"; score `0.60·cosine + 0.25·token-set + 0.15·attribute` with **hard-key veto**; ~2,000 planted **hard negatives**; family-level splits; precision/recall vs **four baselines on the same candidates**; lists the highest-text-similarity pairs that are still vetoed; `INSUFFICIENT_EVIDENCE`; standards knowledge graph; pooling scenarios | Look-alike Guard (SF-1) and baseline scoreboard (SF-2) are **parity** |
| **AnanthuNarashimman/SamePart** (≈ 23k lines) | Conflict gates outside the model that **veto** it; **egress guard, blocked by default**; reviewer answers the system's question and the pair is **re-decided**; `insufficient_evidence` verdict; synthetic multi-CPSE generator; CI fails on benchmark regression | Air-gap proof (SF-7) and ask-don't-guess (SF-3) are **parity** |
| **Procoder1234556/national-unified-material-master (NUMM)** (≈ 49k lines) | Offline-first; ONMC minting with MESC/UNSPSC/GeM crosswalk fields; steward review; search before buy; surplus transfer; pooled demand; audit verification; air-gapped deployment option | Pooling (SF-10) and search-before-create are **parity** |
| **materialiq03-byte/MaretialIQ** (≈ 55k lines) | All data labelled synthetic with a banner; precision/recall/F1 against labelled ground truth; versioned migrations; access-restricted routes | Honest synthetic labelling is **parity**; SpecID's *bound* on false merges is not shown |
| **KAM185/OneCode-AI** (≈ 6k lines) | Migration mapping CSV with SAP-style columns; **hash-chained, signed, append-only audit**; substitution safety score; code supersession; air-gapped model setup; regression tests | Migration pack and substitutes are **parity** |
| **mkhanamm/SIH_cpse-material-master** (≈ 14k lines) | Veto in the pipeline; offline TF-IDF+SVD backend; measured average precision; explicit, honest limitations list | Honesty panel is **parity**; good model for wording |
| **tapomay2006-boop/MATRIQ_26** (≈ 47k lines) | Siamese reranker trained with hard negatives; calibrated threshold; near-miss discrimination examples; shows when rules pulled a verdict down | Stronger learned component than SpecID P0 |
| **scalptrader2k7/samanvay** | Review-first; exact / near / functional-equivalent / conflict outcomes with insufficient evidence kept reviewable; **explicitly claims no accuracy** until human labels exist | Same honesty stance as SpecID |

---

## 4. Feature-by-feature verdict for SpecID

| SpecID feature (PRD v0.5) | Found in public repos? | Evidence | Verdict |
|---|---|---|---|
| SF-1 Look-alike Guard | Yes | Tulya lists highest-similarity vetoed pairs; MATRIQ near-miss discrimination | Parity |
| SF-2 Baseline scoreboard | Yes | Tulya (four baselines, same candidates), SAMAN (naive baseline), mkhanamm (LR baseline) | Parity |
| SF-3 Ask, don't guess | Yes | SamePart: reviewer answers and the pair is re-decided | Parity |
| SF-4 Cited decisions + conversion notes | Partly | rule-based explanations common; conversion notes on evidence rows not found by search | Parity+ |
| SF-5 Safety number **with a statistical bound** | Bound: **no** | P/R tables common; no Wilson / rule-of-three / confidence bound on false merges found | **Differentiator (the bound)** |
| SF-6 Rulebook impact preview | **No** | only "rules vs model" per pair (MATRIQ); no preview of a rule change over stored decisions | **Differentiator** |
| SF-7 Air-gap proof | Yes | SamePart egress guard; SAMAN, NUMM, OneCode-AI air-gapped modes | Parity |
| SF-8 ERP create simulator / search-before-create | Yes | search-before-create/buy common | Parity |
| SF-9 Reversible merges | Yes | SAMAN rollback; OneCode-AI supersession | Parity |
| SF-10 Pooling view | Yes | NUMM pooled demand; Tulya pooling scenarios | Parity |
| FR-612 One-way substitutes | Yes | SAMAN engineer-approved substitutes; OneCode-AI substitution safety score | Parity |
| FR-907 Migration pack | Yes | SAMAN (with rollback), OneCode-AI (SAP-style CSV) | Parity |
| **SF-11 Multi-CPSE consent** | **No** | 0 repos; approval is by the reviewing team only | **Differentiator (new in v0.5)** |
| **SF-12 Per-CPSE change notices** | **No** (docs only in a few) | mentions of "propagation" in docs, no implementation found | **Differentiator (new in v0.5, P1)** |

**Honest conclusion.** Before this scan, the dossier and PRD said the signature features were "not seen" in public prototypes. That was based on READMEs and is **no longer accurate**. The documents now present them as parity and lead with the governance differentiators.

---

## 5. Existing commercial and standards solutions (summary)

From dossier A2.1–A2.2 and B12 (public documentation only, not product tests):

| Solution | Strength | Gap for this PS |
|---|---|---|
| SAP MDG duplicate check | in-ERP, mature, configurable thresholds | single SAP landscape; score on descriptions; no neutral cross-CPSE registry |
| Verdantis, Sievo, SPARETECH, Verusen/Automa, Palantir AIP | mature cleansing, harmonisation, classification, enterprise integration | enterprise-scoped, vendor-hosted, commercial; no documented multi-organisation consent or rule-change preview |
| UNSPSC, eCl@ss, Shell MESC, CFIHOS | classification and property libraries | classify, do not identify; MESC licensed |

**Where SpecID sits:** commercial tools win on breadth and maturity; public SIH prototypes match SpecID on matching safety; SpecID's case is a **neutral registry run by many CPSEs**, which needs consent, previewed rule changes and change notices.

---

## 6. Changes made in this round (all documents)

| Document | Version | Main changes |
|---|---|---|
| PRD | v0.4 → **v0.5** | Re-positioning (1.7, 1.8, 1.10, 15.4, Appendix G); **SF-11 multi-CPSE consent (P0, FR-1501–1504)**, **SF-6 impact preview promoted to P0**, **SF-12 change notices (P1, FR-1511–1513)**; US-31, US-32; SC-13, SC-14; screens S16–S19; API-37, API-38; tests T-S7, T-S8; demo script rewritten; R-20, D-12, D-13. **Outdated items fixed:** blocking key (FR-501), auth library (6.3), run statuses (FR-507), schema moved to doc 05 (Appendix E now a pointer), screens list (11.1) |
| TRD | v1.0 → **v1.1** | Consent sequence (2.3 b2) and algorithm (TR-ALG-11), consent and notice services (TR-MOD-32, 33), impact preview P0 with affected CNMCs/CPSEs (TR-ALG-10), routes delegated to App Flow, tests TR-TST-15/16, TD-10, **section 19 production path**; TD-03/TD-04 marked applied |
| 03 App Flow | v1.0 → **v1.1** | S18 consent queue, S19 notices, consent strip and redirects, S10 impact preview P0, journeys J11/J12, four-profile demo path, demo times synced with PRD 15.1 |
| 04 UI/UX Brief | v1.0 → **v1.1** | ConsentStrip and ImpactPreviewTable components, S18 and S10 layouts, screenshot guidance for the differentiators |
| 05 Backend Schema | schema v0.5 → **v0.6** | `review_consent`, `change_notice`, `AWAITING_CONSENT`; **re-executed on PostgreSQL 16 (58 statements, 26 tables)**; consent, notice, audit, crosswalk, maker ≠ checker, RLS and dashboard-SQL tests re-run; data dictionary regenerated from the live database |
| 06 Implementation Plan | v1.0 → **v1.1** | Consent in Phase 6 / G3, impact preview in Phase 7 / G4, P1 order updated, four browser profiles, re-scan task, upstream-update table marked applied |
| Research / PPT dossier | v0.4 → **v0.5** | **Slide 2 uniqueness table rewritten** around governance with a comparison footnote; flowchart shows consent and rule preview; Slide 5 control bullet; A2.5 replaced with measured counts; A3 and B2.1 notes; judge Q11 rewritten, Q17 added; Appendix E now 45 repos |

---

## 7. Cross-document consistency audit

Automated checks run over all seven files after the edits:

| Check | Result |
|---|---|
| Every `FR-` referenced in any document is defined in the PRD (109 FRs) | pass |
| Every `API-` referenced exists (API-01–38) | pass (the only hit, "API 600", is a valve standard) |
| Screen IDs ≤ S19 everywhere | pass |
| No stale counts ("29 statements", "54 statements", "24 tables", "API-01 … API-36", "S0–S15") outside change-log history | pass |
| No document except change logs refers to PRD v0.4 | pass |
| Every database table named in TRD, App Flow and Plan exists in the schema DDL | pass |
| PRD user stories US-01–32, success criteria SC-1–14 contiguous | pass |
| Schema DDL executes on PostgreSQL 16; TRD dashboard SQL runs on it | pass |
| TRD YAML / Python blocks parse | pass |
| Demo timings in PRD 15.1 and App Flow traceability agree | pass |

Manual review points (judgement, not automated): terminology (verdict names, CNMC, consent) is used the same way in all documents; P0/P1 tiers of SF-6, SF-11, SF-12 agree in PRD 1.6/1.8, TRD, App Flow, Plan.

---

## 8. Readiness assessment

| Dimension | Status for the SIH finale | Status for an industry deployment | Where specified |
|---|---|---|---|
| Problem fit (PS SIH26099) | all 11 *Expected Solution* bullets mapped to P0 | — | PRD 1.12 |
| Differentiation | three governance differentiators + bounded safety number, measured against 41 repos | consent and change notices are what a multi-CPSE registry needs | PRD 1.8 |
| Specification depth | requirements, design, flows, UI, schema, plan all cross-referenced | good basis for a pilot RFP | all docs |
| Data model | executed and constraint-tested | needs partitioning and replicas at scale | doc 05, TRD 19 |
| Security | RBAC, maker ≠ checker in DB, append-only audit, air-gap, optional RLS | SSO/MFA, VAPT, secrets vault, CERT-In incident and log obligations, DPDP Act 2023 for user data | TRD 11, 19 |
| Evidence | L0 + L1 only; synthetic L2 planned | needs L3 pilot with labelled CPSE data | PRD 10, dossier |
| Build maturity | **no code yet** — competitors have tens of thousands of lines | — | Implementation Plan |
| Operations | single laptop, snapshot, backup video | HA, backup/PITR, monitoring, on-call, governance council | TRD 19 |

**Verdict.** The documents are internally consistent and specific enough for a team or an AI coding agent to build from. "Industry ready" applies to the *specification quality*, not to the product: production needs the items in TRD section 19 and real CPSE evidence.

---

## 9. Optimality review: choices kept and alternatives considered

| Choice | Kept because | Alternative seen in public repos | Recommendation |
|---|---|---|---|
| Rule-based veto decides; ML only ranks | safety: a model cannot guarantee CL150 ≠ CL300 | learned pairwise models (SAMAN), Siamese reranker (MATRIQ) | keep; add LightGBM ranker in P1 as planned |
| Blocking without pressure class | rating near-misses must reach the veto | multi-pass blocking (SAMAN: 7 passes) | keep; measure pair completeness per channel |
| One-copy DDL in doc 05 | prevents drift | — | keep |
| Consent rule `ALL_PARTICIPANTS` | strongest guarantee, small extra cost | none | keep; make `NONE` available for single-CPSE pilots |
| UNSPSC only | PS asks for classification | SAMAN also maps **HSN** (India GST) | **consider adding an optional HSN field** next to UNSPSC (P1, same verified-table rule) |
| CI golden + property tests | regression safety | SamePart fails CI on benchmark regression | **consider adding a frozen-threshold benchmark gate in CI** (cheap) |
| No datasheet / OCR enrichment, no Hindi | 36-hour scope | several repos mention them | P2 / pilot |

---

## 10. Recommendations

1. **Lead with governance on Slide 2 and in the demo** (already applied): consent, impact preview, bounded number.
2. **Do not claim** look-alike lists, baselines, egress guards, hash chains, substitutes or migration as unique (Appendix G of the PRD enforces the wording).
3. **Re-run this scan one week before any later round.** Keep the clone-and-scan script (`analyze.py` approach in section 1) in the repository under `tools/`.
4. **Build the differentiators first in their phases** (consent by G3, impact preview by G4) so they cannot be cut.
5. Consider the two cheap improvements in section 9 (HSN field, CI benchmark gate).
6. Never name other teams on slides or on stage; this review is for internal preparation.

---

## 11. Sources

- Public repositories: the 41 listed in section 2 (links in the table) and the 4 unreachable ones listed in dossier Appendix E.
- Discovery searches (3 Oct 2026) surfaced, among others: [SyedAsif7/sih-numm-ps26099](https://github.com/SyedAsif7/sih-numm-ps26099), [AnanthuNarashimman/SamePart](https://github.com/AnanthuNarashimman/SamePart), [scalptrader2k7/samanvay](https://github.com/scalptrader2k7/samanvay), [Procoder1234556/national-unified-material-master](https://github.com/Procoder1234556/national-unified-material-master), [Janvi-kapoor/MAITRI-MDM-SIH26099](https://github.com/Janvi-kapoor/MAITRI-MDM-SIH26099), [DaggupatiChandraSekhar/cpse-national-unified-material-master](https://github.com/DaggupatiChandraSekhar/cpse-national-unified-material-master), [Ankus0001h/Unimaster](https://github.com/Ankus0001h/Unimaster), [ashishh-pingale/ScrewIT](https://github.com/ashishh-pingale/ScrewIT), [om-bhope11/Matiq-Ai-Harmonization-](https://github.com/om-bhope11/Matiq-Ai-Harmonization-), [rohinish-singh/OneMate](https://github.com/rohinish-singh/onemate).
- Commercial and standards solutions: dossier Appendix D references S3–S12.

## Appendix: scan script (reproducible)

Clone the repositories into `r/<owner>_<repo>` (`git clone --depth 1`), then run this script; it writes `analysis.json` with per-repository code/document hit counts for every capability pattern.

```python
import os,re,json,subprocess
CODE={".py",".ts",".tsx",".js",".jsx",".java",".go",".sql",".kt",".rs",".cs",".rb",".php",".yml",".yaml",".toml",".ipynb"}
DOC={".md",".txt",".rst"}
SKIP={"node_modules",".git","dist","build","venv",".venv","__pycache__",".next","site-packages","vendor","coverage"}
F={
 "veto":r"\bveto|hard[_ -]?(constraint|block|gate|rule)|safety[_ -]?gate|spec[_ -]?mismatch|critical[_ -]?attribute|must[_ -]?match",
 "unknown_verdict":r"insufficient[_ -]?data|undecid|abstain|cannot[_ -]?decide|needs[_ -]?info|needs[_ -]?review",
 "baseline":r"\bbaseline",
 "false_merge":r"false[_ -]?merge|wilson|rule[_ -]?of[_ -]?three|false[_ -]?positive[_ -]?rate",
 "rule_cite":r"rule[_ -]?id\b|rule_text|rule[_ -]?citation|cited[_ -]?rule",
 "offline":r"air[_ -]?gap|offline|on[_ -]?prem",
 "egress_guard":r"egress|internal:\s*true",
 "maker_checker":r"maker[_ -]?checker|four[_ -]?eyes|dual[_ -]?approval",
 "hash_audit":r"hash[_ -]?chain|prev_hash|previous_hash|tamper",
 "audit":r"\baudit",
 "crosswalk":r"crosswalk|legacy[_ -]?code",
 "migration":r"migration[_ -]?(pack|plan|file|support)|rationali[sz]",
 "unspsc":r"unspsc|eclass|ecl@ss",
 "sap":r"\bSAP\b|MATNR|MAKTX",
 "search_before_create":r"search[_ -]?before[_ -]?create|pre[_ -]?creation|before[_ -]?creat|create[_ -]?check|prevent(ion)?[_ -]?dup",
 "embeddings":r"sentence[_-]?transformers|SentenceTransformer|faiss|pgvector|embedding",
 "hosted_llm":r"openai|gemini|groq|anthropic|generativeai|api\.openai|gpt-4|gpt-3",
 "local_llm":r"ollama|llama\.cpp|vllm|transformers\.pipeline",
 "uom":r"\buom\b|unit[_ -]?of[_ -]?measure",
 "dn_nps":r"\bnps\b|nps_to_dn|\bDN\s?\d{2,3}\b|\d+\s?NB\b",
 "synthetic":r"synthetic",
 "substitute":r"substitut|interchangeab|functional(ly)?[_ -]?equivalen",
 "near_miss":r"near[_ -]?miss|look[_ -]?alike|hard[_ -]?negative",
 "property_tests":r"\bhypothesis\b|property[_ -]?based",
 "dashboard":r"dashboard",
 "demand_agg":r"demand[_ -]?aggregat|joint[_ -]?procure|pooling|pooled",
 "ml_model":r"LogisticRegression|RandomForest|XGBoost|xgboost|LightGBM|lightgbm|sklearn",
 "calibration":r"isotonic|calibrat",
 "docker":r"^FROM\s|services:",
}
CR={k:re.compile(v,re.I|re.M) for k,v in F.items()}
claim=re.compile(r"(accuracy|precision|recall|f1)[^\n]{0,40}?\b(\d{2,3}(\.\d+)?)\s?%",re.I)
out={}
for d in sorted(os.listdir("r")):
    root="r/"+d; code=doc=0; loc=0; tests=0
    hits={k:{"code":0,"doc":0} for k in F}
    readme=""; langs={}
    for dp,dn,fn in os.walk(root):
        dn[:]=[x for x in dn if x not in SKIP]
        for f in fn:
            p=os.path.join(dp,f); ext=os.path.splitext(f)[1].lower()
            if f.lower() in ("package-lock.json","yarn.lock","pnpm-lock.yaml","poetry.lock"): continue
            try:
                if os.path.getsize(p)>2_000_000: continue
                s=open(p,encoding="utf-8",errors="ignore").read()
            except Exception: continue
            kind="code" if (ext in CODE or f in ("Dockerfile","docker-compose.yml")) else "doc" if ext in DOC else None
            if not kind: continue
            if kind=="code":
                code+=1; n=s.count("\n"); loc+=n; langs[ext]=langs.get(ext,0)+n
                if re.search(r"(^|/)(tests?|__tests__|spec)(/|$)",dp.replace(root,"")) or re.match(r"(test_.*\.py|.*_test\.py|.*\.(test|spec)\.(t|j)sx?)$",f): tests+=1
            else:
                doc+=1
            if f.lower().startswith("readme") and dp==root: readme=s
            for k,c in CR.items():
                if c.search(s): hits[k][kind]+=1
    rm=readme.lower()
    out[d]={"code_files":code,"loc":loc,"doc_files":doc,"test_files":tests,"langs":dict(sorted(langs.items(),key=lambda x:-x[1])[:3]),
            "hits":hits,"readme_len":len(readme),"readme_claims":[m.group(0)[:80] for m in claim.finditer(readme)][:5],
            "readme_synthetic":"synthetic" in rm}
json.dump(out,open("analysis.json","w"),indent=1)
print(len(out))
```

*End of Competitive Review.*
