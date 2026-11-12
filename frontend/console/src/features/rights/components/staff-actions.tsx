/**
 * The DPO's decisions on one request, before and around the holders.
 *
 * Steps 2 to 4 of every flow, and the early exits attached to them: verify
 * identity (session, a code to the stored channel, or manually with a reason),
 * classify what arrived, confirm withdrawal-versus-erasure, decide whether a
 * nominee's event is evidenced, and - for a grievance - recuse the DPO. Then
 * the transitions the server offers, rendered from its answer with each
 * blocker's reason, the way the project controls are.
 *
 * Every button here calls the server and shows its sentence. Nothing decides
 * locally what may happen next.
 */
"use client";

import { AlertTriangle, ArrowLeft, ArrowRight, Ban, Lock } from "lucide-react";
import * as React from "react";

import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Field,
  Input,
  Select,
  Textarea,
} from "@/components/ui/primitives";
import { REQUEST_TYPE_COPY, STATUS_COPY } from "@/features/rights/components/copy";
import { ReleaseFiles } from "@/features/rights/components/release-files";
import {
  useAssignReviewer,
  useClassify,
  useConfirmIntent,
  useConfirmVerificationCode,
  useEscalate,
  useFailVerification,
  useRecordEvent,
  useRefuse,
  useSendVerificationCode,
  useTransitionRequest,
  useTreatAsWithdrawal,
  useVerifyManually,
} from "@/features/rights/mutations";
import {
  AUTOMATIC,
  holdersNotYetFound,
} from "@/features/rights/components/request-summary";
import { useUsers } from "@/features/users";
import { isApiError } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { useAuth, useToast } from "@/providers";
import type { RightsRequestDetail, RightsRequestType } from "@/types";
import { RIGHTS_REQUEST_TYPES, RIGHTS_REQUEST_TYPES_TAKEN } from "@/types";

function messageOf(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}

/* ------------------------------------------------------------ verification */

/** The states a request may still be closed as not verified from; the server
 *  asks whether a code has somewhere to go only in these. */
const BEFORE_COLLATION: ReadonlySet<string> = new Set(["received", "in_progress", "awaiting_holders"]);

/** Said to anybody but the DPO and Legal on a request with no account: a code
 *  there is theirs to send or confirm, and the server refuses everybody else
 *  alike (`officers_only`), whatever the register holds. */
const OFFICERS_ONLY =
  "Only the DPO or the Legal office can send or confirm a code for a request with no account. " +
  "Verify manually, or close as not verified.";

/** Where a code to a stored channel would go, as the server answers it
 *  (`code_channel`, 0065): the account's contact, the address a dismissed
 *  report from the public link came from, nowhere, or not known just now. The
 *  server answers only the DPO and Legal, and only while identity waits. For
 *  anyone else a request with an account offers the account's contact, and
 *  one with none says only that a code is the officers': whether a channel is
 *  held for it is a fact about the register, which is theirs. */
function storedChannel(
  r: RightsRequestDetail,
  officer: boolean,
): { offered: boolean; says: string } {
  const account = {
    offered: true,
    says: `Sent to the contact we hold for ${r.subject_name ?? "this person"} - never to what was typed on the form.`,
  };
  const nowhere = {
    offered: false,
    says: "No account matches this contact, so there is no stored channel. Verify manually, or close as not verified.",
  };
  if (!officer && !r.subject_uuid) return { offered: false, says: OFFICERS_ONLY };
  if (r.code_channel === true) {
    return r.subject_uuid
      ? account
      : {
          offered: true,
          says:
            "Sent to the address a report the requester sent through the public link came from - never to what " +
            "was typed on the form. The public form may have sent one already.",
        };
  }
  if (r.code_channel === false) return nowhere;
  if (officer && r.verification_status === "pending" && BEFORE_COLLATION.has(r.status) && !r.subject_uuid) {
    return {
      offered: false,
      says: "Whether a code can go to a stored channel could not be checked just now: the key service did not answer. Reload to try again.",
    };
  }
  return r.subject_uuid ? account : nowhere;
}

