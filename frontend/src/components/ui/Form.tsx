import { CircleAlert } from "lucide-react";
import type { InputHTMLAttributes, ReactNode } from "react";
import { ApiError } from "../../api/client";

export const BTN_PRIMARY =
  "inline-flex h-8 items-center justify-center rounded bg-primary px-3 text-body font-medium text-on-primary disabled:cursor-not-allowed disabled:opacity-50";
export const BTN_SECONDARY =
  "inline-flex h-8 items-center justify-center rounded border border-border-strong bg-surface px-3 text-body text-text hover:bg-surface-2 disabled:cursor-not-allowed disabled:opacity-50";
export const INPUT =
  "h-8 w-full rounded border border-border-strong bg-surface px-2 text-body text-text";

/** Labelled input; the label is always visible (UI/UX brief 10). */
export function Field({
  label,
  id,
  hint,
  ...props
}: { label: string; id: string; hint?: string } & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div className="mb-3">
      <label htmlFor={id} className="mb-1 block text-label text-text">
        {label}
      </label>
      <input id={id} className={INPUT} {...props} />
      {hint && <p className="mt-1 text-micro text-muted">{hint}</p>}
    </div>
  );
}

/** Renders an RFC 7807 problem or any error as one short alert (TRD TR-UI-04 ProblemAlert). */
export function ProblemAlert({ error, children }: { error?: unknown; children?: ReactNode }) {
  if (!error && !children) return null;
  let text: ReactNode = children;
  if (!text && error instanceof ApiError)
    text = error.problem.detail || error.problem.title || error.message;
  else if (!text) text = "Something went wrong. Try again.";
  return (
    <p
      role="alert"
      className="mb-3 flex items-start gap-2 rounded border border-danger px-3 py-2 text-body text-danger"
    >
      <CircleAlert size={16} strokeWidth={1.75} aria-hidden="true" className="mt-0.5 shrink-0" />
      <span>{text}</span>
    </p>
  );
}
