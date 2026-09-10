/**
 * Steps 6 to 8: holders derived, DPO confirms; tickets issued; returns recorded.
 *
 * The list is derived from the records - export_line says who received a file
 * with her in it, asset_consent says whose rig captured her - and then
 * confirmed by the DPO, who adds what the records miss. A derived holder is
 * not a confirmed one; the button is the difference.
 *
 * A ticket falls due early on purpose, halfway by default, so a holder that
 * misses it can be escalated once and the response still go out on time.
 * "Escalate once" is literal: the button disappears after it.
 */
"use client";

import { AlertTriangle, ExternalLink, Mail, MailPlus, Monitor, Plus, Send, Wand2 } from "lucide-react";
import * as React from "react";

import { FileInput } from "@/components/forms";
import { Dialog, DialogContent, DialogFooter } from "@/components/ui/dialog";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Field,
  Input,
  Select,
  Skeleton,
  Textarea,
} from "@/components/ui/primitives";
import { useProcessors, useRespondents } from "@/features/registry";
import { TicketBadge, dueCopy } from "@/features/rights/components/copy";
import { holderMessageAttachmentUrl } from "@/features/rights/api";
import { BriefPanel, ReplyBox, Thread, UnreadBadge } from "@/features/rights/components/thread";
import {
  useAddHolder,
  useConfirmHolder,
  useDeriveHolders,
  useEscalateTicket,
  useIssueTickets,
  useLogContact,
  usePostToHolder,
  useReassignHolder,
  useRemindHolder,
  useReturnTicket,
  useWithdrawTicket,
} from "@/features/rights/mutations";
import { useHolderThread } from "@/features/rights/queries";
import { config } from "@/lib/config";
import { formatDate, formatDateTime } from "@/lib/format";
import { useToast } from "@/providers";
import type { RightsHolder, RightsRequestDetail } from "@/types";

function messageOf(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}

export function HoldersCard({ request: r }: { request: RightsRequestDetail }) {
  const toast = useToast();
  const uuid = r.request_uuid;
  const derive = useDeriveHolders(uuid);
  const issue = useIssueTickets(uuid);
  const [adding, setAdding] = React.useState(false);
  const [issuing, setIssuing] = React.useState(false);
  const [instruction, setInstruction] = React.useState("");
  const [dueAt, setDueAt] = React.useState("");

  const open = r.status !== "closed";
  const canWork = open && r.status !== "received";
  const confirmedPending = r.holders.filter((h) => h.confirmed_at && h.ticket_status === "pending");
  const isErasure = r.request_type === "erasure";

  async function run<T>(fn: () => Promise<T>, title: string, description?: string) {
    try {
      await fn();
      toast.success(title, description);
    } catch (err) {
      toast.error("Not done", messageOf(err, "The server refused."));
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle>{isErasure ? "7–9 · Holders, instructions, confirmations" : "6–8 · Holders, tickets, returns"}</CardTitle>
          <p className="mt-1 text-xs text-text-muted">
            export_line and asset_consent are exact - the DPO adds what they miss.
          </p>
          {r.holders.length > 0 && <HoldersRollup holders={r.holders} />}
        </div>
        {canWork && (
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" size="sm" loading={derive.isPending} onClick={() => run(() => derive.mutateAsync(), "Holders derived", "Confirm each one, then issue tickets.")}>
              <Wand2 className="size-4" />
              Derive from the records
            </Button>
            <Button variant="secondary" size="sm" onClick={() => setAdding(true)}>
              <Plus className="size-4" />
              Add a holder
            </Button>
          </div>
        )}
      </CardHeader>

      <CardBody className="space-y-4">
        {r.holders.length === 0 ? (
          <p className="text-sm text-text-muted">
            No holders yet.{" "}
            {canWork
              ? "Derive them from the records, or add what you know."
              : r.status === "received"
                ? "Start the request first."
                : "Nothing was held anywhere."}
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {r.holders.map((h) => (
              <HolderRow key={h.holder_uuid} request={r} holder={h} canWork={canWork} />
            ))}
          </ul>
        )}

        {canWork && confirmedPending.length > 0 && (
          <div className="rounded-md border border-accent-border bg-accent-subtle p-3">
            <p className="text-sm font-medium text-accent-text">
              {confirmedPending.length} confirmed holder{confirmedPending.length === 1 ? "" : "s"} waiting for a ticket
            </p>
            {issuing ? (
              <div className="mt-2 space-y-3">
                <Field label="Instruction" hint="Leave empty for the standard instruction for this kind of request.">
                  {(p) => <Textarea {...p} rows={3} value={instruction} onChange={(e) => setInstruction(e.target.value)} />}
                </Field>
                <Field label="Due" hint={`Halfway (${formatDate(r.clock.halfway_at)}) unless you set a date. Early on purpose: a miss can be escalated once and the response still go out on time.`}>
                  {(p) => <Input {...p} type="date" value={dueAt} onChange={(e) => setDueAt(e.target.value)} />}
                </Field>
                <div className="flex gap-2">
                  <Button
                    variant="primary"
                    size="sm"
                    loading={issue.isPending}
                    onClick={() =>
                      run(
                        () =>
                          issue.mutateAsync({
                            instruction: instruction.trim() || null,
                            due_at: dueAt ? new Date(`${dueAt}T12:00:00`).toISOString() : null,
                          }),
                        "Tickets issued",
                        "The request is now awaiting holders.",
                      ).then(() => setIssuing(false))
                    }
                  >
                    <Send className="size-4" />
                    Issue {confirmedPending.length === 1 ? "the ticket" : "the tickets"}
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => setIssuing(false)}>
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <Button variant="primary" size="sm" className="mt-2" onClick={() => setIssuing(true)}>
                <Send className="size-4" />
                Issue tickets
              </Button>
            )}
          </div>
        )}
      </CardBody>

      <Dialog open={adding} onOpenChange={(next) => !next && setAdding(false)}>
        <DialogContent title="Add a holder" description="A party the records did not name. Added and confirmed in one step - you are the source.">
          <AddHolderForm request={r} onDone={() => setAdding(false)} />
        </DialogContent>
      </Dialog>
    </Card>
  );
}

