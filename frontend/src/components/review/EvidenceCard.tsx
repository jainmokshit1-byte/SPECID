import { BookOpen, ChevronDown } from "lucide-react";
import { useState } from "react";
import { ATTR_LABEL, type EvidenceRow } from "../../api/review";
import { show } from "../../lib/values";
import { Tooltip } from "../ui/Tooltip";

const STATUS: Record<EvidenceRow["status"], { word: string; row: string; text: string }> = {
  MATCH: { word: "Match", row: "", text: "text-eq-fg" },
  PARTIAL: { word: "Partly known", row: "bg-ins-bg", text: "text-ins-fg" },
  MISSING_ONE: { word: "Not stated on one side", row: "bg-ins-bg", text: "text-ins-fg" },
  CONFLICT: { word: "Different (veto)", row: "bg-ne-bg", text: "text-ne-fg" },
};

/** EvidenceCard (UI/UX brief 6): reads like a diff. Decisive rows (conflicts, unknown core
 * values, flags) first, with a left bar; matches behind "Show all attributes". Each row names its
 * rule; conversions appear as mono chips under the value. */
export function EvidenceCard({
  rows,
  labelA = "A",
  labelB = "B",
}: {
  rows: EvidenceRow[];
  labelA?: string;
  labelB?: string;
}) {
  const [all, setAll] = useState(false);
  const decisive = rows.filter((r) => r.status !== "MATCH");
  const shown = all || decisive.length === 0 ? rows : decisive;
  const matches = rows.length - decisive.length;
  return (
    <div>
      <p className="mb-2 text-label font-normal text-muted">
        {matches} of {rows.length} attributes match
        {decisive.length > 0 && ` · ${decisive.length} decide the outcome`}
      </p>
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-table">
          <thead className="bg-surface-2 text-left text-label uppercase tracking-wide text-muted">
            <tr>
              <th className="px-3 py-2 font-medium">Attribute</th>
              <th className="px-3 py-2 font-medium">{labelA}</th>
              <th className="px-3 py-2 font-medium">{labelB}</th>
              <th className="px-3 py-2 font-medium">Status</th>
              <th className="px-3 py-2 font-medium">Rule</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((r) => {
              const s = STATUS[r.status];
              const decisiveRow = r.status !== "MATCH";
              return (
                <tr
                  key={r.attr}
                  className={`border-t border-border align-top ${s.row} ${
                    r.status === "CONFLICT"
                      ? "shadow-[inset_3px_0_0_var(--ne-fg)]"
                      : decisiveRow
                        ? "shadow-[inset_3px_0_0_var(--ins-fg)]"
                        : ""
                  }`}
                >
                  <td className="px-3 py-2">
                    {ATTR_LABEL[r.attr] ?? r.attr}
                    <span className="ml-1.5 text-micro uppercase text-muted">
                      {r.level === "core" ? "key" : "extra"}
                    </span>
                  </td>
                  <td
                    className={`px-3 py-2 font-mono text-mono ${r.status === "CONFLICT" ? "font-semibold text-ne-fg" : ""}`}
                  >
                    {show(r.a)}
                    {r.note_a && <NoteChip note={r.note_a} />}
                  </td>
                  <td
                    className={`px-3 py-2 font-mono text-mono ${r.status === "CONFLICT" ? "font-semibold text-ne-fg" : ""}`}
                  >
                    {show(r.b)}
                    {r.note_b && <NoteChip note={r.note_b} />}
                  </td>
                  <td className={`px-3 py-2 ${s.text}`}>{s.word}</td>
                  <td className="px-3 py-2">
                    <Tooltip text={r.rule_text}>
                      <span
                        tabIndex={0}
                        className="inline-flex items-center gap-1 font-mono text-micro text-muted"
                      >
                        <BookOpen size={12} aria-hidden="true" />
                        {r.rule}
                      </span>
                    </Tooltip>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {decisive.length > 0 && matches > 0 && (
        <button
          type="button"
          onClick={() => setAll((a) => !a)}
          aria-expanded={all}
          className="mt-2 inline-flex items-center gap-1 text-label text-muted hover:text-text"
        >
          <ChevronDown size={14} className={all ? "rotate-180" : ""} aria-hidden="true" />
          {all
            ? "Show only the deciding attributes"
            : `Show all attributes (${matches} more match)`}
        </button>
      )}
    </div>
  );
}

function NoteChip({ note }: { note: string }) {
  return (
    <span className="mt-1 block w-fit rounded-chip bg-surface-2 px-1.5 py-0.5 font-mono text-micro text-muted">
      {note}
    </span>
  );
}
