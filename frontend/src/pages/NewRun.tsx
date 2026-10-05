import { useMutation, useQuery } from "@tanstack/react-query";
import { ChevronDown, CircleAlert, Play } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { type Batch, listBatches } from "../api/batches";
import { MODE_HINT, MODE_LABEL, type RunMode, startRun } from "../api/runs";
import { useUser } from "../auth/useAuth";
import { Chip } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { INPUT, ProblemAlert } from "../components/ui/Form";
import { PageHeader } from "../components/ui/PageHeader";
import { EmptyState, SkeletonRows } from "../components/ui/States";
import { formatCount, formatDateTime } from "../lib/format";

const MODES: RunMode[] = ["CROSS_CPSE", "WITHIN_CPSE", "BOTH"];

/** Default selection: the batches named in `?batches=`, else the newest ingested file per CPSE. */
// eslint-disable-next-line react-refresh/only-export-components -- pure helper, tested directly
export function defaultSelection(batches: Batch[], requested: string[]): string[] {
  const ingested = batches.filter((b) => b.status === "INGESTED");
  const named = requested.filter((id) => ingested.some((b) => b.id === id));
  if (named.length) {
    // add the newest file of every other CPSE, so a cross-CPSE run is one click away
    const have = new Set(ingested.filter((b) => named.includes(b.id)).map((b) => b.cpse_code));
    const extra = latestPerCpse(ingested).filter((b) => !have.has(b.cpse_code));
    return [...named, ...extra.map((b) => b.id)];
  }
  return latestPerCpse(ingested).map((b) => b.id);
}

function latestPerCpse(batches: Batch[]): Batch[] {
  const by = new Map<string, Batch>();
  for (const b of [...batches].sort((x, y) => y.created_at.localeCompare(x.created_at)))
    if (!by.has(b.cpse_code)) by.set(b.cpse_code, b);
  return [...by.values()].sort((a, b) => a.cpse_code.localeCompare(b.cpse_code));
}

