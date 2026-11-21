import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VEILBENCH — Privacy-Preserving MPC Benchmarking",
  description: "Secure Multiparty Computation using Shamir Secret Sharing-based Secure Summation",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased selection:bg-indigo-500 selection:text-white">
        {children}
      </body>
    </html>
  );
}
