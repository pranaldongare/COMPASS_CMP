/**
 * Reports from the public link, waiting for an office (0058, ADR 0037).
 *
 * Both offices see them until one claims or dismisses them; nothing runs on
 * them until then. Claiming logs the incident under the number it arrived
 * with, in this office, where the other cannot see it. Dismissing keeps the
 * report with the reason, for either office to read later. Neither can be
 * undone, so each asks first.
 *
 * A stranger can fill the intake, and it has to stay readable while they do. So
 * the list comes a page at a time with only who sent each report and its title,
 * and the rest of a report is read when somebody presses Read it.
 */
"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Archive, Inbox } from "lucide-react";
import { useRouter } from "next/navigation";
import * as React from "react";

import { Dialog, DialogContent } from "@/components/ui/dialog";
import {
  Alert,
  Button,
  Card,
  CardHeader,
  CardTitle,
  DescriptionItem,
  DescriptionList,
  Field,
  Mono,
  Skeleton,
  Textarea,
} from "@/components/ui/primitives";
import {
  claimIncidentReport,
  dismissIncidentReport,
  getIncidentReport,
  listDismissedReports,
  listIncidentReports,
} from "@/features/breach/api";
import { LoggedDetails, REPORTED_CYBER_ATTACK } from "@/features/breach/components/logged-details";
import { messageOf } from "@/features/breach/components/record-breach";
import { ApiError } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { keys } from "@/lib/query";
import { useToast } from "@/providers";
import type { IncidentReportRow } from "@/types";

/** How many reports the list shows at a time: the server's own default. */
const PAGE = 50;

/** Everything here but the logged details comes from the list's row, so a
 *  report can be claimed or dismissed even when the rest of it cannot be read. */
