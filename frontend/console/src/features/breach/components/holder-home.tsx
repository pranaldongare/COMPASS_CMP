/**
 * The temporary ticket holder's home (2026-10-11, the role-dashboard design,
 * screen 7).
 *
 * A breach-only login (S3-09) has no dashboard: the server's `nav` leaves it
 * out, and the dashboard sends it here. So the top of its Tickets page is its
 * home - a greeting, four figures, what needs it, and its tickets in two
 * lists - all read off the breach tickets addressed to it, which are the only
 * records it may see. Nothing from the register reaches it here either: the
 * breach reference, the ask, the state and the answer-by date (BD-13).
 *
 * The design's "Access ends" figure has no data behind it: a grant ends when
 * the breach closes or the ticket is withdrawn, not on a date. The fourth
 * figure is the earliest answer-by date instead, which is the date that
 * matters to the holder. The design's ticket references (BT-...) do not exist
 * either - a breach ticket carries only its breach's reference - so the lists
 * show the breach reference and the ask.
 */
"use client";

import {
  AlertTriangle,
  BarChart3,
  Calendar,
  CalendarClock,
  ChevronRight,
  Clock,
  ShieldCheck,
  Ticket,
} from "lucide-react";
import Link from "next/link";
import type { ComponentType } from "react";

import { BarList, StatTile } from "@/components/ui/charts";
import { PanelHeader } from "@/components/ui/panel";
import { Button, Card } from "@/components/ui/primitives";
import { cn, formatDateTime } from "@/lib/format";
import type { MyBreachTicket } from "@/types";

/** The id of the breach-ticket list further down the Tickets page. */
export const BREACH_TICKETS_ANCHOR = "breach-tickets";
const ALL = `#${BREACH_TICKETS_ANCHOR}`;

/** Opens the ticket on the same page: the Tickets page reads `breach_ticket`. */
const ticketHref = (t: MyBreachTicket) => `/tickets?breach_ticket=${t.ticket_uuid}`;

const DAY_CHIP = new Intl.DateTimeFormat("en-GB", {
  weekday: "short",
  day: "numeric",
  month: "short",
  year: "numeric",
});
const DAY_MONTH = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short" });

/** An answer-by date (`YYYY-MM-DD`) as a local calendar day. */
function localDay(value: string): Date {
  const [y, m, d] = value.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d);
}

