/**
 * What is waiting for her, above her consents.
 *
 * She lands on her consents because that is what most people come for. But
 * a response ready to download, a request that has moved, a nominee who
 * acted, a nomination waiting for her answer - none of those live on that
 * page, and none of them should need a visit to a second one to be noticed.
 * Each line links to the card it concerns. Nothing is shown when nothing is
 * true, so the page opens the way it always did on a quiet day.
 */
"use client";

import { ArrowRight, Download, Scale, UserRound } from "lucide-react";
import Link from "next/link";

import { useMyNominations, useMyRequests, useNominationsNamingMe } from "@/features/rights/queries";
import { formatDate } from "@/lib/format";

interface Line {
  key: string;
  icon: React.ReactNode;
  text: string;
  href: string;
  tone: "attention" | "quiet";
}

const OPEN = new Set(["received", "in_progress", "awaiting_holders", "collating"]);

export function HomeStrip() {
  const requests = useMyRequests();
  const nominations = useMyNominations();
  const naming = useNominationsNamingMe();
  const lines: Line[] = [];

  const ready = (requests.data ?? []).filter((r) => r.download_available);
  if (ready.length === 1) {
    const r = ready[0]!;
    lines.push({
      key: `dl-${r.request_uuid}`,
      icon: <Download className="size-4" aria-hidden="true" />,
      text: `Our response to ${r.reference} is ready to download${r.download_expires_at ? ` until ${formatDate(r.download_expires_at)}` : ""}.`,
      href: "/my-requests",
      tone: "attention",
    });
  } else if (ready.length > 1) {
    const soonest = ready
      .map((r) => r.download_expires_at)
      .filter((d): d is string => Boolean(d))
      .sort()[0];
    lines.push({
      key: "dl-many",
      icon: <Download className="size-4" aria-hidden="true" />,
      text: `${ready.length} responses are ready to download${soonest ? `; the first window closes ${formatDate(soonest)}` : ""}.`,
      href: "/my-requests",
      tone: "attention",
    });
  }
  const open = (requests.data ?? []).filter((r) => OPEN.has(r.status));
  if (open.length > 0) {
    const first = open[0]!;
    lines.push({
      key: "open",
      icon: <Scale className="size-4" aria-hidden="true" />,
      text:
        open.length === 1
          ? `${first.reference} is with the Privacy Office; you will hear by ${formatDate(first.due_at)}.`
          : `${open.length} requests are with the Privacy Office; the first is due by ${formatDate(first.due_at)}.`,
      href: "/my-requests",
      tone: "quiet",
    });
  }
  for (const n of nominations.data ?? []) {
    if (n.invoked_at) {
      lines.push({
        key: `inv-${n.nomination_uuid}`,
        icon: <UserRound className="size-4" aria-hidden="true" />,
        text: `${n.nominee_name} acted for you on ${formatDate(n.invoked_at)}, reporting ${n.invoked_event === "death" ? "that you have died" : "that you cannot act"}${n.invoked_reference ? ` (${n.invoked_reference})` : ""}.`,
        href: "/my-requests",
        tone: "attention",
      });
    }
  }
  for (const n of naming.data ?? []) {
    if (n.status === "pending") {
      lines.push({
        key: `naming-${n.nomination_uuid}`,
        icon: <UserRound className="size-4" aria-hidden="true" />,
        text: `${n.principal_name} has named you to act for them; accept or decline from the link sent to ${n.contact}.`,
        href: "/my-requests",
        tone: "attention",
      });
    }
  }

  if (lines.length === 0) return null;
  return (
    <ul className="mb-6 divide-y divide-border rounded-xl border border-border bg-surface" data-testid="home-strip">
      {lines.map((l) => (
        <li key={l.key}>
          <Link href={l.href} className="group flex items-center gap-3 px-4 py-3 text-sm transition-colors hover:bg-surface-hover">
            <span className={l.tone === "attention" ? "text-accent-text" : "text-text-subtle"}>{l.icon}</span>
            <span className="min-w-0 flex-1">{l.text}</span>
            <ArrowRight className="size-4 shrink-0 text-text-subtle transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
          </Link>
        </li>
      ))}
    </ul>
  );
}
