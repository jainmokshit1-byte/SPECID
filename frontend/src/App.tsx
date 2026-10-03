import { Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { TooltipProvider } from "./components/ui/Tooltip";
import { Home } from "./pages/Home";
import { Login } from "./pages/Login";
import { NotFound } from "./pages/NotFound";
import { Placeholder } from "./pages/Placeholder";
import { LOGIN_ROUTE, SHELL_ROUTES } from "./routes";

/** Built screens get their page; every other App Flow route renders its placeholder by URL. */
const PAGES: Record<string, () => JSX.Element> = { "/": Home };

export function App() {
  return (
    <TooltipProvider delayDuration={300}>
      <Routes>
        <Route path={LOGIN_ROUTE.path} element={<Login />} />
        <Route element={<AppShell />}>
          {SHELL_ROUTES.map((r) => {
            const Page = PAGES[r.path];
            return (
              <Route
                key={r.path}
                path={r.path}
                element={Page ? <Page /> : <Placeholder route={r} />}
              />
            );
          })}
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </TooltipProvider>
  );
}
