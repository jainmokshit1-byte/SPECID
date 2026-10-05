import { useQuery } from "@tanstack/react-query";
import { CircleSlash } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  Legend,
  ResponsiveContainer,
  Tooltip as ChartTip,
  XAxis,
  YAxis,
} from "recharts";
import { type LookalikeItem, getLookalikes } from "../api/insights";
import { ATTR_LABEL } from "../api/review";
import { Chip } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { ProblemAlert } from "../components/ui/Form";
import { PageHeader } from "../components/ui/PageHeader";
import { EmptyState, SkeletonRows } from "../components/ui/States";
import { useRun } from "../hooks/useRun";
import { formatCount } from "../lib/format";

/** S13 Look-alike Guard (App Flow 5.12, SF-1): pairs that text similarity would merge but the
 * specification separates, with the one attribute that differs; and the reverse (hidden twins). */
export function Lookalikes() {
  const { run } = useRun();
  const [kind, setKind] = useState<"vetoed" | "twins">("vetoed");
  const q = useQuery({
    queryKey: ["lookalikes", kind, run],
    queryFn: () => getLookalikes(kind, run),
    enabled: !!run,
  });
  const d = q.data;
  return (
    <section className="max-w-6xl">
      <PageHeader
        title="Look-alike Guard"
        purpose="Text says these are the same; the specification says no. A wrong merge here could put a CL150 valve where CL300 is needed."
      />
      <div role="tablist" className="mb-4 flex gap-1">
        {(
          [
            ["vetoed", "Look-alikes blocked"],
            ["twins", "Hidden twins"],
          ] as const
        ).map(([k, label]) => (
          <button
            key={k}
            role="tab"
            type="button"
            aria-selected={kind === k}
            onClick={() => setKind(k)}
            className={`rounded-full px-3 py-1 text-label ${kind === k ? "bg-primary text-on-primary" : "bg-surface-2 text-muted hover:text-text"}`}
          >
            {label}
          </button>
        ))}
      </div>
      {!run ? (
        <EmptyState
          icon={CircleSlash}
          title="No run yet"
          text="Run matching first; look-alikes come from a run."
        />
      ) : q.isPending ? (
        <SkeletonRows rows={6} />
      ) : q.error ? (
        <ProblemAlert error={q.error} />
      ) : (
        <div className="space-y-5">
          <div className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
            <Card
              title="Text similarity cannot tell them apart"
              hint="Every compared pair by text similarity. Different items (red) reach the same high similarity as same items (green)."
            >
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={d!.histogram.map((h) => ({
                      ...h,
                      bucket: `${Math.round(h.from * 100)}–${Math.round(h.to * 100)}%`,
                    }))}
                  >
                    <XAxis
                      dataKey="bucket"
                      tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                      width={48}
                    />
                    <ChartTip
                      contentStyle={{
                        background: "var(--surface)",
                        border: "1px solid var(--border)",
                        borderRadius: 6,
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Bar dataKey="same" name="Same item" stackId="a" fill="var(--eq-fg)" />
                    <Bar dataKey="unknown" name="Can't tell" stackId="a" fill="var(--ins-fg)" />
                    <Bar
                      dataKey="different"
                      name="Different (veto)"
                      stackId="a"
                      fill="var(--ne-fg)"
                      radius={[3, 3, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
            <Card
              title="What stopped the merges"
              hint="The deciding attribute of each blocked look-alike."
            >
              <p className="tabular text-display text-ne-fg">{formatCount(d!.total)}</p>
              <p className="mb-3 text-label font-normal text-muted">
                {kind === "vetoed"
                  ? `pairs at ≥ ${Math.round((d!.thresholds.lookalike_min_sim ?? 0.85) * 100)}% text similarity, blocked by the specification`
                  : `pairs at ≤ ${Math.round((d!.thresholds.hidden_twin_max_sim ?? 0.75) * 100)}% similarity, found to be the same item`}
              </p>
              {kind === "vetoed" &&
                byLabel(d!.decisive_attributes)
                  .slice(0, 6)
                  .map(([label, pairs]) => (
                    <div key={label} className="flex justify-between py-0.5 text-body">
                      <span>{label}</span>
                      <span className="tabular text-muted">{formatCount(pairs)}</span>
                    </div>
                  ))}
            </Card>
          </div>
          <Card title={kind === "vetoed" ? "Blocked look-alikes" : "Hidden twins"} padded={false}>
            {d!.items.length === 0 ? (
              <p className="p-4 text-body text-muted">No pairs above the threshold in this run.</p>
            ) : (
              <ul>
                {d!.items.slice(0, 60).map((i) => (
                  <Row key={i.pair_id} i={i} />
                ))}
              </ul>
            )}
          </Card>
        </div>
      )}
    </section>
  );
}

/** Attributes that share a label (valve, flange and fastener "Type") are counted together. */
function byLabel(attrs: { attr: string; pairs: number }[]): [string, number][] {
  const sums = new Map<string, number>();
  for (const a of attrs) {
    const label = ATTR_LABEL[a.attr] ?? a.attr;
    sums.set(label, (sums.get(label) ?? 0) + a.pairs);
  }
  return [...sums].sort((x, y) => y[1] - x[1]);
}

function Row({ i }: { i: LookalikeItem }) {
  const decisive = new Set(
    i.decisive.map((d) => String(d.a)).concat(i.decisive.map((d) => String(d.b))),
  );
  return (
    <li className="grid gap-3 border-t border-border px-4 py-3 first:border-t-0 md:grid-cols-[1fr_1fr_12rem]">
      {[i.a, i.b].map((s, k) => (
        <div key={k}>
          <span className="flex items-center gap-1.5">
            <Chip tone="info">{s.cpse}</Chip>
            <span className="font-mono text-micro text-muted">{s.legacy_code}</span>
          </span>
          <span className="mt-1 block font-mono text-micro text-text">{s.text}</span>
        </div>
      ))}
      <div className="text-label font-normal">
        <span className="tabular block text-muted">
          text {Math.round(i.text_sim * 100)}% similar
        </span>
        {i.decisive.map((d) => (
          <span key={d.attr} className="mt-1 block text-ne-fg">
            {ATTR_LABEL[d.attr] ?? d.attr}:{" "}
            <span className="font-mono font-semibold">{String(d.a)}</span> vs{" "}
            <span className="font-mono font-semibold">{String(d.b)}</span>
          </span>
        ))}
        {decisive.size === 0 && <span className="mt-1 block text-eq-fg">same specification</span>}
        <Link to={`/pairs/${i.pair_id}`} className="mt-1 block text-primary hover:underline">
          Evidence
        </Link>
      </div>
    </li>
  );
}
