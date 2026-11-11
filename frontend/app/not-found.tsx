import Link from "next/link";

export default function NotFound() {
  return (
    <div className="page-content">
      <section className="panel no-assessment-panel">
        <div className="no-assessment-icon">404</div>
        <h2>Page not found</h2>
        <p>The page you requested does not exist in this workspace.</p>
        <Link href="/" className="button button-primary">Return to overview</Link>
      </section>
    </div>
  );
}
