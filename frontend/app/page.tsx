"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  Boxes,
  CalendarDays,
  CircleAlert,
  ClipboardCheck,
  Package,
  RefreshCw,
  ShieldCheck,
  TrendingUp,
  Warehouse,
} from "lucide-react";
import { apiGet, apiPost } from "@/lib/api";
import type {
  AssessmentResponse,
  ForecastListResponse,
  HealthResponse,
  InventoryItem,
  ProductListResponse,
} from "@/lib/types";
import { formatDate, formatDateTime, formatDemand, formatNumber } from "@/lib/format";
import { PageHeading } from "@/components/page-heading";
import { StatCard } from "@/components/stat-card";
import { ConnectionBadge, RiskBadge } from "@/components/status-badge";
import { ErrorNotice, HistoricalNotice } from "@/components/notice";
import { LoadingBlock, TableLoading } from "@/components/loading";

type DashboardResults = [
  PromiseSettledResult<HealthResponse>,
  PromiseSettledResult<ProductListResponse>,
  PromiseSettledResult<InventoryItem[]>,
  PromiseSettledResult<ForecastListResponse>,
  PromiseSettledResult<AssessmentResponse>,
];

function fetchDashboardData(): Promise<DashboardResults> {
  return Promise.allSettled([
    apiGet<HealthResponse>("/api/backend/v1/health"),
    apiGet<ProductListResponse>("/api/backend/v1/products?limit=6"),
    apiGet<InventoryItem[]>("/api/backend/v1/inventory"),
    apiGet<ForecastListResponse>("/api/backend/v1/forecasts?limit=1"),
    apiGet<AssessmentResponse>("/api/backend/v1/inventory/assessment"),
  ] as const);
}

