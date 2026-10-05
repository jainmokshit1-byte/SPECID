import { useQuery } from "@tanstack/react-query";
import { CircleCheckBig, ShieldAlert } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { CATEGORY_LABEL } from "../api/batches";
import { type Stage, STATE_LABEL, listClusters } from "../api/review";
import { useUser } from "../auth/useAuth";
import { Chip } from "../components/ui/Badge";
import { ProblemAlert } from "../components/ui/Form";
import { PageHeader } from "../components/ui/PageHeader";
import { EmptyState, SkeletonRows } from "../components/ui/States";
import { formatCount } from "../lib/format";

const STAGES: { id: Stage | "all"; label: string }[] = [
  { id: "to_propose", label: "To propose" },
  { id: "to_check", label: "To check" },
  { id: "awaiting_consent", label: "Waiting for consent" },
  { id: "done", label: "Done" },
];

const STATE_TONE = {
  OPEN: "info",
  MADE: "warn",
  AWAITING_CONSENT: "neutral",
  DONE: "good",
} as const;

/** S5 Review queue (App Flow 5.5): groups of the same item, highest priority first. A maker
 * starts on "To propose", a checker on "To check"; the filter lives in the URL. */
export function ReviewQueue() {
  const { role } = useUser();
  const [params, setParams] = useSearchParams();
  const stage =
    (params.get("stage") as Stage | null) ?? (role === "CHECKER" ? "to_check" : "to_propose");
  const run = params.get("run") ?? undefined;
  const q = useQuery({
    queryKey: ["clusters", run, stage],
    queryFn: () => listClusters({ run_id: run, stage, limit: 200 }),
  });

  return (
    <section className="max-w-6xl">
      <PageHeader
        title="Review queue"
        purpose="Groups of records that are the same item. Open one, check the evidence, and decide."
      />
      <div role="tablist" aria-label="Stage" className="mb-4 flex flex-wrap gap-1">
        {STAGES.map((s) => (
          <button
            key={s.id}
            type="button"
            role="tab"
            aria-selected={stage === s.id}
            onClick={() => {
              const next = new URLSearchParams(params);
              next.set("stage", s.id);
              setParams(next, { replace: true });
            }}
            className={`rounded-full px-3 py-1 text-label transition-colors ${
              stage === s.id
                ? "bg-primary text-on-primary"
                : "bg-surface-2 text-muted hover:text-text"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>
      {q.isPending ? (
        <SkeletonRows rows={6} />
      ) : q.error ? (
        <ProblemAlert error={q.error} />
      ) : q.data.items.length === 0 ? (
        <EmptyState
          icon={CircleCheckBig}
          title="Nothing waiting here"
          text={
            stage === "to_check"
              ? "No proposals waiting for a second check."
              : "Nothing waiting for you in this stage of the newest run."
          }
        />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border bg-surface">
          <p className="border-b border-border px-4 py-2 text-label font-normal text-muted">
            {formatCount(q.data.total)} groups · sorted by priority (spend × open questions)
          </p>
          <table className="w-full text-table">
            <thead className="bg-surface-2 text-left text-label uppercase tracking-wide text-muted">
              <tr>
                <th className="px-4 py-2 font-medium">Item</th>
                <th className="px-4 py-2 font-medium">CPSEs</th>
                <th className="px-4 py-2 text-right font-medium">Records</th>
                <th className="px-4 py-2 text-right font-medium">Priority</th>
                <th className="px-4 py-2 font-medium">State</th>
              </tr>
            </thead>
            <tbody>
              {q.data.items.map((c) => (
                <tr key={c.id} className="border-t border-border hover:bg-surface-2">
                  <td className="px-4 py-2.5">
                    <Link to={`/clusters/${c.id}`} className="block max-w-xl">
                      <span className="text-label font-normal text-muted">
                        {CATEGORY_LABEL[c.category ?? ""] ?? c.category}
                        {c.critical && (
                          <span className="ml-2 inline-flex items-center gap-1 text-ne-fg">
                            <ShieldAlert size={12} aria-hidden="true" /> critical
                          </span>
                        )}
                        {c.flags > 0 && <span className="ml-2 text-ins-fg">{c.flags} flag(s)</span>}
                      </span>
                      <span className="block truncate font-mono text-mono text-primary hover:underline">
                        {c.sample_text}
                      </span>
                    </Link>
                  </td>
                  <td className="px-4 py-2.5">
                    <span className="flex flex-wrap gap-1">
                      {c.cpses.map((p) => (
                        <Chip key={p} tone="info">
                          {p}
                        </Chip>
                      ))}
                    </span>
                  </td>
                  <td className="tabular px-4 py-2.5 text-right">{c.members}</td>
                  <td className="tabular px-4 py-2.5 text-right text-muted">
                    {c.priority !== null ? formatCount(Math.round(c.priority)) : "–"}
                  </td>
                  <td className="px-4 py-2.5">
                    <Chip tone={STATE_TONE[c.state]}>{STATE_LABEL[c.state]}</Chip>
                    {c.made_by && (
                      <span className="ml-2 text-micro text-muted">by {c.made_by}</span>
                    )}
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
