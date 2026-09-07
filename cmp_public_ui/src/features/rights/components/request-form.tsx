/**
 * Asking for something: the data principal's form, and the public one.
 *
 * The same four rights in the same words, with the section of the Act beside
 * each so she can look it up. One thing the form says out loud because people
 * get it wrong: erasure is not withdrawal. Withdrawing stops future processing
 * and is one click on her consent record; erasure is a request the Privacy
 * Office fulfils, and the DPO will confirm which she means before anything is
 * deleted.
 *
 * The public variant adds a contact. Whatever she types, the verification code
 * goes to the channel already on file - so the form says that too, because a
 * person who typed a new address and waited for a code that never came would
 * otherwise conclude the form was broken.
 */
"use client";

import * as React from "react";

import { FormError, useApiForm } from "@/components/forms";
import { DialogFooter } from "@/components/ui/dialog";
import { Alert, Button, Field, Input, Select, Textarea } from "@/components/ui/primitives";
import { submitPublicRequest } from "@/features/rights/api";
import { REQUEST_TYPE_COPY } from "@/features/rights/components/copy";
import { useMakeRequest } from "@/features/rights/mutations";
import {
  myRequestSchema,
  publicRequestSchema,
  type MyRequestForm as MyRequestFormValues,
  type MyRequestValues,
  type PublicRequestForm as PublicRequestFormValues,
  type PublicRequestValues,
} from "@/features/rights/schemas";
import { useToast } from "@/providers";
import type { MyRequest, PublicRequestReceipt, RightsRequestType } from "@/types";
import { RIGHTS_REQUEST_TYPES } from "@/types";

function TypeSelect({
  value,
  onChange,
  inputProps,
}: {
  value: RightsRequestType;
  onChange: (next: RightsRequestType) => void;
  inputProps: Record<string, unknown>;
}) {
  return (
    <Select
      {...inputProps}
      value={value}
      onChange={(e) => onChange(e.target.value as RightsRequestType)}
    >
      {RIGHTS_REQUEST_TYPES.map((t) => (
        <option key={t} value={t}>
          {REQUEST_TYPE_COPY[t].label} ({REQUEST_TYPE_COPY[t].section})
        </option>
      ))}
    </Select>
  );
}

function TypeBlurb({ type }: { type: RightsRequestType }) {
  return (
    <Alert tone={type === "erasure" ? "warning" : "info"}>
      <p className="text-sm">{REQUEST_TYPE_COPY[type].blurb}</p>
    </Alert>
  );
}

/** Signed in: the session is the verification, so the clock starts on submit. */
export function MyRequestForm({
  onDone,
  initialType = "access",
}: {
  onDone: (created: MyRequest) => void;
  initialType?: RightsRequestType;
}) {
  const toast = useToast();
  const make = useMakeRequest();
  const form = useApiForm<MyRequestValues, MyRequestFormValues>(myRequestSchema, {
    request_type: initialType,
    request_text: "",
    about_dpo: false,
  });
  const type = form.watch("request_type") as RightsRequestType;

  const submit = form.submit(async (values) => {
    const created = await make.mutateAsync(values);
    toast.success(
      `Recorded as ${created.reference}`,
      `You will hear from us by ${new Date(created.due_at).toLocaleDateString()}.`,
    );
    onDone(created);
  });

  return (
    <form method="post" onSubmit={submit} noValidate>
      <FormError message={form.formError} />
      <div className="space-y-4">
        <Field label="What are you asking for" required error={form.formState.errors.request_type?.message}>
          {(p) => (
            <TypeSelect
              inputProps={p}
              value={type}
              onChange={(next) => form.setValue("request_type", next, { shouldValidate: true })}
            />
          )}
        </Field>
        <TypeBlurb type={type} />

        <Field
          label="Your request"
          hint="In your own words. Which project, which data, what you want done."
          required
          error={form.formState.errors.request_text?.message}
        >
          {(p) => <Textarea {...p} rows={5} maxLength={20_000} {...form.register("request_text")} />}
        </Field>

        {type === "grievance" && (
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              className="mt-0.5 size-4 rounded border-border-strong accent-[var(--accent)]"
              {...form.register("about_dpo")}
            />
            <span>
              This complaint is about the Data Protection Officer&apos;s own decisions.
              <span className="block text-xs text-text-subtle">
                It will be reviewed by somebody independent of the DPO.
              </span>
            </span>
          </label>
        )}
      </div>

      <DialogFooter>
        <Button type="submit" variant="primary" loading={make.isPending}>
          Send the request
        </Button>
      </DialogFooter>
    </form>
  );
}

/** From the notice link, with no account. Neutral whatever happens. */
export function PublicRequestForm({
  onDone,
}: {
  onDone: (receipt: PublicRequestReceipt) => void;
}) {
  const [pending, setPending] = React.useState(false);
  const form = useApiForm<PublicRequestValues, PublicRequestFormValues>(publicRequestSchema, {
    request_type: "access",
    contact: "",
    name: "",
    request_text: "",
  });
  const type = form.watch("request_type") as RightsRequestType;

  const submit = form.submit(async (values) => {
    setPending(true);
    try {
      onDone(await submitPublicRequest({ ...values, name: values.name || null }));
    } finally {
      setPending(false);
    }
  });

  return (
    <form method="post" onSubmit={submit} noValidate className="space-y-4">
      <FormError message={form.formError} />

      <Field label="What are you asking for" required error={form.formState.errors.request_type?.message}>
        {(p) => (
          <TypeSelect
            inputProps={p}
            value={type}
            onChange={(next) => form.setValue("request_type", next, { shouldValidate: true })}
          />
        )}
      </Field>
      <TypeBlurb type={type} />

      <Field
        label="The email or mobile you registered with"
        hint="We send a verification code to the contact we already hold for you - never to a new one typed here."
        required
        error={form.formState.errors.contact?.message}
      >
        {(p) => <Input {...p} autoComplete="email" {...form.register("contact")} />}
      </Field>

      <Field label="Your name" error={form.formState.errors.name?.message}>
        {(p) => <Input {...p} autoComplete="name" {...form.register("name")} />}
      </Field>

      <Field
        label="Your request"
        hint="In your own words. Which project, which data, what you want done."
        required
        error={form.formState.errors.request_text?.message}
      >
        {(p) => <Textarea {...p} rows={5} maxLength={20_000} {...form.register("request_text")} />}
      </Field>

      <Button type="submit" variant="primary" loading={pending}>
        Send the request
      </Button>
    </form>
  );
}
