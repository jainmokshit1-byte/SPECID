import { useQuery } from "@tanstack/react-query";
import { Library, Search } from "lucide-react";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { CATEGORY_LABEL } from "../api/batches";
import { listCnmc } from "../api/registry";
import { CodeChip } from "../components/review/CodeChip";
import { Chip } from "../components/ui/Badge";
import { INPUT, ProblemAlert } from "../components/ui/Form";
import { PageHeader } from "../components/ui/PageHeader";
import { EmptyState, SkeletonRows } from "../components/ui/States";
import { formatCount, formatDateTime } from "../lib/format";

const CATEGORIES = ["VALVE", "PIPE", "FLANGE", "FASTENER", "MOTOR", "GASKET"];

/** S8a Registry (App Flow 5.8): every national code, searchable by code, text or legacy code. */
export function Registry() {
  const [params, setParams] = useSearchParams();
  const [text, setText] = useState(params.get("q") ?? "");
  const q = params.get("q") ?? "";
  const category = params.get("category") ?? "";
  const list = useQuery({
    queryKey: ["cnmc", q, category],
    queryFn: () => listCnmc({ q, category, limit: 200 }),
  });

  function set(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  }

  return (
    <section className="max-w-6xl">
      <PageHeader
        title="Registry"
        purpose="One national code per real item, each linked to the codes every CPSE used before."
      />
      <form
        className="mb-4 flex flex-wrap gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          set("q", text.trim());
        }}
      >
        <span className="relative min-w-64 flex-1">
          <Search size={16} className="absolute left-2 top-2 text-muted" aria-hidden="true" />
          <input
            aria-label="Search the registry"
            className={`${INPUT} pl-8`}
            placeholder="National code, description or a CPSE's legacy code"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        </span>
        <select
          aria-label="Category"
          className={`${INPUT} w-44`}
          value={category}
          onChange={(e) => set("category", e.target.value)}
        >
          <option value="">All categories</option>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {CATEGORY_LABEL[c]}
            </option>
          ))}
        </select>
      </form>
      {list.isPending ? (
        <SkeletonRows rows={5} />
      ) : list.error ? (
        <ProblemAlert error={list.error} />
      ) : list.data.items.length === 0 ? (
        <EmptyState
          icon={Library}
          title={q || category ? "No national code matches" : "No national codes yet"}
          text={
            q || category
              ? "Try another search."
              : "Codes are issued when a checker confirms a group and every CPSE involved consents."
          }
          action={
            !q && !category ? (
              <Link to="/review" className="text-body font-medium text-primary">
                Open the review queue
              </Link>
            ) : undefined
          }
        />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border bg-surface">
          <p className="border-b border-border px-4 py-2 text-label font-normal text-muted">
            {formatCount(list.data.total)} national code{list.data.total === 1 ? "" : "s"}
          </p>
          <table className="w-full text-table">
            <thead className="bg-surface-2 text-left text-label uppercase tracking-wide text-muted">
              <tr>
                <th className="px-4 py-2 font-medium">National code</th>
                <th className="px-4 py-2 font-medium">Description</th>
                <th className="px-4 py-2 font-medium">CPSEs</th>
                <th className="px-4 py-2 text-right font-medium">Old codes</th>
                <th className="px-4 py-2 font-medium">Issued</th>
              </tr>
            </thead>
            <tbody>
              {list.data.items.map((r) => (
                <tr key={r.cnmc} className="border-t border-border hover:bg-surface-2">
                  <td className="whitespace-nowrap px-4 py-2.5">
                    <CodeChip code={r.cnmc} />
                  </td>
                  <td className="px-4 py-2.5">
                    <span className="block font-mono text-mono">{r.short_desc_40}</span>
                    <span className="text-micro text-muted">
                      {CATEGORY_LABEL[r.category] ?? r.category}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    <span className="flex flex-wrap gap-1">
                      {r.cpses.map((c) => (
                        <Chip key={c} tone="info">
                          {c}
                        </Chip>
                      ))}
                    </span>
                  </td>
                  <td className="tabular px-4 py-2.5 text-right">{r.codes}</td>
                  <td className="px-4 py-2.5 text-muted">{formatDateTime(r.issued_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
