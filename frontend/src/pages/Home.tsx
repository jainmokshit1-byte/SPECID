import { useQuery } from "@tanstack/react-query";
import { ArrowRightLeft, BadgeCheck, Boxes, Database, IndianRupee, Network } from "lucide-react";
import { Link } from "react-router-dom";
import { Bar, BarChart, ResponsiveContainer, Tooltip as ChartTip, XAxis, YAxis } from "recharts";
import { CATEGORY_LABEL, listBatches } from "../api/batches";
import { type Dashboard, getDashboard } from "../api/insights";
import { STATE_LABEL, type TaskState } from "../api/review";
import { listRuns } from "../api/runs";
import { useUser } from "../auth/useAuth";
import { Chip } from "../components/ui/Badge";
import { BuiltLink } from "../components/ui/BuiltLink";
import { Card } from "../components/ui/Card";
import { HealthRing } from "../components/ui/HealthRing";
import { NextStepCard } from "../components/ui/NextStepCard";
import { PageHeader } from "../components/ui/PageHeader";
import { StatTile } from "../components/ui/StatTile";
import { useRun } from "../hooks/useRun";
import { formatCount, formatDateTime, formatInr } from "../lib/format";

const FIRST_RUN_STEPS = ["Upload files", "Check quality", "Run matching", "Review", "Issue codes"];

/** Where the first-run checklist stands, from data only (DEC-16: never an invented number). */
// eslint-disable-next-line react-refresh/only-export-components -- pure helper, tested directly
export function firstRunStep(ingestedCpses: number, doneRuns: number): number {
  if (doneRuns > 0) return 3;
  if (ingestedCpses >= 2) return 2;
  if (ingestedCpses === 1) return 1;
  return 0;
}

