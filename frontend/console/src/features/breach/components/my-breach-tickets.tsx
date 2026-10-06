/**
 * Breach tickets addressed to me (S3-08), on the Tickets page.
 *
 * What the Privacy Office asked of me about a personal data breach, and my
 * answer. Only what BD-13 allows is here: the breach reference, the
 * instruction, the thread, the state and the answer-by date. Nothing else
 * from the register - not its title, not who it touched - reaches this page,
 * and the register itself is not mine to open.
 *
 * Once the ticket or the breach is closed it stays here to read (2026-10-06).
 * While it is open I can bring in a colleague (S3-09), who gets their own
 * ticket opening with my note. What comes back is my own ticket whatever
 * happened to theirs, so this page never says whether they had an account.
 */
"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, MessageSquareReply, ShieldAlert, UserPlus } from "lucide-react";
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
  Textarea,
} from "@/components/ui/primitives";
import {
  addBreachColleague,
  messageBreachOffice,
  myBreachTicketFileUrl,
  returnBreachTicket,
} from "@/features/breach/api";
import { messageOf } from "@/features/breach/components/record-breach";
import { TicketStateBadge } from "@/features/breach/components/tickets-card";
import { useMyBreachTicket } from "@/features/breach/queries";
import { formatDate, formatDateTime } from "@/lib/format";
import { keys } from "@/lib/query";
import { useToast } from "@/providers";
import type { MyBreachTicket, ReturnOutcome } from "@/types";
import { RETURN_OUTCOME_COPY } from "@/types";

export function BreachTicketCard({ ticket: t, openAtFirst }: { ticket: MyBreachTicket; openAtFirst?: boolean }) {
  const [responding, setResponding] = React.useState(Boolean(openAtFirst));
  const [adding, setAdding] = React.useState(false);
  const canReturn = t.moves.some((m) => m.move === "return");
  const overdue = t.state === "issued" && t.answer_by && new Date(t.answer_by) < new Date(new Date().toDateString());
  return (
    <Card data-testid="breach-ticket">
      <CardHeader className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <CardTitle className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-sm">{t.breach_reference}</span>
            <Badge tone="danger" dot={false}>
              <ShieldAlert className="mr-1 size-3" aria-hidden="true" />
              Personal data breach
            </Badge>
            <TicketStateBadge state={t.state} />
            <UnreadBadge count={t.unread} />
          </CardTitle>
          <p className="mt-1 text-xs text-text-muted">From the Privacy Office · {formatDateTime(t.created_at)}</p>
        </div>
        {t.answer_by && (
          <p className={overdue ? "flex items-center gap-1 text-sm font-medium text-danger-text" : "text-sm text-text-muted"}>
            {overdue && <AlertTriangle className="size-4" aria-hidden="true" />}
            Answer by {formatDate(t.answer_by)}
          </p>
        )}
      </CardHeader>
      <CardBody className="space-y-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-text-subtle">What you are asked</p>
          <p className="mt-1 whitespace-pre-wrap text-sm">{t.instruction}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant={canReturn ? "primary" : "secondary"} size="sm" onClick={() => setResponding(true)}>
            <MessageSquareReply className="size-4" aria-hidden="true" />
            {canReturn ? "Respond" : "Open"}
          </Button>
          {t.may_add_colleague && (
            <Button variant="secondary" size="sm" onClick={() => setAdding(true)}>
              <UserPlus className="size-4" aria-hidden="true" />
              Add a colleague
            </Button>
          )}
        </div>
      </CardBody>
      {adding && <AddColleague ticket={t} onClose={() => setAdding(false)} />}
      <Dialog open={responding} onOpenChange={(next) => !next && setResponding(false)}>
        <DialogContent
          title={`${t.breach_reference} · breach ticket`}
          description={
            canReturn
              ? "Everything said so far, and your response. Tick the box to make a response your return."
              : "Everything said is kept. Only the Privacy Office closes a ticket."
          }
        >
          {responding && <Respond ticket={t} onDone={() => setResponding(false)} />}
        </DialogContent>
      </Dialog>
    </Card>
  );
}

