/**
 * The ready-made audit reports: one question of the trail, for a period.
 * The shape of the answer first - how many, by event, by who - then the rows
 * a page at a time, newest first. An officer reads their own office's.
 */
"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import * as React from "react";

import { FilterBar, FilterSelect } from "@/components/data-display/resource-list";
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  EmptyState,
  Skeleton,
  Table,
  Td,
  Th,
  Tr,
} from "@/components/ui/primitives";
import { useAuditVocabulary } from "@/features/audit";
import { BreakdownBars } from "@/features/analytics/components/charts";
import { MakeReport } from "@/features/analytics/components/make-report";
import {
  periodParams,
  type AnalyticsFilters,
} from "@/features/analytics/components/toolbar";
import { roleTitle } from "@/features/analytics/format";
import { useAuditReport } from "@/features/analytics/queries";
import { formatDateTime, humanise } from "@/lib/format";
import type { AuditReportSummary, Catalogue } from "@/types";

const PAGE = 25;

export function AuditPanel({
  catalogue,
  filters,
  onMade,
}: {
  catalogue: Catalogue;
  filters: AnalyticsFilters;
  onMade: () => void;
}) {
  const reports = catalogue.audit_reports;
  const [key, setKey] = React.useState(reports[0]?.key ?? "");
  const period = periodParams(filters);
  // Cursor paging: the cursors of the pages before this one, kept for one
  // report and one period - choosing another starts again at the newest.
  const question = `${key}|${JSON.stringify(period)}`;
  const [paging, setPaging] = React.useState<{
    of: string;
    stack: string[];
    cursor?: string;
  }>({
    of: question,
    stack: [],
  });
  const here =
    paging.of === question
      ? paging
      : { of: question, stack: [] as string[], cursor: undefined };
  const { stack, cursor } = here;
  const setStack = (next: string[]) =>
    setPaging((p) => ({ ...(p.of === question ? p : here), stack: next }));
  const setCursor = (next: string | undefined) =>
    setPaging((p) => ({ ...(p.of === question ? p : here), cursor: next }));

  const query = useAuditReport(
    key,
    { ...(period ?? { period: "last_30_days" }), cursor, limit: PAGE },
    period !== null,
  );
  const vocabulary = useAuditVocabulary();
  const eventLabel = (e: string) => {
    const known = vocabulary.data?.event_types.find((x) => x.value === e);
    return known ? `${known.group_label}: ${known.label}` : humanise(e.replace(/\./g, " "));
  };

  if (reports.length === 0) return null;
  const info = reports.find((r) => r.key === key) ?? reports[0];
  const data = query.data;
  const summary = (data?.summary ?? {}) as AuditReportSummary;

  return (
    <div className="space-y-5">
      <FilterBar>
        <FilterSelect
          label="Audit report"
          value={key}
          onChange={(v) => v && setKey(v)}
          options={reports.map((r) => ({ value: r.key, label: r.title }))}
          allLabel={null}
        />
      </FilterBar>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <p className="max-w-3xl text-sm text-text-muted">{info.description}</p>
        {period && (
          <MakeReport
            catalogue={catalogue}
            kind="audit"
            params={{ ...period, audit: info.key }}
            onMade={onMade}
          />
        )}
      </div>

      {period === null ? null : query.isLoading ? (
        <Skeleton className="h-60" />
      ) : query.isError ? (
        <Alert tone="danger" title="Could not read this audit report">
          {query.error.userMessage()}
        </Alert>
      ) : data ? (
        <>
          <div className="grid gap-4 lg:grid-cols-[14rem_minmax(0,1fr)_minmax(0,1fr)]">
            <Card>
              <CardBody>
                <p className="text-[0.8125rem] font-medium text-text-muted">Entries</p>
                <p className="tabular mt-1.5 text-[1.75rem] leading-none font-semibold">
                  {data.total.toLocaleString("en-IN")}
                </p>
                <p className="mt-2 text-xs text-text-subtle">{data.period.label}</p>
              </CardBody>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">By event</CardTitle>
              </CardHeader>
              <CardBody>
                <BreakdownBars
                  label="Entries by event"
                  items={(summary.by_event ?? []).map((r) => ({
                    key: r.key,
                    label: eventLabel(r.key),
                    value: r.count,
                    text: r.count.toLocaleString("en-IN"),
                  }))}
                />
              </CardBody>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">By role</CardTitle>
              </CardHeader>
              <CardBody>
                <BreakdownBars
                  label="Entries by the role of who did it"
                  items={(summary.by_actor_role ?? []).map((r) => ({
                    key: r.key,
                    label: roleTitle(r.key),
                    value: r.count,
                    text: r.count.toLocaleString("en-IN"),
                  }))}
                />
              </CardBody>
            </Card>
          </div>

          <Card>
            {data.items.length === 0 ? (
              <EmptyState
                title="Nothing in this period"
                description="No entry of this report's events was recorded in the period."
              />
            ) : (
              <Table aria-label={`${info.title}, ${data.period.label}`}>
                <thead>
                  <tr>
                    <Th>When</Th>
                    <Th>Event</Th>
                    <Th>By</Th>
                    <Th>Role</Th>
                    <Th>About</Th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((row) => (
                    <Tr key={row.log_uuid}>
                      <Td className="whitespace-nowrap">
                        {formatDateTime(row.occurred_at)}
                      </Td>
                      <Td>{eventLabel(row.event_type)}</Td>
                      <Td>{row.actor_name ?? (row.actor_uuid ? "—" : "System")}</Td>
                      <Td>{roleTitle(row.actor_role)}</Td>
                      <Td>
                        {row.subject_name ??
                          (row.entity_type ? humanise(row.entity_type) : "—")}
                      </Td>
                    </Tr>
                  ))}
                </tbody>
              </Table>
            )}
            <div className="flex items-center justify-between gap-3 border-t border-border px-4 py-2.5 text-sm">
              <span className="text-text-muted">Page {stack.length + 1}</span>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  disabled={stack.length === 0}
                  onClick={() => {
                    const before = [...stack];
                    const prev = before.pop();
                    setStack(before);
                    setCursor(prev || undefined);
                  }}
                >
                  <ChevronLeft className="size-4" aria-hidden="true" />
                  Newer
                </Button>
                <Button
                  size="sm"
                  disabled={!data.next_cursor}
                  onClick={() => {
                    setStack([...stack, cursor ?? ""]);
                    setCursor(data.next_cursor ?? undefined);
                  }}
                >
                  Older
                  <ChevronRight className="size-4" aria-hidden="true" />
                </Button>
              </div>
            </div>
          </Card>
        </>
      ) : null}
    </div>
  );
}
