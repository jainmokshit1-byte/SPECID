/** Health score 0-100 as a ring, with the number in the middle (S3, dashboard). */
export function HealthRing({
  score,
  size = 112,
  label = "Health",
}: {
  score: number | null;
  size?: number;
  label?: string;
}) {
  const r = 42;
  const c = 2 * Math.PI * r;
  const v = score === null ? 0 : Math.max(0, Math.min(100, score));
  const tone =
    score === null
      ? "stroke-border"
      : v >= 90
        ? "stroke-eq-fg"
        : v >= 70
          ? "stroke-ins-fg"
          : "stroke-ne-fg";
  return (
    <figure
      className="relative inline-flex shrink-0 items-center justify-center"
      style={{ width: size, height: size }}
      role="img"
      aria-label={score === null ? `${label}: not available` : `${label} ${v} of 100`}
    >
      <svg viewBox="0 0 100 100" width={size} height={size} className="-rotate-90">
        <circle cx="50" cy="50" r={r} fill="none" strokeWidth="9" className="stroke-surface-2" />
        <circle
          cx="50"
          cy="50"
          r={r}
          fill="none"
          strokeWidth="9"
          strokeLinecap="round"
          className={`${tone} transition-[stroke-dashoffset] duration-1000 ease-out`}
          strokeDasharray={c}
          strokeDashoffset={c * (1 - v / 100)}
        />
      </svg>
      <figcaption className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="tabular text-display leading-none text-text">{score ?? "–"}</span>
        <span className="mt-1 text-micro uppercase tracking-wide text-muted">{label}</span>
      </figcaption>
    </figure>
  );
}
