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
 */
"use client";

import { AlertTriangle, CheckCircle2, Inbox, MessageSquareReply } from "lucide-react";
import { useSearchParams } from "next/navigation";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { EmptyQueue } from "@/components/ui/graphics";
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  EmptyState,
  Skeleton,
} from "@/components/ui/primitives";
import { ConsentScope } from "@/features/rights/components/consent-scope";
import { RequestTypeBadge, TicketBadge, dueCopy } from "@/features/rights/components/copy";
import { myMessageAttachmentUrl } from "@/features/rights/api";
import { BriefPanel, ReplyBox, Thread, UnreadBadge } from "@/features/rights/components/thread";
import { useMessageOffice, useReturnMyTicket } from "@/features/rights/mutations";
import { useMyTicket, useMyTickets } from "@/features/rights/queries";
import { formatDate, formatDateTime } from "@/lib/format";
import { useToast } from "@/providers";
import type { MyTicket } from "@/types";

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
  // A link from the dashboard queue or from a mail opens the ticket it names.
  const wanted = useSearchParams().get("ticket");
  // Open ones first, the most pressing at the top: overdue, then soonest due.
  const open = (tickets.data ?? [])
    .filter((t) => t.ticket_status === "issued" || t.ticket_status === "escalated")
    .sort((a, b) => (a.due_at ? new Date(a.due_at).getTime() : Infinity) - (b.due_at ? new Date(b.due_at).getTime() : Infinity));
  const done = (tickets.data ?? []).filter((t) => !open.includes(t));
  const { overdue, soon } = urgency(open);
  const unread = (tickets.data ?? []).reduce((n, t) => n + t.unread_for_holder, 0);

  return (
    <>
      <PageHeader
        eyebrow="Rights requests"
        title="Tickets for you"
        description="A person has asked what we hold about them, or for it to be corrected or erased, and the Privacy Office has asked your team to answer for the data it holds. Return each ticket here with what was done."
      />

      {tickets.isLoading && <Skeleton className="h-40" />}
      {tickets.error && (
        <Alert tone="danger" title="Could not load your tickets">
          {tickets.error.userMessage()}
        </Alert>
      )}

      {tickets.data && tickets.data.length > 0 && (
        <div className="mb-6 grid gap-3 sm:grid-cols-4" data-testid="ticket-summary">
          <Stat label="Open" value={open.length} tone="neutral" />
          <Stat label="Overdue" value={overdue} tone={overdue ? "danger" : "neutral"} />
          <Stat label="Due within 7 days" value={soon} tone={soon ? "warning" : "neutral"} />
          <Stat label="Unread from the Privacy Office" value={unread} tone={unread ? "warning" : "neutral"} />
        </div>
      )}

      {tickets.data && tickets.data.length === 0 && (
        <Card>
          <EmptyState
            illustration={<EmptyQueue />}
            title="Nothing addressed to you"
            description="When the Privacy Office issues a ticket to your team, it appears here with its instruction and its date."
          />
        </Card>
      )}

      {open.length > 0 && (
        <section className="space-y-3">
          <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-text-subtle">
            <Inbox className="size-4" aria-hidden="true" />
            Open · {open.length}
          </h2>
          {open.map((t) => (
            <TicketCard key={t.holder_uuid} ticket={t} openAtFirst={t.holder_uuid === wanted} />
          ))}
        </section>
      )}

      {done.length > 0 && (
        <section className="mt-8 space-y-3">
          <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-text-subtle">
            <CheckCircle2 className="size-4" aria-hidden="true" />
            Returned · {done.length}
          </h2>
          {done.map((t) => (
            <TicketCard key={t.holder_uuid} ticket={t} openAtFirst={t.holder_uuid === wanted} />
          ))}
        </section>
      )}
    </>
  );
}

