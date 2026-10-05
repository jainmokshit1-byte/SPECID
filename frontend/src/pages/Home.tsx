import { useQuery } from "@tanstack/react-query";
import { listBatches } from "../api/batches";
import { listRuns } from "../api/runs";
import { useUser } from "../auth/useAuth";
import { BuiltLink } from "../components/ui/BuiltLink";
import { NextStepCard } from "../components/ui/NextStepCard";
import { PageHeader } from "../components/ui/PageHeader";

const FIRST_RUN_STEPS = ["Upload files", "Check quality", "Run matching", "Review", "Issue codes"];

/** Where the first-run checklist stands, from data only (DEC-16: never an invented number). */
// eslint-disable-next-line react-refresh/only-export-components -- pure helper, tested directly
export function firstRunStep(ingestedCpses: number, doneRuns: number): number {
  if (doneRuns > 0) return 3;
  if (ingestedCpses >= 2) return 2;
  if (ingestedCpses === 1) return 1;
  return 0;
}

const NEXT: { sentence: string; to: string; pattern?: string; label: string }[] = [
  {
    sentence: "Start by uploading a CPSE material master file.",
    to: "/upload",
    label: "Upload files",
  },
  {
    sentence: "Check the quality report, then add a second CPSE's file to compare.",
    to: "/upload",
    label: "Upload another CPSE",
  },
  {
    sentence: "Files from two or more CPSEs are in. Start a matching run.",
    to: "/runs/new",
    label: "Start a run",
  },
  {
    sentence: "A run is done. Review the groups of same items.",
    to: "/review",
    label: "Open review queue",
  },
];

/** S0 Home (UI/UX brief 7.1, App Flow 3.3, 4.3): the Next-step card for the signed-in role.
 * The step follows the data: files ingested per CPSE, then finished runs. The AUDITOR's next
 * step is verifying the audit chain. Stat tiles and the chart arrive with the dashboard (WP1.12). */
export function Home() {
  const { role } = useUser();
  const worker = role !== "AUDITOR";
  const batches = useQuery({ queryKey: ["batches"], queryFn: listBatches, enabled: worker });
  const runs = useQuery({ queryKey: ["runs"], queryFn: listRuns, enabled: worker });
  const cpses = new Set(
    (batches.data ?? []).filter((b) => b.status === "INGESTED").map((b) => b.cpse_code),
  ).size;
  const step = firstRunStep(cpses, (runs.data ?? []).filter((r) => r.status === "DONE").length);
  const next = NEXT[step]!;
  return (
    <section className="max-w-5xl">
      <PageHeader title="Home" purpose="Start here: the card below shows what to do next." />
      {!worker ? (
        <NextStepCard
          sentence="Verify the audit chain to check that no event was changed."
          action={<BuiltLink to="/audit" label="Open audit" />}
        />
      ) : (
        <NextStepCard
          sentence={next.sentence}
          action={<BuiltLink to={next.to} label={next.label} />}
          steps={FIRST_RUN_STEPS}
          current={step}
        />
      )}
    </section>
  );
}
