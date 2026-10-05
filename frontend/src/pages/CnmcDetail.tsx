import { useMutation, useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { CATEGORY_LABEL } from "../api/batches";
import { MIGRATION_LABEL, download, getCnmc } from "../api/registry";
import { ATTR_LABEL } from "../api/review";
import { CodeChip } from "../components/review/CodeChip";
import { Chip } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { ProblemAlert } from "../components/ui/Form";
import { PageHeader } from "../components/ui/PageHeader";
import { SkeletonRows } from "../components/ui/States";
import { formatCount, formatDateTime } from "../lib/format";

const ACTION_WORDS: Record<string, string> = {
  REVIEW_PROPOSED: "Proposed",
  REVIEW_CONFIRMED: "Confirmed",
  REVIEW_OVERTURNED: "Overturned",
  CONSENT_REQUESTED: "Consent requested",
  CONSENT_GIVEN: "Consented for their CPSE",
  CONSENT_DECLINED: "Declined for their CPSE",
  CNMC_ISSUED: "National code issued",
};

/** S8b National code detail (App Flow 5.8): specification, descriptions, class, every legacy
 * code mapped to it with UoM and migration action, and its history from the audit log. */
export function CnmcDetail() {
  const { cnmc = "" } = useParams();
  const q = useQuery({ queryKey: ["cnmc", cnmc], queryFn: () => getCnmc(cnmc) });
  const dl = useMutation({
    mutationFn: () =>
      download(`/exports/crosswalk?format=csv&cnmc=${cnmc}`, `specid_crosswalk_${cnmc}.csv`),
  });
  const header = (
    <PageHeader
      title="National code"
      purpose="One code for this item across CPSEs, with the codes each CPSE used before."
      action={
        <Button variant="secondary" icon={Download} busy={dl.isPending} onClick={() => dl.mutate()}>
          Download crosswalk
        </Button>
      }
    />
  );
  if (q.isPending || q.error)
    return (
      <section className="max-w-6xl">
        {header}
        {q.error ? <ProblemAlert error={q.error} /> : <SkeletonRows rows={6} />}
      </section>
    );
  const n = q.data;
  const spec = Object.entries(n.canonical_spec).filter(([, v]) => v !== null && v !== undefined);
  return (
    <section className="max-w-6xl">
      {header}
      <ProblemAlert error={dl.error} />
      <div className="mb-5 rounded-lg border border-border bg-surface p-5 shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          <CodeChip code={n.cnmc} link={false} big />
          <Chip tone={n.status === "ACTIVE" ? "good" : "neutral"}>{n.status.toLowerCase()}</Chip>
          <Chip tone="info">{CATEGORY_LABEL[n.category] ?? n.category}</Chip>
        </div>
        <p className="mt-3 font-mono text-h3 text-text">{n.short_desc_40}</p>
        <p className="mt-1 text-body text-muted">{n.long_desc}</p>
        <p className="mt-3 text-micro text-muted">
          Issued {formatDateTime(n.issued_at)}
          {n.issued_by ? ` by ${n.issued_by}` : ""} · class {n.class_path.join(" › ")} · base unit{" "}
          {n.base_uom ?? "—"} · UNSPSC {n.unspsc ?? "not mapped"} · HSN {n.hsn ?? "not mapped"}
          {n.source_cluster && (
            <>
              {" · "}
              <Link className="text-primary hover:underline" to={`/clusters/${n.source_cluster}`}>
                review record
              </Link>
            </>
          )}
        </p>
      </div>
      <div className="grid gap-5 lg:grid-cols-[20rem_1fr]">
        <Card title="Specification">
          <dl className="space-y-1.5">
            {spec.map(([k, v]) => (
              <div key={k} className="flex justify-between gap-3 text-body">
                <dt className="text-muted">{ATTR_LABEL[k] ?? k}</dt>
                <dd className="font-mono text-mono text-text">{String(v)}</dd>
              </div>
            ))}
          </dl>
        </Card>
        <Card
          title="Legacy codes mapped here"
          hint="Migration actions appear once a CPSE downloads its migration pack."
          padded={false}
        >
          <table className="w-full text-table">
            <thead className="text-left text-label uppercase tracking-wide text-muted">
              <tr>
                <th className="px-4 py-2 font-medium">CPSE</th>
                <th className="px-4 py-2 font-medium">Legacy code</th>
                <th className="px-4 py-2 font-medium">Unit</th>
                <th className="px-4 py-2 text-right font-medium">Stock</th>
                <th className="px-4 py-2 font-medium">Action</th>
              </tr>
            </thead>
            <tbody>
              {n.crosswalk.map((x) => (
                <tr key={`${x.cpse}-${x.legacy_code}`} className="border-t border-border align-top">
                  <td className="px-4 py-2">
                    <Chip tone="info">{x.cpse}</Chip>
                  </td>
                  <td className="px-4 py-2">
                    <span className="block font-mono text-mono">{x.legacy_code}</span>
                    <span className="block font-mono text-micro text-muted">{x.short_text}</span>
                  </td>
                  <td className="px-4 py-2 font-mono text-mono">
                    {x.uom ?? "—"}
                    {x.uom_factor === null && x.uom && (
                      <span className="block text-micro text-ins-fg">factor needed</span>
                    )}
                  </td>
                  <td className="tabular px-4 py-2 text-right">
                    {x.stock_qty !== null ? formatCount(x.stock_qty) : "—"}
                  </td>
                  <td className="px-4 py-2 text-muted">
                    {x.migration_action ? MIGRATION_LABEL[x.migration_action] : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
      <Card title="History" hint="From the tamper-evident audit log." className="mt-5">
        <ol className="relative space-y-3 border-l border-border pl-4">
          {n.history.map((h, i) => (
            <li key={i} className="text-body">
              <span
                className="absolute -left-1.5 mt-1.5 h-3 w-3 rounded-full border-2 border-surface bg-primary"
                aria-hidden="true"
              />
              <span className="font-medium">
                {ACTION_WORDS[h.action] ?? h.action.toLowerCase().replaceAll("_", " ")}
              </span>
              {h.actor && <span className="text-muted"> by {h.actor}</span>}
              <span className="block text-micro text-muted">{formatDateTime(h.ts)}</span>
            </li>
          ))}
        </ol>
      </Card>
    </section>
  );
}
