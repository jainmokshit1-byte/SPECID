import { Link } from "react-router-dom";
import { NextStepCard } from "../components/ui/NextStepCard";
import { PageHeader } from "../components/ui/PageHeader";
import { Tooltip } from "../components/ui/Tooltip";
import { BUILT_PATHS } from "../routes";

const FIRST_RUN_STEPS = ["Upload files", "Check quality", "Run matching", "Review", "Issue codes"];

/** S0 Home (UI/UX brief 7.1, App Flow 3.3). Phase 1: the first-run checklist only; stat tiles and
 * the chart need runs, and role-specific next steps need sign-in (Phase 3). */
export function Home() {
  return (
    <section className="max-w-5xl">
      <PageHeader title="Home" purpose="Start here: the card below shows what to do next." />
      <NextStepCard
        sentence="Start by uploading a CPSE material master file."
        action={<UploadButton />}
        steps={FIRST_RUN_STEPS}
        current={0}
      />
    </section>
  );
}

const PRIMARY =
  "inline-flex h-8 items-center rounded bg-primary px-3 text-body font-medium text-on-primary";

/** Never leads to a placeholder: disabled, with the reason, until S2 is built (Phase 5). */
function UploadButton() {
  if (BUILT_PATHS.has("/upload"))
    return (
      <Link to="/upload" className={PRIMARY}>
        Upload files
      </Link>
    );
  return (
    <Tooltip text="Upload opens once the upload screen is built">
      <span tabIndex={0} className="inline-block">
        <button type="button" disabled className={`${PRIMARY} cursor-not-allowed opacity-50`}>
          Upload files
        </button>
      </span>
    </Tooltip>
  );
}
