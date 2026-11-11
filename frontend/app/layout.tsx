import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { AppShell } from "@/components/app-shell";

export const metadata: Metadata = {
  title: {
    default: "Stockout Radar | Inventory Intelligence",
    template: "%s | Stockout Radar",
  },
  description:
    "Demand forecasting and inventory decision support for retail operations.",
  applicationName: "Stockout Radar",
};

export const viewport: Viewport = {
  themeColor: "#101c2b",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
