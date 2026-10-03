import { type FormEvent, useState } from "react";
import { Navigate, useSearchParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/useAuth";
import { landingAfterLogin } from "../auth/access";
import { BTN_PRIMARY, Field, ProblemAlert } from "../components/ui/Form";

/** S1 Login (App Flow 4.1, 4.2): outside the shell. It shows no data, so it carries no SYNTHETIC
 * DATA badge (UI/UX brief 6). No sign-up and no e-mail reset: an ADMIN resets passwords. */
export function Login() {
  const { status, user, login } = useAuth();
  const [params] = useSearchParams();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (status === "signed-in" && user && !busy)
    return <Navigate to={landingAfterLogin(params.get("next"), user.role)} replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setMessage(null);
    setBusy(true);
    try {
      await login(username.trim(), password); // then the signed-in branch above redirects
    } catch (err) {
      setPassword("");
      if (err instanceof ApiError && err.status === 401) setMessage("Wrong username or password");
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
        </section>
      </main>
    </div>
  );
}
