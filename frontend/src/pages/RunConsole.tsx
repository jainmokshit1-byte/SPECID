import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Boxes,
  CircleSlash,
  CircleX,
  Clock,
  Database,
  GitCompareArrows,
  OctagonPause,
  RotateCcw,
  ShieldCheck,
} from "lucide-react";
import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  ACTIVE,
  CHANNEL_LABEL,
  MODE_LABEL,
  type Run,
  cancelRun,
  durationMs,
  formatDuration,
  getRun,
  listPairs,
  startRun,
} from "../api/runs";
import { Chip, StatusBadge, VerdictBadge } from "../components/ui/Badge";
import { BuiltLink } from "../components/ui/BuiltLink";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Dialog } from "../components/ui/Dialog";
import { ProblemAlert } from "../components/ui/Form";
import { Meter, VerdictBar } from "../components/ui/Meter";
import { PageHeader } from "../components/ui/PageHeader";
import { StatTile } from "../components/ui/StatTile";
import { SkeletonRows } from "../components/ui/States";
import { type Step, Stepper } from "../components/ui/Stepper";
import { formatCount, formatDateTime } from "../lib/format";
import { VERDICT_ORDER, type Verdict } from "../lib/verdicts";

const STAGES: { id: string; label: string; timing?: string }[] = [
  { id: "read", label: "Read descriptions", timing: "read" },
  { id: "candidates", label: "Find likely pairs", timing: "candidates" },
  { id: "decide", label: "Decide each pair", timing: "decide" },
  { id: "cluster", label: "Group same items", timing: "cluster" },
];

// eslint-disable-next-line react-refresh/only-export-components -- pure helper, tested directly
export function stageSteps(run: Run): Step[] {
  const s = run.stats ?? {};
  const t = s.timings_ms ?? {};
  const detail: Record<string, string | undefined> = {
    read: s.records !== undefined ? `${formatCount(s.records)} records` : undefined,
    candidates:
      s.candidate_pairs !== undefined ? `${formatCount(s.candidate_pairs)} pairs` : undefined,
    decide: s.verdicts
      ? `${formatCount(Object.values(s.verdicts).reduce((a, b) => a + (b ?? 0), 0))} decided`
      : undefined,
    cluster: s.clusters !== undefined ? `${formatCount(s.clusters)} groups` : undefined,
  };
  return STAGES.map((st) => {
    const ms = st.timing ? t[st.timing] : undefined;
    const parts = [detail[st.id], ms !== undefined ? formatDuration(ms) : undefined].filter(
      Boolean,
    );
    return { id: st.id, label: st.label, detail: parts.join(" · ") || undefined };
  });
}

/** S4c Run console (App Flow 5.4): live stage stepper, stats, cancel; on DONE the verdict mix,
 * channels and pairs; on FAILED the error and "Start again". */
