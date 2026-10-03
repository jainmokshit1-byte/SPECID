import { Lock } from "lucide-react";
import { Link } from "react-router-dom";
import { roleHome } from "../auth/access";
import { useUser } from "../auth/useAuth";
import { PageHeader } from "../components/ui/PageHeader";
import type { RouteDef } from "../routes";

/** App Flow 4.4: a page the role may not open stays on its URL and shows this panel with a link
 * to the role home. The API answers 403 for the same actions (TRD TR-SEC-03). */
export function NoAccess({ route }: { route: RouteDef }) {
  const user = useUser();
  return (
    <section className="max-w-3xl">
      <PageHeader title={route.title} purpose={route.purpose} />
      <div
        role="alert"
        className="flex items-start gap-3 rounded border border-border bg-surface p-4 text-body"
      >
        <Lock size={18} strokeWidth={1.75} aria-hidden="true" className="mt-0.5 text-muted" />
        <div>
          <p className="font-medium">No access</p>
          <p className="mt-1 text-muted">
            The {user.role} role cannot open this page. It is for: {route.roles.join(", ")}.
          </p>
          <Link to={roleHome(user.role)} className="mt-2 inline-block text-primary underline">
            Go to your home page
          </Link>
        </div>
      </div>
    </section>
  );
}
