/**
 * An outside holder's ticket, once the code is entered (0049, 2026-10-08).
 *
 * What is asked, the items to act on (for an erasure), everything said so far
 * - the platform's brief of what it already holds first - and two things to
 * do: write to the Privacy Office, or give the answer. The answer is its own
 * form, in order: what was done, then what is held and what was done with it,
 * then any proof. It waits for the office to accept it or send it back.
 */
"use client";

import { Download, Paperclip, Send } from "lucide-react";
import * as React from "react";

import { FileInput } from "@/components/forms";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Field,
  Table,
  Td,
  Textarea,
  Th,
  Tr,
} from "@/components/ui/primitives";
import {
  OUTCOME_COPY,
  downloadFile,
  giveAnswer,
  writeMessage,
  type HolderItem,
  type HolderMessage,
  type HolderTicketDetail,
  type ReturnOutcome,
} from "@/features/holder-ticket/api";
import { ApiError } from "@/lib/errors";
import { formatDate, formatDateTime, saveBlob } from "@/lib/format";

const OPEN = ["waiting", "sent_back", "overdue", "final_reminder"];
const ACCEPT = "application/pdf,image/png,image/jpeg,text/csv,text/plain";
const MAX = 25 * 1024 * 1024;

type Tone = "info" | "warning" | "danger" | "success" | "accent" | "neutral";
const TONE: Record<string, Tone> = {
  waiting: "info",
  sent_back: "warning",
  overdue: "danger",
  final_reminder: "danger",
  review: "accent",
  accepted: "success",
  no_answer: "danger",
};

function said(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.userMessage() : fallback;
}

export function TicketView({
  token,
  detail,
  onChange,
}: {
  token: string;
  detail: HolderTicketDetail;
  onChange: (next: HolderTicketDetail) => void;
}) {
  const t = detail.ticket;
  const open = OPEN.includes(t.state) && t.request_status !== "closed";
  const [answering, setAnswering] = React.useState(false);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <CardTitle className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-sm">{t.reference}</span>
              <Badge tone={TONE[t.state] ?? "neutral"} dot={false}>
                {t.state_label}
              </Badge>
            </CardTitle>
            <p className="mt-1 text-xs text-text-muted">For {t.label}</p>
          </div>
          {t.due_at && (
            <p className={t.overdue ? "text-sm font-medium text-danger-text" : "text-sm text-text-muted"}>
              Answer by {formatDate(t.due_at)}
            </p>
          )}
        </CardHeader>
        <CardBody className="space-y-4">
          <StateNote detail={detail} />
          <section>
            <h2 className="text-xs font-semibold tracking-wide text-text-subtle uppercase">What you are asked</h2>
            <p className="mt-1 text-sm whitespace-pre-wrap">{t.instruction ?? "See the messages below."}</p>
          </section>
          <Items items={detail.items} />
          {t.return_summary && (
            <section className="rounded-md bg-bg-inset p-3 text-sm">
              <p className="flex flex-wrap items-center gap-2 font-medium">
                Your answer{t.returned_at && ` · ${formatDateTime(t.returned_at)}`}
                {t.return_outcome && (
                  <Badge
                    tone={t.return_outcome === "done" ? "success" : t.return_outcome === "failed" ? "danger" : "warning"}
                    dot={false}
                  >
                    {OUTCOME_COPY[t.return_outcome]}
                  </Badge>
                )}
              </p>
              <p className="mt-1 whitespace-pre-wrap">{t.return_summary}</p>
            </section>
          )}
          {open &&
            (answering ? (
              <AnswerForm
                token={token}
                onCancel={() => setAnswering(false)}
                onDone={(next) => {
                  setAnswering(false);
                  onChange(next);
                }}
              />
            ) : (
              <div className="flex flex-wrap items-center gap-3 rounded-md border border-accent-border bg-accent-subtle p-3">
                <Button variant="primary" onClick={() => setAnswering(true)}>
                  <Send className="size-4" aria-hidden="true" />
                  Submit your answer
                </Button>
                <span className="text-xs text-text-muted">
                  When your work is done: what was done, what you hold, and any proof.
                </span>
              </div>
            ))}
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Messages</CardTitle>
        </CardHeader>
        <CardBody className="space-y-4">
          <Thread token={token} messages={detail.messages} />
          {t.request_status !== "closed" ? (
            <MessageBox token={token} onSent={onChange} />
          ) : (
            <p className="text-sm text-text-muted">The request is closed; nothing more can be written here.</p>
          )}
        </CardBody>
      </Card>
    </div>
  );
}

