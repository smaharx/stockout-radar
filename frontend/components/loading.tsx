export function LoadingBlock({ rows = 4 }: { rows?: number }) {
  return (
    <div className="loading-stack" aria-label="Loading data" role="status">
      {Array.from({ length: rows }).map((_, index) => <div className="loading-row" key={index} />)}
    </div>
  );
}

export function TableLoading({ columns = 5 }: { columns?: number }) {
  return (
    <div className="table-loading" role="status" aria-label="Loading table">
      {Array.from({ length: 5 }).map((_, row) => (
        <div className="table-loading-row" key={row} style={{ gridTemplateColumns: `repeat(${columns}, minmax(45px, 1fr))` }}>
          {Array.from({ length: columns }).map((__, col) => <span key={col} />)}
        </div>
      ))}
    </div>
  );
}
