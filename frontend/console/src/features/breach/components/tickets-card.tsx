/**
 * Breach tickets, the office's side (S3-08).
 *
 * The DPO asks the people who must act - whoever runs the system that leaked,
 * whoever holds the log - and they answer on a thread and return the ticket.
 * Only the DPO closes one. Tickets wait for the breach to be recorded, go to
 * internal people only, and one person holds one ticket per breach; the server
 * refuses otherwise and says why. Somebody without a console login is named by
 * their email and given a breach-only login for this breach (S3-09); the
 * table shows whose login it is and whether it is waiting, in use, or kept
 * read only once their part is over. Every control here comes from the moves the
 * server returns with each ticket: nothing in the console decides what may
 * happen next.
 *
 * A document can go with the ticket as it is raised: it is the ticket's first
 * message. The date to resolve it by is either side's to move, with a reason
 * and no approval (0061); the thread keeps what it was and why it changed, so
 * the trail is there for both of them to read.
 *
 * Laid out as a rights ticket is (2026-11-12), so the two read alike: the
 * holder's answer first, then what may be done about it - Close the ticket
 * with Send back beside it - then what they were asked, then the messages.
 * The table opens a ticket with a button that reads as one ("Review the
 * answer" once there is one), and the person a ticket goes to is found by
 * typing: the matches are listed as the name is typed.
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, ChevronRight, ClipboardList, ExternalLink, Undo2, UserPlus } from "lucide-react";
import * as React from "react";

import { AuditTrailLink } from "@/components/data-display/audit-link";
import { ChangeDate } from "@/components/data-display/change-date";
import { ReplyBox, Thread, UnreadBadge } from "@/components/data-display/thread";
import { FileInput } from "@/components/forms";
import { Dialog, DialogContent, DialogSaved } from "@/components/ui/dialog";
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
  Skeleton,
  Table,
  Td,
  Textarea,
  Th,
  Tr,
} from "@/components/ui/primitives";
import {
  assignBreachTicket,
  breachTicketFileUrl,
  changeBreachTicketDate,
  getBreachTicket,
  listBreachTickets,
  messageBreachHolder,
  moveBreachTicket,
} from "@/features/breach/api";
import {
  ATTACHMENT_ACCEPT,
  ATTACHMENT_MAX_BYTES,
  TICKET_REPLY_FILE,
} from "@/features/breach/components/attachments";
import { messageOf } from "@/features/breach/components/record-breach";
import { StaffPicker, type StaffChoice } from "@/features/users/components/staff-picker";
import { todayLocal } from "@/lib/dates";
import { cn, formatDate, formatDateTime } from "@/lib/format";
import { keys } from "@/lib/query";
import { useToast } from "@/providers";
import type {
  Breach,
  BreachTicket,
  BreachTicketEvent,
  BreachTicketMoveKind,
  BreachTicketState,
  TemporaryAccess,
  TicketMessage,
} from "@/types";
import { RETURN_OUTCOME_COPY } from "@/types";

/**
 * A ticket's state, as the office reads it and as its holder does. The words
 * are a rights ticket's (2026-11-12): what the holder sends is their answer,
 * and it waits for the office to review it.
 */
export const TICKET_STATE: Record<
  BreachTicketState,
  { label: string; holder: string; tone: "info" | "warning" | "success" | "neutral" }
> = {
  issued: { label: "Waiting on the holder", holder: "To answer", tone: "info" },
  returned: { label: "Answered - review", holder: "Answered - with the Privacy Office", tone: "warning" },
  closed: { label: "Closed", holder: "Closed", tone: "success" },
  withdrawn: { label: "Withdrawn", holder: "Withdrawn", tone: "neutral" },
};

type OfficeMove = Exclude<BreachTicketMoveKind, "return">;

const MOVE_COPY: Record<OfficeMove, { label: string; ask: string; hint: string; done: string }> = {
  send_back: {
    label: "Send back",
    ask: "What is missing or wrong",
    hint: "Sent to the holder, and kept with the ticket.",
    done: "Sent back",
  },
  close: { label: "Close the ticket", ask: "", hint: "", done: "Ticket closed" },
  withdraw: {
    label: "Withdraw",
    ask: "Reason for withdrawing",
    hint: "Sent to the holder, and kept with the ticket.",
    done: "Ticket withdrawn",
  },
  reopen: {
    label: "Reopen",
    ask: "Reason for reopening",
    hint: "Sent to the holder, and kept with the ticket.",
    done: "Ticket reopened",
  },
};

