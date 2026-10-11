/**
 * The open breaches on the DPO's dashboard (S3-04). The server sends them to
 * the DPO alone; for anyone else the list is empty and nothing renders.
 *
 * A work list like the queues beside it (2026-10-10, the role-dashboard
 * design): the five with the latest activity, each a row - its reference, its
 * title, and how its duties stand - and the register one click away. Each
 * duty's own clock is on the breach.
 */
import { ShieldAlert } from "lucide-react";
import Link from "next/link";

import { PanelHeader } from "@/components/ui/panel";
import { Card } from "@/components/ui/primitives";
import { cn } from "@/lib/format";
import type { BreachSummary } from "@/types";

const SHOWN = 5;

/** How a breach's duties stand, as one pill. */
function standing(b: BreachSummary): { text: string; tone: string } {
  if (b.obligations.length === 0)
    return { text: "Validate it", tone: "bg-bg-inset text-text-muted" };
  const outstanding = b.obligations.filter((d) => d.state === "outstanding");
  const late = outstanding.filter((d) => d.clock.overdue || d.clock.past_target).length;
  if (late) return { text: `${late} late`, tone: "bg-danger-subtle text-danger-text" };
  if (outstanding.length)
    return { text: `${outstanding.length} due`, tone: "bg-warning-subtle text-warning-text" };
  return { text: "Duties done", tone: "bg-success-subtle text-success-text" };
}

export function OpenBreaches({ breaches }: { breaches: BreachSummary[] }) {
  if (breaches.length === 0) return null;
  const shown = [...breaches]
    .sort((a, b) => b.last_activity_at.localeCompare(a.last_activity_at))
    .slice(0, SHOWN);
  return (
    <Card aria-label="Open breaches" className="flex h-full flex-col overflow-hidden rounded-2xl">
      <PanelHeader
        icon={ShieldAlert}
        tint={3}
        title="Open breaches"
        count={breaches.length}
        link={{ href: "/breaches", label: "See all" }}
      />
      <ul>
        {shown.map((b) => {
          const pill = standing(b);
          return (
            <li key={b.breach_uuid} className="border-b border-border/60 last:border-b-0">
              <Link
                href={`/breaches/${b.breach_uuid}`}
                className="grid h-12 grid-cols-[8.25rem_minmax(0,1fr)_auto] items-center gap-3 px-[18px] text-[0.8125rem] transition-colors hover:bg-[var(--row-hover)]"
              >
                <span className="truncate font-mono text-[0.71875rem] text-text-muted">
                  {b.reference}
                </span>
                <span className="truncate">{b.title}</span>
                <span
                  className={cn(
                    "rounded-full px-2.5 py-0.5 text-[0.6875rem] font-semibold whitespace-nowrap",
                    pill.tone,
                  )}
                >
                  {pill.text}
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}
