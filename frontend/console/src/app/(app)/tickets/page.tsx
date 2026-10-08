/**
 * Tickets addressed to me.
 *
 * A rights request goes out to the parties that hold the person's data as a
 * ticket each. When the holder is one of our own teams, the ticket does not
 * go by email: it is here, in front of the person that team named, and they
 * return it here with what was done and, where it helps, evidence.
 *
 * Only what is addressed to this account, and only what the instruction says.
 * The request itself - its verification, its scope, the other holders - is the
 * Privacy Office's, and stays on its own page.
 *
 * Breach tickets (S3-08) sit above them: the Privacy Office asking for help
 * with a personal data breach, which runs on a clock of its own. They carry
 * the breach reference and nothing else from the register.
 *
 * Reworked 2026-10-08 with the review step: an answer goes to the Privacy
 * Office to accept or send back, so tickets fall in three groups - to do,
 * waiting on the office, done - read off the state the server sends. Giving
 * the answer is its own form (what was done, then what, then proof), apart
 * from writing to the office, which no longer closes the window.
 */
"use client";

import { AlertTriangle, CheckCircle2, Clock, Inbox, MessageSquareReply, Send, ShieldAlert } from "lucide-react";
import { useSearchParams } from "next/navigation";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import { FileInput } from "@/components/forms";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { EmptyQueue } from "@/components/ui/graphics";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  EmptyState,
  Field,
  Skeleton,
  Textarea,
} from "@/components/ui/primitives";
import { ConsentScope } from "@/features/rights/components/consent-scope";
import { RequestTypeBadge, dueCopy } from "@/features/rights/components/copy";
import { myMessageAttachmentUrl } from "@/features/rights/api";
import { BreachTicketCard } from "@/features/breach/components/my-breach-tickets";
import { useMyBreachTickets } from "@/features/breach/queries";
import { ReplyBox, Thread, UnreadBadge } from "@/components/data-display/thread";
import { BriefPanel } from "@/features/rights/components/thread";
import { useMessageOffice, useReturnMyTicket } from "@/features/rights/mutations";
import { useMyTicket, useMyTickets } from "@/features/rights/queries";
import { formatDate, formatDateTime } from "@/lib/format";
import { useToast } from "@/providers";
import type { MyTicket, ReturnOutcome, TicketState } from "@/types";
import { RETURN_OUTCOME_COPY } from "@/types";

export default function TicketsPage() {
  return (
    // useSearchParams forces client rendering, so Next wants a boundary here.
    <React.Suspense fallback={<Skeleton className="h-40" />}>
      <TicketsInner />
    </React.Suspense>
  );
}

function TicketsInner() {
  const tickets = useMyTickets();
  const breach = useMyBreachTickets();
  // A link from the dashboard queue, the bell or a mail opens the ticket it names.
  const params = useSearchParams();
  const wanted = params.get("ticket");
  const wantedBreach = params.get("breach_ticket");
  const breachOpen = (breach.data ?? []).filter((t) => t.state === "issued" || t.state === "returned");
  const breachDone = (breach.data ?? []).filter((t) => !breachOpen.includes(t));
  const all = tickets.data ?? [];
  // To do first, the most pressing at the top: overdue, then soonest due.
  const todo = all
    .filter((t) => TO_DO.includes(t.state))
    .sort((a, b) => (a.due_at ? new Date(a.due_at).getTime() : Infinity) - (b.due_at ? new Date(b.due_at).getTime() : Infinity));
  const withOffice = all.filter((t) => t.state === "review");
  const done = all.filter((t) => !todo.includes(t) && !withOffice.includes(t));
  const overdue = todo.filter((t) => t.overdue).length;
  const soon = todo.filter((t) => {
    const d = dueCopy(t.due_at, true);
    return !t.overdue && d !== null && d.days <= 7;
  }).length;
  const unread = all.reduce((n, t) => n + t.unread_for_holder, 0);

  return (
    <>
      <PageHeader
        eyebrow="Your work"
        title="My tasks"
        description="What the Privacy Office has asked of you: tickets on rights requests and on personal data breaches. Answer each by its date; the office reviews your answer."
      />

      {breach.data && breach.data.length > 0 && (
        <section className="mb-8 space-y-3" aria-label="Breach tickets">
          <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-text-subtle">
            <ShieldAlert className="size-4" aria-hidden="true" />
            Breach tickets · {breachOpen.length} open
          </h2>
          {[...breachOpen, ...breachDone].map((t) => (
            <BreachTicketCard key={t.ticket_uuid} ticket={t} openAtFirst={t.ticket_uuid === wantedBreach} />
          ))}
        </section>
      )}

      {tickets.isLoading && <Skeleton className="h-40" />}
      {tickets.error && (
        <Alert tone="danger" title="Could not load your tickets">
          {tickets.error.userMessage()}
        </Alert>
      )}

      {all.length > 0 && (
        <div className="mb-6 grid gap-3 sm:grid-cols-4" data-testid="ticket-summary">
          <Stat label="To do" value={todo.length} tone="neutral" />
          <Stat label="Overdue" value={overdue} tone={overdue ? "danger" : "neutral"} />
          <Stat label="Due within 7 days" value={soon} tone={soon ? "warning" : "neutral"} />
          <Stat label="Unread from the Privacy Office" value={unread} tone={unread ? "warning" : "neutral"} />
        </div>
      )}

      {tickets.data && all.length === 0 && (breach.data?.length ?? 0) === 0 && (
        <Card>
          <EmptyState
            illustration={<EmptyQueue />}
            title="Nothing addressed to you"
            description="When the Privacy Office sends your team a ticket, it appears here with what is asked and the date to answer by."
          />
        </Card>
      )}

      <Group icon={<Inbox className="size-4" aria-hidden="true" />} title="To do" tickets={todo} wanted={wanted} />
      <Group
        icon={<Clock className="size-4" aria-hidden="true" />}
        title="Waiting on the Privacy Office"
        tickets={withOffice}
        wanted={wanted}
      />
      <Group icon={<CheckCircle2 className="size-4" aria-hidden="true" />} title="Done" tickets={done} wanted={wanted} />
    </>
  );
}

