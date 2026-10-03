# 04 · UI/UX Design Brief: SpecID Prototype
## Visual and interaction design guide · PS SIH26099

| Field | Value |
|---|---|
| Document | 04 of 6 · UI/UX Design Brief (how the app looks and feels) |
| Version | v1.2 draft · 3 Oct 2026. **v1.2: minimal and beginner-friendly** — simplicity rules (1.4), 5-item task navigation with tabs, Next-step card, compact SYNTHETIC badge, slim footer, progressive disclosure in the evidence card, simpler Home. Tokens and accessibility rules unchanged. v1.1: consent strip, impact preview |
| Source of truth above this | PRD v0.5 (sections 1.8, 11.1–11.4, NFR-09) · TRD v1.1 (TR-UI-01–10) · 03 App Flow v1.1 (routes, modals, states) |
| Applies to | Every screen S0–S19, every component, every exported image used on the slides |

**How an AI coding agent should use this file.** Use only the tokens in section 3 (no raw hex in components). Build every screen from the components in section 6. Every verdict is shown with **colour + icon + text**. If a design question is not answered here, choose the plainer option and add the answer to this file.

---

## 1. Design intent

### 1.1 Aesthetic in one line
**"An engineering control room": calm, dense, table-first, every number labelled.** It should feel like a tool a materials engineer trusts at 6 p.m. on a busy day, not a marketing dashboard.

### 1.2 Principles (in priority order)
1. **Evidence before opinion.** The attribute-by-attribute evidence card is the hero of the product. Verdicts are never shown without a way to see *why*.
2. **Honest by default.** Synthetic data, heuristic confidence and unknowns are always labelled. Nothing looks more certain than it is.
3. **Density with calm.** Many rows on screen, generous line height, few colours. Colour is reserved for meaning (verdicts, warnings).
4. **Readable on a projector.** The finale demo runs on a projector or TV, often at **1366 × 768** or 1920 × 1080 with poor contrast. Design for that first.
5. **Keyboard-friendly.** Reviewers process hundreds of clusters; every frequent action has a key.

### 1.4 Simplicity rules (v1.2, apply to every screen)

1. **One job per screen.** The title says it; one sentence under the title explains it in plain words.
2. **One primary button per screen.** Everything else is secondary, or inside a "⋯" menu.
3. **Show the next step, not everything.** Home shows a single Next-step card; lists show what needs action first.
4. **Progressive disclosure.** Show the decisive information; put the rest behind "Show details", tabs, or a drawer. Advanced options are collapsed by default.
5. **Plain words first, technical words second.** e.g. "National code (CNMC)", "Not the same item (veto)"; every technical term has a tooltip and a Help glossary entry.
6. **No unbuilt features in navigation.** Placeholders never appear in menus.
7. **At most two charts on any screen**, each with one takeaway sentence above it.
8. **Quiet chrome.** Status (synthetic, air-gap) uses small badges, not full-width bars.
9. **Generous space.** 16–24 px between groups, 40 px table rows by default; density toggle for power users.
10. **A new user can finish the main task without help:** upload → run → review → code. Test this with someone who has not seen the app (section 11).

### 1.3 Reference apps (what to borrow, not copy)

| Reference | Borrow |
|---|---|
| Linear | Sidebar density, quiet greys, crisp focus states, keyboard-first review |
| GitHub pull-request diff view | The evidence card reads like a diff: two columns, row status at the edge, the changed value highlighted |
| Stripe Dashboard | Tables with clear numeric alignment, filter chips, detail drawers |
| Grafana | Stat tiles with small labels and big numbers on the dashboard |

---

## 2. Theme and modes

| Mode | Use |
|---|---|
| **Light (default)** | Demo, projector, screenshots for slides. Higher legibility on projectors |
| Dark (optional) | Follows `prefers-color-scheme`, toggle in the user menu. Same tokens, dark values |
| **Stage mode** | Toggle in the user menu (and `?stage=1`): root font size 115%, sidebar collapsed to icons, footer enlarged, row height +4 px. Use during the demo so the back row of judges can read |

---

## 3. Design tokens

All colours were checked for WCAG 2.1 contrast while writing this brief (text ≥ 4.5:1, UI boundaries ≥ 3:1). Values are CSS custom properties consumed by Tailwind (section 9).

