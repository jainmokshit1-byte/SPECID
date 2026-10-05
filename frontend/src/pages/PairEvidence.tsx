import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { type PairSide, getPair } from "../api/review";
import { EvidenceCard } from "../components/review/EvidenceCard";
import { Chip, VerdictBadge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { ProblemAlert } from "../components/ui/Form";
import { PageHeader } from "../components/ui/PageHeader";
import { StatTile } from "../components/ui/StatTile";
import { SkeletonRows } from "../components/ui/States";

/** S7 Pair evidence (App Flow 5.7): one pair, both raw texts, the evidence card, text
 * similarity, look-alike class and both text baselines. Deep-linkable for a judge or auditor. */
export function PairEvidence() {
  const { pairId = "" } = useParams();
  const q = useQuery({ queryKey: ["pair", pairId], queryFn: () => getPair(pairId) });
  const header = (
    <PageHeader
      title="Pair evidence"
      purpose="Why SpecID decided what it did for these two records, attribute by attribute."
    />
  );
  if (q.isPending || q.error)
    return (
      <section className="max-w-6xl">
        {header}
        {q.error ? <ProblemAlert error={q.error} /> : <SkeletonRows rows={6} />}
      </section>
    );
  const p = q.data;
  const label = (s: PairSide) => `${s.cpse} ${s.legacy_code}`;
  return (
    <section className="max-w-6xl">
      {header}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <VerdictBadge verdict={p.verdict} />
        {p.reasons.map((r) => (
          <Chip key={r} tone="warn">
            {r}
          </Chip>
        ))}
        {p.lookalike === "LOOKALIKE_VETOED" && <Chip tone="bad">Look-alike, blocked</Chip>}
        {p.lookalike === "HIDDEN_TWIN" && <Chip tone="good">Hidden twin</Chip>}
      </div>
      <div className="mb-5 grid gap-3 md:grid-cols-2">
        {[p.a, p.b].map((s) => (
          <Card key={s.record_id}>
            <span className="flex items-center gap-2">
              <Chip tone="info">{s.cpse}</Chip>
              <span className="font-mono text-mono text-muted">{s.legacy_code}</span>
            </span>
            <p className="mt-2 font-mono text-mono text-text">{s.long_text || s.short_text}</p>
            {(s.manufacturer || s.mpn) && (
              <p className="mt-1 text-micro text-muted">
                {s.manufacturer} {s.mpn}
              </p>
            )}
          </Card>
        ))}
      </div>
      <div className="mb-5 grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile
          label="Text similarity"
          value={p.text_sim !== null ? `${Math.round(p.text_sim * 100)}%` : "–"}
          sub="of the cleaned texts"
        />
        <StatTile
          label="Confidence (heuristic)"
          value={p.p_equiv !== null ? p.p_equiv.toFixed(2) : "–"}
          sub="never changes a verdict"
        />
        <StatTile
          label="Text-only baseline"
          value={p.baseline ? (p.baseline.b1 ? "Same" : "Different") : "–"}
          sub={p.baseline ? `B1 at ${p.baseline.tau1}` : undefined}
        />
        <StatTile
          label="Text + numbers"
          value={p.baseline ? (p.baseline.b2 ? "Same" : "Different") : "–"}
          sub={p.baseline ? `B2 at ${p.baseline.tau2}` : undefined}
        />
      </div>
      <Card title="Evidence" hint={`Template version ${p.template_version ?? "–"}`}>
        <EvidenceCard rows={p.evidence} labelA={label(p.a)} labelB={label(p.b)} />
      </Card>
    </section>
  );
}
