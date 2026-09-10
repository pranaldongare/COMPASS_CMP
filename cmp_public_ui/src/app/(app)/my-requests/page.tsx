/**
 * The data principal's requests - sections 11 to 14, from her side.
 *
 * What she sees of a request is what she is entitled to: the reference, the
 * clock, where it is on the path, and the response when there is one. The
 * verification notes and the holder tickets are ours and are not here; the
 * holders themselves are in the response, which is where they belong.
 *
 * Two things are one click away because the Act says they should be: making
 * a request, and disputing a response. A grievance is not an appeal against
 * the outcome alone - late, incomplete, or sent the wrong way all count.
 *
 * A grievance and the request it disputes are both hers, so they are both on
 * this page: the grievance card says what she disputed and jumps to it, and
 * the original says it was disputed and jumps back. No second page to find.
 */
"use client";

import { ArrowDownRight, Download, History, MessageSquareWarning, Plus, ShieldCheck } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { ActivityFeed } from "@/components/data-display/activity-feed";
import { FormError, useApiForm } from "@/components/forms";
import { PageHeader } from "@/components/layout/app-shell";
import { Dialog, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { EmptyRecords } from "@/components/ui/graphics";
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  EmptyState,
  Field,
  Mono,
  Skeleton,
  Textarea,
} from "@/components/ui/primitives";
import { downloadMyResponse } from "@/features/rights/api";
import { ClockColumn } from "@/features/rights/components/clock-column";
import { OUTCOME_COPY, RequestStatusBadge, RequestTypeBadge } from "@/features/rights/components/copy";
import { NominationCard } from "@/features/rights/components/nomination-card";
import { NomineeOfCard } from "@/features/rights/components/nominee-of-card";
import { Path } from "@/features/rights/components/path";
import { MyRequestForm } from "@/features/rights/components/request-form";
import { useDispute } from "@/features/rights/mutations";
import { useMyRequestTrail, useMyRequests } from "@/features/rights/queries";
import { excerpt, relate } from "@/features/rights/relate";
import {
  disputeSchema,
  type DisputeForm as DisputeFormValues,
  type DisputeValues,
} from "@/features/rights/schemas";
import { cn, formatDate, formatDateTime, saveBlob } from "@/lib/format";
import { useToast } from "@/providers";
import type { MyRequest } from "@/types";

function cardId(uuid: string): string {
  return `request-${uuid}`;
}

export default function MyRequestsPage() {
  const requests = useMyRequests();
  const [asking, setAsking] = React.useState(false);
  const [open, setOpen] = React.useState<string | null>(null);
  const [flash, setFlash] = React.useState<string | null>(null);
  const { byUuid, followers } = relate(requests.data ?? []);

  React.useEffect(() => {
    if (!flash) return;
    const timer = window.setTimeout(() => setFlash(null), 1800);
    return () => window.clearTimeout(timer);
  }, [flash]);

  function jump(uuid: string) {
    setOpen(uuid);
    setFlash(uuid);
    document.getElementById(cardId(uuid))?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <>
      <PageHeader
        title="Your requests"
        description="Ask for access to your data, a correction, erasure, or raise a grievance. Every request runs on a published clock, and you can see where it is."
        actions={
          <Button variant="primary" onClick={() => setAsking(true)}>
            <Plus className="size-4" />
            Make a request
          </Button>
        }
      />

      {requests.isLoading && <Skeleton className="h-40" />}
      {requests.error && (
        <Alert tone="danger" title="Could not load your requests">
          {requests.error.userMessage()}
        </Alert>
      )}
      {requests.data && requests.data.length === 0 && (
        <Card>
          <EmptyState
            illustration={<EmptyRecords />}
            title="No requests yet"
            description="When you make one, its reference, its deadline and its progress appear here."
          />
        </Card>
      )}

      <div className="space-y-4">
        {requests.data?.map((r) => (
          <RequestCard
            key={r.request_uuid}
            request={r}
            about={r.linked_request_uuid ? (byUuid.get(r.linked_request_uuid) ?? null) : null}
            followedBy={followers.get(r.request_uuid) ?? []}
            expanded={open === r.request_uuid}
            highlighted={flash === r.request_uuid}
            onToggle={() => setOpen(open === r.request_uuid ? null : r.request_uuid)}
            onJump={jump}
          />
        ))}
      </div>

      <div className="mt-8 space-y-6">
        {/* First: something somebody else needs from her is more pressing
            than something she may one day arrange. Absent when there is none. */}
        <NomineeOfCard />
        <NominationCard />
      </div>

      <Dialog open={asking} onOpenChange={(next) => !next && setAsking(false)}>
        <DialogContent
          title="Make a request"
          description="You are signed in, so this counts as verified and the clock starts now."
        >
          <MyRequestForm
            onDone={(created) => {
              setAsking(false);
              setOpen(created.request_uuid);
            }}
          />
        </DialogContent>
      </Dialog>
    </>
  );
}