### 3.1 Neutral and brand

| Token | Light | Dark | Use | Contrast checked |
|---|---|---|---|---|
| `--bg` | `#F7F8FA` | `#0E1116` | page background | text on bg 16.8:1 / 15.5:1 |
| `--surface` | `#FFFFFF` | `#161A21` | cards, tables, sidebar | — |
| `--surface-2` | `#F1F3F6` | `#1E232B` | table header, hover row, code chips | — |
| `--border` | `#D9DEE5` | `#2C333D` | dividers (decorative) | — |
| `--border-strong` | `#8A94A6` | `#646E7D` | input outlines, focus-adjacent UI | 3.1:1 / 3.4:1 |
| `--text` | `#14181F` | `#E6E9EE` | primary text | 16.8:1 / 15.5:1 |
| `--text-muted` | `#4B5563` | `#A3ABB8` | labels, secondary text | 7.6:1 / 7.5:1 |
| `--primary` | `#1D4ED8` | `#7AA2F7` | primary buttons, links, focus ring | 6.7:1 on white / 6.9:1 on surface |
| `--on-primary` | `#FFFFFF` | `#0E1116` | text on primary buttons | 6.7:1 / 7.5:1 |
| `--danger` | `#B42318` | `#F87171` | destructive buttons (unmerge, cancel run) | 6.6:1 white on red |

### 3.2 Semantic colours (verdicts and states)

| Token pair (fg / bg) | Light fg / bg | Dark fg / bg | Meaning | Icon (lucide) | Text label |
|---|---|---|---|---|---|
| `--eq` | `#166534` / `#E7F6EC` | `#4ADE80` / `#0F2A1A` | EQUIVALENT / IDENTICAL / MATCH | `CheckCircle2` | "Equivalent", "Identical", "Match" |
| `--ne` | `#B42318` / `#FDECEA` | `#F87171` / `#2E1213` | NOT_EQUIVALENT / CONFLICT / veto | `XCircle` | "Not equivalent", "Conflict" |
| `--ins` | `#8A5300` / `#FFF4DB` | `#FBBF24` / `#2E2208` | INSUFFICIENT_DATA / PARTIAL / missing | `HelpCircle` | "Insufficient data", "Partial", "Missing" |
| `--flag` | `#8A5300` outline | `#FBBF24` outline | flags (unverified, unexplained token) | `AlertTriangle` | "Unverified: design_standard" |
| `--auto` | `#1D4ED8` / `#E8EFFD` | `#7AA2F7` / `#15213A` | AUTO_ELIGIBLE route | `Zap` | "Auto-eligible" |
| `--review` | `#4B5563` / `#EEF0F3` | `#A3ABB8` / `#222831` | REVIEW route, neutral tags | `UserCheck` | "Review" |
| `--ai` | `#6D28D9` / `#F1EBFD` | `#C4B5FD` / `#251C3D` | values produced by ML (category by ML, dense channel) | `Bot` | "ML" |
| `--user` | `#1D4ED8` outline | `#7AA2F7` outline | value supplied by a reviewer | `PenLine` | "Supplied by user" |
| `--synthetic` | `#422006` / `#FDE68A` | same | SYNTHETIC badge (same in both modes) | `FlaskConical` | "SYNTHETIC DATA" |
| `--airgap` | `#E2E8F0` / `#0F172A` with dot `#22C55E` | same | footer | `ShieldCheck` | "AIR-GAPPED" |

Contrast of each fg on its bg: eq 6.4:1, ne 5.8:1, ins 5.8:1, auto 5.8:1, review 6.6:1, ai 6.1:1 (light); 8.8, 6.3, 9.3, 6.4, 6.4, 8.7 (dark); ribbon 11.7:1; footer 14.5:1.

**Rule:** red, green and amber appear **only** for verdict and status meaning. Charts use the same semantic colours for verdicts and neutral greys otherwise; no rainbow palettes.

### 3.3 Typography

| Token | Value |
|---|---|
| UI font | **Inter** (self-hosted via `@fontsource/inter`, weights 400/500/600) |
| Mono font | **JetBrains Mono** (self-hosted via `@fontsource/jetbrains-mono`, 400/600) for material descriptions, codes, CNMCs, attribute values. Before adopting, render the test string `O0o l1I| 5S 8B` at 13 px and confirm every glyph is distinct; if not, switch to IBM Plex Mono |
| No web fonts at runtime | The app is offline (TRD TR-UI-07); fonts are bundled |
| Numbers | `font-variant-numeric: tabular-nums` in tables and stat tiles |

