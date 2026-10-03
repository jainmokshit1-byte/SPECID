import { NavLink } from "react-router-dom";
import { NAV_GROUPS } from "../../routes";

/** Left sidebar grouped by job (03 App Flow 3.1). Phase 1: every item shown; role filtering
 * (App Flow 3.2) and queue/consent badges arrive with auth and data in later phases. */
export function Sidebar() {
  return (
    <nav
      aria-label="Main"
      className="z-sidebar flex w-sidebar shrink-0 flex-col overflow-y-auto border-r border-border bg-surface"
    >
      <div className="flex h-topbar shrink-0 items-center px-4 text-h3 text-text">SpecID</div>
      {NAV_GROUPS.map((g) => (
        <div key={g.group} className="px-2 pb-3">
          <div className="px-2 pb-1 text-label uppercase text-muted">{g.group}</div>
          <ul>
            {g.items.map((item) => (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  end={item.path === "/"}
                  className={({ isActive }) =>
                    `flex items-center justify-between rounded px-2 py-1.5 text-body ${
                      isActive
                        ? "bg-surface-2 font-medium text-primary"
                        : "text-text hover:bg-surface-2"
                    }`
                  }
                >
                  <span>{item.label}</span>
                  {item.p1 && <span className="text-micro text-muted">P1</span>}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );
}
