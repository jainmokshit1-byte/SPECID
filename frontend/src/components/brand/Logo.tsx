/** SpecID mark: three differently written records (left strokes) resolving into one verified
 * specification (the checked block). Inline SVG, so it is bundled and works offline. */
export function LogoMark({ size = 22 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      className="shrink-0"
    >
      <rect x="1" y="1" width="22" height="22" rx="6" className="fill-primary" />
      <path
        d="M5 7.5h4.5M5 12h3M5 16.5h4"
        className="stroke-on-primary"
        strokeWidth="1.8"
        strokeLinecap="round"
        opacity="0.7"
      />
      <path
        d="M10.5 7.5 13 12l-2.5 4.5"
        className="stroke-on-primary"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.85"
      />
      <rect x="13.6" y="8" width="6.4" height="8" rx="1.6" className="fill-on-primary" />
      <path
        d="m15.3 12.1 1.2 1.2 2.1-2.4"
        className="stroke-primary"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function Wordmark() {
  return (
    <span className="flex items-center gap-2">
      <LogoMark />
      <span className="text-h3 tracking-tight text-text">
        Spec<span className="text-primary">ID</span>
      </span>
    </span>
  );
}
