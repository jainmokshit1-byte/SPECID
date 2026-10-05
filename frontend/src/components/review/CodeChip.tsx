import { Check, Copy } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

/** CNMCChip (UI/UX brief 6): the code in mono, a copy button, optionally a link. */
export function CodeChip({
  code,
  link = true,
  big = false,
}: {
  code: string;
  link?: boolean;
  big?: boolean;
}) {
  const [copied, setCopied] = useState(false);
  const text = big ? "text-h2" : "text-mono";
  return (
    <span className="inline-flex items-center gap-1">
      {link ? (
        <Link to={`/registry/${code}`} className={`font-mono ${text} text-primary hover:underline`}>
          {code}
        </Link>
      ) : (
        <span className={`font-mono ${text} text-text`}>{code}</span>
      )}
      <button
        type="button"
        aria-label={`Copy ${code}`}
        onClick={() => {
          void navigator.clipboard?.writeText(code);
          setCopied(true);
          window.setTimeout(() => setCopied(false), 1500);
        }}
        className="rounded p-0.5 text-muted hover:bg-surface-2 hover:text-text"
      >
        {copied ? <Check size={14} aria-hidden="true" /> : <Copy size={14} aria-hidden="true" />}
      </button>
    </span>
  );
}
