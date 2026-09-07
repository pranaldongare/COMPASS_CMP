/**
 * The second half of the public form: the code, against the reference.
 *
 * The message for a wrong code and for a code that was never issued is the
 * same on purpose. The server would not say which, and this form does not
 * try to guess.
 */
"use client";

import * as React from "react";

import { FormError, useApiForm } from "@/components/forms";
import { Button, Field, Input } from "@/components/ui/primitives";
import { verifyPublicRequest } from "@/features/rights/api";
import {
  verifySchema,
  type VerifyForm as VerifyFormValues,
  type VerifyValues,
} from "@/features/rights/schemas";
import type { PublicVerifyResult } from "@/types";

export function VerifyForm({
  reference,
  onDone,
}: {
  reference?: string;
  onDone: (result: PublicVerifyResult) => void;
}) {
  const [pending, setPending] = React.useState(false);
  const form = useApiForm<VerifyValues, VerifyFormValues>(verifySchema, {
    reference: reference ?? "",
    code: "",
  });

  const submit = form.submit(async (values) => {
    setPending(true);
    try {
      onDone(await verifyPublicRequest(values));
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
      <Button type="submit" variant="primary" loading={pending}>
        Confirm it is me
      </Button>
    </form>
  );
}
