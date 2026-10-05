import { useMutation } from "@tanstack/react-query";
import {
  CircleAlert,
  CircleCheck,
  Search as SearchIcon,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { useState } from "react";
import { type SearchCandidate, type SearchResult, searchBeforeCreate } from "../api/insights";
import { ATTR_LABEL } from "../api/review";
import { CodeChip } from "../components/review/CodeChip";
import { EvidenceCard } from "../components/review/EvidenceCard";
import { Chip, VerdictBadge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { INPUT, ProblemAlert } from "../components/ui/Form";
import { PageHeader } from "../components/ui/PageHeader";

const EXAMPLES = [
  "GATE VALVE 4IN 150# WCB FLGD RF",
  "PIPE SMLS 6IN SCH40 A106 GR.B",
  "25NB 300# WCB BW",
];

/** S9 Search-before-create (App Flow 5.9, FR-1001-1003): is this item already coded? */
export function Search() {
  const [text, setText] = useState("");
  const [mpn, setMpn] = useState("");
  const [maker, setMaker] = useState("");
  const q = useMutation({ mutationFn: () => searchBeforeCreate(text, mpn, maker) });
  return (
    <section className="max-w-6xl">
      <PageHeader
        title="Search before create"
        purpose="Before creating a new material code, check whether the item already has a national code. SAP can call the same check through the API."
      />
      <Card>
        <form
          className="grid gap-3 md:grid-cols-[1fr_12rem_12rem_auto]"
          onSubmit={(e) => {
            e.preventDefault();
            if (text.trim().length > 1) q.mutate();
          }}
        >
          <input
            aria-label="Description"
            className={INPUT}
            placeholder="Description, as you would type it in SAP"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <input
            aria-label="Manufacturer"
            className={INPUT}
            placeholder="Maker (optional)"
            value={maker}
            onChange={(e) => setMaker(e.target.value)}
          />
          <input
            aria-label="Part number"
            className={INPUT}
            placeholder="Part no. (optional)"
            value={mpn}
            onChange={(e) => setMpn(e.target.value)}
          />
          <Button
            type="submit"
            icon={SearchIcon}
            busy={q.isPending}
            disabled={text.trim().length < 2}
          >
            Check
          </Button>
        </form>
        <p className="mt-2 flex flex-wrap items-center gap-2 text-micro text-muted">
          Try:
          {EXAMPLES.map((e) => (
            <button
              key={e}
              type="button"
              className="rounded bg-surface-2 px-1.5 py-0.5 font-mono hover:text-text"
              onClick={() => setText(e)}
            >
              {e}
            </button>
          ))}
        </p>
      </Card>
      <ProblemAlert error={q.error} />
      {q.data && <Result r={q.data} />}
    </section>
  );
}

// eslint-disable-next-line react-refresh/only-export-components -- shared with the SAP simulator
export function resultBanner(r: SearchResult): [string, typeof CircleCheck, string] {
  if (r.recommended_action === "USE_EXISTING")
    return [
      "border-ne-fg bg-ne-bg text-ne-fg",
      ShieldAlert,
      "Duplicate risk: this item already has a national code.",
    ];
  if (r.recommended_action === "SUPPLY_ATTRIBUTES")
    return ["border-ins-fg bg-ins-bg text-ins-fg", CircleAlert, r.message];
  return [
    "border-eq-fg bg-eq-bg text-eq-fg",
    CircleCheck,
    "No national code matches this specification. A new code may be created.",
  ];
}

function Result({ r }: { r: SearchResult }) {
  const [tone, Icon, text] = resultBanner(r);
  return (
    <div className="mt-5 space-y-4">
      <div className={`flex items-start gap-2 rounded-lg border px-4 py-3 text-body ${tone}`}>
        <Icon size={18} className="mt-0.5 shrink-0" aria-hidden="true" />
        <div>
          <p className="font-medium">{text}</p>
          {r.missing.length > 0 && (
            <p className="mt-0.5 text-label font-normal">
              Add: {r.missing.map((m) => ATTR_LABEL[m] ?? m).join(", ")}
            </p>
          )}
        </div>
      </div>
      <Card title="What SpecID read" hint="The specification parsed from your text.">
        <div className="flex flex-wrap items-center gap-1.5">
          {r.query.category ? (
            <Chip tone="info">{r.query.category}</Chip>
          ) : (
            <Chip tone="warn">category not recognised</Chip>
          )}
          {r.query.class_source === "ML" && (
            <Chip tone="ai" icon={Sparkles}>
              category by AI
            </Chip>
          )}
          {Object.entries(r.query.attrs).map(([k, v]) => (
            <span key={k} className="rounded-chip bg-surface-2 px-1.5 py-0.5 font-mono text-micro">
              {ATTR_LABEL[k] ?? k}: {String(v)}
            </span>
          ))}
          {r.query.repairs.map((x) => (
            <span
              key={x}
              className="rounded-chip bg-ai-bg px-1.5 py-0.5 font-mono text-micro text-ai-fg"
            >
              spelling {x}
            </span>
          ))}
        </div>
      </Card>
      {r.candidates.map((c) => (
        <CandidateCard key={c.cnmc} c={c} />
      ))}
    </div>
  );
}

function CandidateCard({ c }: { c: SearchCandidate }) {
  const [open, setOpen] = useState(c.verdict !== "NOT_EQUIVALENT");
  return (
    <Card>
      <div className="flex flex-wrap items-center gap-3">
        <CodeChip code={c.cnmc} />
        <VerdictBadge verdict={c.verdict} />
        <span className="font-mono text-mono">{c.short_desc_40}</span>
        <span className="ml-auto flex gap-1">
          {c.cpses.map((p) => (
            <Chip key={p} tone="info">
              {p}
            </Chip>
          ))}
        </span>
      </div>
      {c.conflicts.length > 0 && (
        <p className="mt-2 text-label font-normal text-ne-fg">
          Looks similar ({Math.round(c.text_sim * 100)}% text), but{" "}
          {c.conflicts.map((x) => ATTR_LABEL[x] ?? x).join(", ")} differs: a different item.
        </p>
      )}
      <button
        type="button"
        className="mt-2 text-label text-primary hover:underline"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        {open ? "Hide evidence" : "Show evidence"}
      </button>
      {open && (
        <div className="mt-2">
          <EvidenceCard rows={c.evidence} labelA="Your text" labelB={c.cnmc} />
        </div>
      )}
    </Card>
  );
}
