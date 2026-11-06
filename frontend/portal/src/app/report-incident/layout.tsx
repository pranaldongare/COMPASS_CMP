import type { Metadata } from "next";
import type * as React from "react";

export const metadata: Metadata = { title: "Report an incident" };

export default function ReportIncidentLayout({ children }: { children: React.ReactNode }) {
  return children;
}