function StateNote({ detail }: { detail: HolderTicketDetail }) {
  const t = detail.ticket;
  switch (t.state) {
    case "review":
      return <Alert tone="info">Your answer is with the Privacy Office. They accept it, or send it back with what is missing.</Alert>;
    case "accepted":
      return <Alert tone="success">The Privacy Office accepted your answer. Nothing further is needed.</Alert>;
    case "withdrawn":
      return <Alert tone="info">The Privacy Office withdrew this ticket. Nothing further is needed; the reason is in the messages.</Alert>;
    case "no_answer":
      return <Alert tone="warning">The request was answered without your reply. Nothing further can be sent on this ticket.</Alert>;
    default:
      return t.sent_back_at ? (
        <Alert tone="warning" title={`Sent back to you ${formatDateTime(t.sent_back_at)}`}>
          <p>{t.sent_back_reason}</p>
        </Alert>
      ) : null;
  }
}

function whatToDo(i: HolderItem): string {
  switch (i.decision) {
    case "erase":
      return "Erase it";
    case "redact":
      return `Remove the person from it; keep the ${i.other_subjects === 1 ? "other person" : `other ${i.other_subjects} people`}`;
    case "retain":
      return i.retain_until ? `Keep it until ${formatDate(i.retain_until)}, then erase it` : "Keep it for now";
    default:
      return "Set it aside, untouched, until the Privacy Office decides";
  }
}

function Items({ items }: { items: HolderItem[] }) {
  if (items.length === 0) return null;
  return (
    <section className="space-y-2">
      <h2 className="text-xs font-semibold tracking-wide text-text-subtle uppercase">
        What to do with each item · {items.length}
      </h2>
      <Table>
        <caption className="sr-only">What to do with each item</caption>
        <thead>
          <tr>
            <Th>Item</Th>
            <Th>Collected</Th>
            <Th>What to do</Th>
          </tr>
        </thead>
        <tbody>
          {items.map((i) => (
            <Tr key={i.item_uuid}>
              <Td>
                <span className="font-mono text-xs">{i.source_asset_ref}</span>
                <span className="block text-xs text-text-muted">
                  {i.asset_type} · {i.source_name} · {i.project_name}
                </span>
              </Td>
              <Td className="whitespace-nowrap text-text-muted">{formatDate(i.collected_on)}</Td>
              <Td className="font-medium">{whatToDo(i)}</Td>
            </Tr>
          ))}
        </tbody>
      </Table>
    </section>
  );
}

const WHO: Record<HolderMessage["author_side"], string> = {
  office: "The Privacy Office",
  holder: "You",
  system: "The platform",
};

function Thread({ token, messages }: { token: string; messages: HolderMessage[] }) {
  if (messages.length === 0) return <p className="text-sm text-text-muted">Nothing yet.</p>;
  return (
    <ol className="space-y-3">
      {messages.map((m) => (
        <li
          key={m.message_uuid}
          className={
            m.author_side === "holder"
              ? "ml-8 rounded-md border border-accent-border bg-accent-subtle p-3 text-sm"
              : m.author_side === "system"
                ? "rounded-md bg-bg-inset p-3 text-sm"
                : "mr-8 rounded-md border border-border p-3 text-sm"
          }
        >
          <p className="text-xs text-text-muted">
            <span className="font-medium text-text">{m.author_side === "office" ? (m.author_name ?? WHO.office) : WHO[m.author_side]}</span>
            {" · "}
            {formatDateTime(m.created_at)}
          </p>
          <p className="mt-1 whitespace-pre-wrap">{m.body}</p>
          {m.evidence_hash && (
            <button
              type="button"
              className="mt-2 inline-flex items-center gap-1 text-xs text-accent-text underline underline-offset-2"
              onClick={async () => {
                const got = await downloadFile(token, m.message_uuid);
                saveBlob(got.blob, m.evidence_name ?? got.filename);
              }}
            >
              <Download className="size-3" aria-hidden="true" />
              {m.evidence_name ?? "Download the file"}
            </button>
          )}
        </li>
      ))}
    </ol>
  );
}

