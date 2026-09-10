/**
 * The register of rights requests.
 *
 * The DPO's most time-bound work: every request runs on a published clock,
 * and this list exists to answer "what is due soonest, and what is already
 * late" before anything else. Overdue rows are marked; the filter chips read
 * the query string so a dashboard count lands on the rows it counted.
 *
 * For an administrator the same page shows only grievances escalated away
 * from the DPO - the server scopes it, this page does not.
 */
"use client";

import { Plus } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import {
  FilterBar,
  FilterSelect,
  ResourceList,
  useCursorStack,
  useFilterParam,
} from "@/components/data-display/resource-list";
import { PageHeader } from "@/components/layout/app-shell";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { EmptyRecords } from "@/components/ui/graphics";
import { Button, Mono, Td, Tr } from "@/components/ui/primitives";
import { REQUEST_TYPE_COPY, RequestStatusBadge, RequestTypeBadge } from "@/features/rights/components/copy";
import { LogRequestForm } from "@/features/rights/components/log-request-form";
import { useRequests } from "@/features/rights/queries";
import { cn, formatDate, formatDateTime } from "@/lib/format";
import { useAuth } from "@/providers";
import type { RightsRequestRow } from "@/types";
import { RIGHTS_REQUEST_STATUSES, RIGHTS_REQUEST_TYPES } from "@/types";

const STATUS_LABELS: Record<string, string> = {
  received: "Received",
  in_progress: "In progress",
  awaiting_holders: "Awaiting holders",
  collating: "Collating",
  closed: "Closed",
};

function RequestsPageView() {
  const { me } = useAuth();
  const stack = useCursorStack();
  const [status, setStatus] = useFilterParam("status");
  const [type, setType] = useFilterParam("type");
  const [overdue, setOverdue] = useFilterParam("overdue");
  const [logging, setLogging] = React.useState(false);

  const query = useRequests({
    status: status || undefined,
    type: type || undefined,
    overdue: overdue ? true : undefined,
    cursor: stack.cursor,
    limit: 25,
  });

  const isAdmin = me?.role === "admin";

  return (
    <>
      <PageHeader
        title="Rights requests"
        description={
          isAdmin
            ? "Grievances about the DPO, escalated to you as the independent reviewer. Accountability cannot review itself."
            : "Access, correction, erasure and grievance - sections 11 to 14. Every request runs on the published clock from the moment it arrives."
        }
        actions={
          !isAdmin ? (
            <Button variant="primary" onClick={() => setLogging(true)}>
              <Plus className="size-4" />
              Log a request received by email
            </Button>
          ) : null
        }
      />

      <FilterBar>
        <FilterSelect
          label="Status"
          value={status}
          onChange={(v) => {
            setStatus(v);
            stack.reset();
          }}
          options={RIGHTS_REQUEST_STATUSES.map((s) => ({ value: s, label: STATUS_LABELS[s] }))}
          allLabel="All statuses"
        />
        <FilterSelect
          label="Kind"
          value={type}
          onChange={(v) => {
            setType(v);
            stack.reset();
          }}
          options={RIGHTS_REQUEST_TYPES.map((t) => ({ value: t, label: REQUEST_TYPE_COPY[t].label }))}
          allLabel="All kinds"
        />
        <FilterSelect
          label="Clock"
          value={overdue}
          onChange={(v) => {
            setOverdue(v);
            stack.reset();
          }}
          options={[{ value: "1", label: "Overdue only" }]}
          allLabel="Any"
        />
      </FilterBar>

      <ResourceList<RightsRequestRow>
        query={query}
        stack={stack}
        caption="Rights requests in scope, with their deadlines"
        columns={["Reference", "Who", "Kind", "Status", "Received", "Due"]}
        keyOf={(r) => r.request_uuid}
        empty={{
          illustration: <EmptyRecords />,
          title: status || type || overdue ? "No requests match" : "No requests yet",
          description: isAdmin
            ? "A grievance escalated away from the DPO appears here."
            : "A request made from the dashboard, the notice link or an email you log appears here with its clock.",
        }}
        row={(r) => (
          <Tr className={cn(r.clock.overdue && "bg-danger-subtle/40")}>
            <Td>
              <Link href={`/requests/${r.request_uuid}`} className="font-medium text-accent-text hover:underline">
                <Mono>{r.reference}</Mono>
              </Link>
              {r.about_dpo && (
                <p className="mt-0.5 text-2xs font-semibold uppercase tracking-wide text-warning-text">about the DPO</p>
              )}
              {r.consent_uuid && (
                <p className="mt-0.5 text-2xs font-semibold uppercase tracking-wide text-accent-text" title={r.consent_project ?? undefined}>
                  one consent{r.consent_project ? ` · ${r.consent_project}` : ""}
                </p>
              )}
            </Td>
            <Td>
              <p className="text-sm">{r.subject_name ?? r.submitted_name ?? "Unmatched contact"}</p>
              <p className="text-xs text-text-subtle">{r.submitted_contact}</p>
            </Td>
            <Td>
              <RequestTypeBadge type={r.request_type} />
            </Td>
            <Td>
              <div className="flex flex-wrap gap-1">
                <RequestStatusBadge status={r.status} outcome={r.outcome} />
                {r.verification_status === "pending" && r.status !== "closed" && (
                  <span className="text-2xs text-warning-text">unverified</span>
                )}
              </div>
            </Td>
            <Td className="whitespace-nowrap text-text-muted">{formatDateTime(r.received_at)}</Td>
            <Td className="whitespace-nowrap">
              <span className={cn("tabular", r.clock.overdue ? "font-medium text-danger-text" : r.clock.at_risk ? "text-warning-text" : "text-text-muted")}>
                {formatDate(r.due_at)}
              </span>
              {r.status !== "closed" && (
                <p className="text-xs text-text-subtle">
                  {r.clock.overdue
                    ? `${Math.abs(r.clock.days_remaining)} day${Math.abs(r.clock.days_remaining) === 1 ? "" : "s"} late`
                    : `${r.clock.days_remaining} day${r.clock.days_remaining === 1 ? "" : "s"} left`}
                </p>
              )}
            </Td>
          </Tr>
        )}
      />

      <Dialog open={logging} onOpenChange={(open) => !open && setLogging(false)}>
        <DialogContent
          title="Log a request received by email"
          description="Same record as the dashboard and the notice link. The clock starts on receipt."
        >
          <LogRequestForm onDone={() => setLogging(false)} />
        </DialogContent>
      </Dialog>
    </>
  );
}

export default function RequestsPage() {
  return (
    <React.Suspense fallback={<PageSkeleton />}>
      <RequestsPageView />
    </React.Suspense>
  );
}

function PageSkeleton() {
  return (
    <div className="space-y-4" aria-hidden="true">
      <div className="shimmer h-8 w-64 rounded-lg" />
      <div className="shimmer h-14 rounded-xl" />
      <div className="shimmer h-72 rounded-xl" />
    </div>
  );
}