const ACCESS: Record<TemporaryAccess, { label: string; tone: "info" | "success" | "neutral"; hint: string }> = {
  pending: {
    label: "Temporary login · not yet signed in",
    tone: "info",
    hint: "Emailed a code to set a password; they have not done so yet.",
  },
  active: { label: "Temporary login", tone: "success", hint: "Signs in for this breach only." },
  ended: {
    label: "Temporary login · read only",
    tone: "neutral",
    hint: "Their ticket is closed to them; they can still sign in and read it. Reopening it lets them answer again.",
  },
};

/** A holder's breach-only login, if they have one (S3-09). */
export function AccessBadge({ access }: { access: TemporaryAccess | null }) {
  if (!access) return null;
  const copy = ACCESS[access];
  return (
    <Badge tone={copy.tone} dot={false} title={copy.hint}>
      {copy.label}
    </Badge>
  );
}

export function TicketStateBadge({
  state,
  side = "office",
}: {
  state: BreachTicketState;
  /** Whose words: the office's, or the holder's own. */
  side?: "office" | "holder";
}) {
  const copy = TICKET_STATE[state];
  return (
    <Badge tone={copy.tone} dot={false}>
      {side === "holder" ? copy.holder : copy.label}
    </Badge>
  );
}

/** The first line on a thread that opens with a document. */
const RAISED_WITH_FILE = "Document attached when this ticket was raised.";

/** A date with no time (`YYYY-MM-DD`) as that day in the reader's own calendar.
 *  `new Date` reads it as midnight at Greenwich, the evening before for anyone
 *  west of it. */
export function localDay(value: string): Date {
  const [y, m, d] = value.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d);
}

/**
 * The holder's answer as it stands: the last one they gave, unless it was
 * sent back or the ticket reopened since - then there is none to review.
 */
export function standingAnswer(events: BreachTicketEvent[]): BreachTicketEvent | null {
  let answer: BreachTicketEvent | null = null;
  for (const event of events) {
    if (event.kind === "returned") answer = event;
    else if (event.kind === "sent_back" || event.kind === "reopened") answer = null;
  }
  return answer;
}

