import { useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { Navigate, useSearchParams } from "react-router-dom";
import { ApiError, type Health, apiGet } from "../api/client";
import { useAuth } from "../auth/useAuth";
import { landingAfterLogin } from "../auth/access";
import { BTN_PRIMARY, BTN_SECONDARY, Field, ProblemAlert } from "../components/ui/Form";

const DEMO_ROLES = [
  ["meera", "Maker", "Meera · CPSE-A proposes a national code"],
  ["arjun", "Checker", "Arjun · CPSE-B approves it"],
  ["kavya", "Checker", "Kavya · CPSE-C gives consent"],
  ["admin", "Admin", "Uploads, runs, users"],
  ["auditor", "Auditor", "Reads the audit chain"],
  ["erp", "ERP", "Searches before creating"],
] as const;

/** S1 Login (App Flow 4.1, 4.2): outside the shell. It shows no data, so it carries no SYNTHETIC
 * DATA badge (UI/UX brief 6). No sign-up and no e-mail reset: an ADMIN resets passwords. */
export function Login() {
  const { status, user, login, demoLogin } = useAuth();
  // Polls fast while a free cloud server wakes up or prepares demo data, then every 30 s.
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => apiGet<Health>("/health"),
    retry: false,
    refetchInterval: (q) =>
      q.state.status === "error" || q.state.data?.demo_status === "preparing" ? 4000 : 30_000,
  });
  const demo = health.data?.demo_mode === true;
  const demoReady = health.data?.demo_status === "ready";
  const [params] = useSearchParams();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (status === "signed-in" && user && !busy)
    return <Navigate to={landingAfterLogin(params.get("next"), user.role)} replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    await attempt(() => login(username.trim(), password));
  }

  async function attempt(go: () => Promise<unknown>) {
    setMessage(null);
    setBusy(true);
    try {
      await go(); // then the signed-in branch above redirects
    } catch (err) {
      setPassword("");
      if (err instanceof ApiError && err.status === 401) setMessage("Wrong username or password");
      else if (err instanceof ApiError && err.status === 404)
        setMessage("The demo is still preparing its data. Try again in a minute.");
      else if (err instanceof ApiError && err.status === 429)
        setMessage("Too many attempts, wait 1 minute");
      else setMessage("Cannot reach the SpecID server. Check that the stack is running.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-bg">
      <main className="flex flex-1 items-center justify-center p-6">
        <section
          aria-labelledby="login-title"
          className="w-full max-w-sm rounded border border-border bg-surface p-6"
        >
          <h1 id="login-title" className="text-h1">
            SpecID
          </h1>
          <p className="mb-4 mt-1 text-body text-muted">
            Sign in to the national material registry.
          </p>
          {health.isError && (
            <p role="status" className="mb-3 rounded bg-surface-2 px-3 py-2 text-micro text-muted">
              Connecting to the server… a free cloud demo sleeps when idle and takes about a minute
              to wake up.
            </p>
          )}
          <form onSubmit={submit} noValidate>
            <ProblemAlert>{message}</ProblemAlert>
            <Field
              id="login-username"
              label="Username"
              autoComplete="username"
              autoFocus
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
            <Field
              id="login-password"
              label="Password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <button
              type="submit"
              className={`${BTN_PRIMARY} mt-2 w-full`}
              disabled={busy || !username.trim() || !password}
            >
              {busy ? "Signing in…" : "Sign in"}
            </button>
          </form>
          {demo && (
            <div className="mt-5 border-t border-border pt-4">
              <p className="text-label uppercase tracking-wide text-muted">Demo: sign in as</p>
              {!demoReady && (
                <p className="mt-1 text-micro text-muted" role="status">
                  {health.data?.demo_status === "failed"
                    ? "Demo data could not be prepared; sign in with a password."
                    : "Preparing demo data (synthetic, about a minute after a cold start)…"}
                </p>
              )}
              <div className="mt-2 grid grid-cols-2 gap-2">
                {DEMO_ROLES.map(([u, role, hint]) => (
                  <button
                    key={u}
                    type="button"
                    title={hint}
                    className={`${BTN_SECONDARY} !h-auto flex-col !items-start !py-1.5 text-left`}
                    disabled={busy || !demoReady}
                    onClick={() => void attempt(() => demoLogin(u))}
                  >
                    <span className="text-label">{role}</span>
                    <span className="block truncate text-micro font-normal text-muted">{hint}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
