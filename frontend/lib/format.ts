export function formatNumber(value: number, maximumFractionDigits = 1): string {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits,
    minimumFractionDigits: 0,
  }).format(value);
}

export function formatDemand(value: number): string {
  if (value > 0 && value < 0.01) return "<0.01";
  return formatNumber(value, 2);
}

export function formatDate(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(`${value.slice(0, 10)}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

export function formatDateTime(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function titleFromPath(path: string): string {
  if (path.startsWith("/forecasts")) return "Demand forecasts";
  if (path.startsWith("/inventory")) return "Inventory management";
  if (path.startsWith("/recommendations")) return "Reorder recommendations";
  return "Overview";
}
