import { Link } from "react-router-dom";
import { PageHeader } from "../components/ui/PageHeader";

/** 404 (03 App Flow section 2): "Page not found" + link to the role home. Roles arrive in Phase 3,
 * so the link goes to Home for now. */
export function NotFound() {
  return (
    <section>
      <PageHeader title="Page not found" purpose="There is no page at this address." />
      <Link to="/" className="text-body text-primary underline">
        Go to your home page
      </Link>
    </section>
  );
}