function RequestCard({
  request: r,
  about,
  followedBy,
  expanded,
  highlighted,
  onToggle,
  onJump,
}: {
  request: MyRequest;
  /** The request this one is about, when it is hers and on this page. */
  about: MyRequest | null;
  /** Her requests that point at this one: the grievance disputing it, or a re-run. */
  followedBy: MyRequest[];
  expanded: boolean;
  highlighted: boolean;
  onToggle: () => void;
  onJump: (uuid: string) => void;
}) {
  const toast = useToast();
  const [disputing, setDisputing] = React.useState(false);
  const [trailOpen, setTrailOpen] = React.useState(false);
  const trail = useMyRequestTrail(trailOpen ? r.request_uuid : undefined);
  const [downloading, setDownloading] = React.useState(false);

  async function download() {
    setDownloading(true);
    try {
      const file = await downloadMyResponse(r.request_uuid);
      saveBlob(file.blob, file.filename);
      toast.success("Downloaded", "Keep it somewhere safe - the link is time-limited.");
    } catch (err) {
      toast.error(
        "Could not download",
        err && typeof err === "object" && "userMessage" in err
          ? (err as { userMessage: () => string }).userMessage()
          : undefined,
      );
    } finally {
      setDownloading(false);
    }
  }

  const closed = r.status === "closed";

  return (
    <Card
      id={cardId(r.request_uuid)}
      className={cn("scroll-mt-24 transition-shadow", highlighted && "ring-2 ring-[var(--accent)]")}
    >
      <CardHeader className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <CardTitle className="flex flex-wrap items-center gap-2">
            <Mono>{r.reference}</Mono>
            <RequestTypeBadge type={r.request_type} />
            <RequestStatusBadge status={r.status} outcome={r.outcome} />
          </CardTitle>
          <p className="mt-1 text-xs text-text-muted">
            Received {formatDateTime(r.received_at)} · you will hear by {formatDate(r.due_at)}
            {r.linked_reference && !about && ` · about ${r.linked_reference}`}
          </p>
        </div>
        <Button variant="ghost" size="sm" onClick={onToggle} aria-expanded={expanded}>
          {expanded ? "Hide" : "Show"} progress
        </Button>
      </CardHeader>

      <CardBody className="space-y-4">
        {r.consent_uuid && (
          <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
            <ShieldCheck className="size-4 text-accent-text" aria-hidden="true" />
            <span className="font-medium">About one consent only:</span>
            <Link href="/my-consents" className="text-accent-text hover:underline">
              {[r.consent_project, r.consent_notice_code && `${r.consent_notice_code} v${r.consent_notice_version ?? ""}`].filter(Boolean).join(" · ")}
              {r.consent_at && ` · given ${formatDate(r.consent_at)}`}
            </Link>
            <span className="text-text-muted">
              {r.consent_purposes && r.consent_purposes.length ? r.consent_purposes.join(", ") : "no purpose granted"}
            </span>
          </p>
        )}
        <p className="whitespace-pre-wrap text-sm text-text-muted">{r.request_text}</p>

        {about && <AboutBlock request={r} about={about} onJump={onJump} />}
        {followedBy.length > 0 && <FollowedBy followedBy={followedBy} onJump={onJump} />}

        {r.verification_status === "pending" && (
          <Alert tone="warning">
            <p className="text-sm">
              We have not yet confirmed this came from you. Check the contact we hold for a
              code, or the Privacy Office will be in touch.
            </p>
          </Alert>
        )}

        {closed && (r.response_text || r.refusal_reason) && (
          <div className="rounded-md border border-border bg-bg-inset p-4">
            <p className="text-2xs font-semibold uppercase tracking-wide text-text-subtle">
              Our response{r.responded_at && ` · ${formatDateTime(r.responded_at)}`}
            </p>
            <p className="mt-1 whitespace-pre-wrap text-sm">{r.response_text ?? r.refusal_reason}</p>
            {r.remedy_text && (
              <p className="mt-2 text-sm">
                <span className="font-medium">Remedy: </span>
                {r.remedy_text}
              </p>
            )}
            <div className="mt-3 flex flex-wrap gap-2">
              {r.download_available && (
                <Button variant="primary" size="sm" loading={downloading} onClick={download}>
                  <Download className="size-4" />
                  Download the file
                  {r.download_expires_at && (
                    <span className="text-xs opacity-80">until {formatDate(r.download_expires_at)}</span>
                  )}
                </Button>
              )}
              {r.request_type !== "grievance" && (
                <Button variant="secondary" size="sm" onClick={() => setDisputing(true)}>
                  <MessageSquareWarning className="size-4" />
                  Dispute this response
                </Button>
              )}
            </div>
            <p className="mt-3 text-xs text-text-subtle">
              If you remain unsatisfied you may complain to the Data Protection Board of India.
              The route to the Board is independent of ours, and the link is in every notice
              you were served.
            </p>
          </div>
        )}

        {expanded && (
          <div className="grid gap-6 md:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
            <div>
              <p className="mb-2 text-2xs font-semibold uppercase tracking-wide text-text-subtle">
                Clock
              </p>
              <ClockColumn clock={r.clock} closed={closed} compact />
            </div>
            <div>
              <p className="mb-2 text-2xs font-semibold uppercase tracking-wide text-text-subtle">
                The path
              </p>
              <Path request={r} />
            </div>
          </div>
        )}

        <div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setTrailOpen((v) => !v)}
            aria-expanded={trailOpen}
          >
            <History className="size-4" />
            {trailOpen ? "Hide" : "Show"} what was recorded
          </Button>
          {trailOpen && (
            <div className="mt-2">
              <ActivityFeed
                entries={trail.data}
                isLoading={trail.isLoading}
                order="oldest"
                emptyTitle="Nothing recorded yet"
              />
            </div>
          )}
        </div>
      </CardBody>

      <Dialog open={disputing} onOpenChange={(next) => !next && setDisputing(false)}>
        <DialogContent
          title={`Dispute ${r.reference}`}
          description="A grievance under section 13. Say what was wrong with the handling - late, incomplete, sent the wrong way, or the outcome itself."
        >
          <DisputeForm request={r} onDone={() => setDisputing(false)} />
        </DialogContent>
      </Dialog>
    </Card>
  );
}

