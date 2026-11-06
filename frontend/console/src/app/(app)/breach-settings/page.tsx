/**
 * Breach settings (0058): who hears of a breach.
 *
 * The public link to give out; which roles are told when a report arrives on
 * it; and the addresses of the organisation's board, where its reports are
 * mailed. Kept by the administrator, the DPO and Legal. Nothing here says
 * anything about a breach, so the administrator sees none by it.
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, Trash2, UserPlus } from "lucide-react";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Field,
  Input,
  Skeleton,
  Table,
  Td,
  Th,
  Tr,
} from "@/components/ui/primitives";
import {
  addBoardRecipient,
  getBreachSettings,
  removeBoardRecipient,
  setIntakeRoles,
} from "@/features/breach/api";
import { messageOf } from "@/features/breach/components/record-breach";
import { formatDateTime } from "@/lib/format";
import { keys } from "@/lib/query";
import { useToast } from "@/providers";
import type { BreachSettings } from "@/types";

function PublicLink({ link }: { link: string }) {
  const toast = useToast();
  async function copy() {
    try {
      await navigator.clipboard.writeText(link);
      toast.success("Link copied");
    } catch {
      toast.error("Not copied", "Select the link and copy it yourself.");
    }
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle>The public link</CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          Anyone can report a breach here, with no account, once they have confirmed their email address. Put it wherever
          people will look for it: the intranet, a notice, a staff handbook.
        </p>
      </CardHeader>
      <CardBody className="flex flex-wrap items-center gap-2">
        <code className="min-w-0 flex-1 rounded-md bg-bg-inset px-3 py-2 text-sm break-all">{link}</code>
        <Button variant="secondary" size="sm" onClick={copy}>
          <Copy className="size-4" />
          Copy
        </Button>
      </CardBody>
    </Card>
  );
}

function WhoIsTold({ settings }: { settings: BreachSettings }) {
  const toast = useToast();
  const qc = useQueryClient();
  const save = useMutation({
    mutationFn: (roles: string[]) => setIntakeRoles(roles),
    onSuccess: (fresh) => qc.setQueryData(keys.breach.settings(), fresh),
  });
  async function toggle(role: string, on: boolean) {
    const next = on ? [...settings.intake_roles, role] : settings.intake_roles.filter((r) => r !== role);
    try {
      await save.mutateAsync(next);
    } catch (err) {
      toast.error("Not saved", messageOf(err, "The server refused."));
    }
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle>Who is told when a report arrives</CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          Every active account in these roles is mailed that a report has arrived. The mail does not say what was
          reported. Only the DPO and the Legal PoC can read a report and act on it, so they are always told.
        </p>
      </CardHeader>
      <CardBody className="grid gap-2 sm:grid-cols-2">
        {settings.roles.map((r) => {
          const officer = settings.officers.includes(r.role);
          return (
            <label key={r.role} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                className="size-4 accent-[var(--accent)]"
                checked={officer || settings.intake_roles.includes(r.role)}
                disabled={officer || save.isPending}
                onChange={(e) => toggle(r.role, e.target.checked)}
              />
              {r.title}
            </label>
          );
        })}
      </CardBody>
    </Card>
  );
}

function BoardList({ settings }: { settings: BreachSettings }) {
  const toast = useToast();
  const qc = useQueryClient();
  const [person, setPerson] = React.useState({ full_name: "", email: "" });
  const stored = (fresh: BreachSettings) => qc.setQueryData(keys.breach.settings(), fresh);
  const add = useMutation({
    mutationFn: () =>
      addBoardRecipient({ full_name: person.full_name.trim() || null, email: person.email.trim() }),
    onSuccess: stored,
  });
  const remove = useMutation({ mutationFn: removeBoardRecipient, onSuccess: stored });
  async function save(e: React.FormEvent) {
    e.preventDefault();
    try {
      await add.mutateAsync();
      setPerson({ full_name: "", email: "" });
    } catch (err) {
      toast.error("Not added", messageOf(err, "The server refused."));
    }
  }
  async function takeOff(uuid: string) {
    try {
      await remove.mutateAsync(uuid);
    } catch (err) {
      toast.error("Not removed", messageOf(err, "The server refused."));
    }
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle>The organisation&apos;s board</CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          Every report to the organisation&apos;s board goes to these addresses, and so does the word that a report for
          the DPDP Board or CERT-In has been finalised.
        </p>
      </CardHeader>
      <CardBody className="space-y-4">
        {settings.board_recipients.length === 0 ? (
          <Alert tone="warning" title="Nobody is on the list">
            No report can be finalised until somebody is.
          </Alert>
        ) : (
          <Table>
            <thead>
              <tr>
                <Th>Name</Th>
                <Th>Mail ID</Th>
                <Th>Added</Th>
                {/* Relative, or the hidden word widens the page on a phone. */}
                <Th className="relative">
                  <span className="sr-only">Remove</span>
                </Th>
              </tr>
            </thead>
            <tbody>
              {settings.board_recipients.map((r) => (
                <Tr key={r.recipient_uuid}>
                  <Td>{r.full_name ?? <span className="text-text-subtle">No name</span>}</Td>
                  <Td className="text-sm break-all">{r.email}</Td>
                  <Td className="text-sm">
                    {formatDateTime(r.added_at)}
                    {r.added_by_name && <span className="block text-xs text-text-subtle">{r.added_by_name}</span>}
                  </Td>
                  <Td className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      aria-label={`Remove ${r.email}`}
                      loading={remove.isPending && remove.variables === r.recipient_uuid}
                      onClick={() => takeOff(r.recipient_uuid)}
                    >
                      <Trash2 className="size-4" />
                    </Button>
                  </Td>
                </Tr>
              ))}
            </tbody>
          </Table>
        )}
        <form method="post" className="grid items-end gap-3 sm:grid-cols-[1fr_1fr_auto]" onSubmit={save}>
          <Field label="Name" hint="Optional">
            {(p) => (
              <Input
                {...p}
                value={person.full_name}
                onChange={(e) => setPerson({ ...person, full_name: e.target.value })}
              />
            )}
          </Field>
          <Field label="Mail ID" required>
            {(p) => (
              <Input
                {...p}
                type="email"
                value={person.email}
                onChange={(e) => setPerson({ ...person, email: e.target.value })}
              />
            )}
          </Field>
          <Button type="submit" variant="secondary" disabled={!person.email.trim()} loading={add.isPending}>
            <UserPlus className="size-4" />
            Add
          </Button>
        </form>
      </CardBody>
    </Card>
  );
}

export default function BreachSettingsPage() {
  const query = useQuery({ queryKey: keys.breach.settings(), queryFn: getBreachSettings });
  return (
    <>
      <PageHeader
        title="Breach settings"
        description="Who hears of a breach, and how. Kept by the administrator, the DPO and Legal."
      />
      {query.isLoading && <Skeleton className="h-96" />}
      {query.error && (
        <Alert tone="danger" title="Could not load the settings">
          {query.error.message}
        </Alert>
      )}
      {query.data && (
        <div className="space-y-6">
          <PublicLink link={query.data.report_link} />
          <WhoIsTold settings={query.data} />
          <BoardList settings={query.data} />
        </div>
      )}
    </>
  );
}
