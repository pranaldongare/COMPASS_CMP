/**
 * Breach tickets addressed to me (S3-08), on the Tickets page.
 *
 * What the Privacy Office asked of me about a personal data breach, and my
 * answer. Only what BD-13 allows is here: the breach reference, the
 * instruction, the thread, the state and the resolve-by date. Nothing else
 * from the register - not its title, not who it affected - reaches this page,
 * and the register itself is not mine to open.
 *
 * Once the ticket or the breach is closed it stays here to read (2026-10-06).
 * While it is open I can bring in a colleague (S3-09), who gets their own
 * ticket opening with my note. What comes back is my own ticket whatever
 * happened to theirs, so this page never says whether they had an account.
 * While it is open I can move its date too, saying why: no approval, and the
 * Privacy Office is told (0061).
 */
"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, MessageSquareReply, Send, ShieldAlert, UserPlus } from "lucide-react";
import * as React from "react";

import { ChangeDate } from "@/components/data-display/change-date";
import { ReplyBox, Thread, UnreadBadge } from "@/components/data-display/thread";
import { FileInput } from "@/components/forms";
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
  Skeleton,
  Textarea,
} from "@/components/ui/primitives";
import { Tab, TabList, TabPanel, Tabs } from "@/components/ui/tabs";
import {
  addBreachColleague,
  changeMyBreachTicketDate,
  messageBreachOffice,
  myBreachTicketFileUrl,
  returnBreachTicket,
} from "@/features/breach/api";
import {
  ATTACHMENT_ACCEPT,
  ATTACHMENT_MAX_BYTES,
  TICKET_REPLY_FILE,
} from "@/features/breach/components/attachments";
import { messageOf } from "@/features/breach/components/record-breach";
import { localDay, TicketStateBadge } from "@/features/breach/components/tickets-card";
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
  const overdue = t.state === "issued" && t.answer_by && localDay(t.answer_by) < new Date(new Date().toDateString());
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
            <TicketStateBadge state={t.state} side="holder" />
            <UnreadBadge count={t.unread} />
          </CardTitle>
          <p className="mt-1 text-xs text-text-muted">From the Privacy Office · {formatDateTime(t.created_at)}</p>
        </div>
        {t.answer_by && (
          <p className={overdue ? "flex items-center gap-1 text-sm font-medium text-danger-text" : "text-sm text-text-muted"}>
            {overdue && <AlertTriangle className="size-4" aria-hidden="true" />}
            Resolve by {formatDate(localDay(t.answer_by))}
          </p>
        )}
      </CardHeader>
      <CardBody className="space-y-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-text-subtle">What you are asked</p>
          <p className="mt-1 whitespace-pre-wrap text-sm">{t.instruction}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {/* The same word as on a rights ticket (2026-11-12): Answer while
              one is due, Open once it is not. */}
          <Button variant={canReturn ? "primary" : "secondary"} size="sm" onClick={() => setResponding(true)}>
            <MessageSquareReply className="size-4" aria-hidden="true" />
            {canReturn ? "Answer" : "Open"}
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
              ? "Answer the ticket, or message the Privacy Office with a question."
              : "Everything said is kept. Only the Privacy Office closes a ticket."
          }
        >
          {responding && <Respond ticket={t} onDone={() => setResponding(false)} />}
        </DialogContent>
      </Dialog>
    </Card>
  );
}

/**
 * The ticket's window, as a rights ticket's is (2026-11-12): "Answer the
 * ticket" and "Messages" are two tabs, so a message is not taken for the
 * answer. It used to be one box with a tick, "This is my return", and a
 * drop-down above it that only mattered when the box was ticked.
 */
