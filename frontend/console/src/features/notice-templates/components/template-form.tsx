/**
 * Writing a notice template, or changing one (0044).
 *
 * The same Rule 3 fields a notice has, under a title of the DPO's choosing,
 * and no project. On a new template the first text can be pasted at once;
 * more languages, and the purposes, are added on its page. Notices already
 * made from a template keep what they were made with - saying so here is what
 * stops an edit looking like it reached them.
 */
"use client";

import { z } from "zod";

import { FormError, useApiForm } from "@/components/forms";
import { DialogFooter } from "@/components/ui/dialog";
import { Alert, Button, Field, Input, Select, Textarea } from "@/components/ui/primitives";
import { useEnums } from "@/features/meta";
import {
  useCreateNoticeTemplate,
  useUpdateNoticeTemplate,
} from "@/features/notice-templates/mutations";
import { AUDIENCES } from "@/features/notices/components/notice-form";
import { useToast } from "@/providers";
import { httpUrl, optional } from "@/schemas/primitives";
import type { LanguageCode, NoticeAudience, NoticeTemplate, NoticeTemplateDetail } from "@/types";

const templateSchema = z.object({
  title: z
    .string()
    .trim()
    .min(3, "Give it a name the list can show - what kind of study it is for")
    .max(200, "Keep the name under 200 characters"),
  withdraw_url: httpUrl("The withdrawal URL"),
  exercise_rights_url: httpUrl("The rights URL"),
  board_complaint_url: httpUrl("The Board complaint URL"),
  dpo_contact: z
    .string()
    .trim()
    .min(3, "State how the DPO can be reached")
    .max(255, "That is longer than the contact field holds"),
  applicable_to: optional(z.string()),
  note: optional(z.string().trim().max(4000, "Keep the note under 4,000 characters")),
  language_code: z.string().optional(),
  rendered_text: z.string().optional(),
});

export function TemplateForm({
  template,
  onDone,
}: {
  /** Editing this one; omitted for a new template. */
  template?: NoticeTemplate;
  onDone: (saved?: NoticeTemplateDetail) => void;
}) {
  const toast = useToast();
  const { data: enums } = useEnums();
  const create = useCreateNoticeTemplate();
  const update = useUpdateNoticeTemplate(template?.template_uuid ?? "");

  const form = useApiForm(templateSchema, {
    title: template?.title ?? "",
    withdraw_url: template?.withdraw_url ?? "",
    exercise_rights_url: template?.exercise_rights_url ?? "",
    board_complaint_url: template?.board_complaint_url ?? "",
    dpo_contact: template?.dpo_contact ?? "",
    applicable_to: template?.applicable_to ?? "",
    note: template?.note ?? "",
    language_code: "english",
    rendered_text: "",
  });

  const onSubmit = form.submit(async (values) => {
    const fields = {
      title: values.title,
      withdraw_url: values.withdraw_url,
      exercise_rights_url: values.exercise_rights_url,
      board_complaint_url: values.board_complaint_url,
      dpo_contact: values.dpo_contact,
      applicable_to: (values.applicable_to || null) as NoticeAudience | null,
      note: values.note || null,
    };
    if (template) {
      const saved = await update.mutateAsync(fields);
      toast.success("Template saved");
      onDone(saved);
      return;
    }
    const text = values.rendered_text?.trim();
    const saved = await create.mutateAsync({
      ...fields,
      rendered_text: text ? values.rendered_text : null,
      language_code: text ? ((values.language_code || "english") as LanguageCode) : null,
    });
    toast.success(
      `Template ${saved.template_code} created`,
      "Add its purposes and languages, then give the ID to the study's R&D User.",
    );
    onDone(saved);
  });

  return (
    <form method="post" onSubmit={onSubmit} noValidate>
      <FormError message={form.formError} />
      <div className="space-y-4">
        {template && template.used_count > 0 && (
          <Alert tone="info">
            <p className="text-sm">
              {template.used_count} project notice{template.used_count === 1 ? " was" : "s were"}{" "}
              made from this template. They are copies and keep what they were made with;
              changes here reach only notices made from now on.
            </p>
          </Alert>
        )}

        <Field
          label="Template name"
          hint="For your list - the kind of study it is for. The data principal never sees it."
          error={form.formState.errors.title?.message}
          required
        >
          {(p) => (
            <Input {...p} {...form.register("title")} placeholder="Gait video studies, adults" />
          )}
        </Field>

        <Field label="DPO contact" error={form.formState.errors.dpo_contact?.message} required>
          {(p) => (
            <Input {...p} {...form.register("dpo_contact")} placeholder="privacy@example.org" />
          )}
        </Field>

        <Field
          label="Applies to"
          hint="Who a notice made from it addresses. Required before that notice can be published."
          error={form.formState.errors.applicable_to?.message}
        >
          {(p) => (
            <Select {...p} {...form.register("applicable_to")}>
              <option value="">Not decided yet</option>
              {AUDIENCES.map((a) => (
                <option key={a.value} value={a.value}>
                  {a.label}
                </option>
              ))}
            </Select>
          )}
        </Field>

        <Field
          label="Note for the collector"
          hint="Shown to whoever collects against a notice made from it, never to the data principal. Optional."
          error={form.formState.errors.note?.message}
        >
          {(p) => <Textarea {...p} {...form.register("note")} rows={2} />}
        </Field>

        <Field
          label="Withdraw consent URL"
          hint="Withdrawing must be as easy as giving consent was."
          error={form.formState.errors.withdraw_url?.message}
          required
        >
          {(p) => (
            <Input {...p} {...form.register("withdraw_url")} placeholder="https://…/withdraw" />
          )}
        </Field>

        <Field
          label="Exercise rights URL"
          error={form.formState.errors.exercise_rights_url?.message}
          required
        >
          {(p) => (
            <Input {...p} {...form.register("exercise_rights_url")} placeholder="https://…/rights" />
          )}
        </Field>

        <Field
          label="Board complaint URL"
          hint="The Data Protection Board portal - not our own grievance form."
          error={form.formState.errors.board_complaint_url?.message}
          required
        >
          {(p) => (
            <Input
              {...p}
              {...form.register("board_complaint_url")}
              placeholder="https://dpb.gov.in/complaint"
            />
          )}
        </Field>

        {!template && (
          <>
            <div className="rule-fade h-px" aria-hidden="true" />
            <Field label="Language" hint="Which language the text below is. Add others afterwards.">
              {(p) => (
                <Select {...p} {...form.register("language_code")}>
                  {(enums?.language_code ?? [{ value: "english", label: "English" }]).map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
            <Field
              label="Notice text"
              hint="What a data principal will read once a project uses it. Optional now; it can be added on the template's page."
              error={form.formState.errors.rendered_text?.message}
            >
              {(p) => (
                <Textarea
                  {...p}
                  {...form.register("rendered_text")}
                  rows={10}
                  className="min-h-48 font-mono text-xs leading-relaxed"
                />
              )}
            </Field>
          </>
        )}
      </div>

      <DialogFooter>
        <Button type="button" variant="ghost" onClick={() => onDone()}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" loading={create.isPending || update.isPending}>
          {template ? "Save changes" : "Create template"}
        </Button>
      </DialogFooter>
    </form>
  );
}