function AssignDialog({ breach, onClose }: { breach: Breach; onClose: () => void }) {
  const toast = useToast();
  const qc = useQueryClient();
  const [byEmail, setByEmail] = React.useState(false);
  const [picked, setPicked] = React.useState<StaffChoice | null>(null);
  const [person, setPerson] = React.useState({ full_name: "", email: "", mobile: "" });
  const [instruction, setInstruction] = React.useState("");
  const [answerBy, setAnswerBy] = React.useState("");
  const [file, setFile] = React.useState<File | null>(null);
  const named = byEmail ? person.email.trim() !== "" : picked !== null;
  const assign = useMutation({
    // The ticket stands whatever becomes of the file, and a second assignment
    // would be refused, so a refused file comes back as words, not an error.
    mutationFn: async () => {
      const made = await assignBreachTicket(breach.breach_uuid, {
        ...(byEmail
          ? { full_name: person.full_name.trim(), email: person.email.trim(), mobile: person.mobile.trim() || null }
          : { user_uuid: picked!.uuid }),
        instruction: instruction.trim(),
        answer_by: answerBy || null,
      });
      if (!file) return null;
      try {
        await messageBreachHolder(breach.breach_uuid, made.ticket.ticket_uuid, {
          body: RAISED_WITH_FILE,
          evidence: file,
        });
        return null;
      } catch (err) {
        return messageOf(err, "The server refused it");
      }
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: keys.breach.tickets(breach.breach_uuid) });
      void qc.invalidateQueries({ queryKey: keys.breach.detail(breach.breach_uuid) });
    },
  });
  async function save() {
    try {
      const refused = await assign.mutateAsync();
      if (refused) {
        toast.warning("Ticket assigned, but the attachment was not added", `${refused}. Add it on the ticket.`);
      } else {
        toast.success(
          "Ticket assigned",
          byEmail
            ? "They are emailed how to sign in, or that a ticket is waiting if they already have an account. The email does not name the breach."
            : "They are emailed that a ticket is waiting. The email does not name the breach.",
        );
      }
      onClose();
    } catch (err) {
      toast.error("Ticket not assigned", messageOf(err, "The server refused."));
    }
  }
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent
        title="Assign a ticket"
        description="To a staff member, or to a colleague on the organisation's email domains. The assignee sees the breach reference, the instruction and the messages only."
      >
        <div className="space-y-4">
          <fieldset className="space-y-1.5">
            <legend className="text-sm font-medium text-text">Assignee</legend>
            <div className="flex flex-wrap gap-x-5 gap-y-1 text-sm">
              <label className="flex items-center gap-2">
                <input type="radio" name="assign-to" checked={!byEmail} onChange={() => setByEmail(false)} />
                Staff member
              </label>
              <label className="flex items-center gap-2">
                <input type="radio" name="assign-to" checked={byEmail} onChange={() => setByEmail(true)} />
                Person without a console account
              </label>
            </div>
          </fieldset>
          {byEmail ? (
            <>
              <p className="text-xs text-text-muted">
                The person receives a login limited to this breach: they set a password from the email, sign in with a
                one-time code, and see only their ticket. Access ends when the ticket is withdrawn or the breach is
                closed. If the address already has a console account, the ticket goes to that account.
              </p>
              <Field label="Name" hint="Required when the address has no account.">
                {(p) => (
                  <Input
                    {...p}
                    autoComplete="off"
                    value={person.full_name}
                    onChange={(e) => setPerson({ ...person, full_name: e.target.value })}
                  />
                )}
              </Field>
              <Field label="Work email" required hint="Must be on one of the organisation's domains.">
                {(p) => (
                  <Input
                    {...p}
                    type="email"
                    autoComplete="off"
                    value={person.email}
                    onChange={(e) => setPerson({ ...person, email: e.target.value })}
                  />
                )}
              </Field>
              <Field label="Mobile" hint="Optional.">
                {(p) => (
                  <Input
                    {...p}
                    type="tel"
                    autoComplete="off"
                    value={person.mobile}
                    onChange={(e) => setPerson({ ...person, mobile: e.target.value })}
                  />
                )}
              </Field>
            </>
          ) : (
            <StaffPicker label="Assign to" value={picked} onChange={setPicked} />
          )}
          <Field label="Instruction" required hint="What the assignee is asked to do. They read this on the ticket.">
            {(p) => <Textarea {...p} rows={4} value={instruction} onChange={(e) => setInstruction(e.target.value)} />}
          </Field>
          <Field label="Resolve by" hint="Optional. Visible to both parties; shown as overdue on your dashboard once passed.">
            {(p) => <Input {...p} type="date" value={answerBy} min={todayLocal()} onChange={(e) => setAnswerBy(e.target.value)} />}
          </Field>
          <FileInput
            label="Attachment"
            hint="Optional. PDF, Word, image, saved email, CSV or text, up to 25 MB. Visible to the assignee on the ticket."
            accept={ATTACHMENT_ACCEPT}
            maxBytes={ATTACHMENT_MAX_BYTES}
            file={file}
            onChange={setFile}
          />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button
              variant="primary"
              disabled={!named || !instruction.trim()}
              loading={assign.isPending}
              onClick={save}
            >
              <UserPlus className="size-4" />
              Assign ticket
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function outcomeTone(outcome: BreachTicketEvent["outcome"]): "success" | "warning" | "danger" | "neutral" {
  return outcome === "done" ? "success" : outcome === "failed" ? "danger" : outcome ? "warning" : "neutral";
}

/** The file that came with an answer: on the last "return" message of the thread. */
function answerFile(messages: TicketMessage[]): TicketMessage | null {
  const returns = messages.filter((m) => m.kind === "return");
  const last = returns[returns.length - 1];
  return last?.evidence_hash ? last : null;
}

