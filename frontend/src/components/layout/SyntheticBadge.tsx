import { FlaskConical } from "lucide-react";
import { Tooltip } from "../ui/Tooltip";

/** Compact amber badge in the top bar (UI/UX brief 6; replaces the v1.1 ribbon, DEC-10). Not
 * dismissible. Always on until it is wired to `is_synthetic` in Phase 2 (DEC-05). */
export function SyntheticBadge() {
  return (
    <Tooltip text="Results on synthetic data are optimistic by construction">
      <span
        role="note"
        tabIndex={0}
        aria-label="SYNTHETIC DATA: results on synthetic data are optimistic by construction"
        className="flex h-7 items-center gap-1.5 rounded-chip bg-synthetic-bg px-2 text-label text-synthetic-fg"
      >
        <FlaskConical size={14} strokeWidth={1.75} aria-hidden="true" />
        SYNTHETIC DATA
      </span>
    </Tooltip>
  );
}