function Respond({ ticket: t, onDone }: { ticket: MyBreachTicket; onDone: () => void }) {
  const toast = useToast();
  const qc = useQueryClient();
  const detail = useMyBreachTicket(t.ticket_uuid);
  const after = (fresh: unknown) => {
    qc.setQueryData(keys.breach.myTicket(t.ticket_uuid), fresh);
    void qc.invalidateQueries({ queryKey: keys.breach.mine() });
  };
  const send = useMutation({
    mutationFn: (input: { body: string; evidence: File | null }) => messageBreachOffice(t.ticket_uuid, input),
    onSuccess: after,
  });
  const redate = useMutation({
    mutationFn: (body: { answer_by: string; reason: string }) => changeMyBreachTicketDate(t.ticket_uuid, body),
    onSuccess: after,
  });
  const live = detail.data?.ticket ?? t;
  const canReturn = live.moves.some((m) => m.move === "return");
  const [tab, setTab] = React.useState<"answer" | "messages">(canReturn ? "answer" : "messages");
  if (detail.isLoading) return <Skeleton className="h-40" />;
  if (detail.error && !detail.data) return <Alert tone="danger">{detail.error.userMessage()}</Alert>;
  const canWrite = live.state === "issued" || live.state === "returned";
  const messages = (
    <div className="space-y-3">
      <Thread
        messages={detail.data?.messages ?? []}
        you="holder"
        evidenceHref={(m) => (m.evidence_hash ? myBreachTicketFileUrl(t.ticket_uuid, m.message_uuid) : null)}
      />
      {canReturn && (
        <Alert tone="warning">
          <p className="text-sm">
            A message does not answer the ticket. To answer it, use{" "}
            <button
              type="button"
              className="font-semibold underline underline-offset-2"
              onClick={() => setTab("answer")}
            >
              Answer the ticket
            </button>
            .
          </p>
        </Alert>
      )}
      <ReplyBox
        {...TICKET_REPLY_FILE}
        pending={send.isPending}
        placeholder="Ask a question or send an update."
        disabledReason={canWrite ? null : "This ticket is closed. Nothing further is needed from you."}
        onSend={async (body, file) => {
          await send.mutateAsync({ body, evidence: file });
          // The window stays open, as a rights ticket's does: the message is
          // on the thread above, and the answer may follow it.
          toast.success("Message sent", "The Privacy Office can see it.");
        }}
      />
    </div>
  );
  return (
    <div className="space-y-4">
      {live.may_change_date && (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-sm">
          <span className="text-text-muted">
            {live.answer_by ? `Resolve by ${formatDate(localDay(live.answer_by))}` : "No resolve-by date"}
          </span>
          <ChangeDate
            label="Resolve by"
            current={live.answer_by}
            told="The Privacy Office is told."
            pending={redate.isPending}
            onSave={({ date, reason }) => redate.mutateAsync({ answer_by: date, reason })}
          />
        </div>
      )}
      {canReturn ? (
        <Tabs
          value={tab}
          onValueChange={(next) => setTab(next as "answer" | "messages")}
          label="Answer or messages"
          layout="underline"
        >
          <TabList>
            <Tab value="answer" icon={Send}>
              Answer the ticket
            </Tab>
            <Tab value="messages" icon={MessageSquareReply} count={detail.data?.messages.length ?? 0}>
              Messages
            </Tab>
          </TabList>
          <TabPanel value="answer" className="pt-4">
            <AnswerForm ticket={t} onSaved={after} onDone={onDone} />
          </TabPanel>
          <TabPanel value="messages" className="pt-4">
            {messages}
          </TabPanel>
        </Tabs>
      ) : (
        messages
      )}
    </div>
  );
}

