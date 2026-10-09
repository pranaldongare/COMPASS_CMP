/**
 * The processors a DCO or an RCO collects for (2026-10-09, 0050).
 *
 * They see the data sources of these processors and no others, and register
 * new ones only under them. A DCO collects for third parties and an RCO for
 * the R&D team's own, so only that kind is offered - the server refuses the
 * other. The register can hold hundreds of processors, so the list is
 * searched rather than scrolled; what is chosen stays on top as chips.
 */
"use client";

import { X } from "lucide-react";
import * as React from "react";

import { FormError, useApiForm } from "@/components/forms";
import { DialogFooter } from "@/components/ui/dialog";
import { Alert, Button, Input, Skeleton } from "@/components/ui/primitives";
import { useProcessors } from "@/features/registry";
import { useSetUserProcessors } from "@/features/users/mutations";
import { useToast } from "@/providers";
import type { CollectorProcessor, User, Uuid } from "@/types";
import { z } from "zod";

export interface PickedProcessor {
  processor_uuid: Uuid;
  legal_name: string;
}

export function ProcessorPicker({
  role,
  value,
  onChange,
}: {
  role: "dco" | "rco";
  value: PickedProcessor[];
  onChange: (next: PickedProcessor[]) => void;
}) {
  const [q, setQ] = React.useState("");
  const [term, setTerm] = React.useState("");
  React.useEffect(() => {
    const t = setTimeout(() => setTerm(q.trim()), 250);
    return () => clearTimeout(t);
  }, [q]);
  const processors = useProcessors({ status: "active", q: term || undefined, limit: 50 });
  const inHouse = role === "rco";
  const chosen = new Set(value.map((p) => p.processor_uuid));
  const offered = (processors.data?.items ?? []).filter(
    (p) => p.is_in_house === inHouse && !chosen.has(p.processor_uuid),
  );
  const id = React.useId();

  return (
    <fieldset>
      <legend className="text-sm font-medium">Collects for</legend>
      <p className="mt-0.5 mb-2 text-xs text-text-muted">
        {inHouse
          ? "The in-house teams this R&D Collection Owner collects for."
          : "The third parties this Data Collection Owner collects for."}{" "}
        They see these processors&apos; data sources and no others, and add new ones only under
        them.
      </p>

      {value.length > 0 && (
        <ul className="mb-2 flex flex-wrap gap-1.5" aria-label="Chosen processors">
          {value.map((p) => (
            <li
              key={p.processor_uuid}
              className="inline-flex items-center gap-1 rounded-full border border-accent-border bg-accent-subtle py-0.5 pr-1 pl-2.5 text-sm"
            >
              {p.legal_name}
              <button
                type="button"
                aria-label={`Remove ${p.legal_name}`}
                onClick={() => onChange(value.filter((v) => v.processor_uuid !== p.processor_uuid))}
                className="rounded-full p-0.5 text-text-muted hover:bg-surface-hover hover:text-text"
              >
                <X className="size-3.5" aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      )}

      <label htmlFor={id} className="sr-only">
        Find a processor
      </label>
      <Input
        id={id}
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder={inHouse ? "Find an in-house team" : "Find a third party"}
      />
      <div className="mt-1.5 max-h-44 overflow-y-auto rounded-lg border border-border">
        {processors.isLoading ? (
          <Skeleton className="m-2 h-16" />
        ) : offered.length === 0 ? (
          <p className="px-3 py-2 text-sm text-text-muted">
            {term ? "No processor of this kind matches." : "No other processor of this kind is registered."}
          </p>
        ) : (
          <ul>
            {offered.map((p) => (
              <li key={p.processor_uuid}>
                <button
                  type="button"
                  onClick={() =>
                    onChange([...value, { processor_uuid: p.processor_uuid, legal_name: p.legal_name }])
                  }
                  className="block w-full px-3 py-1.5 text-left text-sm hover:bg-surface-hover"
                >
                  {p.legal_name}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </fieldset>
  );
}

/** The set on an existing account, from its page. */
export function ProcessorsForm({ user, onDone }: { user: User; onDone: () => void }) {
  const toast = useToast();
  const save = useSetUserProcessors(user.uuid);
  const [picked, setPicked] = React.useState<PickedProcessor[]>(
    (user.processors ?? []).map((p: CollectorProcessor) => ({
      processor_uuid: p.processor_uuid,
      legal_name: p.legal_name,
    })),
  );
  const form = useApiForm(z.object({}), {});

  const onSubmit = form.submit(async () => {
    await save.mutateAsync(picked.map((p) => p.processor_uuid));
    toast.success(
      "Processors saved",
      picked.length
        ? `${user.full_name} now sees the data sources of ${picked.length} processor(s).`
        : `${user.full_name} collects for no processor and sees no data sources.`,
    );
    onDone();
  });

  return (
    <form method="post" onSubmit={onSubmit} noValidate>
      <FormError message={form.formError} />
      {picked.length === 0 && (
        <Alert tone="warning" className="mb-4">
          With no processor they see no data sources and cannot add one.
        </Alert>
      )}
      <ProcessorPicker role={user.role === "rco" ? "rco" : "dco"} value={picked} onChange={setPicked} />
      <DialogFooter>
        <Button type="button" variant="ghost" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" loading={save.isPending}>
          Save processors
        </Button>
      </DialogFooter>
    </form>
  );
}
