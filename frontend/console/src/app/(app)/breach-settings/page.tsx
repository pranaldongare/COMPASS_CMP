/**
 * Breach settings (0058): who hears of a breach.
 *
 * The public link to give out; which roles are told when a report arrives on
 * it; and the addresses of the organisation's board, where its reports are
 * mailed. Kept by the administrator, the DPO and Legal. Nothing here says
 * anything about a breach, so the administrator sees none by it.
 *
 * The board's list is where every send starts (0064): whoever finalises a
 * report may leave an address out of it, or add one for it alone. A mandatory
 * address goes with every report, and cannot be taken off the list until it
 * is optional again. Every change to the list is mailed to the DPO and the
 * Legal PoC, so the server refuses one it cannot tell them of.
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, Trash2 } from "lucide-react";

import { PageHeader } from "@/components/layout/app-shell";
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
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
  setBoardRecipientMandatory,
  setIntakeRoles,
} from "@/features/breach/api";
import { BoardAddressForm, type BoardAddress } from "@/features/breach/components/board-picker";
import { messageOf } from "@/features/breach/components/record-breach";
import { isApiError } from "@/lib/errors";
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

/** What every change to the board's list sets going. */
const TOLD = "The DPO and the Legal PoC are mailed about the change.";

/** Why a change to the list did not happen. The officers are mailed about every
 *  change, so one they cannot be told of is not made; the API client says only
 *  "something went wrong" of a 503, which would leave nobody knowing to wait. */
function refusal(err: unknown): string {
  if (isApiError(err) && err.status === 503) {
    return "Not changed: the officers could not be told just now. Try again in a moment.";
  }
  return messageOf(err, "The server refused.");
}

function BoardList({ settings }: { settings: BreachSettings }) {
  const toast = useToast();
  const qc = useQueryClient();
  const stored = (fresh: BreachSettings) => qc.setQueryData(keys.breach.settings(), fresh);
  const add = useMutation({
    mutationFn: (person: BoardAddress) =>
      addBoardRecipient({ full_name: person.full_name || null, email: person.email }),
    onSuccess: stored,
  });
  const remove = useMutation({ mutationFn: removeBoardRecipient, onSuccess: stored });
  const mark = useMutation({
    mutationFn: ({ uuid, on }: { uuid: string; on: boolean }) => setBoardRecipientMandatory(uuid, on),
    onSuccess: stored,
  });
  const anyMandatory = settings.board_recipients.some((r) => r.mandatory);

  async function save(person: BoardAddress) {
    try {
      await add.mutateAsync(person);
      toast.success("Added to the list", TOLD);
      return true;
    } catch (err) {
      toast.error("Not added", refusal(err));
      return false;
    }
  }
  async function takeOff(uuid: string) {
    try {
      await remove.mutateAsync(uuid);
      toast.success("Removed from the list", TOLD);
    } catch (err) {
      toast.error("Not removed", refusal(err));
    }
  }
  async function toggle(uuid: string, on: boolean) {
    try {
      await mark.mutateAsync({ uuid, on });
      toast.success(on ? "Marked mandatory" : "No longer mandatory", TOLD);
    } catch (err) {
      toast.error("Not changed", refusal(err));
    }
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle>The organisation&apos;s board</CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          Every report to the organisation&apos;s board goes to these addresses, and so does the word that a report for
          the DPDP Board or CERT-In has been finalised. Whoever finalises a report may leave an address out of that one
          report, or add another for it alone. A mandatory address goes with every report and cannot be left out or
          removed until it is made optional. Every change to this list is mailed to the DPO and the Legal PoC.
        </p>
      </CardHeader>
      <CardBody className="space-y-4">
        {settings.board_recipients.length === 0 ? (
          <Alert tone="warning" title="Nobody is on the list">
            No report can be sent until somebody is, unless an address is added when it is finalised.
          </Alert>
        ) : (
          <Table>
            <thead>
              <tr>
                <Th>Name</Th>
                <Th>Mail ID</Th>
                <Th>Added</Th>
                <Th>Mandatory</Th>
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
                  <Td>
                    <input
                      type="checkbox"
                      className="size-4 accent-[var(--accent)]"
                      aria-label={`Mandatory: ${r.email}`}
                      checked={r.mandatory}
                      // One press at a time per row: the box shows the server's answer.
                      disabled={mark.isPending && mark.variables?.uuid === r.recipient_uuid}
                      onChange={(e) => toggle(r.recipient_uuid, e.target.checked)}
                    />
                    {r.mandatory && r.mandatory_changed_at && (
                      <span className="block text-xs text-text-subtle">
                        {formatDateTime(r.mandatory_changed_at)}
                        {r.mandatory_changed_by_name && <> · {r.mandatory_changed_by_name}</>}
                      </span>
                    )}
                  </Td>
                  <Td className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      aria-label={`Remove ${r.email}`}
                      disabled={r.mandatory}
                      title={r.mandatory ? "Make it optional before removing it" : undefined}
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
        {anyMandatory && (
          <p className="text-xs text-text-subtle">A mandatory address cannot be removed. Untick Mandatory first.</p>
        )}
        <BoardAddressForm submitLabel="Add" pending={add.isPending} onAdd={save} />
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
