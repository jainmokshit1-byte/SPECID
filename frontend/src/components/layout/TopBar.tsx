import { CircleHelp, UserRound } from "lucide-react";
import { Link } from "react-router-dom";

/** Top bar (03 App Flow 3.1, 3.3): run selector, help, user menu. Runs arrive in Phase 5 and
 * login in Phase 3, so both controls are shown disabled with their reason. */
export function TopBar() {
  return (
    <header className="z-topbar flex h-topbar shrink-0 items-center gap-3 border-b border-border bg-surface px-4">
      <label htmlFor="run-select" className="text-label text-muted">
        Run
      </label>
      <select
        id="run-select"
        disabled
        title="Runs are available from Phase 5"
        className="h-8 min-w-64 cursor-not-allowed rounded border border-border-strong bg-surface px-2 text-body text-muted opacity-50"
      >
        <option>No runs yet</option>
      </select>
      <div className="ml-auto flex items-center gap-3">
        <Link
          to="/about"
          aria-label="Help and About"
          className="rounded p-1 text-muted hover:bg-surface-2"
        >
          <CircleHelp size={20} strokeWidth={1.75} aria-hidden="true" />
        </Link>
        <span className="flex items-center gap-1.5 text-body text-muted">
          <UserRound size={20} strokeWidth={1.75} aria-hidden="true" />
          Not signed in
        </span>
      </div>
    </header>
  );
}
