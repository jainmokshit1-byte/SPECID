import { type FormEvent, useState } from "react";
import { apiPost } from "../api/client";
import { useAuth } from "../auth/useAuth";
import { Dialog } from "./ui/Dialog";
import { BTN_PRIMARY, BTN_SECONDARY, Field, ProblemAlert } from "./ui/Form";

const MIN_LEN = 10; // TRD TR-SEC-01

/** "Change password" from the user menu, and the forced first-login change (App Flow 4.2).
 * POST /me/password (DEC-14); the server writes PASSWORD_CHANGED (DEC-15). */
export function ChangePasswordDialog({
  open,
  onOpenChange,
  forced = false,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  forced?: boolean;
}) {
  const { refresh } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    if (next.length < MIN_LEN) return setMessage(`Use at least ${MIN_LEN} characters.`);
    if (next !== confirm) return setMessage("The two new passwords do not match.");
    setBusy(true);
    try {
      await apiPost("/me/password", { current_password: current, new_password: next });
      setCurrent("");
      setNext("");
      setConfirm("");
      await refresh();
      onOpenChange(false);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      forced={forced}
      title="Change password"
      description={
        forced
          ? "Choose your own password before you continue. Your current password was set by an admin."
          : "Enter your current password and a new one."
      }
    >
      <form onSubmit={submit} noValidate>
        <ProblemAlert error={error}>{message}</ProblemAlert>
        <Field
          id="cp-current"
          label="Current password"
          type="password"
          autoComplete="current-password"
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
          required
        />
        <Field
          id="cp-new"
          label="New password"
          type="password"
          autoComplete="new-password"
          hint={`At least ${MIN_LEN} characters.`}
          value={next}
          onChange={(e) => setNext(e.target.value)}
          required
        />
        <Field
          id="cp-confirm"
          label="Repeat new password"
          type="password"
          autoComplete="new-password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          required
        />
        <div className="mt-4 flex justify-end gap-2">
          {!forced && (
            <button type="button" className={BTN_SECONDARY} onClick={() => onOpenChange(false)}>
              Cancel
            </button>
          )}
          <button type="submit" className={BTN_PRIMARY} disabled={busy || !current}>
            Change password
          </button>
        </div>
      </form>
    </Dialog>
  );
}
