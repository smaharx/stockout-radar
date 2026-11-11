"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, Download, Search, SlidersHorizontal } from "lucide-react";
import { apiGet } from "@/lib/api";
import type { ForecastListResponse } from "@/lib/types";
import { formatDate, formatDemand, formatNumber } from "@/lib/format";
import { PageHeading } from "@/components/page-heading";
import { HistoricalNotice, ErrorNotice } from "@/components/notice";
import { TableLoading } from "@/components/loading";

const PAGE_SIZE = 25;

export default function ForecastsPage() {
  const [data, setData] = useState<ForecastListResponse | null>(null);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshTick, setRefreshTick] = useState(0);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(0);
    }, 250);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(page * PAGE_SIZE) });
      if (search) params.set("search", search);
      try {
        const result = await apiGet<ForecastListResponse>(`/api/backend/v1/forecasts?${params.toString()}`);
        if (active) setData(result);
      } catch (reason) {
        if (active) setError(reason instanceof Error ? reason.message : "Forecasts could not be loaded.");
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => { active = false; };
  }, [page, search, refreshTick]);

  const totalPages = Math.max(1, Math.ceil((data?.total ?? 0) / PAGE_SIZE));
  const firstRecord = data?.total ? page * PAGE_SIZE + 1 : 0;
  const lastRecord = Math.min((page + 1) * PAGE_SIZE, data?.total ?? 0);
  const startWeek = data?.items[0]?.forecast_start_week;

  function downloadCurrentPage() {
    if (!data) return;
    const columns = ["stock_code", "history_through_week", "forecast_start_week", "forecast_4week_demand", "raw_model_prediction", "prediction_was_clipped", "model_artifact"];
    const rows = data.items.map((item) => [item.stock_code, item.history_through_week, item.forecast_start_week, item.forecast_4week_demand, item.raw_model_prediction, item.prediction_was_clipped, item.model_artifact]);
    const csv = [columns, ...rows].map((row) => row.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(",")).join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `stockout-radar-forecasts-page-${page + 1}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="page-content">
      <PageHeading
        eyebrow="DEMAND INTELLIGENCE"
        title="Demand forecasts"
        description="Explore product-level four-week demand forecasts from the active model run."
        actions={<button className="button button-secondary" onClick={downloadCurrentPage} disabled={!data?.items.length}><Download size={15} /> Export page</button>}
      />
      <HistoricalNotice date={formatDate(startWeek)} />
      {error && <ErrorNotice message={error} onRetry={() => setRefreshTick((current) => current + 1)} />}

      <section className="panel table-panel page-table-panel">
        <div className="table-toolbar">
          <div className="table-toolbar-title">
            <div className="toolbar-icon"><SlidersHorizontal size={16} /></div>
            <div><strong>Product forecast catalog</strong><span>{data ? `${formatNumber(data.total, 0)} products · run #${data.forecast_run_id}` : "Loading forecast catalog"}</span></div>
          </div>
          <label className="search-field">
            <Search size={16} />
            <input value={searchInput} onChange={(event) => setSearchInput(event.target.value)} placeholder="Search product code…" aria-label="Search product code" />
            {searchInput && <button type="button" onClick={() => setSearchInput("")} aria-label="Clear search">×</button>}
          </label>
        </div>
        {loading ? <TableLoading columns={6} /> : data?.items.length ? (
          <>
            <div className="table-scroll">
              <table className="data-table">
                <thead><tr><th>Product code</th><th>History through</th><th>Forecast begins</th><th className="align-right">4-week demand</th><th className="align-right">Raw model output</th><th>Model handling</th></tr></thead>
                <tbody>
                  {data.items.map((item) => (
                    <tr key={item.stock_code}>
                      <td><div className="product-cell"><span className="product-code-icon"><span className="code-dot" /></span><strong>{item.stock_code}</strong></div></td>
                      <td className="muted-cell">{formatDate(item.history_through_week)}</td>
                      <td className="muted-cell">{formatDate(item.forecast_start_week)}</td>
                      <td className="align-right numeric-cell demand-cell">{formatDemand(item.forecast_4week_demand)} <small>units</small></td>
                      <td className="align-right numeric-cell">{formatNumber(item.raw_model_prediction, 3)}</td>
                      <td>{item.prediction_was_clipped ? <span className="table-tag tag-info">Clipped at zero</span> : <span className="table-tag tag-neutral">Unmodified</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="table-pagination">
              <span>Showing <strong>{firstRecord}–{lastRecord}</strong> of <strong>{formatNumber(data.total, 0)}</strong> products</span>
              <div className="pagination-controls">
                <button className="button button-secondary button-small" disabled={page === 0} onClick={() => setPage((current) => Math.max(0, current - 1))}><ArrowLeft size={14} /> Previous</button>
                <span className="page-counter">Page {page + 1} of {totalPages}</span>
                <button className="button button-secondary button-small" disabled={page + 1 >= totalPages} onClick={() => setPage((current) => Math.min(totalPages - 1, current + 1))}>Next <ArrowRight size={14} /></button>
              </div>
            </div>
          </>
        ) : (
          <div className="empty-table-state"><Search size={22} /><strong>{search ? "No matching products" : "No forecasts available"}</strong><p>{search ? `No product codes matched “${search}”. Try a different search.` : "Generate and load a forecast run before browsing this catalog."}</p></div>
        )}
      </section>
      <div className="page-footnote"><span className="footnote-marker">i</span> The model produces one aggregate demand estimate for the next four weeks. The current dataset does not provide separate weekly forecasts or live inventory feeds.</div>
    </div>
  );
}
