import { LoadingBlock } from "@/components/loading";

export default function Loading() {
  return (
    <div className="page-content" aria-label="Loading Stockout Radar" role="status">
      <div className="page-heading"><div><div className="page-eyebrow">WORKSPACE</div><h1>Loading workspace</h1><p>Preparing your inventory and forecast data.</p></div></div>
      <div className="stats-grid">{Array.from({ length: 4 }).map((_, index) => <div className="stat-card" key={index}><LoadingBlock rows={2} /></div>)}</div>
    </div>
  );
}
