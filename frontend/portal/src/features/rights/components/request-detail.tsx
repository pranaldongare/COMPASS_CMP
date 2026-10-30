/**
 * One request, as the person entitled to it sees it (2026-10-30, mock-up B).
 *
 * Shared by her own page and a nominee's: a nominee under section 14 is the
 * person exercising the right, so what they are shown of a request they raised
 * is what she is shown of hers. Two copies would drift, and the one that
 * drifted would be the nominee's.
 *
 * Her answer first, when there is one, with its file and the way to dispute
 * it; then where the request stands, in four plain steps and the date she will
 * hear by; then what she asked. The office's working is not here: the clock's
 * internal checkpoints and the staff flow (what made the page clumsy), the
 * verification notes and the holders' tickets - the holders themselves are in
 * the answer. Everything recorded about it is one click away.
 *
 * Disputing is the one thing a nominee does not get from here. A dispute makes
 * a new request in her name, which is acting rather than reading, and acting
 * keeps its own door: the nominee page and a code to the contact she recorded.
 */
"use client";

import {
  ArrowDownRight,
  Check,
  Download,
  History,
  MessageSquareWarning,
  Minus,
  Paperclip,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import * as React from "react";
import { ActivityFeed } from "@/components/data-display/activity-feed";
import { FormError, useApiForm } from "@/components/forms";
import { Dialog, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { Alert, Button, Field, Mono, Textarea } from "@/components/ui/primitives";
import { downloadMyResponse, downloadMyResponseFile } from "@/features/rights/api";
import {
  OUTCOME_COPY,
  RequestStatusBadge,
  RequestTypeBadge,
} from "@/features/rights/components/copy";
import { useDispute } from "@/features/rights/mutations";
import { useMyRequestTrail } from "@/features/rights/queries";
import { excerpt } from "@/features/rights/relate";
import {
  disputeSchema,
  type DisputeForm as DisputeFormValues,
  type DisputeValues,
} from "@/features/rights/schemas";
import { cn, formatBytes, formatDate, formatDateTime, saveBlob } from "@/lib/format";
import { useToast } from "@/providers";
import type { MyRequest } from "@/types";

/* ------------------------------------------------------------- the steps */

export type StepState = "done" | "current" | "todo" | "skipped";

export interface Step {
  label: string;
  note?: string;
  state: StepState;
  /** A date that has passed without the step. */
  late?: boolean;
}

/** Outcomes that end a request before her data is gathered. */
const EARLY: readonly string[] = ["refused", "not_verified", "reclassified_withdrawal"];

/** Where a request stands, in four steps in her words. */
export function progressSteps(r: MyRequest): Step[] {
  const closed = r.status === "closed";
  const verified = r.verification_status === "verified";
  const unconfirmed = r.verification_status === "failed" || r.outcome === "not_verified";
  const grievance = r.request_type === "grievance";
  const ended = closed && EARLY.includes(r.outcome ?? "");

  const you: Step = verified
    ? { label: "We confirmed it was you", state: "done" }
    : unconfirmed
      ? { label: "We could not confirm it was you", state: "skipped" }
      : {
          label: "Confirm it was you",
          note: "with the code sent to the contact we hold",
          state: "current",
        };

  const started = r.status !== "received" || closed;
  const middle: Step = ended
    ? { label: grievance ? "Looked into" : "Data gathered", state: "skipped" }
    : closed
      ? { label: grievance ? "We looked into it" : "We gathered your data", state: "done" }
      : started
        ? {
            label: grievance ? "We are looking into it" : "We are gathering your data",
            note:
              r.status === "awaiting_holders"
                ? "from the teams that hold it"
                : r.status === "collating"
                  ? "preparing your answer"
                  : undefined,
            state: "current",
          }
        : {
            label: grievance ? "We look into it" : "We gather your data",
            note: verified ? "starting shortly" : undefined,
            state: verified ? "current" : "todo",
          };

  const answered = r.responded_at ?? r.closed_at;
  const answer: Step = closed
    ? {
        label: grievance ? "Decided" : "Answered",
        note: answered ? formatDate(answered) : undefined,
        state: "done",
      }
    : {
        label: grievance ? "Our decision" : "Your answer",
        note: r.clock.overdue
          ? `was due ${formatDate(r.due_at)}`
          : `by ${formatDate(r.due_at)}`,
        state: "todo",
        late: r.clock.overdue,
      };

  return [
    { label: "Received", note: formatDate(r.received_at), state: "done" },
    you,
    middle,
    answer,
  ];
}

function Progress({ request: r }: { request: MyRequest }) {
  const steps = progressSteps(r);
  return (
    <ol aria-label="Where it is" className="grid grid-cols-4">
      {steps.map((s, i) => (
        <li
          key={s.label}
          aria-current={s.state === "current" ? "step" : undefined}
          className={cn(
            "relative px-1 pt-7 text-center text-xs",
            // The line into each step from the one before, coloured once reached.
            i > 0 &&
              "before:absolute before:top-[9px] before:right-1/2 before:left-[-50%] before:h-[3px] before:bg-border",
            i > 0 &&
              (s.state === "done" || s.state === "current") &&
              "before:bg-[var(--accent)]",
          )}
        >
          <span
            className={cn(
              "absolute top-0 left-1/2 z-10 grid size-[21px] -translate-x-1/2 place-items-center rounded-full border-2 bg-surface",
              s.state === "done" && "border-[var(--accent)] bg-[var(--accent)] text-white",
              s.state === "current" &&
                "border-[var(--accent)] shadow-[0_0_0_4px_var(--accent-subtle)]",
              s.state === "todo" && "border-border",
              s.state === "skipped" && "border-border text-text-subtle",
            )}
            aria-hidden="true"
          >
            {s.state === "done" && <Check className="size-3" />}
            {s.state === "skipped" && <Minus className="size-3" />}
          </span>
          <span
            className={cn(
              "block font-medium",
              s.state === "todo" || s.state === "skipped" ? "text-text-muted" : "text-text",
            )}
          >
            {s.label}
          </span>
          {s.note && (
            <span className={cn("block", s.late ? "text-danger-text" : "text-text-muted")}>
              {s.note}
            </span>
          )}
        </li>
      ))}
    </ol>
  );
}

/* ------------------------------------------------------------- the detail */

const GOOD: readonly string[] = ["complete", "no_records", "upheld"];

export function RequestDetail({
  request: r,
  about,
  followedBy,
  canDispute = true,
  onJump,
}: {
  request: MyRequest;
  /** The request this one is about, when it is hers and on this page. */
  about: MyRequest | null;
  /** Her requests that point at this one: the grievance disputing it, or a re-run. */
  followedBy: MyRequest[];
  /** False for a nominee: a dispute is a new request in her name, and making
   *  one is acting rather than reading. */
  canDispute?: boolean;
  onJump: (uuid: string) => void;
}) {
  const toast = useToast();
  const [disputing, setDisputing] = React.useState(false);
  const [trailOpen, setTrailOpen] = React.useState(false);
  const trail = useMyRequestTrail(trailOpen ? r.request_uuid : undefined);
  const [downloading, setDownloading] = React.useState(false);
  const [fetching, setFetching] = React.useState<string | null>(null);

  function failed(err: unknown) {
    toast.error(
      "Could not download",
      err && typeof err === "object" && "userMessage" in err
        ? (err as { userMessage: () => string }).userMessage()
        : undefined,
    );
  }

  async function downloadFile(fileUuid: string, name: string) {
    setFetching(fileUuid);
    try {
      const file = await downloadMyResponseFile(r.request_uuid, fileUuid);
      saveBlob(file.blob, file.filename || name);
    } catch (err) {
      failed(err);
    } finally {
      setFetching(null);
    }
  }

  async function download() {
    setDownloading(true);
    try {
      const file = await downloadMyResponse(r.request_uuid);
      saveBlob(file.blob, file.filename);
      toast.success("Downloaded", "Keep it somewhere safe - the link is time-limited.");
    } catch (err) {
      failed(err);
    } finally {
      setDownloading(false);
    }
  }

  const closed = r.status === "closed";
  const grievance = r.request_type === "grievance";
  const answer = r.response_text ?? r.refusal_reason;
  const answered = r.responded_at ?? r.closed_at;

  return (
    <div className="space-y-5">
      <div>
        <h2 className="flex flex-wrap items-center gap-2 text-base font-semibold">
          <Mono>{r.reference}</Mono>
          <RequestTypeBadge type={r.request_type} />
          <RequestStatusBadge status={r.status} outcome={r.outcome} voice="self" />
        </h2>
        <p className="mt-1 text-xs text-text-muted">
          Sent {formatDateTime(r.received_at)}
          {closed && answered
            ? ` · answered ${formatDate(answered)}`
            : ` · you will hear by ${formatDate(r.due_at)}`}
          {r.linked_reference && !about && ` · about ${r.linked_reference}`}
        </p>
      </div>

      {r.verification_status === "pending" && (
        <Alert tone="warning">
          <p className="text-sm">
            We have not yet confirmed this came from you. Check the contact we hold for a
            code, or the Privacy Office will be in touch.
          </p>
        </Alert>
      )}

      {closed && answer && (
        <section
          aria-label={grievance ? "Our decision" : "Your answer"}
          className={cn(
            "rounded-lg border p-4",
            GOOD.includes(r.outcome ?? "")
              ? "border-success-border bg-success-subtle"
              : r.outcome === "partial"
                ? "border-warning-border bg-warning-subtle"
                : "border-border bg-bg-inset",
          )}
        >
          <p className="text-sm font-semibold">
            {grievance ? "Our decision" : "Your answer"}
            {r.outcome && (
              <span className="font-normal text-text-muted">
                {" "}
                · {OUTCOME_COPY[r.outcome].label}
              </span>
            )}
          </p>
          {r.responded_at && (
            <p className="text-xs text-text-muted">{formatDateTime(r.responded_at)}</p>
          )}
          <p className="mt-2 text-sm whitespace-pre-wrap">{answer}</p>
          {r.remedy_text && (
            <p className="mt-2 text-sm">
              <span className="font-medium">Remedy: </span>
              {r.remedy_text}
            </p>
          )}
          {r.response_files.length > 0 && (
            <ul className="mt-3 space-y-1">
              {r.response_files.map((f) => (
                <li key={f.file_uuid} className="flex flex-wrap items-center gap-2 text-sm">
                  <Paperclip className="size-3.5 text-text-subtle" aria-hidden="true" />
                  <span>{f.file_name}</span>
                  {r.download_available ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      loading={fetching === f.file_uuid}
                      onClick={() => downloadFile(f.file_uuid, f.file_name)}
                    >
                      <Download className="size-4" />
                      Download
                    </Button>
                  ) : (
                    <span className="text-xs text-text-subtle">download window closed</span>
                  )}
                </li>
              ))}
            </ul>
          )}
          {(r.download_available || (canDispute && !grievance)) && (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              {r.download_available && (
                <Button
                  variant="primary"
                  size="sm"
                  loading={downloading}
                  onClick={download}
                >
                  <Download className="size-4" />
                  Download your data
                </Button>
              )}
              {r.download_available && r.download_expires_at && (
                <span className="text-xs text-text-muted">
                  until {formatDate(r.download_expires_at)}
                </span>
              )}
              {canDispute && !grievance && (
                <Button variant="secondary" size="sm" onClick={() => setDisputing(true)}>
                  <MessageSquareWarning className="size-4" />
                  Dispute this answer
                </Button>
              )}
            </div>
          )}
          <p className="mt-3 text-xs text-text-subtle">
            Still not satisfied? You can complain to the Data Protection Board of India. The
            link is in every notice you were given.
          </p>
        </section>
      )}

      <section>
        <p className="mb-3 text-2xs font-semibold tracking-wide text-text-subtle uppercase">
          Where it is
        </p>
        <Progress request={r} />
      </section>

      <section className="space-y-2">
        <p className="text-2xs font-semibold tracking-wide text-text-subtle uppercase">
          You asked
        </p>
        {r.consent_uuid && (
          <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
            <ShieldCheck className="size-4 text-accent-text" aria-hidden="true" />
            <span className="font-medium">About one consent only:</span>
            <Link
              href={`/my-consents?consent=${r.consent_uuid}`}
              className="text-accent-text hover:underline"
            >
              {[
                r.consent_project,
                r.consent_notice_code &&
                  `${r.consent_notice_code} v${r.consent_notice_version ?? ""}`,
              ]
                .filter(Boolean)
                .join(" · ")}
              {r.consent_at && ` · given ${formatDate(r.consent_at)}`}
            </Link>
          </p>
        )}
        <p className="rounded-md bg-bg-inset p-3 text-sm whitespace-pre-wrap">
          {r.request_text}
        </p>
        {(r.attachments ?? []).length > 0 && (
          <ul className="space-y-1">
            {r.attachments.map((a) => (
              <li key={a.attachment_uuid} className="flex items-center gap-2 text-sm">
                <Paperclip className="size-3.5 text-text-subtle" aria-hidden="true" />
                <span className="min-w-0 truncate">{a.file_name}</span>
                <span className="text-xs text-text-muted">{formatBytes(a.size_bytes)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {about && <AboutBlock request={r} about={about} onJump={onJump} />}
      {followedBy.length > 0 && <FollowedBy followedBy={followedBy} onJump={onJump} />}

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

      <Dialog open={disputing} onOpenChange={(next) => !next && setDisputing(false)}>
        <DialogContent
          title={`Dispute ${r.reference}`}
          description="A grievance under section 13. Say what was wrong with the handling - late, incomplete, sent the wrong way, or the outcome itself."
        >
          <DisputeForm request={r} onDone={() => setDisputing(false)} />
        </DialogContent>
      </Dialog>
    </div>
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
      <p className="text-2xs font-semibold tracking-wide text-text-subtle uppercase">
        {disputing ? "What you disputed" : "Ordered by your grievance"}
      </p>
      <p className="mt-1 flex flex-wrap items-center gap-2 text-sm">
        <Mono>{about.reference}</Mono>
        <RequestTypeBadge type={about.request_type} />
        <RequestStatusBadge status={about.status} outcome={about.outcome} voice="self" />
        {about.responded_at && (
          <span className="text-xs text-text-muted">
            answered {formatDate(about.responded_at)}
          </span>
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
      <Button
        variant="ghost"
        size="sm"
        className="mt-2"
        onClick={() => onJump(about.request_uuid)}
      >
        <ArrowDownRight className="size-4" />
        See {about.reference}
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
          <RequestStatusBadge status={f.status} outcome={f.outcome} voice="self" />
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
    toast.success(
      `Grievance recorded as ${created.reference}`,
      "It is linked to the original request.",
    );
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
