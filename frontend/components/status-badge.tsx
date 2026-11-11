import { AlertTriangle, CheckCircle2, Clock3 } from "lucide-react";

export function RiskBadge({ status }: { status: string }) {
  const normalized = status.toUpperCase();
  if (normalized === "REORDER_NOW") {
    return <span className="risk-badge risk-danger"><AlertTriangle size={13} /> Reorder now</span>;
  }
  if (normalized === "WATCH") {
    return <span className="risk-badge risk-watch"><Clock3 size={13} /> Watch</span>;
  }
  if (normalized === "HEALTHY") {
    return <span className="risk-badge risk-healthy"><CheckCircle2 size={13} /> Healthy</span>;
  }
  return <span className="risk-badge risk-neutral">{status.replaceAll("_", " ")}</span>;
}

export function ConnectionBadge({ connected }: { connected: boolean | null }) {
  if (connected === null) return <span className="connection-badge connection-pending"><span /> Checking API</span>;
  return connected
    ? <span className="connection-badge connection-ok"><span /> API connected</span>
    : <span className="connection-badge connection-error"><span /> API unavailable</span>;
}
