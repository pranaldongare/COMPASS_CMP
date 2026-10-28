/**
 * The four figures at the top of a dashboard (2026-10-10).
 *
 * The dashboard opened on a list of numbers; this is the summary above it: the
 * four figures that say where this role's work stands, each a link to the rows
 * behind it, with one line of context. Chosen per role from the counts the
 * server already sends - nothing new is fetched, and a figure the server did
 * not send for this role is simply not shown.
 */
"use client";

import {
  AlertTriangle,
  CheckCircle2,
  FileText,
  FolderKanban,
  Inbox,
  Link2,
  Scale,
  ShieldAlert,
  Sparkles,
  UserPlus,
  Users,
  type LucideIcon,
} from "lucide-react";

import { StatTile } from "@/components/ui/charts";
import { COUNT_LABELS, COUNT_LINKS } from "@/features/dashboard/components/config";

interface Figure {
  key: string;
  label?: string;
  icon: LucideIcon;
  href?: string;
  /** A line under the figure, from the other counts. */
  hint?: (counts: Record<string, number>) => string | undefined;
  /** Shown in amber when this is above zero. */
  alarm?: (counts: Record<string, number>) => boolean;
  /** The hint chip's colour (2026-10-10): green when the hint is good news,
   *  red when it says something is late, amber when it is a to-do. */
  hintTone?: (counts: Record<string, number>) => "good" | "bad" | "warn" | "neutral";
}

const TINTS = ["blue", "amber", "teal", "violet"] as const;

const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

