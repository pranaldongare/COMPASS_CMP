/**
 * One message, one channel at a time: the words, the variables, a preview.
 *
 * The editor is deliberately plain. The words are plain text on both channels,
 * placeholders are `{name}` and nothing else, and the server refuses a save
 * that names a variable the message does not provide - so the chips under the
 * body are the whole vocabulary, and clicking one inserts it where the cursor
 * is. Preview renders with sample values so the editor reads what a person
 * would read; save records who changed what, in the audit trail.
 *
 * Reset is two clicks on purpose. It throws the office's words away, and the
 * default that returns may be a long way from what was there.
 */
"use client";

import { Eye, RotateCcw, Save } from "lucide-react";
import * as React from "react";

import { Alert, Badge, Button, Field, Input, Textarea } from "@/components/ui/primitives";
import {
  usePreviewMessage,
  useResetMessage,
  useSaveMessage,
} from "@/features/messages/mutations";
import { formatDate } from "@/lib/format";
import { useToast } from "@/providers";
import type { MessageChannel, MessageChannelTemplate, MessageTemplate } from "@/types";

const CHANNEL_LABEL: Record<MessageChannel, string> = { email: "Email", sms: "SMS" };

function userMessage(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}

export function MessageEditor({ message }: { message: MessageTemplate }) {
  const [channel, setChannel] = React.useState<MessageChannel>(message.channels[0].channel);
  const current =
    message.channels.find((c) => c.channel === channel) ?? message.channels[0];

  return (
    <div className="space-y-4">
      {message.channels.length > 1 && (
        <div role="tablist" aria-label="Channel" className="flex gap-1">
          {message.channels.map((c) => (
            <Button
              key={c.channel}
              role="tab"
              aria-selected={c.channel === channel}
              variant={c.channel === channel ? "primary" : "subtle"}
              size="sm"
              onClick={() => setChannel(c.channel)}
            >
              {CHANNEL_LABEL[c.channel]}
              {c.customised && <span className="sr-only"> (customised)</span>}
            </Button>
          ))}
        </div>
      )}
      {/* Keyed so a channel switch, or fresh words from the server, start a
          fresh draft rather than carrying one channel's text into another. */}
      <ChannelEditor
        key={`${message.key}:${current.channel}:${current.updated_at ?? "default"}`}
        message={message}
        template={current}
      />
    </div>
  );
}