const NEXT: { sentence: string; to: string; label: string }[] = [
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

/** S0 Home (UI/UX brief 7.1, App Flow 3.3, PRD FR-1201, FR-1203): the next step, then the
 * dashboard of the selected run. Every figure comes from that run (DEC-16). */
export function Home() {
  const { role } = useUser();
  const worker = role !== "AUDITOR";
  const batches = useQuery({ queryKey: ["batches"], queryFn: listBatches, enabled: worker });
  const runs = useQuery({ queryKey: ["runs"], queryFn: listRuns });
  const { run } = useRun();
  const dash = useQuery({
    queryKey: ["dashboard", run],
    queryFn: () => getDashboard(run),
    enabled: !!run,
  });
  const cpses = new Set(
    (batches.data ?? []).filter((b) => b.status === "INGESTED").map((b) => b.cpse_code),
  ).size;
  const step = firstRunStep(cpses, (runs.data ?? []).filter((r) => r.status === "DONE").length);
  const next = NEXT[step]!;
  return (
    <section className="max-w-7xl">
      <PageHeader
        title="Home"
        purpose="What to do next, and what the latest matching run found across CPSEs."
      />
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
      {dash.data && !dash.data.empty && <DashboardView d={dash.data} />}
    </section>
  );
}

function DashboardView({ d }: { d: Dashboard }) {
  const m = d.money;
  const backlogOrder: TaskState[] = ["OPEN", "MADE", "AWAITING_CONSENT", "DONE"];
  const chart = d.by_category.map((c) => ({
    name: CATEGORY_LABEL[c.category] ?? c.category,
    groups: c.groups,
  }));
  return (
    <div className="mt-6 space-y-5">
      <p className="text-label font-normal text-muted">
        Run <span className="font-mono">{String(d.run_id).slice(0, 8)}</span> ·{" "}
        {formatCount(d.records)} records · computed {formatDateTime(d.computed_at)}
        {d.is_synthetic && " · synthetic data"}
      </p>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <StatTile
          icon={Database}
          label="Records"
          value={formatCount(d.records)}
          sub={`${d.per_cpse.length} CPSEs`}
        />
        <StatTile
          icon={Network}
          label="Same item across CPSEs"
          value={formatCount(d.groups.cross_cpse)}
          sub={`${formatCount(d.groups.three_plus)} held by 3 CPSEs`}
        />
        <StatTile
          icon={BadgeCheck}
          label="National codes"
          value={formatCount(d.issued)}
          sub="issued from this run"
          accent="text-eq-fg"
        />
        <StatTile
          icon={IndianRupee}
          label="Price gap"
          value={formatInr(m.total_price_gap)}
          sub={`${formatCount(m.groups_with_prices)} items bought by ≥ 2 CPSEs`}
          accent="text-ins-fg"
        />
        <StatTile
          icon={ArrowRightLeft}
          label="Idle stock to share"
          value={formatInr(m.stock_sharing.total_value)}
          sub={`${formatCount(m.stock_sharing.suggestions)} transfers before buying`}
          accent="text-auto-fg"
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.3fr_1fr]">
        <Card
          title="Per CPSE"
          hint="Records, data health, and duplicates found inside each CPSE's own master."
          padded={false}
        >
          <table className="w-full text-table">
            <thead className="text-left text-label uppercase tracking-wide text-muted">
              <tr>
                <th className="px-4 py-2 font-medium">CPSE</th>
                <th className="px-4 py-2 text-right font-medium">Records</th>
                <th className="px-4 py-2 text-right font-medium">Annual spend</th>
                <th className="px-4 py-2 text-right font-medium">Internal duplicates</th>
                <th className="px-4 py-2 text-right font-medium">Health</th>
              </tr>
            </thead>
            <tbody>
              {d.per_cpse.map((c) => (
                <tr key={c.cpse} className="border-t border-border">
                  <td className="px-4 py-2">
                    <Chip tone="info">{c.cpse}</Chip>
                  </td>
                  <td className="tabular px-4 py-2 text-right">{formatCount(c.records)}</td>
                  <td className="tabular px-4 py-2 text-right">{formatInr(c.annual_spend)}</td>
                  <td className="tabular px-4 py-2 text-right">
                    {formatCount(c.internal_duplicates)}
                  </td>
                  <td className="px-4 py-1 text-right">
                    <span className="inline-block align-middle">
                      <HealthRing score={c.health_score} size={44} label={`${c.cpse} health`} />
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
        <Card title="Groups by category" hint="Same-item groups found in this run.">
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chart} layout="vertical" margin={{ left: 8, right: 16 }}>
                <XAxis type="number" hide />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={80}
                  tick={{ fill: "var(--text-muted)", fontSize: 12 }}
                  axisLine={false}
                  tickLine={false}
                />
                <ChartTip
                  cursor={{ fill: "var(--surface-2)" }}
                  contentStyle={{
                    background: "var(--surface)",
                    border: "1px solid var(--border)",
                    borderRadius: 6,
                  }}
                />
                <Bar dataKey="groups" fill="var(--primary)" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <table className="sr-only">
            <tbody>
              {chart.map((c) => (
                <tr key={c.name}>
                  <td>{c.name}</td>
                  <td>{c.groups}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <Card
          title="Same item, different prices"
          hint="What each CPSE pays for one item over the last 12 months. The gap is what buying at the lowest CPSE price would close."
          actions={
            <Link to="/pooling" className="text-label text-primary hover:underline">
              All
            </Link>
          }
        >
          <ul className="space-y-3">
            {m.top_price_gaps.slice(0, 4).map((g) => {
              const max = Math.max(...g.by_cpse.map((b) => b.avg_price));
              return (
                <li key={g.cluster_id}>
                  <div className="flex items-baseline justify-between gap-3">
                    <Link
                      to={`/clusters/${g.cluster_id}`}
                      className="truncate font-mono text-micro text-primary hover:underline"
                    >
                      {g.sample_text}
                    </Link>
                    <span className="tabular shrink-0 text-label text-ins-fg">
                      gap {formatInr(g.price_gap)}
                    </span>
                  </div>
                  <div className="mt-1 space-y-0.5">
                    {g.by_cpse.map((b) => (
                      <div
                        key={b.cpse}
                        className="grid grid-cols-[4.5rem_1fr_6rem] items-center gap-2 text-micro"
                      >
                        <span className="text-muted">{b.cpse}</span>
                        <span className="h-1.5 overflow-hidden rounded-full bg-surface-2">
                          <span
                            className={`block h-full rounded-full ${
                              b.avg_price === g.lowest_price ? "bg-eq-fg" : "bg-ins-fg"
                            }`}
                            style={{ width: `${(b.avg_price / max) * 100}%` }}
                          />
                        </span>
                        <span className="tabular text-right">{formatInr(b.avg_price)}</span>
                      </div>
                    ))}
                  </div>
                </li>
              );
            })}
          </ul>
          <p className="mt-3 text-micro text-muted">{m.note}</p>
        </Card>
        <Card
          title="Transfer before buying"
          hint="Stock one CPSE has not used in 12 months, for an item another CPSE keeps buying."
        >
          {m.stock_sharing.top.length === 0 ? (
            <p className="text-body text-muted">
              No idle stock matches another CPSE's demand in this run.
            </p>
          ) : (
            <ul className="space-y-2">
              {m.stock_sharing.top.slice(0, 5).map((s) => (
                <li
                  key={`${s.cluster_id}-${s.holder}`}
                  className="rounded-lg bg-surface-2 px-3 py-2"
                >
                  <span className="block truncate font-mono text-micro text-text">
                    {s.sample_text}
                  </span>
                  <span className="mt-1 flex flex-wrap items-center gap-1.5 text-label font-normal text-muted">
                    <Chip tone="info">{s.holder}</Chip> holds {formatCount(s.idle_stock)} idle
                    <ArrowRightLeft size={13} aria-hidden="true" />
                    <Chip tone="info">{s.buyer}</Chip> buys {formatCount(s.buyer_annual_qty)} a year
                    ·<span className="text-text">{formatInr(s.value_at_buyer_price)}</span>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_2fr]">
        <Card title="Review backlog" hint="Groups by step in the approval flow.">
          <ul className="space-y-1.5">
            {backlogOrder.map((s) => (
              <li key={s} className="flex justify-between text-body">
                <span className="text-muted">{STATE_LABEL[s]}</span>
                <span className="tabular">{formatCount(d.backlog[s] ?? 0)}</span>
              </li>
            ))}
          </ul>
        </Card>
        <Card
          title="Top groups by priority"
          hint="Spend × open questions: review these first."
          padded={false}
        >
          <ul>
            {d.top_groups.slice(0, 6).map((g) => (
              <li
                key={g.id}
                className="flex items-center gap-3 border-t border-border px-4 py-2 first:border-t-0"
              >
                <Boxes size={16} className="shrink-0 text-muted" aria-hidden="true" />
                <Link
                  to={`/clusters/${g.id}`}
                  className="min-w-0 flex-1 truncate font-mono text-micro text-primary hover:underline"
                >
                  {g.sample_text}
                </Link>
                <span className="hidden gap-1 sm:flex">
                  {g.cpses.map((c) => (
                    <Chip key={c} tone="info">
                      {c}
                    </Chip>
                  ))}
                </span>
                <span className="tabular w-24 text-right text-label">
                  {formatInr(g.annual_spend)}
                </span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}