const FIGURES: Record<string, Figure[]> = {
  dpo: [
    {
      key: "requests_open",
      icon: Scale,
      hint: (c) =>
        c.requests_overdue
          ? `${plural(c.requests_overdue, "overdue")}`
          : c.requests_due_7d
            ? `${c.requests_due_7d} due within 7 days`
            : "none overdue",
      alarm: (c) => (c.requests_overdue ?? 0) > 0,
      hintTone: (c) => (c.requests_overdue ? "bad" : c.requests_due_7d ? "warn" : "good"),
    },
    {
      key: "open_breaches",
      label: "Open breaches",
      icon: ShieldAlert,
      href: "/breaches",
      hint: (c) =>
        c.breach_duties_late
          ? `${plural(c.breach_duties_late, "duty", "duties")} late`
          : "no duty late",
      alarm: (c) => (c.breach_duties_late ?? 0) > 0,
      hintTone: (c) => (c.breach_duties_late ? "bad" : "good"),
    },
    {
      key: "total_consents",
      icon: FileText,
      hint: (c) => (c.withdrawals != null ? `${c.withdrawals} withdrawn` : undefined),
    },
    {
      key: "pending_approval",
      label: "Projects awaiting approval",
      icon: FolderKanban,
      hint: (c) =>
        c.unapproved_languages
          ? `${plural(c.unapproved_languages, "notice text")} to approve`
          : undefined,
      hintTone: () => "warn",
    },
  ],
  dco: [
    {
      key: "approved_projects",
      icon: CheckCircle2,
      hint: () => "ready to collect",
      hintTone: () => "good",
    },
    { key: "active_links", icon: Link2 },
    { key: "consents", icon: FileText },
    {
      key: "tickets_for_me",
      icon: Inbox,
      alarm: (c) => (c.tickets_for_me ?? 0) > 0,
      hint: (c) => (c.tickets_for_me ? "waiting on you" : "none waiting"),
      hintTone: (c) => (c.tickets_for_me ? "warn" : "good"),
    },
  ],
  rco: [
    {
      key: "approved_projects",
      icon: CheckCircle2,
      hint: () => "ready to collect",
      hintTone: () => "good",
    },
    { key: "active_links", icon: Link2 },
    { key: "consents", icon: FileText },
    {
      key: "tickets_for_me",
      icon: Inbox,
      alarm: (c) => (c.tickets_for_me ?? 0) > 0,
      hint: (c) => (c.tickets_for_me ? "waiting on you" : "none waiting"),
      hintTone: (c) => (c.tickets_for_me ? "warn" : "good"),
    },
  ],
  dco_admin: [
    { key: "projects", icon: FolderKanban },
    { key: "approved_projects", icon: CheckCircle2 },
    {
      key: "sites_awaiting_source",
      icon: AlertTriangle,
      alarm: (c) => (c.sites_awaiting_source ?? 0) > 0,
      hint: (c) => (c.sites_awaiting_source ? "needs set-up" : "all set up"),
      hintTone: (c) => (c.sites_awaiting_source ? "warn" : "good"),
    },
    {
      key: "sources_without_owner",
      icon: UserPlus,
      alarm: (c) => (c.sources_without_owner ?? 0) > 0,
      hint: (c) => (c.sources_without_owner ? "assign an owner" : "all owned"),
      hintTone: (c) => (c.sources_without_owner ? "warn" : "good"),
    },
  ],
  rnd_user: [
    { key: "total", label: "Your projects", icon: FolderKanban },
    {
      key: "in_draft",
      icon: FileText,
      hint: (c) => (c.in_draft ? "finish to submit" : undefined),
      hintTone: () => "warn",
    },
    {
      key: "pending_approval",
      icon: Scale,
      hint: (c) => (c.pending_approval ? "with the DPO" : undefined),
    },
    {
      key: "approved",
      icon: CheckCircle2,
      hint: (c) => (c.approved ? "collecting" : undefined),
      hintTone: () => "good",
    },
  ],
  // The Legal office (increment 8): its requests and breaches as the DPO's,
  // and the HR track's own work - activities live, versions to approve.
  legal: [
    {
      key: "requests_open",
      icon: Scale,
      hint: (c) =>
        c.requests_in_intake
          ? `${c.requests_in_intake} in the shared intake`
          : c.requests_overdue
            ? `${plural(c.requests_overdue, "overdue")}`
            : "none overdue",
      alarm: (c) => (c.requests_overdue ?? 0) > 0,
      hintTone: (c) => (c.requests_overdue ? "bad" : c.requests_in_intake ? "warn" : "good"),
    },
    {
      key: "open_breaches",
      label: "Open breaches",
      icon: ShieldAlert,
      href: "/breaches",
      hint: (c) =>
        c.breach_duties_late
          ? `${plural(c.breach_duties_late, "duty", "duties")} late`
          : "no duty late",
      alarm: (c) => (c.breach_duties_late ?? 0) > 0,
      hintTone: (c) => (c.breach_duties_late ? "bad" : "good"),
    },
    {
      key: "activities_live",
      icon: Sparkles,
      hint: (c) => (c.total_consents != null ? `${c.total_consents} consents` : undefined),
    },
    {
      key: "versions_in_draft",
      icon: FileText,
      hint: (c) => (c.versions_in_draft ? "to approve" : "none waiting"),
      hintTone: (c) => (c.versions_in_draft ? "warn" : "good"),
    },
  ],
  hr_user: [
    { key: "activities_live", label: "Your live activities", icon: Sparkles },
    {
      key: "consents",
      icon: FileText,
      hint: (c) => (c.withdrawals_7d ? `${c.withdrawals_7d} withdrawn this week` : undefined),
    },
    {
      key: "links_expiring_7d",
      icon: Link2,
      alarm: (c) => (c.links_expiring_7d ?? 0) > 0,
      hint: (c) => (c.links_expiring_7d ? "extend or let close" : "none ending"),
      hintTone: (c) => (c.links_expiring_7d ? "warn" : "good"),
    },
    {
      key: "tickets_for_me",
      icon: Inbox,
      alarm: (c) => (c.tickets_for_me ?? 0) > 0,
      hint: (c) => (c.tickets_for_me ? "waiting on you" : "none waiting"),
      hintTone: (c) => (c.tickets_for_me ? "warn" : "good"),
    },
  ],
  admin: [
    {
      key: "users_active",
      label: "Active accounts",
      icon: Users,
      href: "/users?status=active",
    },
    {
      key: "users_pending",
      label: "Accounts pending",
      icon: UserPlus,
      href: "/users?status=pending",
      hint: (c) =>
        c.staff_invites_pending
          ? `${plural(c.staff_invites_pending, "invitation")} unanswered`
          : undefined,
      hintTone: () => "warn",
    },
    {
      key: "grievances_about_dpo",
      icon: Scale,
      alarm: (c) => (c.grievances_about_dpo ?? 0) > 0,
      hint: (c) =>
        c.grievances_to_escalate ? `${c.grievances_to_escalate} to review` : undefined,
      hintTone: () => "bad",
    },
    {
      key: "suspended_registry_rows",
      label: "Suspended sources and processors",
      icon: AlertTriangle,
      href: "/sources?status=suspended",
    },
  ],
};

export function KpiRow({
  role,
  counts,
  trends = {},
}: {
  role: string | undefined;
  counts: Record<string, number>;
  /** New per day this week, by count key: the line under a figure. */
  trends?: Record<string, number[]>;
}) {
  const figures = (FIGURES[role ?? ""] ?? []).filter((f) => f.key in counts);
  if (figures.length === 0) return null;
  return (
    <section
      aria-label="At a glance"
      className="stagger grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
    >
      {figures.map((f, i) => {
        const Icon = f.icon;
        return (
          <StatTile
            key={f.key}
            label={f.label ?? COUNT_LABELS[f.key] ?? f.key}
            value={counts[f.key] ?? 0}
            hint={f.hint?.(counts)}
            hintTone={f.hintTone?.(counts) ?? "neutral"}
            trend={trends[f.key]}
            tone={f.alarm?.(counts) ? "attention" : "accent"}
            icon={<Icon />}
            tint={TINTS[i % TINTS.length]}
            href={f.href ?? COUNT_LINKS[f.key]}
          />
        );
      })}
    </section>
  );
}
