import { Outlet, useLocation } from "react-router-dom";
import { useUser } from "../../auth/useAuth";
import { useShowUnbuilt } from "../../hooks/useShowUnbuilt";
import { navLocation, routePatternOf, visibleNav } from "../../nav";
import { RUN_SCOPED_PATHS, SHELL_ROUTES } from "../../routes";
import { Tabs } from "../ui/Tabs";
import { Footer } from "./Footer";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

/** Shell layout, v1.2 minimal (UI/UX brief 4): sidebar 220 px · top bar 52 px · footer 24 px ·
 * no full-width ribbon. Tabs of the current sidebar item sit above the page (App Flow 3.1). */
export function AppShell() {
  const { pathname } = useLocation();
  const showUnbuilt = useShowUnbuilt();
  const { role } = useUser();
  const items = visibleNav(showUnbuilt, role);
  const pattern = routePatternOf(pathname);
  const here = navLocation(pattern);
  const route = SHELL_ROUTES.find((r) => r.path === pattern);
  const title = here?.item.label ?? route?.title ?? "Page not found";
  const tabs = items.find((i) => i.id === here?.item.id)?.tabs ?? [];

  return (
    <div className="flex h-screen">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-toast focus:bg-surface focus:p-2"
      >
        Skip to content
      </a>
      <Sidebar items={items} activeId={here?.item.id ?? null} />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar title={title} runScoped={pattern !== null && RUN_SCOPED_PATHS.has(pattern)} />
        <main id="main" className="flex-1 overflow-y-auto p-6">
          <Tabs tabs={tabs} current={here?.tab.path ?? null} />
          <Outlet />
        </main>
        <Footer />
      </div>
    </div>
  );
}
