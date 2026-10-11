/**
 * The head of a dashboard card (2026-10-10, the role-dashboard design): a
 * tinted icon tile, the title, a count, and a link at the right - "See all",
 * "Open", "Audit trail". One height everywhere, so cards side by side line up.
 */
import { ChevronRight } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { cn } from "@/lib/format";

export function PanelHeader({
  icon,
  tint = 0,
  title,
  count,
  link,
  id,
}: {
  icon: React.ComponentType<{ className?: string }>;
  /** Blue, violet, teal or amber (.nav-tint-0..3); "danger" for attention. */
  tint?: 0 | 1 | 2 | 3 | "danger";
  title: string;
  count?: number | string;
  link?: { href: string; label: string };
  /** For the heading, so the card can be named by it. */
  id?: string;
}) {
  return (
    <div className="flex h-[3.125rem] shrink-0 items-center gap-2.5 border-b border-border px-[18px]">
      <span
        aria-hidden="true"
        className={cn(
          "grid size-7 shrink-0 place-items-center rounded-lg [&_svg]:size-[0.9375rem]",
          tint === "danger" ? "bg-danger-subtle text-danger-text" : `nav-tint-${tint}`,
        )}
      >
        {React.createElement(icon)}
      </span>
      <h2 id={id} className="truncate text-sm font-semibold">
        {title}
      </h2>
      {count !== undefined && (
        <span className="tabular rounded-full bg-bg-inset px-2 py-0.5 text-[0.6875rem] font-bold text-text-muted">
          {count}
        </span>
      )}
      {link && (
        <Link
          href={link.href}
          className="ml-auto inline-flex shrink-0 items-center gap-0.5 text-xs font-semibold text-accent-text hover:underline"
        >
          {link.label}
          <ChevronRight className="size-3.5" aria-hidden="true" />
        </Link>
      )}
    </div>
  );
}
