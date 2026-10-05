import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

/** StatTile (UI/UX brief 6): small label, big number, sublabel with its base. */
export function StatTile({
  label,
  value,
  sub,
  icon: Icon,
  accent,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  icon?: LucideIcon;
  accent?: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface px-4 py-3 shadow-sm">
      <div className="flex items-center gap-1.5 text-label uppercase tracking-wide text-muted">
        {Icon && <Icon size={14} strokeWidth={1.9} aria-hidden="true" className={accent} />}
        {label}
      </div>
      <div className="tabular mt-1 text-h1 text-text">{value}</div>
      {sub && <div className="mt-0.5 text-label font-normal text-muted">{sub}</div>}
    </div>
  );
}