function ChannelEditor({
  message,
  template,
}: {
  message: MessageTemplate;
  template: MessageChannelTemplate;
}) {
  const toast = useToast();
  const save = useSaveMessage();
  const reset = useResetMessage();
  const preview = usePreviewMessage();
  const isEmail = template.channel === "email";

  const [subject, setSubject] = React.useState(template.subject ?? "");
  const [body, setBody] = React.useState(template.body);
  const [error, setError] = React.useState<string | null>(null);
  const [confirmingReset, setConfirmingReset] = React.useState(false);
  const bodyRef = React.useRef<HTMLTextAreaElement>(null);

  const dirty = body !== template.body || (isEmail && subject !== (template.subject ?? ""));
  const input = { subject: isEmail ? subject : null, body };

  function insertVariable(name: string) {
    const el = bodyRef.current;
    const token = `{${name}}`;
    if (!el) {
      setBody((b) => b + token);
      return;
    }
    const start = el.selectionStart ?? body.length;
    const end = el.selectionEnd ?? body.length;
    const next = body.slice(0, start) + token + body.slice(end);
    setBody(next);
    requestAnimationFrame(() => {
      el.focus();
      el.setSelectionRange(start + token.length, start + token.length);
    });
  }

  async function onSave() {
    setError(null);
    try {
      await save.mutateAsync({ key: message.key, channel: template.channel, input });
      toast.success(
        "Words saved",
        `${message.title} (${CHANNEL_LABEL[template.channel]}) now sends what you wrote.`,
      );
    } catch (err) {
      setError(userMessage(err, "Could not save these words."));
    }
  }

  async function onPreview() {
    setError(null);
    try {
      await preview.mutateAsync({ key: message.key, channel: template.channel, input });
    } catch (err) {
      setError(userMessage(err, "Could not render a preview."));
    }
  }

  async function onReset() {
    setError(null);
    try {
      await reset.mutateAsync({ key: message.key, channel: template.channel });
      setConfirmingReset(false);
      toast.info(
        "Back to the default",
        `${message.title} (${CHANNEL_LABEL[template.channel]}) sends the default words again.`,
      );
    } catch (err) {
      setError(userMessage(err, "Could not reset."));
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 text-xs text-text-muted">
        {template.customised ? (
          <>
            <Badge tone="info" dot={false}>
              Customised
            </Badge>
            <span>
              by {template.updated_by_name ?? "somebody"}
              {template.updated_at ? ` on ${formatDate(template.updated_at)}` : ""}
            </span>
          </>
        ) : (
          <Badge dot={false}>Default words</Badge>
        )}
      </div>

      {error && <Alert tone="danger">{error}</Alert>}

      {isEmail && (
        <Field label="Subject" required hint="One line. Placeholders work here too.">
          {(p) => (
            <Input
              {...p}
              value={subject}
              maxLength={200}
              onChange={(e) => setSubject(e.target.value)}
            />
          )}
        </Field>
      )}

      <Field
        label={isEmail ? "Body" : "Message"}
        required
        hint={
          isEmail
            ? "Plain text. Blank lines separate paragraphs."
            : "Plain text, at most 480 characters (three SMS segments)."
        }
      >
        {(p) => (
          <Textarea
            {...p}
            ref={bodyRef}
            rows={isEmail ? 12 : 4}
            maxLength={isEmail ? 6000 : 480}
            value={body}
            onChange={(e) => setBody(e.target.value)}
            className="font-mono text-sm"
          />
        )}
      </Field>

      <div>
        <p className="mb-1 text-xs font-medium text-text-muted">
          Variables this message can use (click to insert)
        </p>
        <ul className="flex flex-wrap gap-1.5">
          {message.variables.map((v) => (
            <li key={v.name}>
              <button
                type="button"
                onClick={() => insertVariable(v.name)}
                title={`${v.description} Example: ${v.sample}`}
                className="bg-surface-subtle hover:bg-surface-muted rounded-md border border-border px-2 py-0.5 font-mono text-xs"
              >
                {`{${v.name}}`}
              </button>
            </li>
          ))}
        </ul>
      </div>

      {preview.data && preview.data.channel === template.channel && (
        <div className="bg-surface-subtle rounded-lg border border-border p-3">
          <p className="mb-2 text-xs font-medium text-text-muted">
            Preview, with sample values
          </p>
          {preview.data.subject && (
            <p className="mb-2 text-sm font-semibold">{preview.data.subject}</p>
          )}
          <pre className="font-sans text-sm whitespace-pre-wrap">{preview.data.body}</pre>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant="primary"
          size="sm"
          loading={save.isPending}
          disabled={!dirty}
          onClick={onSave}
        >
          <Save className="size-4" aria-hidden="true" />
          Save
        </Button>
        <Button variant="subtle" size="sm" loading={preview.isPending} onClick={onPreview}>
          <Eye className="size-4" aria-hidden="true" />
          Preview
        </Button>
        {template.customised &&
          (confirmingReset ? (
            <>
              <Button
                variant="danger"
                size="sm"
                loading={reset.isPending}
                onClick={onReset}
              >
                Yes, use the default words
              </Button>
              <Button variant="subtle" size="sm" onClick={() => setConfirmingReset(false)}>
                Keep mine
              </Button>
            </>
          ) : (
            <Button variant="subtle" size="sm" onClick={() => setConfirmingReset(true)}>
              <RotateCcw className="size-4" aria-hidden="true" />
              Reset to default
            </Button>
          ))}
      </div>
    </div>
  );
}
