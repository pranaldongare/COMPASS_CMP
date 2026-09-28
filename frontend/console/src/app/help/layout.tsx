import type { Metadata } from "next";
import type * as React from "react";

export const metadata: Metadata = { title: "Help manual" };

export default function HelpLayout({ children }: { children: React.ReactNode }) {
  return children;
}