function ReportDialog({ report, onClose }: { report: IncidentReportRow; onClose: () => void }) {
  const toast = useToast();
  const qc = useQueryClient();
  const router = useRouter();
  const [dismissing, setDismissing] = React.useState(false);
  const [reason, setReason] = React.useState("");
  const refresh = () => void qc.invalidateQueries({ queryKey: keys.breach.intake() });
  const claim = useMutation({
    mutationFn: () => claimIncidentReport(report.report_uuid),
    onSuccess: (breach) => {
      refresh();
      void qc.invalidateQueries({ queryKey: ["breaches"] });
      toast.success(`${breach.reference} is yours`, "It is now an incident in your office's register.");
      onClose();
      router.push(`/breaches/${breach.breach_uuid}`);
    },
    onError: (err) => {
      refresh();
      toast.error("Not claimed", messageOf(err, "The server refused."));
      // Somebody got there first, and the refusal has just said so.
      if (err instanceof ApiError && err.status === 409) onClose();
    },
  });
  const dismiss = useMutation({
    mutationFn: () => dismissIncidentReport(report.report_uuid, reason.trim()),
    onSuccess: () => {
      refresh();
      toast.success("Report dismissed", "It is kept, with your reason.");
      onClose();
    },
    onError: (err) => toast.error("Not dismissed", messageOf(err, "The server refused.")),
  });
  const full = useQuery({
    queryKey: keys.breach.intakeReport(report.report_uuid),
    queryFn: () => getIncidentReport(report.report_uuid),
    refetchOnMount: "always",
    refetchInterval: 60_000,
  });
  // An office may take it up while it is open here, and then there is nothing
  // left to act on. The server says so: a report gone from this page of the
  // list may only have moved to another.
  const taken = full.error instanceof ApiError && full.error.status === 409;
  const acting = claim.isPending || dismiss.isPending;
  React.useEffect(() => {
    if (!taken || acting) return;
    void qc.invalidateQueries({ queryKey: keys.breach.intake() });
    toast.warning("That report has been taken up", "An office claimed or dismissed it while it was open here.");
    onClose();
  }, [taken, acting, qc, toast, onClose]);
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent
        size="lg"
        title={`Reported incident ${report.reference}`}
        description="No clock has started. Claiming it logs it as an incident in your office; the other office then no longer sees it."
      >
        <div className="space-y-4">
          <DescriptionList>
            <DescriptionItem term="What">{report.title}</DescriptionItem>
            <DescriptionItem term="Reported by">
              {report.reporter_name}
              <span className="block text-xs text-text-subtle">{report.reporter_email}</span>
            </DescriptionItem>
            <DescriptionItem term="Arrived">{formatDateTime(report.received_at)}</DescriptionItem>
            <DescriptionItem term="They noticed it">
              {report.noticed_at ? formatDateTime(report.noticed_at) : "Not said"}
            </DescriptionItem>
            {report.cyber_attack && (
              <DescriptionItem term="Was it a cyber attack?">
                {REPORTED_CYBER_ATTACK[report.cyber_attack]}
              </DescriptionItem>
            )}
            {full.data && <LoggedDetails logged={full.data.logged} cyber={null} />}
          </DescriptionList>
          {full.isLoading && (
            <div role="status" aria-label="Reading the report">
              <Skeleton className="h-24" />
            </div>
          )}
          {full.error && !full.data && !taken && (
            <div className="space-y-2">
              <Alert tone="danger" title="The rest of this report could not be read">
                {messageOf(full.error, "Try again in a moment.")}
              </Alert>
              <Button variant="secondary" size="sm" loading={full.isFetching} onClick={() => void full.refetch()}>
                Read it again
              </Button>
            </div>
          )}
          {dismissing ? (
            <div className="space-y-2 border-t border-border pt-3">
              <Field label="Why is it being dismissed?" hint="Kept with the report" required>
                {(p) => <Textarea {...p} rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />}
              </Field>
              <div className="flex justify-end gap-2">
                <Button variant="ghost" onClick={() => setDismissing(false)}>
                  Back
                </Button>
                <Button
                  variant="primary"
                  disabled={!reason.trim()}
                  loading={dismiss.isPending}
                  onClick={() => dismiss.mutate()}
                >
                  Dismiss the report
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex flex-wrap justify-end gap-2">
              <Button variant="ghost" onClick={onClose}>
                Close
              </Button>
              <Button variant="secondary" onClick={() => setDismissing(true)}>
                Dismiss
              </Button>
              <Button variant="primary" loading={claim.isPending} onClick={() => claim.mutate()}>
                Claim for my office
              </Button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

/** Nothing while nothing waits: the register is the page's work. */
export function IntakeCard() {
  // The row, not its uuid: it may leave this page while it is open here.
  const [opened, setOpened] = React.useState<IncidentReportRow | null>(null);
  const [offset, setOffset] = React.useState(0);
  const query = useQuery({
    queryKey: keys.breach.intakePage(offset),
    queryFn: () => listIncidentReports({ limit: PAGE, offset }),
    refetchInterval: 60_000,
    // The page on the screen stays until the next has come.
    placeholderData: keepPreviousData,
  });
  const rows = query.data?.items ?? [];
  const total = query.data?.total ?? 0;
  const turning = query.isPlaceholderData;
  // Reports taken up can leave the last page with nothing on it. Put right
  // while rendering, so that empty page never reaches the screen.
  const lastPage = Math.max(Math.floor((total - 1) / PAGE), 0) * PAGE;
  if (query.data && !turning && offset > lastPage) setOffset(lastPage);
  return (
    <>
      {query.error && !query.data && (
        <div className="mb-6">
          <Alert tone="danger" title="Reports from the public link could not be read">
            {messageOf(query.error, "Try again in a moment.")}
          </Alert>
        </div>
      )}
      {total > 0 && (
        <Card className="mb-6" data-testid="incident-intake">
          <CardHeader>
            <CardTitle>
              <Inbox className="mr-2 inline size-4" aria-hidden="true" />
              Reported through the public link ({total})
            </CardTitle>
            <p className="mt-1 text-xs text-text-muted">
              Waiting for an office, the oldest first. The DPO and Legal both see these until one claims or dismisses
              them.
            </p>
          </CardHeader>
          <ul className="divide-y divide-border">
            {rows.map((r) => (
              <li key={r.report_uuid} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium">{r.title}</p>
                  <p className="text-xs text-text-muted">
                    <Mono>{r.reference}</Mono> · {r.reporter_name} · {formatDateTime(r.received_at)}
                  </p>
                </div>
                <Button variant="secondary" size="sm" onClick={() => setOpened(r)}>
                  Read it
                </Button>
              </li>
            ))}
          </ul>
          {total > PAGE && (
            <div className="flex items-center justify-between gap-2 border-t border-border px-5 py-2">
              <Button
                variant="ghost"
                size="sm"
                disabled={offset === 0 || turning}
                onClick={() => setOffset(Math.max(offset - PAGE, 0))}
              >
                Previous
              </Button>
              <span className="text-xs text-text-muted">
                {offset + 1} to {offset + rows.length} of {total}
              </span>
              <Button
                variant="ghost"
                size="sm"
                disabled={offset + rows.length >= total || turning}
                onClick={() => setOffset(offset + PAGE)}
              >
                Next
              </Button>
            </div>
          )}
        </Card>
      )}
      {opened && <ReportDialog report={opened} onClose={() => setOpened(null)} />}
    </>
  );
}

function DismissedDialog({ onClose }: { onClose: () => void }) {
  const query = useQuery({
    queryKey: [...keys.breach.intake(), "dismissed"],
    queryFn: listDismissedReports,
  });
  const rows = query.data ?? [];
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent
        size="lg"
        title="Dismissed reports"
        description="Reports from the public link that an office did not take up, the latest first, with who dismissed each and why."
      >
        {query.isLoading ? (
          <Skeleton className="h-40" />
        ) : query.error && !query.data ? (
          <Alert tone="danger">{query.error.message}</Alert>
        ) : rows.length === 0 ? (
          <p className="text-sm text-text-muted">No report has been dismissed.</p>
        ) : (
          <ul className="divide-y divide-border">
            {rows.map((r) => (
              <li key={r.reference} className="space-y-1 py-3 first:pt-0 last:pb-0">
                <p className="text-sm font-medium break-words">{r.title}</p>
                <p className="text-xs text-text-muted">
                  <Mono>{r.reference}</Mono> · arrived {formatDateTime(r.received_at)}
                </p>
                {/* Erased under a rights request. The request is one office's, and
                    both offices read this list, so it is not named. */}
                {r.reporter_erased_at ? (
                  <p className="text-xs text-text-muted">
                    Reporter&apos;s name and email erased {formatDateTime(r.reporter_erased_at)}, at their request
                  </p>
                ) : (
                  <p className="text-xs break-words text-text-muted">
                    Reported by {[r.reporter_name, r.reporter_email].filter(Boolean).join(", ")}
                  </p>
                )}
                <p className="text-xs text-text-muted">
                  Dismissed {formatDateTime(r.dismissed_at)} by {r.dismissed_by_name ?? "unknown"}
                </p>
                <p className="rounded bg-bg-inset px-2 py-1 text-xs break-words whitespace-pre-wrap text-text">
                  “{r.dismissal_reason}”
                </p>
              </li>
            ))}
          </ul>
        )}
      </DialogContent>
    </Dialog>
  );
}

/** What became of the reports nobody took up, whether or not any wait now: the
 *  office a report mattered to may only hear of it after the other dismissed it. */
export function DismissedReportsButton() {
  const [open, setOpen] = React.useState(false);
  return (
    <>
      <Button variant="secondary" onClick={() => setOpen(true)}>
        <Archive className="size-4" />
        Dismissed reports
      </Button>
      {open && <DismissedDialog onClose={() => setOpen(false)} />}
    </>
  );
}
