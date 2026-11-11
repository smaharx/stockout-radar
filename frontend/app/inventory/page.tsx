"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Check, ChevronDown, PackagePlus, Pencil, Plus, RefreshCw, Search, ShieldCheck, Warehouse } from "lucide-react";
import { apiGet, apiPut } from "@/lib/api";
import type { InventoryItem, InventoryWrite, Product, ProductListResponse } from "@/lib/types";
import { formatDateTime, formatDemand, formatNumber } from "@/lib/format";
import { PageHeading } from "@/components/page-heading";
import { ErrorNotice, HistoricalNotice } from "@/components/notice";
import { TableLoading } from "@/components/loading";

const emptyForm = { stock_code: "", current_stock: "", lead_time_days: "7", safety_stock: "0" };

export default function InventoryPage() {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [productSearch, setProductSearch] = useState("");
  const [productMatches, setProductMatches] = useState<{ query: string; items: Product[] }>({ query: "", items: [] });
  const [selectedForecast, setSelectedForecast] = useState<Product | null>(null);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [refreshTick, setRefreshTick] = useState(0);

  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true);
      try {
        const result = await apiGet<InventoryItem[]>("/api/backend/v1/inventory");
        if (active) { setItems(result); setError(null); }
      } catch (reason) {
        if (active) setError(reason instanceof Error ? reason.message : "Inventory records could not be loaded.");
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => { active = false; };
  }, [refreshTick]);

  useEffect(() => {
    const query = productSearch.trim();
    if (query.length < 1 || selectedForecast?.stock_code === query) {
      return;
    }
    let active = true;
    const timer = window.setTimeout(async () => {
      try {
        const result = await apiGet<ProductListResponse>(`/api/backend/v1/products?search=${encodeURIComponent(query)}&limit=8`);
        if (active) setProductMatches({ query, items: result.items });
      } catch {
        if (active) setProductMatches({ query, items: [] });
      }
    }, 220);
    return () => { active = false; window.clearTimeout(timer); };
  }, [productSearch, selectedForecast]);

  function chooseProduct(product: Product) {
    setForm((current) => ({ ...current, stock_code: product.stock_code }));
    setProductSearch(product.stock_code);
    setSelectedForecast(product);
    setShowSuggestions(false);
  }

  function editItem(item: InventoryItem) {
    setForm({
      stock_code: item.stock_code,
      current_stock: String(item.current_stock),
      lead_time_days: String(item.lead_time_days),
      safety_stock: String(item.safety_stock),
    });
    setProductSearch(item.stock_code);
    setSelectedForecast(null);
    setMessage(`Editing inventory inputs for ${item.stock_code}.`);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setMessage(null);
    const payload: InventoryWrite = {
      current_stock: Number(form.current_stock),
      lead_time_days: Number(form.lead_time_days),
      safety_stock: Number(form.safety_stock),
    };
    try {
      const saved = await apiPut<InventoryItem>(`/api/backend/v1/inventory/${encodeURIComponent(form.stock_code.trim())}`, payload);
      setMessage(`Inventory for product ${saved.stock_code} was saved successfully.`);
      setForm(emptyForm);
      setProductSearch("");
      setSelectedForecast(null);
      setRefreshTick((current) => current + 1);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Inventory could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  const visibleProductMatches =
    productMatches.query === productSearch.trim() &&
    selectedForecast?.stock_code !== productSearch.trim()
      ? productMatches.items
      : [];
  const safetyUnits = items.reduce((sum, item) => sum + item.safety_stock, 0);
  const averageLeadTime = items.length ? items.reduce((sum, item) => sum + item.lead_time_days, 0) / items.length : 0;

  return (
    <div className="page-content">
      <PageHeading
        eyebrow="STOCK CONTROL"
        title="Inventory management"
        description="Maintain operator-supplied stock quantities, replenishment lead times and safety buffers."
        actions={<button className="button button-secondary" onClick={() => setRefreshTick((current) => current + 1)} disabled={loading}><RefreshCw size={15} /> Refresh records</button>}
      />
      <HistoricalNotice />
      {error && <ErrorNotice message={error} onRetry={() => setRefreshTick((current) => current + 1)} />}
      {message && <div className="success-banner" role="status"><Check size={16} /> {message}</div>}

      <div className="inventory-workspace-grid">
        <section className="panel inventory-form-panel">
          <div className="panel-heading panel-heading-form">
            <div className="panel-heading-icon panel-heading-icon-blue"><PackagePlus size={18} /></div>
            <div><h3>Add or update inventory</h3><p>Enter verified stock data for a product in the forecast catalog.</p></div>
          </div>
          <form className="inventory-form" onSubmit={handleSubmit}>
            <div className="field-group field-autocomplete">
              <label htmlFor="stock-code">Product code <span className="required-mark">*</span></label>
              <div className="input-with-icon">
                <Search size={16} />
                <input
                  id="stock-code"
                  required
                  maxLength={100}
                  autoComplete="off"
                  placeholder="Search a product code"
                  value={productSearch}
                  onFocus={() => setShowSuggestions(true)}
                  onChange={(event) => {
                    setProductSearch(event.target.value);
                    setForm((current) => ({ ...current, stock_code: event.target.value.trim() }));
                    setSelectedForecast(null);
                    setShowSuggestions(true);
                  }}
                />
                <ChevronDown size={15} className="input-trailing-icon" />
              </div>
              {showSuggestions && visibleProductMatches.length > 0 && (
                <div className="suggestion-list" role="listbox" aria-label="Matching products">
                  {visibleProductMatches.map((product) => (
                    <button type="button" key={product.stock_code} onClick={() => chooseProduct(product)}>
                      <span><strong>{product.stock_code}</strong><small>Four-week forecast</small></span>
                      <b>{formatDemand(product.forecast_4week_demand)} units</b>
                    </button>
                  ))}
                </div>
              )}
              <span className="field-hint">Choose a result from the forecast catalog. The product must have an active forecast.</span>
              {selectedForecast && <div className="selected-product-note"><ShieldCheck size={14} /> Active forecast found · {formatDemand(selectedForecast.forecast_4week_demand)} units over four weeks</div>}
            </div>

            <div className="field-grid-two">
              <div className="field-group">
                <label htmlFor="current-stock">Current stock <span className="required-mark">*</span></label>
                <div className="input-unit"><input id="current-stock" required type="number" min="0" step="0.01" placeholder="e.g. 120" value={form.current_stock} onChange={(event) => setForm((current) => ({ ...current, current_stock: event.target.value }))} /><span>units</span></div>
              </div>
              <div className="field-group">
                <label htmlFor="lead-time">Lead time <span className="required-mark">*</span></label>
                <div className="input-unit"><input id="lead-time" required type="number" min="1" max="28" step="1" value={form.lead_time_days} onChange={(event) => setForm((current) => ({ ...current, lead_time_days: event.target.value }))} /><span>days</span></div>
              </div>
            </div>
            <div className="field-group">
              <label htmlFor="safety-stock">Safety stock <span className="required-mark">*</span></label>
              <div className="input-unit"><input id="safety-stock" required type="number" min="0" step="0.01" value={form.safety_stock} onChange={(event) => setForm((current) => ({ ...current, safety_stock: event.target.value }))} /><span>units</span></div>
              <span className="field-hint">Buffer quantity held above estimated lead-time demand.</span>
            </div>
            <div className="form-guidance"><ShieldCheck size={16} /><p>Inventory values are provided by the operator. Stockout Radar does not infer on-hand quantities from sales history.</p></div>
            <div className="form-actions">
              <button type="button" className="button button-secondary" onClick={() => { setForm(emptyForm); setProductSearch(""); setSelectedForecast(null); setMessage(null); }}>Clear form</button>
              <button type="submit" className="button button-primary" disabled={saving || !form.stock_code.trim()}><Plus size={16} /> {saving ? "Saving…" : "Save inventory"}</button>
            </div>
          </form>
        </section>

        <section className="inventory-side-column">
          <div className="panel inventory-metric-panel">
            <div className="mini-panel-title"><div className="panel-heading-icon"><Warehouse size={17} /></div><span>Inventory coverage</span></div>
            <div className="inventory-summary-number">{formatNumber(items.length, 0)}<span>products tracked</span></div>
            <div className="side-metric-divider" />
            <div className="side-metric-row"><span>Combined safety stock</span><strong>{formatNumber(safetyUnits)} units</strong></div>
            <div className="side-metric-row"><span>Average lead time</span><strong>{items.length ? `${formatNumber(averageLeadTime, 1)} days` : "—"}</strong></div>
            <div className="side-metric-row"><span>Forecast horizon</span><strong>28 days</strong></div>
          </div>
          <div className="panel method-panel">
            <div className="method-panel-icon"><ShieldCheck size={17} /></div>
            <div><strong>Input guidance</strong><p>Lead times must be between 1 and 28 days because the current forecast horizon is four weeks. Use confirmed stock counts and supplier lead times.</p></div>
          </div>
        </section>
      </div>

      <div className="section-heading-row section-heading-spaced table-section-heading">
        <div><h2>Tracked inventory</h2><p>Saved stock parameters used in inventory assessments.</p></div>
        <span className="as-of-label">{formatNumber(items.length, 0)} records</span>
      </div>
      <section className="panel table-panel">
        {loading ? <TableLoading columns={5} /> : items.length ? (
          <div className="table-scroll">
            <table className="data-table">
              <thead><tr><th>Product code</th><th className="align-right">Current stock</th><th className="align-right">Lead time</th><th className="align-right">Safety stock</th><th>Last updated</th><th /></tr></thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.stock_code}>
                    <td><div className="product-cell"><span className="product-code-icon"><Warehouse size={14} /></span><strong>{item.stock_code}</strong></div></td>
                    <td className="align-right numeric-cell">{formatNumber(item.current_stock)}</td>
                    <td className="align-right numeric-cell">{item.lead_time_days} days</td>
                    <td className="align-right numeric-cell">{formatNumber(item.safety_stock)}</td>
                    <td className="muted-cell">{formatDateTime(item.updated_at)}</td>
                    <td><button className="row-action-button" onClick={() => editItem(item)}><Pencil size={14} /> Edit</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-table-state"><Warehouse size={22} /><strong>No inventory records yet</strong><p>Add one or more products above. You can assess only products for which inventory quantities have been entered.</p></div>
        )}
      </section>
    </div>
  );
}
