import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CircleAlert,
  Copy,
  FileWarning,
  Files,
  Layers,
  Play,
  Receipt,
  Ruler,
  Upload as UploadIcon,
} from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  CATEGORY_LABEL,
  FIELD_LABEL,
  FIELDS,
  HEALTH_LABEL,
  getBatch,
  uploadProcurement,
} from "../api/batches";
import { Chip, StatusBadge } from "../components/ui/Badge";
import { BuiltLink } from "../components/ui/BuiltLink";
import { Button, buttonClass } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Dropzone } from "../components/ui/Dropzone";
import { ProblemAlert } from "../components/ui/Form";
import { HealthRing } from "../components/ui/HealthRing";
import { Meter, pct } from "../components/ui/Meter";
import { PageHeader } from "../components/ui/PageHeader";
import { StatTile } from "../components/ui/StatTile";
import { SkeletonRows } from "../components/ui/States";
import { formatCount, formatDateTime } from "../lib/format";

/** S3 Data-quality report (App Flow 5.3, PRD FR-103): health score with its parts, fields
 * filled, categories recognised and key attributes read, then the next step. */
export function Quality() {
  const { batchId = "" } = useParams();
  const batch = useQuery({ queryKey: ["batch", batchId], queryFn: () => getBatch(batchId) });

  const header = (action?: JSX.Element) => (
    <PageHeader
      title="Data-quality report"
      purpose="How readable this file is before matching: what is filled, what is recognised, what will be undecidable."
      action={action}
    />
  );
  if (batch.isPending || batch.error)
    return (
      <section className="max-w-6xl">
        {header()}
        {batch.error ? <ProblemAlert error={batch.error} /> : <SkeletonRows rows={6} />}
      </section>
    );
  const b = batch.data;
  const q = b.quality;

  return (
    <section className="max-w-6xl">
      {header(
        <BuiltLink
          to={`/runs/new?batches=${b.id}`}
          pattern="/runs/new"
          label="Start a run with this batch"
          icon={Play}
        />,
      )}
      <div className="mb-5 flex flex-wrap items-center gap-2 text-body">
        <Chip tone="info">{b.cpse_code}</Chip>
        <span className="font-mono text-mono">{b.filename}</span>
        <StatusBadge status={b.status} />
        <span className="text-muted">· uploaded {formatDateTime(b.created_at)}</span>
        <Link to="/upload" className="ml-auto text-body text-primary hover:underline">
          Upload another CPSE
        </Link>
      </div>

      {!q ? (
        <Card>
          <p className="text-body text-muted">
            This file has not been ingested yet. Finish the mapping on the upload page.
          </p>
        </Card>
      ) : (
        <div className="space-y-5">
          <div className="grid gap-5 lg:grid-cols-[22rem_1fr]">
            <Card title="Health score" hint="Mean of the five parts below, 0 to 100.">
              <div className="flex items-center gap-5">
                <HealthRing score={q.health_score} />
                <div className="min-w-0 flex-1">
                  {Object.entries(HEALTH_LABEL).map(([k, label]) => (
                    <div key={k} className="py-1">
                      <div className="flex justify-between text-label font-normal">
                        <span className="text-muted">{label}</span>
                        <span className="tabular text-text">
                          {pct(q.health_components[k] ?? 0, 0)}
                        </span>
                      </div>
                      <span className="mt-1 block h-1.5 overflow-hidden rounded-full bg-surface-2">
                        <span
                          className={`block h-full rounded-full transition-[width] duration-700 ${
                            (q.health_components[k] ?? 0) >= 0.9
                              ? "bg-eq-fg"
                              : (q.health_components[k] ?? 0) >= 0.7
                                ? "bg-ins-fg"
                                : "bg-ne-fg"
                          }`}
                          style={{ width: `${(q.health_components[k] ?? 0) * 100}%` }}
                        />
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
              <StatTile
                icon={Files}
                label="Records"
                value={formatCount(q.rows)}
                sub="ingested from this file"
              />
              <StatTile
                icon={FileWarning}
                label="Rows left out"
                value={formatCount(q.rejected_rows)}
                sub="no code or no description"
              />
              <StatTile
                icon={Copy}
                label="Repeated codes"
                value={formatCount(q.duplicate_legacy_codes)}
                sub="same material code twice; first kept"
              />
              <StatTile
                icon={Ruler}
                label="Unclear units"
                value={formatCount(q.uom_ambiguous + q.uom_unknown)}
                sub={`${formatCount(q.uom_ambiguous)} ambiguous (e.g. MT) · ${formatCount(q.uom_unknown)} unknown`}
              />
              <StatTile
                icon={CircleAlert}
                label="Short text > 40"
                value={formatCount(q.short_text_over_40)}
                sub="longer than an SAP short text"
              />
              <StatTile
                icon={Layers}
                label="Unchanged, skipped"
                value={formatCount(q.skipped_unchanged)}
                sub="already ingested earlier"
              />
            </div>
          </div>

          <div className="grid gap-5 lg:grid-cols-2">
            <Card
              title="Categories"
              hint="Share of records per category, and how many have every key attribute readable."
            >
              <table className="w-full text-table">
                <thead className="text-left text-label uppercase tracking-wide text-muted">
                  <tr>
                    <th className="pb-2 font-medium">Category</th>
                    <th className="pb-2 text-right font-medium">Share</th>
                    <th className="w-1/2 pb-2 pl-4 font-medium">All key attributes read</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(q.category_share)
                    .sort((a, b) => b[1] - a[1])
                    .map(([cat, share]) => {
                      const parsed = q.core_parse_rate[cat];
                      return (
                        <tr key={cat} className="border-t border-border">
                          <td className="py-2">
                            {cat === "UNRECOGNISED" ? (
                              <span className="text-ins-fg">{CATEGORY_LABEL[cat]}</span>
                            ) : (
                              (CATEGORY_LABEL[cat] ?? cat)
                            )}
                          </td>
                          <td className="tabular py-2 text-right">{pct(share)}</td>
                          <td className="py-2 pl-4">
                            {parsed === undefined ? (
                              <span className="text-label text-muted">needs the AI classifier</span>
                            ) : (
                              <span className="flex items-center gap-2">
                                <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-2">
                                  <span
                                    className="block h-full rounded-full bg-primary transition-[width] duration-700"
                                    style={{ width: `${parsed * 100}%` }}
                                  />
                                </span>
                                <span className="tabular w-12 text-right text-muted">
                                  {pct(parsed, 0)}
                                </span>
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
            </Card>
            <Card
              title="Fields filled"
              hint="Share of records with a value, per field of the mapping."
            >
              {FIELDS.filter(
                (f) => (q.completeness[f] ?? 0) > 0 || f === "legacy_code" || f === "short_text",
              ).map((f) => (
                <Meter key={f} label={FIELD_LABEL[f]} value={q.completeness[f] ?? 0} />
              ))}
              {FIELDS.some((f) => (q.completeness[f] ?? 0) === 0) && (
                <p className="mt-2 text-micro text-muted">
                  Not in this file:{" "}
                  {FIELDS.filter((f) => (q.completeness[f] ?? 0) === 0)
                    .map((f) => FIELD_LABEL[f])
                    .join(", ")}
                </p>
              )}
            </Card>
          </div>

          <ProcurementCard batchId={b.id} />
        </div>
      )}
    </section>
  );
}

function ProcurementCard({ batchId }: { batchId: string }) {
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const upload = useMutation({
    mutationFn: () => uploadProcurement(batchId, file!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["batch", batchId] }),
  });
  return (
    <Card
      title="Purchase history"
      hint="Optional. Adds prices and quantities for the savings and demand views. Never used to decide identity."
      actions={<Receipt size={18} className="text-muted" aria-hidden="true" />}
    >
      <div className="grid items-start gap-4 md:grid-cols-[1fr_auto]">
        <Dropzone compact file={file} onFile={setFile} label="Drop the purchase-history file" />
        <Button
          icon={UploadIcon}
          disabled={!file}
          busy={upload.isPending}
          onClick={() => upload.mutate()}
        >
          Add purchase history
        </Button>
      </div>
      <ProblemAlert error={upload.error} />
      {upload.data && (
        <p
          role="status"
          className="mt-3 rounded border border-eq-fg bg-eq-bg px-3 py-2 text-body text-eq-fg"
        >
          {formatCount(upload.data.lines)} purchase lines added
          {upload.data.duplicates ? ` · ${formatCount(upload.data.duplicates)} already there` : ""}
          {upload.data.unmatched
            ? ` · ${formatCount(upload.data.unmatched)} with an unknown material code`
            : ""}
          {upload.data.invalid ? ` · ${formatCount(upload.data.invalid)} unreadable` : ""}.
        </p>
      )}
      <p className="mt-3 text-micro text-muted">
        Columns: legacy_code, po_date, qty, uom, unit_price, currency, vendor, plant. Next:{" "}
        <Link
          className={buttonClass("ghost", "h-auto px-0 text-micro text-primary")}
          to="/runs/new"
        >
          start a matching run
        </Link>
        .
      </p>
    </Card>
  );
}
