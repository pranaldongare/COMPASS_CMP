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
 *
 * Signed in, she can confine a request to one consent: the access she wants
 * is the data under that consent, the erasure is of that data and no other.
 * From her consents page the consent is already chosen; from her requests
 * page she picks it, or asks about everything.
 */
"use client";

import * as React from "react";

import { FormError, useApiForm } from "@/components/forms";
import { DialogFooter } from "@/components/ui/dialog";
import { Alert, Button, Field, Input, Select, Textarea } from "@/components/ui/primitives";
import { useMyConsents } from "@/features/my-consents";
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
import { formatDate } from "@/lib/format";
import { useToast } from "@/providers";
import type { MyConsent, MyRequest, PublicRequestReceipt, RightsRequestType } from "@/types";
import { RIGHTS_REQUEST_TYPES } from "@/types";

function TypeSelect({
  value,
  onChange,
  inputProps,
  exclude = [],
}: {
  value: RightsRequestType;
  onChange: (next: RightsRequestType) => void;
  inputProps: Record<string, unknown>;
  exclude?: RightsRequestType[];
}) {
  return (
    <Select
      {...inputProps}
      value={value}
      onChange={(e) => onChange(e.target.value as RightsRequestType)}
    >
      {RIGHTS_REQUEST_TYPES.filter((t) => !exclude.includes(t)).map((t) => (
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

/** One consent, the way the picker and the fixed box name it. */
export function consentLabel(c: MyConsent): string {
  return `${c.project_name} · ${c.notice_code} v${c.version} · ${formatDate(c.affirmative_action_at)}${c.is_withdrawal ? " (withdrawn)" : ""}`;
}

function ConsentPicker({
  value,
  onChange,
  inputProps,
}: {
  value: string | null;
  onChange: (next: string | null) => void;
  inputProps: Record<string, unknown>;
}) {
  const consents = useMyConsents();
  const list = consents.data ?? [];
  return (
    <Select
      {...inputProps}
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value || null)}
      disabled={consents.isLoading}
    >
      <option value="">Everything you hold about me</option>
      {list.map((c) => (
        <option key={c.consent_uuid} value={c.consent_uuid}>
          {consentLabel(c)}
        </option>
      ))}
    </Select>
  );
}

/** Signed in: the session is the verification, so the clock starts on submit. */
export function MyRequestForm({
  onDone,
  initialType = "access",
  consent = null,
}: {
  onDone: (created: MyRequest) => void;
  initialType?: RightsRequestType;
  /** Already chosen - from her consents page - and not changeable here. */
  consent?: MyConsent | null;
}) {
  const toast = useToast();
  const make = useMakeRequest();
  const form = useApiForm<MyRequestValues, MyRequestFormValues>(myRequestSchema, {
    request_type: initialType,
    request_text: "",
    about_dpo: false,
    consent_uuid: consent?.consent_uuid ?? null,
  });
  const type = form.watch("request_type") as RightsRequestType;
  const confined = (form.watch("consent_uuid") as string | null) ?? null;

  const submit = form.submit(async (values) => {
    const created = await make.mutateAsync({
      ...values,
      // A grievance is about handling, not about one consent.
      consent_uuid: values.request_type === "grievance" ? null : values.consent_uuid,
    });
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
              exclude={consent ? ["grievance"] : []}
            />
          )}
        </Field>
        <TypeBlurb type={type} />

        {consent ? (
          <div className="rounded-md border border-border bg-bg-inset p-3 text-sm">
            <p className="text-2xs font-semibold uppercase tracking-wide text-text-subtle">
              About this consent only
            </p>
            <p className="mt-1">{consentLabel(consent)}</p>
            <p className="mt-1 text-xs text-text-muted">
              Only the data held under this consent is in question. Holders, what is in scope
              and the response are all confined to it.
            </p>
          </div>
        ) : (
          type !== "grievance" && (
            <Field
              label="About"
              hint="Everything we hold about you, or one consent - the request then covers only the data under it."
              error={form.formState.errors.consent_uuid?.message}
            >
              {(p) => (
                <ConsentPicker
                  inputProps={p}
                  value={confined}
                  onChange={(next) => form.setValue("consent_uuid", next, { shouldValidate: true })}
                />
              )}
            </Field>
          )
        )}

        <Field
          label="Your request"
          hint={
            confined
              ? "In your own words. Which data under this consent, and what you want done."
              : "In your own words. Which project, which data, what you want done."
          }
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
