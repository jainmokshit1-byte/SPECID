import { VERDICT_ORDER, VERDICTS, type Verdict } from "../../lib/verdicts";
import { Tooltip } from "./Tooltip";

// eslint-disable-next-line react-refresh/only-export-components -- pure helper, tested directly
export function pct(value: number, digits = 1): string {
  return `${(value * 100).toFixed(digits)}%`;
}

function toneFor(value: number): string {
  if (value >= 0.9) return "bg-eq-fg";
  if (value >= 0.7) return "bg-ins-fg";
  return "bg-ne-fg";
}

/** One labelled horizontal bar (0..1). Colour follows the value unless `bar` is given. */
export function Meter({
  label,
  value,
  bar,
  hint,
}: {
  label: string;
  value: number;
  bar?: string;
  hint?: string;
}) {
  const v = Math.max(0, Math.min(1, value));
  return (
    <div className="grid grid-cols-[minmax(7rem,11rem)_1fr_3.5rem] items-center gap-3 py-1">
      <span className="truncate text-body text-text" title={hint ?? label}>
        {label}
      </span>
      <span
        className="h-2 overflow-hidden rounded-full bg-surface-2"
        role="meter"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(v * 100)}
      >
        <span
          className={`block h-full rounded-full transition-[width] duration-700 ease-out ${bar ?? toneFor(v)}`}
          style={{ width: `${v * 100}%` }}
        />
      </span>
      <span className="tabular text-right text-table text-muted">{pct(v)}</span>
    </div>
  );
}

/** Verdict mix as one stacked bar with a legend; counts, never only colours. */
export function VerdictBar({
  verdicts,
  showLegend = true,
  height = "h-2.5",
}: {
  verdicts: Partial<Record<Verdict, number>>;
  showLegend?: boolean;
  height?: string;
}) {
  const total = VERDICT_ORDER.reduce((s, v) => s + (verdicts[v] ?? 0), 0);
  if (total === 0) return <span className="text-label text-muted">No pairs</span>;
  return (
    <div>
      <div className={`flex ${height} w-full overflow-hidden rounded-full bg-surface-2`}>
        {VERDICT_ORDER.map((v) => {
          const n = verdicts[v] ?? 0;
          if (!n) return null;
          return (
            <Tooltip key={v} text={`${VERDICTS[v].label}: ${n.toLocaleString("en-US")}`}>
              <span
                className={`block h-full ${VERDICTS[v].bar} transition-[width] duration-700`}
                style={{ width: `${(n / total) * 100}%` }}
              />
            </Tooltip>
          );
        })}
      </div>
      {showLegend && (
        <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
          {VERDICT_ORDER.map((v) => (
            <li key={v} className="flex items-center gap-1.5 text-label text-muted">
              <span className={`h-2 w-2 rounded-sm ${VERDICTS[v].bar}`} aria-hidden="true" />
              {VERDICTS[v].label}
              <span className="tabular text-text">
                {(verdicts[v] ?? 0).toLocaleString("en-US")}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
