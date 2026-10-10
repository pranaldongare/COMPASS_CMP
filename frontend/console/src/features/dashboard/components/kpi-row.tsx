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
    },
    {
      key: "open_breaches",
      label: "Open breaches",
      icon: ShieldAlert,
      href: "/breaches",
      hint: (c) =>
        c.breach_duties_late ? `${plural(c.breach_duties_late, "duty", "duties")} late` : "no duty late",
      alarm: (c) => (c.breach_duties_late ?? 0) > 0,
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
      hint: (c) => (c.unapproved_languages ? `${plural(c.unapproved_languages, "notice text")} to approve` : undefined),
    },
  ],
  dco: [
    { key: "approved_projects", icon: CheckCircle2 },
    { key: "active_links", icon: Link2 },
    { key: "consents", icon: FileText },
    { key: "tickets_for_me", icon: Inbox, alarm: (c) => (c.tickets_for_me ?? 0) > 0 },
  ],
  rco: [
    { key: "approved_projects", icon: CheckCircle2 },
    { key: "active_links", icon: Link2 },
    { key: "consents", icon: FileText },
    { key: "tickets_for_me", icon: Inbox, alarm: (c) => (c.tickets_for_me ?? 0) > 0 },
  ],
  dco_admin: [
    { key: "projects", icon: FolderKanban },
    { key: "approved_projects", icon: CheckCircle2 },
    {
      key: "sites_awaiting_source",
      icon: AlertTriangle,
      alarm: (c) => (c.sites_awaiting_source ?? 0) > 0,
    },
    {
      key: "sources_without_owner",
      icon: UserPlus,
      alarm: (c) => (c.sources_without_owner ?? 0) > 0,
    },
  ],
  rnd_user: [
    { key: "total", label: "Your projects", icon: FolderKanban },
    { key: "in_draft", icon: FileText },
    { key: "pending_approval", icon: Scale },
    { key: "approved", icon: CheckCircle2 },
  ],
  admin: [
    { key: "users_active", label: "Active accounts", icon: Users, href: "/users?status=active" },
    {
      key: "users_pending",
      label: "Accounts pending",
      icon: UserPlus,
      href: "/users?status=pending",
      hint: (c) =>
        c.staff_invites_pending ? `${plural(c.staff_invites_pending, "invitation")} unanswered` : undefined,
    },
    {
      key: "grievances_about_dpo",
      icon: Scale,
      alarm: (c) => (c.grievances_about_dpo ?? 0) > 0,
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
}: {
  role: string | undefined;
  counts: Record<string, number>;
}) {
  const figures = (FIGURES[role ?? ""] ?? []).filter((f) => f.key in counts);
  if (figures.length === 0) return null;
  return (
    <section aria-label="At a glance" className="stagger grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {figures.map((f, i) => {
        const Icon = f.icon;
        return (
          <StatTile
            key={f.key}
            label={f.label ?? COUNT_LABELS[f.key] ?? f.key}
            value={counts[f.key] ?? 0}
            hint={f.hint?.(counts)}
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
