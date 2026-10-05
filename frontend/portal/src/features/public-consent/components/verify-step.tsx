/**
 * Step two: confirm the contact.
 *
 * The code proves the address belongs to the person filling in the form, which
 * is what makes the consent attributable. Without it, anybody could record
 * consent in somebody else's name.
 */
"use client";

import * as React from "react";

import {
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Field,
  Input,
} from "@/components/ui/primitives";
import { requestOtp, verifyOtp } from "@/features/public-consent/api";
import { ApiError } from "@/lib/errors";

export function VerifyStep({
  token,
  contact,
  onDone,
  onError,
  onChangeContact,
}: {
  token: string;
  /** The one contact she chose, and the only one this flow asks about. */
  contact: string;
  onDone: () => void;
  onError: (message: string | null) => void;
  /** Back to the first step, the link still open. */
  onChangeContact: () => void;
}) {
  const [code, setCode] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [resending, setResending] = React.useState(false);
  const [resent, setResent] = React.useState(false);
  const isEmail = contact.includes("@");

  /**
   * Another code to the same contact. The server's answer is the same
   * sentence whoever she is, and its quota - five an hour - is per contact;
   * a 429 is shown in its own words, which name no account.
   */
  async function resend() {
    setResending(true);
    setResent(false);
    onError(null);
    try {
      await requestOtp(token, contact);
      setCode("");
      setResent(true);
    } catch (err) {
      onError(err instanceof ApiError ? err.userMessage() : "Could not send a new code.");
    } finally {
      setResending(false);
    }
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    onError(null);
    try {
      const result = await verifyOtp(token, { contact, code });
      if (result.complete) {
        await onDone();
        return;
      }
      // An account whose other medium has never answered a code. It cannot be
      // finished from here - this flow knows one contact - and the honest
      // answer is where it can be, rather than a second code box appearing on
      // a consent form.
      setCode("");
      onError(
        "Your account still has a contact to confirm. Sign in to the portal to finish " +
          "that, then open this link again.",
      );
    } catch (err) {
      onError(err instanceof ApiError ? err.userMessage() : "Verification failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{isEmail ? "Confirm your email" : "Confirm your mobile"}</CardTitle>
        <p className="mt-1 text-sm text-text-muted">
          We have sent a six-digit code to <strong>{contact}</strong>. It expires in ten
          minutes.
        </p>
      </CardHeader>
      <CardBody>
        <form method="post" onSubmit={submit} className="space-y-4" noValidate>
          <Field label="Six-digit code" required>
            {(props) => (
              <Input
                {...props}
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                inputMode="numeric"
                autoComplete="one-time-code"
                placeholder="000000"
                className="text-center font-mono text-lg tracking-[0.4em]"
                autoFocus
              />
            )}
          </Field>
          <Button
            type="submit"
            variant="primary"
            className="w-full"
            loading={busy}
            disabled={code.length !== 6}
          >
            Verify and continue
          </Button>
        </form>
        {resent && (
          <p className="mt-3 text-sm text-text-muted" role="status">
            A new code is on its way. The earlier one no longer works.
          </p>
        )}
        <div className="mt-4 flex flex-wrap justify-between gap-2 border-t border-border-subtle pt-4">
          <Button type="button" variant="ghost" loading={resending} onClick={resend}>
            Send a new code
          </Button>
          <Button type="button" variant="ghost" onClick={onChangeContact}>
            Use a different contact
          </Button>
        </div>
      </CardBody>
    </Card>
  );
}
