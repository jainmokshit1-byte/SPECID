# Next steps: the plan, in simple words

Read this out top to bottom. It says what we build, in what order, what you will be able to click after each step, and how we know a step is really done. The product it builds is described in `docs/SOLUTION.md`. If a word is unfamiliar, see `docs/GET_READY.md`.

**The big idea of the plan:** build **thin, complete slices**. After each slice, something new works from start to end in the browser. After slice 2 we already have a full demo; every later slice only adds. So if time runs out, we still have a working product.

Dates are **estimates**, assuming we work on it most days. The SIH grand finale is expected in December 2026, so there is buffer.

---

## Where we start from (today, 4 Oct)

- **Working:** the matching engine (reads valves, pipes, flanges, bolts and motors; decides same / equivalent / different / can't tell; never merged a look-alike trap in testing), the database (all 26 tables), login with roles, user management, tamper-proof audit log, synthetic data generator. 512 tests pass.
- **Missing:** everything a judge clicks: upload, matching runs, review, national codes, dashboard, AI, SAP connection.
- **Main weakness:** the engine says "can't tell" for 58% of items that really are the same. About half of that is fixable by AI reading (values are in the text but missed), and half needs the "ask the owner" workflow.

---

## Step 0 · Get set (this week, 1–2 days)

| # | What | Who |
|---|---|---|
| 0.1 | Read `GET_READY.md` and do its hands-on part | you |
| 0.2 | Read `SOLUTION.md`; tell me what to change. Approving it also approves the changes listed in its section 12 | you |
| 0.3 | **Ask the SPOC:** can we bring code written before the finale? (open question Q-01) | you |
| 0.4 | Talk to your friend: are they still coding? Agree that the build follows the new slice order, so we don't edit the same files | you |
| 0.5 | Tell the PPT team which features to show (section "What to tell the PPT team" below) | you |
| 0.6 | Give Docker more memory: create `C:\Users\Asus\.wslconfig` with `[wsl2]` and `memory=10GB`, then restart Docker Desktop | you (I can write the file) |
| 0.7 | Update `CLAUDE.md`, `PROGRESS.md` and the plan so every future session follows the new order; log the changes as decisions | me |
| 0.8 | Commit the new docs | me, after your OK |

**Done when:** you can explain the project in 60 seconds, the docs are approved and committed, and Q-01 is asked.

---

## Slice 1 · Upload and match (week of 5 Oct)

**Goal:** upload three CPSE files, press one button, and see which records the system thinks are the same.

What we build:
- **Upload screen:** drop a CSV or Excel file; columns are matched automatically (also SAP names like `MATNR`, `MAKTX`); a quality report and a first health score appear.
- **Generator upgrade:** synthetic files also get procurement history (prices, quantities) and stock on hand, ready for the savings screens later.
- **Candidate search:** find likely pairs quickly (same category and size, similar words) instead of comparing everything with everything.
- **The run:** read → find pairs → decide → group, running in the background with a live progress bar.
- **Runs screen:** list of runs, a "new run" button, the live console, and a results summary (how many same, different, can't tell).
- **Typo-tolerant dictionary (first AI-ish layer, still rules):** fixes `LFANGE`, `PIEP`, `CLSAS`, `FLAT FACE`. We re-measure the "can't tell" rate before and after.

You will be able to: log in as meera → upload 3 files → see the quality report → start a run → watch it finish → see the result counts.

**Done when:** the full flow works in the browser on the 3,000-record set in under 10 minutes, the "can't tell" rate is measured again (and is lower), and still 0 look-alike traps are merged.

---

## Slice 2 · Review → national code (week of 12 Oct) · the core demo

**Goal:** turn a group of matching records into one national code, with approvals, consent and migration files.

What we build:
- **Review queue and cluster screen (the hero screen):** the records side by side, their spec fingerprints, and the evidence card (which rule, which conversion, like `4 IN = DN100`).
- **Maker → checker:** meera proposes, arjun (another CPSE) approves. The same person can't do both.
- **Consent:** the code waits until every CPSE involved agrees. kavya (CPSE-C) sees it in her inbox and consents, or declines with a reason.
- **National code issued:** CNMC number, standard 40-character SAP text and long description, class, and a crosswalk row per old code.
- **Registry screen:** all national codes, a detail page with every linked old code, and downloads: crosswalk (CSV/JSON/SAP-style) and the **migration pack** per CPSE.
- **Change notices:** each affected CPSE gets a notice listing what changed for it.
- Every step is written to the audit log.

You will be able to: run the whole story from upload to "national code issued, migration file downloaded", using 3 browser windows (maker, checker, CPSE-C steward).

**Done when:** that story works end to end twice in a row; the same user can't approve their own proposal (blocked in the screen and in the API); the audit chain verifies.

**After this slice we have a complete, honest demo of the problem statement.**

---

## Slice 3 · The visible AI (weeks of 19 and 26 Oct)

**Goal:** AI reads what the rules miss, every AI value is checked, and "can't tell" becomes a question to the right person.

What we build:
- **Local AI setup:** download a small open model and the embedding model once, store them in `models/`, then run fully offline (the Ollama container is already in the compose file).
- **Model bake-off:** try 2–3 small models on our data, measure speed and correctness on this laptop, and pick one. If the CPU is too slow, try the laptop's GPU; if that fails, the AI reader is switched off and labelled.
- **Category classifier:** guesses the category when the text has no category word (`25NB 300# WCB BW` is a valve).
- **Meaning search:** embeddings + FAISS find pairs worded completely differently.
- **AI reader with the grounding check:** the AI returns each value plus the exact words it came from; we accept it only if those words exist in the text, the value is allowed, and our rules agree. AI values get an **AI-VERIFIED** badge and highlighted source words in the evidence card.
- **Ask, don't guess:** for "can't tell" pairs, the missing value becomes a question in the owning CPSE's inbox. The answer (with a source note) re-decides the pair at once.
- **Run console split:** "rules read X%, AI read Y%, Z% need a person".

You will be able to: show a pair that was "can't tell", see the AI read the missing value with its source words highlighted, see a question go to CPSE-B and the pair flip after the answer.

**Done when:** the "can't tell" rate drops clearly on the synthetic set (measured, not promised), **0 look-alike traps are merged**, a test proves the grounding check rejects invented values, and the whole demo still works with Wi-Fi off.

---

## Slice 4 · Money and prevention (week of 2 Nov)

**Goal:** show the value in rupees, and stop new duplicates.

What we build:
- **Dashboard:** duplicates per CPSE, health score per CPSE, top clusters by spend, review backlog.
- **Savings & stock sharing:** per national code, the price each CPSE pays, combined yearly demand, the price gap, and "CPSE-A has idle stock that CPSE-B is about to buy".
- **Search-before-create:** type a description and get "already exists as NMC-…".
- **SAP "Create Material" simulator:** a mock SAP screen that warns live while you type a duplicate.
- **API keys** for the `erp` user, so a real SAP system could call the same check.
- **Look-alike Guard screen:** pairs that look alike but differ, with the one attribute that differs highlighted.
- **HSN code** next to UNSPSC on each national code (only from a verified table).

You will be able to: open the dashboard and see money; type a duplicate into the fake SAP screen and get warned; show CL150 vs CL300 blocked.

**Done when:** every dashboard panel is filled from the run (no typed-in numbers), and the SAP simulator catches a duplicate of a code issued in slice 2.

---

## Slice 5 · Proof (week of 9 Nov)

**Goal:** numbers a judge can trust.

What we build:
- **Evaluation runner + screen:** correct merges, wrong merges (k of n, with a 95% upper bound), "can't tell" rate, and two simple text baselines on the same pairs. All labelled SYNTHETIC.
- **Real-text test set:** about 200 real public material descriptions (for example from public tender documents), labelled by a teammate who did not write the rules. Results shown separately. (Decision needed: where we keep this set; see below.)
- **Honesty panel and About page:** what the numbers mean and do not mean.
- **Rulebook + impact preview:** an admin drafts a rule change and sees which past decisions and national codes it would change before activating it.
- **Golden tests to 60+**, covering every category.

**Done when:** the evaluation page shows synthetic and real-text results side by side with baselines, and the impact preview shows real changes for a sample rule draft.

---

## Slice 6 · Polish and demo-proofing (week of 16 Nov, then buffer to the finale)

What we do:
- Loading, empty and error states on every screen; works at 1366×768 (projector size).
- The 5-minute demo script (`SOLUTION.md` section 7), rehearsed with Wi-Fi off, 3 times in a row.
- A database snapshot that restores in under 2 minutes; a second laptop with the same setup; a backup video and screenshots.
- README with setup and demo users.
- Re-run the competitor scan of public SIH26099 repos and adjust any "not found elsewhere" wording.

**Done when:** anyone on the team can run the demo alone, offline, from the snapshot.

---

## How we work together (every slice)

1. **I propose a short plan** for the slice: files to create, tests to write, what you'll see. You approve or change it.
2. **I build in small steps**, each with tests, and run the full test suite after each step.
3. **You click-test** the result in the browser (I'll give you the exact clicks).
4. **I commit** with a clear message after your OK, and update `PROGRESS.md`.
5. If something in the spec is unclear or contradicts itself, I stop and ask you instead of guessing.

---

## What to tell the PPT team now

- **Headline:** "AI reads, rules verify, people approve, every CPSE consents → one national code, linked to every old code."
- **Show as different:** multi-CPSE consent; change notices; rule-change impact preview; verified AI reading (every AI value shows its source words); duplicate firewall in the SAP create screen; savings and stock sharing in rupees.
- **Show as solid (not unique):** veto on key attributes, look-alike guard, audit trail, offline mode, migration pack.
- **Never write:** first, only, best, beats. No accuracy or savings numbers as real results.
- **Screenshots:** I can give them real screenshots after slice 2 (core flow) and slice 4 (dashboard, SAP screen).

---

## Decisions I need from you

| # | Question | My suggestion |
|---|---|---|
| D1 | Approve `SOLUTION.md` (including its section 12 changes)? | yes, after your edits |
| D2 | Can I edit `impdocs/` to match, or should the new docs live only in `docs/`? | keep `impdocs/` as history; new docs in `docs/` are the source of truth; update `CLAUDE.md` to say so |
| D3 | Real-text test set: keep it outside git (local only) or in the repo? `CLAUDE.md` forbids real CPSE data in the repo | keep it local only (git-ignored), with a note of the public source of each line |
| D4 | Is your friend still coding? | if yes, split by slice so we don't collide |
| D5 | Commit and push the new docs now? | commit now; push after you've read them |
