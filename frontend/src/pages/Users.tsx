import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { apiGet, apiPost } from "../api/client";
import { useUser } from "../auth/useAuth";
import { Dialog } from "../components/ui/Dialog";
import { BTN_PRIMARY, BTN_SECONDARY, Field, INPUT, ProblemAlert } from "../components/ui/Form";
import { PageHeader } from "../components/ui/PageHeader";
import { formatDateTime } from "../lib/format";
import type { Role } from "../routes";

interface UserRow {
  id: string;
  username: string;
  display_name: string | null;
  role: Role;
  cpse_id: string | null;
  cpse_code: string | null;
  is_active: boolean;
  must_change_password: boolean;
  last_login_at: string | null;
  created_at: string;
}

interface Cpse {
  id: string;
  code: string;
  name: string;
}

interface UserList {
  items: UserRow[];
  cpses: Cpse[];
}

const ROLES: Role[] = ["MAKER", "CHECKER", "ADMIN", "AUDITOR", "INTEGRATOR"];
/** Users who act for one CPSE (FR-1501); the API requires the CPSE for them. */
const CPSE_ROLES: Role[] = ["MAKER", "CHECKER"];
const MIN_LEN = 10;

type Modal =
  { kind: "add" } | { kind: "reset"; user: UserRow } | { kind: "disable"; user: UserRow };

/** S16 Users (App Flow 5.15; DEC-14): list, "Add user", "Reset password", "Disable". ADMIN only.
 * API keys are P1 (FR-1004) and not built. Every change is audited by the API. */
