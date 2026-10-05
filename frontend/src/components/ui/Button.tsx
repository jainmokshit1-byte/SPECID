import { LoaderCircle, type LucideIcon } from "lucide-react";
import { type ButtonHTMLAttributes, forwardRef } from "react";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

const BASE =
  "inline-flex h-8 items-center justify-center gap-1.5 rounded px-3 text-body font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 [.stage_&]:h-9";

const VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-primary text-on-primary hover:brightness-110 active:brightness-95",
  secondary: "border border-border-strong bg-surface text-text hover:bg-surface-2",
  ghost: "text-muted hover:bg-surface-2 hover:text-text",
  danger: "bg-danger text-white hover:brightness-110",
};

// eslint-disable-next-line react-refresh/only-export-components -- pure helper, tested directly
export function buttonClass(variant: ButtonVariant = "primary", extra = ""): string {
  return `${BASE} ${VARIANTS[variant]} ${extra}`.trim();
}

/** Buttons of UI/UX brief 6: primary (filled), secondary (outline), ghost (text), danger.
 * `busy` shows a spinner and disables the button; an icon goes before the label. */
export const Button = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: ButtonVariant;
    icon?: LucideIcon;
    busy?: boolean;
  }
>(function Button(
  { variant = "primary", icon: Icon, busy, className = "", children, disabled, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type="button"
      className={buttonClass(variant, className)}
      disabled={disabled || busy}
      aria-busy={busy || undefined}
      {...rest}
    >
      {busy ? (
        <LoaderCircle size={16} strokeWidth={2} className="animate-spin" aria-hidden="true" />
      ) : (
        Icon && <Icon size={16} strokeWidth={1.9} aria-hidden="true" />
      )}
      {children}
    </button>
  );
});
