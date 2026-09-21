/**
 * The audit trail.
 *
 * Read-only for everyone, including the DPO reading it. There is no edit control
 * on this page because there is no edit endpoint behind it: the route is not
 * registered, the grant is revoked from the application role, and a database
 * trigger refuses the statement. The Privacy Office is audited by this table, and
 * a DPO who can edit her own audit trail makes it worthless as evidence.
 *
 * What the page is for is asking questions of the trail: what happened to this
 * consent record, what did this person do, what has been done about this data
 * principal, what happened in the rights area last week. The filters live in
 * the URL, so an answer can be bookmarked and handed to somebody else; the
 * summary strip describes the rows the filters select before the rows do; and
 * the same filters produce the CSV, so the file is the page.
 *
 * "Verify chain" walks the hash chain server-side. Each row carries a digest over
 * its own content and its predecessor's, so editing row N invalidates N and
 * everything after it - the answer is not "something changed" but "the trail is
 * sound up to exactly here".
 */
"use client";

import { CheckCircle2, Download, ShieldAlert, ShieldCheck } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import * as React from "react";

import { ActiveFilters } from "@/components/data-display/active-filters";
import {
  AuditDetailDialog,
  distinctSentence,
  EntityRef,
} from "@/components/data-display/audit-detail";
import { ResourceList, useCursorStack } from "@/components/data-display/resource-list";
import { PageHeader } from "@/components/layout/app-shell";
import { EmptyRecords } from "@/components/ui/graphics";
import { Alert, Button, Skeleton, Td, Tr } from "@/components/ui/primitives";
import { StatusBadge } from "@/components/ui/status";
import {
  downloadAudit,
  useAudit,
  useAuditSummary,
  useAuditVerify,
  useAuditVocabulary,
} from "@/features/audit";
import {
  AuditFilters,
  type AuditFilterState,
  describeFilters,
  EMPTY_FILTERS,
  FILTER_KEYS,
  toApiParams,
} from "@/features/audit/components/audit-filters";
import { AuditSummaryStrip } from "@/features/audit/components/audit-summary";
import { formatDateTime, humanise } from "@/lib/format";
import { useToast } from "@/providers";
import type { AuditEntry } from "@/types";