function TicketDialog({
  breach,
  ticket,
  onClose,
}: {
  breach: Breach;
  ticket: BreachTicket;
  onClose: () => void;
}) {
  const toast = useToast();
  const qc = useQueryClient();
  const detail = useQuery({
    queryKey: keys.breach.ticket(breach.breach_uuid, ticket.ticket_uuid),
    queryFn: () => getBreachTicket(breach.breach_uuid, ticket.ticket_uuid),
  });
  const [asking, setAsking] = React.useState<OfficeMove | null>(null);
  const [reason, setReason] = React.useState("");
  // Each move made, or given up with Cancel: its reason is dealt with, so
  // closing need not ask about it. Named, so a message half-typed below the
  // reason is still asked about.
  const [moved, setMoved] = React.useState(0);
  const reasonPart = React.useId();
  const refresh = () => {
    void qc.invalidateQueries({ queryKey: keys.breach.tickets(breach.breach_uuid) });
    void qc.invalidateQueries({ queryKey: keys.breach.detail(breach.breach_uuid) });
  };
  const write = useMutation({
    mutationFn: (input: { body: string; evidence: File | null }) =>
      messageBreachHolder(breach.breach_uuid, ticket.ticket_uuid, input),
    onSuccess: (fresh) => {
      qc.setQueryData(keys.breach.ticket(breach.breach_uuid, ticket.ticket_uuid), fresh);
      refresh();
    },
  });
  const move = useMutation({
    mutationFn: (m: OfficeMove) =>
      moveBreachTicket(breach.breach_uuid, ticket.ticket_uuid, m, reason.trim() || undefined),
    onSuccess: (fresh) => {
      qc.setQueryData(keys.breach.ticket(breach.breach_uuid, ticket.ticket_uuid), fresh);
      refresh();
    },
  });
  const redate = useMutation({
    mutationFn: (body: { answer_by: string; reason: string }) =>
      changeBreachTicketDate(breach.breach_uuid, ticket.ticket_uuid, body),
    onSuccess: (fresh) => {
      qc.setQueryData(keys.breach.ticket(breach.breach_uuid, ticket.ticket_uuid), fresh);
      refresh();
    },
  });
  async function act(m: OfficeMove) {
    try {
      await move.mutateAsync(m);
      toast.success(MOVE_COPY[m].done);
      setAsking(null);
      setReason("");
      setMoved((n) => n + 1);
    } catch (err) {
      toast.error("Not done", messageOf(err, "The server refused."));
    }
  }
  const t = detail.data?.ticket ?? ticket;
  const messages = detail.data?.messages ?? [];
  const moves = t.moves.filter((m) => m.move !== "return").map((m) => ({ ...m, move: m.move as OfficeMove }));
  // As on a rights ticket: the main move first - closing an answered ticket -
  // with Send back beside it, and a menu only where there is more than one
  // thing to put in it. Here there never is, so each is a button.
  const main = moves.find((m) => m.move === "close");
  const others = moves.filter((m) => m !== main);
  const answer = standingAnswer(t.events);
  const file = answer ? answerFile(messages) : null;
  const who = t.holder_name ?? "The holder";
  const start = (m: OfficeMove, needsReason: boolean) => (needsReason ? setAsking(m) : void act(m));

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent
        title={`Ticket for ${t.holder_name ?? "a member of staff"}`}
        description={`On ${breach.reference}. ${TICKET_STATE[t.state].label}.`}
        size="lg"
      >
        <DialogSaved count={moved} part={reasonPart} />
        {detail.isLoading ? (
          <Skeleton className="h-40" />
        ) : detail.error && !detail.data ? (
          <Alert tone="danger">{detail.error.message}</Alert>
        ) : (
          <div className="space-y-5">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-sm">
              <TicketStateBadge state={t.state} />
              <AccessBadge access={t.temporary_access} />
              <span className={cn(t.overdue ? "font-medium text-danger-text" : "text-text-muted")}>
                {t.answer_by ? `Resolve by ${formatDate(localDay(t.answer_by))}` : "No resolve-by date"}
              </span>
              {t.added_by_name && <span className="text-xs text-text-muted">Added by {t.added_by_name}</span>}
              {t.may_change_date && (
                <ChangeDate
                  label="Resolve by"
                  current={t.answer_by}
                  told={`${who} is told.`}
                  pending={redate.isPending}
                  onSave={({ date, reason: why }) => redate.mutateAsync({ answer_by: date, reason: why })}
                />
              )}
              {/* Everything done on this ticket, for whoever may read the trail. */}
              <span className="ml-auto">
                <AuditTrailLink
                  entityType="breach_ticket"
                  uuid={t.ticket_uuid}
                  label={`Ticket on ${breach.reference}`}
                />
              </span>
            </div>

            {answer && (
              <section
                className={
                  t.state === "returned"
                    ? "rounded-md border border-accent-border bg-accent-subtle p-3"
                    : "rounded-md border border-border p-3"
                }
              >
                <h3 className="text-xs font-semibold tracking-wide text-text-subtle uppercase">Their answer</h3>
                <p className="mt-1 flex flex-wrap items-center gap-2 text-sm">
                  {answer.outcome && (
                    <Badge tone={outcomeTone(answer.outcome)} dot>
                      {RETURN_OUTCOME_COPY[answer.outcome]}
                    </Badge>
                  )}
                  <span className="text-xs text-text-muted">{formatDateTime(answer.occurred_at)}</span>
                </p>
                <p className="mt-2 text-sm whitespace-pre-wrap">{answer.summary}</p>
                {file && (
                  <a
                    className="mt-2 inline-flex items-center gap-1 text-sm text-accent-text underline underline-offset-2"
                    href={breachTicketFileUrl(breach.breach_uuid, t.ticket_uuid, file.message_uuid)}
                  >
                    {file.evidence_name ?? "Their proof"} <ExternalLink className="size-3" aria-hidden="true" />
                  </a>
                )}
                {t.state === "returned" && (
                  <p className="mt-2 text-xs text-text-muted">
                    Read it, and their messages below; then close the ticket, or send it back with what is missing.
                  </p>
                )}
              </section>
            )}

            {moves.length > 0 &&
              (asking ? (
                <section
                  className="space-y-3 rounded-md border border-accent-border bg-accent-subtle/40 p-3"
                  data-dialog-part={reasonPart}
                >
                  <h3 className="text-sm font-semibold">{MOVE_COPY[asking].label}</h3>
                  <Field label={MOVE_COPY[asking].ask} hint={MOVE_COPY[asking].hint} required>
                    {(p) => <Textarea {...p} rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />}
                  </Field>
                  <div className="flex justify-end gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setAsking(null);
                        setReason("");
                        setMoved((n) => n + 1);
                      }}
                    >
                      Cancel
                    </Button>
                    <Button
                      variant="primary"
                      size="sm"
                      disabled={!reason.trim()}
                      loading={move.isPending}
                      onClick={() => act(asking)}
                    >
                      {MOVE_COPY[asking].label}
                    </Button>
                  </div>
                </section>
              ) : (
                <div className="flex flex-wrap items-center gap-2">
                  {main && (
                    <Button
                      variant="primary"
                      size="sm"
                      loading={move.isPending && move.variables === main.move}
                      onClick={() => start(main.move, main.reason_required)}
                    >
                      <Check className="size-4" aria-hidden="true" />
                      {MOVE_COPY[main.move].label}
                    </Button>
                  )}
                  {others.map((m) => (
                    <Button
                      key={m.move}
                      variant={m.move === "withdraw" && others.length > 1 ? "ghost" : "secondary"}
                      size="sm"
                      loading={move.isPending && move.variables === m.move}
                      onClick={() => start(m.move, m.reason_required)}
                    >
                      {m.move === "send_back" && <Undo2 className="size-4" aria-hidden="true" />}
                      {MOVE_COPY[m.move].label}
                    </Button>
                  ))}
                </div>
              ))}

            {detail.data?.instruction && (
              <section className="space-y-2">
                <h3 className="text-xs font-semibold tracking-wide text-text-subtle uppercase">What they were asked</h3>
                <p className="rounded-md bg-bg-inset p-3 text-sm whitespace-pre-wrap">{detail.data.instruction}</p>
              </section>
            )}

            <section className="space-y-3">
              <h3 className="text-xs font-semibold tracking-wide text-text-subtle uppercase">Messages</h3>
              <Thread
                messages={messages}
                you="office"
                evidenceHref={(m) =>
                  m.evidence_hash ? breachTicketFileUrl(breach.breach_uuid, t.ticket_uuid, m.message_uuid) : null
                }
              />
              <ReplyBox
                {...TICKET_REPLY_FILE}
                pending={write.isPending}
                placeholder="Write to them - they read it in the console, not in an email."
                disabledReason={t.may_write ? null : "This ticket is not open; reopen it to write."}
                onSend={async (body, attached) => {
                  await write.mutateAsync({ body, evidence: attached });
                }}
              />
            </section>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export function TicketsCard({ breach }: { breach: Breach }) {
  const [assigning, setAssigning] = React.useState(false);
  const [opened, setOpened] = React.useState<BreachTicket | null>(null);
  const query = useQuery({
    queryKey: keys.breach.tickets(breach.breach_uuid),
    queryFn: () => listBreachTickets(breach.breach_uuid),
    refetchInterval: 30_000,
  });
  const recorded = breach.breach_reference !== null;
  const open = breach.status === "open";
  const rows = query.data ?? [];
  // Who added whom, as an indent: a colleague sits under the ticket of the
  // holder who added them (S3-09).
  const depth = (t: BreachTicket): number => {
    let n = 0;
    let at = t;
    while (at.parent_ticket_uuid && n < 6) {
      const parent = rows.find((r) => r.ticket_uuid === at.parent_ticket_uuid);
      if (!parent) break;
      at = parent;
      n += 1;
    }
    return n;
  };

  return (
    <Card id="tickets" className="scroll-mt-20">
      <CardHeader className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <CardTitle>
            <ClipboardList className="mr-2 inline size-4" aria-hidden="true" />
            Tickets
          </CardTitle>
          <p className="mt-1 text-xs text-text-muted">
            Assign work to the people who must act: staff, or a colleague on the organisation&apos;s email domains, who
            receives a login for this breach only. An assignee sees the breach reference, the instruction and the
            messages. Only this office closes a ticket, and the breach closes only when none is open.
          </p>
        </div>
        {open && recorded && (
          <Button variant="secondary" size="sm" onClick={() => setAssigning(true)}>
            <UserPlus className="size-4" />
            Assign a ticket
          </Button>
        )}
      </CardHeader>
      <CardBody className="space-y-3">
        {!recorded && (
          <Alert tone="info" title="Tickets are available once the breach is recorded">
            A ticket is addressed to a person on the breach&apos;s record, so it is assigned once validation records
            this as a personal data breach.
          </Alert>
        )}
        {query.isLoading ? (
          <Skeleton className="h-16" />
        ) : query.error ? (
          <Alert tone="danger">{query.error.message}</Alert>
        ) : rows.length === 0 ? (
          recorded && <p className="text-sm text-text-muted">No tickets yet.</p>
        ) : (
          <Table>
            <caption className="sr-only">Tickets on this breach</caption>
            <thead>
              <tr>
                <Th>Holder</Th>
                <Th>State</Th>
                <Th>Resolve by</Th>
                <Th>Last activity</Th>
                <Th>Next</Th>
              </tr>
            </thead>
            <tbody>
              {rows.map((t) => {
                // An answer is read before anything is done about it: the row
                // opens it, as a rights ticket's does.
                const toReview = t.state === "returned";
                return (
                  <Tr key={t.ticket_uuid} className={cn(t.overdue && "bg-danger-subtle/40")}>
                    <Td>
                      <span style={{ paddingLeft: `${depth(t) * 1.25}rem` }} className="block">
                        <button
                          type="button"
                          className="text-left font-medium text-accent-text hover:underline"
                          onClick={() => setOpened(t)}
                        >
                          {t.holder_name ?? "A member of staff"}
                        </button>
                        {t.temporary_access && (
                          <span className="mt-0.5 block">
                            <AccessBadge access={t.temporary_access} />
                          </span>
                        )}
                        {t.added_by_name && (
                          <span className="block text-xs text-text-subtle">added by {t.added_by_name}</span>
                        )}
                      </span>
                    </Td>
                    <Td>
                      <span className="flex flex-wrap items-center gap-1">
                        <TicketStateBadge state={t.state} />
                        <UnreadBadge count={t.unread} />
                      </span>
                    </Td>
                    <Td className={cn("text-sm", t.overdue && "font-medium text-danger-text")}>
                      {t.answer_by ? formatDate(localDay(t.answer_by)) : "-"}
                    </Td>
                    <Td className="text-sm">{t.last_activity_at ? formatDateTime(t.last_activity_at) : "-"}</Td>
                    <Td className="text-right">
                      {/* Outlined, or filled when there is an answer to read:
                          a borderless "Open" read as text, not a button. */}
                      <Button variant={toReview ? "primary" : "secondary"} size="sm" onClick={() => setOpened(t)}>
                        {toReview ? "Review the answer" : "Open"}
                        <ChevronRight className="size-4" />
                      </Button>
                    </Td>
                  </Tr>
                );
              })}
            </tbody>
          </Table>
        )}
      </CardBody>
      {assigning && <AssignDialog breach={breach} onClose={() => setAssigning(false)} />}
      {opened && <TicketDialog breach={breach} ticket={opened} onClose={() => setOpened(null)} />}
    </Card>
  );
}
