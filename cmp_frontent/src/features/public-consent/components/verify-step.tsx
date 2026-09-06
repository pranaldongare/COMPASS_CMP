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
import { verifyOtp } from "@/features/public-consent/api";
import { ApiError } from "@/lib/errors";

export function VerifyStep({
  token,
  contacts,
  onDone,
  onError,
}: {
  token: string;
  /** Every contact given at registration, mobile first. Each answers in turn. */
  contacts: string[];
  onDone: () => void;
  onError: (message: string | null) => void;
}) {
  const [index, setIndex] = React.useState(0);
  const [code, setCode] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const contact = contacts[index] ?? contacts[0] ?? "";
  const isEmail = contact.includes("@");
  const last = index >= contacts.length - 1;

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    onError(null);
    try {
      const result = await verifyOtp(token, { contact, code });
      if (result.complete) {
        await onDone();
      } else {
        setCode("");
        setIndex((i) => i + 1);
      }
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
          We have sent a six-digit code to <strong>{contact}</strong>. It expires in
          ten minutes.
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
            {last ? "Confirm and read the notice" : "Confirm and continue"}
          </Button>
        </form>
      </CardBody>
    </Card>
  );
}