function HolderRow({ request: r, holder: h, canWork }: { request: RightsRequestDetail; holder: RightsHolder; canWork: boolean }) {
  const toast = useToast();
  const confirm = useConfirmHolder(r.request_uuid);
  const escalate = useEscalateTicket(r.request_uuid);
  const [returning, setReturning] = React.useState(false);
  const [contacting, setContacting] = React.useState(false);
  const [talking, setTalking] = React.useState(false);
  const [reassigning, setReassigning] = React.useState(false);
  const [withdrawing, setWithdrawing] = React.useState(false);
  const remind = useRemindHolder(r.request_uuid);
  const ticketOpen = h.ticket_status === "issued" || h.ticket_status === "escalated";
  const due = dueCopy(h.due_at, ticketOpen);
  const [responderName, setResponderName] = React.useState(h.responder_name ?? "");
  const [responderContact, setResponderContact] = React.useState(h.responder_contact ?? "");
  // The processor's registered respondents, offered instead of typing. An
  // account among them means the portal; a name and address means email.
  const respondents = useRespondents(h.processor_uuid ?? undefined);
  const [respondentUuid, setRespondentUuid] = React.useState(h.respondent_uuid ?? "");

  const overdue = h.due_at && (h.ticket_status === "issued" || h.ticket_status === "escalated") && new Date(h.due_at) < new Date();
  const evidence = (h.evidence.exports?.length ?? 0) + (h.evidence.assets?.length ?? 0);

  async function run<T>(fn: () => Promise<T>, title: string) {
    try {
      await fn();
      toast.success(title);
    } catch (err) {
      toast.error("Not done", messageOf(err, "The server refused."));
    }
  }

  return (
    <li className="space-y-2 py-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="flex flex-wrap items-center gap-2 text-sm font-medium">
            {h.label}
            <TicketBadge status={h.ticket_status} />
            {h.confirmed_at ? (
              <Badge tone="success" dot={false}>confirmed</Badge>
            ) : (
              <Badge tone="warning" dot={false}>derived, not confirmed</Badge>
            )}
            {h.is_in_house && <Badge tone="neutral" dot={false}>in-house</Badge>}
            {h.channel === "portal" ? (
              <Badge tone="info" dot={false}>
                <Monitor className="mr-1 size-3" aria-hidden="true" />
                on the portal
              </Badge>
            ) : (
              <Badge tone="neutral" dot={false}>
                <Mail className="mr-1 size-3" aria-hidden="true" />
                by mail
              </Badge>
            )}
            <UnreadBadge count={h.unread_for_office} />
          </p>
          <p className="mt-0.5 text-xs text-text-muted">
            {h.derived_from === "manual"
              ? "Added by the DPO"
              : `Named by ${h.evidence.exports?.length ?? 0} export${(h.evidence.exports?.length ?? 0) === 1 ? "" : "s"} and ${h.evidence.assets?.length ?? 0} asset${(h.evidence.assets?.length ?? 0) === 1 ? "" : "s"}`}
            {evidence === 0 && h.derived_from !== "manual" && " (no evidence attached)"}
            {h.responder_name && ` · responder ${h.responder_name}`}
            {h.responder_contact && ` (${h.responder_contact})`}
            {h.channel === "portal" && " · returns it in their console"}
          </p>
          {h.contact_log.length > 0 && (
            <details className="mt-1 text-xs">
              <summary className="cursor-pointer text-text-muted">
                Contact log · {h.contact_log.length}
              </summary>
              <ul className="mt-1 space-y-0.5 border-l-2 border-border pl-2">
                {h.contact_log.map((c, i) => (
                  <li key={i} className="text-text-muted">
                    <span className="font-medium text-text">{CONTACT_LABEL[c.kind] ?? c.kind}</span>
                    {" · "}
                    {formatDateTime(c.at)}
                    {c.to && ` · to ${c.to}`}
                    {c.note && ` - ${c.note}`}
                  </li>
                ))}
              </ul>
            </details>
          )}
          {h.issued_at && (
            <p className={overdue ? "mt-0.5 flex flex-wrap items-center gap-1 text-xs font-medium text-danger-text" : "mt-0.5 text-xs text-text-subtle"}>
              {overdue && <AlertTriangle className="size-3.5" aria-hidden="true" />}
              Issued {formatDateTime(h.issued_at)}
              {due && (
                <span className={due.tone === "danger" ? "font-medium text-danger-text" : due.tone === "warning" ? "font-medium text-warning-text" : ""}>
                  {" · "}
                  {due.text}
                  {h.due_at && ` (${formatDate(h.due_at)})`}
                </span>
              )}
              {h.escalated_at && ` · escalated ${formatDateTime(h.escalated_at)}`}
              {h.reminders_sent > 0 && ` · ${h.reminders_sent} reminder${h.reminders_sent === 1 ? "" : "s"}`}
              {h.returned_at && ` · returned ${formatDateTime(h.returned_at)}`}
            </p>
          )}
          {ticketOpen && h.channel === "portal" && (
            <p className="mt-0.5 text-xs text-text-subtle">
              {h.seen_at ? `Seen by the team ${formatDateTime(h.seen_at)}` : "Not yet seen by the team"}
            </p>
          )}
          {h.return_summary && (
            <p className="mt-1 rounded-md bg-bg-inset p-2 text-xs">
              <span className="font-medium">Returned: </span>
              {h.return_summary}
              {h.return_evidence_hash && (
                <a
                  className="ml-2 inline-flex items-center gap-1 text-accent-text underline underline-offset-2"
                  href={`${config.apiUrl}/requests/${r.request_uuid}/holders/${h.holder_uuid}/evidence`}
                >
                  evidence <ExternalLink className="size-3" aria-hidden="true" />
                </a>
              )}
            </p>
          )}
        </div>

        {canWork && (
          <div className="flex flex-wrap gap-2">
            {!h.confirmed_at && (
              <Button
                variant="primary"
                size="sm"
                loading={confirm.isPending}
                onClick={() =>
                  run(
                    () =>
                      confirm.mutateAsync(
                        respondentUuid
                          ? { holderUuid: h.holder_uuid, respondent_uuid: respondentUuid }
                          : { holderUuid: h.holder_uuid, responder_name: responderName || null, responder_contact: responderContact || null },
                      ),
                    "Holder confirmed",
                  )
                }
              >
                Confirm
              </Button>
            )}
            {h.issued_at && (
              <Button variant="secondary" size="sm" onClick={() => setTalking(true)}>
                Thread{h.message_count ? ` · ${h.message_count}` : ""}
              </Button>
            )}
            {(h.ticket_status === "issued" || h.ticket_status === "escalated") && h.channel === "email" && (
              <Button variant="secondary" size="sm" onClick={() => setContacting(true)}>
                <MailPlus className="size-4" />
                Mail · log a contact
              </Button>
            )}
            {(h.ticket_status === "issued" || h.ticket_status === "escalated") && (
              <Button variant="secondary" size="sm" onClick={() => setReturning(true)}>
                {h.channel === "portal" ? "Record the return for them" : "Record the return"}
              </Button>
            )}
            {ticketOpen && h.due_at && (
              <Button variant="subtle" size="sm" loading={remind.isPending} onClick={() => run(() => remind.mutateAsync(h.holder_uuid), "Reminder sent")}>
                Remind
              </Button>
            )}
            {ticketOpen && (
              <Button variant="subtle" size="sm" onClick={() => setReassigning(true)}>
                Reassign
              </Button>
            )}
            {ticketOpen && (
              <Button variant="subtle" size="sm" onClick={() => setWithdrawing(true)}>
                Withdraw
              </Button>
            )}
            {h.ticket_status === "issued" && overdue && (
              <Button variant="subtle" size="sm" loading={escalate.isPending} onClick={() => run(() => escalate.mutateAsync(h.holder_uuid), "Escalated once")}>
                Escalate
              </Button>
            )}
          </div>
        )}
      </div>

      {canWork && !h.confirmed_at && (
        <div className="space-y-2">
          {(respondents.data?.length ?? 0) > 0 && (
            <Field
              label="Respondent"
              hint="Registered on the processor. An account answers on the portal; a name and address are mailed."
            >
              {(p) => (
                <Select {...p} value={respondentUuid} onChange={(e) => setRespondentUuid(e.target.value)}>
                  <option value="">Type one below instead…</option>
                  {respondents.data!.map((rs) => (
                    <option key={rs.respondent_uuid} value={rs.respondent_uuid}>
                      {rs.name} · {rs.contact} · {rs.user_uuid ? "portal" : "mail"}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
          )}
          {!respondentUuid && (
            <div className="grid gap-2 sm:grid-cols-2">
              <Field label="Responder name">
                {(p) => <Input {...p} value={responderName} onChange={(e) => setResponderName(e.target.value)} />}
              </Field>
              <Field label="Responder contact" hint="The instruction is emailed here when a ticket is issued, and you track the reply by hand.">
                {(p) => <Input {...p} value={responderContact} onChange={(e) => setResponderContact(e.target.value)} />}
              </Field>
            </div>
          )}
        </div>
      )}
      <Dialog open={talking} onOpenChange={(next) => !next && setTalking(false)}>
        <DialogContent
          title={`${h.label} · the ticket's thread`}
          description={
            h.channel === "portal"
              ? "The team reads this in their console and is told by mail when you write."
              : "The holder is reached by mail: what you write here is sent to the address on record and logged."
          }
        >
          {talking && <HolderThreadPanel request={r} holder={h} canWork={canWork} />}
        </DialogContent>
      </Dialog>
      <Dialog open={reassigning} onOpenChange={(next) => !next && setReassigning(false)}>
        <DialogContent
          title={`${h.label} · send this ticket to somebody else`}
          description="The instruction and the brief are delivered again to the new respondent, the thread says so, and the ticket counts as unseen until they open it."
        >
          <ReassignForm request={r} holder={h} respondents={respondents.data ?? []} onDone={() => setReassigning(false)} />
        </DialogContent>
      </Dialog>
      <Dialog open={withdrawing} onOpenChange={(next) => !next && setWithdrawing(false)}>
        <DialogContent
          title={`${h.label} · withdraw this ticket`}
          description="For a ticket issued in error, or a party that turns out to hold nothing of hers. Not a return and not a gap: the response will not name them as outstanding. They are told."
        >
          <WithdrawForm request={r} holder={h} onDone={() => setWithdrawing(false)} />
        </DialogContent>
      </Dialog>
      <Dialog open={contacting} onOpenChange={(next) => !next && setContacting(false)}>
        <DialogContent
          title={`${h.label} · by mail`}
          description="The mail lives in your inbox; this is the record on the request that it was sent, chased, or answered."
        >
          <ContactForm request={r} holder={h} onDone={() => setContacting(false)} />
        </DialogContent>
      </Dialog>

      <Dialog open={returning} onOpenChange={(next) => !next && setReturning(false)}>
        <DialogContent title={`What ${h.label} returned`} description="A confirmation of what was done and how - not an assurance. Evidence is optional and kept with the ticket.">
          <ReturnForm request={r} holder={h} onDone={() => setReturning(false)} />
        </DialogContent>
      </Dialog>
    </li>
  );
}

function HolderThreadPanel({ request: r, holder: h, canWork }: { request: RightsRequestDetail; holder: RightsHolder; canWork: boolean }) {
  const thread = useHolderThread(r.request_uuid, h.holder_uuid);
  const post = usePostToHolder(r.request_uuid);
  if (thread.isLoading) return <Skeleton className="h-40" />;
  if (thread.error) return <Alert tone="danger">{thread.error.userMessage()}</Alert>;
  const brief = thread.data?.holder.brief ?? h.brief;
  return (
    <div className="space-y-4">
      {brief && <BriefPanel brief={brief} />}
      <Thread
        messages={thread.data?.messages ?? []}
        you="office"
        evidenceHref={(m) =>
          m.evidence_hash ? holderMessageAttachmentUrl(r.request_uuid, h.holder_uuid, m.message_uuid) : null
        }
      />
      <ReplyBox
        pending={post.isPending}
        placeholder="Write to the team, or ask for more."
        disabledReason={canWork ? null : "The request is closed; the thread is kept as it stands."}
        onSend={async (body, file) => {
          await post.mutateAsync({ holderUuid: h.holder_uuid, body, evidence: file });
        }}
      />
    </div>
  );
}

function HoldersRollup({ holders }: { holders: RightsHolder[] }) {
  const issued = holders.filter((h) => h.issued_at);
  const returned = holders.filter((h) => h.ticket_status === "returned").length;
  const open = holders.filter((h) => h.ticket_status === "issued" || h.ticket_status === "escalated");
  const overdue = open.filter((h) => h.due_at && new Date(h.due_at) < new Date()).length;
  const unseen = open.filter((h) => h.channel === "portal" && !h.seen_at).length;
  const withdrawn = holders.filter((h) => h.ticket_status === "withdrawn").length;
  const unread = holders.reduce((n, h) => n + h.unread_for_office, 0);
  if (issued.length === 0) return null;
  const parts = [
    `${issued.length} ticket${issued.length === 1 ? "" : "s"} issued`,
    `${returned} returned`,
    overdue ? `${overdue} overdue` : null,
    unseen ? `${unseen} not yet seen` : null,
    unread ? `${unread} unread from teams` : null,
    withdrawn ? `${withdrawn} withdrawn` : null,
  ].filter(Boolean);
  return (
    <p className={overdue ? "mt-1 text-xs font-medium text-danger-text" : "mt-1 text-xs font-medium text-text"}>
      {parts.join(" · ")}
    </p>
  );
}

function ReassignForm({ request: r, holder: h, respondents, onDone }: { request: RightsRequestDetail; holder: RightsHolder; respondents: { respondent_uuid: string; name: string; contact: string; user_uuid: string | null }[]; onDone: () => void }) {
  const toast = useToast();
  const reassign = useReassignHolder(r.request_uuid);
  const [respondentUuid, setRespondentUuid] = React.useState("");
  const [name, setName] = React.useState("");
  const [contact, setContact] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await reassign.mutateAsync(
        respondentUuid
          ? { holderUuid: h.holder_uuid, respondent_uuid: respondentUuid }
          : { holderUuid: h.holder_uuid, responder_name: name.trim(), responder_contact: contact.trim() },
      );
      toast.success("Ticket reassigned", "The instruction has been sent to them.");
      onDone();
    } catch (err) {
      setError(messageOf(err, "Could not reassign."));
    }
  }
  return (
    <form method="post" onSubmit={submit} noValidate>
      <div className="space-y-4">
        {error && <Alert tone="danger">{error}</Alert>}
        {respondents.length > 0 && (
          <Field label="A registered respondent" hint="An account answers on the portal; a name and address are mailed.">
            {(p) => (
              <Select {...p} value={respondentUuid} onChange={(e) => setRespondentUuid(e.target.value)}>
                <option value="">Type one below instead…</option>
                {respondents.filter((rs) => rs.respondent_uuid !== h.respondent_uuid).map((rs) => (
                  <option key={rs.respondent_uuid} value={rs.respondent_uuid}>
                    {rs.name} · {rs.contact} · {rs.user_uuid ? "portal" : "mail"}
                  </option>
                ))}
              </Select>
            )}
          </Field>
        )}
        {!respondentUuid && (
          <div className="grid gap-2 sm:grid-cols-2">
            <Field label="Name" required>{(p) => <Input {...p} value={name} onChange={(e) => setName(e.target.value)} />}</Field>
            <Field label="Email address" hint="The instruction is mailed here." required>{(p) => <Input {...p} type="email" value={contact} onChange={(e) => setContact(e.target.value)} />}</Field>
          </div>
        )}
      </div>
      <DialogFooter>
        <Button type="submit" variant="primary" loading={reassign.isPending} disabled={!respondentUuid && (!name.trim() || !contact.trim())}>
          Reassign and re-send
        </Button>
      </DialogFooter>
    </form>
  );
}

function WithdrawForm({ request: r, holder: h, onDone }: { request: RightsRequestDetail; holder: RightsHolder; onDone: () => void }) {
  const toast = useToast();
  const withdraw = useWithdrawTicket(r.request_uuid);
  const [reason, setReason] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await withdraw.mutateAsync({ holderUuid: h.holder_uuid, reason: reason.trim() });
      toast.success("Ticket withdrawn", `${h.label} has been told.`);
      onDone();
    } catch (err) {
      setError(messageOf(err, "Could not withdraw."));
    }
  }
  return (
    <form method="post" onSubmit={submit} noValidate>
      <div className="space-y-4">
        {error && <Alert tone="danger">{error}</Alert>}
        <Field label="Why" hint="Recorded on the thread and in the audit trail, and sent to them." required>
          {(p) => <Textarea {...p} rows={3} maxLength={2000} value={reason} onChange={(e) => setReason(e.target.value)} />}
        </Field>
      </div>
      <DialogFooter>
        <Button type="submit" variant="primary" loading={withdraw.isPending} disabled={!reason.trim()}>
          Withdraw the ticket
        </Button>
      </DialogFooter>
    </form>
  );
}

const CONTACT_LABEL: Record<string, string> = {
  mail_sent: "Instruction mailed",
  ticket_on_portal: "Ticket on the portal",
  chased: "Chased",
  reply_noted: "Reply noted",
  note: "Note",
  escalated: "Escalated",
  returned_on_portal: "Returned on the portal",
  reminder: "Reminder sent",
  reassigned: "Reassigned",
  withdrawn: "Withdrawn",
};

function ContactForm({ request: r, holder: h, onDone }: { request: RightsRequestDetail; holder: RightsHolder; onDone: () => void }) {
  const toast = useToast();
  const log = useLogContact(r.request_uuid);
  const [kind, setKind] = React.useState<"mail_sent" | "chased" | "reply_noted" | "note">("chased");
  const [send, setSend] = React.useState(false);
  const [note, setNote] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await log.mutateAsync({ holderUuid: h.holder_uuid, kind, note: note.trim() || null, send });
      toast.success(send ? "Instruction mailed and logged" : "Contact logged");
      onDone();
    } catch (err) {
      setError(messageOf(err, "Could not log the contact."));
    }
  }

  return (
    <form method="post" onSubmit={submit} noValidate>
      <div className="space-y-4">
        {error && <Alert tone="danger">{error}</Alert>}
        <label className="flex items-start gap-2 text-sm">
          <input type="checkbox" className="mt-0.5 size-4" checked={send} onChange={(e) => setSend(e.target.checked)} />
          <span>
            Send the instruction to {h.responder_contact ?? "the address on record"} now
            <span className="block text-xs text-text-subtle">The same instruction and date as the ticket. Logged as sent.</span>
          </span>
        </label>
        {!send && (
          <Field label="What happened">
            {(p) => (
              <Select {...p} value={kind} onChange={(e) => setKind(e.target.value as typeof kind)}>
                <option value="mail_sent">I mailed them from my own inbox</option>
                <option value="chased">I chased them</option>
                <option value="reply_noted">They replied</option>
                <option value="note">A note</option>
              </Select>
            )}
          </Field>
        )}
        <Field label="Note" hint="What was said, or where the mail is.">
          {(p) => <Textarea {...p} rows={3} maxLength={2000} value={note} onChange={(e) => setNote(e.target.value)} />}
        </Field>
      </div>
      <DialogFooter>
        <Button type="submit" variant="primary" loading={log.isPending}>
          {send ? "Send and log" : "Log it"}
        </Button>
      </DialogFooter>
    </form>
  );
}

