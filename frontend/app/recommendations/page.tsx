"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Check, ClipboardCheck, RefreshCw, Search, ShieldCheck } from "lucide-react";
import { apiGet, apiPost, ApiError } from "@/lib/api";
import type { AssessmentResponse, Recommendation } from "@/lib/types";
import { formatDateTime, formatNumber } from "@/lib/format";
import { PageHeading } from "@/components/page-heading";
import { HistoricalNotice, ErrorNotice } from "@/components/notice";
import { TableLoading } from "@/components/loading";
import { RiskBadge } from "@/components/status-badge";
import { StatCard } from "@/components/stat-card";

export default function RecommendationsPage() {
  const [assessment, setAssessment] = useState<AssessmentResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [filter, setFilter] = useState("ALL");
  const [search, setSearch] = useState("");
  const [refreshTick, setRefreshTick] = useState(0);

  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const result = await apiGet<AssessmentResponse>("/api/backend/v1/inventory/assessment");
        if (active) setAssessment(result);
      } catch (reason) {
        if (active && reason instanceof ApiError && reason.status === 404) setAssessment(null);
        else if (active) setError(reason instanceof Error ? reason.message : "The latest assessment could not be loaded.");
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => { active = false; };
  }, [refreshTick]);

  async function runAssessment() {
    setRunning(true);
    setError(null);
    setMessage(null);
    try {
      const result = await apiPost<AssessmentResponse>("/api/backend/v1/inventory/assessment");
      setAssessment(result);
      setFilter("ALL");
      setMessage(`Assessment #${result.summary.assessment_run_id} completed successfully.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The assessment could not be completed.");
    } finally {
      setRunning(false);
    }
  }

  const rows = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return (assessment?.recommendations ?? []).filter((item) => {
      const statusMatch = filter === "ALL" || item.risk_status === filter;
      const searchMatch = !normalizedSearch || item.stock_code.toLowerCase().includes(normalizedSearch);
      return statusMatch && searchMatch;
    });
  }, [assessment, filter, search]);
  const summary = assessment?.summary;

  return (
    <div className="page-content">
      <PageHeading
        eyebrow="REPLENISHMENT DECISIONS"
        title="Reorder recommendations"
        description="Review replenishment priorities calculated from the active four-week forecast and saved inventory inputs."
        actions={
          <>
            <button className="button button-secondary" onClick={() => setRefreshTick((current) => current + 1)} disabled={loading}><RefreshCw size={15} /> Refresh</button>
            <button className="button button-primary" onClick={runAssessment} disabled={running}><ClipboardCheck size={16} /> {running ? "Running assessment…" : "Run assessment"}</button>
          </>
        }
      />
      <HistoricalNotice />
      {error && <ErrorNotice message={error} onRetry={() => setRefreshTick((current) => current + 1)} />}
      {message && <div className="success-banner" role="status"><Check size={16} /> {message}</div>}

      {loading ? <div className="recommendation-loading"><TableLoading columns={5} /></div> : summary ? (
        <>
          <div className="assessment-meta-bar">
            <div className="assessment-meta-main"><div className="assessment-meta-icon"><ShieldCheck size={17} /></div><div><strong>Assessment #{summary.assessment_run_id}</strong><span>Completed {formatDateTime(summary.created_at)} · Forecast run #{summary.forecast_run_id}</span></div></div>
            <div className="assessment-meta-count"><span>Products assessed</span><strong>{formatNumber(summary.item_count, 0)}</strong></div>
          </div>
          <div className="stats-grid recommendation-stats">
            <StatCard label="Reorder now" value={formatNumber(summary.reorder_now_count, 0)} detail="At or below calculated reorder point" icon={<AlertTriangle size={19} />} tone="red" />
            <StatCard label="Watch list" value={formatNumber(summary.watch_count, 0)} detail="Below target stock level" icon={<RefreshCw size={19} />} tone="amber" />
            <StatCard label="Healthy" value={formatNumber(summary.healthy_count, 0)} detail="At or above target stock level" icon={<ShieldCheck size={19} />} tone="green" />
            <StatCard label="Suggested replenishment" value={formatNumber(summary.total_recommended_order_qty, 0)} detail="Total units across this assessment" icon={<ClipboardCheck size={19} />} tone="blue" />
          </div>
          <section className="panel table-panel recommendation-table-panel">
            <div className="table-toolbar recommendation-toolbar">
              <div className="table-toolbar-title"><div className="toolbar-icon"><ClipboardCheck size={16} /></div><div><strong>Assessment results</strong><span>{formatNumber(rows.length, 0)} matching products</span></div></div>
              <div className="table-toolbar-controls">
                <label className="search-field recommendation-search"><Search size={16} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search product code…" aria-label="Search recommendations" /></label>
                <select className="filter-select" value={filter} onChange={(event) => setFilter(event.target.value)} aria-label="Filter by risk status">
                  <option value="ALL">All statuses</option>
                  <option value="REORDER_NOW">Reorder now</option>
                  <option value="WATCH">Watch</option>
                  <option value="HEALTHY">Healthy</option>
                </select>
              </div>
            </div>
            {rows.length ? (
              <div className="table-scroll">
                <table className="data-table recommendation-data-table">
                  <thead><tr><th>Product</th><th>Risk status</th><th className="align-right">On hand</th><th className="align-right">Lead-time demand</th><th className="align-right">Reorder point</th><th className="align-right">Target stock</th><th className="align-right">Days of cover</th><th className="align-right">Order quantity</th></tr></thead>
                  <tbody>
                    {rows.map((item) => <RecommendationRow key={item.stock_code} item={item} />)}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty-table-state"><Search size={22} /><strong>No matching recommendations</strong><p>Change the risk filter or search for another product code.</p></div>
            )}
            <div className="table-pagination recommendation-pagination"><span>Showing <strong>{rows.length}</strong> of <strong>{summary.item_count}</strong> assessed products</span><span className="muted-cell">Latest saved assessment snapshot</span></div>
          </section>
          <div className="calculation-note"><ShieldCheck size={17} /><div><strong>How these recommendations are calculated</strong><p>Average daily demand is estimated by spreading the four-week forecast evenly over 28 days. Reorder point = estimated lead-time demand + safety stock. Target stock = four-week forecast + safety stock. Lead times are limited to 28 days by the current forecast horizon.</p></div></div>
        </>
      ) : (
        <section className="panel no-assessment-panel">
          <div className="no-assessment-icon"><ClipboardCheck size={25} /></div>
          <h2>No inventory assessment has been run</h2>
          <p>Once inventory inputs have been saved, run an assessment to calculate reorder points, stock coverage and recommended order quantities.</p>
          <button className="button button-primary" onClick={runAssessment} disabled={running}><ClipboardCheck size={16} /> {running ? "Running assessment…" : "Run assessment"}</button>
          <span className="empty-helper">At least one product must have current stock, lead time and safety stock entered.</span>
        </section>
      )}
    </div>
  );
}

function RecommendationRow({ item }: { item: Recommendation }) {
  return (
    <tr>
      <td><div className="product-cell"><span className="product-code-icon"><ClipboardCheck size={14} /></span><strong>{item.stock_code}</strong></div></td>
      <td><RiskBadge status={item.risk_status} /></td>
      <td className="align-right numeric-cell">{formatNumber(item.current_stock)}</td>
      <td className="align-right numeric-cell">{formatNumber(item.estimated_lead_time_demand, 2)}</td>
      <td className="align-right numeric-cell">{formatNumber(item.reorder_point, 2)}</td>
      <td className="align-right numeric-cell">{formatNumber(item.target_stock_level, 2)}</td>
      <td className="align-right numeric-cell">{item.estimated_days_of_cover === null ? "—" : `${formatNumber(item.estimated_days_of_cover, 1)} d`}</td>
      <td className="align-right"><span className={`order-quantity ${item.recommended_order_qty > 0 ? "order-quantity-active" : ""}`}>{formatNumber(item.recommended_order_qty, 0)} units</span></td>
    </tr>
  );
}
