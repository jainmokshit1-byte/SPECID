import { Check } from "lucide-react";
import type { ReactNode } from "react";

/** Home, top: one sentence, one primary button, optional first-run checklist with the current
 * step highlighted (UI/UX brief 6, App Flow 3.3). */
export function NextStepCard({
  sentence,
  action,
  steps,
  current,
}: {
  sentence: string;
  action: ReactNode;
  steps?: string[];
  /** Index of the current step in `steps`. */
  current?: number;
}) {
  return (
    <section
      aria-labelledby="next-step-title"
      className="rounded border border-border bg-surface p-5"
    >
      <h2 id="next-step-title" className="text-label uppercase text-muted">
        Next step
      </h2>
      <div className="mt-2 flex items-center justify-between gap-4">
        <p className="text-h3">{sentence}</p>
        <div className="shrink-0">{action}</div>
      </div>
      {steps && (
        <ol aria-label="First-run steps" className="mt-4 flex flex-wrap gap-2">
          {steps.map((s, i) => {
            const state =
              current === undefined
                ? "todo"
                : i < current
                  ? "done"
                  : i === current
                    ? "current"
                    : "todo";
            return (
              <li
                key={s}
                aria-current={state === "current" ? "step" : undefined}
                className={`flex items-center gap-1.5 rounded-chip px-2 py-1 text-label ${
                  state === "current"
                    ? "bg-primary text-on-primary"
                    : state === "done"
                      ? "bg-eq-bg text-eq-fg"
                      : "bg-surface-2 text-muted"
                }`}
              >
                {state === "done" ? (
                  <Check size={14} strokeWidth={2} aria-label="done" />
                ) : (
                  <span aria-hidden="true">{i + 1}</span>
                )}
                {s}
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
