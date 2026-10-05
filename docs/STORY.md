# SpecID: the story

*How one valve explains the whole product. Plain words, no jargon. Names, companies and numbers in this story are made up for illustration; the real app shows numbers from its own runs.*

---

## Chapter 1 · A broken pump on a Monday

It is Monday morning at **CPSE-B**, a big government refinery. A pump has failed, and the maintenance team needs one part to fix it: a **4-inch gate valve, pressure class 150, cast steel, flanged**.

The store says: *"We have none."* So the buyer raises a purchase order: **₹23,100 each, 6 weeks delivery**. The pump waits.

Forty kilometres away, **CPSE-A**, another government company, has **55 of exactly that valve** sitting idle in its store. It bought them last year for **₹18,400 each**.

Nobody at CPSE-B could know. Not because people were careless, but because the two companies **describe the same valve differently**:

| Company | Its code | How its computer describes the valve |
|---|---|---|
| CPSE-A | 10004521 | `GATE VLV 4" CL150 WCB FLGD RF` |
| CPSE-B | MAT-77812 | `Valve, Gate, 100 NB, 150#, Cast Steel A216 WCB, Flanged RF` |
| CPSE-C | V/GT/0093 | `GATE VALVE DN100 CLASS 150 WCB RAISED FACE` |

Three codes, three descriptions, **one valve**. Multiply this by lakhs of items and dozens of CPSEs, and you get the problem the government wants solved: duplicate codes, dirty data, no shared buying, extra stock everywhere.

The government's goal has a name: **"One Nation – One Material Code."**

---

## Chapter 2 · Why this is harder than it looks

"Just compare the text," someone says. Two reasons it fails:

**1. The same thing is written in many ways.**
`4"`, `4 IN`, `100 NB` and `DN100` are all the same size. `150#`, `CL150` and `CLASS 150` are the same pressure rating. `FLGD` means flanged. A computer comparing letters sees different words.

**2. Different things can be written almost the same way.** This is the dangerous part.

```
GATE VLV 4" CL150 WCB FLGD RF
GATE VLV 4" CL300 WCB FLGD RF
```

These look 95% the same. But the second valve is built for **double the pressure**. If a system merges them under one code, one day someone fits a CL150 valve where a CL300 is needed, in a refinery. That valve can burst.

So the system must be **clever enough** to see that the three different texts in Chapter 1 are one valve, and **careful enough** to never merge the two look-alikes above.

That is what **SpecID** does.

---

## Chapter 3 · Meera uploads her list

**Meera** is the material data steward at CPSE-A. She logs into SpecID and uploads her company's item list, exported from SAP as an Excel file.

SpecID recognises the SAP column names on its own (`MATNR` = code, `MAKTX` = description, `MEINS` = unit), so Meera doesn't have to map anything.

A **quality report** appears at once: how many items, how many have no maker, how many have odd units, how many look like internal duplicates. CPSE-A gets a **health score**. CPSE-B and CPSE-C upload theirs too.

---

## Chapter 4 · SpecID reads every description

Now Meera clicks **Run**. SpecID reads every description and turns it into a clean **spec card**, its "Material DNA":

```
GATE VLV 4" CL150 WCB FLGD RF
        ↓
Type: GATE · Size: DN100 · Class: 150 · Body: A216-WCB · Ends: FLANGED, raised face
```

It reads in **four layers**, cheapest first:
1. **Rules** know the standards: `4"` = `DN100`, `150#` = `CL150`, `WCB` = `A216-WCB`.
2. **A spell-checker for engineering words** fixes typos: `LFANGE` → `FLANGE`, `CLSAS` → `CLASS`.
3. **An AI classifier** works out what an item is even when the word is missing (`25NB 300# WCB BW` is a valve).
4. **A small AI model running on the CPSE's own computer** (no internet) reads whatever is still unclear.

Here is the safety catch: **every value the AI reads must point to the exact words it came from**. SpecID checks that those words really are in the description, and that its own rules read them the same way. If not, the AI's answer is thrown away. On screen, AI-read values carry an **AI-VERIFIED** badge, and the source words are highlighted.

*AI reads. Rules check. Nothing is taken on trust.*

---

## Chapter 5 · Finding the pairs and deciding

With thousands of records, comparing every one with every other would take forever. So SpecID first finds **likely pairs**: same kind of item and same size, similar words, or similar meaning (a small AI search model helps here).

Then, for each pair, it compares the spec cards **attribute by attribute** and gives one of four answers:

| Answer | Meaning | Example |
|---|---|---|
| **IDENTICAL** | Same spec, same maker, same part number | Two records of the same maker's part number |
| **EQUIVALENT** | Same spec, any maker: interchangeable | The three valves from Chapter 1 |
| **NOT EQUIVALENT** | A key attribute differs. **Blocked, nothing can override it** | CL150 vs CL300 |
| **CAN'T TELL** | A key attribute is unknown | One record doesn't say the flange face |

Every answer comes with an **evidence card**: each attribute, both values, the rule used, and any conversion (`4 IN = DN100`). Anyone can see *why*.

And a special screen, the **Look-alike Guard**, lists all the pairs that *look* the same but were blocked, with the one attribute that differs highlighted in red. It shows a judge, or a CPSE engineer, exactly what a plain text-matcher would have got dangerously wrong.

