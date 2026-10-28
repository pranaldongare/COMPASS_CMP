/**
 * Writing an HR category, or renaming one (0052).
 *
 * The code is asked for once: templates, activities and the audit trail name
 * the category by it, so it does not change afterwards. Name and description
 * do.
 */
"use client";

import { z } from "zod";

import { FormError, useApiForm } from "@/components/forms";
import { DialogFooter } from "@/components/ui/dialog";
import { Badge, Button, Field, Input, Textarea } from "@/components/ui/primitives";
import {
  useCreateHrCategory,
  useUpdateHrCategory,
} from "@/features/hr-categories/mutations";
import { useToast } from "@/providers";
import { optional } from "@/schemas/primitives";
import type { HrCategory } from "@/types";

export function CategoryStatusBadge({ status }: { status: "active" | "retired" }) {
  return status === "active" ? (
    <Badge tone="success" dot>
      Active
    </Badge>
  ) : (
    <Badge tone="neutral" dot>
      Retired
    </Badge>
  );
}

const categorySchema = z.object({
  category_code: z
    .string()
    .trim()
    .transform((v) => v.toUpperCase())
    .pipe(
      z
        .string()
        .regex(
          /^[A-Z][A-Z0-9_]{1,23}$/,
          "2 to 24 characters: a letter first, then letters, digits or underscores",
        ),
    ),
  name: z
    .string()
    .trim()
    .min(1, "Give it a name people will recognise")
    .max(200, "Keep the name under 200 characters"),
  description: optional(
    z.string().trim().max(20000, "That is longer than the field holds"),
  ),
});

export function CategoryForm({
  category,
  onDone,
}: {
  /** Renaming this one; omitted for a new category. */
  category?: HrCategory;
  onDone: (saved?: HrCategory) => void;
}) {
  const toast = useToast();
  const create = useCreateHrCategory();
  const update = useUpdateHrCategory(category?.category_uuid ?? "");

  const form = useApiForm(categorySchema, {
    category_code: category?.category_code ?? "",
    name: category?.name ?? "",
    description: category?.description ?? "",
  });

  const onSubmit = form.submit(async (values) => {
    if (category) {
      const saved = await update.mutateAsync({
        name: values.name,
        description: values.description || null,
      });
      toast.success("Category saved");
      onDone(saved);
      return;
    }
    const saved = await create.mutateAsync({
      category_code: values.category_code,
      name: values.name,
      description: values.description || null,
    });
    toast.success(
      `${saved.category_code} created`,
      "Name the processors that hold its data, then write its templates.",
    );
    onDone(saved);
  });

  return (
    <form method="post" onSubmit={onSubmit} noValidate>
      <FormError message={form.formError} />
      <div className="space-y-4">
        <Field
          label="Code"
          hint={
            category
              ? "Fixed once given: templates, activities and the trail name the category by it."
              : "Short and stable, like WELLNESS, CSR or BGV. It cannot be changed later."
          }
          error={form.formState.errors.category_code?.message}
          required
        >
          {(p) => (
            <Input
              {...p}
              {...form.register("category_code")}
              readOnly={Boolean(category)}
              autoComplete="off"
              placeholder="WELLNESS"
              className="font-mono uppercase"
            />
          )}
        </Field>
        <Field label="Name" error={form.formState.errors.name?.message} required>
          {(p) => (
            <Input {...p} {...form.register("name")} placeholder="Employee wellness" />
          )}
        </Field>
        <Field
          label="Description"
          hint="What activities fall under it. Optional."
          error={form.formState.errors.description?.message}
        >
          {(p) => <Textarea {...p} {...form.register("description")} rows={3} />}
        </Field>
      </div>
      <DialogFooter>
        <Button type="button" variant="ghost" onClick={() => onDone()}>
          Cancel
        </Button>
        <Button
          type="submit"
          variant="primary"
          loading={create.isPending || update.isPending}
        >
          {category ? "Save changes" : "Create category"}
        </Button>
      </DialogFooter>
    </form>
  );
}