| Style | Size / line height | Weight | Use |
|---|---|---|---|
| `display` | 30 / 36 | 600 | stat tile number |
| `h1` | 24 / 32 | 600 | page title |
| `h2` | 20 / 28 | 600 | section title |
| `h3` | 16 / 24 | 600 | card title |
| `body` | 14 / 22 | 400 | default text |
| `table` | 13 / 20 | 400 | table cells |
| `mono` | 13 / 20 | 400 | descriptions, codes |
| `label` | 12 / 16 | 500, letter-spacing 0.02em, uppercase only for sidebar group labels | labels, chips |
| `micro` | 11 / 14 | 500 | footer, badges counts (never below 11 px) |

In stage mode every size scales by 115%.

### 3.4 Space, shape, depth

| Token | Value |
|---|---|
| Spacing scale | 4-px grid: 4, 8, 12, 16, 24, 32, 48 |
| Radius | 6 px controls and cards; 4 px chips and badges; 999 px only for status dots |
| Borders | 1 px `--border`; inputs 1 px `--border-strong` |
| Shadows | Only for floating layers: popover/menu `0 4px 12px rgb(0 0 0 / 0.08)`; modal `0 12px 32px rgb(0 0 0 / 0.16)`. Cards are flat with a border |
| Focus | 2 px `--primary` outline, 2 px offset, on every interactive element; never removed |
| Motion | 120–160 ms ease-out for popovers, drawers, row highlight. No decorative animation. `prefers-reduced-motion` disables all transitions except progress bars |
| Z-order | sidebar 10 · top bar 20 · drawer 40 · modal 50 · toast 60 · top-bar badges 70 |

### 3.5 Iconography
`lucide-react` (bundled, offline). 16 px in tables, 20 px in buttons and headers, stroke 1.75. Icons never appear without a text label or an `aria-label`.

---

## 4. Layout system

| Item | Spec |
|---|---|
| Design target | **1366 × 768 first**, then 1920 × 1080. Everything on the demo path must fit 1366 × 768 at 100% without horizontal scroll |
| Shell | Sidebar 220 px with **5 task items + Rules + Help** (collapsible to 56 px icons) · top bar 52 px holding the page title, the SYNTHETIC badge, the run selector (run-scoped pages only) and the user menu · **slim footer 24 px** with only the air-gap status · no full-width ribbon |
| Content | Fluid width, 24 px padding; reading text max 72 characters wide; tables use full width |
| Grid | 12 columns, 16 px gutter for dashboards; detail pages use a 2:1 split (main : side panel) at ≥ 1280 px |
| Density | Table rows **40 px default** (comfortable) / 32 px (compact toggle); stage mode 44 px |
| Responsive | ≥ 1024 px full app. 768–1023 px: sidebar collapsed to icons, side panels move below. < 768 px (phones): **read-only** support for S9 search and S8 registry lookup only (tables become stacked cards); other screens show "Use a larger screen for review" |

---

## 5. Content and microcopy

| Rule | Example |
|---|---|
| Verdict words are fixed | "Identical", "Equivalent", "Not equivalent", "Insufficient data". Never "Match 95%" |
| Always say what is unknown | "Face not stated on CPSE-B record" rather than "Low confidence" |
| Counts with their base | "False merges: 0 of 1,212 hard negatives (95% upper bound 0.25%)" — never "0 errors" or "100% accurate" (example numbers only) |
| Confidence is labelled | "Confidence (heuristic) 0.88" in P0; "Probability (calibrated)" only after P1 |
| Banned words (PRD NFR-14) | first, only, best, novel algorithm, beats, guaranteed, 100% |
| Numbers | Indian grouping for money via `Intl.NumberFormat('en-IN')` (₹12,34,567); counts with thin separators (12,345); shares to 1 decimal ("3.4%") |
| Dates | Stored UTC; displayed in IST as `03 Oct 2026, 10:19`; relative times only in lists ("5 min ago", full date on hover) |
| Buttons | Verb first: "Start run", "Confirm and issue code", "Download migration pack" |
| Errors | What happened + what to do: "This legacy code is already mapped to NMC-…. Open it or unmerge it first." |
| Codes | CNMC and legacy codes in mono with a copy button |

