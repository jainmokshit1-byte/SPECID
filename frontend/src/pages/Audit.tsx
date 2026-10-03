import { useInfiniteQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, CircleCheck, CircleX } from "lucide-react";
import { Fragment, useEffect, useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import { apiGet } from "../api/client";
import {
  AUDIT_ACTIONS,
  AUDIT_OBJECT_TYPES,
  type AuditEvent,
  type AuditPage,
  type VerifyResult,
  cursorBefore,
} from "../api/audit";
import { BTN_PRIMARY, BTN_SECONDARY, INPUT, ProblemAlert } from "../components/ui/Form";
import { PageHeader } from "../components/ui/PageHeader";
import { formatCount, formatDateTime, istDayStart } from "../lib/format";

const FILTERS = ["actor", "action", "object_type", "from", "to"] as const;
type FilterKey = (typeof FILTERS)[number];

/** S12 Audit (App Flow 5.13, J7): filterable log, rows expand to before/after JSON, Verify chain.
 * Filters live in the query string (App Flow 9); a broken chain links to `#event=<id>`. */
export function Audit() {
  const [params, setParams] = useSearchParams();
  const { hash } = useLocation();
  const focus = Number(/^#event=(\d+)$/.exec(hash)?.[1] ?? NaN);
  const focusId = Number.isFinite(focus) ? focus : null;
  const queryClient = useQueryClient();

  const filters = Object.fromEntries(FILTERS.map((k) => [k, params.get(k) ?? ""])) as Record<
    FilterKey,
    string
  >;
  const active = FILTERS.some((k) => filters[k]);

  const list = useInfiniteQuery({
    queryKey: ["audit", filters, focusId],
    initialPageParam: focusId !== null ? cursorBefore(focusId + 1) : "",
    getNextPageParam: (last: AuditPage) => last.next_cursor ?? undefined,
    queryFn: ({ pageParam }) => {
      const q = new URLSearchParams({ limit: "50" });
      if (filters.actor) q.set("actor", filters.actor);
      if (filters.action) q.set("action", filters.action);
      if (filters.object_type) q.set("object_type", filters.object_type);
      if (filters.from) q.set("since", istDayStart(filters.from));
      if (filters.to) q.set("until", istDayStart(filters.to, 1));
      if (pageParam) q.set("cursor", pageParam);
      return apiGet<AuditPage>(`/audit?${q}`);
    },
  });

  const verify = useMutation({
    mutationFn: () => apiGet<VerifyResult>("/audit/verify"),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["audit"] }),
  });

  function setFilter(key: FilterKey, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  }

  const rows = list.data?.pages.flatMap((p) => p.items) ?? [];

  return (
    <section className="max-w-6xl">
      <PageHeader
        title="Audit"
        purpose="Every change is recorded in a hash chain. Verify the chain to check that no event was edited."
        action={
          <button
            type="button"
            className={BTN_PRIMARY}
            disabled={verify.isPending}
            onClick={() => verify.mutate()}
          >
            {verify.isPending ? "Verifying…" : "Verify chain"}
          </button>
        }
      />

      {verify.data && <VerifyBanner result={verify.data} />}
      {verify.isError && <ProblemAlert error={verify.error} />}

      <form
        aria-label="Filters"
        className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-5"
        onSubmit={(e) => e.preventDefault()}
      >
        <FilterInput label="Actor (username)" id="f-actor">
          <input
            id="f-actor"
            className={INPUT}
            key={filters.actor}
            defaultValue={filters.actor}
            onBlur={(e) => setFilter("actor", e.target.value.trim())}
            onKeyDown={(e) => {
              if (e.key === "Enter") setFilter("actor", e.currentTarget.value.trim());
            }}
          />
        </FilterInput>
        <FilterInput label="Action" id="f-action">
          <select
            id="f-action"
            className={INPUT}
            value={filters.action}
            onChange={(e) => setFilter("action", e.target.value)}
          >
            <option value="">All actions</option>
            {AUDIT_ACTIONS.map((a) => (
              <option key={a}>{a}</option>
            ))}
          </select>
        </FilterInput>
        <FilterInput label="Object type" id="f-object">
          <select
            id="f-object"
            className={INPUT}
            value={filters.object_type}
            onChange={(e) => setFilter("object_type", e.target.value)}
          >
            <option value="">All types</option>
            {AUDIT_OBJECT_TYPES.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
        </FilterInput>
        <FilterInput label="From (IST)" id="f-from">
          <input
            id="f-from"
            type="date"
            className={INPUT}
            value={filters.from}
            onChange={(e) => setFilter("from", e.target.value)}
          />
        </FilterInput>
        <FilterInput label="To (IST)" id="f-to">
          <input
            id="f-to"
            type="date"
            className={INPUT}
            value={filters.to}
            onChange={(e) => setFilter("to", e.target.value)}
          />
        </FilterInput>
      </form>

      {list.isError ? (
        <ProblemAlert error={list.error} />
      ) : list.isPending ? (
        <Skeleton />
      ) : rows.length === 0 ? (
        <Empty
          active={active}
          onClear={() => setParams(new URLSearchParams(), { replace: true })}
        />
      ) : (
        <>
          {focusId !== null && (
            <p className="mb-2 text-body text-muted">
              Showing events from #{focusId} back.{" "}
              <Link to="/audit" className="text-primary underline">
                Show newest
              </Link>
            </p>
          )}
          <EventTable rows={rows} focusId={focusId} />
          {list.hasNextPage && (
            <button
              type="button"
              className={`${BTN_SECONDARY} mt-3`}
              disabled={list.isFetchingNextPage}
              onClick={() => void list.fetchNextPage()}
            >
              {list.isFetchingNextPage ? "Loading…" : "Load older events"}
            </button>
          )}
        </>
      )}
    </section>
  );
}

function VerifyBanner({ result }: { result: VerifyResult }) {
  if (result.ok)
    return (
      <p
        role="status"
        className="mb-4 flex items-center gap-2 rounded border border-eq-fg bg-eq-bg px-3 py-2 text-body text-eq-fg"
      >
        <CircleCheck size={16} strokeWidth={1.75} aria-hidden="true" />
        Chain intact ({formatCount(result.events)} events)
      </p>
    );
  return (
    <p
      role="alert"
      className="mb-4 flex items-center gap-2 rounded border border-ne-fg bg-ne-bg px-3 py-2 text-body text-ne-fg"
    >
      <CircleX size={16} strokeWidth={1.75} aria-hidden="true" />
      Chain broken at event #{result.first_bad_id}.
      <Link to={`/audit#event=${result.first_bad_id}`} className="font-medium underline">
        Show event #{result.first_bad_id}
      </Link>
    </p>
  );
}

function FilterInput({
  label,
  id,
  children,
}: {
  label: string;
  id: string;
  children: JSX.Element;
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-label text-text">
        {label}
      </label>
      {children}
    </div>
  );
}

function EventTable({ rows, focusId }: { rows: AuditEvent[]; focusId: number | null }) {
  const [open, setOpen] = useState<Set<number>>(() => new Set(focusId ? [focusId] : []));
  useEffect(() => {
    if (focusId === null) return;
    setOpen((s) => new Set(s).add(focusId));
    document.getElementById(`event-${focusId}`)?.scrollIntoView?.({ block: "center" });
  }, [focusId, rows.length]);

  const toggle = (id: number) =>
    setOpen((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });

  return (
    <div className="overflow-x-auto rounded border border-border bg-surface">
      <table className="w-full text-table">
        <thead className="sticky top-0 border-b border-border bg-surface text-left text-label text-muted">
          <tr>
            <th className="w-8 px-2 py-2" aria-label="Expand" />
            <th className="px-2 py-2 text-right">#</th>
            <th className="px-2 py-2">Time (IST)</th>
            <th className="px-2 py-2">Actor</th>
            <th className="px-2 py-2">Action</th>
            <th className="px-2 py-2">Object</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((e) => {
            const expanded = open.has(e.id);
            return (
              <Fragment key={e.id}>
                <tr
                  id={`event-${e.id}`}
                  className={`h-10 border-b border-border hover:bg-surface-2 ${
                    e.id === focusId ? "bg-ne-bg" : ""
                  }`}
                >
                  <td className="px-2">
                    <button
                      type="button"
                      aria-expanded={expanded}
                      aria-label={`${expanded ? "Hide" : "Show"} details of event ${e.id}`}
                      onClick={() => toggle(e.id)}
                      className="rounded p-1 text-muted hover:bg-surface-2"
                    >
                      {expanded ? (
                        <ChevronDown size={14} aria-hidden="true" />
                      ) : (
                        <ChevronRight size={14} aria-hidden="true" />
                      )}
                    </button>
                  </td>
                  <td className="px-2 text-right font-mono">{e.id}</td>
                  <td className="whitespace-nowrap px-2">{formatDateTime(e.ts)}</td>
                  <td className="px-2">{e.actor ?? <span className="text-muted">none</span>}</td>
                  <td className="px-2 font-mono">{e.action}</td>
                  <td className="px-2">
                    <span className="text-muted">{e.object_type}</span>{" "}
                    <span className="font-mono">{e.object_id}</span>
                  </td>
                </tr>
                {expanded && (
                  <tr className="border-b border-border bg-surface-2">
                    <td />
                    <td colSpan={5} className="px-2 py-3">
                      <div className="grid gap-3 md:grid-cols-2">
                        <Json label="Before" value={e.before} />
                        <Json label="After" value={e.after} />
                      </div>
                      <dl className="mt-3 grid grid-cols-[6rem_1fr] gap-x-3 gap-y-1 text-micro">
                        <dt className="text-muted">Hash</dt>
                        <dd className="break-all font-mono">{e.hash}</dd>
                        <dt className="text-muted">Previous</dt>
                        <dd className="break-all font-mono">
                          {e.prev_hash ?? "none (first event)"}
                        </dd>
                      </dl>
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Json({ label, value }: { label: string; value: unknown }) {
  return (
    <div>
      <p className="mb-1 text-label text-muted">{label}</p>
      <pre className="overflow-x-auto rounded border border-border bg-surface p-2 font-mono text-mono">
        {value === null ? "none" : JSON.stringify(value, null, 2)}
      </pre>
    </div>
  );
}

function Skeleton() {
  return (
    <div aria-label="Loading events" role="status" className="space-y-1">
      {Array.from({ length: 5 }, (_, i) => (
        <div key={i} className="h-10 rounded bg-surface-2" />
      ))}
    </div>
  );
}

function Empty({ active, onClear }: { active: boolean; onClear: () => void }) {
  return (
    <div className="rounded border border-border bg-surface p-6 text-center">
      <p className="text-h3">{active ? "No results for these filters." : "No events recorded."}</p>
      {active && (
        <button type="button" className={`${BTN_SECONDARY} mt-3`} onClick={onClear}>
          Clear filters
        </button>
      )}
    </div>
  );
}
