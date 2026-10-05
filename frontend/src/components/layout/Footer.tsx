import { useAirGap, useHealth } from "../../hooks/useSystemStatus";

const CONSENT_LABEL: Record<string, string> = {
  ALL_PARTICIPANTS: "all CPSEs",
  NONE: "not required",
};

/** Slim footer (UI/UX brief 4, 6): consent mode on the left (PRD FR-1504), air-gap status on the
 * right (FR-1463, wording fixed by DEC-10). Values come only from the API: until /system/airgap
 * exists (Phase 5) it says "unavailable", never "Air-gapped". Version and commit are in /health
 * until Help (S17) exists. */
export function Footer() {
  const health = useHealth();
  return (
    <footer className="flex h-footer shrink-0 items-center gap-3 border-t border-border bg-surface px-4 text-micro text-muted">
      {health.data && (
        <span>Consent: {CONSENT_LABEL[health.data.consent_mode] ?? health.data.consent_mode}</span>
      )}
      <span className="ml-auto flex items-center gap-2">
        {health.data?.egress_guard?.enabled === false && <OffTag>GUARD OFF</OffTag>}
        {health.data?.embeddings_enabled === false && <OffTag>DENSE OFF</OffTag>}
        <AirGapStatus />
      </span>
    </footer>
  );
}

const AI_LABEL: Record<string, string> = { gemini: "Gemini (synthetic data only)", off: "off" };

export function AirGapStatus() {
  const airgap = useAirGap();
  const health = useHealth();
  // The hosted demo is online by design (DEC-41/42): never call it air-gapped.
  if (airgap.data && (airgap.data.mode === "ONLINE" || health.data?.demo_mode))
    return (
      <span className="flex items-center gap-1.5 text-text">
        <span className="h-2 w-2 rounded-full bg-auto-fg" aria-hidden="true" />
        Cloud demo · AI: {AI_LABEL[health.data?.ai_provider ?? "off"] ?? health.data?.ai_provider} ·
        outbound outside the allow-list blocked: {airgap.data.blocked_egress_attempts}
      </span>
    );
  if (airgap.data)
    return (
      <span className="flex items-center gap-1.5 text-text">
        <span className="h-2 w-2 rounded-full bg-airgap-dot" aria-hidden="true" />
        Air-gapped · blocked attempts: {airgap.data.blocked_egress_attempts}
      </span>
    );
  return (
    <span className="flex items-center gap-1.5">
      <span className="h-2 w-2 rounded-full bg-border-strong" aria-hidden="true" />
      {airgap.isError
        ? "Air-gap status unavailable: API not reachable"
        : "Air-gap status unavailable"}
    </span>
  );
}

function OffTag({ children }: { children: string }) {
  return <span className="rounded-chip bg-ins-bg px-1.5 text-ins-fg">{children}</span>;
}