export function VerificationCard({ request: r }: { request: RightsRequestDetail }) {
  const toast = useToast();
  const { me } = useAuth();
  const officer = me?.role === "dpo" || me?.role === "legal";
  // The server's own refusal of a code, once it has given one: it stands for
  // this request whatever the page thought, so the code is offered no more.
  const [refused, setRefused] = React.useState<string | null>(null);
  const channel = refused ? { offered: false, says: refused } : storedChannel(r, officer);
  const uuid = r.request_uuid;
  const send = useSendVerificationCode(uuid);
  const confirm = useConfirmVerificationCode(uuid);
  const manual = useVerifyManually(uuid);
  const fail = useFailVerification(uuid);
  const [code, setCode] = React.useState("");
  const [note, setNote] = React.useState("");
  const [failing, setFailing] = React.useState(false);

  const closed = r.status === "closed";

  async function run<T>(fn: () => Promise<T>, title: string) {
    try {
      await fn();
      toast.success(title);
    } catch (err) {
      // Send a code or Confirm on a request with no account, by anybody but
      // the DPO or Legal: refused alike whatever the register holds.
      if (isApiError(err) && err.code === "officers_only") setRefused(err.userMessage());
      toast.error("Not done", messageOf(err, "The server refused."));
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>3 · Identity verified?</CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          session · code to a stored channel · manual, with reason recorded
        </p>
      </CardHeader>
      <CardBody className="space-y-3">
        {r.verification_status === "verified" && (
          <Alert tone="success">
            <p className="text-sm">
              Verified by {r.verification_method}
              {r.verified_at && ` on ${formatDateTime(r.verified_at)}`}
              {r.verified_by_name && ` (${r.verified_by_name})`}.
              {r.verification_note && (
                <span className="mt-1 block text-xs italic">&ldquo;{r.verification_note}&rdquo;</span>
              )}
            </p>
          </Alert>
        )}
        {r.verification_status === "failed" && (
          <Alert tone="danger">
            <p className="text-sm">
              Not satisfied. The requester was told nothing either way, and may try again.
              {r.verification_note && <span className="block text-xs italic">&ldquo;{r.verification_note}&rdquo;</span>}
            </p>
          </Alert>
        )}

        {r.verification_status === "pending" && !closed && (
          <div className="space-y-4">
            <div className="rounded-md border border-border p-3">
              <p className="text-sm font-medium">A code to the stored channel</p>
              <p className="mt-0.5 text-xs text-text-muted">{channel.says}</p>
              {channel.offered && (
                <div className="mt-2 flex flex-wrap items-end gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    loading={send.isPending}
                    onClick={() => run(() => send.mutateAsync(), "Code sent")}
                  >
                    Send a code
                  </Button>
                  <Field label="Code the requester read back">
                    {(p) => (
                      <Input
                        {...p}
                        value={code}
                        onChange={(e) => setCode(e.target.value)}
                        inputMode="numeric"
                        maxLength={10}
                        className="w-32"
                      />
                    )}
                  </Field>
                  <Button
                    variant="primary"
                    size="sm"
                    disabled={code.length < 4}
                    loading={confirm.isPending}
                    onClick={() => run(() => confirm.mutateAsync(code), "Identity verified")}
                  >
                    Confirm
                  </Button>
                </div>
              )}
            </div>

            <div className="rounded-md border border-border p-3">
              <p className="text-sm font-medium">Manually, with the reason recorded</p>
              <Field label="How identity was established" hint="Recorded in the trail. The reason is the control.">
                {(p) => <Textarea {...p} rows={2} value={note} onChange={(e) => setNote(e.target.value)} />}
              </Field>
              <div className="mt-2 flex flex-wrap gap-2">
                <Button
                  variant="primary"
                  size="sm"
                  disabled={note.trim().length < 3}
                  loading={manual.isPending}
                  onClick={() => run(() => manual.mutateAsync(note.trim()), "Identity verified")}
                >
                  Record as verified
                </Button>
                <Button variant="subtle" size="sm" onClick={() => setFailing((v) => !v)}>
                  No match, or not satisfied
                </Button>
              </div>
              {failing && (
                <Alert tone="warning" className="mt-3">
                  <p className="text-sm">
                    Closes the request as not verified and audits it. The requester gets a
                    neutral message - nothing is confirmed either way - and may try again.
                  </p>
                  <Button
                    variant="primary"
                    size="sm"
                    className="mt-2"
                    loading={fail.isPending}
                    onClick={() => run(() => fail.mutateAsync(note.trim() || null), "Closed as not verified")}
                  >
                    Close as not verified
                  </Button>
                </Alert>
              )}
            </div>
          </div>
        )}
      </CardBody>
    </Card>
  );
}

/* ------------------------------------------------------- classification */

export function ClassificationCard({ request: r }: { request: RightsRequestDetail }) {
  const toast = useToast();
  const { me } = useAuth();
  const uuid = r.request_uuid;
  const classify = useClassify(uuid);
  const refuse = useRefuse(uuid);
  const withdrawal = useTreatAsWithdrawal(uuid);
  const intent = useConfirmIntent(uuid);
  const event = useRecordEvent(uuid);
  const escalate = useEscalate(uuid);
  const assign = useAssignReviewer(uuid);

  const [type, setType] = React.useState<RightsRequestType>(r.request_type);
  const [note, setNote] = React.useState("");
  const [reason, setReason] = React.useState("");
  const [refusing, setRefusing] = React.useState(false);
  const [refusalFiles, setRefusalFiles] = React.useState<File[]>([]);
  const [reviewer, setReviewer] = React.useState("");

  const admins = useUsers({ role: "admin", status: "active", limit: 100 });
  const closed = r.status === "closed";
  const beforeCollation = !closed && r.status !== "collating";
  const isAdmin = me?.role === "admin";

  async function run<T>(fn: () => Promise<T>, title: string) {
    try {
      await fn();
      toast.success(title);
    } catch (err) {
      toast.error("Not done", messageOf(err, "The server refused."));
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          4 ·{" "}
          {r.request_type === "erasure"
            ? "Withdrawal, or erasure?"
            : r.request_type === "grievance"
              ? "Linked, and about whom?"
              : `A valid ${REQUEST_TYPE_COPY[r.request_type].label.toLowerCase()} request?`}
        </CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          The DPO can reclassify anything that arrived as free text. The clock does not restart.
        </p>
      </CardHeader>
      <CardBody className="space-y-4">
        {r.classified_at ? (
          <Alert tone="success">
            <p className="text-sm">
              Classified as {REQUEST_TYPE_COPY[r.request_type].label.toLowerCase()} on{" "}
              {formatDateTime(r.classified_at)}
              {r.original_type && ` (arrived as ${REQUEST_TYPE_COPY[r.original_type].label.toLowerCase()})`}.
            </p>
          </Alert>
        ) : (
          beforeCollation &&
          !isAdmin && (
            <div className="flex flex-wrap items-end gap-2">
              <Field label="This is a request for">
                {(p) => (
                  <Select {...p} value={type} onChange={(e) => setType(e.target.value as RightsRequestType)}>
                    {RIGHTS_REQUEST_TYPES.filter(
                      (t) => (RIGHTS_REQUEST_TYPES_TAKEN as readonly string[]).includes(t) || t === r.request_type,
                    ).map((t) => (
                      <option key={t} value={t}>
                        {REQUEST_TYPE_COPY[t].label} ({REQUEST_TYPE_COPY[t].section})
                      </option>
                    ))}
                  </Select>
                )}
              </Field>
              <Button
                variant="primary"
                size="sm"
                loading={classify.isPending}
                onClick={() => run(() => classify.mutateAsync({ request_type: type, note: note || null }), "Classified")}
              >
                Confirm classification
              </Button>
            </div>
          )
        )}

        {r.request_type === "erasure" && beforeCollation && !r.intent_confirmed_at && (
          <div className="rounded-md border border-warning-border bg-warning-subtle p-3">
            <p className="text-sm font-medium text-warning-text">Does the requester mean erasure, or withdrawal?</p>
            <p className="mt-0.5 text-xs text-text-muted">
              Withdrawal stops future processing, and the requester can do it from their consent record.
              Erasure removes data already collected. Confirm which before anything is deleted.
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              <Button variant="primary" size="sm" loading={intent.isPending} onClick={() => run(() => intent.mutateAsync(), "Erasure confirmed")}>
                They mean erasure
              </Button>
              <Button variant="secondary" size="sm" loading={withdrawal.isPending} onClick={() => run(() => withdrawal.mutateAsync(note || null), "Handled as withdrawal")}>
                They meant withdrawal
              </Button>
            </div>
          </div>
        )}
        {r.intent_confirmed_at && (
          <p className="text-xs text-text-muted">Erasure confirmed on {formatDateTime(r.intent_confirmed_at)}.</p>
        )}

        {r.channel === "nominee" && beforeCollation && !r.trigger_evidenced_at && (
          <div className="rounded-md border border-warning-border bg-warning-subtle p-3">
            <p className="text-sm font-medium text-warning-text">Is the triggering event evidenced?</p>
            <p className="mt-0.5 text-xs text-text-muted">
              {r.nominee_name} says {r.trigger_event === "death" ? "the principal has died" : "the principal cannot act"}.
              What we accept as proof is a Legal decision, published and applied consistently.
              {r.trigger_evidence_hash && " Evidence was attached - download it from the header."}
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              <Button variant="primary" size="sm" loading={event.isPending} onClick={() => run(() => event.mutateAsync({ evidenced: true, note: note || null }), "Event evidenced")}>
                Evidenced to our standard
              </Button>
              <Button variant="secondary" size="sm" loading={event.isPending} onClick={() => run(() => event.mutateAsync({ evidenced: false, note: note || null }), "Refused - not evidenced")}>
                Not evidenced - refuse
              </Button>
            </div>
          </div>
        )}
        {r.trigger_evidenced_at && (
          <p className="text-xs text-text-muted">Event evidenced on {formatDateTime(r.trigger_evidenced_at)}.</p>
        )}

        {r.request_type === "grievance" && (
          <div className="rounded-md border border-border p-3">
            <p className="text-sm font-medium">Is the complaint about the DPO?</p>
            {r.about_dpo ? (
              <div className="mt-1 space-y-2 text-xs text-text-muted">
                <p>
                  Yes - escalated to an independent reviewer
                  {r.escalated_at && ` on ${formatDateTime(r.escalated_at)}`}.
                  {r.reviewer_name ? ` Reviewer: ${r.reviewer_name}.` : " No reviewer assigned yet."}
                </p>
                {isAdmin && !closed && (
                  <div className="flex flex-wrap items-end gap-2">
                    <Field label="Reviewer" hint="An administrator - somebody who is not the DPO.">
                      {(p) => (
                        <Select {...p} value={reviewer} onChange={(e) => setReviewer(e.target.value)}>
                          <option value="">Choose…</option>
                          {(admins.data?.items ?? []).map((u) => (
                            <option key={u.uuid} value={u.uuid}>
                              {u.full_name} · {u.email}
                            </option>
                          ))}
                        </Select>
                      )}
                    </Field>
                    <Button variant="primary" size="sm" disabled={!reviewer} loading={assign.isPending} onClick={() => run(() => assign.mutateAsync(reviewer), "Reviewer assigned")}>
                      Assign
                    </Button>
                  </div>
                )}
              </div>
            ) : (
              !closed &&
              !isAdmin && (
                <div className="mt-1">
                  <p className="text-xs text-text-muted">
                    The DPO owns grievances, including ones about the DPO&apos;s own decisions - and that is a
                    real conflict. Recuse if this concerns your handling.
                  </p>
                  <Button variant="subtle" size="sm" className="mt-2" loading={escalate.isPending} onClick={() => run(() => escalate.mutateAsync(), "Escalated to an independent reviewer")}>
                    Escalate (about me)
                  </Button>
                </div>
              )
            )}
          </div>
        )}

        {beforeCollation && !isAdmin && (
          <div className="space-y-2">
            <Field label="Note" hint="Optional. Recorded with whichever decision you take.">
              {(p) => <Textarea {...p} rows={2} value={note} onChange={(e) => setNote(e.target.value)} />}
            </Field>
            {/* The other way out of step 4 (2026-10-07): a button that reads
                as one, with what it does beside it - it was a grey line of
                text the DPO did not know could be clicked. */}
            <div className="rounded-md border border-border p-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium">Not a rights request, or cannot be met?</p>
                  <p className="mt-0.5 text-xs text-text-muted">
                    Refuse it with a written reason. The requester is told why, with the grievance
                    route, and the request closes.
                  </p>
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  className="border-danger-border text-danger-text hover:border-danger-border hover:bg-danger-subtle"
                  aria-expanded={refusing}
                  onClick={() => setRefusing((v) => !v)}
                >
                  <Ban className="size-4" />
                  {refusing ? "Keep the request" : "Refuse this request"}
                </Button>
              </div>
              {refusing && (
                <div className="mt-3 rounded-md border border-danger-border bg-danger-subtle p-3">
                  <Field label="Reason, in writing" hint="Sent to the requester with the grievance route. A refusal is still a response." required>
                    {(p) => <Textarea {...p} rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />}
                  </Field>
                  {/* A refusal may rest on a document - a letter, the
                      retention schedule, an order - and it goes with the
                      reason, as files go with a response (2026-11-12). */}
                  <div className="mt-3">
                    <ReleaseFiles
                      label="Documents sent with the refusal"
                      hint="A letter, the retention schedule, an order. PDF, image, CSV or text, up to 25 MB each. The requester downloads them from their account."
                      files={refusalFiles}
                      onChange={setRefusalFiles}
                    />
                  </div>
                  <Button
                    variant="danger"
                    size="sm"
                    className="mt-3"
                    disabled={reason.trim().length < 3}
                    loading={refuse.isPending}
                    onClick={() =>
                      run(
                        () => refuse.mutateAsync({ reason: reason.trim(), files: refusalFiles }),
                        refusalFiles.length
                          ? `Refused, with reasons and ${refusalFiles.length} document${refusalFiles.length === 1 ? "" : "s"}`
                          : "Refused, with reasons",
                      )
                    }
                  >
                    Refuse and close
                  </Button>
                </div>
              )}
            </div>
          </div>
        )}
      </CardBody>
    </Card>
  );
}

/* ------------------------------------------------------------ transitions */

export function RequestTransitions({ request: r }: { request: RightsRequestDetail }) {
  const toast = useToast();
  const move = useTransitionRequest(r.request_uuid);
  // Sending tickets moves a request to awaiting holders by itself; from
  // collating the same move is the way back (2026-10-08), so it is offered.
  const generic = r.transitions.filter(
    (t) => t.via === "transition" && (!AUTOMATIC.includes(t.to) || r.status === "collating"),
  );

  if (r.status === "closed") {
    return (
      <Card>
        <CardBody className="flex items-start gap-3 text-sm text-text-muted">
          <Lock className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <p>Closed. Disagreement with the outcome is a grievance - a new request linked to this one.</p>
        </CardBody>
      </Card>
    );
  }
  if (generic.length === 0) return null;
  // Started with nobody asked yet: finding the holders comes first, and
  // collating straight away is the exception for nothing to ask anyone.
  const notFound = holdersNotYetFound(r);

  async function run(to: string, reason?: string) {
    try {
      await move.mutateAsync(reason ? { to, reason } : { to });
      toast.success(`Moved to ${STATUS_COPY[to as keyof typeof STATUS_COPY]?.label ?? to}`);
    } catch (err) {
      toast.error("Could not move this request", messageOf(err, "The server refused."));
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>What happens next</CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          Currently {STATUS_COPY[r.status].label.toLowerCase()}. Rendered from the server&apos;s answer.
        </p>
      </CardHeader>
      <CardBody className="space-y-3">
        {notFound && (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-accent-border bg-accent-subtle px-4 py-3">
            <div className="min-w-0">
              <p className="text-sm font-medium">Find who holds the data</p>
              <p className="mt-1 text-xs text-text-muted">
                From the records, or add one you know of; then confirm who answers and send the
                tickets.
              </p>
            </div>
            <Button asChild variant="primary" size="sm">
              <a href="#holders">
                Go to Holders
                <ArrowRight className="size-4" />
              </a>
            </Button>
          </div>
        )}
        {generic.map((option) =>
          option.reason_required ? (
            <GoBack key={option.to} to={option.to} pending={move.isPending} onGo={(reason) => run(option.to, reason)} />
          ) : (
          <div key={option.to} className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-border px-4 py-3">
            <div className="min-w-0">
              <p className="text-sm font-medium">
                {notFound && option.to === "collating" && "Nothing to ask anyone? "}
                Move to {STATUS_COPY[option.to].label.toLowerCase()}
              </p>
              {notFound && option.to === "collating" && (
                <p className="mt-1 text-xs text-text-muted">
                  Only when nobody outside the CMP holds this person&apos;s data: its own records
                  answer the request.
                </p>
              )}
              {option.blocked_by && (
                <p className="mt-1 flex items-center gap-1.5 text-xs text-warning-text">
                  <AlertTriangle className="size-3.5 shrink-0" aria-hidden="true" />
                  {option.blocked_by}
                </p>
              )}
            </div>
            <Button
              variant={option.allowed && !notFound ? "primary" : "secondary"}
              size="sm"
              disabled={!option.allowed}
              loading={move.isPending}
              title={option.blocked_by}
              onClick={() => run(option.to)}
            >
              {STATUS_COPY[option.to].label}
              <ArrowRight className="size-4" />
            </Button>
          </div>
          ),
        )}
      </CardBody>
    </Card>
  );
}

/** Why a request goes back from collating (2026-10-08): codes the trail keeps. */
const BACK_REASONS: { value: string; label: string }[] = [
  { value: "new_holder", label: "A holder still to ask" },
  { value: "more_from_holder", label: "More needed from a holder" },
  { value: "other", label: "Something else" },
];

function GoBack({ to, pending, onGo }: { to: RightsRequestDetail["status"]; pending: boolean; onGo: (reason: string) => void }) {
  const [reason, setReason] = React.useState("");
  const where = STATUS_COPY[to].label.toLowerCase();
  return (
    <div className="space-y-2 rounded-md border border-border px-4 py-3">
      <p className="text-sm font-medium">Back to {where}</p>
      <p className="text-xs text-text-muted">
        Moved to collating too soon? Go back to add a holder or ask a holder for more, then send
        the ticket from Holders and tickets. The clock does not pause.
      </p>
      <div className="flex flex-wrap items-end gap-2">
        <Field label="Why">
          {(p) => (
            <Select {...p} value={reason} onChange={(e) => setReason(e.target.value)}>
              <option value="">Choose…</option>
              {BACK_REASONS.map((b) => (
                <option key={b.value} value={b.value}>
                  {b.label}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Button variant="secondary" size="sm" disabled={!reason} loading={pending} onClick={() => onGo(reason)}>
          <ArrowLeft className="size-4" aria-hidden="true" />
          Back to {where}
        </Button>
      </div>
    </div>
  );
}