export function Users() {
  const me = useUser();
  const queryClient = useQueryClient();
  const users = useQuery({ queryKey: ["users"], queryFn: () => apiGet<UserList>("/users") });
  const [modal, setModal] = useState<Modal | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  function done(message: string) {
    setModal(null);
    setNotice(message);
    void queryClient.invalidateQueries({ queryKey: ["users"] });
  }

  return (
    <section className="max-w-6xl">
      <PageHeader
        title="Users"
        purpose="Add users, reset passwords and disable accounts. Every change is written to the audit log."
        action={
          <button type="button" className={BTN_PRIMARY} onClick={() => setModal({ kind: "add" })}>
            Add user
          </button>
        }
      />
      {notice && (
        <p
          role="status"
          className="mb-4 rounded border border-eq-fg bg-eq-bg px-3 py-2 text-body text-eq-fg"
        >
          {notice}
        </p>
      )}

      {users.isError ? (
        <ProblemAlert error={users.error} />
      ) : users.isPending ? (
        <p role="status" className="text-body text-muted">
          Loading users…
        </p>
      ) : (
        <div className="overflow-x-auto rounded border border-border bg-surface">
          <table className="w-full text-table">
            <thead className="border-b border-border text-left text-label text-muted">
              <tr>
                <th className="px-3 py-2">Username</th>
                <th className="px-3 py-2">Name</th>
                <th className="px-3 py-2">Role</th>
                <th className="px-3 py-2">CPSE</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Last login (IST)</th>
                <th className="px-3 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.data.items.map((u) => (
                <tr key={u.id} className="h-10 border-b border-border hover:bg-surface-2">
                  <td className="px-3 font-mono">{u.username}</td>
                  <td className="px-3">{u.display_name ?? ""}</td>
                  <td className="px-3">{u.role}</td>
                  <td className="px-3">
                    {u.cpse_code ?? <span className="text-muted">none</span>}
                  </td>
                  <td className="px-3">
                    {u.is_active ? "Active" : <span className="text-muted">Disabled</span>}
                    {u.is_active && u.must_change_password && (
                      <span className="ml-2 rounded-chip bg-ins-bg px-1.5 text-micro text-ins-fg">
                        must change password
                      </span>
                    )}
                  </td>
                  <td className="whitespace-nowrap px-3">
                    {u.last_login_at ? (
                      formatDateTime(u.last_login_at)
                    ) : (
                      <span className="text-muted">never</span>
                    )}
                  </td>
                  <td className="px-3 py-1 text-right">
                    <div className="flex justify-end gap-2">
                      <button
                        type="button"
                        className={BTN_SECONDARY}
                        aria-label={`Reset password of ${u.username}`}
                        onClick={() => setModal({ kind: "reset", user: u })}
                      >
                        Reset password
                      </button>
                      {u.is_active && u.id !== me.id && (
                        <button
                          type="button"
                          className={BTN_SECONDARY}
                          aria-label={`Disable ${u.username}`}
                          onClick={() => setModal({ kind: "disable", user: u })}
                        >
                          Disable
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {modal?.kind === "add" && users.data && (
        <AddUserDialog
          cpses={users.data.cpses}
          onClose={() => setModal(null)}
          onDone={(name) =>
            done(`User ${name} created. They must change the temporary password at first login.`)
          }
        />
      )}
      {modal?.kind === "reset" && (
        <ResetDialog
          user={modal.user}
          onClose={() => setModal(null)}
          onDone={() =>
            done(
              `Password of ${modal.user.username} reset. They must change it at their next login.`,
            )
          }
        />
      )}
      {modal?.kind === "disable" && (
        <DisableDialog
          user={modal.user}
          onClose={() => setModal(null)}
          onDone={() => done(`${modal.user.username} is disabled and can no longer sign in.`)}
        />
      )}
    </section>
  );
}

function AddUserDialog({
  cpses,
  onClose,
  onDone,
}: {
  cpses: Cpse[];
  onClose: () => void;
  onDone: (username: string) => void;
}) {
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [role, setRole] = useState<Role>("MAKER");
  const [cpseId, setCpseId] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const create = useMutation({
    mutationFn: () =>
      apiPost<UserRow>("/users", {
        username: username.trim(),
        display_name: displayName.trim() || null,
        role,
        cpse_id: cpseId || null,
        temporary_password: password,
      }),
    onSuccess: (u) => onDone(u.username),
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    setMessage(null);
    if (CPSE_ROLES.includes(role) && !cpseId)
      return setMessage(`A ${role} acts for one CPSE. Choose the CPSE.`);
    if (password.length < MIN_LEN)
      return setMessage(`Use at least ${MIN_LEN} characters for the temporary password.`);
    create.mutate();
  }

  return (
    <Dialog
      open
      onOpenChange={(o) => !o && onClose()}
      title="Add user"
      description="The user signs in with the temporary password and must change it at first login."
    >
      <form onSubmit={submit} noValidate>
        <ProblemAlert error={create.error}>{message}</ProblemAlert>
        <Field
          id="u-username"
          label="Username"
          autoComplete="off"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <Field
          id="u-name"
          label="Display name (optional)"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
        />
        <div className="mb-3 grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="u-role" className="mb-1 block text-label text-text">
              Role
            </label>
            <select
              id="u-role"
              className={INPUT}
              value={role}
              onChange={(e) => setRole(e.target.value as Role)}
            >
              {ROLES.map((r) => (
                <option key={r}>{r}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="u-cpse" className="mb-1 block text-label text-text">
              CPSE{CPSE_ROLES.includes(role) ? "" : " (optional)"}
            </label>
            <select
              id="u-cpse"
              className={INPUT}
              value={cpseId}
              onChange={(e) => setCpseId(e.target.value)}
            >
              <option value="">None</option>
              {cpses.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.code}
                </option>
              ))}
            </select>
          </div>
        </div>
        <Field
          id="u-password"
          label="Temporary password"
          type="password"
          autoComplete="new-password"
          hint={`At least ${MIN_LEN} characters. Give it to the user directly.`}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <div className="mt-4 flex justify-end gap-2">
          <button type="button" className={BTN_SECONDARY} onClick={onClose}>
            Cancel
          </button>
          <button
            type="submit"
            className={BTN_PRIMARY}
            disabled={create.isPending || !username.trim()}
          >
            Add user
          </button>
        </div>
      </form>
    </Dialog>
  );
}

function ResetDialog({
  user,
  onClose,
  onDone,
}: {
  user: UserRow;
  onClose: () => void;
  onDone: () => void;
}) {
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const reset = useMutation({
    mutationFn: () => apiPost(`/users/${user.id}/reset-password`, { temporary_password: password }),
    onSuccess: onDone,
  });
  return (
    <Dialog
      open
      onOpenChange={(o) => !o && onClose()}
      title={`Reset password of ${user.username}`}
      description="Set a temporary password. The user must change it at the next login."
    >
      <form
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          setMessage(null);
          if (password.length < MIN_LEN) return setMessage(`Use at least ${MIN_LEN} characters.`);
          reset.mutate();
        }}
      >
        <ProblemAlert error={reset.error}>{message}</ProblemAlert>
        <Field
          id="r-password"
          label="Temporary password"
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <div className="mt-4 flex justify-end gap-2">
          <button type="button" className={BTN_SECONDARY} onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className={BTN_PRIMARY} disabled={reset.isPending}>
            Reset password
          </button>
        </div>
      </form>
    </Dialog>
  );
}

function DisableDialog({
  user,
  onClose,
  onDone,
}: {
  user: UserRow;
  onClose: () => void;
  onDone: () => void;
}) {
  const disable = useMutation({
    mutationFn: () => apiPost(`/users/${user.id}/disable`),
    onSuccess: onDone,
  });
  return (
    <Dialog
      open
      onOpenChange={(o) => !o && onClose()}
      title={`Disable ${user.username}?`}
      description="They can no longer sign in, and their current session stops working."
    >
      <ProblemAlert error={disable.error} />
      <div className="mt-4 flex justify-end gap-2">
        <button type="button" className={BTN_SECONDARY} onClick={onClose}>
          Cancel
        </button>
        <button
          type="button"
          className="inline-flex h-8 items-center rounded bg-danger px-3 text-body font-medium text-on-primary disabled:opacity-50"
          disabled={disable.isPending}
          onClick={() => disable.mutate()}
        >
          Disable user
        </button>
      </div>
    </Dialog>
  );
}
