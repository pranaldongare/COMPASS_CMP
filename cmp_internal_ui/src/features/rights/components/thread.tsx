/**
 * A ticket's thread and the brief it opened with.
 *
 * The same two pieces on both sides. The Privacy Office sees them on the
 * request, the team on its ticket; the messages are the same rows, and what
 * differs is which side is "you". The brief is what the platform wrote when
 * the ticket was issued - the person, and every record naming this holder -
 * and it is shown as data, not just as the prose that went in the mail.
 */
"use client";

import { Building2, FileText, MessageSquare, Send, ShieldCheck, UserRound } from "lucide-react";
import * as React from "react";

import { Alert, Badge, Button, Textarea } from "@/components/ui/primitives";
import { formatDate, formatDateTime } from "@/lib/format";
import type { HolderBrief, TicketMessage } from "@/types";

const KIND_LABEL: Record<TicketMessage["kind"], string> = {
  brief: "Brief from the platform",
  instruction: "Instruction",
  message: "Message",
  return: "Returned",
  escalation: "Escalation",
};

/** The brief, as the reader would want to check it: lists, not prose. */
export function BriefPanel({ brief }: { brief: HolderBrief }) {
  const s = brief.subject;
  const nothing = brief.consents.length + brief.exports.length + brief.assets.length === 0;
  return (
    <div className="space-y-3 rounded-md border border-border bg-bg-inset p-3 text-sm">
      <p className="flex items-center gap-2 font-medium">
        <UserRound className="size-4 text-text-subtle" aria-hidden="true" />
        {s.full_name ?? "The person named"}
        <span className="font-normal text-text-muted">
          {[s.email, s.mobile].filter(Boolean).join(" · ")}
        </span>
      </p>
      {nothing ? (
        <p className="text-text-muted">
          The platform holds no consent, export or asset record naming this holder as holding
          anything of theirs. The question is what, if anything, they hold.
        </p>
      ) : (
        <>
          <p className="text-xs font-medium uppercase tracking-wider text-text-subtle">
            What the platform already records this holder as holding
          </p>
          {brief.consents.length > 0 && (
            <ul className="space-y-1">
              {brief.consents.map((c) => (
                <li key={c.consent_uuid} className="flex flex-wrap items-baseline gap-x-2">
                  <Badge tone={c.withdrawal ? "warning" : "success"} dot={false}>
                    {c.withdrawal ? "withdrawal" : "consent"}
                  </Badge>
                  <span>
                    {c.at ? formatDate(c.at) : "-"} · {c.project} at {c.site}
                  </span>
                  <span className="text-text-muted">
                    {c.granted.length ? c.granted.join(", ") : "no purpose granted"}
                  </span>
                </li>
              ))}
            </ul>
          )}
          {brief.exports.length > 0 && (
            <ul className="space-y-1">
              {brief.exports.map((e) => (
                <li key={e.export_uuid} className="flex flex-wrap items-baseline gap-x-2">
                  <Badge tone="info" dot={false}>export</Badge>
                  <span>
                    {e.at ? formatDate(e.at) : "-"} · {e.project} · {e.type}
                  </span>
                </li>
              ))}
            </ul>
          )}
          {brief.assets.length > 0 && (
            <ul className="space-y-1">
              {brief.assets.map((a) => (
                <li key={a.asset_uuid} className="flex flex-wrap items-baseline gap-x-2">
                  <Badge tone="neutral" dot={false}>asset</Badge>
                  <span className="font-mono text-xs">{a.ref ?? a.asset_uuid}</span>
                  <span className="text-text-muted">
                    {a.source}
                    {a.collected_on && ` · collected ${a.collected_on}`}
                    {a.role && ` · ${a.role}`}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}

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
    end.current?.scrollIntoView({ block: "nearest" });
  }, [messages.length]);
  return (
    <ol className="max-h-[28rem] space-y-3 overflow-y-auto pr-1" aria-label="Messages">
      {messages.map((m) => {
        const mine = m.author_side === you;
        const system = m.author_side === "system";
        const who = system
          ? "The platform"
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
                  Evidence attached
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

/** A reply box. The caller sends. */
export function ReplyBox({
  onSend,
  pending,
  placeholder,
  disabledReason,
}: {
  onSend: (body: string) => Promise<void>;
  pending: boolean;
  placeholder: string;
  disabledReason?: string | null;
}) {
  const [body, setBody] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await onSend(body.trim());
      setBody("");
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
    <form method="post" onSubmit={submit} noValidate className="space-y-2">
      {error && <Alert tone="danger">{error}</Alert>}
      <Textarea
        rows={3}
        maxLength={20_000}
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder={placeholder}
        aria-label="Message"
      />
      <div className="flex justify-end">
        <Button type="submit" variant="primary" size="sm" loading={pending} disabled={!body.trim()}>
          <Send className="size-4" aria-hidden="true" />
          Send
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
