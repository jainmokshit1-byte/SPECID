import type { ReactNode } from "react";

/** A bordered surface block with an optional header line (title, one-line hint, actions). */
export function Card({
  title,
  hint,
  actions,
  children,
  className = "",
  padded = true,
}: {
  title?: ReactNode;
  hint?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  padded?: boolean;
}) {
  return (
    <section className={`rounded-lg border border-border bg-surface shadow-sm ${className}`}>
      {(title || actions) && (
        <header className="flex items-start justify-between gap-3 border-b border-border px-4 py-3">
          <div className="min-w-0">
            {title && <h2 className="text-h3 text-text">{title}</h2>}
            {hint && <p className="mt-0.5 text-label font-normal text-muted">{hint}</p>}
          </div>
          {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className={padded ? "p-4" : ""}>{children}</div>
    </section>
  );
}
