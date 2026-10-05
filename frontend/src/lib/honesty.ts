// One source for the honesty text (PRD FR-1442, DEC-07): S11 Evaluation and S17 About read it
// from here, so the wording cannot drift.

export const HONESTY_POINTS = [
  "Every number on this page comes from synthetic data written by the same team that wrote the rules. It is optimistic by construction.",
  "It is not a measure of accuracy on real CPSE data. Real numbers need a pilot with two or three CPSEs and labelled records.",
  "Zero wrong merges in a test is reported with its upper bound (rule of three), never as “0%” or “never”.",
  "The two text baselines are deliberately simple and tuned fairly on a separate split; stronger learned matchers exist and are not compared here.",
  "Savings shown in the app are price gaps and idle stock on synthetic prices, not savings achieved.",
];

export const EVIDENCE_LADDER = [
  ["L0", "Design", "The rules and the decision policy are written down and reviewed."],
  ["L1", "Unit tests", "Golden pairs and property tests pass on every change."],
  ["L2", "Synthetic benchmark", "Seeded data with known answers: this page."],
  ["L3", "Pilot on real data", "Labelled CPSE records: the next step, not done yet."],
] as const;
