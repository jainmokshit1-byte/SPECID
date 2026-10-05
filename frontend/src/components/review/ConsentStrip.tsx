import { CircleCheck, CircleX, Clock3 } from "lucide-react";
import type { Consent } from "../../api/review";
import { Tooltip } from "../ui/Tooltip";

const VIA: Record<string, string> = {
  MAKER_PROPOSAL: "by the maker's proposal",
  CHECKER_CONFIRMATION: "by the checker's confirmation",
  STEWARD: "by the CPSE steward",
};

/** ConsentStrip (UI/UX brief 6, SF-11): one chip per participating CPSE; never colour only. */
export function ConsentStrip({ consents }: { consents: Consent[] }) {
  return (
    <ul aria-label="Consent of each CPSE" className="flex flex-wrap items-center gap-1.5">
      {consents.map((c) => {
        const tip =
          c.decision === "CONSENT"
            ? `${c.cpse} consented ${VIA[c.via ?? ""] ?? ""}${c.by ? ` (${c.by})` : ""}`
            : c.decision === "DECLINE"
              ? `${c.cpse} declined: ${c.reason ?? ""}`
              : `${c.cpse} has not answered yet`;
        const [cls, Icon, word] =
          c.decision === "CONSENT"
            ? ["bg-eq-bg text-eq-fg", CircleCheck, "consented"]
            : c.decision === "DECLINE"
              ? ["bg-ne-bg text-ne-fg", CircleX, "declined"]
              : ["bg-review-bg text-review-fg", Clock3, "waiting"];
        return (
          <li key={c.cpse}>
            <Tooltip text={tip}>
              <span
                tabIndex={0}
                className={`inline-flex items-center gap-1 rounded-chip px-1.5 py-0.5 text-label ${cls}`}
              >
                <Icon size={13} strokeWidth={2} aria-hidden="true" />
                {c.cpse} <span className="font-normal">{word}</span>
              </span>
            </Tooltip>
          </li>
        );
      })}
    </ul>
  );
}
