import type { LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";
import { BUILT_PATHS } from "../../routes";
import { type ButtonVariant, buttonClass } from "./Button";
import { Tooltip } from "./Tooltip";

/** A button-styled link that never leads to a placeholder: disabled, with the reason, until the
 * target screen is built (UI/UX brief 1.4 rule 6). `pattern` is the route pattern when `to`
 * carries ids or a query. */
export function BuiltLink({
  to,
  label,
  pattern,
  variant = "primary",
  icon: Icon,
}: {
  to: string;
  label: string;
  pattern?: string;
  variant?: ButtonVariant;
  icon?: LucideIcon;
}) {
  const path = pattern ?? to.split("?")[0]!;
  const content = (
    <>
      {Icon && <Icon size={16} strokeWidth={1.9} aria-hidden="true" />}
      {label}
    </>
  );
  if (BUILT_PATHS.has(path))
    return (
      <Link to={to} className={buttonClass(variant)}>
        {content}
      </Link>
    );
  return (
    <Tooltip text="Opens once this screen is built">
      <span tabIndex={0} className="inline-block">
        <button type="button" disabled className={buttonClass(variant)}>
          {content}
        </button>
      </span>
    </Tooltip>
  );
}
