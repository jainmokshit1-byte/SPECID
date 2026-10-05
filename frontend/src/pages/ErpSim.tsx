import { useQuery } from "@tanstack/react-query";
import { CircleCheck, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { searchBeforeCreate } from "../api/insights";
import { listCnmc } from "../api/registry";
import { CodeChip } from "../components/review/CodeChip";
import { VerdictBadge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { PageHeader } from "../components/ui/PageHeader";
import { resultBanner } from "./Search";

const FIELD =
  "h-7 w-full border border-[#7f9db9] bg-white px-1.5 font-mono text-[13px] text-[#1a1a1a] focus:outline focus:outline-2 focus:outline-[#f0ab00]";

/** S14 Create material, mock ERP (PRD SF-8, FR-1471): an SAP-style form with search-before-create
 * running live as the user types (300 ms debounce). Saving is a simulation. */
export function ErpSim() {
  const [desc, setDesc] = useState("");
  const [debounced, setDebounced] = useState("");
  const [uom, setUom] = useState("EA");
  const [saved, setSaved] = useState(false);
  useEffect(() => {
    const t = window.setTimeout(() => setDebounced(desc.trim()), 300);
    return () => window.clearTimeout(t);
  }, [desc]);
  const q = useQuery({
    queryKey: ["erp-search", debounced],
    queryFn: () => searchBeforeCreate(debounced),
    enabled: debounced.length >= 6,
  });
  // The example is a code that exists in this registry, so the check has something to find.
  const example = useQuery({
    queryKey: ["erp-example"],
    queryFn: () => listCnmc({ limit: 1 }),
  }).data?.items[0]?.short_desc_40;
  const r = q.data;
  const top = r?.candidates.find((c) => c.verdict === "EQUIVALENT" || c.verdict === "IDENTICAL");
  const len = desc.length;
  return (
    <section className="max-w-6xl">
      <PageHeader
        title="Create material (SAP simulation)"
        purpose="What a CPSE user sees in SAP when SpecID is connected: a duplicate is flagged while they type. Nothing here writes to any ERP."
      />
      <div className="grid gap-5 lg:grid-cols-[1.3fr_1fr]">
        <div className="overflow-hidden rounded border border-[#7f9db9] bg-[#eef3f8] text-[#1a1a1a] shadow-sm">
          <div className="flex items-center gap-2 bg-gradient-to-b from-[#365a87] to-[#25446b] px-3 py-1.5 text-[13px] font-semibold text-white">
            <span className="rounded bg-white/20 px-1">MM01</span> Create Material (Initial Screen)
            — Basic Data 1
          </div>
          <div className="space-y-3 p-4 text-[13px]">
            <div className="grid grid-cols-[9rem_1fr] items-center gap-2">
              <label htmlFor="erp-type">Material Type</label>
              <select id="erp-type" className={FIELD}>
                <option>ERSA Spare parts</option>
                <option>ROH Raw materials</option>
              </select>
              <label htmlFor="erp-desc">Material Description</label>
              <div>
                <input
                  id="erp-desc"
                  className={`${FIELD} ${len > 40 ? "border-[#bb0000]" : ""}`}
                  value={desc}
                  onChange={(e) => {
                    setDesc(e.target.value);
                    setSaved(false);
                  }}
                  placeholder="e.g. GATE VLV 4IN 150# WCB FLGD RF"
                />
                <span
                  className={`mt-0.5 block text-right text-[11px] ${len > 40 ? "text-[#bb0000]" : len > 35 ? "text-[#a36200]" : "text-[#555]"}`}
                >
                  {len} / 40{len > 40 ? " — too long, abbreviate" : ""}
                </span>
              </div>
              <label htmlFor="erp-uom">Base Unit of Measure</label>
              <select
                id="erp-uom"
                className={`${FIELD} w-28`}
                value={uom}
                onChange={(e) => setUom(e.target.value)}
              >
                {["EA", "M", "KG", "SET"].map((u) => (
                  <option key={u}>{u}</option>
                ))}
              </select>
              <label htmlFor="erp-group">Material Group</label>
              <input id="erp-group" className={`${FIELD} w-40`} defaultValue="VLV" />
            </div>
            {top && r && (
              <div className="rounded border border-[#e9730c] bg-[#fef7f1] p-3 text-[#6b3600]">
                <p className="font-semibold">
                  ⚠ This material already exists in the national registry.
                </p>
                <p className="mt-1">
                  {top.cnmc} · {top.short_desc_40} · used by {top.cpses.join(", ")}
                </p>
                <div className="mt-2 flex gap-2">
                  <button
                    type="button"
                    className="rounded border border-[#e9730c] bg-white px-2 py-0.5"
                    onClick={() => setDesc(top.short_desc_40 ?? desc)}
                  >
                    Use SpecID description
                  </button>
                  <a
                    href={`/registry/${top.cnmc}`}
                    className="rounded border border-[#e9730c] bg-white px-2 py-0.5"
                  >
                    Use {top.cnmc}
                  </a>
                </div>
              </div>
            )}
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setSaved(true)}
                className="inline-flex items-center gap-1 rounded border border-[#2b5788] bg-gradient-to-b from-[#f4f8fc] to-[#d9e5f1] px-3 py-1 text-[13px]"
              >
                <Save size={14} aria-hidden="true" /> Save
              </button>
            </div>
            {saved && (
              <p role="status" className="flex items-center gap-1 text-[#256f3a]">
                <CircleCheck size={14} aria-hidden="true" /> Would create the material (simulation:
                nothing was written).
              </p>
            )}
          </div>
        </div>
        <div className="rounded-lg border border-border bg-surface p-4 shadow-sm">
          <p className="text-label uppercase tracking-wide text-muted">SpecID check (live)</p>
          {debounced.length < 6 ? (
            <p className="mt-2 text-body text-muted">Start typing a description in the SAP form.</p>
          ) : q.isFetching && !r ? (
            <p className="mt-2 text-body text-muted">Checking…</p>
          ) : r ? (
            <>
              {(() => {
                const [tone, Icon, text] = resultBanner(r);
                return (
                  <p
                    className={`mt-2 flex items-start gap-2 rounded border px-3 py-2 text-body ${tone}`}
                  >
                    <Icon size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
                    {text}
                  </p>
                );
              })()}
              <ul className="mt-3 space-y-2">
                {r.candidates.slice(0, 4).map((c) => (
                  <li key={c.cnmc} className="flex flex-wrap items-center gap-2 text-micro">
                    <CodeChip code={c.cnmc} />
                    <VerdictBadge verdict={c.verdict} />
                    <span className="font-mono">{c.short_desc_40}</span>
                  </li>
                ))}
              </ul>
            </>
          ) : null}
          <Button
            variant="ghost"
            className="mt-3"
            onClick={() => setDesc(example ?? "GATE VALVE 4IN 150# WCB FLGD RF")}
          >
            Try an example
          </Button>
        </div>
      </div>
    </section>
  );
}
