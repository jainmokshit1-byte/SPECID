import { useQuery } from "@tanstack/react-query";
import { GitCompareArrows, Plus } from "lucide-react";
import { Link } from "react-router-dom";
import { ACTIVE, MODE_LABEL, durationMs, formatDuration, listRuns } from "../api/runs";
import { StatusBadge } from "../components/ui/Badge";
import { BuiltLink } from "../components/ui/BuiltLink";
import { ProblemAlert } from "../components/ui/Form";
import { VerdictBar } from "../components/ui/Meter";
import { PageHeader } from "../components/ui/PageHeader";
import { EmptyState, SkeletonRows } from "../components/ui/States";
import { formatCount, formatDateTime } from "../lib/format";

/** S4a Runs (App Flow 5.4): every matching run with its status and verdict mix. */
export function Runs() {
  const runs = useQuery({
    queryKey: ["runs"],
    queryFn: listRuns,
    refetchInterval: (q) => (q.state.data?.some((r) => ACTIVE.includes(r.status)) ? 2000 : false),
  });
  return (
    <section className="max-w-6xl">
      <PageHeader
        title="Matching runs"
        purpose="Each run reads the chosen files, finds likely pairs, decides them and groups the same items."
        action={<BuiltLink to="/runs/new" label="New run" icon={Plus} />}
      />
      {runs.isPending ? (
        <SkeletonRows rows={4} />
      ) : runs.error ? (
        <ProblemAlert error={runs.error} />
      ) : runs.data.length === 0 ? (
        <EmptyState
          icon={GitCompareArrows}
          title="No runs yet"
          text="Upload files from two or more CPSEs, then start a run to find the same items."
          action={<BuiltLink to="/runs/new" label="New run" icon={Plus} />}
        />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border bg-surface">
          <table className="w-full text-table">
            <thead className="bg-surface-2 text-left text-label uppercase tracking-wide text-muted">
              <tr>
                <th className="px-4 py-2 font-medium">Run</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium">Mode</th>
                <th className="px-4 py-2 text-right font-medium">Records</th>
                <th className="px-4 py-2 text-right font-medium">Pairs</th>
                <th className="w-72 px-4 py-2 font-medium">Verdict mix</th>
                <th className="px-4 py-2 font-medium">Started</th>
                <th className="px-4 py-2 text-right font-medium">Took</th>
              </tr>
            </thead>
            <tbody>
              {runs.data.map((r) => (
                <tr key={r.id} className="border-t border-border hover:bg-surface-2">
                  <td className="px-4 py-2.5">
                    <Link
                      className="font-mono text-mono text-primary hover:underline"
                      to={`/runs/${r.id}`}
                    >
                      {r.id.slice(0, 8)}
                    </Link>
                  </td>
                  <td className="px-4 py-2.5">
                    <StatusBadge status={r.status} />
                  </td>
                  <td className="px-4 py-2.5">{MODE_LABEL[r.mode]}</td>
                  <td className="tabular px-4 py-2.5 text-right">
                    {r.stats?.records !== undefined ? formatCount(r.stats.records) : "–"}
                  </td>
                  <td className="tabular px-4 py-2.5 text-right">
                    {r.stats?.candidate_pairs !== undefined
                      ? formatCount(r.stats.candidate_pairs)
                      : "–"}
                  </td>
                  <td className="px-4 py-2.5">
                    {r.stats?.verdicts ? (
                      <VerdictBar verdicts={r.stats.verdicts} showLegend={false} height="h-2" />
                    ) : (
                      <span className="text-label text-muted">–</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-muted">
                    {formatDateTime(r.started_at)}
                    {r.started_by && <span className="block text-micro">by {r.started_by}</span>}
                  </td>
                  <td className="tabular px-4 py-2.5 text-right text-muted">
                    {formatDuration(durationMs(r))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