---

## 6. Component specifications

| Component | Anatomy | States / rules |
|---|---|---|
| **VerdictBadge** | icon + text in a 4-px-radius chip using the semantic fg/bg pair | sizes sm (table) and md (headers). Never colour-only |
| **RouteTag** | outlined chip: "Auto-eligible" (`--auto`) or "Review" (`--review`) with reason tooltip | — |
| **EvidenceCard** | table: `attribute · level (core/ext) · value A · value B · status · note` + rule icon | Row background tinted by status (MATCH none, CONFLICT `--ne` bg, PARTIAL/MISSING `--ins` bg). **Decisive attribute** row gets a 3-px left bar in `--ne` and bold values. Conversion notes as small mono chips under the value (`4 IN = DN100`). `MISSING_BOTH` rows collapsed into "+2 not stated on either side". Provenance badges (`ML`, `Supplied by user`) after values **v1.2:** by default show only the rows that decide the outcome (conflicts, partial/missing core values, flags) plus a one-line summary "5 of 7 attributes match"; "Show all attributes" expands the rest |
| **RulePopover** | rule ID (mono), rule text, template version, "Open in rulebook" link | opens on click and on focus+Enter; closes on Esc |
| **ConversionChip** | mono 11 px chip, `--surface-2` bg | e.g. `WCB → A216-WCB`, `STD = SCH40 (DN150 ≤ 250)` |
| **RecordColumn** | CPSE tag, legacy code (mono, copy), raw description (mono, wraps), UoM, make/MPN | Up to 4 columns side by side; more → horizontal scroll within the card only |
| **CNMCChip** | `NMC-00000001974` mono + copy + link | — |
| **CharCounter** | `35 / 40` | turns `--ins` at 36–40, `--ne` above 40 with text "too long; abbreviate" |
| **StatTile** | label (12 px muted), number (display), sublabel with base ("of 10,230 records") | optional sparkline; source tag "Run 4F2A · synthetic" |
| **DataTable** | sticky header, sortable columns, numeric right-aligned, row hover `--surface-2`, virtualised > 200 rows | selection checkbox only where bulk actions exist |
| **FilterBar** | chips for active filters, "Clear all" | reflects URL state |
| **SyntheticBadge** | compact amber badge in the top bar: flask icon + "SYNTHETIC DATA" (`--synthetic`), tooltip "Results on synthetic data are optimistic by construction" | not dismissible; on every page with synthetic data; present in screenshots (replaces the v1.1 full-width ribbon) |
| **AirGapStatus** | slim footer, right-aligned: green dot + "Air-gapped · 0 blocked" (micro text); version and commit moved to Help | grey "status unavailable" until the endpoint exists; amber `GUARD OFF` / `DENSE OFF` tags when relevant |
| **StageStepper** | horizontal steps with counts and durations | current step animated progress bar only |
| **HonestyPanel** | bordered card with `Info` icon, fixed copy from PRD 9.13.5 | always expanded on S11 |
| **Toast** | bottom-right, 4 s, action link optional | errors stay until dismissed |
| **Modal / Drawer** | modal max 560 px; drawer 480 px from right | focus trapped; Esc closes; primary action right-aligned |
| **EmptyState** | 32-px muted icon, one-line title, one sentence, one primary button | copy from 03 App Flow 8.2 |
| **Skeleton** | grey blocks matching row height | no shimmer under reduced motion |
| **Buttons** | primary (filled `--primary`), secondary (outline), ghost (text), danger (filled `--danger`) · height 32 px (36 px stage mode) | disabled = 50% opacity + `not-allowed` cursor + tooltip explaining why |
| **ConsentStrip** (SF-11) | one chip per participating CPSE: `CPSE-A ✔` (`--eq`), `CPSE-C … waiting` (`--review` with a clock icon), `CPSE-C ✖ declined` (`--ne`, reason in tooltip) | always in the S6 header for multi-CPSE clusters, in S18 rows and on the CNMC page history; never colour-only |
| **ImpactPreviewTable** (SF-6) | transition matrix (from → to verdict with counts), affected CNMCs per CPSE, first 50 changes | zero-change result shown as a calm green "No stored decision changes"; non-zero transitions use the semantic colours of the *target* verdict |
| **NextStepCard** | on Home: one sentence, one primary button, optional 5-step first-run checklist with the current step highlighted | content by role (App Flow 3.3); "All caught up" when nothing is pending |
| **PageHeader** | title (h1), one-sentence purpose (muted), one primary button on the right, "⋯" menu for the rest | used on every page |
| **Tabs** | underline tabs under the page header for sibling screens (e.g. Review: To review · Consents · Look-alikes); badge numbers only where action is needed | URL changes per tab so links and Back work |
| **GlossaryTooltip** | dotted underline on technical words; tooltip with one plain sentence and "More in Help" | verdict names, CNMC, consent, veto, look-alike |
| **Keyboard hints** | small `kbd` chips next to S6 action buttons: `A` `R` `S` `N` | hidden on touch devices |

