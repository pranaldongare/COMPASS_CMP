/**
 * The categories an HR PoC runs activities in (0052), set by the
 * administrator on the account's page, as a DCO's processors are.
 *
 * The whole set: a category left unticked is taken away. A retired category
 * already assigned stays offered, so saving the rest does not drop it.
 */
"use client";

import * as React from "react";

import { DialogFooter } from "@/components/ui/dialog";
import { Alert, Button, Mono, Skeleton } from "@/components/ui/primitives";
import { useSetUserCategories } from "@/features/hr-categories/mutations";
import { useHrCategories } from "@/features/hr-categories/queries";
import { useToast } from "@/providers";
import type { User } from "@/types";

function messageOf(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}

export function UserCategoriesForm({ user, onDone }: { user: User; onDone: () => void }) {
  const toast = useToast();
  const save = useSetUserCategories(user.uuid);
  const categories = useHrCategories();
  const held = new Set((user.categories ?? []).map((c) => c.category_uuid));
  const [chosen, setChosen] = React.useState<string[]>([...held]);
  const offered = (categories.data ?? []).filter(
    (c) => c.status === "active" || held.has(c.category_uuid),
  );

  function toggle(uuid: string) {
    setChosen((current) =>
      current.includes(uuid) ? current.filter((u) => u !== uuid) : [...current, uuid],
    );
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    try {
      await save.mutateAsync(chosen);
      toast.success(
        "Categories saved",
        chosen.length
          ? `${user.full_name} now runs activities in ${chosen.length} categor${chosen.length === 1 ? "y" : "ies"}.`
          : `${user.full_name} is assigned to no category and sees none.`,
      );
      onDone();
    } catch (err) {
      toast.error("Not saved", messageOf(err, "The server refused."));
    }
  }

  return (
    <form method="post" onSubmit={submit} noValidate>
      {categories.isLoading ? (
        <Skeleton className="h-32" />
      ) : categories.error ? (
        <Alert tone="danger">{categories.error.userMessage()}</Alert>
      ) : offered.length === 0 ? (
        <Alert tone="info">The Legal PoC has not written a category yet.</Alert>
      ) : (
        <fieldset>
          <legend className="mb-2 text-sm text-text-muted">
            They see these categories and the activities run under them, and no others.
          </legend>
          <div className="grid gap-1.5 sm:grid-cols-2">
            {offered.map((c) => (
              <label
                key={c.category_uuid}
                className="grid cursor-pointer grid-cols-[auto_1fr] items-center gap-x-2 gap-y-0.5 rounded-lg border border-border px-2.5 py-2 text-sm transition-colors hover:bg-bg-inset has-[:checked]:border-accent-border has-[:checked]:bg-accent-subtle"
              >
                <input
                  type="checkbox"
                  checked={chosen.includes(c.category_uuid)}
                  onChange={() => toggle(c.category_uuid)}
                  className="size-4 rounded border-border-strong accent-[var(--accent)]"
                />
                <span className="block min-w-0 truncate font-medium">{c.name}</span>
                <span className="col-start-2 text-2xs text-text-muted">
                  <Mono>{c.category_code}</Mono>
                  {c.status === "retired" && " · retired"}
                </span>
              </label>
            ))}
          </div>
        </fieldset>
      )}
      <DialogFooter>
        <Button type="button" variant="ghost" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" loading={save.isPending}>
          Save categories
        </Button>
      </DialogFooter>
    </form>
  );
}
