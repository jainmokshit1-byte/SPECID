import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  BadgeCheck,
  Check,
  CircleHelp,
  CircleX,
  Clock3,
  Handshake,
  RotateCcw,
  ShieldAlert,
  Undo2,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { CATEGORY_LABEL } from "../api/batches";
import {
  type ClusterDetail,
  type Outcome,
  STATE_LABEL,
  answerConsent,
  check,
  getCluster,
  propose,
} from "../api/review";
import { useUser } from "../auth/useAuth";
import { CodeChip } from "../components/review/CodeChip";
import { ConsentStrip } from "../components/review/ConsentStrip";
import { EvidenceCard } from "../components/review/EvidenceCard";
import { SpecGrid } from "../components/review/SpecGrid";
import { Chip, VerdictBadge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Dialog } from "../components/ui/Dialog";
import { INPUT, ProblemAlert } from "../components/ui/Form";
import { PageHeader } from "../components/ui/PageHeader";
import { SkeletonRows } from "../components/ui/States";
import { formatDateTime } from "../lib/format";

type Ask =
  | { kind: "propose"; decision: "REJECT" | "NEEDS_INFO" }
  | { kind: "overturn" }
  | { kind: "decline" };

const ASK_COPY: Record<string, { title: string; text: string; button: string }> = {
  REJECT: {
    title: "Reject this group?",
    text: "Say why these records are not the same item. A checker confirms your proposal.",
    button: "Propose reject",
  },
  NEEDS_INFO: {
    title: "Ask for missing information?",
    text: "Say which value is missing and from which CPSE. The group waits until it is supplied.",
    button: "Propose needs info",
  },
  overturn: {
    title: "Overturn the proposal?",
    text: "The group goes back to the maker with your comment.",
    button: "Overturn",
  },
  decline: {
    title: "Decline for your CPSE?",
    text: "Your CPSE's codes stay out of the national code. The reason is recorded and shared.",
    button: "Decline",
  },
};

/** S6 Cluster review, the hero screen (App Flow 5.6, UI/UX brief 7.3): the records side by side
 * with the specification read from each, the proposed national code, the evidence of every pair,
 * and only the actions this user may take (from the API's `can`). */
