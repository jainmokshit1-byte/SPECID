import {
  Ban,
  CircleCheck,
  CircleX,
  Clock3,
  LoaderCircle,
  type LucideIcon,
  OctagonPause,
} from "lucide-react";
import type { ReactNode } from "react";
import { VERDICTS, type Verdict } from "../../lib/verdicts";
import { Tooltip } from "./Tooltip";

export type Tone = "neutral" | "good" | "bad" | "warn" | "info" | "ai";

const TONES: Record<Tone, string> = {
  neutral: "bg-review-bg text-review-fg",
  good: "bg-eq-bg text-eq-fg",
  bad: "bg-ne-bg text-ne-fg",
  warn: "bg-ins-bg text-ins-fg",
  info: "bg-auto-bg text-auto-fg",
  ai: "bg-ai-bg text-ai-fg",
};

/** A small chip: icon + text, never colour alone (UI/UX brief 6). */
export function Chip({
  tone = "neutral",
  icon: Icon,
  children,
  spin,
  className = "",
}: {
  tone?: Tone;
  icon?: LucideIcon;
  children: ReactNode;
  spin?: boolean;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-chip px-1.5 py-0.5 text-label ${TONES[tone]} ${className}`}
    >
      {Icon && (
        <Icon
          size={13}
          strokeWidth={2}
          aria-hidden="true"
          className={spin ? "animate-spin" : undefined}
        />
      )}
      {children}
    </span>
  );
}

/** VerdictBadge: fixed words and colours, with the plain-words meaning on hover. */
export function VerdictBadge({ verdict, count }: { verdict: Verdict; count?: number }) {
  const m = VERDICTS[verdict];
  const Icon = m.icon;
  return (
    <Tooltip text={m.plain}>
      <span
        tabIndex={0}
        className={`inline-flex items-center gap-1 whitespace-nowrap rounded-chip px-1.5 py-0.5 text-label ${m.bg} ${m.fg}`}
      >
        <Icon size={13} strokeWidth={2} aria-hidden="true" />
        {m.label}
        {count !== undefined && (
          <span className="tabular ml-0.5 font-semibold">{count.toLocaleString("en-US")}</span>
        )}
      </span>
    </Tooltip>
  );
}

const STATUS: Record<string, { tone: Tone; icon: LucideIcon; label: string; spin?: boolean }> = {
  QUEUED: { tone: "neutral", icon: Clock3, label: "Queued" },
  RUNNING: { tone: "info", icon: LoaderCircle, label: "Running", spin: true },
  CANCELLING: { tone: "warn", icon: OctagonPause, label: "Cancelling" },
  CANCELLED: { tone: "neutral", icon: Ban, label: "Cancelled" },
  DONE: { tone: "good", icon: CircleCheck, label: "Done" },
  FAILED: { tone: "bad", icon: CircleX, label: "Failed" },
  UPLOADED: { tone: "neutral", icon: Clock3, label: "Uploaded" },
  MAPPED: { tone: "info", icon: Clock3, label: "Mapped" },
  INGESTING: { tone: "info", icon: LoaderCircle, label: "Ingesting", spin: true },
  INGESTED: { tone: "good", icon: CircleCheck, label: "Ingested" },
};

/** Run and batch status as a chip. */
export function StatusBadge({ status }: { status: string }) {
  const s = STATUS[status] ?? { tone: "neutral" as Tone, icon: Clock3, label: status };
  return (
    <Chip tone={s.tone} icon={s.icon} spin={s.spin}>
      {s.label}
    </Chip>
  );
}