/** States in which the ticket waits on the holder. */
const TO_DO: TicketState[] = ["waiting", "sent_back", "overdue", "final_reminder"];

const STATE_TONE: Partial<Record<TicketState, "info" | "warning" | "danger" | "success" | "neutral" | "accent">> = {
  waiting: "info",
  sent_back: "warning",
  overdue: "danger",
  final_reminder: "danger",
  review: "accent",
  accepted: "success",
  no_answer: "danger",
};

function Group({ icon, title, tickets, wanted }: { icon: React.ReactNode; title: string; tickets: MyTicket[]; wanted: string | null }) {
  if (tickets.length === 0) return null;
  return (
    <section className="mb-8 space-y-3">
      <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-text-subtle">
        {icon}
        {title} · {tickets.length}
      </h2>
      {tickets.map((t) => (
        <TicketCard key={t.holder_uuid} ticket={t} openAtFirst={t.holder_uuid === wanted} />
      ))}
    </section>
  );
}

function Stat({ label, value, tone }: { label: string; value: number; tone: "neutral" | "warning" | "danger" }) {
  const colour = tone === "danger" ? "text-danger-text" : tone === "warning" ? "text-warning-text" : "text-text";
  return (
    <div className="rounded-lg border border-border bg-surface px-4 py-3">
      <p className={`text-2xl font-semibold tabular-nums ${colour}`}>{value}</p>
      <p className="text-xs text-text-muted">{label}</p>
    </div>
  );
}

function outcomeTone(o: ReturnOutcome | null): "success" | "warning" | "danger" | "neutral" {
  return o === "done" ? "success" : o === "failed" ? "danger" : o ? "warning" : "neutral";
}

