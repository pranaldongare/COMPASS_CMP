/**
 * Who holds the person's data, what each was asked, and their answers
 * (reworked 2026-10-08).
 *
 * A guided path - find who holds the data, choose who answers, send tickets,
 * wait for answers, review them - with only the step at hand offered. One
 * table: holder, state, due, last activity, next action. A row opens its
 * ticket: what it was asked (the instruction and the brief, no longer hidden
 * in a thread), its answer, its thread, and what may be done now - the main
 * move first, the rest under More.
 *
 * Nothing here decides what a ticket may do: the server sends each holder's
 * state in words, whether it is overdue, and its moves, and the card draws
 * them. An answer counts once the office accepts it.
 */
"use client";

import {
  AlertTriangle,
  Check,
  ChevronRight,
  ExternalLink,
  Mail,
  Monitor,
  MoreHorizontal,
  Plus,
  Search,
  Send,
} from "lucide-react";
import * as React from "react";

import { FileInput } from "@/components/forms";
import { ReplyBox, Thread, UnreadBadge } from "@/components/data-display/thread";
import { Dialog, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { Menu, MenuItem } from "@/components/ui/menu";
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
import { useProcessors, useRespondents } from "@/features/registry";
import { holderMessageAttachmentUrl } from "@/features/rights/api";
import { ConfinedNote } from "@/features/rights/components/consent-scope";
import { BriefPanel } from "@/features/rights/components/thread";
import {
  useAcceptTicket,
  useAddHolder,
  useConfirmHolder,
  useDeriveHolders,
  useEscalateTicket,
  useIssueTickets,
  useLogContact,
  usePostToHolder,
  useReassignHolder,
  useRemindHolder,
  useRemoveHolder,
  useReopenTicket,
  useReturnTicket,
  useSendBackTicket,
  useWithdrawTicket,
} from "@/features/rights/mutations";
import { useHolderThread } from "@/features/rights/queries";
import { config } from "@/lib/config";
import { formatDate, formatDateTime } from "@/lib/format";
import { useToast } from "@/providers";
import type {
  ReturnOutcome,
  RightsHolder,
  RightsRequestDetail,
  TicketMove,
  TicketMoveName,
  TicketState,
} from "@/types";
import { RETURN_OUTCOME_COPY } from "@/types";

function messageOf(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}

/** The end of the chosen day: a ticket due today is overdue tomorrow. */
function endOfDay(date: string): string {
  return new Date(`${date}T23:59:00`).toISOString();
}

type Tone = "neutral" | "accent" | "success" | "warning" | "danger" | "info";

const STATE_TONE: Record<TicketState, Tone> = {
  not_confirmed: "warning",
  not_sent: "neutral",
  waiting: "info",
  sent_back: "warning",
  overdue: "danger",
  final_reminder: "danger",
  review: "accent",
  accepted: "success",
  withdrawn: "neutral",
  no_answer: "danger",
};

/** An accepted answer that did not do all of it is not a success. */
function stateBadge(h: RightsHolder) {
  let tone = STATE_TONE[h.state] ?? "neutral";
  let label = h.state_label;
  if ((h.state === "accepted" || h.state === "review") && h.return_outcome && h.return_outcome !== "done") {
    tone = h.return_outcome === "failed" ? "danger" : "warning";
    label = `${h.state_label} · ${RETURN_OUTCOME_COPY[h.return_outcome].toLowerCase()}`;
  }
  return (
    <Badge tone={tone} dot>
      {label}
    </Badge>
  );
}

const WORKING = ["in_progress", "awaiting_holders"];

const STEPS: { key: string; label: string }[] = [
  { key: "find", label: "Find who holds the data" },
  { key: "choose", label: "Choose who answers" },
  { key: "send", label: "Send tickets" },
  { key: "wait", label: "Wait for answers" },
  { key: "review", label: "Review answers" },
];

function stepOf(holders: RightsHolder[]): number {
  if (holders.length === 0) return 0;
  if (holders.some((h) => h.state === "not_confirmed")) return 1;
  if (holders.some((h) => h.state === "not_sent")) return 2;
  if (holders.some((h) => h.state === "review")) return 4;
  if (holders.some((h) => ["waiting", "sent_back", "overdue", "final_reminder"].includes(h.state))) return 3;
  return 5;
}

function Stepper({ holders }: { holders: RightsHolder[] }) {
  const at = stepOf(holders);
  const count = (states: TicketState[]) => holders.filter((h) => states.includes(h.state)).length;
  const notes = [
    holders.length ? `${holders.length} found` : "",
    count(["not_confirmed"]) ? `${count(["not_confirmed"])} to confirm` : "",
    count(["not_sent"]) ? `${count(["not_sent"])} to send` : "",
    count(["waiting", "sent_back", "overdue", "final_reminder"])
      ? `${count(["waiting", "sent_back", "overdue", "final_reminder"])} waiting${count(["overdue", "final_reminder"]) ? `, ${count(["overdue", "final_reminder"])} overdue` : ""}`
      : "",
    count(["review"]) ? `${count(["review"])} to review` : "",
  ];
  return (
    <ol className="flex flex-wrap gap-x-1 gap-y-2 text-xs" aria-label="Where the tickets stand">
      {STEPS.map((s, i) => {
        const done = i < at;
        const current = i === at;
        return (
          <li key={s.key} className="flex items-center gap-1">
            <span
              className={
                current
                  ? "flex items-center gap-1.5 rounded-full border border-accent-border bg-accent-subtle px-2.5 py-1 font-semibold text-accent-text"
                  : done
                    ? "flex items-center gap-1.5 rounded-full px-2.5 py-1 text-text-muted"
                    : "flex items-center gap-1.5 rounded-full px-2.5 py-1 text-text-subtle"
              }
              aria-current={current ? "step" : undefined}
            >
              {done ? (
                <Check className="size-3.5 text-success-text" aria-hidden="true" />
              ) : (
                <span className="tabular">{i + 1}</span>
              )}
              {s.label}
              {notes[i] && <span className="font-normal text-text-muted">· {notes[i]}</span>}
            </span>
            {i < STEPS.length - 1 && <ChevronRight className="size-3 text-text-subtle" aria-hidden="true" />}
          </li>
        );
      })}
    </ol>
  );
}

export function HoldersCard({ request: r }: { request: RightsRequestDetail }) {
  const toast = useToast();
  const uuid = r.request_uuid;
  const derive = useDeriveHolders(uuid);
  const [adding, setAdding] = React.useState(false);
  const [openUuid, setOpenUuid] = React.useState<string | null>(null);
  const [startWith, setStartWith] = React.useState<TicketMoveName | null>(null);

  const working = WORKING.includes(r.status);
  const unsent = r.holders.filter((h) => h.state === "not_sent");
  const opened = r.holders.find((h) => h.holder_uuid === openUuid) ?? null;

  function open(h: RightsHolder, move: TicketMoveName | null = null) {
    setStartWith(move);
    setOpenUuid(h.holder_uuid);
  }

  return (
    <Card id="holders" className="scroll-mt-20">
      <CardHeader className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 space-y-2">
          <CardTitle>{r.request_type === "erasure" ? "7–9 · Holders and tickets" : "6–8 · Holders and tickets"}</CardTitle>
          <p className="text-xs text-text-muted">
            Who holds this person&apos;s data, what each was asked, and their answers. An answer counts
            once you accept it.
          </p>
          {r.consent_uuid && <ConfinedNote project={r.consent_project} />}
          <Stepper holders={r.holders} />
        </div>
        {working && (
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              size="sm"
              loading={derive.isPending}
              onClick={async () => {
                try {
                  await derive.mutateAsync();
                  toast.success("Holders found", "Confirm who answers for each, then send the tickets.");
                } catch (err) {
                  toast.error("Not done", messageOf(err, "The server refused."));
                }
              }}
            >
              <Search className="size-4" />
              Find who holds the data
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
            {working
              ? "No holders yet. Find who holds the data from the records, or add one you know of."
              : r.status === "received"
                ? "Start the request first."
                : "No holders: nothing was held anywhere."}
          </p>
        ) : (
          <Table>
            <caption className="sr-only">Holders and their tickets</caption>
            <thead>
              <tr>
                <Th>Holder</Th>
                <Th>State</Th>
                <Th>Answer by</Th>
                <Th>Last activity</Th>
                {/* Visible, not sr-only: an absolute label inside the
                    scrolling table widened the whole page on a phone. */}
                <Th>Next</Th>
              </tr>
            </thead>
            <tbody>
              {r.holders.map((h) => {
                const main = h.moves.find((m) => m.primary);
                return (
                  <Tr key={h.holder_uuid} className={h.overdue ? "bg-danger-subtle/40" : undefined}>
                    <Td>
                      <button
                        type="button"
                        className="text-left font-medium text-accent-text hover:underline"
                        onClick={() => open(h)}
                      >
                        {h.label}
                      </button>
                      <span className="mt-0.5 flex flex-wrap items-center gap-1.5 text-xs text-text-muted">
                        {h.channel === "portal" ? (
                          <>
                            <Monitor className="size-3" aria-hidden="true" /> In the console
                          </>
                        ) : (
                          <>
                            <Mail className="size-3" aria-hidden="true" /> By email
                          </>
                        )}
                        {h.responder_user_name || h.responder_name ? ` · ${h.responder_user_name ?? h.responder_name}` : ""}
                        <UnreadBadge count={h.unread_for_office} />
                      </span>
                    </Td>
                    <Td>{stateBadge(h)}</Td>
                    <Td className={h.overdue ? "whitespace-nowrap font-medium text-danger-text" : "whitespace-nowrap text-text-muted"}>
                      {h.overdue && <AlertTriangle className="mr-1 inline size-3.5" aria-hidden="true" />}
                      {h.due_at ? formatDate(h.due_at) : "-"}
                    </Td>
                    <Td className="whitespace-nowrap text-text-muted">
                      {h.last_activity_at ? formatDateTime(h.last_activity_at) : "-"}
                    </Td>
                    <Td className="text-right">
                      <Button
                        variant={main ? "primary" : "ghost"}
                        size="sm"
                        onClick={() => open(h, main?.move ?? null)}
                      >
                        {main ? main.label : "Open"}
                      </Button>
                    </Td>
                  </Tr>
                );
              })}
            </tbody>
          </Table>
        )}

        {working && unsent.length > 0 && <SendTickets request={r} count={unsent.length} />}
      </CardBody>

      <Dialog open={adding} onOpenChange={(next) => !next && setAdding(false)}>
        <DialogContent
          title="Add a holder"
          description="Somebody the records did not name. Added as confirmed - you are the source."
        >
          <AddHolderForm request={r} onDone={() => setAdding(false)} />
        </DialogContent>
      </Dialog>

      <Dialog open={opened !== null} onOpenChange={(next) => !next && setOpenUuid(null)}>
        {opened && (
          <DialogContent title={opened.label} description={describe(opened)} size="lg">
            <TicketPanel
              key={`${opened.holder_uuid}:${opened.state}`}
              request={r}
              holder={opened}
              startWith={startWith}
              onClose={() => setOpenUuid(null)}
            />
          </DialogContent>
        )}
      </Dialog>
    </Card>
  );
}

function describe(h: RightsHolder): string {
  const reach =
    h.channel === "portal"
      ? `They answer in the console${h.responder_user_name ? ` (${h.responder_user_name})` : ""}.`
      : `They are reached by email${h.responder_contact ? ` at ${h.responder_contact}` : ""}; you record their answer.`;
  return `${h.state_label}${h.due_at ? ` · answer by ${formatDate(h.due_at)}` : ""}. ${reach}`;
}

function SendTickets({ request: r, count }: { request: RightsRequestDetail; count: number }) {
  const toast = useToast();
  const issue = useIssueTickets(r.request_uuid);
  const [open, setOpen] = React.useState(false);
  const [instruction, setInstruction] = React.useState("");
  const [dueOn, setDueOn] = React.useState("");
  return (
    <div className="rounded-md border border-accent-border bg-accent-subtle p-3">
      <p className="text-sm font-medium text-accent-text">
        {count} holder{count === 1 ? " is" : "s are"} ready for a ticket
      </p>
      {open ? (
        <div className="mt-2 space-y-3">
          <Field label="What you ask them" hint="Leave empty for the standard words for this kind of request.">
            {(p) => <Textarea {...p} rows={3} value={instruction} onChange={(e) => setInstruction(e.target.value)} />}
          </Field>
          <Field
            label="Answer by"
            hint={`Halfway to the response date (${formatDate(r.clock.halfway_at)}) unless you choose a day - early on purpose, so a late answer can still be chased in time.`}
          >
            {(p) => <Input {...p} type="date" value={dueOn} onChange={(e) => setDueOn(e.target.value)} />}
          </Field>
          <div className="flex gap-2">
            <Button
              variant="primary"
              size="sm"
              loading={issue.isPending}
              onClick={async () => {
                try {
                  await issue.mutateAsync({
                    instruction: instruction.trim() || null,
                    due_at: dueOn ? endOfDay(dueOn) : null,
                  });
                  toast.success(count === 1 ? "Ticket sent" : `${count} tickets sent`, "You will see each answer here when it comes.");
                  setOpen(false);
                } catch (err) {
                  toast.error("Not sent", messageOf(err, "The server refused."));
                }
              }}
            >
              <Send className="size-4" />
              Send {count === 1 ? "the ticket" : `${count} tickets`}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setOpen(false)}>
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <Button variant="primary" size="sm" className="mt-2" onClick={() => setOpen(true)}>
          <Send className="size-4" />
          Send tickets
        </Button>
      )}
    </div>
  );
}