function Respond({ ticket: t, onDone }: { ticket: MyBreachTicket; onDone: () => void }) {
  const toast = useToast();
  const qc = useQueryClient();
  const detail = useMyBreachTicket(t.ticket_uuid);
  const [outcome, setOutcome] = React.useState<ReturnOutcome | "">("");
  const after = (fresh: unknown) => {
    qc.setQueryData(keys.breach.myTicket(t.ticket_uuid), fresh);
    void qc.invalidateQueries({ queryKey: keys.breach.mine() });
  };
  const send = useMutation({
    mutationFn: (input: { body: string; evidence: File | null }) => messageBreachOffice(t.ticket_uuid, input),
    onSuccess: after,
  });
  const ret = useMutation({
    mutationFn: (input: { summary: string; outcome: ReturnOutcome; evidence: File | null }) =>
      returnBreachTicket(t.ticket_uuid, input),
    onSuccess: after,
  });
  if (detail.isLoading) return <Skeleton className="h-40" />;
  if (detail.error) return <Alert tone="danger">{detail.error.userMessage()}</Alert>;
  const live = detail.data?.ticket ?? t;
  const canReturn = live.moves.some((m) => m.move === "return");
  const canWrite = live.state === "issued" || live.state === "returned";
  return (
    <div className="space-y-4">
      <Thread
        messages={detail.data?.messages ?? []}
        you="holder"
        evidenceHref={(m) => (m.evidence_hash ? myBreachTicketFileUrl(t.ticket_uuid, m.message_uuid) : null)}
      />
      {canReturn && (
        <Field
          label="When you return the ticket: what was done?"
          hint="Only “did all of it” counts as done. If you could not do some or all of it, say so and why."
        >
          {(p) => (
            <Select {...p} value={outcome} onChange={(e) => setOutcome(e.target.value as ReturnOutcome | "")}>
              <option value="">Choose before returning…</option>
              {(Object.keys(RETURN_OUTCOME_COPY) as ReturnOutcome[]).map((o) => (
                <option key={o} value={o}>
                  {RETURN_OUTCOME_COPY[o]}
                </option>
              ))}
            </Select>
          )}
        </Field>
      )}
      <ReplyBox
        pending={send.isPending || ret.isPending}
        placeholder="Write to the Privacy Office: a question, or what you have found."
        disabledReason={canWrite ? null : "This ticket is closed. Nothing further is needed from you."}
        finalOption={
          canReturn
            ? {
                label: "This is my return",
                hint: "What was done and how. The Privacy Office closes the ticket or sends it back.",
              }
            : null
        }
        onSend={async (body, file, final) => {
          if (final) {
            if (!outcome) {
              const say = "Choose what was done before returning the ticket.";
              throw Object.assign(new Error(say), { userMessage: () => say });
            }
            await ret.mutateAsync({ summary: body, outcome, evidence: file });
            toast.success("Ticket returned", "The Privacy Office can see it.");
            onDone();
          } else {
            await send.mutateAsync({ body, evidence: file });
            // Sent: the window closes, as a response does. The thread keeps
            // it, and Respond opens it again.
            toast.success("Message sent", "The Privacy Office can see it.");
            onDone();
          }
        }}
      />
    </div>
  );
}

function AddColleague({ ticket: t, onClose }: { ticket: MyBreachTicket; onClose: () => void }) {
  const toast = useToast();
  const qc = useQueryClient();
  const [person, setPerson] = React.useState({ full_name: "", email: "", mobile: "", note: "" });
  const add = useMutation({
    mutationFn: () =>
      addBreachColleague(t.ticket_uuid, {
        full_name: person.full_name.trim(),
        email: person.email.trim(),
        mobile: person.mobile.trim() || null,
        note: person.note.trim(),
      }),
    onSuccess: (fresh) => {
      qc.setQueryData(keys.breach.myTicket(t.ticket_uuid), fresh);
      void qc.invalidateQueries({ queryKey: keys.breach.mine() });
    },
  });
  async function save() {
    try {
      await add.mutateAsync();
      toast.success(
        "Colleague added",
        "They have their own ticket on this, opening with your note, and are emailed about it. The Privacy Office can see that you added them.",
      );
      onClose();
    } catch (err) {
      toast.error("Not added", messageOf(err, "The server refused."));
    }
  }
  const set = (k: keyof typeof person) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setPerson({ ...person, [k]: e.target.value });
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent
        title="Add a colleague"
        description={`Somebody on the organisation's own email domains who can help with ${t.breach_reference}. They get their own ticket, which opens with your note rather than the Privacy Office's instruction. If they have no console login, they are given one for this breach only.`}
      >
        <div className="space-y-3">
          <Field label="Their name" hint="Needed if they have no console login">
            {(p) => <Input {...p} autoComplete="off" value={person.full_name} onChange={set("full_name")} />}
          </Field>
          <Field label="Their work email" required>
            {(p) => <Input {...p} type="email" autoComplete="off" value={person.email} onChange={set("email")} />}
          </Field>
          <Field label="Their mobile" hint="Optional">
            {(p) => <Input {...p} type="tel" autoComplete="off" value={person.mobile} onChange={set("mobile")} />}
          </Field>
          <Field label="What you are asking them to do" required hint="They read this, and so does the Privacy Office">
            {(p) => <Textarea {...p} rows={4} value={person.note} onChange={set("note")} />}
          </Field>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button
              variant="primary"
              disabled={!person.email.trim() || !person.note.trim()}
              loading={add.isPending}
              onClick={save}
            >
              Add
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
