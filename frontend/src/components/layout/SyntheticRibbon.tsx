import { FlaskConical } from "lucide-react";

/** Persistent, not dismissible (PRD 11.2, UI/UX brief 6). Always on until it is wired to
 * `is_synthetic` in Phase 2 (docs/DECISIONS.md DEC-05). */
export function SyntheticRibbon() {
  return (
    <div
      role="note"
      className="z-ribbon flex h-bar shrink-0 items-center justify-center gap-2 bg-synthetic-bg text-label text-synthetic-fg"
    >
      <FlaskConical size={16} strokeWidth={1.75} aria-hidden="true" />
      <span>SYNTHETIC DATA: results are optimistic by construction</span>
    </div>
  );
}
