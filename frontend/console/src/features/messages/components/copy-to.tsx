/**
 * Who a message is copied to by email (2026-10-08).
 *
 * Up to five addresses - a team mailbox that follows the work up, an
 * approvals inbox - one per line. Only on a message the server lets be copied;
 * one that carries a code or a link, or a person's own record, says why it
 * never is. A text message is never copied, whatever is set here.
 */
"use client";

import { Lock, Save } from "lucide-react";
import * as React from "react";

import { Button, Field, Textarea } from "@/components/ui/primitives";
import { useSaveMessageCopies } from "@/features/messages/mutations";
import { useToast } from "@/providers";
import type { MessageTemplate } from "@/types";

function userMessage(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}

export function CopyTo({ message }: { message: MessageTemplate }) {
  const toast = useToast();
  const save = useSaveMessageCopies();
  const current = (message.copies ?? []).map((c) => c.email).join("\n");
  const [text, setText] = React.useState(current);
  const [seen, setSeen] = React.useState(current);
  if (seen !== current) {
    setSeen(current);
    setText(current);
  }

  if (!message.copyable) {
    return (
      <p className="flex items-start gap-2 text-xs text-text-muted">
        <Lock className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
        Never copied: it carries a code or a link, or a person&apos;s own record, and a copy would
        hand it to somebody else.
      </p>
    );
  }

  const addresses = text
    .split(/[\n,;]+/)
    .map((a) => a.trim())
    .filter(Boolean);

  async function submit() {
    try {
      await save.mutateAsync({ key: message.key, addresses });
      toast.success(
        addresses.length ? `Copied to ${addresses.length} ${addresses.length === 1 ? "address" : "addresses"}` : "No longer copied",
      );
    } catch (err) {
      toast.error("Not saved", userMessage(err, "The server refused."));
    }
  }

  return (
    <div className="space-y-2 rounded-md border border-border p-3">
      <Field
        label="Copy to"
        hint="Email only. Up to 5 addresses, one per line - a team mailbox, an approvals inbox. Each copy gets the same email, in Cc."
      >
        {(p) => (
          <Textarea
            {...p}
            rows={2}
            value={text}
            placeholder="approvals@example.org"
            onChange={(e) => setText(e.target.value)}
          />
        )}
      </Field>
      {(message.deployment_copies ?? 0) > 0 && (
        <p className="text-xs text-text-muted">
          Also copied to {message.deployment_copies}{" "}
          {message.deployment_copies === 1 ? "address" : "addresses"} set for every copyable email
          in the platform&apos;s settings (EMAIL_CC_ADDRESSES). Ask whoever runs the platform to
          change {message.deployment_copies === 1 ? "it" : "them"}.
        </p>
      )}
      <Button
        variant="secondary"
        size="sm"
        disabled={text === current || addresses.length > 5}
        loading={save.isPending}
        onClick={submit}
      >
        <Save className="size-4" />
        Save copies
      </Button>
    </div>
  );
}