---

## 7. Screen layouts

The layouts below define placement; flows and actions are in 03 App Flow.

### 7.1 S0 Home (v1.2)
```
┌ Home · Run 4F2A ─────────────────────────────────────────────── [SYNTHETIC DATA] ┐
│ ┌ Next step ───────────────────────────────────────────────────────────────────┐ │
│ │ 12 clusters wait for your review.                       [ Start reviewing ]   │ │
│ └──────────────────────────────────────────────────────────────────────────────┘ │
│ [Records 3,0xx]   [Duplicates found 2xx · 8%]   [National codes issued 4x]       │  3 tiles only
│                                                                                  │
│ Duplicates by CPSE (one bar chart, one takeaway sentence above it)               │
│                                                                                  │
│ ▸ More: verdict mix · data quality · top clusters · demand across CPSEs          │  collapsed
└──────────────────────────────────────────────────────────────────────────────────┘
```
(Numbers are placeholders, not results.) Everything from the v1.1 dashboard is still there (PRD FR-1201, FR-1203), but behind "More" so a new user is not overwhelmed. On stage, open "More" when you reach the demand panel.

### 7.2 S5 Review queue
Filter bar on top; table columns: priority bar (small horizontal bar), category, members, CPSE tags, verdict summary (badges), flags (⚠ count with tooltip), critical (shield icon + "Critical"), proposed CNMC text (mono, truncated with tooltip), state chip.

### 7.3 S6 Cluster review (the hero screen)
```
┌ ‹ Queue   Cluster 4F2A · VALVE · 3 records · 3 CPSEs · priority 0.82        [SYNTHETIC] ┐
│ [✔ Equivalent]  [Review: critical class]  ⚠ design_standard unverified                  │
├───────────────────────────┬───────────────────────────┬─────────────────────────────────┤
│ CPSE-A · 100234 ⧉         │ CPSE-B · 77-4410 ⧉        │ CPSE-C · VLV-00918 ⧉            │
│ VALVE GATE 4IN CL150      │ GATE VALVE, 4 INCH, CLASS │ GV 100NB 150# WCB RF FLANGED    │
│ A216 WCB FLGD RF          │ 150, ASTM A216 WCB, RF    │                                 │
│ EA · —                    │ NOS → EA                  │ EA                              │
├───────────────────────────┴───────────────────────────┴─────────────────────────────────┤
│ EVIDENCE                                     A            B            status    rule   │
│ valve_type        core                       GATE         GATE         ✔ Match    ⓘ     │
│                                                           [GV = GATE]                   │
│ size_dn           core                       100          100          ✔ Match    ⓘ     │
│                                              [4 IN = DN100] [100 NB = DN100]            │
│ pressure_class    core                       150          150          ✔ Match    ⓘ     │
│ body_material     core                       A216-WCB     A216-WCB     ✔ Match    ⓘ     │
│ design_standard   ext                        API-600      (not stated) ⚠ Unverified ⓘ   │
│ + 1 attribute not stated on either side                                                 │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│ Proposed CNMC text  VLV GATE 4IN CL150 A216-WCB FLGD RF                     35 / 40     │
│ Class path  PIPING › VALVE › GATE      UNSPSC  not mapped                               │
│ Comment [_____________________________________________]                                 │
│ [Approve  A] [Reject  R] [Split…  S] [Needs info  N]                                    │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```
Side panel at ≥ 1280 px: pairs list of the cluster with mini verdict badges and "blocked edges" (why not merged).