export default function OverviewPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [products, setProducts] = useState<ProductListResponse | null>(null);
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [forecast, setForecast] = useState<ForecastListResponse | null>(null);
  const [assessment, setAssessment] = useState<AssessmentResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [runningAssessment, setRunningAssessment] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const applyDashboardResults = useCallback((results: DashboardResults) => {
    const [
      healthResult,
      productsResult,
      inventoryResult,
      forecastResult,
      assessmentResult,
    ] = results;

    if (healthResult.status === "fulfilled") setHealth(healthResult.value);
    else setHealth(null);

    if (productsResult.status === "fulfilled") setProducts(productsResult.value);
    if (inventoryResult.status === "fulfilled") setInventory(inventoryResult.value);
    if (forecastResult.status === "fulfilled") setForecast(forecastResult.value);

    if (assessmentResult.status === "fulfilled") {
      setAssessment(assessmentResult.value);
    } else {
      setAssessment(null);
    }

    const failures = [
      healthResult,
      productsResult,
      inventoryResult,
      forecastResult,
    ].filter((result) => result.status === "rejected") as PromiseRejectedResult[];

    if (failures.length) {
      setError(
        failures[0].reason instanceof Error
          ? failures[0].reason.message
          : "One or more dashboard data sources could not be loaded."
      );
    }
  }, []);

  const loadDashboard = useCallback(async () => {
    const results = await fetchDashboardData();

    applyDashboardResults(results);
    setLoading(false);
    setRefreshing(false);
  }, [applyDashboardResults]);

  useEffect(() => {
    let cancelled = false;

    void fetchDashboardData()
      .then((results) => {
        if (cancelled) return;

        applyDashboardResults(results);
        setLoading(false);
      })
      .catch((reason: unknown) => {
        if (cancelled) return;

        setError(
          reason instanceof Error
            ? reason.message
            : "The dashboard could not be loaded."
        );
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [applyDashboardResults]);

  function handleRefresh() {
    setRefreshing(true);
    setError(null);
    void loadDashboard();
  }

  async function handleRunAssessment() {
    setRunningAssessment(true);
    setMessage(null);
    setError(null);
    try {
      const result = await apiPost<AssessmentResponse>("/api/backend/v1/inventory/assessment");
      setAssessment(result);
      setMessage(`Assessment ${result.summary.assessment_run_id} completed for ${result.summary.item_count} inventory items.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The inventory assessment could not be completed.");
    } finally {
      setRunningAssessment(false);
    }
  }

  const summary = assessment?.summary;
  const forecastStart = forecast?.items[0]?.forecast_start_week ?? products?.items[0]?.forecast_start_week;
  const recommendations = assessment?.recommendations.slice(0, 5) ?? [];
  const priorityCount = summary?.reorder_now_count ?? 0;
  const totalTracked = inventory.length;

  return (
    <div className="page-content">
      <PageHeading
        eyebrow="OPERATIONS OVERVIEW"
        title="Inventory operations overview"
        description="Monitor demand signals, review stock exposure and act on replenishment priorities."
        actions={
          <>
            <button className="button button-secondary" onClick={handleRefresh} disabled={refreshing}>
              <RefreshCw size={15} className={refreshing ? "spin" : ""} />
              Refresh
            </button>
            <button className="button button-primary" onClick={handleRunAssessment} disabled={runningAssessment || totalTracked === 0}>
              <ClipboardCheck size={16} />
              {runningAssessment ? "Assessing…" : "Run assessment"}
            </button>
          </>
        }
      />

      <div className="dashboard-status-row">
        <ConnectionBadge connected={health ? health.status === "ok" && health.database === "connected" : error ? false : null} />
        <span className="status-divider" />
        <span className="status-meta"><CalendarDays size={14} /> Forecast cycle: {formatDate(forecastStart)}</span>
        <span className="status-meta"><ShieldCheck size={14} /> Model: {forecast?.items[0]?.model_artifact ?? "Stockout Radar"}</span>
      </div>

      <HistoricalNotice date={formatDate(forecastStart)} />
      {error && <ErrorNotice message={error} onRetry={handleRefresh} />}
      {message && <div className="success-banner" role="status"><ShieldCheck size={16} /> {message}</div>}

      <div className="section-heading-row section-heading-spaced">
        <div>
          <h2>Inventory snapshot</h2>
          <p>Key indicators from the active forecast and latest assessment.</p>
        </div>
        <span className="as-of-label">{summary ? `Assessment #${summary.assessment_run_id}` : "Awaiting first assessment"}</span>
      </div>

      <div className="stats-grid">
        {loading ? (
          <>{Array.from({ length: 4 }).map((_, index) => <div className="stat-card stat-card-skeleton" key={index}><LoadingBlock rows={2} /></div>)}</>
        ) : (
          <>
            <StatCard label="Products in catalog" value={products ? formatNumber(products.total, 0) : "—"} detail="Products with an active four-week forecast" icon={<Package size={19} />} tone="blue" />
            <StatCard label="Inventory tracked" value={formatNumber(totalTracked, 0)} detail="Products with operator-supplied stock data" icon={<Warehouse size={19} />} tone="green" />
            <StatCard label="Reorder required" value={formatNumber(priorityCount, 0)} detail={summary ? `${summary.watch_count} watch · ${summary.healthy_count} healthy` : "Run an assessment to calculate risk"} icon={<CircleAlert size={19} />} tone="red" />
            <StatCard label="Suggested order quantity" value={formatNumber(summary?.total_recommended_order_qty ?? 0, 0)} detail="Units across the latest assessment" icon={<Boxes size={19} />} tone="amber" />
          </>
        )}
      </div>

      <div className="dashboard-grid-main">
        <section className="panel risk-panel">
          <div className="panel-heading">
            <div>
              <h3>Inventory risk profile</h3>
              <p>Distribution across the latest completed assessment.</p>
            </div>
            <Link href="/recommendations" className="panel-link">View recommendations <ArrowUpRight size={14} /></Link>
          </div>
          {loading ? <LoadingBlock rows={4} /> : summary ? (
            <>
              <div className="risk-total-block">
                <div className="risk-total-value">{formatNumber(summary.item_count, 0)}</div>
                <div><strong>Items assessed</strong><span>Assessment #{summary.assessment_run_id} · {formatDateTime(summary.created_at)}</span></div>
              </div>
              <div className="risk-stacked-bar" aria-label={`${summary.reorder_now_count} reorder now, ${summary.watch_count} watch, ${summary.healthy_count} healthy`}>
                {summary.reorder_now_count > 0 && <span className="risk-segment segment-danger" style={{ width: `${(summary.reorder_now_count / Math.max(summary.item_count, 1)) * 100}%` }} />}
                {summary.watch_count > 0 && <span className="risk-segment segment-watch" style={{ width: `${(summary.watch_count / Math.max(summary.item_count, 1)) * 100}%` }} />}
                {summary.healthy_count > 0 && <span className="risk-segment segment-healthy" style={{ width: `${(summary.healthy_count / Math.max(summary.item_count, 1)) * 100}%` }} />}
              </div>
              <div className="risk-legend-list">
                <div><span className="legend-label"><i className="legend-dot dot-danger" /> Reorder now</span><strong>{summary.reorder_now_count}</strong></div>
                <div><span className="legend-label"><i className="legend-dot dot-watch" /> Watch</span><strong>{summary.watch_count}</strong></div>
                <div><span className="legend-label"><i className="legend-dot dot-healthy" /> Healthy</span><strong>{summary.healthy_count}</strong></div>
              </div>
            </>
          ) : (
            <div className="empty-inline">
              <div className="empty-icon"><Activity size={20} /></div>
              <strong>No inventory assessment yet</strong>
              <p>Add inventory quantities, then run an assessment to see risk distribution here.</p>
              <Link href="/inventory" className="button button-secondary button-small">Set up inventory <ArrowRight size={14} /></Link>
            </div>
          )}
        </section>

        <section className="panel model-panel">
          <div className="panel-heading">
            <div>
              <h3>Forecast coverage</h3>
              <p>Active model run details.</p>
            </div>
            <div className="panel-heading-icon"><TrendingUp size={18} /></div>
          </div>
          {loading ? <LoadingBlock rows={3} /> : (
            <div className="model-details">
              <div className="model-detail-row"><span>Forecast run</span><strong>{forecast?.forecast_run_id ? `#${forecast.forecast_run_id}` : "—"}</strong></div>
              <div className="model-detail-row"><span>Forecast horizon</span><strong>4 weeks</strong></div>
              <div className="model-detail-row"><span>Forecast start</span><strong>{formatDate(forecastStart)}</strong></div>
              <div className="model-detail-row"><span>Forecast records</span><strong>{products ? formatNumber(products.total, 0) : "—"}</strong></div>
              <div className="model-detail-row"><span>Model artifact</span><strong className="model-artifact">{forecast?.items[0]?.model_artifact ?? "—"}</strong></div>
            </div>
          )}
          <Link href="/forecasts" className="model-panel-footer">Explore demand forecasts <ArrowRight size={15} /></Link>
        </section>
      </div>

      <div className="section-heading-row section-heading-spaced table-section-heading">
        <div>
          <h2>Priority replenishment</h2>
          <p>Products flagged for action in the latest assessment.</p>
        </div>
        <Link href="/recommendations" className="button button-secondary button-small">View all <ArrowRight size={14} /></Link>
      </div>

      <section className="panel table-panel">
        {loading ? <TableLoading columns={6} /> : recommendations.length ? (
          <div className="table-scroll">
            <table className="data-table">
              <thead><tr><th>Product</th><th>Risk status</th><th className="align-right">On hand</th><th className="align-right">4-week demand</th><th className="align-right">Reorder point</th><th className="align-right">Order quantity</th><th /></tr></thead>
              <tbody>
                {recommendations.map((item) => (
                  <tr key={item.stock_code}>
                    <td><div className="product-cell"><span className="product-code-icon"><Package size={15} /></span><strong>{item.stock_code}</strong></div></td>
                    <td><RiskBadge status={item.risk_status} /></td>
                    <td className="align-right numeric-cell">{formatNumber(item.current_stock)}</td>
                    <td className="align-right numeric-cell">{formatDemand(item.forecast_4week_demand)}</td>
                    <td className="align-right numeric-cell">{formatNumber(item.reorder_point, 2)}</td>
                    <td className="align-right"><span className="order-quantity">{formatNumber(item.recommended_order_qty, 0)} units</span></td>
                    <td><Link href="/recommendations" className="row-arrow" aria-label={`View recommendation for ${item.stock_code}`}><ArrowUpRight size={16} /></Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-table-state">
            <ClipboardCheck size={22} />
            <strong>{summary ? "No products currently require attention" : "No recommendations to display"}</strong>
            <p>{summary ? "Your latest assessment did not produce a reorder queue." : "Add inventory details and run an assessment to generate replenishment recommendations."}</p>
            <Link href="/inventory" className="text-link">Manage inventory <ArrowRight size={14} /></Link>
          </div>
        )}
      </section>

      <div className="dashboard-bottom-grid">
        <section className="panel catalog-panel">
          <div className="panel-heading">
            <div><h3>Forecast catalog sample</h3><p>A sample of products in the active catalog.</p></div>
            <Link href="/forecasts" className="panel-link">Browse catalog <ArrowUpRight size={14} /></Link>
          </div>
          {loading ? <TableLoading columns={2} /> : products?.items.length ? (
            <div className="catalog-list">
              {products.items.slice(0, 5).map((item) => (
                <div className="catalog-row" key={item.stock_code}>
                  <div><strong>{item.stock_code}</strong><span>Starts {formatDate(item.forecast_start_week)}</span></div>
                  <strong className="catalog-demand">{formatDemand(item.forecast_4week_demand)} <small>units</small></strong>
                </div>
              ))}
            </div>
          ) : <div className="empty-copy">No product forecasts are available.</div>}
        </section>
        <section className="panel inventory-summary-panel">
          <div className="panel-heading">
            <div><h3>Inventory workspace</h3><p>Operator-managed stock parameters.</p></div>
            <div className="panel-heading-icon"><Warehouse size={18} /></div>
          </div>
          {loading ? <LoadingBlock rows={3} /> : (
            <>
              <div className="inventory-summary-number">{formatNumber(totalTracked, 0)}<span> tracked products</span></div>
              <p className="inventory-summary-description">Inventory quantities, supplier lead times and safety-stock buffers are supplied by the operator. They are not inferred from the historical sales dataset.</p>
              <Link href="/inventory" className="button button-primary button-full">Manage inventory <ArrowRight size={15} /></Link>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