export function RunConsole() {
  const { runId = "" } = useParams();
  const queryClient = useQueryClient();
  const run = useQuery({
    queryKey: ["run", runId],
    queryFn: () => getRun(runId),
    refetchInterval: (q) => (q.state.data && ACTIVE.includes(q.state.data.status) ? 1000 : false),
  });
  const [confirm, setConfirm] = useState(false);
  const cancel = useMutation({
    mutationFn: () => cancelRun(runId),
    onSuccess: (r) => {
      setConfirm(false);
      queryClient.setQueryData(["run", runId], r);
    },
  });

  if (run.isPending || run.error)
    return (
      <section className="max-w-6xl">
        <PageHeader title="Run console" purpose="Watch the run, then open the results." />
        {run.error ? <ProblemAlert error={run.error} /> : <SkeletonRows rows={6} />}
      </section>
    );
  const r = run.data;
  const s = r.stats ?? {};
  const active = ACTIVE.includes(r.status);
  const prog = s.progress;
  const stage =
    r.status === "DONE" ? "done" : prog?.stage === "queued" ? null : (prog?.stage ?? null);
  const progress = prog && prog.total > 0 ? prog.done / prog.total : null;
  const n = s.records ?? 0;
  const allPairs = (n * (n - 1)) / 2;

  return (
    <section className="max-w-6xl">
      <PageHeader
        title="Run console"
        purpose="Watch the run, then open the results. Every number on this page comes from this run."
        action={
          active ? (
            <Button
              variant="secondary"
              icon={OctagonPause}
              onClick={() => setConfirm(true)}
              disabled={r.status === "CANCELLING"}
            >
              {r.status === "CANCELLING" ? "Cancelling…" : "Cancel run"}
            </Button>
          ) : r.status === "DONE" ? (
            <BuiltLink to={`/review?run=${r.id}`} pattern="/review" label="Open review queue" />
          ) : undefined
        }
      />
      <div className="mb-5 flex flex-wrap items-center gap-2 text-body">
        <span className="font-mono text-mono text-text">{r.id.slice(0, 8)}</span>
        <StatusBadge status={r.status} />
        <Chip>{MODE_LABEL[r.mode]}</Chip>
        <span className="text-muted">
          started {formatDateTime(r.started_at)}
          {r.started_by ? ` by ${r.started_by}` : ""} · {formatDuration(durationMs(r))}
        </span>
      </div>

      <Card className="mb-5">
        <Stepper
          steps={stageSteps(r)}
          current={stage}
          progress={progress}
          finished={r.status === "DONE"}
          failed={r.status === "FAILED"}
        />
        {r.status === "QUEUED" && (
          <p className="mt-3 flex items-center gap-2 text-body text-muted">
            <Clock size={16} aria-hidden="true" /> Waiting for the worker. Runs go one at a time.
          </p>
        )}
      </Card>

      {r.status === "FAILED" && <FailedPanel run={r} />}
      {r.status === "CANCELLED" && (
        <Card className="mb-5">
          <p className="text-body text-muted">
            This run was cancelled. Its partial results were removed.
          </p>
        </Card>
      )}

      <div className="mb-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile
          icon={Database}
          label="Records"
          value={s.records !== undefined ? formatCount(s.records) : "–"}
          sub={
            s.unclassified ? `${formatCount(s.unclassified)} without a category` : "read and parsed"
          }
        />
        <StatTile
          icon={GitCompareArrows}
          label="Pairs compared"
          value={s.candidate_pairs !== undefined ? formatCount(s.candidate_pairs) : "–"}
          sub={
            allPairs > 0 && s.candidate_pairs !== undefined
              ? `${((s.candidate_pairs / allPairs) * 100).toFixed(1)}% of ${formatCount(allPairs)} possible`
              : "likely pairs only"
          }
        />
        <StatTile
          icon={Boxes}
          label="Groups found"
          value={s.clusters !== undefined ? formatCount(s.clusters) : "–"}
          sub="same item, to review"
        />
        <StatTile
          icon={ShieldCheck}
          label="Blocked egress"
          value={s.blocked_egress ?? "–"}
          sub="outbound attempts during the run"
          accent="text-eq-fg"
        />
      </div>

      {s.verdicts && (
        <div className="mb-5 grid gap-5 lg:grid-cols-[1.4fr_1fr]">
          <Card
            title="Verdict mix"
            hint="Every compared pair gets one of four answers. A veto is never overridden."
          >
            <VerdictSummary verdicts={s.verdicts} />
          </Card>
          <Card title="How pairs were found" hint="A pair found by two routes counts for both.">
            {Object.entries(CHANNEL_LABEL).map(([k, label]) => (
              <Meter
                key={k}
                label={label}
                value={s.candidate_pairs ? (s.channels?.[k as "B"] ?? 0) / s.candidate_pairs : 0}
                bar={k === "D" ? "bg-ai-fg" : "bg-primary"}
                hint={`${formatCount(s.channels?.[k as "B"] ?? 0)} pairs`}
              />
            ))}
            {!s.channels?.D && (
              <p className="mt-1 text-micro text-muted">
                Meaning search (AI) is off for this run; rules and text search found these pairs.
              </p>
            )}
          </Card>
        </div>
      )}

      {!!(s.classified_by_ml || s.ai_records_asked) && (
        <div className="mb-5">
          <Card
            title="What AI did in this run"
            hint="AI reads and proposes; a value counts only if it is written in the record text and allowed by the rulebook. Rules still decide."
          >
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <AiFact
                label="Category guessed by AI"
                value={s.classified_by_ml}
                sub="records with no category word"
              />
              <AiFact
                label="Records read by AI"
                value={s.ai_records_asked}
                sub={s.ai_provider ?? "off"}
              />
              <AiFact
                label="Values accepted"
                value={s.ai_values_accepted}
                sub="found in the text, allowed"
              />
              <AiFact
                label="Values rejected"
                value={s.ai_values_rejected}
                sub="not in the text or not allowed"
              />
            </div>
          </Card>
        </div>
      )}

      {r.status === "DONE" && <PairsPanel runId={r.id} counts={s.verdicts ?? {}} />}

      <Dialog
        open={confirm}
        onOpenChange={setConfirm}
        title="Cancel this run?"
        description="The run stops after the current batch of pairs and its partial results are removed."
      >
        <ProblemAlert error={cancel.error} />
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setConfirm(false)}>
            Keep running
          </Button>
          <Button variant="danger" busy={cancel.isPending} onClick={() => cancel.mutate()}>
            Cancel run
          </Button>
        </div>
      </Dialog>
    </section>
  );
}

