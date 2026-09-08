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

import { AlertTriangle, CheckCircle2, Inbox } from "lucide-react";
import * as React from "react";

import { FileInput } from "@/components/forms";
import { PageHeader } from "@/components/layout/app-shell";
import { Dialog, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { EmptyQueue } from "@/components/ui/graphics";
import {
  Alert,
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
import { RequestTypeBadge, TicketBadge } from "@/features/rights/components/copy";
import { useReturnMyTicket } from "@/features/rights/mutations";
import { useMyTickets } from "@/features/rights/queries";
import { formatDate, formatDateTime } from "@/lib/format";
import { useToast } from "@/providers";
import type { MyTicket } from "@/types";

export default function TicketsPage() {
  const tickets = useMyTickets();
  const open = (tickets.data ?? []).filter((t) => t.ticket_status === "issued" || t.ticket_status === "escalated");
  const done = (tickets.data ?? []).filter((t) => !open.includes(t));

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
            <TicketCard key={t.holder_uuid} ticket={t} />
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
            <TicketCard key={t.holder_uuid} ticket={t} />
          ))}
        </section>
      )}
    </>
  );
}

function TicketCard({ ticket: t }: { ticket: MyTicket }) {
  const [returning, setReturning] = React.useState(false);
  const isOpen = t.ticket_status === "issued" || t.ticket_status === "escalated";
  const overdue = isOpen && t.due_at && new Date(t.due_at) < new Date();

  return (
    <Card data-testid="ticket">
      <CardHeader className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <CardTitle className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-sm">{t.reference}</span>
            <RequestTypeBadge type={t.request_type} />
            <TicketBadge status={t.ticket_status} />
          </CardTitle>
          <p className="mt-1 text-xs text-text-muted">
            For {t.label}
            {t.subject_name && ` · about ${t.subject_name}`}
            {t.issued_at && ` · issued ${formatDateTime(t.issued_at)}`}
          </p>
        </div>
        {t.due_at && (
          <p className={overdue ? "flex items-center gap-1 text-sm font-medium text-danger-text" : "text-sm text-text-muted"}>
            {overdue && <AlertTriangle className="size-4" aria-hidden="true" />}
            {overdue ? "Overdue - was due " : "Due "}
            {formatDate(t.due_at)}
          </p>
        )}
      </CardHeader>
      <CardBody className="space-y-3">
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
        {isOpen && (
          <Button variant="primary" size="sm" onClick={() => setReturning(true)}>
            Return this ticket
          </Button>
        )}
      </CardBody>
      <Dialog open={returning} onOpenChange={(next) => !next && setReturning(false)}>
        <DialogContent
          title={`Return ${t.reference}`}
          description="What was done and how - a confirmation, not an assurance. Evidence is optional and kept with the ticket."
        >
          <ReturnForm ticket={t} onDone={() => setReturning(false)} />
        </DialogContent>
      </Dialog>
    </Card>
  );
}

function ReturnForm({ ticket: t, onDone }: { ticket: MyTicket; onDone: () => void }) {
  const toast = useToast();
  const ret = useReturnMyTicket();
  const [summary, setSummary] = React.useState("");
  const [file, setFile] = React.useState<File | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await ret.mutateAsync({ holderUuid: t.holder_uuid, summary: summary.trim(), evidence: file });
      toast.success("Ticket returned", "The Privacy Office can see it.");
      onDone();
    } catch (err) {
      setError(
        err && typeof err === "object" && "userMessage" in err
          ? (err as { userMessage: () => string }).userMessage()
          : "Could not return the ticket.",
      );
    }
  }

  return (
    <form method="post" onSubmit={submit} noValidate>
      <div className="space-y-4">
        {error && <Alert tone="danger">{error}</Alert>}
        <Field label="What was done" required>
          {(p) => <Textarea {...p} rows={5} maxLength={20_000} value={summary} onChange={(e) => setSummary(e.target.value)} />}
        </Field>
        <FileInput
          label="Evidence"
          hint="PDF, image, CSV or text, up to 25 MB."
          accept="application/pdf,image/png,image/jpeg,text/csv,text/plain"
          maxBytes={25 * 1024 * 1024}
          file={file}
          onChange={setFile}
        />
      </div>
      <DialogFooter>
        <Button type="submit" variant="primary" loading={ret.isPending} disabled={!summary.trim()}>
          Return the ticket
        </Button>
      </DialogFooter>
    </form>
  );
}
