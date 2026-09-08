/**
 * Who answers a rights-request ticket for a processor.
 *
 * Two shapes, and the processor decides which. An in-house processor's
 * respondent is an account here: the ticket is in their console when they
 * sign in, and they return it there. A third party's is a name and an address:
 * the Privacy Office mails the instruction and tracks the exchange by hand on
 * the request. The form only offers the shape the processor allows, and the
 * server holds the same rule.
 */
"use client";

import { Building2, Monitor, Plus, UserRoundX } from "lucide-react";
import * as React from "react";

import { Alert, Badge, Button, Field, Input, Select, Skeleton } from "@/components/ui/primitives";
import { useAddRespondent, useRemoveRespondent, useRespondents } from "@/features/registry";
import { useStaff } from "@/features/users/queries";
import { humanise } from "@/lib/format";
import { useAuth, useToast } from "@/providers";
import type { Processor } from "@/types";

function messageOf(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}

export function RespondentsPanel({ processor }: { processor: Processor }) {
  const { me } = useAuth();
  const toast = useToast();
  const canEdit = me?.role === "dpo" || me?.role === "admin";
  const respondents = useRespondents(processor.processor_uuid);
  const add = useAddRespondent(processor.processor_uuid);
  const remove = useRemoveRespondent(processor.processor_uuid);
  const staff = useStaff(canEdit && processor.is_in_house);
  const [name, setName] = React.useState("");
  const [contact, setContact] = React.useState("");
  const [userUuid, setUserUuid] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await add.mutateAsync(
        processor.is_in_house
          ? { user_uuid: userUuid }
          : { name: name.trim(), contact: contact.trim() },
      );
      setName("");
      setContact("");
      setUserUuid("");
      toast.success("Respondent added");
    } catch (err) {
      setError(messageOf(err, "Could not add the respondent."));
    }
  }

  return (
    <div className="space-y-4">
      <Alert tone="info">
        <p className="text-sm">
          {processor.is_in_house
            ? "In-house: a respondent is a CMP account. A ticket addressed to them is in their console the moment it is issued, and they return it there."
            : "Third party: a respondent is a name and an address. The instruction is mailed there, and the Privacy Office tracks the exchange by hand on the request."}
        </p>
      </Alert>

      {respondents.isLoading && <Skeleton className="h-16" />}
      {respondents.error && <Alert tone="danger">{respondents.error.userMessage()}</Alert>}
      {respondents.data && respondents.data.length === 0 && (
        <p className="text-sm text-text-muted">
          Nobody yet. Until somebody is named, the DPO types who answers on each request.
        </p>
      )}
      {respondents.data && respondents.data.length > 0 && (
        <ul className="divide-y divide-border rounded-md border border-border">
          {respondents.data.map((rs) => (
            <li key={rs.respondent_uuid} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
              <div className="min-w-0">
                <p className="flex flex-wrap items-center gap-2 text-sm font-medium">
                  {rs.name}
                  {rs.user_uuid ? (
                    <Badge tone="info" dot={false}>
                      <Monitor className="mr-1 size-3" aria-hidden="true" />
                      on the portal{rs.user_role ? ` · ${humanise(rs.user_role)}` : ""}
                    </Badge>
                  ) : (
                    <Badge tone="neutral" dot={false}>
                      <Building2 className="mr-1 size-3" aria-hidden="true" />
                      by mail
                    </Badge>
                  )}
                </p>
                <p className="text-xs text-text-muted">{rs.contact}</p>
              </div>
              {canEdit && (
                <Button
                  variant="subtle"
                  size="sm"
                  loading={remove.isPending}
                  onClick={() =>
                    remove
                      .mutateAsync(rs.respondent_uuid)
                      .then(() => toast.success("Respondent removed"))
                      .catch((err) => toast.error("Not removed", messageOf(err, "The server refused.")))
                  }
                >
                  <UserRoundX className="size-4" aria-hidden="true" />
                  Remove
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}

      {canEdit && (
        <form method="post" onSubmit={submit} noValidate className="space-y-3 border-t border-border pt-4">
          {error && <Alert tone="danger">{error}</Alert>}
          {processor.is_in_house ? (
            <Field label="Account" hint="An active member of staff. Their name and address follow from the account." required>
              {(p) => (
                <Select {...p} value={userUuid} onChange={(e) => setUserUuid(e.target.value)}>
                  <option value="">Choose…</option>
                  {(staff.data ?? []).map((u) => (
                    <option key={u.uuid} value={u.uuid}>
                      {u.full_name} · {humanise(u.role)} · {u.email}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Name" required>
                {(p) => <Input {...p} value={name} onChange={(e) => setName(e.target.value)} autoComplete="off" />}
              </Field>
              <Field label="Email address" hint="Where the instruction is sent." required>
                {(p) => <Input {...p} type="email" value={contact} onChange={(e) => setContact(e.target.value)} autoComplete="off" />}
              </Field>
            </div>
          )}
          <Button
            type="submit"
            variant="primary"
            size="sm"
            loading={add.isPending}
            disabled={processor.is_in_house ? !userUuid : !name.trim() || !contact.trim()}
          >
            <Plus className="size-4" aria-hidden="true" />
            Add respondent
          </Button>
        </form>
      )}
    </div>
  );
}
