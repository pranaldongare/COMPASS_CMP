/**
 * Every open breach on the DPO's dashboard, each with its duties and their
 * clocks (S3-04). The server sends it to the DPO alone; for anyone else the
 * list is empty and nothing renders.
 */
import { ShieldAlert } from "lucide-react";
import Link from "next/link";

import { Card, CardBody, CardHeader, CardTitle, Mono } from "@/components/ui/primitives";
import { DutyStateBadge, clockText } from "@/features/breach/components/copy";
import { cn } from "@/lib/format";
import type { BreachSummary } from "@/types";

export function OpenBreaches({ breaches }: { breaches: BreachSummary[] }) {
  if (breaches.length === 0) return null;
  return (
    <Card aria-label="Open breaches">
      <CardHeader>
        <CardTitle>
          <ShieldAlert className="mr-2 inline size-4" aria-hidden="true" />
          Open breaches
        </CardTitle>
      </CardHeader>
      <CardBody>
        <ul className="divide-y divide-border">
          {breaches.map((b) => (
            <li key={b.breach_uuid} className="py-3">
              <Link href={`/breaches/${b.breach_uuid}`} className="font-medium text-accent-text hover:underline">
                <Mono>{b.reference}</Mono>
              </Link>
              <span className="ml-2 text-sm">{b.title}</span>
              {b.obligations.length === 0 ? (
                <p className="mt-1 text-xs text-text-muted">No duty yet: validate it.</p>
              ) : (
                <ul className="mt-2 grid gap-1 sm:grid-cols-2">
                  {b.obligations.map((d) => (
                    <li key={d.obligation_uuid} className="flex flex-wrap items-center gap-2 text-sm">
                      <DutyStateBadge duty={d} />
                      <span>{d.label}</span>
                      <span
                        className={cn(
                          "text-xs",
                          d.clock.overdue || d.clock.past_target ? "text-danger-text" : "text-text-muted",
                        )}
                      >
                        {clockText(d.state, d.clock)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ul>
      </CardBody>
    </Card>
  );
}
