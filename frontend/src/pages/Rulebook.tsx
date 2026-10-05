import { useQuery } from "@tanstack/react-query";
import { BookOpenCheck, ShieldAlert } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { CATEGORY_LABEL } from "../api/batches";
import { ATTR_LABEL } from "../api/review";
import { getTemplate, listTemplates } from "../api/templates";
import { Chip } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { ProblemAlert } from "../components/ui/Form";
import { PageHeader } from "../components/ui/PageHeader";
import { KeyValue, SkeletonRows } from "../components/ui/States";

const label = (a: string) => ATTR_LABEL[a] ?? a.replace(/_/g, " ");

const TIERS = [
  ["core", "Must match", "Known and equal on both sides, or no match. A conflict is a veto.", "ne"],
  [
    "extended",
    "Must not conflict",
    "Different values veto; known on one side only goes to a person.",
    "ins",
  ],
  ["tolerant", "Ignored", "Never blocks a match (paint, packaging).", "muted"],
  [
    "make",
    "Make",
    "Manufacturer and part number; never needed, never a veto on their own.",
    "muted",
  ],
] as const;

/** S10a Rulebook (App Flow 5.10, FR-401): one card per category with what must match. */
export function Rulebook() {
  const q = useQuery({ queryKey: ["templates"], queryFn: listTemplates });
  return (
    <section className="max-w-6xl">
      <PageHeader
        title="Rulebook"
        purpose="The engineering rules that decide whether two records are the same item. No score or AI model can override them."
      />
      {q.isPending ? (
        <SkeletonRows rows={4} />
      ) : q.error ? (
        <ProblemAlert error={q.error} />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {q.data.map((t) => (
            <Link
              key={t.id}
              to={`/templates/${t.id}`}
              className="group rounded-lg border border-border bg-surface p-4 shadow-sm transition hover:border-primary"
            >
              <span className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-h3">
                  <BookOpenCheck size={18} className="text-primary" aria-hidden="true" />
                  {CATEGORY_LABEL[t.category] ?? t.category}
                </span>
                <span className="text-label text-muted">v{t.version}</span>
              </span>
              <span className="mt-2 block text-label font-normal text-muted">Must match</span>
              <span className="mt-1 flex flex-wrap gap-1">
                {t.core.map((a) => (
                  <Chip key={a} tone="info">
                    {label(a)}
                  </Chip>
                ))}
              </span>
              {t.critical_default && (
                <span className="mt-3 flex items-center gap-1 text-label text-ins-fg">
                  <ShieldAlert size={14} aria-hidden="true" /> Safety-critical: always two people
                </span>
              )}
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}

/** S10b Template detail (App Flow 5.10): attribute tiers, allowed values, aliases, rule text. */
export function TemplateDetailPage() {
  const { templateId = "" } = useParams();
  const q = useQuery({
    queryKey: ["template", templateId],
    queryFn: () => getTemplate(templateId),
  });
  const t = q.data;
  return (
    <section className="max-w-6xl">
      <PageHeader
        title={t ? `Rulebook · ${CATEGORY_LABEL[t.category] ?? t.category}` : "Template detail"}
        purpose="Which attributes must match, which values are allowed, and how short forms are read."
      />
      {q.isPending ? (
        <SkeletonRows rows={6} />
      ) : q.error ? (
        <ProblemAlert error={q.error} />
      ) : (
        <div className="space-y-5">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {TIERS.map(([key, name, text, tone]) => (
              <Card key={key} title={name} hint={text}>
                <ul className="space-y-1">
                  {t![key].length === 0 ? (
                    <li className="text-body text-muted">–</li>
                  ) : (
                    t![key].map((a) => (
                      <li key={a} className={`text-body ${tone === "ne" ? "font-medium" : ""}`}>
                        {label(a)}
                        {t!.rule_text[a] && (
                          <span className="block text-micro text-muted">{t!.rule_text[a]}</span>
                        )}
                      </li>
                    ))
                  )}
                </ul>
              </Card>
            ))}
          </div>
          <div className="grid gap-5 lg:grid-cols-2">
            <Card title="Allowed values">
              {Object.entries(t!.value_domains).map(([a, vs]) => (
                <div key={a} className="py-1">
                  <span className="text-label">{label(a)}</span>
                  <span className="mt-1 flex flex-wrap gap-1">
                    {vs.map((v) => (
                      <span
                        key={String(v)}
                        className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-micro"
                      >
                        {String(v)}
                      </span>
                    ))}
                  </span>
                </div>
              ))}
            </Card>
            <Card title="Short forms read as">
              {Object.entries(t!.aliases).map(([a, m]) => (
                <div key={a} className="py-1">
                  <span className="text-label">{label(a)}</span>
                  <span className="mt-1 block font-mono text-micro text-muted">
                    {Object.entries(m)
                      .map(([k, v]) => `${k} → ${v}`)
                      .join("  ·  ")}
                  </span>
                </div>
              ))}
            </Card>
          </div>
          <Card title="Rules">
            <ul className="list-disc space-y-1 pl-5 text-body">
              {t!.rules.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
            <div className="mt-3">
              <KeyValue k="Version" v={`v${t!.version} · ${t!.status}`} />
              <KeyValue
                k="Safety-critical"
                v={t!.critical_default ? "Yes: maker and checker always" : "No"}
              />
              {t!.unspsc && <KeyValue k="UNSPSC" v={t!.unspsc} />}
            </div>
          </Card>
        </div>
      )}
    </section>
  );
}