function ReturnForm({ request: r, holder: h, onDone }: { request: RightsRequestDetail; holder: RightsHolder; onDone: () => void }) {
  const toast = useToast();
  const ret = useReturnTicket(r.request_uuid);
  const [summary, setSummary] = React.useState("");
  const [file, setFile] = React.useState<File | null>(null);

  return (
    <form
      method="post"
      noValidate
      onSubmit={async (e) => {
        e.preventDefault();
        try {
          await ret.mutateAsync({ holderUuid: h.holder_uuid, summary, evidence: file });
          toast.success("Return recorded");
          onDone();
        } catch (err) {
          toast.error("Not recorded", messageOf(err, "The server refused."));
        }
      }}
    >
      <div className="space-y-4">
        <Field label="Summary of the return" required>
          {(p) => <Textarea {...p} rows={4} value={summary} onChange={(e) => setSummary(e.target.value)} />}
        </Field>
        <FileInput label="Evidence" hint="PDF, image, CSV or text, up to 25 MB." accept="application/pdf,image/png,image/jpeg,text/csv,text/plain" maxBytes={25 * 1024 * 1024} file={file} onChange={setFile} />
      </div>
      <DialogFooter>
        <Button type="button" variant="ghost" onClick={onDone}>Cancel</Button>
        <Button type="submit" variant="primary" disabled={summary.trim().length === 0} loading={ret.isPending}>
          Record
        </Button>
      </DialogFooter>
    </form>
  );
}

