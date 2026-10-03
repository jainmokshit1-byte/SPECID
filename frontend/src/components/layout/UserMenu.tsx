import * as DM from "@radix-ui/react-dropdown-menu";
import { ChevronDown, KeyRound, LogOut, UserRound } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth, useUser } from "../../auth/useAuth";
import { ChangePasswordDialog } from "../ChangePasswordDialog";

const ITEM =
  "flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-body text-text outline-none data-[highlighted]:bg-surface-2";

/** User menu (App Flow 3.3): name, role, CPSE; "Change password"; "Logout" → /login (4.4). */
export function UserMenu() {
  const user = useUser();
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [changing, setChanging] = useState(false);
  const name = user.display_name || user.username;

  return (
    <>
      <DM.Root>
        <DM.Trigger className="flex h-8 items-center gap-1.5 rounded px-2 text-body text-text hover:bg-surface-2">
          <UserRound size={18} strokeWidth={1.75} aria-hidden="true" />
          {name}
          <ChevronDown size={14} strokeWidth={1.75} aria-hidden="true" />
        </DM.Trigger>
        <DM.Portal>
          <DM.Content
            align="end"
            sideOffset={4}
            className="z-modal min-w-52 rounded border border-border bg-surface p-1 shadow-md"
          >
            <DM.Label className="px-2 py-1.5">
              <span className="block text-body font-medium text-text">{name}</span>
              <span className="block text-label text-muted">
                {user.role}
                {user.cpse_code ? ` · ${user.cpse_code}` : ""}
              </span>
            </DM.Label>
            <DM.Separator className="my-1 h-px bg-border" />
            <DM.Item className={ITEM} onSelect={() => setChanging(true)}>
              <KeyRound size={16} strokeWidth={1.75} aria-hidden="true" />
              Change password
            </DM.Item>
            <DM.Item
              className={ITEM}
              onSelect={() => {
                logout();
                navigate("/login", { replace: true });
              }}
            >
              <LogOut size={16} strokeWidth={1.75} aria-hidden="true" />
              Logout
            </DM.Item>
          </DM.Content>
        </DM.Portal>
      </DM.Root>
      <ChangePasswordDialog open={changing} onOpenChange={setChanging} />
    </>
  );
}
