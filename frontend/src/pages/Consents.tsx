import { useQuery } from "@tanstack/react-query";
import { Handshake } from "lucide-react";
import { Link } from "react-router-dom";
import { CATEGORY_LABEL } from "../api/batches";
import { consentQueue } from "../api/review";
import { useUser } from "../auth/useAuth";
import { ProblemAlert } from "../components/ui/Form";
import { PageHeader } from "../components/ui/PageHeader";
import { EmptyState, SkeletonRows } from "../components/ui/States";
import { formatDateTime } from "../lib/format";

/** S18 Consent queue (App Flow 5.14b, SF-11): national codes waiting for my CPSE's answer. */
export function Consents() {
  const user = useUser();
  const q = useQuery({ queryKey: ["consents"], queryFn: consentQueue });
  return (
    <section className="max-w-6xl">
      <PageHeader
        title="Consent queue"
        purpose={`National codes that would absorb ${user.cpse_code ?? "your CPSE"}'s codes. Nothing changes your master data until you consent.`}
      />
      {q.isPending ? (
        <SkeletonRows rows={4} />
      ) : q.error ? (
        <ProblemAlert error={q.error} />
      ) : q.data.items.length === 0 ? (
        <EmptyState
          icon={Handshake}
          title="Nothing waiting"
          text={`No national codes are waiting for ${user.cpse_code ?? "your CPSE"}'s consent.`}
        />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border bg-surface">
          <table className="w-full text-table">
            <thead className="bg-surface-2 text-left text-label uppercase tracking-wide text-muted">
              <tr>
                <th className="px-4 py-2 font-medium">Item</th>
                <th className="px-4 py-2 font-medium">My codes</th>
                <th className="px-4 py-2 font-medium">Proposed / confirmed by</th>
                <th className="px-4 py-2 font-medium">Waiting since</th>
              </tr>
            </thead>
            <tbody>
              {q.data.items.map((i) => (
                <tr key={i.cluster_id} className="border-t border-border hover:bg-surface-2">
                  <td className="px-4 py-2.5">
                    <Link to={`/clusters/${i.cluster_id}`} className="block">
                      <span className="text-label font-normal text-muted">
                        {CATEGORY_LABEL[i.category ?? ""] ?? i.category} · {i.members} records
                      </span>
                      <span className="block font-mono text-mono text-primary hover:underline">
                        {i.sample_text}
                      </span>
                    </Link>
                  </td>
                  <td className="px-4 py-2.5 font-mono text-micro">{i.my_codes.join(", ")}</td>
                  <td className="px-4 py-2.5 text-muted">
                    {i.proposed_by} / {i.confirmed_by}
                  </td>
                  <td className="px-4 py-2.5 text-muted">{formatDateTime(i.waiting_since)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
