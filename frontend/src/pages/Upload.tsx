import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  CircleAlert,
  CircleCheck,
  FileUp,
  Info,
  RotateCcw,
  Sparkles,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  type Batch,
  type BatchUploaded,
  FIELD_LABEL,
  FIELDS,
  type Field,
  ingestBatch,
  listBatches,
  saveMapping,
  uploadBatch,
  uploadProcurement,
} from "../api/batches";
import { apiGet } from "../api/client";
import { useUser } from "../auth/useAuth";
import { Chip, StatusBadge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Dropzone } from "../components/ui/Dropzone";
import { INPUT, ProblemAlert } from "../components/ui/Form";
import { PageHeader } from "../components/ui/PageHeader";
import { EmptyState, SkeletonRows } from "../components/ui/States";
import { formatCount, formatDateTime } from "../lib/format";

const NOT_USED = "";
const REQUIRED_TEXT: Field[] = ["short_text", "long_text"];

/** Problems that block "Save & ingest", in plain words (App Flow 5.2 step 4). */
// eslint-disable-next-line react-refresh/only-export-components -- pure helper, tested directly
export function mappingProblems(mapping: Record<string, string>): string[] {
  const targets = Object.values(mapping).filter(Boolean);
  const out: string[] = [];
  if (!targets.includes("legacy_code")) out.push("Choose the column that holds the material code.");
  if (!targets.some((t) => REQUIRED_TEXT.includes(t as Field)))
    out.push("Choose a column with the short or long description.");
  const dup = targets.filter((t, i) => targets.indexOf(t) !== i);
  for (const t of new Set(dup))
    out.push(`Two columns are set to “${FIELD_LABEL[t as Field] ?? t}”.`);
  return out;
}

/** S2 Upload & mapping (App Flow 5.2, UI/UX brief 7.8): (1) CPSE, synthetic flag, file;
 * (2) mapping table with suggestions and samples; sticky "Save & ingest". */
export function Upload() {
  const [uploaded, setUploaded] = useState<BatchUploaded | null>(null);
  return (
    <section className="max-w-6xl">
      <PageHeader
        title="Upload & mapping"
        purpose="Add a CPSE's material master file. Columns are matched automatically; check them, then ingest."
      />
      {uploaded ? (
        <MappingStep batch={uploaded} onRestart={() => setUploaded(null)} />
      ) : (
        <FileStep onUploaded={setUploaded} />
      )}
      <RecentUploads />
    </section>
  );
}