---

## Chapter 6 · "Can't tell? Then ask."

Some pairs end as **CAN'T TELL**. For example, CPSE-B's valve doesn't say whether its flange face is raised or flat, and those two are not interchangeable.

Most systems would guess. **SpecID never guesses.** It writes a question:

> *"Flange face of record MAT-77812 is missing. Please confirm."*

The question goes to **CPSE-B's inbox**, because only CPSE-B knows its own item. Their steward checks the datasheet, answers "Raised face (datasheet DS-114, page 2)", and SpecID **re-decides the pair at once**: now it's EQUIVALENT.

---

## Chapter 7 · People approve, and every CPSE agrees

SpecID has now grouped the three valves into a **cluster**: one real item, three records. But SpecID doesn't issue a national code by itself. **People do.**

1. **Meera** (CPSE-A, the *maker*) opens the cluster, checks the spec cards and evidence, and clicks **Propose national code**.
2. **Arjun** (CPSE-B, the *checker*) reviews and confirms. Meera can't confirm her own proposal; the system blocks it.
3. The cluster includes CPSE-C's record, and a national code will change CPSE-C's data too. So the card says: **"Waiting for CPSE-C consent."**
4. **Kavya**, CPSE-C's steward, sees it in her inbox, checks, and clicks **Consent**. (If she declined, CPSE-C's record would stay out, with her reason recorded.)

Nobody overwrites another company's master data without its agreement. **That is what makes this a national registry and not one team's tool.**

---

## Chapter 8 · A national code is born

The moment the last consent arrives, SpecID issues the code:

```
NMC-00000012345
GATE VALVE DN100 CL150 A216-WCB FLG RF          (40-character SAP text)
Gate valve, DN100 (4 IN), Class 150, body ASTM A216 WCB, flanged ends, raised face
Class: Valves › Gate valves · UNSPSC … · HSN …
```

And a **crosswalk**, the link from every old code to the new one:

| CPSE | Old code | → National code | What to do with the old code |
|---|---|---|---|
| CPSE-A | 10004521 | NMC-00000012345 | keep for now |
| CPSE-B | MAT-77812 | NMC-00000012345 | block for new buying |
| CPSE-C | V/GT/0093 | NMC-00000012345 | phase out when stock reaches zero |

Each CPSE gets a **change notice** in its inbox and downloads its **migration pack**, a file its SAP team can load. Every step, from upload to issue, is written into a **tamper-proof audit log**; if anyone edits a past record, the log shows exactly where.

---

## Chapter 9 · The next duplicate never gets created

A month later, a new employee at CPSE-B goes to create a material in SAP and types:

`GATE VLV 4IN 150# WCB FLANGED`

Before they can save, a warning pops up:

> **This item already exists: NMC-00000012345, used by 3 CPSEs. Use the existing code.**

SAP asked SpecID first, through its API. Cleaning old duplicates is half the job. **Stopping new ones is the other half.**

---

## Chapter 10 · The money appears

Now that the three records are one code, the **dashboard** can finally add them up:

- **Price check:** CPSE-A pays ₹18,400, CPSE-C ₹21,000, CPSE-B ₹23,100 for the same valve.
- **Combined demand:** 312 valves a year across the three. Buying together could close the price gap.
- **Stock sharing:** CPSE-A holds 55 idle; CPSE-B is about to buy 20. **Transfer before buying.**

Back to Monday: CPSE-B's pump gets its valve from CPSE-A **the same week**, instead of waiting 6 weeks and paying more.

Leadership also sees each CPSE's **health score** improve as duplicates are cleaned.

---

## Chapter 11 · Why anyone should trust it

- **Offline:** everything, including the AI, runs on the CPSE's own machines. Turn off the Wi-Fi in the demo and it still works; a counter shows **0** attempts to reach the internet.
- **Honest numbers:** an evaluation page shows how SpecID performs on test data: correct matches, wrong merges (with a safety bound), and how often it says "can't tell". It shows simple text-matching tools on the same test for comparison, plus a test on real public descriptions. Every number says what it is (synthetic or real text) and what it does **not** prove.
- **Rules anyone can read:** the rules live in plain files that CPSE engineers can review. When the national rulebook changes, the admin first sees a **preview**: *"this change would affect 40 past decisions and 3 national codes in 2 CPSEs"*. Only then can it go live.

---

## The ending: what changed

| Before | After |
|---|---|
| 3 codes for one valve | 1 national code, linked to all 3 old codes |
| Nobody knew CPSE-A had idle stock | The dashboard says: transfer before buying |
| Three different prices, unseen | The price gap is visible; buying together is possible |
| New duplicates created every week | Warned at the moment of creation |
| "Is the AI right?" | Every value shows its source; risky merges are blocked; people approve; every CPSE consents |

**One Nation – One Material Code, without one wrong merge.**

---

## In one breath (for the stage)

> "SpecID reads every CPSE's material list with AI, checks every AI reading against engineering rules, never merges two items whose key specs differ, asks the owning CPSE when something is missing, and issues one national code only after people approve and every CPSE involved agrees. Then it stops new duplicates inside SAP, and shows the money: the price gaps, the combined demand, and the idle stock that can be shared. All offline, on the CPSEs' own machines."
