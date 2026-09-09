/**
 * Who answers a rights-request ticket for a processor.
 *
 * Two shapes. An account here answers on the portal: the ticket is in their
 * console when they sign in, and they return it there. A name and an address
 * are mailed, and the Privacy Office tracks the exchange by hand on the
 * request. An in-house processor's respondent must be an account. A third
 * party's may be either - usually a person at the third party, sometimes one
 * of our own people who represents them here. The server holds the same rule.
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
  // A third party's respondent is usually somebody there, reached by mail;
  // it may be one of our own people who represents them here. In-house is
  // always an account.
  const [asAccount, setAsAccount] = React.useState(processor.is_in_house);
  const useAccount = processor.is_in_house || asAccount;
  const staff = useStaff(canEdit && useAccount);
  const [name, setName] = React.useState("");
  const [contact, setContact] = React.useState("");
  const [userUuid, setUserUuid] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await add.mutateAsync(
        useAccount ? { user_uuid: userUuid } : { name: name.trim(), contact: contact.trim() },
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
            : "Third party: usually a name and an address there, mailed and tracked by hand on the request. Where one of our own people represents this processor, name their account instead and the ticket goes to their console."}
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
          {!processor.is_in_house && (
            <fieldset className="space-y-1">
              <legend className="text-sm font-medium">Who answers for them</legend>
              <div className="flex flex-wrap gap-4 text-sm">
                <label className="flex items-center gap-2">
                  <input type="radio" name="respondent-shape" checked={!asAccount} onChange={() => setAsAccount(false)} />
                  Somebody at the third party, by mail
                </label>
                <label className="flex items-center gap-2">
                  <input type="radio" name="respondent-shape" checked={asAccount} onChange={() => setAsAccount(true)} />
                  One of our own accounts, on the portal
                </label>
              </div>
            </fieldset>
          )}
          {useAccount ? (
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
            disabled={useAccount ? !userUuid : !name.trim() || !contact.trim()}
          >
            <Plus className="size-4" aria-hidden="true" />
            Add respondent
          </Button>
        </form>
      )}
    </div>
  );
}
