// Fixed verdict vocabulary (UI/UX brief 5): words, colour pairs and icons in one place, so no
// screen invents its own "Match 95%". Colour is never the only signal: every badge has an icon.

import {
  CircleCheck,
  CircleDashed,
  CircleHelp,
  CircleSlash,
  type LucideIcon,
  ShieldCheck,
} from "lucide-react";

export type Verdict = "IDENTICAL" | "EQUIVALENT" | "NOT_EQUIVALENT" | "INSUFFICIENT_DATA";

export interface VerdictMeta {
  label: string;
  /** Plain-words explanation for tooltips (UI/UX brief 1.4 rule 5). */
  plain: string;
  fg: string;
  bg: string;
  /** Solid fill for bars and charts. */
  bar: string;
  icon: LucideIcon;
}

export const VERDICTS: Record<Verdict, VerdictMeta> = {
  IDENTICAL: {
    label: "Identical",
    plain: "Same specification and the same maker part number.",
    fg: "text-eq-fg",
    bg: "bg-eq-bg",
    bar: "bg-eq-fg",
    icon: ShieldCheck,
  },
  EQUIVALENT: {
    label: "Equivalent",
    plain: "Same specification, any maker: interchangeable.",
    fg: "text-eq-fg",
    bg: "bg-eq-bg",
    bar: "bg-eq-fg opacity-60",
    icon: CircleCheck,
  },
  NOT_EQUIVALENT: {
    label: "Not equivalent",
    plain: "A key attribute differs (veto). Never merged.",
    fg: "text-ne-fg",
    bg: "bg-ne-bg",
    bar: "bg-ne-fg",
    icon: CircleSlash,
  },
  INSUFFICIENT_DATA: {
    label: "Insufficient data",
    plain: "A key attribute is unknown on one side. The system asks instead of guessing.",
    fg: "text-ins-fg",
    bg: "bg-ins-bg",
    bar: "bg-ins-fg",
    icon: CircleHelp,
  },
};

export const VERDICT_ORDER: Verdict[] = [
  "IDENTICAL",
  "EQUIVALENT",
  "INSUFFICIENT_DATA",
  "NOT_EQUIVALENT",
];

export const UNKNOWN_ICON = CircleDashed;
