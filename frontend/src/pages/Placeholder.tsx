import { Construction } from "lucide-react";
import { useParams } from "react-router-dom";
import type { RouteDef } from "../routes";

/** Placeholder for a route from 03 App Flow section 2 until its phase builds the real screen. */
export function Placeholder({ route }: { route: RouteDef }) {
  const params = useParams();
  const paramEntries = Object.entries(params).filter(([k]) => k !== "*");

  return (
    <section aria-labelledby="page-title" className="max-w-3xl">
      <div className="mb-2 flex items-center gap-2">
        <span className="rounded-chip bg-surface-2 px-1.5 py-0.5 font-mono text-micro text-muted">
          {route.screen}
        </span>
        {route.pri === "P1" && (
          <span className="rounded-chip border border-border-strong px-1.5 py-0.5 text-micro text-muted">
            P1
          </span>
        )}
      </div>
      <h1 id="page-title" className="text-h1">
        {route.title}
      </h1>
      <p className="mt-1 text-body text-muted">{route.purpose}</p>

      <dl className="mt-6 grid grid-cols-[10rem_1fr] gap-x-4 gap-y-2 rounded border border-border bg-surface p-4 text-table">
        <dt className="text-muted">Route</dt>
        <dd className="font-mono">{route.path}</dd>
        {paramEntries.map(([k, v]) => (
          <div key={k} className="contents">
            <dt className="text-muted">{k}</dt>
            <dd className="font-mono">{v}</dd>
          </div>
        ))}
        <dt className="text-muted">Roles</dt>
        <dd>{route.roles.join(", ")}</dd>
        <dt className="text-muted">Requirements</dt>
        <dd>{route.prd}</dd>
      </dl>

      <p className="mt-4 flex items-center gap-2 text-body text-muted">
        <Construction size={16} strokeWidth={1.75} aria-hidden="true" />
        {route.phase === null
          ? "Placeholder. Not yet scheduled in the Implementation Plan."
          : `Placeholder. Built in Phase ${route.phase} of the Implementation Plan.`}
      </p>
    </section>
  );
}
