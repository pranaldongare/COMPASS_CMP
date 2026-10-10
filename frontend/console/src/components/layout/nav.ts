/**
 * Where the console can take somebody, and what each destination is called.
 *
 * One list, read by the sidebar, the header's breadcrumb and the command
 * palette, so the three cannot disagree about a page's name or its section.
 *
 * It is not a permission list. `me.nav`, which the server computes from the
 * permission matrix, decides which of these a person sees; anything it does not
 * name is not rendered anywhere.
 */
import {
  Bell,
  Boxes,
  Building2,
  ClipboardCheck,
  Database,
  FileCheck,
  FileText,
  FolderKanban,
  Gauge,
  HandHelping,
  Inbox,
  Layers,
  Link2,
  MapPin,
  MessageSquareText,
  Scale,
  ShieldAlert,
  ScrollText,
  ShieldCheck,
  Upload,
  UserRound,
  Users,
} from "lucide-react";
import type * as React from "react";

import type { Me } from "@/types";

export interface NavItem {
  /** Must match a value in `me.nav`. Anything not in that list is not rendered. */
  key: string;
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  /** Other words somebody might type for it in the command palette. */
  keywords?: string;
}

export interface NavSection {
  title: string;
  items: NavItem[];
}

export const SECTIONS: NavSection[] = [
  {
    title: "Overview",
    items: [
      {
        key: "dashboard",
        href: "/dashboard",
        label: "Dashboard",
        icon: Gauge,
        keywords: "home",
      },
    ],
  },
  {
    title: "Governance",
    items: [
      {
        key: "projects",
        href: "/projects",
        label: "Projects",
        icon: FolderKanban,
        keywords: "study",
      },
      {
        key: "approvals",
        href: "/approvals",
        // The stored proofs - not the queue of things awaiting a decision.
        label: "Approval documents",
        icon: FileCheck,
        keywords: "review",
      },
      {
        key: "notices",
        href: "/notices",
        label: "Notices",
        icon: ScrollText,
        keywords: "privacy notice",
      },
      { key: "purposes", href: "/purposes", label: "Purposes", icon: ClipboardCheck },
    ],
  },
  {
    title: "Consent",
    items: [
      {
        key: "consents",
        href: "/consents",
        label: "Consents",
        icon: FileText,
        keywords: "artefact register",
      },
      { key: "links", href: "/links", label: "Consent links", icon: Link2 },
      { key: "sites", href: "/sites", label: "Collection sites", icon: MapPin },
    ],
  },
  {
    title: "Registry",
    items: [
      {
        key: "processors",
        href: "/processors",
        label: "Processors",
        icon: Building2,
        keywords: "vendor third party",
      },
      { key: "sources", href: "/sources", label: "Data sources", icon: Database },
    ],
  },
  {
    title: "Data movement",
    items: [
      { key: "collections", href: "/collections", label: "Collections", icon: Layers },
      {
        key: "exports",
        href: "/exports",
        label: "Exports",
        icon: Upload,
        keywords: "csv download",
      },
      {
        key: "imports",
        href: "/imports",
        label: "Imports",
        icon: Boxes,
        keywords: "manifest upload",
      },
    ],
  },
  {
    title: "Oversight",
    items: [
      // The DPO's register of rights requests, and - for the administrator -
      // the grievances escalated away from the DPO.
      {
        key: "requests",
        href: "/requests",
        label: "Rights requests",
        icon: Scale,
        keywords: "erasure access correction grievance",
      },
      // Personal data breaches: the register, and every duty's clock (S3-01).
      {
        key: "breaches",
        href: "/breaches",
        label: "Breaches",
        icon: ShieldAlert,
        keywords: "incident cert-in board rule 7 personal data breach",
      },
      {
        key: "audit",
        href: "/audit",
        label: "Audit trail",
        icon: ShieldCheck,
        keywords: "log history",
      },
      {
        key: "users",
        href: "/users",
        label: "Users",
        icon: Users,
        keywords: "staff accounts",
      },
      {
        key: "delegate",
        href: "/delegate",
        label: "Delegations",
        icon: HandHelping,
        keywords: "cover leave",
      },
      // The words of every email and SMS the platform sends.
      {
        key: "messages",
        href: "/messages",
        // The words the platform sends; not an inbox.
        label: "Message templates",
        icon: MessageSquareText,
        keywords: "email sms templates",
      },
    ],
  },
  {
    title: "You",
    items: [
      // A rights request's holder that is one of our own teams is answered
      // here, by whoever that team named - whatever their role.
      {
        key: "tickets",
        href: "/tickets",
        label: "My tasks",
        icon: Inbox,
        keywords: "tickets for you",
      },
      { key: "notifications", href: "/notifications", label: "Notifications", icon: Bell },
      {
        key: "profile",
        href: "/account",
        label: "My profile",
        icon: UserRound,
        keywords: "account settings",
      },
    ],
  },
];

