import { Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthProvider";
import { useUser } from "./auth/useAuth";
import { RequireAuth } from "./auth/RequireAuth";
import { AppShell } from "./components/layout/AppShell";
import { TooltipProvider } from "./components/ui/Tooltip";
import { Home } from "./pages/Home";
import { Login } from "./pages/Login";
import { NoAccess } from "./pages/NoAccess";
import { NotFound } from "./pages/NotFound";
import { Placeholder } from "./pages/Placeholder";
import { LOGIN_ROUTE, type RouteDef, SHELL_ROUTES } from "./routes";

/** Built screens get their page; every other App Flow route renders its placeholder by URL. */
const PAGES: Record<string, () => JSX.Element> = { "/": Home };

/** A route the role may not open stays on its URL and shows "No access" (App Flow 4.4). */
function Screen({ route }: { route: RouteDef }) {
  const user = useUser();
  if (!route.roles.includes(user.role)) return <NoAccess route={route} />;
  const Page = PAGES[route.path];
  return Page ? <Page /> : <Placeholder route={route} />;
}

export function App() {
  return (
    <AuthProvider>
      <TooltipProvider delayDuration={300}>
        <Routes>
          <Route path={LOGIN_ROUTE.path} element={<Login />} />
          <Route
            element={
              <RequireAuth>
                <AppShell />
              </RequireAuth>
            }
          >
            {SHELL_ROUTES.map((r) => (
              <Route key={r.path} path={r.path} element={<Screen route={r} />} />
            ))}
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </TooltipProvider>
    </AuthProvider>
  );
}
