import { Link } from "react-router-dom";
import { useUser } from "../auth/useAuth";
import { NextStepCard } from "../components/ui/NextStepCard";
import { PageHeader } from "../components/ui/PageHeader";
import { Tooltip } from "../components/ui/Tooltip";
import { BUILT_PATHS } from "../routes";

const FIRST_RUN_STEPS = ["Upload files", "Check quality", "Run matching", "Review", "Issue codes"];

const PRIMARY =
  "inline-flex h-8 items-center rounded bg-primary px-3 text-body font-medium text-on-primary";

/** S0 Home (UI/UX brief 7.1, App Flow 3.3, 4.3): the Next-step card for the signed-in role.
 * Never an invented number (DECISIONS.md DEC-16): until runs exist, MAKER, CHECKER and ADMIN see
 * the first-run checklist at step 1; review and consent counts arrive with S5 and S18 (Phase 6).
 * The AUDITOR's next step is verifying the audit chain. Stat tiles and the chart need runs. */
export function Home() {
  const { role } = useUser();
  return (
    <section className="max-w-5xl">
      <PageHeader title="Home" purpose="Start here: the card below shows what to do next." />
      {role === "AUDITOR" ? (
        <NextStepCard
          sentence="Verify the audit chain to check that no event was changed."
          action={<BuiltLink to="/audit" label="Open audit" />}
        />
      ) : (
        <NextStepCard
          sentence="Start by uploading a CPSE material master file."
          action={<BuiltLink to="/upload" label="Upload files" />}
          steps={FIRST_RUN_STEPS}
          current={0}
        />
      )}
    </section>
  );
}

/** Never leads to a placeholder: disabled, with the reason, until the target screen is built. */
function BuiltLink({ to, label }: { to: string; label: string }) {
  if (BUILT_PATHS.has(to))
    return (
      <Link to={to} className={PRIMARY}>
        {label}
      </Link>
    );
  return (
    <Tooltip text="Opens once this screen is built">
      <span tabIndex={0} className="inline-block">
        <button type="button" disabled className={`${PRIMARY} cursor-not-allowed opacity-50`}>
          {label}
        </button>
      </span>
    </Tooltip>
  );
}
