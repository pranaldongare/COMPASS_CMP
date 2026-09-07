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

import { AlertTriangle, ArrowRight, Lock } from "lucide-react";
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
import { useUsers } from "@/features/users";
import { formatDateTime } from "@/lib/format";
import { useAuth, useToast } from "@/providers";
import type { RightsRequestDetail, RightsRequestType } from "@/types";
import { RIGHTS_REQUEST_TYPES } from "@/types";

function messageOf(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}

/* ------------------------------------------------------------ verification */

export function VerificationCard({ request: r }: { request: RightsRequestDetail }) {
  const toast = useToast();
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
              <p className="mt-0.5 text-xs text-text-muted">
                {r.subject_uuid
                  ? `Sent to the contact we hold for ${r.subject_name ?? "this person"} - never to what was typed on the form.`
                  : "No account matches this contact, so there is no stored channel. Verify manually, or close as not verified."}
              </p>
              {r.subject_uuid && (
                <div className="mt-2 flex flex-wrap items-end gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    loading={send.isPending}
                    onClick={() => run(() => send.mutateAsync(), "Code sent")}
                  >
                    Send a code
                  </Button>
                  <Field label="Code she read back">
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
                    {RIGHTS_REQUEST_TYPES.map((t) => (
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
            <p className="text-sm font-medium text-warning-text">Does she mean erasure, or withdrawal?</p>
            <p className="mt-0.5 text-xs text-text-muted">
              Withdrawal stops future processing and is hers to do from her consent record.
              Erasure removes data already collected. Confirm which before anything is deleted.
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              <Button variant="primary" size="sm" loading={intent.isPending} onClick={() => run(() => intent.mutateAsync(), "Erasure confirmed")}>
                She means erasure
              </Button>
              <Button variant="secondary" size="sm" loading={withdrawal.isPending} onClick={() => run(() => withdrawal.mutateAsync(note || null), "Handled as withdrawal")}>
                She meant withdrawal
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
                    The DPO owns grievances, including ones about her own decisions - and that is a
                    real conflict. Recuse if this concerns your handling.
                  </p>
                  <Button variant="subtle" size="sm" className="mt-2" loading={escalate.isPending} onClick={() => run(() => escalate.mutateAsync(), "Escalated to an independent reviewer")}>
                    This is about me - escalate
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
            <Button variant="ghost" size="sm" onClick={() => setRefusing((v) => !v)}>
              Not a rights request, or refused
            </Button>
            {refusing && (
              <div className="rounded-md border border-danger-border bg-danger-subtle p-3">
                <Field label="Reason, in writing" hint="Sent to the requester with the grievance route. A refusal is still a response." required>
                  {(p) => <Textarea {...p} rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />}
                </Field>
                <Button variant="primary" size="sm" className="mt-2" disabled={reason.trim().length < 3} loading={refuse.isPending} onClick={() => run(() => refuse.mutateAsync(reason.trim()), "Refused, with reasons")}>
                  Refuse and close
                </Button>
              </div>
            )}
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
  const generic = r.transitions.filter((t) => t.via === "transition");

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

  async function run(to: string) {
    try {
      await move.mutateAsync({ to });
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
        {generic.map((option) => (
          <div key={option.to} className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-border px-4 py-3">
            <div className="min-w-0">
              <p className="text-sm font-medium">Move to {STATUS_COPY[option.to].label.toLowerCase()}</p>
              {option.blocked_by && (
                <p className="mt-1 flex items-center gap-1.5 text-xs text-warning-text">
                  <AlertTriangle className="size-3.5 shrink-0" aria-hidden="true" />
                  {option.blocked_by}
                </p>
              )}
            </div>
            <Button
              variant={option.allowed ? "primary" : "secondary"}
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
        ))}
      </CardBody>
    </Card>
  );
}
