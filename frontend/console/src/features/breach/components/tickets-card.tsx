/**
 * Breach tickets, the office's side (S3-08).
 *
 * The DPO asks the people who must act - whoever runs the system that leaked,
 * whoever holds the log - and they answer on a thread and return the ticket.
 * Only the DPO closes one. Tickets wait for the breach to be recorded, go to
 * internal people only, and one person holds one ticket per breach; the server
 * refuses otherwise and says why. Somebody without a console login is named by
 * their email and given a breach-only login for this breach (S3-09); the
 * table shows whose login it is and whether it is waiting, in use or ended. Every control here comes from the moves the
 * server returns with each ticket: nothing in the console decides what may
 * happen next.
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ClipboardList, MessagesSquare, UserPlus } from "lucide-react";
import * as React from "react";

import { ReplyBox, Thread, UnreadBadge } from "@/components/data-display/thread";
import { Dialog, DialogContent } from "@/components/ui/dialog";
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
  Table,
  Td,
  Textarea,
  Th,
  Tr,
} from "@/components/ui/primitives";
import {
  assignBreachTicket,
  breachTicketFileUrl,
  getBreachTicket,
  listBreachTickets,
  messageBreachHolder,
  moveBreachTicket,
} from "@/features/breach/api";
import { messageOf } from "@/features/breach/components/record-breach";
import { useUsers } from "@/features/users";
import { cn, formatDate, formatDateTime } from "@/lib/format";
import { keys } from "@/lib/query";
import { useToast } from "@/providers";
import type { Breach, BreachTicket, BreachTicketMoveKind, BreachTicketState, TemporaryAccess } from "@/types";

export const TICKET_STATE: Record<BreachTicketState, { label: string; tone: "info" | "warning" | "success" | "neutral" }> = {
  issued: { label: "Waiting on the holder", tone: "info" },
  returned: { label: "Returned", tone: "warning" },
  closed: { label: "Closed", tone: "success" },
  withdrawn: { label: "Withdrawn", tone: "neutral" },
};

const MOVE_COPY: Record<Exclude<BreachTicketMoveKind, "return">, { label: string; ask: string; done: string }> = {
  send_back: { label: "Send back", ask: "What is missing or wrong? The holder reads this.", done: "Sent back" },
  close: { label: "Close the ticket", ask: "", done: "Ticket closed" },
  withdraw: { label: "Withdraw", ask: "Why is it withdrawn? The holder reads this.", done: "Ticket withdrawn" },
  reopen: { label: "Reopen", ask: "Why is it reopened? The holder reads this.", done: "Ticket reopened" },
};

const ACCESS: Record<TemporaryAccess, { label: string; tone: "info" | "success" | "neutral"; hint: string }> = {
  pending: {
    label: "Temporary login · not yet signed in",
    tone: "info",
    hint: "Emailed a code to set a password; they have not done so yet.",
  },
  active: { label: "Temporary login", tone: "success", hint: "Signs in for this breach only." },
  ended: { label: "Temporary login ended", tone: "neutral", hint: "Reopening the ticket gives it back, with a new email." },
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

export function TicketStateBadge({ state }: { state: BreachTicketState }) {
  const copy = TICKET_STATE[state];
  return (
    <Badge tone={copy.tone} dot={false}>
      {copy.label}
    </Badge>
  );
}

function AssignDialog({ breach, onClose }: { breach: Breach; onClose: () => void }) {
  const toast = useToast();
  const qc = useQueryClient();
  const [byEmail, setByEmail] = React.useState(false);
  const [q, setQ] = React.useState("");
  const [picked, setPicked] = React.useState<string>("");
  const [person, setPerson] = React.useState({ full_name: "", email: "", mobile: "" });
  const [instruction, setInstruction] = React.useState("");
  const [answerBy, setAnswerBy] = React.useState("");
  const search = q.trim();
  const people = useUsers(search.length >= 3 ? { q: search, status: "active" } : { status: "active" });
  // Staff only: the server refuses anyone else, and says so; offering them
  // would only invite the refusal.
  const staff = (people.data?.items ?? []).filter((u) => u.role !== "data_subject" && u.role !== "breach_holder");
  const named = byEmail ? person.email.trim() !== "" : picked !== "";
  const assign = useMutation({
    mutationFn: () =>
      assignBreachTicket(breach.breach_uuid, {
        ...(byEmail
          ? { full_name: person.full_name.trim(), email: person.email.trim(), mobile: person.mobile.trim() || null }
          : { user_uuid: picked }),
        instruction: instruction.trim(),
        answer_by: answerBy || null,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: keys.breach.tickets(breach.breach_uuid) });
      void qc.invalidateQueries({ queryKey: keys.breach.detail(breach.breach_uuid) });
    },
  });
  async function save() {
    try {
      await assign.mutateAsync();
      toast.success(
        "Ticket assigned",
        byEmail
          ? "They are emailed how to sign in, or that a ticket is waiting if they already can; the email names no breach."
          : "They are emailed that a ticket is waiting; the email names no breach.",
      );
      onClose();
    } catch (err) {
      toast.error("Not assigned", messageOf(err, "The server refused."));
    }
  }
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent
        title="Assign a ticket"
        description="To somebody on the organisation's own email domains. They see the breach reference, your instruction and the thread - nothing else from the register."
      >
        <div className="space-y-3">
          <fieldset className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
            <legend className="sr-only">Who are you asking?</legend>
            <label className="flex items-center gap-2">
              <input type="radio" name="assign-to" checked={!byEmail} onChange={() => setByEmail(false)} />
              A member of staff
            </label>
            <label className="flex items-center gap-2">
              <input type="radio" name="assign-to" checked={byEmail} onChange={() => setByEmail(true)} />
              Someone without a console login
            </label>
          </fieldset>
          {byEmail ? (
            <>
              <p className="text-xs text-text-muted">
                They are given a login for this breach only: they set a password from the email, sign in with a code
                like all staff, and see only their ticket. It ends when you withdraw their ticket or the breach closes.
                If the address already has a console login, the ticket goes to it as usual.
              </p>
              <Field label="Their name" hint="Needed when nobody has an account at this address">
                {(p) => (
                  <Input
                    {...p}
                    autoComplete="off"
                    value={person.full_name}
                    onChange={(e) => setPerson({ ...person, full_name: e.target.value })}
                  />
                )}
              </Field>
              <Field label="Their work email" required hint="On one of the organisation's own domains">
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
              <Field label="Their mobile" hint="Optional">
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
            <>
              <Field label="Find them" hint="Part of a name (three letters or more), or a whole email">
                {(p) => <Input {...p} value={q} onChange={(e) => setQ(e.target.value)} />}
              </Field>
              <Field label="Who" required>
                {(p) => (
                  <Select {...p} value={picked} onChange={(e) => setPicked(e.target.value)}>
                    <option value="">{people.isLoading ? "Looking…" : "Choose a member of staff"}</option>
                    {staff.map((u) => (
                      <option key={u.uuid} value={u.uuid}>
                        {u.full_name}
                        {u.email ? ` · ${u.email}` : ""}
                      </option>
                    ))}
                  </Select>
                )}
              </Field>
            </>
          )}
          <Field label="What you are asking them to do" required>
            {(p) => <Textarea {...p} rows={4} value={instruction} onChange={(e) => setInstruction(e.target.value)} />}
          </Field>
          <Field label="Answer by" hint="Optional. Shown to both of you, and counted on your dashboard once passed">
            {(p) => <Input {...p} type="date" value={answerBy} onChange={(e) => setAnswerBy(e.target.value)} />}
          </Field>
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
              Assign
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
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
  const [asking, setAsking] = React.useState<Exclude<BreachTicketMoveKind, "return"> | null>(null);
  const [reason, setReason] = React.useState("");
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
    mutationFn: (m: Exclude<BreachTicketMoveKind, "return">) =>
      moveBreachTicket(breach.breach_uuid, ticket.ticket_uuid, m, reason.trim() || undefined),
    onSuccess: (fresh) => {
      qc.setQueryData(keys.breach.ticket(breach.breach_uuid, ticket.ticket_uuid), fresh);
      refresh();
    },
  });
  async function act(m: Exclude<BreachTicketMoveKind, "return">) {
    try {
      await move.mutateAsync(m);
      toast.success(MOVE_COPY[m].done);
      setAsking(null);
      setReason("");
    } catch (err) {
      toast.error("Not done", messageOf(err, "The server refused."));
    }
  }
  const t = detail.data?.ticket ?? ticket;
  const moves = t.moves.filter((m) => m.move !== "return");
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent
        title={`Ticket for ${t.holder_name ?? "a member of staff"}`}
        description={`On ${breach.reference}. ${TICKET_STATE[t.state].label}.`}
        size="lg"
      >
        {detail.isLoading ? (
          <Skeleton className="h-40" />
        ) : detail.error ? (
          <Alert tone="danger">{detail.error.message}</Alert>
        ) : (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2 text-xs text-text-muted">
              <TicketStateBadge state={t.state} />
              <AccessBadge access={t.temporary_access} />
              {t.answer_by && <span className={cn(t.overdue && "font-medium text-danger-text")}>Answer by {formatDate(t.answer_by)}</span>}
              {t.added_by_name && <span>Added by {t.added_by_name}</span>}
            </div>
            <Thread
              messages={detail.data?.messages ?? []}
              you="office"
              evidenceHref={(m) =>
                m.evidence_hash ? breachTicketFileUrl(breach.breach_uuid, t.ticket_uuid, m.message_uuid) : null
              }
            />
            {moves.length > 0 && (
              <div className="space-y-2 border-t border-border pt-3">
                {asking ? (
                  <div className="space-y-2">
                    <Field label={MOVE_COPY[asking].ask} required>
                      {(p) => <Textarea {...p} rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />}
                    </Field>
                    <div className="flex justify-end gap-2">
                      <Button variant="ghost" size="sm" onClick={() => setAsking(null)}>
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
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {moves.map((m) => {
                      const kind = m.move as Exclude<BreachTicketMoveKind, "return">;
                      return (
                        <Button
                          key={m.move}
                          variant={kind === "close" ? "primary" : "secondary"}
                          size="sm"
                          loading={move.isPending && move.variables === kind}
                          onClick={() => (m.reason_required ? setAsking(kind) : act(kind))}
                        >
                          {MOVE_COPY[kind].label}
                        </Button>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
            <ReplyBox
              pending={write.isPending}
              placeholder="Write to the holder. They are not emailed the words; they read them in the console."
              disabledReason={t.may_write ? null : "This ticket is not open; reopen it to write."}
              onSend={async (body, file) => {
                await write.mutateAsync({ body, evidence: file });
              }}
            />
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
            Ask the people who must act - staff, or anyone on the organisation&apos;s own domains, who is given a login
            for this breach only. They see the breach reference, your instruction and the thread, nothing else. Only you close a ticket, and the breach closes only when none is open.
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
          <Alert tone="info" title="Tickets wait for the breach to be recorded">
            A ticket reaches a person on the breach&apos;s account, so it is assigned once validation records this as a
            personal data breach.
          </Alert>
        )}
        {query.isLoading ? (
          <Skeleton className="h-16" />
        ) : query.error ? (
          <Alert tone="danger">{query.error.message}</Alert>
        ) : rows.length === 0 ? (
          recorded && <p className="text-sm text-text-muted">No ticket yet.</p>
        ) : (
          <Table>
            <thead>
              <tr>
                <Th>Holder</Th>
                <Th>State</Th>
                <Th>Answer by</Th>
                <Th>Last activity</Th>
                <Th>
                  <span className="sr-only">Open</span>
                </Th>
              </tr>
            </thead>
            <tbody>
              {rows.map((t) => (
                <Tr key={t.ticket_uuid} className={cn(t.overdue && "bg-danger-subtle/40")}>
                  <Td>
                    <span style={{ paddingLeft: `${depth(t) * 1.25}rem` }} className="block">
                      <span className="font-medium">{t.holder_name ?? "A member of staff"}</span>
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
                    {t.answer_by ? formatDate(t.answer_by) : "-"}
                  </Td>
                  <Td className="text-sm">{t.last_activity_at ? formatDateTime(t.last_activity_at) : "-"}</Td>
                  <Td className="text-right">
                    <Button variant="ghost" size="sm" onClick={() => setOpened(t)}>
                      <MessagesSquare className="size-4" />
                      Open
                    </Button>
                  </Td>
                </Tr>
              ))}
            </tbody>
          </Table>
        )}
      </CardBody>
      {assigning && <AssignDialog breach={breach} onClose={() => setAssigning(false)} />}
      {opened && <TicketDialog breach={breach} ticket={opened} onClose={() => setOpened(null)} />}
    </Card>
  );
}
