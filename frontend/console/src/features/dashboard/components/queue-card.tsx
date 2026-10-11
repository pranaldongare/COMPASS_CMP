/**
 * A queue: the things waiting for this person.
 *
 * The most important element on the screen for a DPO, because a queue that is
 * not surfaced is work nobody knows about. Each row links to the thing itself,
 * not to a filtered list — one click, not two.
 *
 * Drawn as the role-dashboard design has it (2026-10-10): a card head with
 * the queue's icon and count, then rows on one grid - the reference in
 * monospace, the person or project with an initials disc, and the state as a
 * pill at the right - so two queues side by side line up row for row.
 */

"use client";

import {
  AlertTriangle,
  Building2,
  CheckCircle2,
  Clock,
  FolderKanban,
  Inbox,
  Lock,
  MapPin,
  Scale,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { PanelHeader } from "@/components/ui/panel";
import { Card } from "@/components/ui/primitives";
import { StatusBadge } from "@/components/ui/status";
import { cn, formatDate } from "@/lib/format";

const SHOWN = 5;

/** A queue's icon and tint, from its name - the server names the queues. */
function queueLook(name: string): { icon: LucideIcon; tint: 0 | 1 | 2 | 3 } {
  const n = name.toLowerCase();
  if (/rights request|grievance/.test(n)) return { icon: Scale, tint: 0 };
  if (/ticket|written/.test(n)) return { icon: Inbox, tint: 3 };
  if (/approval|review/.test(n)) return { icon: Clock, tint: 1 };
  if (/exception|reconcile|floor|erasure/.test(n)) return { icon: AlertTriangle, tint: 3 };
  if (/site/.test(n)) return { icon: MapPin, tint: 3 };
  if (/processor|source|suspended/.test(n)) return { icon: Building2, tint: 1 };
  if (/lockout/.test(n)) return { icon: Lock, tint: 3 };
  if (/ready|approved/.test(n)) return { icon: CheckCircle2, tint: 2 };
  return { icon: FolderKanban, tint: 0 };
}

const PILL = {
  bad: "bg-danger-subtle text-danger-text",
  warn: "bg-warning-subtle text-warning-text",
  neutral: "bg-bg-inset text-text-muted",
} as const;

function initials(text: string): string {
  return text
    .split(/[\s·-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("");
}

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
  const look = queueLook(name);
  // "Due soon" is measured from when the card first drew, not re-read on
  // every render.
  const [now] = React.useState(() => Date.now());
  return (
    <Card
      id={slug ? `q-${slug}` : undefined}
      className="flex h-full scroll-mt-20 flex-col overflow-hidden rounded-2xl"
    >
      <PanelHeader
        icon={look.icon}
        tint={look.tint}
        title={name}
        count={count}
        link={
          (rest > 0 || capped) && listHref
            ? { href: listHref, label: "See all" }
            : undefined
        }
      />

      {items.length === 0 ? (
        <p className="px-[18px] py-4 text-sm text-text-muted">
          Nothing waiting. This queue is clear.
        </p>
      ) : (
        <ul>
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

            // The reference column: what the record is called in the register.
            const reference =
              (item.reference as string) ??
              (item.internal_project_name as string) ??
              (item.source_collection_ref as string) ??
              (item.source_code as string) ??
              "";
            // The name column: who or what it is about. A site reads with its
            // project beside it; a request with the person.
            const who =
              typeof item.site_label === "string"
                ? `${item.site_label} · ${String(item.project_name ?? "")}`
                : ((item.subject_name as string) ??
                  (item.project_name as string) ??
                  (item.full_name as string) ??
                  (item.name as string) ??
                  (item.legal_name as string) ??
                  (reference ? "" : "Item"));

            // The state pill: the clock first - it is what makes a row urgent.
            let pill: { text: string; tone: keyof typeof PILL } | null = null;
            if (typeof item.due_at === "string") {
              const days = Math.ceil((new Date(item.due_at).getTime() - now) / 86_400_000);
              pill = item.overdue
                ? { text: `Overdue ${formatDate(item.due_at)}`, tone: "bad" }
                : {
                    text: `Due ${formatDate(item.due_at)}`,
                    tone: days <= 7 ? "warn" : "neutral",
                  };
            } else if (typeof item.declared_asset_count === "number") {
              const missing =
                Number(item.declared_asset_count) - Number(item.mapped_asset_count ?? 0);
              pill = { text: `${missing} unaccounted`, tone: "warn" };
            } else if (typeof item.action === "string") {
              pill = { text: item.action, tone: "warn" };
            } else if (typeof item.updated_at === "string") {
              pill = { text: formatDate(item.updated_at), tone: "neutral" };
            }

            const Row = (
              <div className="grid h-12 grid-cols-[8.25rem_minmax(0,1fr)_auto] items-center gap-3 px-[18px] text-[0.8125rem] transition-colors hover:bg-[var(--row-hover)]">
                {/* No reference: the name takes its column too. */}
                {reference && (
                  <span className="truncate font-mono text-[0.71875rem] text-text-muted">
                    {reference}
                  </span>
                )}
                <span
                  className={cn(
                    "flex min-w-0 items-center gap-2",
                    !reference && "col-span-2",
                  )}
                >
                  {who && (
                    <span
                      aria-hidden="true"
                      className="grid size-[26px] shrink-0 place-items-center rounded-full bg-accent-subtle text-[0.625rem] font-bold text-accent-text"
                    >
                      {initials(who)}
                    </span>
                  )}
                  <span className="truncate">{who}</span>
                </span>
                <span className="flex justify-end">
                  {typeof item.project_status === "string" && !pill ? (
                    <StatusBadge kind="project" value={item.project_status} />
                  ) : pill ? (
                    <span
                      title={pill.text}
                      className={cn(
                        "max-w-56 truncate rounded-full px-2.5 py-0.5 text-[0.6875rem] font-semibold",
                        PILL[pill.tone],
                      )}
                    >
                      {pill.text}
                    </span>
                  ) : null}
                </span>
              </div>
            );

            return (
              <li key={uuid ?? index} className="border-b border-border/60 last:border-b-0">
                {href ? <Link href={href}>{Row}</Link> : Row}
              </li>
            );
          })}
          {(rest > 0 || capped) && (
            <li className="px-[18px] py-2.5 text-xs text-text-muted">
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
