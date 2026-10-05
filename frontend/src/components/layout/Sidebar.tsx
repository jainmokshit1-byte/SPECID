import {
  BookCheck,
  CircleHelp,
  CircleCheckBig,
  Database,
  House,
  type LucideIcon,
  PieChart,
  Upload,
} from "lucide-react";
import { Link } from "react-router-dom";
import type { NavItemId, VisibleItem } from "../../nav";
import { Wordmark } from "../brand/Logo";
import { DevTag } from "../ui/Tabs";

const ICONS: Record<NavItemId, LucideIcon> = {
  home: House,
  data: Upload,
  review: CircleCheckBig,
  registry: Database,
  results: PieChart,
  rules: BookCheck,
  help: CircleHelp,
};

/** Left sidebar, App Flow 3.1: task items at the top, Rules and Help at the bottom. An item links
 * to its first visible tab; items are already filtered by role (3.2). Review/consent badges come
 * with S5 and S18 (Phase 6). */
export function Sidebar({ items, activeId }: { items: VisibleItem[]; activeId: NavItemId | null }) {
  const top = items.filter((i) => !i.bottom);
  const bottom = items.filter((i) => i.bottom);
  return (
    <nav
      aria-label="Main"
      className="z-sidebar flex w-sidebar shrink-0 flex-col border-r border-border bg-surface"
    >
      <div className="flex h-topbar shrink-0 items-center border-b border-border px-4">
        <Wordmark />
      </div>
      <ItemList items={top} activeId={activeId} />
      <div className="mt-auto pb-2">
        <ItemList items={bottom} activeId={activeId} />
      </div>
    </nav>
  );
}

function ItemList({ items, activeId }: { items: VisibleItem[]; activeId: NavItemId | null }) {
  if (items.length === 0) return null;
  return (
    <ul className="space-y-0.5 px-2 pt-2">
      {items.map((item) => {
        const Icon = ICONS[item.id];
        const active = item.id === activeId;
        const first = item.tabs[0]!;
        return (
          <li key={item.id}>
            <Link
              to={first.path}
              aria-current={active ? "page" : undefined}
              className={`flex items-center gap-2.5 rounded px-2 py-2 text-body ${
                active
                  ? "bg-auto-bg font-medium text-primary shadow-[inset_3px_0_0_var(--primary)]"
                  : "text-text hover:bg-surface-2"
              }`}
            >
              <Icon size={18} strokeWidth={1.75} aria-hidden="true" />
              <span className="flex-1">{item.label}</span>
              {item.tabs.every((t) => !t.built) && <DevTag />}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
