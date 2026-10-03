import { Link } from "react-router-dom";
import { SyntheticRibbon } from "../components/layout/SyntheticRibbon";
import { LOGIN_ROUTE } from "../routes";

/** S1 Login placeholder: rendered outside the shell. Sign-in is built in Phase 3. */
export function Login() {
  return (
    <div className="flex min-h-screen flex-col">
      <SyntheticRibbon />
      <main className="flex flex-1 items-center justify-center p-6">
        <section
          aria-labelledby="login-title"
          className="w-full max-w-sm rounded border border-border bg-surface p-6"
        >
          <span className="rounded-chip bg-surface-2 px-1.5 py-0.5 font-mono text-micro text-muted">
            {LOGIN_ROUTE.screen}
          </span>
          <h1 id="login-title" className="mt-2 text-h1">
            SpecID
          </h1>
          <p className="mt-1 text-body text-muted">
            Placeholder. Sign-in is built in Phase {LOGIN_ROUTE.phase} of the Implementation Plan.
          </p>
          <Link to="/" className="mt-4 inline-block text-body text-primary underline">
            Open the app shell
          </Link>
        </section>
      </main>
    </div>
  );
}
