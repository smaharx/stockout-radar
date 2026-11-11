export type HealthResponse = {
  status: string;
  database: string;
};

export type Product = {
  stock_code: string;
  forecast_4week_demand: number;
  forecast_start_week: string;
};

export type ProductListResponse = {
  items: Product[];
  total: number;
};

export type Forecast = {
  stock_code: string;
  history_through_week: string;
  forecast_start_week: string;
  raw_model_prediction: number;
  forecast_4week_demand: number;
  prediction_was_clipped: boolean;
  forecast_horizon_weeks: number;
  model_artifact: string;
};

export type ForecastListResponse = {
  items: Forecast[];
  total: number;
  forecast_run_id: number;
};

export type InventoryItem = {
  stock_code: string;
  current_stock: number;
  lead_time_days: number;
  safety_stock: number;
  updated_at: string;
};

export type InventoryWrite = {
  current_stock: number;
  lead_time_days: number;
  safety_stock: number;
};

export type Recommendation = {
  stock_code: string;
  current_stock: number;
  lead_time_days: number;
  safety_stock: number;
  forecast_4week_demand: number;
  average_daily_demand: number;
  estimated_lead_time_demand: number;
  reorder_point: number;
  target_stock_level: number;
  estimated_days_of_cover: number | null;
  reorder_required: boolean;
  risk_status: "REORDER_NOW" | "WATCH" | "HEALTHY" | string;
  recommended_order_qty: number;
  demand_estimation_method: string;
};

export type AssessmentSummary = {
  assessment_run_id: number;
  forecast_run_id: number;
  created_at: string;
  item_count: number;
  reorder_now_count: number;
  watch_count: number;
  healthy_count: number;
  total_recommended_order_qty: number;
};

export type AssessmentResponse = {
  summary: AssessmentSummary;
  recommendations: Recommendation[];
};
