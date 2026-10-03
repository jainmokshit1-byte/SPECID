import { Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { Login } from "./pages/Login";
import { NotFound } from "./pages/NotFound";
import { Placeholder } from "./pages/Placeholder";
import { LOGIN_ROUTE, SHELL_ROUTES } from "./routes";

export function App() {
  return (
    <Routes>
      <Route path={LOGIN_ROUTE.path} element={<Login />} />
      <Route element={<AppShell />}>
        {SHELL_ROUTES.map((r) => (
          <Route key={r.path} path={r.path} element={<Placeholder route={r} />} />
        ))}
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
