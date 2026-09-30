/**
 * The breach register (S3-01).
 *
 * The question this page answers first is "which duty is due soonest, and
 * which is already late", so each open breach lists its outstanding duties
 * with the server's clock. The DPO's alone: the server answers anyone else
 * 404, and the menu never offers them the page.
 */
"use client";

import { Plus } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { EmptyRecords } from "@/components/ui/graphics";
import {
  Alert,
  Button,
  Card,
  EmptyState,
  Mono,
  Select,
  Table,
  TableSkeleton,
  Td,
  Th,
  Tr,
} from "@/components/ui/primitives";
import {
  BreachStatusBadge,
  OutcomeBadge,
  clockText,
  locationText,
} from "@/features/breach/components/copy";
import { RecordBreachForm } from "@/features/breach/components/record-breach";
import { useBreaches } from "@/features/breach/queries";
import { cn, formatDateTime } from "@/lib/format";
import type { BreachStatus } from "@/types";

export default function BreachesPage() {
  const [status, setStatus] = React.useState<BreachStatus | "">("open");
  const [recording, setRecording] = React.useState(false);
  const query = useBreaches(status || undefined);

  return (
    <>
      <PageHeader
        title="Personal data breaches"
        description="Section 8(6) and Rule 7, and CERT-In. The platform records, derives and tracks every clock; people contain the breach, determine it, and submit to the Board and CERT-In through their own channels."
        actions={
          <Button variant="primary" onClick={() => setRecording(true)}>
            <Plus className="size-4" />
            Record a breach
          </Button>
        }
      />

      <div className="mb-4 flex items-center gap-2">
        <label className="text-sm text-text-muted" htmlFor="breach-status">
          Show
        </label>
        <Select
          id="breach-status"
          className="w-40"
          value={status}
          onChange={(e) => setStatus(e.target.value as BreachStatus | "")}
        >
          <option value="open">Open</option>
          <option value="closed">Closed</option>
          <option value="">All</option>
        </Select>
      </div>

      {query.error ? (
        <Alert tone="danger" title="Could not load the register">
          {query.error.userMessage()}
        </Alert>
      ) : query.isLoading ? (
        <TableSkeleton cols={5} />
      ) : !query.data || query.data.length === 0 ? (
        <EmptyState
          illustration={<EmptyRecords />}
          title={status === "open" ? "No open breach" : "No breach recorded"}
          description="A breach is recorded here as it is noticed, with the time it was first noticed."
        />
      ) : (
        <Card>
          <Table>
            <caption className="sr-only">Breaches, open first, with every outstanding duty</caption>
            <thead>
              <tr>
                <Th>Reference</Th>
                <Th>Where</Th>
                <Th>Determination</Th>
                <Th>Outstanding duties</Th>
                <Th>First noticed</Th>
              </tr>
            </thead>
            <tbody>
              {query.data.map((b) => {
                const outstanding = b.obligations.filter((d) => d.state === "outstanding");
                const late = outstanding.some((d) => d.clock.overdue || d.clock.past_target);
                return (
                  <Tr key={b.breach_uuid} className={cn(late && "bg-danger-subtle/40")}>
                    <Td>
                      <Link href={`/breaches/${b.breach_uuid}`} className="font-medium text-accent-text hover:underline">
                        <Mono>{b.reference}</Mono>
                      </Link>
                      <span className="block text-sm">{b.title}</span>
                      <BreachStatusBadge status={b.status} />
                    </Td>
                    <Td className="text-sm">{locationText(b.location)}</Td>
                    <Td>
                      <OutcomeBadge outcome={b.determination} />
                    </Td>
                    <Td className="text-sm">
                      {outstanding.length === 0 ? (
                        <span className="text-text-muted">None</span>
                      ) : (
                        <ul className="space-y-1">
                          {outstanding.map((d) => (
                            <li key={d.obligation_uuid}>
                              <span className="font-medium">{d.label}</span>
                              <span
                                className={cn(
                                  "block text-xs",
                                  d.clock.overdue || d.clock.past_target ? "text-danger-text" : "text-text-muted",
                                )}
                              >
                                {clockText(d.state, d.clock)}
                              </span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </Td>
                    <Td className="text-sm">{formatDateTime(b.detected_at)}</Td>
                  </Tr>
                );
              })}
            </tbody>
          </Table>
        </Card>
      )}

      <Dialog open={recording} onOpenChange={setRecording}>
        <DialogContent
          title="Record a breach"
          description="As it was noticed. Every time is entered, not filled in: the clocks run from what you type."
          size="lg"
        >
          <RecordBreachForm onDone={() => setRecording(false)} />
        </DialogContent>
      </Dialog>
    </>
  );
}
