import { CircleCheck, CircleHelp } from "lucide-react";
import { ATTR_LABEL, type ClusterMember } from "../../api/review";
import { Chip } from "../ui/Badge";
import { show } from "../../lib/values";

/** "Material DNA": every record of the cluster side by side, each written its own way, with the
 * specification SpecID read from it. A row whose known values all agree gets a check; a value
 * missing on a record is marked, never filled in. */
export function SpecGrid({
  members,
  canonical,
  highlightCpse,
}: {
  members: ClusterMember[];
  canonical: Record<string, unknown>;
  highlightCpse?: string | null;
}) {
  const attrs = Object.keys(canonical).filter((k) =>
    members.some((m) => m.attrs[k] !== null && m.attrs[k] !== undefined),
  );
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-table">
        <thead>
          <tr className="bg-surface-2 align-top">
            <th className="sticky left-0 w-40 bg-surface-2 px-3 py-2 text-left text-label uppercase tracking-wide text-muted">
              Record
            </th>
            {members.map((m) => (
              <th
                key={m.record_id}
                className={`min-w-[13rem] px-3 py-2 text-left font-normal ${
                  highlightCpse === m.cpse ? "bg-auto-bg" : ""
                }`}
              >
                <span className="flex items-center gap-1.5">
                  <Chip tone="info">{m.cpse}</Chip>
                  <span className="font-mono text-micro text-muted">{m.legacy_code}</span>
                </span>
                <span className="mt-1 block font-mono text-micro text-text">
                  {m.long_text || m.short_text}
                </span>
                {(m.manufacturer || m.mpn) && (
                  <span className="mt-0.5 block text-micro text-muted">
                    {m.manufacturer} {m.mpn}
                  </span>
                )}
                {m.mapped_to && (
                  <span className="mt-0.5 block text-micro text-ins-fg">
                    already in {m.mapped_to}
                  </span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {attrs.map((k) => {
            const values = members.map((m) => m.attrs[k]);
            const known = values.filter((v) => v !== null && v !== undefined).map(String);
            const agree = new Set(known).size === 1 && known.length === values.length;
            return (
              <tr key={k} className="border-t border-border">
                <th
                  scope="row"
                  className="sticky left-0 bg-surface px-3 py-2 text-left font-normal text-text"
                >
                  <span className="flex items-center gap-1.5">
                    {agree ? (
                      <CircleCheck
                        size={14}
                        className="text-eq-fg"
                        aria-label="all records agree"
                      />
                    ) : (
                      <CircleHelp
                        size={14}
                        className="text-ins-fg"
                        aria-label="not stated on every record"
                      />
                    )}
                    {ATTR_LABEL[k] ?? k}
                  </span>
                </th>
                {members.map((m) => {
                  const v = m.attrs[k];
                  const missing = v === null || v === undefined;
                  return (
                    <td
                      key={m.record_id}
                      className={`px-3 py-2 font-mono text-mono ${missing ? "text-ins-fg" : "text-text"} ${
                        highlightCpse === m.cpse ? "bg-auto-bg" : ""
                      }`}
                    >
                      {missing ? "not stated" : show(v)}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
