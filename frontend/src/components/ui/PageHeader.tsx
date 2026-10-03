import type { ReactNode } from "react";

/** Every page: title, one-sentence purpose, at most one primary action (UI/UX brief 6, 1.4). */
export function PageHeader({
  title,
  purpose,
  action,
}: {
  title: string;
  purpose: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-6 flex items-start justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-h1">{title}</h1>
        <p className="mt-1 max-w-[72ch] text-body text-muted">{purpose}</p>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
