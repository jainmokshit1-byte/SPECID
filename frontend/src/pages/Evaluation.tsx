import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, FlaskConical, Info, Play, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { CATEGORY_LABEL } from "../api/batches";
import { type EvalRun, type MethodScore, getEval, listEvals, startEval } from "../api/insights";
import { download } from "../api/registry";
import { StatusBadge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { INPUT, ProblemAlert } from "../components/ui/Form";
import { PageHeader } from "../components/ui/PageHeader";
import { StatTile } from "../components/ui/StatTile";
import { EmptyState, SkeletonRows } from "../components/ui/States";
import { formatCount, formatDateTime } from "../lib/format";
import { EVIDENCE_LADDER, HONESTY_POINTS } from "../lib/honesty";

const pct = (v: number | null | undefined, d = 1) =>
  v === null || v === undefined ? "–" : `${(v * 100).toFixed(d)}%`;

/** S11a Evaluation list (App Flow 5.11): seeded runs on synthetic data; New evaluation. */
export function EvaluationList() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [seed, setSeed] = useState(7);
  const list = useQuery({
    queryKey: ["evals"],
    queryFn: listEvals,
    refetchInterval: (q) =>
      q.state.data?.some((e) => e.status === "RUNNING" || e.status === "QUEUED") ? 2000 : false,
  });
  const start = useMutation({
    mutationFn: () => startEval(seed),
    onSuccess: (e) => {
      void queryClient.invalidateQueries({ queryKey: ["evals"] });
      navigate(`/evaluation/${e.id}`);
    },
  });
  return (
    <section className="max-w-6xl">
      <PageHeader
        title="Evaluation"
        purpose="How SpecID performs on seeded synthetic data with known answers, next to two simple text baselines. Same seed, same numbers."
        action={
          <span className="flex items-center gap-2">
            <label htmlFor="seed" className="text-label">
              Seed
            </label>
            <input
              id="seed"
              type="number"
              className={`${INPUT} w-20`}
              value={seed}
              onChange={(e) => setSeed(Number(e.target.value))}
            />
            <Button icon={Play} busy={start.isPending} onClick={() => start.mutate()}>
              New evaluation
            </Button>
          </span>
        }
      />
      <ProblemAlert error={start.error} />
      {list.isPending ? (
        <SkeletonRows rows={3} />
      ) : list.error ? (
        <ProblemAlert error={list.error} />
      ) : list.data.length === 0 ? (
        <EmptyState
          icon={FlaskConical}
          title="No evaluation yet"
          text="Results will be labelled SYNTHETIC."
        />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border bg-surface">
          <table className="w-full text-table">
            <thead className="bg-surface-2 text-left text-label uppercase tracking-wide text-muted">
              <tr>
                <th className="px-4 py-2 font-medium">Evaluation</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 text-right font-medium">Seed</th>
                <th className="px-4 py-2 text-right font-medium">Wrong merges</th>
                <th className="px-4 py-2 font-medium">Started</th>
              </tr>
            </thead>
            <tbody>
              {list.data.map((e) => (
                <tr key={e.id} className="border-t border-border hover:bg-surface-2">
                  <td className="px-4 py-2.5">
                    <Link
                      to={`/evaluation/${e.id}`}
                      className="font-mono text-mono text-primary hover:underline"
                    >
                      {e.id.slice(0, 8)}
                    </Link>
                  </td>
                  <td className="px-4 py-2.5">
                    <StatusBadge status={e.status} />
                  </td>
                  <td className="tabular px-4 py-2.5 text-right">{e.seed}</td>
                  <td className="tabular px-4 py-2.5 text-right">
                    {e.metrics?.methods
                      ? `${e.metrics.methods.specid.false_merges} of ${formatCount(e.metrics.methods.specid.hard_negatives)}`
                      : "–"}
                  </td>
                  <td className="px-4 py-2.5 text-muted">{formatDateTime(e.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

/** S11b Evaluation report (App Flow 5.11, PRD 10.2b, FR-1441-1443): safety headline with its
 * bound, the baseline scoreboard, abstentions, disagreements, per category, honesty panel. */
export function EvaluationReport() {
  const { evalId = "" } = useParams();
  const q = useQuery({
    queryKey: ["eval", evalId],
    queryFn: () => getEval(evalId),
    refetchInterval: (x) =>
      x.state.data && ["QUEUED", "RUNNING"].includes(x.state.data.status) ? 2000 : false,
  });
  const dl = useMutation({
    mutationFn: () => download(`/eval/runs/${evalId}/report.md`, `eval_${evalId}.md`),
  });
  const header = (
    <PageHeader
      title="Evaluation report"
      purpose="Synthetic data with known answers. Read the honesty panel before quoting any number."
      action={
        q.data?.status === "DONE" ? (
          <Button variant="secondary" icon={Download} onClick={() => dl.mutate()}>
            Report (Markdown)
          </Button>
        ) : undefined
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
  const e = q.data;
  return (
    <section className="max-w-6xl">
      {header}
      {e.status !== "DONE" || !e.metrics?.methods ? (
        <Card>
          <p className="text-body text-muted">
            {e.status === "FAILED"
              ? `Failed: ${e.metrics?.error}`
              : "Running… this takes under a minute."}
          </p>
        </Card>
      ) : (
        <Report e={e} />
      )}
    </section>
  );
}

function Report({ e }: { e: EvalRun }) {
  const m = e.metrics!;
  const s = m.methods.specid;
  const rows: [string, MethodScore][] = [
    ["SpecID", s],
    [`B1 · text only (threshold ${m.methods.b1.tau})`, m.methods.b1],
    [`B2 · text + numbers (threshold ${m.methods.b2.tau})`, m.methods.b2],
  ];
  return (
    <div className="space-y-5">
      <div className="rounded-lg border border-eq-fg bg-eq-bg p-5">
        <p className="flex items-center gap-2 text-label uppercase tracking-wide text-eq-fg">
          <ShieldCheck size={16} aria-hidden="true" /> Safety headline · synthetic data
        </p>
        <p className="mt-2 text-display text-text">
          Wrong merges: {s.false_merges} of {formatCount(s.hard_negatives)} look-alike pairs
        </p>
        <p className="mt-1 text-body text-muted">
          95% upper bound {pct(s.false_merge_upper_95, 2)}
          {s.false_merges === 0 ? " (rule of three: zero observed is not “never”)" : ""} · seed{" "}
          {e.seed} · commit {e.git_commit ?? "–"}
        </p>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile
          label="Equivalents found"
          value={pct(s.recall_strict)}
          sub="of truly same pairs (strict)"
        />
        <StatTile
          label="Precision"
          value={pct(s.precision, 2)}
          sub="of the pairs called the same"
        />
        <StatTile
          label="Can't tell"
          value={pct(m.abstentions.rate)}
          sub={`${formatCount(m.abstentions.justified)} of ${formatCount(m.abstentions.total)} miss a key value in the text`}
        />
        <StatTile
          label="Pairs found by blocking"
          value={pct(m.blocking.pair_completeness)}
          sub={`compared ${pct(1 - (m.blocking.reduction_ratio ?? 1), 2)} of all pairs`}
        />
      </div>
      <Card
        title="Scoreboard"
        hint="Same candidate pairs, same test split, same truth. Baseline thresholds tuned on the validation split."
        padded={false}
      >
        <table className="w-full text-table">
          <thead className="bg-surface-2 text-left text-label uppercase tracking-wide text-muted">
            <tr>
              <th className="px-4 py-2 font-medium">Method</th>
              <th className="px-4 py-2 text-right font-medium">Wrong merges (look-alikes)</th>
              <th className="px-4 py-2 text-right font-medium">Same items found</th>
              <th className="px-4 py-2 text-right font-medium">Precision</th>
              <th className="px-4 py-2 text-right font-medium">Decided</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([name, x], i) => (
              <tr key={name} className={`border-t border-border ${i === 0 ? "font-medium" : ""}`}>
                <td className="px-4 py-2">{name}</td>
                <td
                  className={`tabular px-4 py-2 text-right ${x.false_merges ? "text-ne-fg" : "text-eq-fg"}`}
                >
                  {formatCount(x.false_merges)} of {formatCount(x.hard_negatives)}
                </td>
                <td className="tabular px-4 py-2 text-right">{formatCount(x.tp)}</td>
                <td className="tabular px-4 py-2 text-right">{pct(x.precision, 2)}</td>
                <td className="tabular px-4 py-2 text-right">{pct(x.coverage)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="px-4 py-2 text-micro text-muted">
          SpecID decides fewer pairs on purpose: when a key value is missing it says “can't tell”
          and asks, instead of guessing.
        </p>
      </Card>
      <div className="grid gap-5 lg:grid-cols-2">
        <Card title="Where they disagree" hint="On the test split.">
          {(
            [
              ["b1_merged_specid_vetoed", "Text-only merged, SpecID blocked"],
              ["of_which_truly_different", "…of which truly different items"],
              [
                "b1_wrong_merges_specid_asked",
                "Text-only wrong merges (any pair) SpecID sent to a person",
              ],
              ["specid_found_b1_missed", "SpecID found, text-only missed"],
              ["specid_found_b2_missed", "SpecID found, text + numbers missed"],
            ] as const
          ).map(([k, label]) => (
            <div key={k} className="flex justify-between py-1 text-body">
              <span className="text-muted">{label}</span>
              <span className="tabular">{formatCount(m.disagreements[k] ?? 0)}</span>
            </div>
          ))}
        </Card>
        <Card title="Per category (SpecID)" padded={false}>
          <table className="w-full text-table">
            <tbody>
              {Object.entries(m.per_category).map(([c, x]) => (
                <tr key={c} className="border-t border-border first:border-t-0">
                  <td className="px-4 py-1.5">{CATEGORY_LABEL[c] ?? c}</td>
                  <td className="tabular px-4 py-1.5 text-right">found {pct(x.recall_strict)}</td>
                  <td className="tabular px-4 py-1.5 text-right">
                    wrong merges {x.false_merges} of {x.hard_negatives}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
      <HonestyPanel />
    </div>
  );
}

export function HonestyPanel() {
  return (
    <section
      aria-labelledby="honesty"
      className="rounded-lg border border-border-strong bg-surface p-5"
    >
      <h2 id="honesty" className="flex items-center gap-2 text-h3">
        <Info size={18} aria-hidden="true" /> What these numbers do not mean
      </h2>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-body text-text">
        {HONESTY_POINTS.map((p) => (
          <li key={p}>{p}</li>
        ))}
      </ul>
      <p className="mt-4 text-label uppercase tracking-wide text-muted">Evidence ladder</p>
      <ol className="mt-2 grid gap-2 md:grid-cols-4">
        {EVIDENCE_LADDER.map(([id, name, text], i) => (
          <li
            key={id}
            className={`rounded-lg border px-3 py-2 ${i < 3 ? "border-eq-fg bg-eq-bg" : "border-dashed border-border"}`}
          >
            <span className="text-label">
              {id} · {name}
            </span>
            <span className="mt-0.5 block text-micro text-muted">{text}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