function MessageBox({ token, onSent }: { token: string; onSent: (next: HolderTicketDetail) => void }) {
  const [body, setBody] = React.useState("");
  const [file, setFile] = React.useState<File | null>(null);
  const [pending, setPending] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [note, setNote] = React.useState<string | null>(null);
  return (
    <form
      method="post"
      noValidate
      className="space-y-3"
      onSubmit={async (e) => {
        e.preventDefault();
        if (!body.trim()) return;
        setPending(true);
        setError(null);
        try {
          onSent(await writeMessage(token, body.trim(), file));
          setBody("");
          setFile(null);
          setNote("Sent. The Privacy Office has been told.");
        } catch (err) {
          setError(said(err, "Could not send your message."));
        } finally {
          setPending(false);
        }
      }}
    >
      {error && <Alert tone="danger">{error}</Alert>}
      <Field label="Write to the Privacy Office" hint="A question, or what you have found so far.">
        {(p) => <Textarea {...p} rows={3} maxLength={20_000} value={body} onChange={(e) => setBody(e.target.value)} />}
      </Field>
      <FileInput label="Attach a file" hint="Optional. PDF, image, CSV or text, up to 25 MB." accept={ACCEPT} maxBytes={MAX} file={file} onChange={setFile} />
      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" variant="secondary" loading={pending} disabled={!body.trim()}>
          <Paperclip className="size-4" aria-hidden="true" />
          Send
        </Button>
        {note && <span className="text-xs text-text-muted" role="status">{note}</span>}
      </div>
    </form>
  );
}

function AnswerForm({
  token,
  onCancel,
  onDone,
}: {
  token: string;
  onCancel: () => void;
  onDone: (next: HolderTicketDetail) => void;
}) {
  // No default: "did all of it" is never assumed (review DPDP-1).
  const [outcome, setOutcome] = React.useState<ReturnOutcome | "">("");
  const [summary, setSummary] = React.useState("");
  const [file, setFile] = React.useState<File | null>(null);
  const [pending, setPending] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  return (
    <form
      method="post"
      noValidate
      className="space-y-4 rounded-md border border-accent-border p-4"
      onSubmit={async (e) => {
        e.preventDefault();
        if (!outcome || !summary.trim()) return;
        setPending(true);
        setError(null);
        try {
          onDone(await giveAnswer(token, { summary: summary.trim(), outcome, file }));
        } catch (err) {
          setError(said(err, "Could not send your answer."));
        } finally {
          setPending(false);
        }
      }}
    >
      <h2 className="text-sm font-semibold">Submit your answer</h2>
      {error && <Alert tone="danger">{error}</Alert>}
      <fieldset className="space-y-1.5">
        <legend className="text-sm font-medium">1 · What was done?</legend>
        {(Object.keys(OUTCOME_COPY) as ReturnOutcome[]).map((o) => (
          <label key={o} className="flex items-center gap-2 text-sm">
            <input type="radio" name="outcome" className="size-4" checked={outcome === o} onChange={() => setOutcome(o)} />
            {OUTCOME_COPY[o]}
          </label>
        ))}
        <p className="text-xs text-text-muted">Only “did all of it” counts as done. If you could not do some or all of it, say why below.</p>
      </fieldset>
      <Field label="2 · What you hold, and what you did" required>
        {(p) => <Textarea {...p} rows={4} maxLength={20_000} value={summary} onChange={(e) => setSummary(e.target.value)} />}
      </Field>
      <FileInput label="3 · Proof" hint="Optional. PDF, image, CSV or text, up to 25 MB." accept={ACCEPT} maxBytes={MAX} file={file} onChange={setFile} />
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" loading={pending} disabled={!outcome || !summary.trim()}>
          Send your answer
        </Button>
      </div>
    </form>
  );
}
