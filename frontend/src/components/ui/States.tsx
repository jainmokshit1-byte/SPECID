import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

/** EmptyState (UI/UX brief 6): muted icon, one-line title, one sentence, one action. */
export function EmptyState({
  icon: Icon,
  title,
  text,
  action,
}: {
  icon: LucideIcon;
  title: string;
  text: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center rounded-lg border border-dashed border-border bg-surface px-6 py-10 text-center">
      <Icon size={32} strokeWidth={1.5} aria-hidden="true" className="text-border-strong" />
      <p className="mt-3 text-h3 text-text">{title}</p>
      <p className="mt-1 max-w-md text-body text-muted">{text}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

/** Skeleton blocks while loading (no shimmer under reduced motion: see index.css). */
export function Skeleton({ className = "h-4 w-full" }: { className?: string }) {
  return (
    <span aria-hidden="true" className={`block animate-pulse rounded bg-surface-2 ${className}`} />
  );
}

export function SkeletonRows({ rows = 5 }: { rows?: number }) {
  return (
    <div role="status" aria-label="Loading" className="space-y-3 py-2">
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} className="h-5 w-full" />
      ))}
    </div>
  );
}

/** A small "label: value" line used in summaries. */
export function KeyValue({ k, v }: { k: string; v: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1 text-body">
      <span className="text-muted">{k}</span>
      <span className="tabular text-right text-text">{v}</span>
    </div>
  );
}
