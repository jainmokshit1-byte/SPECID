// Where a role lands and which URLs it may open (App Flow 4.3, 4.4). The server still answers 403
// for anything a role may not do (TRD TR-SEC-03); this only decides what the UI shows.

import { routePatternOf } from "../nav";
import { type Role, SHELL_ROUTES } from "../routes";

/** App Flow 4.3: Home for everyone except INTEGRATOR, who lands on Search. */
export function roleHome(role: Role): string {
  return role === "INTEGRATOR" ? "/search" : "/";
}

/** True when the URL's route lists the role (App Flow section 2 roles column). */
export function canOpen(url: string, role: Role): boolean {
  const pathname = url.split(/[?#]/)[0] ?? "";
  const pattern = routePatternOf(pathname);
  const route = SHELL_ROUTES.find((r) => r.path === pattern);
  return route !== undefined && route.roles.includes(role);
}

/** After login: `next` if it is a same-app path the role may open, else the role home. */
export function landingAfterLogin(next: string | null, role: Role): string {
  if (next && next.startsWith("/") && !next.startsWith("//") && canOpen(next, role)) return next;
  return roleHome(role);
}