export function ClusterReview() {
  const { clusterId = "" } = useParams();
  const user = useUser();
  const queryClient = useQueryClient();
  const q = useQuery({ queryKey: ["cluster", clusterId], queryFn: () => getCluster(clusterId) });
  const [ask, setAsk] = useState<Ask | null>(null);
  const [comment, setComment] = useState("");
  const [outcome, setOutcome] = useState<Outcome | null>(null);

  const act = useMutation({
    mutationFn: async (fn: () => Promise<Outcome>) => fn(),
    onSuccess: (out) => {
      setOutcome(out);
      setAsk(null);
      setComment("");
      void queryClient.invalidateQueries({ queryKey: ["cluster", clusterId] });
      void queryClient.invalidateQueries({ queryKey: ["clusters"] });
      void queryClient.invalidateQueries({ queryKey: ["consents"] });
    },
  });

  const c = q.data;
  // keyboard: A approve / confirm, R reject, N needs info (UI/UX brief 1.2 rule 5)
  useEffect(() => {
    if (!c) return;
    function onKey(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement || ask)
        return;
      const k = e.key.toLowerCase();
      if (k === "a" && c!.can.propose) act.mutate(() => propose(clusterId, "APPROVE"));
      else if (k === "a" && c!.can.check) act.mutate(() => check(clusterId, "CONFIRM"));
      else if (k === "r" && c!.can.propose) setAsk({ kind: "propose", decision: "REJECT" });
      else if (k === "n" && c!.can.propose) setAsk({ kind: "propose", decision: "NEEDS_INFO" });
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [c, ask, act, clusterId]);

  if (q.isPending || q.error)
    return (
      <section className="max-w-7xl">
        <PageHeader title="Cluster review" purpose="Check that these records are the same item." />
        {q.error ? <ProblemAlert error={q.error} /> : <SkeletonRows rows={8} />}
      </section>
    );

  const copyKey = ask ? (ask.kind === "propose" ? ask.decision : ask.kind) : "";
  const p = c!.proposal;

  function submitAsk() {
    if (!ask) return;
    if (ask.kind === "propose") act.mutate(() => propose(clusterId, ask.decision, comment));
    else if (ask.kind === "overturn") act.mutate(() => check(clusterId, "OVERTURN", comment));
    else act.mutate(() => answerConsent(clusterId, "DECLINE", comment));
  }

  return (
    <section className="max-w-7xl pb-24">
      <PageHeader
        title="Cluster review"
        purpose="Check that these records are the same item. Every value shows where it came from; nothing is filled in."
        action={
          <Link
            to="/review"
            className="inline-flex items-center gap-1 text-body text-primary hover:underline"
          >
            <ArrowLeft size={16} aria-hidden="true" /> Back to the queue
          </Link>
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Chip tone="info">{CATEGORY_LABEL[c!.category ?? ""] ?? c!.category}</Chip>
        <Chip>{c!.members.length} records</Chip>
        <Chip tone={c!.task.state === "DONE" ? "good" : "warn"}>{STATE_LABEL[c!.task.state]}</Chip>
        {c!.critical && (
          <Chip tone="bad" icon={ShieldAlert}>
            Critical item: two people must agree
          </Chip>
        )}
        {c!.cnmc && (
          <span className="ml-1 inline-flex items-center gap-1.5 text-body">
            <BadgeCheck size={16} className="text-eq-fg" aria-hidden="true" />
            Issued as <CodeChip code={c!.cnmc} />
          </span>
        )}
        <span className="ml-auto">
          <ConsentStrip consents={c!.consents} />
        </span>
      </div>

      {outcome && <OutcomeBanner outcome={outcome} />}

      <div className="grid gap-5 xl:grid-cols-[1fr_22rem]">
        <Card
          title="The records, and what SpecID read from each"
          hint="Same item written differently by each CPSE. A check means every record states the same value."
          padded={false}
        >
          <div className="p-3">
            <SpecGrid
              members={c!.members}
              canonical={p.canonical_spec}
              highlightCpse={c!.can.consent ? user.cpse_code : null}
            />
          </div>
        </Card>
        <Card title="Proposed national code" hint="Generated from the shared specification.">
          <p className="text-label uppercase tracking-wide text-muted">Short text (SAP, 40)</p>
          <p className="mt-1 rounded bg-surface-2 px-2 py-1.5 font-mono text-mono text-text">
            {p.short_desc_40 ?? "Needs a manual abbreviation"}
          </p>
          {p.short_desc_40 && (
            <p
              className={`mt-1 text-right text-micro ${
                p.short_desc_40.length > 35 ? "text-ins-fg" : "text-muted"
              }`}
            >
              {p.short_desc_40.length} / 40
            </p>
          )}
          <p className="mt-3 text-label uppercase tracking-wide text-muted">Long text</p>
          <p className="mt-1 text-body text-text">{p.long_desc}</p>
          <p className="mt-3 text-label uppercase tracking-wide text-muted">Class</p>
          <p className="mt-1 text-body text-text">{p.class_path.join(" › ")}</p>
          <p className="mt-3 text-label uppercase tracking-wide text-muted">Base unit</p>
          <p className="mt-1 font-mono text-mono text-text">{p.base_uom ?? "—"}</p>
          {p.variants.length > 0 && (
            <>
              <p className="mt-3 text-label uppercase tracking-wide text-muted">Makes</p>
              <ul className="mt-1 space-y-0.5 text-micro text-text">
                {p.variants.map(([m, n]) => (
                  <li key={`${m}-${n}`} className="font-mono">
                    {m} {n}
                  </li>
                ))}
              </ul>
            </>
          )}
        </Card>
      </div>

      <PairsCard cluster={c!} />

      {c!.decisions.length > 0 && (
        <Card title="History" className="mt-5">
          <ol className="space-y-2">
            {c!.decisions.map((d, i) => (
              <li key={i} className="flex flex-wrap items-baseline gap-2 text-body">
                <span className="text-micro text-muted">{formatDateTime(d.at)}</span>
                <span className="font-medium">{d.by}</span>
                <span className="text-muted">({d.role.toLowerCase()})</span>
                <span>{d.decision.toLowerCase().replace("_", " ")}</span>
                {d.comment && <span className="text-muted">— “{d.comment}”</span>}
              </li>
            ))}
          </ol>
        </Card>
      )}

      <ActionBar
        cluster={c!}
        busy={act.isPending}
        error={act.error}
        onApprove={() => act.mutate(() => propose(clusterId, "APPROVE"))}
        onConfirm={() => act.mutate(() => check(clusterId, "CONFIRM"))}
        onConsent={() => act.mutate(() => answerConsent(clusterId, "CONSENT"))}
        onAsk={setAsk}
      />

      <Dialog
        open={ask !== null}
        onOpenChange={(o) => !o && setAsk(null)}
        title={ASK_COPY[copyKey]?.title ?? ""}
        description={ASK_COPY[copyKey]?.text ?? ""}
      >
        <label htmlFor="ask-comment" className="mb-1 block text-label">
          {ask?.kind === "decline" ? "Reason" : "Comment"} (at least 5 characters)
        </label>
        <textarea
          id="ask-comment"
          className={`${INPUT} h-24 py-1.5`}
          value={comment}
          onChange={(e) => setComment(e.target.value)}
        />
        <ProblemAlert error={act.error} />
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setAsk(null)}>
            Cancel
          </Button>
          <Button
            variant={ask?.kind === "decline" || copyKey === "REJECT" ? "danger" : "primary"}
            disabled={comment.trim().length < 5}
            busy={act.isPending}
            onClick={submitAsk}
          >
            {ASK_COPY[copyKey]?.button}
          </Button>
        </div>
      </Dialog>
    </section>
  );
}

function OutcomeBanner({ outcome }: { outcome: Outcome }) {
  const [tone, Icon, text] = outcome.cnmc
    ? ["border-eq-fg bg-eq-bg text-eq-fg", BadgeCheck, `National code ${outcome.cnmc} issued.`]
    : outcome.state === "AWAITING_CONSENT"
      ? [
          "border-auto-fg bg-auto-bg text-auto-fg",
          Clock3,
          `Confirmed. Waiting for consent from ${outcome.waiting_for.join(", ")}.`,
        ]
      : outcome.state === "MADE"
        ? [
            "border-auto-fg bg-auto-bg text-auto-fg",
            Check,
            "Proposal saved. A checker confirms it next.",
          ]
        : outcome.state === "OPEN"
          ? ["border-ins-fg bg-ins-bg text-ins-fg", Undo2, "Sent back to the maker."]
          : ["border-border bg-surface-2 text-text", Check, "Recorded."];
  return (
    <div
      role="status"
      className={`mb-4 flex items-center gap-2 rounded-lg border px-4 py-2.5 text-body ${tone}`}
    >
      <Icon size={18} aria-hidden="true" />
      <span className="flex-1">{text}</span>
      {outcome.cnmc && <CodeChip code={outcome.cnmc} />}
      <Link to="/review" className="font-medium underline">
        Next in the queue
      </Link>
    </div>
  );
}

function PairsCard({ cluster }: { cluster: ClusterDetail }) {
  const [open, setOpen] = useState<string | null>(cluster.pairs[0]?.id ?? null);
  const code = Object.fromEntries(
    cluster.members.map((m) => [m.record_id, `${m.cpse} ${m.legacy_code}`]),
  );
  const pair = cluster.pairs.find((x) => x.id === open);
  return (
    <Card
      title="Evidence for each pair"
      hint="Why SpecID says these are the same: attribute by attribute, with the rule it applied."
      className="mt-5"
    >
      <div className="grid gap-4 lg:grid-cols-[16rem_1fr]">
        <ul className="max-h-80 space-y-1 overflow-y-auto">
          {cluster.pairs.map((x) => (
            <li key={x.id}>
              <button
                type="button"
                onClick={() => setOpen(x.id)}
                className={`w-full rounded px-2 py-1.5 text-left text-micro transition-colors ${
                  open === x.id ? "bg-auto-bg text-text" : "text-muted hover:bg-surface-2"
                }`}
              >
                <span className="block font-mono">{code[x.rec_a]}</span>
                <span className="block font-mono">↔ {code[x.rec_b]}</span>
                <span className="mt-0.5 block">
                  <VerdictBadge verdict={x.verdict} />
                </span>
              </button>
            </li>
          ))}
        </ul>
        {pair ? (
          <div>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-label font-normal text-muted">
                Text similarity{" "}
                {pair.text_sim !== null ? `${Math.round(pair.text_sim * 100)}%` : "–"}
                {pair.lookalike === "HIDDEN_TWIN" && " · worded differently, same specification"}
              </span>
              <Link to={`/pairs/${pair.id}`} className="text-label text-primary hover:underline">
                Open full evidence
              </Link>
            </div>
            <EvidenceCard
              rows={pair.evidence}
              labelA={code[pair.rec_a]}
              labelB={code[pair.rec_b]}
            />
          </div>
        ) : (
          <p className="text-body text-muted">No decided pairs.</p>
        )}
      </div>
    </Card>
  );
}

function ActionBar({
  cluster,
  busy,
  error,
  onApprove,
  onConfirm,
  onConsent,
  onAsk,
}: {
  cluster: ClusterDetail;
  busy: boolean;
  error: unknown;
  onApprove: () => void;
  onConfirm: () => void;
  onConsent: () => void;
  onAsk: (a: Ask) => void;
}) {
  const can = cluster.can;
  const proposed = cluster.task.proposed;
  let content: JSX.Element | null = null;
  if (can.propose)
    content = (
      <>
        <span className="text-body text-muted">Your decision as maker:</span>
        <Button
          variant="secondary"
          icon={CircleHelp}
          onClick={() => onAsk({ kind: "propose", decision: "NEEDS_INFO" })}
        >
          Needs info <Kbd k="N" />
        </Button>
        <Button
          variant="secondary"
          icon={CircleX}
          onClick={() => onAsk({ kind: "propose", decision: "REJECT" })}
        >
          Reject <Kbd k="R" />
        </Button>
        <Button icon={Check} busy={busy} onClick={onApprove}>
          Approve as one item <Kbd k="A" light />
        </Button>
      </>
    );
  else if (can.check)
    content = (
      <>
        <span className="text-body text-muted">
          {cluster.task.made_by} proposed{" "}
          <strong className="text-text">{proposed?.toLowerCase().replace("_", " ")}</strong>.
        </span>
        <Button variant="secondary" icon={RotateCcw} onClick={() => onAsk({ kind: "overturn" })}>
          Overturn
        </Button>
        <Button icon={BadgeCheck} busy={busy} onClick={onConfirm}>
          {proposed === "APPROVE" ? "Confirm and issue code" : "Confirm"} <Kbd k="A" light />
        </Button>
      </>
    );
  else if (can.consent)
    content = (
      <>
        <span className="text-body text-muted">
          Your CPSE's records are highlighted. A national code changes your master data, so it needs
          your consent.
        </span>
        <Button variant="secondary" icon={CircleX} onClick={() => onAsk({ kind: "decline" })}>
          Decline
        </Button>
        <Button icon={Handshake} busy={busy} onClick={onConsent}>
          Consent for my CPSE
        </Button>
      </>
    );
  else if (can.waiting_for_other_checker)
    content = (
      <span className="text-body text-muted">
        You made this proposal. Another checker must confirm it.
      </span>
    );
  if (!content) return null;
  return (
    <div className="fixed bottom-footer left-sidebar right-0 z-topbar border-t border-border bg-surface px-6 py-3 shadow-[0_-4px_12px_rgba(0,0,0,0.06)]">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-end gap-3">
        <ProblemAlert error={error} />
        {content}
      </div>
    </div>
  );
}

function Kbd({ k, light }: { k: string; light?: boolean }) {
  return (
    <kbd
      className={`ml-1 rounded border px-1 font-mono text-micro ${
        light ? "border-on-primary text-on-primary opacity-80" : "border-border-strong text-muted"
      }`}
    >
      {k}
    </kbd>
  );
}
