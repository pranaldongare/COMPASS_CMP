/**
 * Breach tickets addressed to me (S3-08), on the Tickets page.
 *
 * What the Privacy Office asked of me about a personal data breach, and my
 * answer. Only what BD-13 allows is here: the breach reference, the
 * instruction, the thread, the state and the answer-by date. Nothing else
 * from the register - not its title, not who it touched - reaches this page,
 * and the register itself is not mine to open.
 */
"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, MessageSquareReply, ShieldAlert } from "lucide-react";
import * as React from "react";

import { ReplyBox, Thread, UnreadBadge } from "@/components/data-display/thread";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Alert, Badge, Button, Card, CardBody, CardHeader, CardTitle, Field, Select, Skeleton } from "@/components/ui/primitives";
import { messageBreachOffice, myBreachTicketFileUrl, returnBreachTicket } from "@/features/breach/api";
import { TicketStateBadge } from "@/features/breach/components/tickets-card";
import { useMyBreachTicket } from "@/features/breach/queries";
import { formatDate, formatDateTime } from "@/lib/format";
import { keys } from "@/lib/query";
import { useToast } from "@/providers";
import type { MyBreachTicket, ReturnOutcome } from "@/types";
import { RETURN_OUTCOME_COPY } from "@/types";

export function BreachTicketCard({ ticket: t, openAtFirst }: { ticket: MyBreachTicket; openAtFirst?: boolean }) {
  const [responding, setResponding] = React.useState(Boolean(openAtFirst));
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
        <Button variant={canReturn ? "primary" : "secondary"} size="sm" onClick={() => setResponding(true)}>
          <MessageSquareReply className="size-4" aria-hidden="true" />
          {canReturn ? "Respond" : "Open"}
        </Button>
      </CardBody>
      <Dialog open={responding} onOpenChange={(next) => !next && setResponding(false)}>
        <DialogContent
          title={`${t.breach_reference} · breach ticket`}
          description={
            canReturn
              ? "Everything said so far, and your response. Tick the box to make a response your return."
              : "Everything said is kept. Only the Privacy Office closes a ticket."
          }
        >
          {responding && <Respond ticket={t} onReturned={() => setResponding(false)} />}
        </DialogContent>
      </Dialog>
    </Card>
  );
}

function Respond({ ticket: t, onReturned }: { ticket: MyBreachTicket; onReturned: () => void }) {
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
            onReturned();
          } else {
            await send.mutateAsync({ body, evidence: file });
          }
        }}
      />
    </div>
  );
}
