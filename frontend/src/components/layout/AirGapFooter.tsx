import { ShieldCheck, ShieldQuestion } from "lucide-react";
import { Link } from "react-router-dom";
import { useAirGap, useHealth } from "../../hooks/useSystemStatus";

/** Footer on every page (FR-1463, FR-1504, UI/UX brief 6). Values come only from the API; until
 * /system/airgap exists (Phase 5) the footer says so instead of claiming AIR-GAPPED. */
export function AirGapFooter() {
  const airgap = useAirGap();
  const health = useHealth();

  const status = airgap.data ? (
    <span className="flex items-center gap-1.5">
      <span className="h-2 w-2 rounded-full bg-airgap-dot" aria-hidden="true" />
      <ShieldCheck size={14} strokeWidth={1.75} aria-hidden="true" />
      AIR-GAPPED · blocked attempts: {airgap.data.blocked_egress_attempts}
    </span>
  ) : (
    <span className="flex items-center gap-1.5">
      <ShieldQuestion size={14} strokeWidth={1.75} aria-hidden="true" />
      {airgap.isError ? "air-gap status: API not reachable" : "air-gap status: not available yet"}
    </span>
  );

  return (
    <footer className="flex h-bar shrink-0 items-center gap-3 bg-airgap-bg px-4 text-micro text-airgap-fg">
      {status}
      {health.data && (
        <>
          <span aria-hidden="true">·</span>
          <span>consent: {health.data.consent_mode}</span>
          <span aria-hidden="true">·</span>
          <span>v{health.data.version}</span>
          <span aria-hidden="true">·</span>
          <span className="font-mono">commit {health.data.git_commit}</span>
        </>
      )}
      <span aria-hidden="true">·</span>
      <Link to="/about" className="underline">
        About
      </Link>
    </footer>
  );
}
