import { Link } from "react-router-dom";
import type { VisibleTab } from "../../nav";

/** Underline tabs for the sibling screens of a sidebar item (UI/UX brief 6). Each tab is a link,
 * so the URL changes and Back works. Rendered only when there is more than one tab to show. */
export function Tabs({ tabs, current }: { tabs: VisibleTab[]; current: string | null }) {
  if (tabs.length < 2) return null;
  return (
    <nav aria-label="Section" className="mb-6 flex gap-6 border-b border-border">
      {tabs.map((t) => {
        const active = t.path === current;
        return (
          <Link
            key={t.path}
            to={t.path}
            aria-current={active ? "page" : undefined}
            className={`-mb-px flex items-center gap-1.5 border-b-2 pb-2 text-body ${
              active
                ? "border-primary font-medium text-primary"
                : "border-transparent text-muted hover:text-text"
            }`}
          >
            {t.label}
            {!t.built && <DevTag />}
          </Link>
        );
      })}
    </nav>
  );
}

/** Marks an unbuilt screen that is listed only because the developer switch is on. */
export function DevTag() {
  return (
    <span className="rounded-chip border border-border-strong px-1 text-micro text-muted">dev</span>
  );
}