function AddHolderForm({ request: r, onDone }: { request: RightsRequestDetail; onDone: () => void }) {
  const toast = useToast();
  const add = useAddHolder(r.request_uuid);
  const processors = useProcessors({ limit: 100 });
  const [processor, setProcessor] = React.useState("");
  const [label, setLabel] = React.useState("");
  const [name, setName] = React.useState("");
  const [contact, setContact] = React.useState("");

  return (
    <form
      method="post"
      noValidate
      onSubmit={async (e) => {
        e.preventDefault();
        try {
          await add.mutateAsync({ label: label || null, processor_uuid: processor || null, responder_name: name || null, responder_contact: contact || null });
          toast.success("Holder added and confirmed");
          onDone();
        } catch (err) {
          toast.error("Not added", messageOf(err, "The server refused."));
        }
      }}
    >
      <div className="space-y-4">
        <Field label="A registered processor" hint="Optional. Pick one and the label follows.">
          {(p) => (
            <Select {...p} value={processor} onChange={(e) => setProcessor(e.target.value)}>
              <option value="">Not in the registry</option>
              {(processors.data?.items ?? []).map((pr) => (
                <option key={pr.processor_uuid} value={pr.processor_uuid}>{pr.legal_name}</option>
              ))}
            </Select>
          )}
        </Field>
        <Field label="Label" hint="Who holds it, in words, where the registry does not know them." required={!processor}>
          {(p) => <Input {...p} value={label} onChange={(e) => setLabel(e.target.value)} />}
        </Field>
        <div className="grid gap-2 sm:grid-cols-2">
          <Field label="Responder name">{(p) => <Input {...p} value={name} onChange={(e) => setName(e.target.value)} />}</Field>
          <Field label="Responder contact">{(p) => <Input {...p} value={contact} onChange={(e) => setContact(e.target.value)} />}</Field>
        </div>
      </div>
      <DialogFooter>
        <Button type="button" variant="ghost" onClick={onDone}>Cancel</Button>
        <Button type="submit" variant="primary" disabled={!processor && label.trim().length === 0} loading={add.isPending}>
          Add
        </Button>
      </DialogFooter>
    </form>
  );
}
