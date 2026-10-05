import { useQuery } from "@tanstack/react-query";
import { IndianRupee } from "lucide-react";
import { Link } from "react-router-dom";
import { getPooling } from "../api/insights";
import { Chip } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { ProblemAlert } from "../components/ui/Form";
import { PageHeader } from "../components/ui/PageHeader";
import { StatTile } from "../components/ui/StatTile";
import { EmptyState, SkeletonRows } from "../components/ui/States";
import { useRun } from "../hooks/useRun";
import { formatCount, formatInr } from "../lib/format";

/** S15 Savings & pooling (SF-10, FR-1203): items bought by several CPSEs at different prices,
 * and idle stock one CPSE could pass to another. Gaps on synthetic prices, not savings achieved. */
export function Pooling() {
  const { run } = useRun();
  const q = useQuery({
    queryKey: ["pooling", run],
    queryFn: () => getPooling(run),
    enabled: !!run,
  });
  return (
    <section className="max-w-6xl">
      <PageHeader
        title="Savings & pooling"
        purpose="The same item bought by several CPSEs at different prices, and stock one CPSE holds while another buys."
      />
      {!run ? (
        <EmptyState
          icon={IndianRupee}
          title="No run yet"
          text="Run matching and add purchase history first."
        />
      ) : q.isPending ? (
        <SkeletonRows rows={6} />
      ) : q.error ? (
        <ProblemAlert error={q.error} />
      ) : (
        <div className="space-y-5">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <StatTile
              label="Pooled annual spend"
              value={formatInr(q.data.pooled_annual_spend)}
              sub={`${formatCount(q.data.groups_with_prices)} items bought by ≥ 2 CPSEs`}
            />
            <StatTile
              label="Price gap"
              value={formatInr(q.data.total_price_gap)}
              sub="if every CPSE paid the lowest CPSE price"
              accent="text-ins-fg"
            />
            <StatTile
              label="Idle stock to share"
              value={formatInr(q.data.stock_sharing.total_value)}
              sub={`${formatCount(q.data.stock_sharing.suggestions)} transfers before buying`}
            />
          </div>
          <p className="text-micro text-muted">{q.data.note}</p>
          <Card title="Same item, different prices" padded={false}>
            <table className="w-full text-table">
              <thead className="bg-surface-2 text-left text-label uppercase tracking-wide text-muted">
                <tr>
                  <th className="px-4 py-2 font-medium">Item</th>
                  <th className="px-4 py-2 font-medium">Price per CPSE (last 12 months)</th>
                  <th className="px-4 py-2 text-right font-medium">Gap</th>
                </tr>
              </thead>
              <tbody>
                {q.data.top_price_gaps.map((g) => (
                  <tr key={g.cluster_id} className="border-t border-border align-top">
                    <td className="px-4 py-2">
                      <Link
                        to={`/clusters/${g.cluster_id}`}
                        className="font-mono text-micro text-primary hover:underline"
                      >
                        {g.sample_text}
                      </Link>
                      {g.cnmc && (
                        <span className="ml-2 font-mono text-micro text-eq-fg">{g.cnmc}</span>
                      )}
                    </td>
                    <td className="px-4 py-2">
                      <span className="flex flex-wrap gap-2">
                        {g.by_cpse.map((b) => (
                          <span key={b.cpse} className="inline-flex items-center gap-1 text-micro">
                            <Chip tone={b.avg_price === g.lowest_price ? "good" : "warn"}>
                              {b.cpse}
                            </Chip>
                            <span className="tabular">{formatInr(b.avg_price)}</span>
                            <span className="text-muted">× {formatCount(b.annual_qty)}</span>
                          </span>
                        ))}
                      </span>
                    </td>
                    <td className="tabular px-4 py-2 text-right text-ins-fg">
                      {formatInr(g.price_gap)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
          <Card title="Transfer before buying" padded={false}>
            <table className="w-full text-table">
              <thead className="bg-surface-2 text-left text-label uppercase tracking-wide text-muted">
                <tr>
                  <th className="px-4 py-2 font-medium">Item</th>
                  <th className="px-4 py-2 font-medium">Holds idle stock</th>
                  <th className="px-4 py-2 font-medium">Buys it</th>
                  <th className="px-4 py-2 text-right font-medium">Value</th>
                </tr>
              </thead>
              <tbody>
                {q.data.stock_sharing.top.map((s) => (
                  <tr key={`${s.cluster_id}-${s.holder}`} className="border-t border-border">
                    <td className="px-4 py-2 font-mono text-micro">{s.sample_text}</td>
                    <td className="px-4 py-2 text-micro">
                      <Chip tone="info">{s.holder}</Chip> {formatCount(s.idle_stock)} (
                      {s.holder_code})
                    </td>
                    <td className="px-4 py-2 text-micro">
                      <Chip tone="info">{s.buyer}</Chip> {formatCount(s.buyer_annual_qty)} / year
                    </td>
                    <td className="tabular px-4 py-2 text-right">
                      {formatInr(s.value_at_buyer_price)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </div>
      )}
    </section>
  );
}
