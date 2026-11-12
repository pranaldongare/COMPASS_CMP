/**
 * The second half of the public form: the code, against the reference.
 *
 * The message for a wrong code and for a code that was never issued is the
 * same on purpose. The server would not say which, and this form does not
 * try to guess. Nor does it say when a code is spent: after too many wrong
 * tries the server discards it and answers as for a wrong one, so after any
 * refusal the form says how to get a new one, in words true whether or not
 * a code was ever sent.
 */
"use client";

import * as React from "react";

import { FormError, useApiForm } from "@/components/forms";
import { Button, Field, Input } from "@/components/ui/primitives";
import { verifyPublicRequest } from "@/features/rights/api";
import { ApiError } from "@/lib/errors";
import {
  verifySchema,
  type VerifyForm as VerifyFormValues,
  type VerifyValues,
} from "@/features/rights/schemas";
import type { PublicVerifyResult } from "@/types";

/** How to get a new code, said to everybody alike: it names no contact and
 *  does not say whether one was ever sent. A new code goes where the first
 *  did, to the contact we hold - for an account, its email when it has one,
 *  whichever contact was typed - so it says so, as the field's hint does. */
export const NEW_CODE =
  "A code stops working after ten minutes, or after too many wrong tries. To get a new one, make " +
  "your request again: if we hold records for the contact you gave, a new code is sent to the " +
  "contact we hold for you.";

export function VerifyForm({
  reference,
  onDone,
  onNewRequest,
}: {
  reference?: string;
  onDone: (result: PublicVerifyResult) => void;
  /** Back to the request form, where a new request sends a new code. */
  onNewRequest?: () => void;
}) {
  const [pending, setPending] = React.useState(false);
  const [refused, setRefused] = React.useState(false);
  const form = useApiForm<VerifyValues, VerifyFormValues>(verifySchema, {
    reference: reference ?? "",
    code: "",
  });

  const submit = form.submit(async (values) => {
    setPending(true);
    setRefused(false);
    try {
      onDone(await verifyPublicRequest(values));
    } catch (error) {
      if (error instanceof ApiError && error.code === "otp_invalid") setRefused(true);
      throw error;
    } finally {
      setPending(false);
    }
  });

  return (
    <form method="post" onSubmit={submit} noValidate className="space-y-4">
      <FormError message={form.formError} />
      <Field
        label="Your reference"
        hint="On the confirmation you were shown, like RR-2026-000123."
        required
        error={form.formState.errors.reference?.message}
      >
        {(p) => <Input {...p} autoComplete="off" {...form.register("reference")} />}
      </Field>
      <Field
        label="The code we sent"
        hint="Six digits, sent to the contact we hold for you. It expires in ten minutes."
        required
        error={form.formState.errors.code?.message}
      >
        {(p) => (
          <Input
            {...p}
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={10}
            {...form.register("code")}
          />
        )}
      </Field>
      {refused && (
        <div className="space-y-1">
          <p className="text-xs text-text-muted">{NEW_CODE}</p>
          {onNewRequest && (
            <button
              type="button"
              className="text-xs text-text-subtle underline underline-offset-2"
              onClick={onNewRequest}
            >
              Make the request again
            </button>
          )}
        </div>
      )}
      <Button type="submit" variant="primary" loading={pending}>
        Verify identity
      </Button>
    </form>
  );
}
