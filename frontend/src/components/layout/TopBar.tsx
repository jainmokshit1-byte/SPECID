import { useRun } from "../../hooks/useRun";
import { formatDateTime } from "../../lib/format";
import { SyntheticBadge } from "./SyntheticBadge";
import { UserMenu } from "./UserMenu";

/** Top bar (App Flow 3.1, 3.3; UI/UX brief 4): page title, SYNTHETIC DATA badge, run selector on
 * run-scoped pages only (`?run=`, default the newest finished run), user menu. */
export function TopBar({ title, runScoped }: { title: string; runScoped: boolean }) {
  return (
    <header className="z-topbar flex h-topbar shrink-0 items-center gap-3 border-b border-border bg-surface px-6">
      <span className="text-h3 text-text">{title}</span>
      <div className="ml-auto flex items-center gap-3">
        <SyntheticBadge />
        {runScoped && <RunSelect />}
        <UserMenu />
      </div>
    </header>
  );
}

function RunSelect() {
  const { run, done, setRun } = useRun();
  const none = done.length === 0;
  return (
    <>
      <label htmlFor="run-select" className="sr-only">
        Run
      </label>
      <select
        id="run-select"
        disabled={none}
        title={none ? "No finished matching runs yet" : "Matching run shown on this page"}
        value={run ?? ""}
        onChange={(e) => setRun(e.target.value)}
        className="h-8 min-w-40 rounded border border-border-strong bg-surface px-2 text-body text-text disabled:cursor-not-allowed disabled:text-muted disabled:opacity-50"
      >
        {none ? (
          <option value="">No runs yet</option>
        ) : (
          done.map((r) => (
            <option key={r.id} value={r.id}>
              Run {r.id.slice(0, 8)} · {formatDateTime(r.finished_at ?? r.started_at)}
            </option>
          ))
        )}
      </select>
    </>
  );
}
