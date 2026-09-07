/**
 * Logging a request that arrived by email.
 *
 * "Dashboard · notice link · email to the DPO - all three make the same
 * record." This is the third. Verification stays pending on purpose: the DPO
 * records how identity was established as a separate act, with a reason, so
 * the record says *how* rather than only that somebody was satisfied.
 */
"use client";

import { FormError, useApiForm } from "@/components/forms";
import { DialogFooter } from "@/components/ui/dialog";
import { Button, Field, Input, Select, Textarea } from "@/components/ui/primitives";
import { REQUEST_TYPE_COPY } from "@/features/rights/components/copy";
import { useLogRequest } from "@/features/rights/mutations";
import {
  logRequestSchema,
  type LogRequestForm as LogRequestFormValues,
  type LogRequestValues,
} from "@/features/rights/schemas";
import { useToast } from "@/providers";
import type { RightsRequest, RightsRequestType } from "@/types";
import { RIGHTS_REQUEST_TYPES } from "@/types";

export function LogRequestForm({ onDone }: { onDone: (created: RightsRequest) => void }) {
  const toast = useToast();
  const log = useLogRequest();
  const form = useApiForm<LogRequestValues, LogRequestFormValues>(logRequestSchema, {
    request_type: "access",
    contact: "",
    name: "",
    request_text: "",
    about_dpo: false,
  });
  const type = form.watch("request_type") as RightsRequestType;

  const submit = form.submit(async (values) => {
    const created = await log.mutateAsync({ ...values, name: values.name || null });
    toast.success(`Logged as ${created.reference}`, "The clock started on receipt. Verify identity next.");
    onDone(created);
  });

  return (
    <form method="post" onSubmit={submit} noValidate>
      <FormError message={form.formError} />
      <div className="space-y-4">
        <Field label="Kind of request" required error={form.formState.errors.request_type?.message}>
          {(p) => (
            <Select {...p} value={type} onChange={(e) => form.setValue("request_type", e.target.value as RightsRequestType, { shouldValidate: true })}>
              {RIGHTS_REQUEST_TYPES.map((t) => (
                <option key={t} value={t}>
                  {REQUEST_TYPE_COPY[t].label} ({REQUEST_TYPE_COPY[t].section})
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field label="Contact it came from" hint="The email or mobile on the message." required error={form.formState.errors.contact?.message}>
          {(p) => <Input {...p} {...form.register("contact")} />}
        </Field>
        <Field label="Name given" error={form.formState.errors.name?.message}>
          {(p) => <Input {...p} {...form.register("name")} />}
        </Field>
        <Field label="The request, as written" hint="Paste it. The DPO classifies it in the next step." required error={form.formState.errors.request_text?.message}>
          {(p) => <Textarea {...p} rows={5} {...form.register("request_text")} />}
        </Field>
        {type === "grievance" && (
          <label className="flex items-start gap-2 text-sm">
            <input type="checkbox" className="mt-0.5 size-4 rounded border-border-strong accent-[var(--accent)]" {...form.register("about_dpo")} />
            <span>The complaint is about the DPO&apos;s own decisions.</span>
          </label>
        )}
      </div>
      <DialogFooter>
        <Button type="submit" variant="primary" loading={log.isPending}>
          Log the request
        </Button>
      </DialogFooter>
    </form>
  );
}
