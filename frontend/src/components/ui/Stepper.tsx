import { Check, CircleX } from "lucide-react";

export interface Step {
  id: string;
  label: string;
  /** Short line under the label, e.g. a count or a duration. */
  detail?: string;
}

/** StageStepper (UI/UX brief 6): horizontal steps; the current one carries a progress bar. */
export function Stepper({
  steps,
  current,
  progress,
  failed,
  finished,
}: {
  steps: Step[];
  /** Id of the running step; null before the first. */
  current: string | null;
  /** 0..1 inside the current step, or null when unknown. */
  progress: number | null;
  failed?: boolean;
  finished?: boolean;
}) {
  const at = finished
    ? steps.length
    : Math.max(
        0,
        steps.findIndex((s) => s.id === current),
      );
  return (
    <ol
      className="grid gap-2"
      style={{ gridTemplateColumns: `repeat(${steps.length}, minmax(0, 1fr))` }}
    >
      {steps.map((s, i) => {
        const done = i < at;
        const active = i === at && !finished;
        const bad = active && failed;
        return (
          <li key={s.id} aria-current={active ? "step" : undefined} className="min-w-0">
            <div className="flex items-center gap-2">
              <span
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-micro font-semibold ${
                  bad
                    ? "bg-ne-bg text-ne-fg"
                    : done
                      ? "bg-eq-bg text-eq-fg"
                      : active
                        ? "bg-primary text-on-primary"
                        : "bg-surface-2 text-muted"
                }`}
              >
                {bad ? (
                  <CircleX size={14} strokeWidth={2.2} aria-label="failed" />
                ) : done ? (
                  <Check size={14} strokeWidth={2.4} aria-label="done" />
                ) : (
                  i + 1
                )}
              </span>
              <span
                className={`truncate text-body ${active ? "font-medium text-text" : "text-muted"}`}
              >
                {s.label}
              </span>
            </div>
            <div className="mt-2 h-1 overflow-hidden rounded-full bg-surface-2">
              <span
                className={`block h-full rounded-full transition-[width] duration-500 ${
                  bad ? "bg-ne-fg" : done ? "bg-eq-fg" : "bg-primary"
                } ${active && progress === null && !bad ? "w-1/3 animate-pulse" : ""}`}
                style={
                  done
                    ? { width: "100%" }
                    : active && progress !== null
                      ? { width: `${progress * 100}%` }
                      : active
                        ? undefined
                        : { width: 0 }
                }
              />
            </div>
            {s.detail && <p className="mt-1 truncate text-micro text-muted">{s.detail}</p>}
          </li>
        );
      })}
    </ol>
  );
}
