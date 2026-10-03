import { Link } from "react-router-dom";

/** 404 (03 App Flow section 2): "Page not found" + link to the role home. Roles arrive in Phase 3,
 * so the link goes to the dashboard for now. */
export function NotFound() {
  return (
    <section aria-labelledby="nf-title">
      <h1 id="nf-title" className="text-h1">
        Page not found
      </h1>
      <Link to="/" className="mt-2 inline-block text-body text-primary underline">
        Go to your home page
      </Link>
    </section>
  );
}
