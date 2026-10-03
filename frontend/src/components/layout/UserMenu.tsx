import * as DM from "@radix-ui/react-dropdown-menu";
import { ChevronDown, LogIn, UserRound } from "lucide-react";
import { Link } from "react-router-dom";

/** User menu (App Flow 3.3). Name, role, CPSE, "Change password" and "Logout" arrive with sign-in
 * in Phase 3; until then it offers the login page only. */
export function UserMenu() {
  return (
    <DM.Root>
      <DM.Trigger className="flex h-8 items-center gap-1.5 rounded px-2 text-body text-muted hover:bg-surface-2">
        <UserRound size={18} strokeWidth={1.75} aria-hidden="true" />
        Not signed in
        <ChevronDown size={14} strokeWidth={1.75} aria-hidden="true" />
      </DM.Trigger>
      <DM.Portal>
        <DM.Content
          align="end"
          sideOffset={4}
          className="z-modal min-w-40 rounded border border-border bg-surface p-1 shadow-md"
        >
          <DM.Item asChild>
            <Link
              to="/login"
              className="flex items-center gap-2 rounded px-2 py-1.5 text-body text-text outline-none data-[highlighted]:bg-surface-2"
            >
              <LogIn size={16} strokeWidth={1.75} aria-hidden="true" />
              Go to login
            </Link>
          </DM.Item>
        </DM.Content>
      </DM.Portal>
    </DM.Root>
  );
}
