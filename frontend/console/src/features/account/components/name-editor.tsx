/**
 * Your own name, which you may correct yourself (s.12). Staff are data
 * principals too (ADR 0013), so the console offers what the portal does.
 *
 * Correcting it here is enough on this platform: the name is sealed on save,
 * its search runs are recomputed so the register still finds you by part of
 * it, and the change is recorded in the audit trail - without the name, which
 * is sealed on the record (ADR 0015). A name changes nothing else: not how you
 * sign in, not your role.
 *
 * `PATCH /me` with `full_name` only. The server trims it and refuses an empty
 * one; this refuses it first so she is not sent a round trip to be told.
 */
"use client";

import * as React from "react";

import { Alert, Button, Field, Input } from "@/components/ui/primitives";
import { useUpdateMe } from "@/features/account/mutations";
import { ApiError } from "@/lib/errors";
import { useToast } from "@/providers";

/** The server's limit (`ShortText`). */
const MAX = 200;

export function NameEditor({ name }: { name: string }) {
  const toast = useToast();
  const update = useUpdateMe();
  const [editing, setEditing] = React.useState(false);
  const [draft, setDraft] = React.useState(name);
  const [error, setError] = React.useState<string | null>(null);

  const next = draft.trim();

  async function save() {
    if (!next) {
      setError("Enter your name.");
      return;
    }
    if (next === name.trim()) {
      setEditing(false);
      return;
    }
    setError(null);
    try {
      await update.mutateAsync({ full_name: next });
      setEditing(false);
      toast.success("Name changed", `Your account now reads ${next}.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.userMessage() : "Could not change your name.");
    }
  }

  if (!editing) {
    return (
      <span className="flex flex-wrap items-center gap-2" data-testid="name-view">
        <span>{name}</span>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => {
            setDraft(name);
            setError(null);
            setEditing(true);
          }}
        >
          Change
        </Button>
      </span>
    );
  }

  // `method="post"`: before React attaches its handler the browser would
  // submit natively, and HTML's default is GET, which puts the name in the URL.
  return (
    <form
      method="post"
      noValidate
      className="space-y-2"
      onSubmit={(e) => {
        e.preventDefault();
        void save();
      }}
    >
      <Field label="Name" hint="As you would like it to appear" required>
        {(p) => (
          <Input
            {...p}
            value={draft}
            maxLength={MAX}
            autoComplete="name"
            onChange={(e) => setDraft(e.target.value)}
          />
        )}
      </Field>
      {error && <Alert tone="danger">{error}</Alert>}
      <div className="flex gap-2">
        <Button type="submit" size="sm" variant="primary" loading={update.isPending} disabled={!next}>
          Save
        </Button>
        <Button type="button" size="sm" variant="ghost" onClick={() => setEditing(false)}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
