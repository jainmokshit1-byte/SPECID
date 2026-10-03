import { SyntheticBadge } from "./SyntheticBadge";
import { UserMenu } from "./UserMenu";

/** Top bar (App Flow 3.1, 3.3; UI/UX brief 4): page title, SYNTHETIC DATA badge, run selector on
 * run-scoped pages only, user menu. Runs arrive in Phase 5, so the selector is disabled until then. */
export function TopBar({ title, runScoped }: { title: string; runScoped: boolean }) {
  return (
    <header className="z-topbar flex h-topbar shrink-0 items-center gap-3 border-b border-border bg-surface px-6">
      <span className="text-h3 text-text">{title}</span>
      <div className="ml-auto flex items-center gap-3">
        <SyntheticBadge />
        {runScoped && (
          <>
            <label htmlFor="run-select" className="sr-only">
              Run
            </label>
            <select
              id="run-select"
              disabled
              title="No matching runs yet"
              className="h-8 min-w-40 cursor-not-allowed rounded border border-border-strong bg-surface px-2 text-body text-muted opacity-50"
            >
              <option>No runs yet</option>
            </select>
          </>
        )}
        <UserMenu />
      </div>
    </header>
  );
}