/** How many open tickets are past their date, and how many fall due within a week. */
function urgency(open: MyTicket[]): { overdue: number; soon: number } {
  let overdue = 0;
  let soon = 0;
  for (const t of open) {
    const d = dueCopy(t.due_at, true);
    if (!d) continue;
    if (d.days < 0) overdue += 1;
    else if (d.days <= 7) soon += 1;
  }
  return { overdue, soon };
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

function TicketCard({ ticket: t, openAtFirst }: { ticket: MyTicket; openAtFirst?: boolean }) {
  const [responding, setResponding] = React.useState(Boolean(openAtFirst));
  const isOpen = t.ticket_status === "issued" || t.ticket_status === "escalated";
  const overdue = isOpen && t.due_at && new Date(t.due_at) < new Date();
  const due = dueCopy(t.due_at, isOpen);

  return (
    <Card data-testid="ticket">
      <CardHeader className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <CardTitle className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-sm">{t.reference}</span>
            <RequestTypeBadge type={t.request_type} />
            <TicketBadge status={t.ticket_status} />
            <UnreadBadge count={t.unread_for_holder} />
          </CardTitle>
          <p className="mt-1 text-xs text-text-muted">
            For {t.label}
            {t.subject_name && ` · about ${t.subject_name}`}
            {t.issued_at && ` · issued ${formatDateTime(t.issued_at)}`}
          </p>
        </div>
        {due && (
          <p className={due.tone === "danger" ? "flex items-center gap-1 text-sm font-medium text-danger-text" : due.tone === "warning" ? "text-sm font-medium text-warning-text" : "text-sm text-text-muted"}>
            {overdue && <AlertTriangle className="size-4" aria-hidden="true" />}
            <span className="capitalize">{due.text}</span>
            {t.due_at && <span className="font-normal text-text-muted"> · {formatDate(t.due_at)}</span>}
          </p>
        )}
      </CardHeader>
      <CardBody className="space-y-3">
        {t.ticket_status === "withdrawn" && (
          <Alert tone="info">
            <p className="text-sm">Withdrawn by the Privacy Office. Nothing further is needed from you; the reason is on the thread.</p>
          </Alert>
        )}
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
          <p className="text-xs font-medium uppercase tracking-wider text-text-subtle">Instruction</p>
          <p className="mt-1 whitespace-pre-wrap text-sm">{t.instruction ?? "See the Privacy Office."}</p>
        </div>
        {t.return_summary && (
          <div className="rounded-md bg-bg-inset p-3 text-sm">
            <span className="font-medium">Returned{t.returned_at && ` ${formatDateTime(t.returned_at)}`}: </span>
            {t.return_summary}
          </div>
        )}
        <div className="flex flex-wrap items-center gap-2">
          <Button variant={isOpen ? "primary" : "secondary"} size="sm" onClick={() => setResponding(true)}>
            <MessageSquareReply className="size-4" aria-hidden="true" />
            {isOpen ? "Respond" : "Open"}
            {t.message_count ? ` · ${t.message_count}` : ""}
          </Button>
          {isOpen && (
            <span className="text-xs text-text-muted">
              Ask, send what you have found, or return the ticket - all from one place.
            </span>
          )}
        </div>
      </CardBody>
      <Dialog open={responding} onOpenChange={(next) => !next && setResponding(false)}>
        <DialogContent
          title={`${t.reference} · ${t.label}`}
          description={
            isOpen
              ? "What the platform already knows, everything said so far, and your response. Tick the box to make a response the final return."
              : "This ticket is returned. Everything said is kept; you can still add a note."
          }
        >
          {responding && <Respond ticket={t} onReturned={() => setResponding(false)} />}
        </DialogContent>
      </Dialog>
    </Card>
  );
}

function Respond({ ticket: t, onReturned }: { ticket: MyTicket; onReturned: () => void }) {
  const toast = useToast();
  const detail = useMyTicket(t.holder_uuid);
  const send = useMessageOffice();
  const ret = useReturnMyTicket();
  const isOpen = t.ticket_status === "issued" || t.ticket_status === "escalated";
  if (detail.isLoading) return <Skeleton className="h-40" />;
  if (detail.error) return <Alert tone="danger">{detail.error.userMessage()}</Alert>;
  const brief = detail.data?.ticket.brief ?? t.brief;
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
      <ReplyBox
        pending={send.isPending || ret.isPending}
        placeholder={
          isOpen
            ? "Ask the Privacy Office a question, or say what you hold and where."
            : "Add a note to the returned ticket."
        }
        finalOption={
          isOpen
            ? {
                label: "This is my return - close the ticket with it",
                hint: "What you hold, what was done and how. The Privacy Office collates it into the response. Leave unticked to keep the conversation going.",
              }
            : null
        }
        onSend={async (body, file, final) => {
          if (final) {
            await ret.mutateAsync({ holderUuid: t.holder_uuid, summary: body, evidence: file });
            toast.success("Ticket returned", "The Privacy Office can see it.");
            onReturned();
          } else {
            await send.mutateAsync({ holderUuid: t.holder_uuid, body, evidence: file });
          }
        }}
      />
    </div>
  );
}