### 7.4 S9 Search-before-create
Large input (mono, 16 px) with Check button; parsed chips row; result banner (eq/ins/ne colours with icon and recommended action in words); ranked candidate cards with an expandable evidence card; action buttons at the bottom.

### 7.5 S11 Evaluation report
Fixed vertical order (PRD 9.13.5). Safety headline as a wide card: big "0 of 1,212" style number with label "False merges on hard negatives" and "95% upper bound …" next to it. Baseline scoreboard as a 3-row table with the SpecID row highlighted by a left bar (not by colour fill). Honesty panel always visible, never collapsed. Evidence ladder as four steps with L2 marked "this page".

### 7.5b S18 Consent queue (differentiator, on the demo path)
```
┌ Consents · CPSE-C · 2 waiting ─────────────────────────────────────────────────── [SYNTHETIC] ┐
│ Category  CPSEs                               Your codes   Proposed CNMC text          Waiting │
│ VALVE     [A ✔] [B ✔] [C … waiting]           VLV-00918    VLV GATE 4IN CL150 A216-…    6 min  │
│ FLANGE    [A ✔] [C … waiting]                 FL-2231      FLG WN 4IN CL150 RF A105     12 min │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
Detail: S6 layout read-only, the CPSE-C column outlined in --primary, evidence card below,
sticky bar:  [Consent for CPSE-C]  [Decline…]   "Consenting maps VLV-00918 to the national code."
```

### 7.5c S10 Rulebook impact preview (differentiator, on the demo path)
Two-column at ≥ 1280 px: left = YAML draft editor (mono, line numbers, validation messages inline); right = result panel in fixed order: golden tests (pass/fail count) → **transition table** → **affected CNMCs per CPSE** → first 50 changes (rows open the pair modal) → acknowledgement checkbox → **Activate** button (disabled with a tooltip until tests pass and the box is ticked).

### 7.6 S13 Look-alike Guard
Two tables stacked (look-alikes vetoed first). Each row: similarity as a number **and** a small bar; texts in mono with the differing token highlighted (`--ne` bg on the token in both texts); decisive attribute chip with rule ID. Chart below: strip/scatter plot, x = text similarity 0–1, three horizontal bands for ✔ / ? / ✖, look-alikes outlined in `--ne`, hidden twins in `--eq`; table fallback toggle.

### 7.7 S8b CNMC detail
Header: CNMC chip, short description, status. Two-column body: left = canonical spec table (with provenance badges) and descriptions; right = class path, UNSPSC, variants. Below: crosswalk table (CPSE, legacy code, relation, UoM, factor, migration action chip), substitutes (P1), history timeline.

### 7.8 S2 Upload & mapping
Two-step layout: (1) CPSE + synthetic checkbox + drop zone; (2) mapping table: source column, sample values (3, mono), target field select, confidence of suggestion (high/medium), required markers. Sticky "Save & ingest" bar at the bottom.

---

## 8. Accessibility (WCAG 2.1 AA target)

| Requirement | How |
|---|---|
| Colour is never the only signal | verdicts = colour + icon + text (PRD NFR-09) |
| Contrast | tokens in section 3 meet ≥ 4.5:1 for text and ≥ 3:1 for UI boundaries |
| Keyboard | every action reachable by Tab; S6 shortcuts; visible focus ring; skip-to-content link |
| Screen readers | landmarks (`nav`, `main`, `footer`); tables with `<th scope>`; icons with `aria-label`; run progress in an `aria-live="polite"` region |
| Text size | nothing below 11 px; zoom to 200% without loss of function on desktop |
| Motion | respects `prefers-reduced-motion` |
| Charts | every chart has a table toggle and a text summary |
| Forms | labels always visible (no placeholder-only fields); errors linked with `aria-describedby` |

---

## 9. Implementation notes (Tailwind)