function TicketCard({ ticket: t, openAtFirst }: { ticket: MyTicket; openAtFirst?: boolean }) {
  const [responding, setResponding] = React.useState(Boolean(openAtFirst));
  const toDo = TO_DO.includes(t.state);
  const due = dueCopy(t.due_at, toDo);

  return (
    <Card data-testid="ticket">
      <CardHeader className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <CardTitle className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-sm">{t.reference}</span>
            <RequestTypeBadge type={t.request_type} />
            <Badge tone={STATE_TONE[t.state] ?? "neutral"} dot={false}>
              {t.state_label}
            </Badge>
            <UnreadBadge count={t.unread_for_holder} />
          </CardTitle>
          <p className="mt-1 text-xs text-text-muted">
            For {t.label}
            {t.subject_name && ` · about ${t.subject_name}`}
            {t.issued_at && ` · sent ${formatDateTime(t.issued_at)}`}
          </p>
        </div>
        {due && (
          <p className={due.tone === "danger" ? "flex items-center gap-1 text-sm font-medium text-danger-text" : due.tone === "warning" ? "text-sm font-medium text-warning-text" : "text-sm text-text-muted"}>
            {t.overdue && <AlertTriangle className="size-4" aria-hidden="true" />}
            <span className="capitalize">{due.text}</span>
            {t.due_at && <span className="font-normal text-text-muted"> · {formatDate(t.due_at)}</span>}
          </p>
        )}
      </CardHeader>
      <CardBody className="space-y-3">
        <StateNote ticket={t} />
        {t.consent_uuid && (
          <div className="text-sm">
            <ConsentScope
              link={false}
              scope={{
                consent_uuid: t.consent_uuid,
                project: t.consent_project,
                notice_code: t.consent_notice_code,
                notice_version: t.consent_notice_version,
                at: t.consent_at,
                purposes: t.consent_purposes,
              }}
            />
            <p className="mt-1 text-xs text-text-muted">Act only on data held under this consent.</p>
          </div>
        )}
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-text-subtle">What you are asked</p>
          <p className="mt-1 whitespace-pre-wrap text-sm">{t.instruction ?? "See the Privacy Office."}</p>
        </div>
        {t.return_summary && (
          <div className="rounded-md bg-bg-inset p-3 text-sm">
            <p className="flex flex-wrap items-center gap-2">
              <span className="font-medium">Your answer{t.returned_at && ` · ${formatDateTime(t.returned_at)}`}</span>
              {t.return_outcome && (
                <Badge tone={outcomeTone(t.return_outcome)} dot={false}>
                  {RETURN_OUTCOME_COPY[t.return_outcome]}
                </Badge>
              )}
            </p>
            <p className="mt-1 whitespace-pre-wrap">{t.return_summary}</p>
          </div>
        )}
        <div className="flex flex-wrap items-center gap-2">
          <Button variant={toDo ? "primary" : "secondary"} size="sm" onClick={() => setResponding(true)}>
            <MessageSquareReply className="size-4" aria-hidden="true" />
            {toDo ? "Answer" : "Open"}
            {t.message_count ? ` · ${t.message_count}` : ""}
          </Button>
          {toDo && (
            <span className="text-xs text-text-muted">Ask a question, or give your answer - both from one place.</span>
          )}
        </div>
      </CardBody>
      <Dialog open={responding} onOpenChange={(next) => !next && setResponding(false)}>
        <DialogContent
          title={`${t.reference} · ${t.label}`}
          description={
            toDo
              ? "What the platform already knows, everything said so far, and your answer."
              : `${t.state_label}. Everything said is kept; you can still write to the Privacy Office.`
          }
        >
          {responding && <Respond ticket={t} onDone={() => setResponding(false)} />}
        </DialogContent>
      </Dialog>
    </Card>
  );
}

/** What the ticket's state means for the holder, where it needs saying. */
function StateNote({ ticket: t }: { ticket: MyTicket }) {
  switch (t.state) {
    case "withdrawn":
      return (
        <Alert tone="info">
          <p className="text-sm">Withdrawn by the Privacy Office. Nothing further is needed from you; the reason is in the messages.</p>
        </Alert>
      );
    case "no_answer":
      return (
        <Alert tone="warning">
          <p className="text-sm">The request was answered without your reply. Nothing further can be sent on this ticket.</p>
        </Alert>
      );
    case "review":
      return (
        <Alert tone="info">
          <p className="text-sm">Your answer is with the Privacy Office. They accept it, or send it back with what is missing.</p>
        </Alert>
      );
    case "accepted":
      return (
        <Alert tone="success">
          <p className="text-sm">
            The Privacy Office accepted your answer{t.accepted_at ? ` on ${formatDate(t.accepted_at)}` : ""}. Nothing further is needed.
          </p>
        </Alert>
      );
    default:
      return t.sent_back_at ? (
        <Alert tone="warning" title={`Sent back to you ${formatDateTime(t.sent_back_at)}`}>
          <p className="text-sm">{t.sent_back_reason}</p>
          {t.due_at && <p className="mt-1 text-xs">Answer again by {formatDate(t.due_at)}.</p>}
        </Alert>
      ) : null;
  }
}