/** A local calendar day as `YYYY-MM-DD`. */
function dayKey(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** Whole days from today to the date: negative is late, 0 is today. */
function daysUntil(answerBy: string, now: Date): number {
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.round((localDay(answerBy).getTime() - today.getTime()) / 86_400_000);
}

const plural = (n: number, one: string, many: string) => (n === 1 ? one : many);

type Urgency = "late" | "today" | "soon" | "open";

function urgencyOf(t: MyBreachTicket, now: Date): Urgency {
  if (!t.answer_by) return "open";
  const days = daysUntil(t.answer_by, now);
  if (days < 0) return "late";
  if (days === 0) return "today";
  if (days <= 7) return "soon";
  return "open";
}

/** Everything the summary shows, counted from the tickets. Exported for the test. */
export function holderFigures(tickets: MyBreachTicket[], now: Date) {
  // Issued is the holder's turn; returned waits on the Privacy Office.
  const open = tickets
    .filter((t) => t.state === "issued")
    .sort(
      (a, b) =>
        (a.answer_by ? localDay(a.answer_by).getTime() : Infinity) -
        (b.answer_by ? localDay(b.answer_by).getTime() : Infinity),
    );
  const returned = tickets.filter((t) => t.state === "returned");
  const by = (u: Urgency) => open.filter((t) => urgencyOf(t, now) === u);
  const earliest = open.find((t) => t.answer_by) ?? null;
  return {
    open,
    returned,
    late: by("late"),
    today: by("today"),
    soon: by("soon"),
    rest: by("open"),
    earliest: earliest?.answer_by ?? null,
  };
}

export function HolderHome({
  tickets,
  name,
  now = new Date(),
}: {
  tickets: MyBreachTicket[];
  /** The holder's full name; the greeting uses the first. */
  name: string;
  now?: Date;
}) {
  const f = holderFigures(tickets, now);
  const first = name.trim().split(/\s+/)[0] || name;

  return (
    <section
      aria-label="Your summary"
      data-testid="holder-home"
      className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-12"
    >
      <Banner first={first} now={now} />
      <Figures f={f} now={now} />
      <Attention f={f} />
      <Card className="flex h-full flex-col overflow-hidden rounded-2xl sm:col-span-2 lg:col-span-5">
        <PanelHeader
          icon={BarChart3}
          title="Your tickets"
          link={{ href: ALL, label: "Open" }}
        />
        <div className="flex-1 px-[18px] py-4">
          <BarList
            items={[
              { key: "open", label: "Open", value: f.open.length, href: ALL },
              { key: "returned", label: "Returned", value: f.returned.length, href: ALL },
              { key: "late", label: "Past its date", value: f.late.length, href: ALL },
            ]}
          />
        </div>
      </Card>
      <TicketList
        title="Your breach tickets"
        icon={Ticket}
        tint={0}
        tickets={f.open}
        empty="Nothing waiting on you."
        pill={(t) => duePill(t, now)}
      />
      <TicketList
        title="Answered"
        icon={ShieldCheck}
        tint={2}
        tickets={f.returned}
        empty="Nothing answered yet."
        pill={() => ({ text: "Returned", className: "bg-bg-inset text-text-muted" })}
      />
      <Activity tickets={tickets} />
    </section>
  );
}

function Banner({ first, now }: { first: string; now: Date }) {
  return (
    <div className="hero-line flex flex-wrap items-center justify-between gap-4 overflow-hidden rounded-2xl border border-border bg-surface px-6 py-6 shadow-[var(--shadow-xs)] sm:col-span-2 lg:col-span-12">
      <div className="min-w-0">
        <p className="mb-1 text-[0.6875rem] font-semibold tracking-[0.09em] text-accent-text uppercase">
          Temporary access
        </p>
        <h2 className="text-[1.625rem] leading-tight font-bold tracking-tight">
          Good day, {first}
        </h2>
        <p className="mt-1 text-[0.8125rem] text-text-muted">
          You were asked to help with a breach. Your tickets are below.
        </p>
      </div>
      <div className="relative flex flex-wrap items-center gap-2.5">
        <span className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3.5 py-2 text-[0.8125rem] text-text-muted">
          <Calendar className="size-4" aria-hidden="true" />
          <time dateTime={dayKey(now)}>{DAY_CHIP.format(now)}</time>
        </span>
        <Button asChild variant="primary">
          <a href={ALL}>
            <Ticket className="size-4" aria-hidden="true" />
            Open my tickets
          </a>
        </Button>
      </div>
    </div>
  );
}

type Figs = ReturnType<typeof holderFigures>;

function Figures({ f, now }: { f: Figs; now: Date }) {
  const late = f.late.length;
  const today = f.today.length;
  const days = f.earliest ? daysUntil(f.earliest, now) : null;
  return (
    <>
      <StatTile
        className="lg:col-span-3"
        label="Tickets open"
        value={f.open.length}
        tint="blue"
        icon={<Ticket />}
        href={ALL}
        hint={
          late
            ? `${late} past its date`
            : today
              ? `${today} due today`
              : f.open.length
                ? "none due today"
                : "nothing open"
        }
        hintTone={late ? "bad" : today ? "warn" : f.open.length ? "neutral" : "good"}
      />
      <StatTile
        className="lg:col-span-3"
        label="Due today"
        value={today}
        tint="amber"
        tone={today > 0 ? "attention" : "neutral"}
        icon={<Clock />}
        href={f.today.length === 1 ? ticketHref(f.today[0]) : ALL}
        hint={today ? "answer today" : "nothing due today"}
        hintTone={today ? "bad" : "neutral"}
      />
      <StatTile
        className="lg:col-span-3"
        label="Answered"
        value={f.returned.length}
        tint="teal"
        icon={<ShieldCheck />}
        href={ALL}
        hint={f.returned.length ? "with the Privacy Office" : undefined}
      />
      <StatTile
        className="lg:col-span-3"
        label="Earliest answer-by"
        value={f.earliest ? DAY_MONTH.format(localDay(f.earliest)) : "—"}
        tint="violet"
        icon={<CalendarClock />}
        href={ALL}
        hint={
          days === null
            ? "no date set"
            : days < 0
              ? `${-days} ${plural(-days, "day", "days")} late`
              : days === 0
                ? "today"
                : `in ${days} ${plural(days, "day", "days")}`
        }
        hintTone={
          days === null ? "neutral" : days < 0 ? "bad" : days === 0 ? "warn" : "neutral"
        }
      />
    </>
  );
}

const MARK: Record<Urgency, { dot: string; text: string; tag: string; tagClass: string }> =
  {
    late: {
      dot: "bg-danger ring-4 ring-danger-subtle",
      text: "text-danger-text",
      tag: "Late",
      tagClass: "bg-danger-subtle text-danger-text",
    },
    today: {
      dot: "bg-danger ring-4 ring-danger-subtle",
      text: "text-danger-text",
      tag: "Due today",
      tagClass: "bg-danger-subtle text-danger-text",
    },
    soon: {
      dot: "bg-warning ring-4 ring-warning-subtle",
      text: "text-warning-text",
      tag: "Due soon",
      tagClass: "bg-warning-subtle text-warning-text",
    },
    open: {
      dot: "bg-text-subtle ring-4 ring-bg-inset",
      text: "text-text",
      tag: "To do",
      tagClass: "bg-bg-inset text-text-muted",
    },
  };

function Attention({ f }: { f: Figs }) {
  const all: Array<{ key: Urgency; tickets: MyBreachTicket[]; label: string }> = [
    {
      key: "late",
      tickets: f.late,
      label: plural(f.late.length, "Ticket past its date", "Tickets past their date"),
    },
    {
      key: "today",
      tickets: f.today,
      label: plural(f.today.length, "Ticket due today", "Tickets due today"),
    },
    {
      key: "soon",
      tickets: f.soon,
      label: plural(f.soon.length, "Ticket due within 7 days", "Tickets due within 7 days"),
    },
    {
      key: "open",
      tickets: f.rest,
      label: plural(f.rest.length, "Other open ticket", "Other open tickets"),
    },
  ];
  const rows = all.filter((r) => r.tickets.length > 0);
  return (
    <Card className="flex h-full flex-col overflow-hidden rounded-2xl sm:col-span-2 lg:col-span-7">
      <PanelHeader
        icon={AlertTriangle}
        tint="danger"
        title="Needs attention"
        count={f.open.length}
        link={{ href: ALL, label: "All" }}
      />
      {rows.length === 0 ? (
        <p className="px-[18px] py-4 text-sm text-text-muted">Nothing is waiting on you.</p>
      ) : (
        <ul data-testid="holder-attention">
          {rows.map((row) => {
            const mark = MARK[row.key];
            return (
              <li key={row.key} className="border-b border-border/60 last:border-b-0">
                <Link
                  href={row.tickets.length === 1 ? ticketHref(row.tickets[0]) : ALL}
                  className="group grid h-[2.875rem] grid-cols-[1.375rem_3.5rem_minmax(0,1fr)_auto_1.125rem] items-center px-[18px] text-[0.8125rem] transition-colors hover:bg-[var(--row-hover)]"
                >
                  <span
                    className={cn("size-[9px] rounded-full", mark.dot)}
                    aria-hidden="true"
                  />
                  <span
                    className={cn(
                      "tabular pr-3.5 text-right text-base font-bold",
                      mark.text,
                    )}
                  >
                    {row.tickets.length}
                  </span>
                  <span className="truncate">{row.label}</span>
                  <span
                    aria-hidden="true"
                    className={cn(
                      "mr-2.5 rounded-full px-2.5 py-0.5 text-[0.6875rem] font-semibold",
                      mark.tagClass,
                    )}
                  >
                    {mark.tag}
                  </span>
                  <ChevronRight
                    className="size-4 text-text-subtle transition-transform group-hover:translate-x-0.5 group-hover:text-accent"
                    aria-hidden="true"
                  />
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}

type Pill = { text: string; className: string };

function duePill(t: MyBreachTicket, now: Date): Pill {
  const u = urgencyOf(t, now);
  if (u === "late") return { text: "Late", className: "bg-danger-subtle text-danger-text" };
  if (u === "today")
    return { text: "Due today", className: "bg-danger-subtle text-danger-text" };
  if (!t.answer_by) return { text: "Open", className: "bg-bg-inset text-text-muted" };
  const when = `Due ${DAY_MONTH.format(localDay(t.answer_by))}`;
  return u === "soon"
    ? { text: when, className: "bg-warning-subtle text-warning-text" }
    : { text: when, className: "bg-bg-inset text-text-muted" };
}

function TicketList({
  title,
  icon,
  tint,
  tickets,
  empty,
  pill,
}: {
  title: string;
  icon: ComponentType<{ className?: string }>;
  tint: 0 | 2;
  tickets: MyBreachTicket[];
  empty: string;
  pill: (t: MyBreachTicket) => Pill;
}) {
  return (
    <Card className="flex h-full flex-col overflow-hidden rounded-2xl sm:col-span-2 lg:col-span-6">
      <PanelHeader
        icon={icon}
        tint={tint}
        title={title}
        count={tickets.length}
        link={{ href: ALL, label: "See all" }}
      />
      {tickets.length === 0 ? (
        <p className="px-[18px] py-4 text-sm text-text-muted">{empty}</p>
      ) : (
        <ul aria-label={title}>
          {tickets.slice(0, 5).map((t) => {
            const p = pill(t);
            const urgent = p.className.includes("danger");
            return (
              <li key={t.ticket_uuid} className="border-b border-border/60 last:border-b-0">
                <Link
                  href={ticketHref(t)}
                  className="grid h-12 grid-cols-[minmax(0,8.25rem)_minmax(0,1fr)_6.5rem] items-center gap-2 px-[18px] text-[0.8125rem] transition-colors hover:bg-[var(--row-hover)]"
                >
                  <span className="truncate font-mono text-xs text-text-muted">
                    {t.breach_reference}
                  </span>
                  <span className="flex min-w-0 items-center gap-2.5">
                    <span
                      aria-hidden="true"
                      className={cn(
                        "grid size-[26px] shrink-0 place-items-center rounded-full text-[0.6875rem] font-bold",
                        urgent ? "bg-danger-subtle text-danger-text" : "nav-tint-0",
                      )}
                    >
                      B
                    </span>
                    <span className="truncate">{t.instruction}</span>
                  </span>
                  <span
                    className={cn(
                      "justify-self-end rounded-full px-2.5 py-0.5 text-[0.6875rem] font-semibold whitespace-nowrap",
                      p.className,
                    )}
                  >
                    {p.text}
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}

/** What can be read off the tickets themselves: when each was issued, and its latest message. */
function Activity({ tickets }: { tickets: MyBreachTicket[] }) {
  const events = tickets
    .flatMap((t) => [
      {
        key: `${t.ticket_uuid}:issued`,
        at: t.created_at,
        t,
        text: `Ticket on ${t.breach_reference} issued to you`,
      },
      ...(t.last_activity_at
        ? [
            {
              key: `${t.ticket_uuid}:message`,
              at: t.last_activity_at,
              t,
              text:
                t.state === "returned"
                  ? `Latest message on ${t.breach_reference}, now with the Privacy Office`
                  : `Latest message on ${t.breach_reference}`,
            },
          ]
        : []),
    ])
    .sort((a, b) => new Date(b.at).getTime() - new Date(a.at).getTime())
    .slice(0, 6);
  return (
    <Card className="overflow-hidden rounded-2xl sm:col-span-2 lg:col-span-12">
      <PanelHeader
        icon={Clock}
        title="Recent activity"
        link={{ href: ALL, label: "All tickets" }}
      />
      {events.length === 0 ? (
        <p className="px-[18px] py-4 text-sm text-text-muted">Nothing yet.</p>
      ) : (
        <ul aria-label="Recent activity">
          {events.map((e) => (
            <li key={e.key} className="border-b border-border/60 last:border-b-0">
              <Link
                href={ticketHref(e.t)}
                className="flex min-h-12 items-center gap-3 px-[18px] py-2.5 text-[0.8125rem] transition-colors hover:bg-[var(--row-hover)]"
              >
                <span
                  className="size-[9px] shrink-0 rounded-full bg-accent ring-4 ring-accent-subtle"
                  aria-hidden="true"
                />
                <span className="min-w-0 flex-1 truncate">{e.text}</span>
                <time dateTime={e.at} className="tabular shrink-0 text-xs text-text-subtle">
                  {formatDateTime(e.at)}
                </time>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
