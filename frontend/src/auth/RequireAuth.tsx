import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { ChangePasswordDialog } from "../components/ChangePasswordDialog";
import { useAuth } from "./useAuth";

/** App Flow 4.2: no valid token → /login?next=<current URL>. A user who must change the password
 * gets the forced dialog first (never demo users when SEED_DEMO_USERS=true: their flag is off). */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { status, user } = useAuth();
  const { pathname, search } = useLocation();
  if (status === "loading")
    return (
      <p role="status" className="p-6 text-body text-muted">
        Loading…
      </p>
    );
  if (status === "signed-out" || !user)
    return <Navigate to={`/login?next=${encodeURIComponent(pathname + search)}`} replace />;
  return (
    <>
      {children}
      {user.must_change_password && <ChangePasswordDialog forced open onOpenChange={() => {}} />}
    </>
  );
}
