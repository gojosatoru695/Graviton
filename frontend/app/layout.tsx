import type { Metadata } from "next";
import "./globals.css";
import { Shell } from "@/components/layout/shell";
import { QueryProvider } from "@/lib/query-provider";

export const metadata: Metadata = {
  title: "Jarvis — Evidence-Backed Reconciliation",
  description: "Jarvis turns scattered orders, customer promises, delivery updates, invoices, and bank statements into one evidence-backed workflow.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">
        <QueryProvider>
          <Shell>{children}</Shell>
        </QueryProvider>
      </body>
    </html>
  );
}
