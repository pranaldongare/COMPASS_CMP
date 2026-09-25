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
        label: "Approvals",
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
        label: "Delegate",
        icon: HandHelping,
        keywords: "cover leave",
      },
      // The words of every email and SMS the platform sends.
      {
        key: "messages",
        href: "/messages",
        label: "Messages",
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
      { key: "tickets", href: "/tickets", label: "Tickets for you", icon: Inbox },
      { key: "notifications", href: "/notifications", label: "Notifications", icon: Bell },
      {
        key: "profile",
        href: "/account",
        label: "Your profile",
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
  return item.label;
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