// ---------------------------------------------------------------- step 1
function FileStep({ onUploaded }: { onUploaded: (b: BatchUploaded) => void }) {
  const user = useUser();
  const [file, setFile] = useState<File | null>(null);
  const [cpse, setCpse] = useState("");
  const [synthetic, setSynthetic] = useState(true);
  const admin = user.role === "ADMIN";
  const cpses = useQuery({
    queryKey: ["cpse-codes"],
    queryFn: async () => (await apiGet<{ cpses: { code: string }[] }>("/users")).cpses,
    enabled: admin,
  });
  const upload = useMutation({
    mutationFn: () => uploadBatch(file!, { cpse: admin ? cpse : undefined, synthetic }),
    onSuccess: onUploaded,
  });
  const ready = !!file && (!admin || !!cpse);

  return (
    <Card
      title="1 · Choose the file"
      hint="CSV or Excel, one CPSE per file. SAP extracts are recognised."
    >
      <div className="grid gap-5 md:grid-cols-[16rem_1fr]">
        <div className="space-y-4">
          <div>
            <span className="mb-1 block text-label text-text">CPSE</span>
            {admin ? (
              <select
                aria-label="CPSE"
                className={INPUT}
                value={cpse}
                onChange={(e) => setCpse(e.target.value)}
              >
                <option value="">Choose a CPSE…</option>
                {cpses.data?.map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.code}
                  </option>
                ))}
              </select>
            ) : (
              <p className="flex h-8 items-center rounded border border-border bg-surface-2 px-2 font-mono text-mono">
                {user.cpse_code ?? "No CPSE on your account"}
              </p>
            )}
            {!admin && <p className="mt-1 text-micro text-muted">You upload for your own CPSE.</p>}
          </div>
          <label className="flex items-start gap-2 text-body">
            <input
              type="checkbox"
              className="mt-1"
              checked={synthetic}
              onChange={(e) => setSynthetic(e.target.checked)}
            />
            <span>
              Synthetic data
              <span className="block text-micro text-muted">
                Shown with the SYNTHETIC DATA badge everywhere.
              </span>
            </span>
          </label>
        </div>
        <div>
          <Dropzone file={file} onFile={setFile} />
          <ProblemAlert error={upload.error} />
          <div className="mt-4 flex justify-end">
            <Button
              icon={FileUp}
              busy={upload.isPending}
              disabled={!ready}
              title={!ready ? "Choose a file (and a CPSE) first" : undefined}
              onClick={() => upload.mutate()}
            >
              Upload and read columns
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------- step 2
function MappingStep({ batch, onRestart }: { batch: BatchUploaded; onRestart: () => void }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [mapping, setMapping] = useState<Record<string, string>>(() =>
    Object.fromEntries(batch.columns.map((c) => [c, batch.suggested_mapping[c] ?? NOT_USED])),
  );
  const [procurement, setProcurement] = useState<File | null>(null);
  const problems = useMemo(() => mappingProblems(mapping), [mapping]);
  const ingest = useMutation({
    mutationFn: async () => {
      const clean = Object.fromEntries(Object.entries(mapping).filter(([, t]) => t));
      await saveMapping(batch.id, clean);
      const done = await ingestBatch(batch.id);
      if (procurement) await uploadProcurement(batch.id, procurement);
      return done;
    },
    onSuccess: (b) => {
      void queryClient.invalidateQueries({ queryKey: ["batches"] });
      navigate(`/batches/${b.id}/quality`);
    },
  });

  if (batch.already_ingested)
    return (
      <Card>
        <div className="flex items-start gap-3">
          <CircleCheck className="mt-0.5 shrink-0 text-eq-fg" size={20} aria-hidden="true" />
          <div className="flex-1">
            <p className="text-h3">This exact file was already ingested for {batch.cpse_code}.</p>
            <p className="text-body text-muted">
              Nothing new was added. Open its quality report instead.
            </p>
          </div>
          <Link to={`/batches/${batch.id}/quality`} className="text-body font-medium text-primary">
            Open quality report
          </Link>
          <Button variant="ghost" icon={RotateCcw} onClick={onRestart}>
            Another file
          </Button>
        </div>
      </Card>
    );

  const sample = (col: string) =>
    batch.sample_rows
      .map((r) => r[col] ?? "")
      .filter(Boolean)
      .slice(0, 3);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 text-body">
        <Chip tone="info">{batch.cpse_code}</Chip>
        <span className="font-mono text-mono">{batch.filename}</span>
        <span className="text-muted">· {formatCount(batch.row_count ?? 0)} rows</span>
        {batch.encoding && batch.encoding !== "utf-8" && batch.encoding !== "xlsx" && (
          <Chip tone="warn" icon={Info}>
            Read as {batch.encoding}
          </Chip>
        )}
        <Button variant="ghost" icon={RotateCcw} className="ml-auto" onClick={onRestart}>
          Choose another file
        </Button>
      </div>
      {batch.preset === "SAP" && (
        <p className="flex items-center gap-2 rounded-lg border border-auto-fg bg-auto-bg px-3 py-2 text-body text-auto-fg">
          <Sparkles size={16} aria-hidden="true" />
          SAP material-master columns detected: the SAP preset filled the mapping.
        </p>
      )}
      <Card
        title="2 · Check the columns"
        hint="Each column of the file and the SpecID field it fills. Columns set to “Not used” are kept only in the raw record."
        padded={false}
      >
        <div className="overflow-x-auto">
          <table className="w-full text-table">
            <thead className="bg-surface-2 text-left text-label uppercase tracking-wide text-muted">
              <tr>
                <th className="px-4 py-2 font-medium">Column in the file</th>
                <th className="px-4 py-2 font-medium">Sample values</th>
                <th className="w-64 px-4 py-2 font-medium">SpecID field</th>
              </tr>
            </thead>
            <tbody>
              {batch.columns.map((col) => {
                const target = mapping[col] ?? NOT_USED;
                const suggested = batch.suggested_mapping[col];
                return (
                  <tr key={col} className="border-t border-border align-top">
                    <td className="px-4 py-2.5 font-mono text-mono text-text">{col}</td>
                    <td className="px-4 py-2.5">
                      <div className="flex max-w-xl flex-col gap-0.5">
                        {sample(col).map((v, i) => (
                          <span
                            key={i}
                            className="truncate font-mono text-micro text-muted"
                            title={v}
                          >
                            {v}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-2">
                      <select
                        aria-label={`Field for ${col}`}
                        value={target}
                        onChange={(e) => setMapping((m) => ({ ...m, [col]: e.target.value }))}
                        className={`${INPUT} ${target ? "" : "text-muted"}`}
                      >
                        <option value={NOT_USED}>Not used</option>
                        {FIELDS.map((f) => (
                          <option key={f} value={f}>
                            {FIELD_LABEL[f]}
                            {f === "legacy_code" ? " *" : ""}
                          </option>
                        ))}
                      </select>
                      {suggested && suggested === target && (
                        <span className="mt-1 inline-flex items-center gap-1 text-micro text-eq-fg">
                          <CircleCheck size={12} aria-hidden="true" /> suggested
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
      <Card
        title="Purchase history (optional)"
        hint="legacy_code, po_date, qty, unit_price, vendor… Vendors are hashed; prices stay inside your CPSE. You can also add it later."
      >
        <Dropzone
          compact
          file={procurement}
          onFile={setProcurement}
          label="Drop the purchase-history file"
        />
      </Card>

      <div className="sticky bottom-0 z-topbar -mx-6 flex items-center gap-3 border-t border-border bg-surface px-6 py-3 shadow-[0_-4px_12px_rgba(0,0,0,0.06)]">
        {problems.length > 0 ? (
          <p className="flex items-center gap-2 text-body text-ins-fg">
            <CircleAlert size={16} aria-hidden="true" />
            {problems[0]}
          </p>
        ) : (
          <p className="flex items-center gap-2 text-body text-eq-fg">
            <CircleCheck size={16} aria-hidden="true" />
            Mapping complete: {Object.values(mapping).filter(Boolean).length} columns used.
          </p>
        )}
        <div className="ml-auto flex items-center gap-3">
          <ProblemAlert error={ingest.error} />
          <Button
            icon={ArrowRight}
            busy={ingest.isPending}
            disabled={problems.length > 0}
            onClick={() => ingest.mutate()}
          >
            Save & ingest
          </Button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- recent uploads
function RecentUploads() {
  const batches = useQuery({ queryKey: ["batches"], queryFn: listBatches });
  return (
    <div className="mt-8">
      <h2 className="mb-3 text-h3">Recent uploads</h2>
      {batches.isPending ? (
        <SkeletonRows rows={3} />
      ) : batches.error ? (
        <ProblemAlert error={batches.error} />
      ) : batches.data.length === 0 ? (
        <EmptyState
          icon={FileUp}
          title="No files yet"
          text="Upload two or more CPSE files to start matching."
        />
      ) : (
        <BatchTable batches={batches.data} />
      )}
    </div>
  );
}

export function BatchTable({ batches }: { batches: Batch[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-border bg-surface">
      <table className="w-full text-table">
        <thead className="bg-surface-2 text-left text-label uppercase tracking-wide text-muted">
          <tr>
            <th className="px-4 py-2 font-medium">CPSE</th>
            <th className="px-4 py-2 font-medium">File</th>
            <th className="px-4 py-2 font-medium">Status</th>
            <th className="px-4 py-2 text-right font-medium">Records</th>
            <th className="px-4 py-2 text-right font-medium">Health</th>
            <th className="px-4 py-2 font-medium">Uploaded</th>
          </tr>
        </thead>
        <tbody>
          {batches.map((b) => (
            <tr key={b.id} className="border-t border-border hover:bg-surface-2">
              <td className="px-4 py-2.5">
                <Chip tone="info">{b.cpse_code}</Chip>
              </td>
              <td className="px-4 py-2.5 font-mono text-mono">
                {b.status === "INGESTED" ? (
                  <Link className="text-primary hover:underline" to={`/batches/${b.id}/quality`}>
                    {b.filename}
                  </Link>
                ) : (
                  b.filename
                )}
                {b.is_synthetic && <span className="ml-2 text-micro text-muted">synthetic</span>}
              </td>
              <td className="px-4 py-2.5">
                <StatusBadge status={b.status} />
              </td>
              <td className="tabular px-4 py-2.5 text-right">
                {b.quality
                  ? formatCount(b.quality.rows)
                  : b.row_count
                    ? formatCount(b.row_count)
                    : "–"}
              </td>
              <td className="tabular px-4 py-2.5 text-right">{b.quality?.health_score ?? "–"}</td>
              <td className="px-4 py-2.5 text-muted">{formatDateTime(b.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
