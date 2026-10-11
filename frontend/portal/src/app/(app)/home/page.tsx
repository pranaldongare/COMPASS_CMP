/**
 * Her home: what she agreed to, and what she asked for, on one page.
 *
 * The portal used to open on My consents, with a strip of what was waiting
 * above them. This is that strip grown into a page of its own (the role
 * dashboards, 2026-10-11): four figures, what needs her, her consents as a
 * whole, the latest of each list, and what has happened lately. Every number
 * and row is counted here from the same three reads the pages behind them
 * make - her consents, her requests, her updates - and opens the records it
 * counts. Nothing is invented: there is no trend data, so there are no
 * sparklines, and the updates feed has no read state, so nothing is "unread".
 */
"use client";

import {
  AlertTriangle,
  Bell,
  CalendarDays,
  ChevronRight,
  Clock,
  FileText,
  Plus,
  Scale,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { eventSentence } from "@/components/data-display/audit-detail";
import { Donut, StatTile } from "@/components/ui/charts";
import { PanelHeader } from "@/components/ui/panel";
import { Button, Skeleton } from "@/components/ui/primitives";
import { useMyConsents } from "@/features/my-consents";
import { useNotifications } from "@/features/notifications";
import { REQUEST_TYPE_COPY } from "@/features/rights/components/copy";
import { useMyRequests, useNominationsNamingMe } from "@/features/rights/queries";
import { cn, formatDateTime, formatRelative, initials } from "@/lib/format";
import { useAuth } from "@/providers";
import type { MyConsent, MyRequest } from "@/types";

/** The statuses a request is still open in, as on My requests. */
const OPEN = new Set(["received", "in_progress", "awaiting_holders", "collating"]);
/** How many rows each list shows before "See all". */
const ROWS = 5;
/** A download window closing within this many days is "due soon". */
const SOON_DAYS = 7;

const TODAY = new Intl.DateTimeFormat("en-GB", {
  weekday: "short",
  day: "numeric",
  month: "short",
  year: "numeric",
});
const DAY_MONTH = new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short" });

type ConsentState = "active" | "partial" | "declined" | "withdrawn";

/** The same reading as the badge on My consents. */
function consentState(c: MyConsent): ConsentState {
  if (c.granted_count === 0) return c.is_withdrawal ? "withdrawn" : "declined";
  return c.granted_count < c.purpose_count ? "partial" : "active";
}

const CONSENT_PILL: Record<ConsentState, { label: string; className: string }> = {
  active: { label: "Active", className: "bg-success-subtle text-success-text" },
  partial: { label: "Partial", className: "bg-info-subtle text-info-text" },
  declined: { label: "Declined", className: "bg-bg-inset text-text-muted" },
  withdrawn: { label: "Withdrawn", className: "bg-warning-subtle text-warning-text" },
};

const isOpen = (r: MyRequest) => OPEN.has(r.status);
const dayMonth = (iso: string) => DAY_MONTH.format(new Date(iso));

export default function HomePage() {
  const { me } = useAuth();
  const consents = useMyConsents();
  const requests = useMyRequests();
  const updates = useNotifications();
  const naming = useNominationsNamingMe();
  // Today, read once: the date chip and "due soon" agree for the visit.
  const [now] = React.useState(() => Date.now());

  const firstName = me?.full_name.trim().split(/\s+/)[0] ?? "";
  const allConsents = consents.data ?? [];
  const allRequests = requests.data ?? [];

  /* ------------------------------------------------------------ figures */

  const states = allConsents.map(consentState);
  const count = (s: ConsentState) => states.filter((x) => x === s).length;
  // Anything still granted is active - what is left after withdrawing one
  // purpose of several can still be withdrawn, so it counts.
  const active = allConsents.filter((c) => c.granted_count > 0);
  const projects = new Set(active.map((c) => c.project_uuid)).size;
  const withdrawn = allConsents
    .filter((c) => consentState(c) === "withdrawn")
    .sort((a, b) => b.affirmative_action_at.localeCompare(a.affirmative_action_at));
  const open = allRequests.filter(isOpen).sort((a, b) => a.due_at.localeCompare(b.due_at));
  const overdue = open.filter((r) => r.clock.overdue);
  const latestUpdate = updates.data?.items[0];

  /* ---------------------------------------------------- needs attention */

  const ready = allRequests.filter((r) => r.download_available);
  const readySoonest = ready
    .map((r) => r.download_expires_at)
    .filter((d): d is string => Boolean(d))
    .sort()[0];
  const readyCloses =
    readySoonest !== undefined &&
    new Date(readySoonest).getTime() - now < SOON_DAYS * 86_400_000;
  const asked = (naming.data ?? []).filter((n) => n.status === "pending");
  const attention: AttentionRow[] = [];
  if (overdue.length > 0) {
    attention.push({
      key: "overdue",
      count: overdue.length,
      label:
        overdue.length === 1
          ? "A request is past its deadline"
          : "Requests are past their deadline",
      severity: "late",
      href:
        overdue.length === 1
          ? `/my-requests?request=${overdue[0]!.request_uuid}`
          : "/my-requests",
    });
  }
  if (ready.length > 0) {
    attention.push({
      key: "ready",
      count: ready.length,
      label:
        ready.length === 1
          ? "A response is ready to download"
          : "Responses are ready to download",
      severity: readyCloses ? "soon" : "todo",
      href:
        ready.length === 1
          ? `/my-requests?request=${ready[0]!.request_uuid}`
          : "/my-requests?view=ready",
    });
  }
  if (asked.length > 0) {
    attention.push({
      key: "naming",
      count: asked.length,
      label:
        asked.length === 1
          ? "Someone has named you to act for them"
          : "People have named you to act for them",
      severity: "todo",
      href: "/my-nominations",
    });
  }

  /* -------------------------------------------------------------- lists */

  const recentConsents = [...allConsents]
    .sort((a, b) => b.affirmative_action_at.localeCompare(a.affirmative_action_at))
    .slice(0, ROWS);
  // Open ones first, soonest due; then the closed, newest first.
  const shownRequests = [
    ...open,
    ...allRequests
      .filter((r) => !isOpen(r))
      .sort((a, b) => b.received_at.localeCompare(a.received_at)),
  ].slice(0, ROWS);

  const segments = [
    { key: "active", label: "Active", value: count("active"), color: "var(--viz-1)" },
    {
      key: "partial",
      label: "Partly active",
      value: count("partial"),
      color: "var(--viz-2)",
    },
    {
      key: "withdrawn",
      label: "Withdrawn",
      value: count("withdrawn"),
      color: "var(--viz-3)",
    },
    {
      key: "declined",
      label: "Declined",
      value: count("declined"),
      color: "var(--viz-neutral)",
    },
  ]
    // Active and Withdrawn always; the others only when she has any.
    .filter((s) => s.value > 0 || s.key === "active" || s.key === "withdrawn")
    .map((s) => ({ ...s, href: "/my-consents" }));

  return (
    <div className="grid gap-4 lg:grid-cols-12">
      {/* The greeting. */}
      <section className="hero-line flex flex-wrap items-center gap-x-6 gap-y-4 rounded-2xl border border-border bg-surface px-6 py-6 lg:col-span-12">
        <div className="min-w-0">
          <p className="text-2xs font-bold tracking-wider text-accent-text uppercase">
            Your data
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight">
            Good day{firstName ? `, ${firstName}` : ""}
          </h1>
          <p className="mt-1 text-sm text-text-muted">
            What you agreed to, and what you asked for.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2.5 sm:ml-auto">
          <span className="inline-flex h-9 items-center gap-1.5 rounded-full border border-border bg-surface px-3.5 text-xs whitespace-nowrap text-text-muted">
            <CalendarDays className="size-3.5" aria-hidden="true" />
            {TODAY.format(now)}
          </span>
          <Button asChild variant="primary">
            <Link href="/my-requests?new=1">
              <Plus aria-hidden="true" />
              Make a request
            </Link>
          </Button>
        </div>
      </section>

      {/* The figures. */}
      <div className="grid gap-4 sm:grid-cols-2 lg:col-span-12 lg:grid-cols-12">
        <StatTile
          className="lg:col-span-3"
          label="Active consents"
          value={consents.data ? active.length : "—"}
          hint={
            consents.data && active.length > 0
              ? `across ${projects} ${projects === 1 ? "project" : "projects"}`
              : undefined
          }
          icon={<ShieldCheck />}
          tint="teal"
          href="/my-consents"
        />
        <StatTile
          className="lg:col-span-3"
          label="Withdrawn"
          value={consents.data ? withdrawn.length : "—"}
          hint={
            withdrawn[0] ? `on ${dayMonth(withdrawn[0].affirmative_action_at)}` : undefined
          }
          icon={<FileText />}
          tint="amber"
          href="/my-consents"
        />
        <StatTile
          className="lg:col-span-3"
          label="Open requests"
          value={requests.data ? open.length : "—"}
          hint={
            overdue.length > 0
              ? `${overdue.length} past ${overdue.length === 1 ? "its" : "their"} deadline`
              : open[0]
                ? `due ${dayMonth(open[0].due_at)}`
                : undefined
          }
          hintTone={overdue.length > 0 ? "bad" : "warn"}
          tone={overdue.length > 0 ? "attention" : "neutral"}
          icon={<Scale />}
          tint="blue"
          href="/my-requests"
        />
        <StatTile
          className="lg:col-span-3"
          label="Updates"
          value={updates.data ? updates.data.total : "—"}
          hint={
            latestUpdate ? `latest ${formatRelative(latestUpdate.occurred_at)}` : undefined
          }
          icon={<Bell />}
          tint="violet"
          href="/notifications"
        />
      </div>

      {/* What needs her, and her consents as a whole. */}
      <section aria-labelledby="home-attention" className={cn(CARD, "lg:col-span-7")}>
        <PanelHeader
          id="home-attention"
          icon={AlertTriangle}
          tint="danger"
          title="Needs attention"
          count={attention.length}
        />
        {requests.isLoading || naming.isLoading ? (
          <Rows />
        ) : attention.length === 0 ? (
          <Quiet>Nothing needs you right now.</Quiet>
        ) : (
          <ul>
            {attention.map((row) => (
              <li key={row.key} className="border-b border-border last:border-0">
                <Attention row={row} />
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="home-chart" className={cn(CARD, "lg:col-span-5")}>
        <PanelHeader
          id="home-chart"
          icon={FileText}
          tint={2}
          title="Your consents"
          link={{ href: "/my-consents", label: "Open" }}
        />
        <div className="flex flex-1 items-center px-[22px] py-[18px]">
          {consents.isLoading ? (
            <Skeleton className="h-36 w-full" />
          ) : consents.error ? (
            <p className="text-sm text-text-muted">Could not load your consents.</p>
          ) : allConsents.length === 0 ? (
            <p className="text-sm text-text-muted">No consent records yet.</p>
          ) : (
            <div className="w-full">
              <Donut
                segments={segments}
                centreLabel={allConsents.length === 1 ? "record" : "records"}
              />
            </div>
          )}
        </div>
      </section>

      {/* The latest of each list. */}
      <section aria-labelledby="home-consents" className={cn(CARD, "lg:col-span-6")}>
        <PanelHeader
          id="home-consents"
          icon={FileText}
          tint={2}
          title="My consents"
          count={consents.data ? allConsents.length : undefined}
          link={{ href: "/my-consents", label: "See all" }}
        />
        {consents.isLoading ? (
          <Rows />
        ) : consents.error ? (
          <Quiet>Could not load your consents.</Quiet>
        ) : recentConsents.length === 0 ? (
          <Quiet>When you agree to a notice, it will appear here.</Quiet>
        ) : (
          <ul>
            {recentConsents.map((c) => {
              const state = consentState(c);
              return (
                <li key={c.consent_uuid} className="border-b border-border last:border-0">
                  <ListRow
                    href={`/my-consents?consent=${c.consent_uuid}`}
                    reference={c.notice_code}
                    name={c.project_name}
                    avatarClass={state === "withdrawn" ? "nav-tint-3" : "nav-tint-2"}
                    pill={CONSENT_PILL[state]}
                  />
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section aria-labelledby="home-requests" className={cn(CARD, "lg:col-span-6")}>
        <PanelHeader
          id="home-requests"
          icon={Scale}
          tint={0}
          title="My requests"
          count={requests.data ? allRequests.length : undefined}
          link={{ href: "/my-requests", label: "See all" }}
        />
        {requests.isLoading ? (
          <Rows />
        ) : requests.error ? (
          <Quiet>Could not load your requests.</Quiet>
        ) : shownRequests.length === 0 ? (
          <Quiet>When you make a request, its reference and deadline appear here.</Quiet>
        ) : (
          <ul>
            {shownRequests.map((r) => (
              <li key={r.request_uuid} className="border-b border-border last:border-0">
                <ListRow
                  href={`/my-requests?request=${r.request_uuid}`}
                  reference={r.reference}
                  name={REQUEST_TYPE_COPY[r.request_type].label}
                  avatarClass="nav-tint-0"
                  pill={duePill(r)}
                />
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* What has happened lately. */}
      <section aria-labelledby="home-activity" className={cn(CARD, "lg:col-span-12")}>
        <PanelHeader
          id="home-activity"
          icon={Clock}
          tint={0}
          title="Recent activity"
          link={{ href: "/notifications", label: "All updates" }}
        />
        {updates.isLoading ? (
          <Rows />
        ) : updates.error ? (
          <Quiet>Could not load your updates.</Quiet>
        ) : !updates.data || updates.data.items.length === 0 ? (
          <Quiet>Events that concern you will appear here as they happen.</Quiet>
        ) : (
          <ul className="px-[18px] pt-1.5 pb-2.5">
            {updates.data.items.slice(0, ROWS).map((e) => (
              <li key={e.log_uuid} className="border-b border-border/60 last:border-0">
                <Link
                  href="/notifications"
                  className="-mx-2 grid min-h-[42px] grid-cols-[20px_minmax(0,1fr)_auto] items-center gap-2.5 rounded-md px-2 text-[0.8125rem] hover:bg-surface-hover"
                >
                  <span
                    aria-hidden="true"
                    className="size-[9px] justify-self-center rounded-full bg-accent shadow-[0_0_0_4px_var(--accent-subtle)]"
                  />
                  <span className="truncate font-medium">{eventSentence(e)}</span>
                  <span
                    className="text-xs whitespace-nowrap text-text-subtle"
                    title={formatDateTime(e.occurred_at)}
                  >
                    {formatRelative(e.occurred_at)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

const CARD =
  "flex h-full min-w-0 flex-col overflow-hidden rounded-2xl border border-border bg-surface shadow-[var(--shadow-xs)]";

/* ============================================================ attention */

interface AttentionRow {
  key: string;
  count: number;
  label: string;
  severity: "late" | "soon" | "todo";
  href: string;
}

const SEVERITY = {
  late: {
    dot: "bg-danger shadow-[0_0_0_4px_var(--danger-subtle)]",
    count: "text-danger-text",
    tag: "bg-danger-subtle text-danger-text",
    label: "Late",
  },
  soon: {
    dot: "bg-warning shadow-[0_0_0_4px_var(--warning-subtle)]",
    count: "text-warning-text",
    tag: "bg-warning-subtle text-warning-text",
    label: "Due soon",
  },
  todo: {
    dot: "bg-text-subtle shadow-[0_0_0_4px_var(--bg-inset)]",
    count: "text-text",
    tag: "bg-bg-inset text-text-muted",
    label: "To do",
  },
} as const;

function Attention({ row }: { row: AttentionRow }) {
  const s = SEVERITY[row.severity];
  return (
    <Link
      href={row.href}
      className="grid min-h-[46px] grid-cols-[22px_56px_minmax(0,1fr)_auto_18px] items-center px-[18px] text-[0.8125rem] transition-colors hover:bg-surface-hover"
    >
      <span aria-hidden="true" className={cn("size-[9px] rounded-full", s.dot)} />
      <span className={cn("tabular pr-3.5 text-right text-base font-bold", s.count)}>
        {row.count}
      </span>
      <span className="truncate">{row.label}</span>
      <span
        className={cn(
          "mr-2.5 rounded-full px-2.5 py-0.5 text-[0.6875rem] font-semibold",
          s.tag,
        )}
      >
        {s.label}
      </span>
      <ChevronRight className="size-[15px] text-text-subtle" aria-hidden="true" />
    </Link>
  );
}

/* ================================================================ lists */

function duePill(r: MyRequest): { label: string; className: string } {
  if (!isOpen(r)) return { label: "Closed", className: "bg-bg-inset text-text-muted" };
  if (r.clock.overdue) {
    const days = Math.abs(r.clock.days_remaining);
    return { label: `Overdue ${days} d`, className: "bg-danger-subtle text-danger-text" };
  }
  return {
    label: `Due ${dayMonth(r.due_at)}`,
    className:
      r.clock.days_remaining <= SOON_DAYS
        ? "bg-warning-subtle text-warning-text"
        : "bg-bg-inset text-text-muted",
  };
}

function ListRow({
  href,
  reference,
  name,
  avatarClass,
  pill,
}: {
  href: string;
  reference: string;
  name: string;
  avatarClass: string;
  pill: { label: string; className: string };
}) {
  return (
    <Link
      href={href}
      className="grid min-h-12 grid-cols-[minmax(0,1fr)_auto] items-center gap-3 px-[18px] py-2 text-[0.8125rem] transition-colors hover:bg-surface-hover sm:grid-cols-[132px_minmax(0,1fr)_104px] sm:py-0"
    >
      <span className="hidden truncate font-mono text-[0.71875rem] text-text-muted sm:block">
        {reference}
      </span>
      <span className="flex min-w-0 items-center gap-2">
        <span
          aria-hidden="true"
          className={cn(
            "grid size-[26px] shrink-0 place-items-center rounded-full text-[0.625rem] font-bold",
            avatarClass,
          )}
        >
          {initials(name)}
        </span>
        <span className="truncate">{name}</span>
      </span>
      <span
        className={cn(
          "justify-self-end rounded-full px-2.5 py-0.5 text-[0.6875rem] font-semibold whitespace-nowrap",
          pill.className,
        )}
      >
        {pill.label}
      </span>
    </Link>
  );
}

/* ================================================================ quiet */

function Quiet({ children }: { children: React.ReactNode }) {
  return <p className="px-[18px] py-4 text-sm text-text-muted">{children}</p>;
}

function Rows() {
  return (
    <div className="space-y-2 px-[18px] py-3">
      {Array.from({ length: 3 }).map((_, i) => (
        <Skeleton key={i} className="h-9" />
      ))}
    </div>
  );
}