```js
// tailwind.config.js (excerpt) — tokens come from CSS variables
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)", surface: "var(--surface)", "surface-2": "var(--surface-2)",
        border: "var(--border)", "border-strong": "var(--border-strong)",
        text: "var(--text)", muted: "var(--text-muted)",
        primary: "var(--primary)", "on-primary": "var(--on-primary)", danger: "var(--danger)",
        eq: { fg: "var(--eq-fg)", bg: "var(--eq-bg)" }, ne: { fg: "var(--ne-fg)", bg: "var(--ne-bg)" },
        ins: { fg: "var(--ins-fg)", bg: "var(--ins-bg)" }, auto: { fg: "var(--auto-fg)", bg: "var(--auto-bg)" },
        review: { fg: "var(--review-fg)", bg: "var(--review-bg)" }, ai: { fg: "var(--ai-fg)", bg: "var(--ai-bg)" },
      },
      fontFamily: { sans: ["Inter", "system-ui", "sans-serif"], mono: ["JetBrains Mono", "ui-monospace", "monospace"] },
      borderRadius: { DEFAULT: "6px", chip: "4px" },
    },
  },
};
```

```css
/* src/styles/tokens.css (excerpt) */
:root {
  --bg:#F7F8FA; --surface:#FFFFFF; --surface-2:#F1F3F6; --border:#D9DEE5; --border-strong:#8A94A6;
  --text:#14181F; --text-muted:#4B5563; --primary:#1D4ED8; --on-primary:#FFFFFF; --danger:#B42318;
  --eq-fg:#166534; --eq-bg:#E7F6EC; --ne-fg:#B42318; --ne-bg:#FDECEA; --ins-fg:#8A5300; --ins-bg:#FFF4DB;
  --auto-fg:#1D4ED8; --auto-bg:#E8EFFD; --review-fg:#4B5563; --review-bg:#EEF0F3; --ai-fg:#6D28D9; --ai-bg:#F1EBFD;
}
.dark {
  --bg:#0E1116; --surface:#161A21; --surface-2:#1E232B; --border:#2C333D; --border-strong:#646E7D;
  --text:#E6E9EE; --text-muted:#A3ABB8; --primary:#7AA2F7; --on-primary:#0E1116; --danger:#F87171;
  --eq-fg:#4ADE80; --eq-bg:#0F2A1A; --ne-fg:#F87171; --ne-bg:#2E1213; --ins-fg:#FBBF24; --ins-bg:#2E2208;
  --auto-fg:#7AA2F7; --auto-bg:#15213A; --review-fg:#A3ABB8; --review-bg:#222831; --ai-fg:#C4B5FD; --ai-bg:#251C3D;
}
.stage { font-size: 115%; }
```

Component library: plain React components on Tailwind; accessible primitives (dialog, popover, menu) from **Radix UI** (bundled, works offline). No CSS-in-JS.

---

## 10. Screenshots for the slides (PRD G6)

| Slide | Screen | Capture rules |
|---|---|---|
| Slide 2 / 3 (differentiator visual) | **S6 header with the ConsentStrip** "A ✔ · B ✔ · C waiting", or the **S10 impact-preview** transition table | light mode, 1920 × 1080, zoom 125%, crop to the strip or table; label "planned screen" until real |
| Slide 3 (prototype visual) | S13 Look-alike Guard, top 3 rows | light mode, stage mode off, 1920 × 1080, browser zoom 125%, crop to the table; SYNTHETIC badge visible |
| Slide 3 (alternative) | S6 cluster review | evidence card fully visible, decisive row in view |
| Backup / Q&A | S11 scoreboard + honesty panel; S9 search result; footer with counter 0 | same settings |

Until the prototype runs, use a mock built from the S13 wireframe and label it "planned screen" (PRD Q-11).

---

## 11. Design checklist (before demo)

- [ ] Demo path fits 1366 × 768 without horizontal scroll
- [ ] Every verdict shows icon + text
- [ ] **New-user test:** someone who has never seen SpecID completes upload → run → review → issue a code without help, in under 5 minutes; note every place they hesitate and fix it
- [ ] Every page has a one-sentence purpose and at most one primary button
- [ ] No unbuilt screen appears in navigation
- [ ] ConsentStrip and impact-preview table readable at 1366 × 768 in stage mode
- [ ] SYNTHETIC badge on every data screen and in screenshots
- [ ] Footer shows AIR-GAPPED and the counter
- [ ] Fonts and icons load with the network off
- [ ] Stage mode tested on the projector or a TV
- [ ] No banned words (section 5)
- [ ] Focus ring visible on every control

*End of UI/UX Design Brief.*