function VerdictSummary({ verdicts }: { verdicts: Partial<Record<Verdict, number>> }) {
  const total = VERDICT_ORDER.reduce((a, v) => a + (verdicts[v] ?? 0), 0);
  const blocked = verdicts.NOT_EQUIVALENT ?? 0;
  return (
    <div>
      <VerdictBar verdicts={verdicts} height="h-3" showLegend={false} />
      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {VERDICT_ORDER.map((v) => (
          <div key={v} className="rounded-lg bg-surface-2 px-3 py-2">
            <VerdictBadge verdict={v} />
            <p className="tabular mt-1 text-h2 text-text">{formatCount(verdicts[v] ?? 0)}</p>
            <p className="text-micro text-muted">
              {total ? `${(((verdicts[v] ?? 0) / total) * 100).toFixed(1)}% of pairs` : "–"}
            </p>
          </div>
        ))}
      </div>
      {blocked > 0 && (
        <p className="mt-3 text-label font-normal text-muted">
          Most blocked pairs are near-misses that share a size: a different pressure class, material
          or end. They were compared on purpose, and none is merged.
        </p>
      )}
    </div>
  );
}

function FailedPanel({ run }: { run: Run }) {
  const again = useMutation({
    mutationFn: () => startRun(run.batch_ids, run.mode),
    onSuccess: (r) => window.location.assign(`/runs/${r.id}`),
  });
  return (
    <div
      role="alert"
      className="mb-5 flex items-start gap-3 rounded-lg border border-danger bg-ne-bg px-4 py-3"
    >
      <CircleX className="mt-0.5 shrink-0 text-ne-fg" size={18} aria-hidden="true" />
      <div className="flex-1">
        <p className="text-body font-medium text-ne-fg">
          The run failed during “{run.stats?.progress?.stage ?? "start"}”.
        </p>
        <p className="mt-0.5 font-mono text-micro text-ne-fg">{run.error}</p>
        <ProblemAlert error={again.error} />
      </div>
      <Button
        variant="secondary"
        icon={RotateCcw}
        busy={again.isPending}
        onClick={() => again.mutate()}
      >
        Start again
      </Button>
    </div>
  );
}

