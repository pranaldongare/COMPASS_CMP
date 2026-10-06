/**
 * A ticket's thread, and the box that writes to it.
 *
 * The same pieces wherever a ticket has two sides: the Privacy Office and a
 * rights request's holder, the office and a breach ticket's holder (S3-08).
 * The messages are rows from the server; what differs is which side is
 * "you". Moved here from the rights feature when breach tickets became its
 * second user.
 */
"use client";

import { Building2, FileText, MessageSquare, Send, ShieldCheck } from "lucide-react";
import * as React from "react";

import { FileInput } from "@/components/forms";
import { useDialogSaved } from "@/components/ui/dialog";
import { Alert, Badge, Button, Textarea } from "@/components/ui/primitives";
import { formatDateTime } from "@/lib/format";
import type { TicketMessage } from "@/types";

const KIND_LABEL: Record<TicketMessage["kind"], string> = {
  brief: "Brief from the platform",
  instruction: "Instruction",
  message: "Message",
  return: "Returned",
  escalation: "Escalation",
  status: "Update",
};

/** The thread, with "you" on the right. */
export function Thread({
  messages,
  you,
  evidenceHref,
}: {
  messages: TicketMessage[];
  you: "office" | "holder";
  evidenceHref?: (m: TicketMessage) => string | null;
}) {
  const end = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    end.current?.scrollIntoView?.({ block: "nearest" });
  }, [messages.length]);
  return (
    <ol className="max-h-[28rem] space-y-3 overflow-y-auto pr-1" aria-label="Messages">
      {messages.map((m) => {
        const mine = m.author_side === you;
        const system = m.author_side === "system";
        // A platform line may be signed: a colleague's ticket opens with the
        // note of the holder who added them (S3-09).
        const who = system
          ? (m.author_name ?? "The platform")
          : (m.author_name ?? (m.author_side === "office" ? "The Privacy Office" : "The team"));
        const Icon = system ? ShieldCheck : m.author_side === "office" ? FileText : Building2;
        const href = evidenceHref?.(m) ?? null;
        return (
          <li key={m.message_uuid} className={mine ? "flex justify-end" : "flex justify-start"}>
            <div
              className={[
                "max-w-[85%] rounded-lg px-3 py-2 text-sm",
                system
                  ? "border border-border bg-bg-inset"
                  : mine
                    ? "bg-accent-subtle text-text"
                    : "border border-border bg-surface",
              ].join(" ")}
            >
              <p className="mb-1 flex flex-wrap items-center gap-x-2 text-xs text-text-muted">
                <Icon className="size-3.5" aria-hidden="true" />
                <span className="font-medium text-text">{who}</span>
                <span>{KIND_LABEL[m.kind]}</span>
                <span>· {formatDateTime(m.created_at)}</span>
              </p>
              <p className="whitespace-pre-wrap">{m.body}</p>
              {m.evidence_hash && (
                <p className="mt-1 text-xs text-text-muted">
                  {m.evidence_name ? `File: ${m.evidence_name}` : "File attached"}
                  {href && (
                    <>
                      {" · "}
                      <a className="text-accent-text underline underline-offset-2" href={href}>
                        download
                      </a>
                    </>
                  )}
                </p>
              )}
            </div>
          </li>
        );
      })}
      <div ref={end} />
    </ol>
  );
}

/**
 * The composer. One box for everything a side says on a ticket: a message,
 * a message with a file, or - for the team - the final return. The caller
 * decides what a submission means; the box only collects it.
 */
export function ReplyBox({
  onSend,
  pending,
  placeholder,
  disabledReason,
  allowFile = true,
  finalOption,
}: {
  onSend: (body: string, file: File | null, final: boolean) => Promise<void>;
  pending: boolean;
  placeholder: string;
  disabledReason?: string | null;
  allowFile?: boolean;
  /** Offered where a submission may close the ticket: label and explanation. */
  finalOption?: { label: string; hint: string } | null;
}) {
  const [body, setBody] = React.useState("");
  const [file, setFile] = React.useState<File | null>(null);
  const [final, setFinal] = React.useState(false);
  // Sent is saved: closing the dialog around it no longer asks.
  const saved = useDialogSaved();
  const [error, setError] = React.useState<string | null>(null);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await onSend(body.trim(), file, final);
      setBody("");
      setFile(null);
      setFinal(false);
      saved();
    } catch (err) {
      setError(
        err && typeof err === "object" && "userMessage" in err
          ? (err as { userMessage: () => string }).userMessage()
          : "Could not send.",
      );
    }
  }
  if (disabledReason) {
    return <p className="text-xs text-text-muted">{disabledReason}</p>;
  }
  return (
    <form method="post" onSubmit={submit} noValidate className="space-y-3">
      {error && <Alert tone="danger">{error}</Alert>}
      <Textarea
        rows={4}
        maxLength={20_000}
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder={placeholder}
        aria-label="Message"
      />
      {allowFile && (
        <FileInput
          label="Attach a file"
          hint="Optional. PDF, image, CSV or text, up to 25 MB. Kept with the message."
          accept="application/pdf,image/png,image/jpeg,text/csv,text/plain"
          maxBytes={25 * 1024 * 1024}
          file={file}
          onChange={setFile}
        />
      )}
      {finalOption && (
        <label className="flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            className="mt-0.5 size-4"
            checked={final}
            onChange={(e) => setFinal(e.target.checked)}
          />
          <span>
            {finalOption.label}
            <span className="block text-xs text-text-subtle">{finalOption.hint}</span>
          </span>
        </label>
      )}
      <div className="flex justify-end">
        <Button
          type="submit"
          variant="primary"
          size="sm"
          loading={pending}
          disabled={!body.trim()}
          data-testid="composer-send"
        >
          <Send className="size-4" aria-hidden="true" />
          {final ? "Return the ticket" : "Send"}
        </Button>
      </div>
    </form>
  );
}

export function UnreadBadge({ count }: { count: number }) {
  if (!count) return null;
  return (
    <Badge tone="warning" dot={false}>
      <MessageSquare className="mr-1 size-3" aria-hidden="true" />
      {count} new
    </Badge>
  );
}