/** One ticket: what it was asked, its answer, its thread, and what may be done now. */
function TicketPanel({
  request: r,
  holder: h,
  startWith,
  onClose,
}: {
  request: RightsRequestDetail;
  holder: RightsHolder;
  startWith: TicketMoveName | null;
  onClose: () => void;
}) {
  // Moves that open a form start on it; the rest (accept, remind, ...) wait
  // for a confirming click inside the panel.
  const [acting, setActing] = React.useState<TicketMoveName | null>(startWith);
  const main = h.moves.find((m) => m.primary);
  const rest = h.moves.filter((m) => m !== main && m.move !== "message");
  const actingMove = h.moves.find((m) => m.move === acting) ?? null;

  return (
    <div className="space-y-5">
      {actingMove ? (
        <MoveForm request={r} holder={h} move={actingMove} onDone={() => setActing(null)} onClose={onClose} />
      ) : (
        h.moves.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            {main && (
              <Button variant="primary" size="sm" onClick={() => setActing(main.move)}>
                {main.label}
              </Button>
            )}
            {rest.length > 0 && (
              <Menu
                label="More actions"
                trigger={
                  <span className="inline-flex items-center gap-1 text-sm">
                    <MoreHorizontal className="size-4" aria-hidden="true" /> More
                  </span>
                }
                align="start"
              >
                {rest.map((m) => (
                  <MenuItem key={m.move} onSelect={() => setActing(m.move)}>
                    {m.label}
                  </MenuItem>
                ))}
              </Menu>
            )}
          </div>
        )
      )}

      {h.return_summary && (
        <section className="rounded-md border border-border p-3">
          <h3 className="text-xs font-semibold tracking-wide text-text-subtle uppercase">Their answer</h3>
          <p className="mt-1 text-sm">
            {stateBadge(h)}
            {h.returned_at && <span className="ml-2 text-xs text-text-muted">{formatDateTime(h.returned_at)}</span>}
          </p>
          <p className="mt-2 text-sm whitespace-pre-wrap">{h.return_summary}</p>
          {h.return_evidence_hash && (
            <a
              className="mt-2 inline-flex items-center gap-1 text-sm text-accent-text underline underline-offset-2"
              href={`${config.apiUrl}/requests/${r.request_uuid}/holders/${h.holder_uuid}/evidence`}
            >
              {h.return_evidence_name ?? "Their proof"} <ExternalLink className="size-3" aria-hidden="true" />
            </a>
          )}
          {h.accepted_at && (
            <p className="mt-2 text-xs text-text-muted">
              Accepted {formatDateTime(h.accepted_at)}
              {h.accepted_by_name ? ` by ${h.accepted_by_name}` : ""}
            </p>
          )}
        </section>
      )}

      {(h.instruction || h.brief) && (
        <section className="space-y-2">
          <h3 className="text-xs font-semibold tracking-wide text-text-subtle uppercase">What they were asked</h3>
          {h.instruction && <p className="rounded-md bg-bg-inset p-3 text-sm whitespace-pre-wrap">{h.instruction}</p>}
          {h.brief && (
            <details className="text-sm">
              <summary className="cursor-pointer text-accent-text">What the platform holds about the person</summary>
              <div className="mt-2">
                <BriefPanel brief={h.brief} />
              </div>
            </details>
          )}
        </section>
      )}

      {h.issued_at && <ThreadSection request={r} holder={h} />}

      {h.contact_log.length > 0 && (
        <details className="text-xs">
          <summary className="cursor-pointer text-text-muted">Everything sent and noted · {h.contact_log.length}</summary>
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
    </div>
  );
}

function ThreadSection({ request: r, holder: h }: { request: RightsRequestDetail; holder: RightsHolder }) {
  const thread = useHolderThread(r.request_uuid, h.holder_uuid);
  const post = usePostToHolder(r.request_uuid);
  const canWrite = h.moves.some((m) => m.move === "message");
  return (
    <section className="space-y-3">
      <h3 className="text-xs font-semibold tracking-wide text-text-subtle uppercase">Messages</h3>
      {thread.isLoading ? (
        <Skeleton className="h-24" />
      ) : thread.error ? (
        <Alert tone="danger">{thread.error.userMessage()}</Alert>
      ) : (
        <Thread
          messages={thread.data?.messages ?? []}
          you="office"
          evidenceHref={(m) =>
            m.evidence_hash ? holderMessageAttachmentUrl(r.request_uuid, h.holder_uuid, m.message_uuid) : null
          }
        />
      )}
      <ReplyBox
        pending={post.isPending}
        placeholder={h.channel === "portal" ? "Write to them - they read it in the console." : "Write to them - it is emailed to them."}
        disabledReason={canWrite ? null : "Nothing more can be written on this ticket."}
        onSend={async (body, file) => {
          await post.mutateAsync({ holderUuid: h.holder_uuid, body, evidence: file });
        }}
      />
    </section>
  );
}

/** One move, as a short form or a confirmation, inside the ticket. */
function MoveForm({
  request: r,
  holder: h,
  move,
  onDone,
  onClose,
}: {
  request: RightsRequestDetail;
  holder: RightsHolder;
  move: TicketMove;
  onDone: () => void;
  onClose: () => void;
}) {
  const uuid = r.request_uuid;
  const toast = useToast();
  const accept = useAcceptTicket(uuid);
  const remind = useRemindHolder(uuid);
  const escalate = useEscalateTicket(uuid);
  const remove = useRemoveHolder(uuid);

  async function confirm(fn: () => Promise<unknown>, title: string, after?: () => void) {
    try {
      await fn();
      toast.success(title);
      (after ?? onDone)();
    } catch (err) {
      toast.error("Not done", messageOf(err, "The server refused."));
    }
  }

  const who = h.responder_user_name ?? h.responder_name ?? h.label;
  const frame = (children: React.ReactNode) => (
    <section className="rounded-md border border-accent-border bg-accent-subtle/40 p-3">
      <h3 className="mb-2 text-sm font-semibold">{move.label}</h3>
      {children}
    </section>
  );
  const simple = (text: string, button: string, run: () => Promise<unknown>, pending: boolean, title: string, after?: () => void) =>
    frame(
      <>
        <p className="text-sm">{text}</p>
        <div className="mt-3 flex gap-2">
          <Button variant="primary" size="sm" loading={pending} onClick={() => confirm(run, title, after)}>
            {button}
          </Button>
          <Button variant="ghost" size="sm" onClick={onDone}>
            Cancel
          </Button>
        </div>
      </>,
    );

  switch (move.move) {
    case "accept":
      return simple(
        h.return_outcome && h.return_outcome !== "done"
          ? `Their answer: ${RETURN_OUTCOME_COPY[h.return_outcome].toLowerCase()}. Accepting takes the answer as it is: the response will say what was not done. To ask again, send it back instead.`
          : "Accepting takes this answer as the holder's. It then counts toward closing the request.",
        "Accept the answer",
        () => accept.mutateAsync(h.holder_uuid),
        accept.isPending,
        "Answer accepted",
      );
    case "remind":
      return simple(
        `Email ${who} a reminder now${h.due_at ? `: their answer is due ${formatDate(h.due_at)}` : ""}. Reminders also go out by themselves every day once it is overdue.`,
        "Send the reminder",
        () => remind.mutateAsync(h.holder_uuid),
        remind.isPending,
        "Reminder sent",
      );
    case "final_reminder":
      return simple(
        `Send ${who} a final reminder that the date has passed. It is sent once, and lets the response go out without their answer, saying it is missing.`,
        "Send final reminder",
        () => escalate.mutateAsync(h.holder_uuid),
        escalate.isPending,
        "Final reminder sent",
      );
    case "remove":
      return simple(
        "Remove this holder from the request. Nothing has been sent to them, so nothing is lost.",
        "Remove",
        () => remove.mutateAsync(h.holder_uuid),
        remove.isPending,
        "Holder removed",
        onClose,
      );
    case "confirm":
      return frame(<ConfirmForm request={r} holder={h} onDone={onDone} />);
    case "record_answer":
      return frame(<ReturnForm request={r} holder={h} onDone={onDone} />);
    case "send_back":
      return frame(<SendBackForm request={r} holder={h} onDone={onDone} />);
    case "withdraw":
      return frame(<WithdrawForm request={r} holder={h} onDone={onDone} />);
    case "reassign":
      return frame(<ReassignForm request={r} holder={h} onDone={onDone} />);
    case "log_contact":
      return frame(<ContactForm request={r} holder={h} onDone={onDone} />);
    case "reopen":
      return frame(<ReopenForm request={r} holder={h} onDone={onDone} />);
    default:
      return null;
  }
}

function FormButtons({ pending, disabled, label, onCancel }: { pending: boolean; disabled?: boolean; label: string; onCancel: () => void }) {
  return (
    <DialogFooter>
      <Button type="button" variant="ghost" onClick={onCancel}>
        Cancel
      </Button>
      <Button type="submit" variant="primary" loading={pending} disabled={disabled}>
        {label}
      </Button>
    </DialogFooter>
  );
}

function ConfirmForm({ request: r, holder: h, onDone }: { request: RightsRequestDetail; holder: RightsHolder; onDone: () => void }) {
  const toast = useToast();
  const confirm = useConfirmHolder(r.request_uuid);
  const respondents = useRespondents(h.processor_uuid ?? undefined);
  const [respondentUuid, setRespondentUuid] = React.useState(h.respondent_uuid ?? "");
  const [name, setName] = React.useState(h.responder_name ?? "");
  const [contact, setContact] = React.useState(h.responder_contact ?? "");
  return (
    <form
      method="post"
      noValidate
      onSubmit={async (e) => {
        e.preventDefault();
        try {
          await confirm.mutateAsync(
            respondentUuid
              ? { holderUuid: h.holder_uuid, respondent_uuid: respondentUuid }
              : { holderUuid: h.holder_uuid, responder_name: name || null, responder_contact: contact || null },
          );
          toast.success("Confirmed", "Send the tickets when every holder is confirmed.");
          onDone();
        } catch (err) {
          toast.error("Not confirmed", messageOf(err, "The server refused."));
        }
      }}
    >
      <div className="space-y-3">
        {(respondents.data?.length ?? 0) > 0 && (
          <Field label="Who answers" hint="Somebody with a console login answers there; anybody else is emailed.">
            {(p) => (
              <Select {...p} value={respondentUuid} onChange={(e) => setRespondentUuid(e.target.value)}>
                <option value="">Somebody else - type them below</option>
                {respondents.data!.map((rs) => (
                  <option key={rs.respondent_uuid} value={rs.respondent_uuid}>
                    {rs.name} · {rs.contact} · {rs.user_uuid ? "in the console" : "by email"}
                  </option>
                ))}
              </Select>
            )}
          </Field>
        )}
        {!respondentUuid && (
          <div className="grid gap-2 sm:grid-cols-2">
            <Field label="Their name">{(p) => <Input {...p} value={name} onChange={(e) => setName(e.target.value)} />}</Field>
            <Field label="Their email" hint="The ticket is emailed here.">
              {(p) => <Input {...p} type="email" value={contact} onChange={(e) => setContact(e.target.value)} />}
            </Field>
          </div>
        )}
      </div>
      <FormButtons pending={confirm.isPending} label="Confirm" onCancel={onDone} />
    </form>
  );
}

function ReassignForm({ request: r, holder: h, onDone }: { request: RightsRequestDetail; holder: RightsHolder; onDone: () => void }) {
  const toast = useToast();
  const reassign = useReassignHolder(r.request_uuid);
  const respondents = useRespondents(h.processor_uuid ?? undefined);
  const [respondentUuid, setRespondentUuid] = React.useState("");
  const [name, setName] = React.useState("");
  const [contact, setContact] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const options = (respondents.data ?? []).filter((rs) => rs.respondent_uuid !== h.respondent_uuid);
  return (
    <form
      method="post"
      noValidate
      onSubmit={async (e) => {
        e.preventDefault();
        setError(null);
        try {
          await reassign.mutateAsync(
            respondentUuid
              ? { holderUuid: h.holder_uuid, respondent_uuid: respondentUuid }
              : { holderUuid: h.holder_uuid, responder_name: name.trim(), responder_contact: contact.trim() },
          );
          toast.success("Sent to someone else", "They have the ticket; whoever had it has been told.");
          onDone();
        } catch (err) {
          setError(messageOf(err, "Could not send it on."));
        }
      }}
    >
      <div className="space-y-3">
        <p className="text-xs text-text-muted">The ticket and what it asks go to them; whoever had it is told it has moved.</p>
        {error && <Alert tone="danger">{error}</Alert>}
        {options.length > 0 && (
          <Field label="Who answers instead">
            {(p) => (
              <Select {...p} value={respondentUuid} onChange={(e) => setRespondentUuid(e.target.value)}>
                <option value="">Somebody else - type them below</option>
                {options.map((rs) => (
                  <option key={rs.respondent_uuid} value={rs.respondent_uuid}>
                    {rs.name} · {rs.contact} · {rs.user_uuid ? "in the console" : "by email"}
                  </option>
                ))}
              </Select>
            )}
          </Field>
        )}
        {!respondentUuid && (
          <div className="grid gap-2 sm:grid-cols-2">
            <Field label="Their name" required>{(p) => <Input {...p} value={name} onChange={(e) => setName(e.target.value)} />}</Field>
            <Field label="Their email" required>{(p) => <Input {...p} type="email" value={contact} onChange={(e) => setContact(e.target.value)} />}</Field>
          </div>
        )}
      </div>
      <FormButtons
        pending={reassign.isPending}
        disabled={!respondentUuid && (!name.trim() || !contact.trim())}
        label="Send to them"
        onCancel={onDone}
      />
    </form>
  );
}

function SendBackForm({ request: r, holder: h, onDone }: { request: RightsRequestDetail; holder: RightsHolder; onDone: () => void }) {
  const toast = useToast();
  const sendBack = useSendBackTicket(r.request_uuid);
  const [reason, setReason] = React.useState("");
  const [date, setDate] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  return (
    <form
      method="post"
      noValidate
      onSubmit={async (e) => {
        e.preventDefault();
        setError(null);
        try {
          await sendBack.mutateAsync({ holderUuid: h.holder_uuid, reason: reason.trim(), due_at: date ? endOfDay(date) : null });
          toast.success("Sent back", `${h.label} has been told what is missing.`);
          onDone();
        } catch (err) {
          setError(messageOf(err, "Could not send it back."));
        }
      }}
    >
      <div className="space-y-3">
        <p className="text-xs text-text-muted">The ticket opens again with your reason and a date; what they sent stays on the record.</p>
        {error && <Alert tone="danger">{error}</Alert>}
        <Field label="What is missing or wrong" hint="Sent to them, and kept with the ticket." required>
          {(p) => <Textarea {...p} rows={3} maxLength={2000} value={reason} onChange={(e) => setReason(e.target.value)} />}
        </Field>
        <Field label="Answer again by" hint={h.due_at ? `Leave empty to keep ${formatDate(h.due_at)}.` : undefined}>
          {(p) => <Input {...p} type="date" value={date} onChange={(e) => setDate(e.target.value)} />}
        </Field>
      </div>
      <FormButtons pending={sendBack.isPending} disabled={!reason.trim()} label="Send it back" onCancel={onDone} />
    </form>
  );
}

function WithdrawForm({ request: r, holder: h, onDone }: { request: RightsRequestDetail; holder: RightsHolder; onDone: () => void }) {
  const toast = useToast();
  const withdraw = useWithdrawTicket(r.request_uuid);
  const [reason, setReason] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  return (
    <form
      method="post"
      noValidate
      onSubmit={async (e) => {
        e.preventDefault();
        setError(null);
        try {
          await withdraw.mutateAsync({ holderUuid: h.holder_uuid, reason: reason.trim() });
          toast.success("Ticket withdrawn", `${h.label} has been told. You can reopen it if needed.`);
          onDone();
        } catch (err) {
          setError(messageOf(err, "Could not withdraw."));
        }
      }}
    >
      <div className="space-y-3">
        <p className="text-xs text-text-muted">For a ticket sent in error, or a holder that turns out to hold nothing. Not an answer, and not a gap in the response.</p>
        {error && <Alert tone="danger">{error}</Alert>}
        <Field label="Why" hint="Sent to them, and kept with the ticket." required>
          {(p) => <Textarea {...p} rows={3} maxLength={2000} value={reason} onChange={(e) => setReason(e.target.value)} />}
        </Field>
      </div>
      <FormButtons pending={withdraw.isPending} disabled={!reason.trim()} label="Withdraw the ticket" onCancel={onDone} />
    </form>
  );
}

function ReopenForm({ request: r, holder: h, onDone }: { request: RightsRequestDetail; holder: RightsHolder; onDone: () => void }) {
  const toast = useToast();
  const reopen = useReopenTicket(r.request_uuid);
  const [date, setDate] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  return (
    <form
      method="post"
      noValidate
      onSubmit={async (e) => {
        e.preventDefault();
        setError(null);
        try {
          await reopen.mutateAsync({ holderUuid: h.holder_uuid, dueOn: date });
          toast.success("Ticket reopened", `${h.label} has been told.`);
          onDone();
        } catch (err) {
          setError(messageOf(err, "Could not reopen."));
        }
      }}
    >
      <div className="space-y-3">
        {error && <Alert tone="danger">{error}</Alert>}
        <Field label="Answer by" required>
          {(p) => <Input {...p} type="date" value={date} onChange={(e) => setDate(e.target.value)} />}
        </Field>
      </div>
      <FormButtons pending={reopen.isPending} disabled={!date} label="Reopen" onCancel={onDone} />
    </form>
  );
}

const CONTACT_LABEL: Record<string, string> = {
  mail_sent: "Ticket emailed",
  ticket_on_portal: "Ticket in their console",
  chased: "Chased",
  reply_noted: "Reply noted",
  note: "Note",
  escalated: "Final reminder sent",
  returned_on_portal: "Answered in the console",
  sent_back: "Sent back",
  reminder: "Reminder sent",
  reassigned: "Sent to someone else",
  withdrawn: "Withdrawn",
};

function ContactForm({ request: r, holder: h, onDone }: { request: RightsRequestDetail; holder: RightsHolder; onDone: () => void }) {
  const toast = useToast();
  const log = useLogContact(r.request_uuid);
  const [kind, setKind] = React.useState<"mail_sent" | "chased" | "reply_noted" | "note">("chased");
  const [send, setSend] = React.useState(false);
  const [note, setNote] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  return (
    <form
      method="post"
      noValidate
      onSubmit={async (e) => {
        e.preventDefault();
        setError(null);
        try {
          await log.mutateAsync({ holderUuid: h.holder_uuid, kind, note: note.trim() || null, send });
          toast.success(send ? "Ticket emailed again and noted" : "Noted");
          onDone();
        } catch (err) {
          setError(messageOf(err, "Could not note it."));
        }
      }}
    >
      <div className="space-y-3">
        {error && <Alert tone="danger">{error}</Alert>}
        <label className="flex items-start gap-2 text-sm">
          <input type="checkbox" className="mt-0.5 size-4" checked={send} onChange={(e) => setSend(e.target.checked)} />
          <span>
            Email the ticket to {h.responder_contact ?? "them"} again now
            <span className="block text-xs text-text-subtle">The same request and date.</span>
          </span>
        </label>
        {!send && (
          <Field label="What happened">
            {(p) => (
              <Select {...p} value={kind} onChange={(e) => setKind(e.target.value as typeof kind)}>
                <option value="mail_sent">I emailed them from my own inbox</option>
                <option value="chased">I chased them</option>
                <option value="reply_noted">They replied (record their answer separately)</option>
                <option value="note">A note</option>
              </Select>
            )}
          </Field>
        )}
        <Field label="Note" hint="What was said, or where the email is.">
          {(p) => <Textarea {...p} rows={3} maxLength={2000} value={note} onChange={(e) => setNote(e.target.value)} />}
        </Field>
      </div>
      <FormButtons pending={log.isPending} label={send ? "Send and note" : "Note it"} onCancel={onDone} />
    </form>
  );
}

function ReturnForm({ request: r, holder: h, onDone }: { request: RightsRequestDetail; holder: RightsHolder; onDone: () => void }) {
  const toast = useToast();
  const ret = useReturnTicket(r.request_uuid);
  const [summary, setSummary] = React.useState("");
  // No default: "did all of it" pre-chosen is how a ticket answered "unable
  // to erase" came to count as erased (review DPDP-1).
  const [outcome, setOutcome] = React.useState<ReturnOutcome | "">("");
  const [file, setFile] = React.useState<File | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  return (
    <form
      method="post"
      noValidate
      onSubmit={async (e) => {
        e.preventDefault();
        if (!outcome) return;
        setError(null);
        try {
          await ret.mutateAsync({ holderUuid: h.holder_uuid, summary, outcome, evidence: file });
          toast.success("Answer recorded", "Recorded by you, it counts at once.");
          onDone();
        } catch (err) {
          setError(messageOf(err, "Could not record it."));
        }
      }}
    >
      <div className="space-y-3">
        <p className="text-xs text-text-muted">What {h.label} told you they did. Only “did all of it” counts as done.</p>
        {error && <Alert tone="danger">{error}</Alert>}
        <fieldset className="space-y-1.5">
          <legend className="text-sm font-medium">What they did</legend>
          {(Object.keys(RETURN_OUTCOME_COPY) as ReturnOutcome[]).map((o) => (
            <label key={o} className="flex items-center gap-2 text-sm">
              <input type="radio" name="outcome" className="size-4 accent-[var(--accent)]" checked={outcome === o} onChange={() => setOutcome(o)} />
              {RETURN_OUTCOME_COPY[o]}
            </label>
          ))}
        </fieldset>
        <Field label="What they said" required>
          {(p) => <Textarea {...p} rows={4} value={summary} onChange={(e) => setSummary(e.target.value)} />}
        </Field>
        <FileInput label="Their proof" hint="Optional. PDF, image, CSV or text, up to 25 MB." accept="application/pdf,image/png,image/jpeg,text/csv,text/plain" maxBytes={25 * 1024 * 1024} file={file} onChange={setFile} />
      </div>
      <FormButtons pending={ret.isPending} disabled={summary.trim().length === 0 || !outcome} label="Record the answer" onCancel={onDone} />
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
          toast.success("Holder added");
          onDone();
        } catch (err) {
          toast.error("Not added", messageOf(err, "The server refused."));
        }
      }}
    >
      <div className="space-y-4">
        <Field label="A registered processor" hint="Optional. Pick one and the name follows.">
          {(p) => (
            <Select {...p} value={processor} onChange={(e) => setProcessor(e.target.value)}>
              <option value="">Not in the registry</option>
              {(processors.data?.items ?? []).map((pr) => (
                <option key={pr.processor_uuid} value={pr.processor_uuid}>
                  {pr.legal_name}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field label="Who holds it" hint="In words, where the registry does not know them." required={!processor}>
          {(p) => <Input {...p} value={label} onChange={(e) => setLabel(e.target.value)} />}
        </Field>
        <div className="grid gap-2 sm:grid-cols-2">
          <Field label="Who answers: name">{(p) => <Input {...p} value={name} onChange={(e) => setName(e.target.value)} />}</Field>
          <Field label="Their email">{(p) => <Input {...p} type="email" value={contact} onChange={(e) => setContact(e.target.value)} />}</Field>
        </div>
      </div>
      <FormButtons pending={add.isPending} disabled={!processor && label.trim().length === 0} label="Add" onCancel={onDone} />
    </form>
  );
}
