import * as DM from "@radix-ui/react-dropdown-menu";
import {
  ChevronDown,
  KeyRound,
  LogOut,
  Monitor,
  Moon,
  Presentation,
  Sun,
  UserRound,
} from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth, useUser } from "../../auth/useAuth";
import { type ThemePref, useAppearance } from "../../lib/theme";
import { ChangePasswordDialog } from "../ChangePasswordDialog";

const THEMES = [
  ["light", "Light", Sun],
  ["dark", "Dark", Moon],
  ["system", "Follow system", Monitor],
] as const;

const ITEM =
  "flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-body text-text outline-none data-[highlighted]:bg-surface-2";

/** User menu (App Flow 3.3): name, role, CPSE; "Change password"; "Logout" → /login (4.4). */
export function UserMenu() {
  const user = useUser();
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [changing, setChanging] = useState(false);
  const { theme, setTheme, stage, setStage } = useAppearance();
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
            <DM.Label className="px-2 pb-1 pt-1.5 text-micro uppercase text-muted">
              Appearance
            </DM.Label>
            <DM.RadioGroup value={theme} onValueChange={(v) => setTheme(v as ThemePref)}>
              {THEMES.map(([value, label, Icon]) => (
                <DM.RadioItem key={value} value={value} className={ITEM}>
                  <Icon size={16} strokeWidth={1.75} aria-hidden="true" />
                  {label}
                  <DM.ItemIndicator className="ml-auto text-primary">●</DM.ItemIndicator>
                </DM.RadioItem>
              ))}
            </DM.RadioGroup>
            <DM.CheckboxItem
              className={ITEM}
              checked={stage}
              onCheckedChange={(v) => setStage(v === true)}
            >
              <Presentation size={16} strokeWidth={1.75} aria-hidden="true" />
              Stage mode (projector)
              <DM.ItemIndicator className="ml-auto text-primary">✓</DM.ItemIndicator>
            </DM.CheckboxItem>
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