function Respond({ ticket: t, onDone }: { ticket: MyTicket; onDone: () => void }) {
  const toast = useToast();
  const detail = useMyTicket(t.holder_uuid);
  const send = useMessageOffice();
  const toDo = TO_DO.includes(t.state);
  const [answering, setAnswering] = React.useState(false);
  if (detail.isLoading) return <Skeleton className="h-40" />;
  if (detail.error) return <Alert tone="danger">{detail.error.userMessage()}</Alert>;
  const brief = detail.data?.ticket.brief ?? t.brief;
  const closed = t.request_status === "closed";
  return (
    <div className="space-y-4">
      {brief && (
        <details open={!detail.data?.messages.some((m) => m.kind === "brief")}>
          <summary className="cursor-pointer text-xs font-medium uppercase tracking-wider text-text-subtle">
            What the platform already knows
          </summary>
          <div className="mt-2">
            <BriefPanel brief={brief} />
          </div>
        </details>
      )}
      <Thread
        messages={detail.data?.messages ?? []}
        you="holder"
        evidenceHref={(m) => (m.evidence_hash ? myMessageAttachmentUrl(t.holder_uuid, m.message_uuid) : null)}
      />
      {toDo &&
        (answering ? (
          <AnswerForm ticket={t} onCancel={() => setAnswering(false)} onDone={onDone} />
        ) : (
          <div className="flex flex-wrap items-center gap-3 rounded-md border border-accent-border bg-accent-subtle p-3">
            <Button variant="primary" size="sm" onClick={() => setAnswering(true)}>
              <Send className="size-4" aria-hidden="true" />
              Submit your answer
            </Button>
            <span className="text-xs text-text-muted">When your work is done: what was done, what you hold, and any proof.</span>
          </div>
        ))}
      {!answering && (
        <ReplyBox
          pending={send.isPending}
          placeholder="Write to the Privacy Office: a question, or what you have found so far."
          disabledReason={closed ? "The request is closed; nothing more can be written." : null}
          onSend={async (body, file) => {
            await send.mutateAsync({ holderUuid: t.holder_uuid, body, evidence: file });
            // The window stays open: the message is on the thread above, and
            // the answer may follow it.
            toast.success("Message sent", "The Privacy Office can see it.");
          }}
        />
      )}
    </div>
  );
}

function AnswerForm({ ticket: t, onCancel, onDone }: { ticket: MyTicket; onCancel: () => void; onDone: () => void }) {
  const toast = useToast();
  const ret = useReturnMyTicket();
  // No default: "did all of it" is not assumed (review DPDP-1).
  const [outcome, setOutcome] = React.useState<ReturnOutcome | "">("");
  const [summary, setSummary] = React.useState("");
  const [file, setFile] = React.useState<File | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  return (
    <form
      method="post"
      noValidate
      className="space-y-4 rounded-md border border-accent-border p-4"
      onSubmit={async (e) => {
        e.preventDefault();
        if (!outcome || !summary.trim()) return;
        setError(null);
        try {
          await ret.mutateAsync({ holderUuid: t.holder_uuid, summary: summary.trim(), outcome, evidence: file });
          toast.success("Answer sent", "The Privacy Office will review it.");
          onDone();
        } catch (err) {
          setError(err && typeof err === "object" && "userMessage" in err ? (err as { userMessage: () => string }).userMessage() : "Could not send your answer.");
        }
      }}
    >
      <h3 className="text-sm font-semibold">Submit your answer</h3>
      {error && <Alert tone="danger">{error}</Alert>}
      <fieldset className="space-y-1.5">
        <legend className="text-sm font-medium">1 · What was done?</legend>
        {(Object.keys(RETURN_OUTCOME_COPY) as ReturnOutcome[]).map((o) => (
          <label key={o} className="flex items-center gap-2 text-sm">
            <input type="radio" name="outcome" className="size-4 accent-[var(--accent)]" checked={outcome === o} onChange={() => setOutcome(o)} />
            {RETURN_OUTCOME_COPY[o]}
          </label>
        ))}
        <p className="text-xs text-text-muted">Only “did all of it” counts as done. If you could not do some or all of it, say why below.</p>
      </fieldset>
      <Field label="2 · What you hold, and what you did" required>
        {(p) => <Textarea {...p} rows={4} value={summary} onChange={(e) => setSummary(e.target.value)} />}
      </Field>
      <FileInput
        label="3 · Proof"
        hint="Optional. PDF, image, CSV or text, up to 25 MB."
        accept="application/pdf,image/png,image/jpeg,text/csv,text/plain"
        maxBytes={25 * 1024 * 1024}
        file={file}
        onChange={setFile}
      />
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" size="sm" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" size="sm" loading={ret.isPending} disabled={!outcome || !summary.trim()}>
          Send your answer
        </Button>
      </div>
    </form>
  );
}
