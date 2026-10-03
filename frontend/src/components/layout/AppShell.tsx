import { Outlet } from "react-router-dom";
import { AirGapFooter } from "./AirGapFooter";
import { Sidebar } from "./Sidebar";
import { SyntheticRibbon } from "./SyntheticRibbon";
import { TopBar } from "./TopBar";

/** Shell layout (UI/UX brief 4): ribbon 28 px · sidebar 232 px · top bar 52 px · footer 28 px. */
export function AppShell() {
  return (
    <div className="flex h-screen flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-toast focus:bg-surface focus:p-2"
      >
        Skip to content
      </a>
      <SyntheticRibbon />
      <div className="flex min-h-0 flex-1">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopBar />
          <main id="main" className="flex-1 overflow-y-auto p-6">
            <Outlet />
          </main>
        </div>
      </div>
      <AirGapFooter />
    </div>
  );
}
