import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BellRing, Check, Download } from "lucide-react";
import { useState } from "react";
import { NOTICE_LABEL, ackNotice, download, listNotices } from "../api/registry";
import { useUser } from "../auth/useAuth";
import { Chip } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { INPUT, ProblemAlert } from "../components/ui/Form";
import { PageHeader } from "../components/ui/PageHeader";
import { EmptyState, SkeletonRows } from "../components/ui/States";
import { formatDateTime } from "../lib/format";

/** S19 Change notices (App Flow 5.14c, SF-12): what changed for my CPSE, with the rows to apply. */
export function Notices() {
  const user = useUser();
  const queryClient = useQueryClient();
  const own = user.role === "MAKER" || user.role === "CHECKER";
  const [cpse, setCpse] = useState("CPSE-A");
  const q = useQuery({
    queryKey: ["notices", own ? "own" : cpse],
    queryFn: () => listNotices(own ? undefined : cpse),
  });
  const ack = useMutation({
    mutationFn: ackNotice,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notices"] }),
  });
  const dl = useMutation({
    mutationFn: (id: string) => download(`/change-notices/${id}/delta.csv`, `notice_${id}.csv`),
  });
  const canAck = user.role === "MAKER" || user.role === "CHECKER";
  return (
    <section className="max-w-5xl">
      <PageHeader
        title="Change notices"
        purpose={`What changed in the national registry for ${q.data?.cpse ?? user.cpse_code ?? "your CPSE"}, and the rows to apply.`}
      />
      {!own && (
        <select
          aria-label="CPSE"
          className={`${INPUT} mb-4 w-36`}
          value={cpse}
          onChange={(e) => setCpse(e.target.value)}
        >
          {["CPSE-A", "CPSE-B", "CPSE-C"].map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>
      )}
      <ProblemAlert error={ack.error ?? dl.error} />
      {q.isPending ? (
        <SkeletonRows rows={4} />
      ) : q.error ? (
        <ProblemAlert error={q.error} />
      ) : q.data.items.length === 0 ? (
        <EmptyState
          icon={BellRing}
          title="No changes yet"
          text="No changes affect your CPSE yet."
        />
      ) : (
        <ul className="space-y-2">
          {q.data.items.map((n) => (
            <li
              key={n.id}
              className={`flex flex-wrap items-center gap-3 rounded-lg border px-4 py-3 ${
                n.acknowledged_at ? "border-border bg-surface" : "border-primary bg-auto-bg"
              }`}
            >
              <Chip tone={n.kind === "CONSENT_DECLINED" ? "warn" : "info"}>
                {NOTICE_LABEL[n.kind] ?? n.kind}
              </Chip>
              <span className="min-w-0 flex-1">
                <span className="block text-body text-text">{n.summary}</span>
                <span className="block font-mono text-micro text-muted">
                  {n.delta.map((d) => String(d.legacy_code)).join(", ")} ·{" "}
                  {formatDateTime(n.created_at)}
                </span>
              </span>
              <Button variant="ghost" icon={Download} onClick={() => dl.mutate(n.id)}>
                Rows
              </Button>
              {n.acknowledged_at ? (
                <span className="text-micro text-muted">
                  Acknowledged{n.acknowledged_by ? ` by ${n.acknowledged_by}` : ""}
                </span>
              ) : (
                canAck && (
                  <Button
                    variant="secondary"
                    icon={Check}
                    busy={ack.isPending}
                    onClick={() => ack.mutate(n.id)}
                  >
                    Acknowledge
                  </Button>
                )
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