/** The same section reads differently by role: the administrator's share of
 * the rights register is the grievances escalated away from the DPO. */
export function labelFor(item: NavItem, role: string | undefined): string {
  if (item.key === "requests" && role === "admin") return "Grievances about the DPO";
  // The register is scoped to their own for these roles, and says so.
  if (item.key === "projects" && (role === "rnd_user" || role === "dco" || role === "rco"))
    return "My projects";
  return item.label;
}

/**
 * Each role's daily work, in the order it runs - the first group of its
 * sidebar (UX review 2026-10-05). The sidebar used to list every section in
 * one order for everybody, which put a DPO's rights requests below
 * governance, consent, registry and data movement. Only keys the server
 * granted are shown; what a role has beyond these follows in the usual groups.
 */
const DAILY_WORK: Record<string, string[]> = {
  dpo: ["dashboard", "requests", "breaches", "tickets", "projects", "notices"],
  rnd_user: ["dashboard", "projects", "approvals", "tickets", "notices"],
  dco_admin: ["dashboard", "sites", "sources", "tickets", "links", "projects"],
  dco: ["dashboard", "projects", "sites", "links", "tickets", "collections"],
  rco: ["dashboard", "projects", "sites", "links", "tickets", "collections"],
  admin: ["dashboard", "users", "requests", "messages", "processors", "sources", "audit"],
  breach_holder: ["tickets"],
};

/** In the account menu and the header's bell, not the sidebar as well. */
const NOT_IN_SIDEBAR = new Set(["profile", "notifications"]);

/** The sidebar: this role's daily work first, then the rest in their groups. */
export function sidebarFor(me: Me | null | undefined): NavSection[] {
  const granted = sectionsFor(me);
  const byKey = new Map(granted.flatMap((s) => s.items).map((item) => [item.key, item]));
  const first = (DAILY_WORK[me?.role ?? ""] ?? ["dashboard"])
    .map((key) => byKey.get(key))
    .filter((item): item is NavItem => Boolean(item));
  const taken = new Set(first.map((item) => item.key));
  const rest = granted
    .map((section) => ({
      ...section,
      items: section.items.filter((i) => !taken.has(i.key) && !NOT_IN_SIDEBAR.has(i.key)),
    }))
    .filter((section) => section.items.length > 0);
  return [{ title: "Your work", items: first }, ...rest];
}

/** The sections this person has, with only the destinations the server granted. */
export function sectionsFor(me: Me | null | undefined): NavSection[] {
  return SECTIONS.map((section) => ({
    ...section,
    items: section.items.filter((item) => me?.nav.includes(item.key)),
  })).filter((section) => section.items.length > 0);
}

/** The destination a path sits under, and its section: `/projects/abc` is Projects. */
export function locate(
  sections: NavSection[],
  pathname: string,
): { section: NavSection; item: NavItem } | null {
  for (const section of sections) {
    for (const item of section.items) {
      if (pathname === item.href || pathname.startsWith(`${item.href}/`)) {
        return { section, item };
      }
    }
  }
  return null;
}

/** The menu icon of a destination's own page, whoever is signed in - for the
 *  tile beside a page's title (2026-10-10). Only an exact match: a record
 *  under a destination is not that destination's page. */
export function iconForPage(pathname: string): NavItem["icon"] | undefined {
  for (const section of SECTIONS) {
    for (const item of section.items) {
      if (item.href === pathname) return item.icon;
    }
  }
  return undefined;
}