/** On a grievance: what she disputed, and the answer she was given, so the
 * grievance reads on its own; one click opens the original. On a re-run: the
 * grievance that ordered it. */
function AboutBlock({
  request: r,
  about,
  onJump,
}: {
  request: MyRequest;
  about: MyRequest;
  onJump: (uuid: string) => void;
}) {
  const disputing = r.request_type === "grievance";
  const answer = excerpt(about.response_text ?? about.refusal_reason);
  return (
    <div className="rounded-md border border-border bg-bg-inset p-4">
      <p className="text-2xs font-semibold uppercase tracking-wide text-text-subtle">
        {disputing ? "What you disputed" : "Ordered by your grievance"}
      </p>
      <p className="mt-1 flex flex-wrap items-center gap-2 text-sm">
        <Mono>{about.reference}</Mono>
        <RequestTypeBadge type={about.request_type} />
        <RequestStatusBadge status={about.status} outcome={about.outcome} />
        {about.responded_at && (
          <span className="text-xs text-text-muted">answered {formatDate(about.responded_at)}</span>
        )}
      </p>
      {answer ? (
        <p className="mt-2 text-sm text-text-muted">
          <span className="font-medium text-text">
            {about.outcome ? `${OUTCOME_COPY[about.outcome].label}: ` : "Their answer: "}
          </span>
          {answer}
        </p>
      ) : (
        <p className="mt-2 text-sm text-text-muted">No answer had been given.</p>
      )}
      <Button variant="ghost" size="sm" className="mt-2" onClick={() => onJump(about.request_uuid)}>
        <ArrowDownRight className="size-4" />
        See {about.reference} in full
      </Button>
    </div>
  );
}

/** On the original: it was disputed, or re-run, and by which request. */
function FollowedBy({
  followedBy,
  onJump,
}: {
  followedBy: MyRequest[];
  onJump: (uuid: string) => void;
}) {
  return (
    <ul className="space-y-1 text-sm">
      {followedBy.map((f) => (
        <li key={f.request_uuid} className="flex flex-wrap items-center gap-2">
          <span className="text-text-muted">
            {f.request_type === "grievance" ? "You disputed this in" : "Re-run as"}
          </span>
          <Mono>{f.reference}</Mono>
          <RequestStatusBadge status={f.status} outcome={f.outcome} />
          <Button variant="ghost" size="sm" onClick={() => onJump(f.request_uuid)}>
            <ArrowDownRight className="size-4" />
            See it
          </Button>
        </li>
      ))}
    </ul>
  );
}

function DisputeForm({ request, onDone }: { request: MyRequest; onDone: () => void }) {
  const toast = useToast();
  const dispute = useDispute(request.request_uuid);
  const form = useApiForm<DisputeValues, DisputeFormValues>(disputeSchema, {
    text: "",
    about_dpo: false,
  });

  const submit = form.submit(async (values) => {
    const created = await dispute.mutateAsync(values);
    toast.success(`Grievance recorded as ${created.reference}`, "It is linked to the original request.");
    onDone();
  });

  return (
    <form method="post" onSubmit={submit} noValidate>
      <FormError message={form.formError} />
      <div className="space-y-4">
        <Field label="What was wrong" required error={form.formState.errors.text?.message}>
          {(p) => <Textarea {...p} rows={5} {...form.register("text")} />}
        </Field>
        <label className="flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            className="mt-0.5 size-4 rounded border-border-strong accent-[var(--accent)]"
            {...form.register("about_dpo")}
          />
          <span>
            This is about the Data Protection Officer&apos;s own decisions.
            <span className="block text-xs text-text-subtle">
              It will be reviewed by somebody independent of the DPO.
            </span>
          </span>
        </label>
      </div>
      <DialogFooter>
        <Button type="button" variant="ghost" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" loading={dispute.isPending}>
          Raise the grievance
        </Button>
      </DialogFooter>
    </form>
  );
}