/** The holder's answer: what was done, what was done about it, and proof. */
function AnswerForm({
  ticket: t,
  onSaved,
  onDone,
}: {
  ticket: MyBreachTicket;
  onSaved: (fresh: unknown) => void;
  onDone: () => void;
}) {
  const toast = useToast();
  const ret = useMutation({
    mutationFn: (input: { summary: string; outcome: ReturnOutcome; evidence: File | null }) =>
      returnBreachTicket(t.ticket_uuid, input),
    onSuccess: onSaved,
  });
  // No default: "did all of it" is not assumed.
  const [outcome, setOutcome] = React.useState<ReturnOutcome | "">("");
  const [summary, setSummary] = React.useState("");
  const [file, setFile] = React.useState<File | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  return (
    <form
      method="post"
      noValidate
      className="space-y-4 rounded-md border border-accent-border bg-accent-subtle/40 p-4"
      onSubmit={async (e) => {
        e.preventDefault();
        if (!outcome || !summary.trim()) return;
        setError(null);
        try {
          await ret.mutateAsync({ summary: summary.trim(), outcome, evidence: file });
          toast.success("Answer submitted", "The Privacy Office will review it.");
          onDone();
        } catch (err) {
          setError(messageOf(err, "Could not submit your answer."));
        }
      }}
    >
      <div>
        <h3 className="text-sm font-semibold">Your answer to the Privacy Office</h3>
        <p className="mt-0.5 text-xs text-text-muted">
          This is what answers the ticket. The office reviews it, then closes the ticket or sends it back.
        </p>
      </div>
      {error && <Alert tone="danger">{error}</Alert>}
      <fieldset className="space-y-1.5">
        <legend className="text-sm font-medium">1 · What was done?</legend>
        {(Object.keys(RETURN_OUTCOME_COPY) as ReturnOutcome[]).map((o) => (
          <label key={o} className="flex items-center gap-2 text-sm">
            <input
              type="radio"
              name="outcome"
              className="size-4 accent-[var(--accent)]"
              checked={outcome === o}
              onChange={() => setOutcome(o)}
            />
            {RETURN_OUTCOME_COPY[o]}
          </label>
        ))}
        <p className="text-xs text-text-muted">
          Only “did all of it” counts as done. If you could not do some or all of it, say why below.
        </p>
      </fieldset>
      <Field label="2 · What you did, and how" required>
        {(p) => <Textarea {...p} rows={4} value={summary} onChange={(e) => setSummary(e.target.value)} />}
      </Field>
      <FileInput
        label="3 · Proof"
        hint="Optional. PDF, Word, image, saved email, CSV or text, up to 25 MB."
        accept={ATTACHMENT_ACCEPT}
        maxBytes={ATTACHMENT_MAX_BYTES}
        file={file}
        onChange={setFile}
      />
      <div className="flex justify-end">
        <Button type="submit" variant="primary" loading={ret.isPending} disabled={!outcome || !summary.trim()}>
          <Send className="size-4" aria-hidden="true" />
          Submit answer
        </Button>
      </div>
    </form>
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
        "They have their own ticket, opening with your instruction, and are emailed about it. The Privacy Office can see that you added them.",
      );
      onClose();
    } catch (err) {
      toast.error("Colleague not added", messageOf(err, "The server refused."));
    }
  }
  const set = (k: keyof typeof person) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setPerson({ ...person, [k]: e.target.value });
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent
        title="Add a colleague"
        description={`A colleague on the organisation's email domains who can help with ${t.breach_reference}. They receive their own ticket, which opens with your instruction. If they have no console account, they receive a login for this breach only.`}
      >
        <div className="space-y-3">
          <Field label="Name" hint="Required when the address has no account.">
            {(p) => <Input {...p} autoComplete="off" value={person.full_name} onChange={set("full_name")} />}
          </Field>
          <Field label="Work email" required hint="Must be on one of the organisation's domains.">
            {(p) => <Input {...p} type="email" autoComplete="off" value={person.email} onChange={set("email")} />}
          </Field>
          <Field label="Mobile" hint="Optional.">
            {(p) => <Input {...p} type="tel" autoComplete="off" value={person.mobile} onChange={set("mobile")} />}
          </Field>
          <Field label="Instruction" required hint="What your colleague is asked to do. They and the Privacy Office read this.">
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
              <UserPlus className="size-4" />
              Add colleague
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
