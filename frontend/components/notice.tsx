import { AlertCircle, Info } from "lucide-react";

export function ErrorNotice({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="notice notice-error" role="alert">
      <AlertCircle size={18} />
      <div><strong>Unable to load this data</strong><p>{message}</p></div>
      {onRetry && <button className="text-button" onClick={onRetry}>Try again</button>}
    </div>
  );
}

export function HistoricalNotice({ date }: { date?: string }) {
  return (
    <div className="notice notice-historical">
      <Info size={17} />
      <p>
        <strong>Historical demonstration data.</strong> Forecasts are derived from Online Retail II transactions from 2010–2011{date ? `; this forecast cycle starts ${date}` : ""}. They are not current market-demand predictions.
      </p>
    </div>
  );
}