function PairsPanel({
  runId,
  counts,
}: {
  runId: string;
  counts: Partial<Record<Verdict, number>>;
}) {
  const [verdict, setVerdict] = useState<Verdict | "LOOKALIKE">("EQUIVALENT");
  const pairs = useQuery({
    queryKey: ["pairs", runId, verdict],
    queryFn: () =>
      listPairs(
        runId,
        verdict === "LOOKALIKE"
          ? { lookalike: "LOOKALIKE_VETOED", limit: 50 }
          : { verdict, limit: 50 },
      ),
  });
  const looks = useQuery({
    queryKey: ["pairs", runId, "look-count"],
    queryFn: () => listPairs(runId, { lookalike: "LOOKALIKE_VETOED", limit: 1 }),
  });
  const tabs: (Verdict | "LOOKALIKE")[] = [...VERDICT_ORDER, "LOOKALIKE"];
  return (
    <Card
      title="Pairs"
      hint="The 50 most similar-looking pairs per answer. Open a group in the review queue to act on it."
      padded={false}
    >
      <div
        role="tablist"
        aria-label="Pairs by answer"
        className="flex flex-wrap gap-1 border-b border-border px-3 py-2"
      >
        {tabs.map((t) => (
          <button
            key={t}
            role="tab"
            type="button"
            aria-selected={verdict === t}
            onClick={() => setVerdict(t)}
            className={`rounded px-2.5 py-1 text-label transition-colors ${
              verdict === t ? "bg-surface-2 text-text" : "text-muted hover:text-text"
            }`}
          >
            {t === "LOOKALIKE" ? (
              <span className="inline-flex items-center gap-1">
                <CircleSlash size={13} aria-hidden="true" /> Look-alikes blocked{" "}
                <span className="tabular">{formatCount(looks.data?.total ?? 0)}</span>
              </span>
            ) : (
              <VerdictBadge verdict={t} count={counts[t] ?? 0} />
            )}
          </button>
        ))}
      </div>
      {pairs.isPending ? (
        <div className="p-4">
          <SkeletonRows rows={5} />
        </div>
      ) : pairs.error ? (
        <div className="p-4">
          <ProblemAlert error={pairs.error} />
        </div>
      ) : pairs.data.items.length === 0 ? (
        <p className="p-4 text-body text-muted">No pairs with this answer.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-table">
            <thead className="text-left text-label uppercase tracking-wide text-muted">
              <tr>
                <th className="px-4 py-2 font-medium">Record A</th>
                <th className="px-4 py-2 font-medium">Record B</th>
                <th className="px-4 py-2 text-right font-medium">Text similarity</th>
                <th className="px-4 py-2 font-medium">Why</th>
              </tr>
            </thead>
            <tbody>
              {pairs.data.items.map((p) => (
                <tr key={p.id} className="border-t border-border align-top hover:bg-surface-2">
                  <td className="px-4 py-2">
                    <RecordCell cpse={p.cpse_a} code={p.code_a} text={p.text_a} />
                  </td>
                  <td className="px-4 py-2">
                    <RecordCell cpse={p.cpse_b} code={p.code_b} text={p.text_b} />
                  </td>
                  <td className="tabular px-4 py-2 text-right">
                    {p.text_sim !== null ? `${Math.round(p.text_sim * 100)}%` : "–"}
                  </td>
                  <td className="px-4 py-2 text-muted">
                    {p.reasons.length ? p.reasons.join("; ") : "All key attributes match"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function RecordCell({ cpse, code, text }: { cpse: string; code: string; text: string }) {
  return (
    <div className="min-w-[14rem] max-w-md">
      <span className="flex items-center gap-1.5">
        <Chip tone="info">{cpse}</Chip>
        <span className="font-mono text-micro text-muted">{code}</span>
      </span>
      <span className="mt-0.5 block font-mono text-micro text-text">{text}</span>
    </div>
  );
}

function AiFact({ label, value, sub }: { label: string; value?: number | null; sub: string }) {
  return (
    <div className="rounded-lg bg-ai-bg px-3 py-2">
      <span className="block text-label text-ai-fg">{label}</span>
      <span className="tabular block text-h2 text-text">
        {value === undefined || value === null ? "–" : formatCount(value)}
      </span>
      <span className="block text-micro text-muted">{sub}</span>
    </div>
  );
}