function AuditPage() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const stack = useCursorStack();
  const toast = useToast();

  // The URL is the state. Read once at mount; written on every change, with
  // `replace` so the back button leaves the page rather than undoing a filter.
  const [filters, setFilters] = React.useState<AuditFilterState>(() => {
    const initial = { ...EMPTY_FILTERS };
    for (const key of FILTER_KEYS) initial[key] = params.get(key) ?? "";
    return initial;
  });
  const [open, setOpen] = React.useState<AuditEntry | null>(null);
  const [verifying, setVerifying] = React.useState(false);
  const [downloading, setDownloading] = React.useState(false);

  function update(next: Partial<AuditFilterState>) {
    const merged = { ...filters, ...next };
    setFilters(merged);
    stack.reset();
    const qs = new URLSearchParams();
    for (const key of FILTER_KEYS) if (merged[key]) qs.set(key, merged[key]);
    const search = qs.toString();
    router.replace(search ? `${pathname}?${search}` : pathname, { scroll: false });
  }

  function clear(keys: (keyof AuditFilterState)[]) {
    const next: Partial<AuditFilterState> = {};
    for (const key of keys) next[key] = "";
    update(next);
  }

  const apiParams = React.useMemo(() => toApiParams(filters), [filters]);
  const vocabulary = useAuditVocabulary();
  const query = useAudit({ ...apiParams, cursor: stack.cursor, limit: 50 });
  const summary = useAuditSummary(apiParams);
  const verification = useAuditVerify(verifying);
  const chips = describeFilters(filters, vocabulary.data, clear);

  async function exportCsv() {
    setDownloading(true);
    try {
      const file = await downloadAudit(apiParams);
      const url = URL.createObjectURL(file.blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = file.filename;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(
        "Audit trail exported",
        `${file.filename} - the download is itself recorded in the trail.`,
      );
    } catch {
      toast.error("Could not export", "Nothing was downloaded.");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Oversight"
        title="Audit trail"
        description="Append-only and hash-chained. Nothing here can be edited or deleted by anyone, including the Privacy Office. Ask it a question: about a person, a record, an area, a period."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="secondary" loading={downloading} onClick={exportCsv}>
              <Download className="size-4" aria-hidden="true" />
              Export CSV
            </Button>
            <Button
              variant="secondary"
              loading={verification.isFetching}
              onClick={() => setVerifying(true)}
            >
              <ShieldCheck className="size-4" aria-hidden="true" />
              Verify chain
            </Button>
          </div>
        }
      />

      {verification.data && (
        <Alert
          tone={verification.data.intact ? "success" : "danger"}
          title={verification.data.intact ? "Chain intact" : "Chain broken"}
          className="mb-4"
        >
          <p className="flex items-start gap-2">
            {verification.data.intact ? (
              <CheckCircle2 className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            ) : (
              <ShieldAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            )}
            <span>{verification.data.message}</span>
          </p>
        </Alert>
      )}

      <AuditFilters value={filters} vocabulary={vocabulary.data} onChange={update} />

      <ActiveFilters filters={chips} onClearAll={() => update({ ...EMPTY_FILTERS })} />

      <AuditSummaryStrip
        summary={summary.data}
        vocabulary={vocabulary.data}
        isLoading={summary.isLoading}
      />

      <ResourceList<AuditEntry>
        query={query}
        stack={stack}
        caption="Audit entries, most recent first"
        columns={["When", "Event", "Actor", "About", "Record"]}
        keyOf={(e) => e.log_uuid}
        empty={{
          illustration: <EmptyRecords />,
          title: chips.length ? "Nothing matches these filters" : "No audit entries",
          description: chips.length
            ? "Widen the question: remove a filter, or extend the dates."
            : "Every write to the platform records one entry here.",
        }}
        row={(e) => (
          // The whole row opens the entry. A listing that shows `notice#42` and
          // offers no way to find out which notice is a log, not a trail.
          <Tr
            onClick={() => setOpen(e)}
            className="cursor-pointer"
            tabIndex={0}
            role="button"
            aria-label={`Open ${humanise(e.event_type.replace(/\./g, " "))}`}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                setOpen(e);
              }
            }}
          >
            <Td className="whitespace-nowrap text-text-muted">
              {formatDateTime(e.occurred_at)}
            </Td>
            <Td>
              <span className="font-medium">
                {humanise(e.event_type.replace(/\./g, " "))}
              </span>
              {/* Only where it says something the title does not. For an event
                  with no mapped sentence the fallback *is* the title, and
                  printing it twice reads as a rendering bug. */}
              {distinctSentence(e) && (
                <p className="mt-0.5 max-w-md text-xs text-text-subtle">
                  {distinctSentence(e)}
                </p>
              )}
            </Td>
            <Td>
              {/* Actor and subject are frequently different people: when a DCO
                  runs an export the actor is the DCO and the subject is nobody. */}
              {e.actor_name ? (
                <>
                  <span className="text-text-muted">{e.actor_name}</span>
                  {e.actor_role && (
                    <StatusBadge
                      kind="role"
                      value={e.actor_role}
                      dot={false}
                      className="ml-1.5"
                    />
                  )}
                </>
              ) : (
                <span className="text-xs text-text-subtle">system</span>
              )}
            </Td>
            <Td className="text-text-muted">
              {e.subject_name ?? <span className="text-xs text-text-subtle">—</span>}
            </Td>
            <Td className="max-w-xs">
              <EntityRef entry={e} />
            </Td>
          </Tr>
        )}
      />

      <AuditDetailDialog entry={open} onClose={() => setOpen(null)} />
    </>
  );
}

/**
 * `useSearchParams` reads the query string, which forces client rendering, so
 * the page sits under a Suspense boundary or Next refuses to prerender it.
 */
export default function AuditPageBoundary() {
  return (
    <React.Suspense fallback={<Skeleton className="h-64" />}>
      <AuditPage />
    </React.Suspense>
  );
}
