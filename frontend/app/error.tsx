"use client";

import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error("Stockout Radar frontend error:", error);
  }, [error]);

  return (
    <div className="page-content">
      <section className="panel no-assessment-panel">
        <div className="no-assessment-icon"><AlertTriangle size={24} /></div>
        <h2>Something went wrong</h2>
        <p>The dashboard encountered an unexpected error. Your saved inventory and assessment records have not been changed by this screen.</p>
        <button className="button button-primary" onClick={reset}>Try again</button>
      </section>
    </div>
  );
}
