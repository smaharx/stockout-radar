"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  Activity,
  Boxes,
  ChartNoAxesCombined,
  ChevronRight,
  Command,
  Menu,
  Radar,
  ShieldCheck,
  Warehouse,
  X,
} from "lucide-react";
import { titleFromPath } from "@/lib/format";

const navigation = [
  { href: "/", label: "Overview", icon: ChartNoAxesCombined },
  { href: "/forecasts", label: "Demand forecasts", icon: Activity },
  { href: "/inventory", label: "Inventory", icon: Warehouse },
  { href: "/recommendations", label: "Reorder recommendations", icon: Boxes },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const pageTitle = titleFromPath(pathname);
  const environmentLabel =
    process.env.NODE_ENV === "production"
      ? "Production environment"
      : "Local environment";

  return (
    <div className="app-frame">
      <aside className={`sidebar ${mobileOpen ? "sidebar-open" : ""}`}>
        <div className="brand-lockup">
          <div className="brand-mark"><Radar size={23} strokeWidth={2.1} /></div>
          <div className="brand-copy">
            <span className="brand-name">Stockout<span>Radar</span></span>
            <span className="brand-subtitle">Inventory intelligence</span>
          </div>
          <button className="icon-button sidebar-close" onClick={() => setMobileOpen(false)} aria-label="Close navigation">
            <X size={18} />
          </button>
        </div>

        <div className="workspace-switcher">
          <div className="workspace-avatar"><Command size={16} /></div>
          <div className="workspace-copy">
            <span className="eyebrow">WORKSPACE</span>
            <strong>Retail operations</strong>
          </div>
          <ChevronRight size={15} className="workspace-chevron" />
        </div>

        <div className="nav-section-label">WORKSPACE</div>
        <nav className="primary-nav" aria-label="Primary navigation">
          {navigation.map((item) => {
            const Icon = item.icon;
            const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            return (
              <Link
                href={item.href}
                key={item.href}
                className={`nav-link ${active ? "nav-link-active" : ""}`}
                onClick={() => setMobileOpen(false)}
                aria-current={active ? "page" : undefined}
              >
                <Icon size={18} strokeWidth={1.9} />
                <span>{item.label}</span>
                {active && <span className="nav-active-indicator" />}
              </Link>
            );
          })}
        </nav>

        <div className="sidebar-spacer" />

        <div className="sidebar-data-card">
          <div className="data-card-icon"><ShieldCheck size={17} /></div>
          <div>
            <strong>Model data source</strong>
            <p>Online Retail II · Historical</p>
            <span className="data-card-tag">2010—2011 dataset</span>
          </div>
        </div>
        <div className="sidebar-footer">
          <div className="sidebar-footer-mark">SR</div>
          <div className="sidebar-footer-copy">
            <strong>Stockout Radar</strong>
            <span>Decision support · v1.0</span>
          </div>
          <span className="footer-status-dot" title={environmentLabel} />
        </div>
      </aside>

      {mobileOpen && <button className="mobile-scrim" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}

      <main className="main-shell">
        <header className="topbar">
          <div className="topbar-left">
            <button className="icon-button mobile-menu" onClick={() => setMobileOpen(true)} aria-label="Open navigation">
              <Menu size={20} />
            </button>
            <div className="breadcrumbs">
              <span>Workspace</span>
              <ChevronRight size={14} />
              <strong>{pageTitle}</strong>
            </div>
          </div>
          <div className="topbar-right">
            <div className="environment-chip"><span className="environment-dot" /> {environmentLabel}</div>
            <div className="topbar-divider" />
            <div className="user-avatar" aria-label="Stockout Radar workspace">SR</div>
          </div>
        </header>
        <div className="content-area">{children}</div>
        <footer className="app-footer">
          <span>Stockout Radar <span className="footer-separator">/</span> Inventory decision support</span>
          <span>Historical model snapshot · Not a live market feed</span>
        </footer>
      </main>
    </div>
  );
}
