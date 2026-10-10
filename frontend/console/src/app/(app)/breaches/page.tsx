/**
 * Incidents and personal data breaches (S3-01, S3-06).
 *
 * An incident is logged first; validation says whether it is a personal data
 * breach, and the first yes records it with its own reference. The question
 * this page answers first is "which duty is due soonest, and which is
 * already late", so each breach lists its outstanding duties with the
 * server's clock. The DPO's alone: the server answers anyone else 404, and
 * the menu never offers them the page.
 *
 * Found by search - a reference (INC or BR), the title, where it occurred -
 * and narrowed by the questions the office asks of the register: what is
 * late or due today, what moved recently, what is still being validated,
 * where a ticket is waiting (2026-10-06). The filters live in the address,
 * so a filtered register can be bookmarked or shared. The register holds at
 * most 500 rows and its titles are sealed, so the narrowing happens here,
 * after the API client has opened them; every clock and count it reads is
 * the server's.
 */
"use client";

import { Plus, X } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { FilterBar, FilterSelect, SearchBox, useFilterParam } from "@/components/data-display/resource-list";
import { PageHeader } from "@/components/layout/app-shell";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { EmptyRecords } from "@/components/ui/graphics";
import {
  Alert,
  Button,
  Card,
  EmptyState,
  Mono,
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
import { cn, formatDateTime, formatRelative } from "@/lib/format";
import type { BreachStatus, BreachSummary } from "@/types";

const HOUR = 3_600_000;
const ACTIVITY: Record<string, { label: string; within: number }> = {
  "24h": { label: "In the last 24 hours", within: 24 * HOUR },
  "7d": { label: "In the last 7 days", within: 7 * 24 * HOUR },
  "30d": { label: "In the last 30 days", within: 30 * 24 * HOUR },
};
const FILTERS = ["q", "validation", "clock", "activity", "tickets", "sort"] as const;

const outstanding = (b: BreachSummary) => b.obligations.filter((d) => d.state === "outstanding");
const isLate = (b: BreachSummary) => outstanding(b).some((d) => d.clock.overdue || d.clock.past_target);
/** Seconds to the soonest outstanding due time; a late one is negative. */
const soonest = (b: BreachSummary): number | null => {
  const left = outstanding(b)
    .map((d) => d.clock.seconds_remaining)
    .filter((s): s is number => s !== null);
  return left.length ? Math.min(...left) : null;
};

function matches(b: BreachSummary, term: string): boolean {
  const haystack = [b.reference, b.incident_reference, b.breach_reference, b.title, locationText(b.location)]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return term
    .toLowerCase()
    .split(/\s+/)
    .every((word) => haystack.includes(word));
}

function BreachesPageView() {
  const [status, setStatus] = useFilterParam("status", "open");
  const [q, setQ] = useFilterParam("q");
  const [validation, setValidation] = useFilterParam("validation");
  const [clock, setClock] = useFilterParam("clock");
  const [activity, setActivity] = useFilterParam("activity");
  const [tickets, setTickets] = useFilterParam("tickets");
  const [sort, setSort] = useFilterParam("sort");
  const [recording, setRecording] = React.useState(false);
  const query = useBreaches(status === "all" ? undefined : (status as BreachStatus));

  // "Recent" is measured from when the register was fetched - each minute -
  // rather than the render's moment, which would make the filter impure.
  const now = query.dataUpdatedAt;
  const all = query.data ?? [];
  const rows = all
    .filter((b) => !q || matches(b, q))
    .filter((b) => !validation || b.determination === validation)
    .filter((b) => {
      if (clock === "overdue") return isLate(b);
      if (clock === "due_24h") {
        const s = soonest(b);
        return !isLate(b) && s !== null && s >= 0 && s <= 24 * 3600;
      }
      return true;
    })
    .filter((b) => {
      const window = ACTIVITY[activity];
      return !window || now - new Date(b.last_activity_at).getTime() <= window.within;
    })
    .filter((b) => {
      if (tickets === "open") return b.tickets_open > 0;
      if (tickets === "overdue") return b.tickets_overdue > 0;
      return true;
    });
  if (sort === "activity") {
    rows.sort((a, b) => new Date(b.last_activity_at).getTime() - new Date(a.last_activity_at).getTime());
  } else if (sort === "due") {
    // Late first, then soonest due; nothing due last, in the server's order.
    rows.sort((a, b) => (soonest(a) ?? Number.POSITIVE_INFINITY) - (soonest(b) ?? Number.POSITIVE_INFINITY));
  }
  const narrowed = FILTERS.some((name) => name !== "sort" && { q, validation, clock, activity, tickets }[name]);
  function clear() {
    setQ("");
    setValidation("");
    setClock("");
    setActivity("");
    setTickets("");
  }

  return (
    <>
      <PageHeader
        title="Incidents and personal data breaches"
        description="Section 8(6) and Rule 7, and CERT-In. Log an incident as it is noticed; the team validates whether it is a personal data breach, and a yes records it. The platform tracks every clock; people contain it, validate it, and submit to the Board and CERT-In through their own channels."
        actions={
          <Button variant="primary" onClick={() => setRecording(true)}>
            <Plus className="size-4" />
            Log an incident
          </Button>
        }
      />

      <FilterBar>
        <SearchBox
          label="Search"
          placeholder="INC-, BR-, title or place"
          value={q}
          onSubmit={setQ}
        />
        <StatusSelect value={status} onChange={setStatus} />
        <FilterSelect
          label="Validation"
          value={validation}
          onChange={setValidation}
          options={[
            { value: "pending", label: "Still validating" },
            { value: "yes", label: "A personal data breach" },
            { value: "no", label: "Not a personal data breach" },
          ]}
        />
        <FilterSelect
          label="Duties"
          value={clock}
          onChange={setClock}
          allLabel="Any"
          options={[
            { value: "overdue", label: "Overdue" },
            { value: "due_24h", label: "Due within 24 hours" },
          ]}
        />
        <FilterSelect
          label="Recent activity"
          value={activity}
          onChange={setActivity}
          allLabel="Any time"
          options={Object.entries(ACTIVITY).map(([value, a]) => ({ value, label: a.label }))}
        />
        <FilterSelect
          label="Tickets"
          value={tickets}
          onChange={setTickets}
          allLabel="Any"
          options={[
            { value: "open", label: "With an open ticket" },
            { value: "overdue", label: "Past their answer-by" },
          ]}
        />
        <FilterSelect
          label="Sort"
          value={sort}
          onChange={setSort}
          allLabel="Open first, newest noticed"
          options={[
            { value: "activity", label: "Most recent activity" },
            { value: "due", label: "Due soonest, late first" },
          ]}
        />
        {narrowed && (
          <Button variant="ghost" onClick={clear}>
            <X className="size-4" />
            Clear filters
          </Button>
        )}
      </FilterBar>

      {query.error ? (
        <Alert tone="danger" title="Could not load the register">
          {query.error.userMessage()}
        </Alert>
      ) : query.isLoading ? (
        <TableSkeleton cols={6} />
      ) : all.length === 0 ? (
        <EmptyState
          illustration={<EmptyRecords />}
          title={status === "open" ? "No open incident" : "No incident logged"}
          description="An incident is logged here as it is noticed, with the time it was first noticed."
        />
      ) : rows.length === 0 ? (
        <EmptyState
          illustration={<EmptyRecords />}
          title="Nothing matches"
          description="No incident in this register matches the search and filters."
          action={
            <Button variant="secondary" onClick={clear}>
              Clear filters
            </Button>
          }
        />
      ) : (
        <>
          {narrowed && (
            <p className="mb-2 text-sm text-text-muted" aria-live="polite">
              {rows.length} of {all.length} shown
            </p>
          )}
          <Card>
            <Table>
              <caption className="sr-only">Incidents and breaches, with every outstanding duty</caption>
              <thead>
                <tr>
                  <Th>Reference</Th>
                  <Th>Where</Th>
                  <Th>Validation</Th>
                  <Th>Outstanding duties</Th>
                  <Th>Tickets</Th>
                  <Th>Last activity</Th>
                  <Th>First noticed</Th>
                </tr>
              </thead>
              <tbody>
                {rows.map((b) => {
                  const due = outstanding(b);
                  const late = isLate(b);
                  return (
                    <Tr key={b.breach_uuid} className={cn(late && "bg-danger-subtle/40")}>
                      <Td>
                        <Link
                          href={`/breaches/${b.breach_uuid}`}
                          className="font-medium text-text hover:text-accent-text hover:underline"
                        >
                          <Mono>{b.reference}</Mono>
                        </Link>
                        {/* A recorded breach is quoted by its BR; the INC it was
                            logged as stays findable beside it. */}
                        {b.breach_reference && b.incident_reference !== b.breach_reference && (
                          <span className="block text-xs text-text-subtle">logged as {b.incident_reference}</span>
                        )}
                        <span className="block text-sm">{b.title}</span>
                        <BreachStatusBadge status={b.status} />
                      </Td>
                      <Td className="text-sm">{locationText(b.location)}</Td>
                      <Td>
                        <OutcomeBadge outcome={b.determination} />
                      </Td>
                      <Td className="text-sm">
                        {due.length === 0 ? (
                          <span className="text-text-muted">None</span>
                        ) : (
                          <ul className="space-y-1">
                            {due.map((d) => (
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
                      <Td className="text-sm">
                        {b.tickets_open === 0 ? (
                          <span className="text-text-muted">None open</span>
                        ) : (
                          <Link
                            href={`/breaches/${b.breach_uuid}#tickets`}
                            className="hover:underline"
                          >
                            {b.tickets_open} open
                            {b.tickets_overdue > 0 && (
                              <span className="block text-xs text-danger-text">
                                {b.tickets_overdue} past their answer-by
                              </span>
                            )}
                          </Link>
                        )}
                      </Td>
                      <Td className="text-sm" title={formatDateTime(b.last_activity_at)}>
                        {formatRelative(b.last_activity_at)}
                      </Td>
                      <Td className="text-sm">{formatDateTime(b.detected_at)}</Td>
                    </Tr>
                  );
                })}
              </tbody>
            </Table>
          </Card>
        </>
      )}

      <Dialog open={recording} onOpenChange={setRecording}>
        <DialogContent
          title="Log an incident"
          description="As it was noticed. Every time is entered, not filled in: the clocks run from what you type."
          size="lg"
        >
          <RecordBreachForm onDone={() => setRecording(false)} />
        </DialogContent>
      </Dialog>
    </>
  );
}

/** Open, closed or all: the one filter the API applies. Open by default. */
function StatusSelect({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <FilterSelect
      label="Show"
      value={value}
      onChange={onChange}
      options={[
        { value: "open", label: "Open" },
        { value: "closed", label: "Closed" },
        { value: "all", label: "All" },
      ]}
      allLabel={null}
    />
  );
}

export default function BreachesPage() {
  // useSearchParams (the filters' home) needs a boundary above it.
  return (
    <React.Suspense fallback={<TableSkeleton cols={6} />}>
      <BreachesPageView />
    </React.Suspense>
  );
}
