/**
 * A queue: the things waiting for this person.
 *
 * The most important element on the screen for a DPO, because a queue that is
 * not surfaced is work nobody knows about. Each row links to the thing itself,
 * not to a filtered list — one click, not two.
 */

"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { EmptyQueue } from "@/components/ui/graphics";
import { Card, CardHeader, CardTitle, EmptyState } from "@/components/ui/primitives";
import { StatusBadge } from "@/components/ui/status";
import { formatDateTime } from "@/lib/format";

const SHOWN = 5;

/** A clear queue is one line, not a card with an illustration: the page's
 * height should say how much work there is. */
export function ClearQueues({ names }: { names: string[] }) {
  if (names.length === 0) return null;
  return <p className="px-1 text-xs text-text-subtle">Clear: {names.join(" · ")}</p>;
}

export function QueueCard({
  name,
  items,
  slug,
  href: listHref,
  capped = false,
}: {
  name: string;
  items: Array<Record<string, unknown>>;
  slug?: string;
  /** Where "see all" goes when the queue is longer than what is shown. */
  href?: string | null;
  /** The server stopped at its row limit, so `items.length` is a floor. */
  capped?: boolean;
}) {
  const shown = items.slice(0, SHOWN);
  const rest = items.length - shown.length;
  // "All 25" claimed a complete list the query had cut short (UX review).
  const count = capped ? `${items.length}+` : String(items.length);
  return (
    <Card id={slug ? `q-${slug}` : undefined} className="scroll-mt-20">
      <CardHeader className="flex items-center justify-between gap-3">
        <CardTitle>{name}</CardTitle>
        <span className="flex items-center gap-3">
          {(rest > 0 || capped) && listHref && (
            <Link
              href={listHref}
              className="text-xs text-accent-text underline-offset-4 hover:underline"
            >
              See all
            </Link>
          )}
          <span className="tabular rounded-full bg-bg-inset px-2.5 py-0.5 text-xs font-medium text-text-muted">
            {count}
          </span>
        </span>
      </CardHeader>

      {items.length === 0 ? (
        <EmptyState
          illustration={<EmptyQueue />}
          title="Nothing waiting"
          description="This queue is clear."
        />
      ) : (
        <ul className="divide-y divide-border">
          {shown.map((item, index) => {
            const uuid =
              (item.request_uuid as string) ??
              (item.project_uuid as string) ??
              (item.collection_uuid as string) ??
              null;
            // A row the server gave a destination opens it: a collection or a
            // site is not its project. Otherwise the order below decides.
            const href =
              typeof item.href === "string"
                ? item.href
                : item.ticket
                  ? `/tickets?ticket=${item.holder_uuid as string}`
                  : item.request_uuid
                    ? `/requests/${item.request_uuid}`
                    : item.project_uuid
                      ? `/projects/${item.project_uuid}`
                      : item.collection_uuid
                        ? `/collections/${item.collection_uuid}`
                        : null;

            // A rights request reads as its reference and the person; the
            // clock is what makes it urgent, so the due date joins the title.
            // A breach ticket carries no person: its reference stands alone.
            const title = item.reference
              ? [String(item.reference), item.subject_name ? String(item.subject_name) : null]
                  .filter(Boolean)
                  .join(" · ")
              : typeof item.site_label === "string"
                ? `${item.site_label} · ${String(item.project_name ?? "")}`
                : ((item.project_name as string) ??
                  (item.source_collection_ref as string) ??
                  (item.full_name as string) ??
                  (item.name as string) ??
                  "Item");

            const Row = (
              <div className="group flex items-center justify-between gap-4 px-5 py-3 transition-colors hover:bg-surface-hover">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{title}</p>
                  {typeof item.action === "string" && (
                    <p className="mt-0.5 text-xs text-text-muted">{item.action}</p>
                  )}
                  {typeof item.due_at === "string" && (
                    <p
                      className={
                        item.overdue
                          ? "mt-0.5 text-xs font-medium text-danger-text"
                          : "mt-0.5 text-xs text-text-subtle"
                      }
                    >
                      {item.overdue ? "Overdue - due " : "Due "}
                      {formatDateTime(item.due_at)}
                    </p>
                  )}
                  {typeof item.declared_asset_count === "number" && (
                    <p className="mt-0.5 text-xs text-warning-text">
                      {item.declared_asset_count} declared,{" "}
                      {String(item.mapped_asset_count ?? 0)} mapped —{" "}
                      {Number(item.declared_asset_count) -
                        Number(item.mapped_asset_count ?? 0)}{" "}
                      unaccounted for
                    </p>
                  )}
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  {typeof item.project_status === "string" && (
                    <StatusBadge kind="project" value={item.project_status} />
                  )}
                  {typeof item.updated_at === "string" && (
                    <span className="hidden text-xs text-text-subtle sm:inline">
                      {formatDateTime(item.updated_at)}
                    </span>
                  )}
                  {href && (
                    <ArrowRight
                      className="size-4 text-text-subtle transition-transform group-hover:translate-x-0.5 group-hover:text-accent"
                      aria-hidden="true"
                    />
                  )}
                </div>
              </div>
            );

            return (
              <li key={uuid ?? index}>{href ? <Link href={href}>{Row}</Link> : Row}</li>
            );
          })}
          {(rest > 0 || capped) && (
            <li className="px-5 py-2.5 text-xs text-text-muted">
              {capped ? "More than these" : `${rest} more`}
              {listHref && (
                <>
                  {" · "}
                  <Link
                    href={listHref}
                    className="text-accent-text underline-offset-4 hover:underline"
                  >
                    see all
                  </Link>
                </>
              )}
            </li>
          )}
        </ul>
      )}
    </Card>
  );
}
