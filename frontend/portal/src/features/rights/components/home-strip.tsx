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
import * as React from "react";

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
      href: `/my-requests?request=${r.request_uuid}`,
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
      href: "/my-requests?view=ready",
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
      href: open.length === 1 ? `/my-requests?request=${first.request_uuid}` : "/my-requests",
      tone: "quiet",
    });
  }
  // A nominee who acted is one line however often (2026-10-10): one per
  // action buried her consents under a column of near-identical sentences.
  const acted = (nominations.data ?? [])
    .filter((n) => n.invoked_at)
    .sort((a, b) => (b.invoked_at ?? "").localeCompare(a.invoked_at ?? ""));
  if (acted.length === 1) {
    const n = acted[0]!;
    lines.push({
      key: `inv-${n.nomination_uuid}`,
      icon: <UserRound className="size-4" aria-hidden="true" />,
      text: `${n.nominee_name} acted for you on ${formatDate(n.invoked_at)}, reporting ${n.invoked_event === "death" ? "that you have died" : "that you cannot act"}${n.invoked_reference ? ` (${n.invoked_reference})` : ""}.`,
      href: "/my-nominations",
      tone: "attention",
    });
  } else if (acted.length > 1) {
    const latest = acted[0]!;
    lines.push({
      key: "inv-many",
      icon: <UserRound className="size-4" aria-hidden="true" />,
      text: `Your nominees acted for you ${acted.length} times; the latest was ${latest.nominee_name} on ${formatDate(latest.invoked_at)}.`,
      href: "/my-nominations",
      tone: "attention",
    });
  }
  for (const n of naming.data ?? []) {
    if (n.status === "pending") {
      lines.push({
        key: `naming-${n.nomination_uuid}`,
        icon: <UserRound className="size-4" aria-hidden="true" />,
        text: `${n.principal_name} has named you to act for them; accept or decline from the link sent to ${n.contact}.`,
        href: "/my-nominations",
        tone: "attention",
      });
    }
  }

  if (lines.length === 0) return null;
  return <Strip lines={lines} />;
}

/** At most three lines until she asks for the rest: the strip is a summary
 *  above her consents, not a page of its own. */
const SHOWN = 3;

function Strip({ lines }: { lines: Line[] }) {
  const [all, setAll] = React.useState(false);
  const shown = all ? lines : lines.slice(0, SHOWN);
  return (
    <div className="mb-6 overflow-hidden rounded-xl border border-border bg-surface shadow-[var(--shadow-xs)]">
    <ul className="divide-y divide-border" data-testid="home-strip">
      {shown.map((l) => (
        <li key={l.key}>
          <Link href={l.href} className="group flex items-center gap-3 px-4 py-3 text-sm transition-colors hover:bg-surface-hover">
            <span className={l.tone === "attention" ? "text-accent-text" : "text-text-subtle"}>{l.icon}</span>
            <span className="min-w-0 flex-1">{l.text}</span>
            <ArrowRight className="size-4 shrink-0 text-text-subtle transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
          </Link>
        </li>
      ))}
    </ul>
      {lines.length > SHOWN && (
        <button
          type="button"
          onClick={() => setAll(!all)}
          className="w-full border-t border-border px-4 py-2 text-left text-sm font-medium text-accent-text hover:bg-surface-hover"
        >
          {all ? "Show fewer" : `Show all ${lines.length}`}
        </button>
      )}
    </div>
  );
}
