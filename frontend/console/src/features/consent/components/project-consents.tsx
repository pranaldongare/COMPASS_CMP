/**
 * A project's consents, on the project's own page (2026-10-09).
 *
 * The project showed how many consents it holds and nothing more: to see them
 * meant going to Consents and filtering. Here they are - the current decision
 * of each person, at which site, how much was agreed and when - filtered by
 * site and status, each opening its record.
 */
"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { FilterBar, FilterSelect } from "@/components/data-display/resource-list";
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Skeleton,
  Table,
  Td,
  Th,
  Tr,
} from "@/components/ui/primitives";
import { StatusBadge } from "@/components/ui/status";
import { useConsents } from "@/features/consent/queries";
import { formatDateTime } from "@/lib/format";
import type { Uuid } from "@/types";

const STATUS_OPTIONS = [
  { value: "consented", label: "Full - every purpose" },
  { value: "partial", label: "Partial - some purposes" },
  { value: "declined", label: "Declined - no purpose" },
  { value: "withdrawn", label: "Withdrawn" },
];

const PAGE = 25;

/**
 * The status filter is the page's, so a figure in "At a glance" can open the
 * card already narrowed to what it counted.
 */
export function ProjectConsents({
  projectUuid,
  sites,
  status,
  onStatus,
}: {
  projectUuid: Uuid;
  sites: { site_uuid: Uuid; site_label: string }[];
  status: string;
  onStatus: (status: string) => void;
}) {
  const [site, setSite] = React.useState("");
  // The cursors of the pages before this one; the last is this page's. They
  // belong to one set of filters: any change starts again at the first page.
  const filters = `${status}|${site}`;
  const [paging, setPaging] = React.useState<{ filters: string; cursors: (string | undefined)[] }>({
    filters,
    cursors: [undefined],
  });
  const cursors = paging.filters === filters ? paging.cursors : [undefined];
  const setCursors = (next: (list: (string | undefined)[]) => (string | undefined)[]) =>
    setPaging({ filters, cursors: next(cursors) });
  const cursor = cursors[cursors.length - 1];
  const query = useConsents(projectUuid, {
    status: status || undefined,
    site: site || undefined,
    cursor,
    limit: PAGE,
  });
  const rows = query.data?.items ?? [];

  return (
    <Card id="consents" className="scroll-mt-20">
      <CardHeader className="flex flex-wrap items-center justify-between gap-2">
        <CardTitle>Consents</CardTitle>
        <span className="flex items-center gap-3">
          <span className="rounded-full bg-bg-inset px-2.5 py-0.5 text-xs font-medium tabular text-text-muted">
            {query.data?.total ?? 0}
          </span>
          <Link
            href={`/consents?project=${projectUuid}`}
            className="inline-flex items-center gap-1 text-xs text-accent-text hover:underline"
          >
            Open in Consents
            <ArrowRight className="size-3" aria-hidden="true" />
          </Link>
        </span>
      </CardHeader>
      <CardBody className="space-y-3">
        <FilterBar>
          <FilterSelect
            label="Site"
            value={site}
            onChange={setSite}
            options={sites.map((s) => ({ value: s.site_uuid, label: s.site_label }))}
            allLabel="All sites"
          />
          <FilterSelect
            label="Status"
            value={status}
            onChange={onStatus}
            options={STATUS_OPTIONS}
            allLabel="All statuses"
          />
        </FilterBar>

        {query.error ? (
          <Alert tone="danger">{query.error.userMessage()}</Alert>
        ) : query.isLoading ? (
          <Skeleton className="h-32" />
        ) : rows.length === 0 ? (
          <p className="text-sm text-text-muted">
            {status || site
              ? "No consent matches these filters."
              : "No consent yet. Records appear once somebody completes a consent link for this project."}
          </p>
        ) : (
          <>
            <Table>
              <caption className="sr-only">This project&apos;s consents</caption>
              <thead>
                <tr>
                  <Th>Data subject</Th>
                  <Th>Site</Th>
                  <Th>Status</Th>
                  <Th>Purposes</Th>
                  <Th>Given</Th>
                </tr>
              </thead>
              <tbody>
                {rows.map((c) => (
                  <Tr key={c.consent_uuid}>
                    <Td>
                      <Link href={`/consents/${c.consent_uuid}`} className="font-medium text-accent-text hover:underline">
                        {c.subject_name}
                      </Link>
                      <p className="mt-0.5 text-xs text-text-subtle">{c.subject_email ?? c.subject_mobile}</p>
                    </Td>
                    <Td className="text-text-muted">{c.site_label}</Td>
                    <Td>
                      <StatusBadge kind="consent" value={c.consent_status} />
                    </Td>
                    <Td className="tabular text-text-muted">
                      {c.granted_count} of {c.granted_count + c.refused_count}
                    </Td>
                    <Td className="whitespace-nowrap text-text-muted">{formatDateTime(c.affirmative_action_at)}</Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
            <div className="flex items-center justify-between gap-2">
              <Button
                variant="ghost"
                size="sm"
                disabled={cursors.length === 1}
                onClick={() => setCursors((list) => list.slice(0, -1))}
              >
                Previous
              </Button>
              <span className="text-xs text-text-muted">Page {cursors.length}</span>
              <Button
                variant="ghost"
                size="sm"
                disabled={!query.data?.next_cursor}
                onClick={() => setCursors((list) => [...list, query.data?.next_cursor ?? undefined])}
              >
                Next
              </Button>
            </div>
          </>
        )}
      </CardBody>
    </Card>
  );
}
