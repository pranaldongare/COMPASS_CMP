/**
 * Asking for something: the data principal's form, and the public one.
 *
 * The same three requests in the same words - access, erasure, a grievance
 * (DPO, 2026-10-07) - with the section of the Act beside each so she can look
 * it up. Each is about everything held about her, never one project or one
 * consent. One thing the form says out loud because people
 * get it wrong: erasure is not withdrawal. Withdrawing stops future processing
 * and is one click on her consent record; erasure is a request the Privacy
 * Office fulfils, and the DPO will confirm which she means before anything is
 * deleted.
 *
 * The public variant adds a contact. Whatever she types, the verification code
 * goes to the channel already on file - so the form says that too, because a
 * person who typed a new address and waited for a code that never came would
 * otherwise conclude the form was broken.
 *
 * Signed in, she can send documents with it (2026-10-07). They go once the
 * request is recorded, one by one; one refused does not undo the request, and
 * the toast says which and why. The public form takes none: nobody is known
 * until the code is confirmed, and a file from nobody is not kept.
 */
"use client";

import { useQueryClient } from "@tanstack/react-query";
import * as React from "react";

import { FormError, useApiForm } from "@/components/forms";
import { DialogFooter } from "@/components/ui/dialog";
import { Alert, Button, Field, Input, Select, Textarea } from "@/components/ui/primitives";
import { attachToMyRequest, submitPublicRequest } from "@/features/rights/api";
import { REQUEST_TYPE_COPY } from "@/features/rights/components/copy";
import { DocumentPicker } from "@/features/rights/components/document-picker";
import { useMakeRequest } from "@/features/rights/mutations";
import {
  myRequestSchema,
  publicRequestSchema,
  type MyRequestForm as MyRequestFormValues,
  type MyRequestValues,
  type PublicRequestForm as PublicRequestFormValues,
  type PublicRequestValues,
} from "@/features/rights/schemas";
import { ApiError } from "@/lib/errors";
import { useToast } from "@/providers";
import type { MyRequest, PublicRequestReceipt, TakenRequestType } from "@/types";
import { RIGHTS_REQUEST_TYPES_TAKEN } from "@/types";

function TypeSelect({
  value,
  onChange,
  inputProps,
}: {
  value: TakenRequestType;
  onChange: (next: TakenRequestType) => void;
  inputProps: Record<string, unknown>;
}) {
  return (
    <Select
      {...inputProps}
      value={value}
      onChange={(e) => onChange(e.target.value as TakenRequestType)}
    >
      {RIGHTS_REQUEST_TYPES_TAKEN.map((t) => (
        <option key={t} value={t}>
          {REQUEST_TYPE_COPY[t].label} ({REQUEST_TYPE_COPY[t].section})
        </option>
      ))}
    </Select>
  );
}

function TypeBlurb({ type }: { type: TakenRequestType }) {
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
  initialType?: TakenRequestType;
}) {
  const toast = useToast();
  const qc = useQueryClient();
  const make = useMakeRequest();
  const [documents, setDocuments] = React.useState<File[]>([]);
  const [sending, setSending] = React.useState(false);
  const form = useApiForm<MyRequestValues, MyRequestFormValues>(myRequestSchema, {
    request_type: initialType,
    request_text: "",
    about_dpo: false,
  });
  const type = form.watch("request_type") as TakenRequestType;

  const submit = form.submit(async (values) => {
    const created = await make.mutateAsync(values);
    // The request first - its clock runs from now - then its documents.
    const refused: string[] = [];
    if (documents.length) {
      setSending(true);
      try {
        for (const file of documents) {
          try {
            await attachToMyRequest(created.request_uuid, file);
          } catch (err) {
            refused.push(
              `${file.name}: ${err instanceof ApiError ? err.userMessage() : "not accepted"}`,
            );
          }
        }
      } finally {
        setSending(false);
        void qc.invalidateQueries({ queryKey: ["me"] });
      }
    }
    const sent = documents.length - refused.length;
    toast.success(
      `Recorded as ${created.reference}`,
      `You will hear from us by ${new Date(created.due_at).toLocaleDateString()}.` +
        (sent ? ` ${sent} document${sent === 1 ? "" : "s"} sent with it.` : ""),
    );
    if (refused.length) {
      toast.error(
        `${refused.length} document${refused.length === 1 ? " was" : "s were"} not sent`,
        `${refused.join("; ")}. Your request is recorded; send the document to the Privacy Office if it matters.`,
      );
    }
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

        <p className="text-xs text-text-muted">
          A request is about everything we hold about you - every project and every consent.
        </p>

        <Field
          label="Your request"
          hint="In your own words: what you are asking for and, if it helps, which data."
          required
          error={form.formState.errors.request_text?.message}
        >
          {(p) => <Textarea {...p} rows={5} maxLength={20_000} {...form.register("request_text")} />}
        </Field>

        <DocumentPicker files={documents} onChange={setDocuments} />

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
        <Button type="submit" variant="primary" loading={make.isPending || sending}>
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
  const type = form.watch("request_type") as TakenRequestType;

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
        hint="In your own words: what you are asking for and, if it helps, which data."
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