/** S4b New run (App Flow 5.4): pick ingested files, the mode, and (ADMIN) options. */
export function NewRun() {
  const { role } = useUser();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const batches = useQuery({ queryKey: ["batches"], queryFn: listBatches });
  const [chosen, setChosen] = useState<string[] | null>(null);
  const [mode, setMode] = useState<RunMode>("CROSS_CPSE");
  const [advanced, setAdvanced] = useState(false);
  const [bm25k, setBm25k] = useState(200);

  const ingested = useMemo(
    () =>
      (batches.data ?? [])
        .filter((b) => b.status === "INGESTED")
        .sort(
          (a, b) =>
            a.cpse_code.localeCompare(b.cpse_code) || b.created_at.localeCompare(a.created_at),
        ),
    [batches.data],
  );
  const selected =
    chosen ?? defaultSelection(ingested, (params.get("batches") ?? "").split(",").filter(Boolean));
  const cpses = new Set(ingested.filter((b) => selected.includes(b.id)).map((b) => b.cpse_code));
  const blocker =
    selected.length === 0
      ? "Choose at least one file."
      : mode === "CROSS_CPSE" && cpses.size < 2
        ? "An across-CPSE run needs files from at least two CPSEs."
        : null;
  const records = ingested
    .filter((b) => selected.includes(b.id))
    .reduce((s, b) => s + (b.quality?.rows ?? 0), 0);

  const start = useMutation({
    mutationFn: () =>
      startRun(selected, mode, role === "ADMIN" && advanced ? { bm25_k: bm25k } : {}),
    onSuccess: (run) => navigate(`/runs/${run.id}`),
  });

  function toggle(id: string) {
    setChosen(selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id]);
  }

  return (
    <section className="max-w-5xl">
      <PageHeader
        title="New run"
        purpose="Choose the files to compare and how. The run takes seconds to minutes; you can watch it live."
      />
      {batches.isPending ? (
        <SkeletonRows rows={4} />
      ) : batches.error ? (
        <ProblemAlert error={batches.error} />
      ) : ingested.length === 0 ? (
        <EmptyState
          icon={CircleAlert}
          title="Nothing to compare yet"
          text="Ingest at least one CPSE file first."
          action={
            <Link to="/upload" className="text-body font-medium text-primary">
              Upload files
            </Link>
          }
        />
      ) : (
        <div className="space-y-5">
          <Card
            title="Files"
            hint="Ingested files. The newest file of each CPSE is chosen for you."
          >
            <ul className="grid gap-2 sm:grid-cols-2">
              {ingested.map((b) => {
                const on = selected.includes(b.id);
                return (
                  <li key={b.id}>
                    <label
                      className={`flex cursor-pointer items-start gap-3 rounded-lg border px-3 py-2.5 transition-colors ${
                        on ? "border-primary bg-auto-bg" : "border-border hover:bg-surface-2"
                      }`}
                    >
                      <input
                        type="checkbox"
                        className="mt-1"
                        checked={on}
                        onChange={() => toggle(b.id)}
                      />
                      <span className="min-w-0 flex-1">
                        <span className="flex items-center gap-2">
                          <Chip tone="info">{b.cpse_code}</Chip>
                          <span className="truncate font-mono text-mono">{b.filename}</span>
                        </span>
                        <span className="mt-1 block text-micro text-muted">
                          {formatCount(b.quality?.rows ?? 0)} records · health{" "}
                          {b.quality?.health_score ?? "–"} · {formatDateTime(b.created_at)}
                        </span>
                      </span>
                    </label>
                  </li>
                );
              })}
            </ul>
          </Card>

          <Card title="What to look for">
            <div role="radiogroup" aria-label="Mode" className="grid gap-2 sm:grid-cols-3">
              {MODES.map((m) => (
                <label
                  key={m}
                  className={`cursor-pointer rounded-lg border px-3 py-2.5 transition-colors ${
                    mode === m ? "border-primary bg-auto-bg" : "border-border hover:bg-surface-2"
                  }`}
                >
                  <span className="flex items-center gap-2 text-body font-medium">
                    <input
                      type="radio"
                      name="mode"
                      checked={mode === m}
                      onChange={() => setMode(m)}
                    />
                    {MODE_LABEL[m]}
                  </span>
                  <span className="mt-1 block text-micro text-muted">{MODE_HINT[m]}</span>
                </label>
              ))}
            </div>
            <button
              type="button"
              onClick={() => setAdvanced((a) => !a)}
              aria-expanded={advanced}
              className="mt-4 flex items-center gap-1 text-label text-muted hover:text-text"
            >
              <ChevronDown size={14} className={advanced ? "rotate-180" : ""} aria-hidden="true" />
              Advanced options
            </button>
            {advanced && (
              <div className="mt-3 grid max-w-md gap-2 rounded-lg bg-surface-2 p-3">
                <label className="text-label" htmlFor="bm25k">
                  Wording neighbours per record without a size
                </label>
                <input
                  id="bm25k"
                  type="number"
                  min={1}
                  max={500}
                  className={INPUT}
                  value={bm25k}
                  disabled={role !== "ADMIN"}
                  onChange={(e) => setBm25k(Number(e.target.value))}
                />
                <p className="text-micro text-muted">
                  {role === "ADMIN"
                    ? "Default 200 (measured on the synthetic set). Larger finds more, slower."
                    : "Only an ADMIN can change the defaults."}
                </p>
              </div>
            )}
          </Card>

          <div className="flex items-center gap-3">
            {blocker ? (
              <p className="flex items-center gap-2 text-body text-ins-fg">
                <CircleAlert size={16} aria-hidden="true" />
                {blocker}
              </p>
            ) : (
              <p className="text-body text-muted">
                {formatCount(records)} records from {cpses.size} CPSE{cpses.size === 1 ? "" : "s"}.
              </p>
            )}
            <div className="ml-auto flex items-center gap-3">
              <ProblemAlert error={start.error} />
              <Button
                icon={Play}
                disabled={!!blocker}
                busy={start.isPending}
                onClick={() => start.mutate()}
              >
                Start run
              </Button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
