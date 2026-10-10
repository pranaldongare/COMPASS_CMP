/**
 * The account register.
 *
 * Two columns that look similar and are not: `role` is authorisation, and
 * `person_type` is identity. They are separate because a DPO is *also* an
 * employee, and a change of employment status must never silently alter what
 * somebody is permitted to do.
 *
 * There is no delete control, because there is no delete endpoint. Accounts
 * deactivate: deleting one orphans every audit row that names it as actor, and
 * an audit entry whose actor cannot be resolved proves nothing.
 */
"use client";

import { Eye, KeyRound, Pencil, Plus, Send, ShieldEllipsis, UserCheck, UserX } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import {
  FilterBar,
  FilterSelect,
  useFilterParam,
  ResourceList,
  SearchBox,
  useCursorStack,
} from "@/components/data-display/resource-list";
import { RoleChangeForm, UserForm } from "@/features/users/components/forms";
import { ConfirmDialog, Dialog, DialogContent } from "@/components/ui/dialog";
import { EmptyRecords } from "@/components/ui/graphics";
import { RowActions } from "@/components/ui/overlay";
import { Alert, Button, Td, Tr, Skeleton, PersonCell } from "@/components/ui/primitives";
import { StatusBadge } from "@/components/ui/status";
import { useEnums } from "@/features/meta";
import { useDeactivateUser, useReactivateUser, useUsers } from "@/features/users";
import { useForceLogout, useResendInvitation, useResetMfa } from "@/features/users";
import type { User } from "@/types";
import { formatDate, humanise } from "@/lib/format";
import { useAuth, useToast } from "@/providers";

function UsersPageView() {
  const { me } = useAuth();
  const toast = useToast();
  const stack = useCursorStack();
  // In the address, so a link from the dashboard ("accounts awaiting
  // activation") opens the register already filtered.
  const [role, setRole] = useFilterParam("role");
  const [status, setStatus] = useFilterParam("status");
  const [q, setQ] = useFilterParam("q");
  // One account, by uuid: where a link names somebody - the requester on a
  // rights request - it opens them, not the whole register (UX review).
  const [person, setPerson] = useFilterParam("person");

  const deactivate = useDeactivateUser();
  const reactivate = useReactivateUser();
  const resetMfa = useResetMfa();
  const forceLogout = useForceLogout();
  const resendInvitation = useResendInvitation();

  const [creating, setCreating] = React.useState(false);
  const [editing, setEditing] = React.useState<User | null>(null);
  const [changingRole, setChangingRole] = React.useState<User | null>(null);
  const [resettingMfa, setResettingMfa] = React.useState<User | null>(null);

  const { data: enums } = useEnums();
  const query = useUsers({
    role: role || undefined,
    status: status || undefined,
    q: q || undefined,
    person: person || undefined,
    cursor: stack.cursor,
    limit: 25,
  });

  // The DPO reads this register; only an administrator provisions.
  const isAdmin = me?.role === "admin";

  async function toggle(user: User) {
    const active = user.status === "active";
    try {
      if (active) {
        const result = await deactivate.mutateAsync(user.uuid);
        // Different acts behind one button, and the server's message says
        // which: a member of staff loses the role and keeps their account as a
        // data principal; a data principal's account is switched off; a
        // temporary ticket holder's breach-only login ends (S3-09).
        toast.success(
          user.role === "data_subject"
            ? "Account deactivated"
            : user.role === "breach_holder"
              ? "Temporary access ended"
              : "Staff access ended",
          result.message ?? "Every session was terminated immediately.",
        );
      } else {
        await reactivate.mutateAsync(user.uuid);
        toast.success("Account reactivated", `${user.full_name} can sign in again.`);
      }
    } catch (err) {
      const message =
        err && typeof err === "object" && "userMessage" in err
          ? (err as { userMessage: () => string }).userMessage()
          : "The change could not be applied.";
      toast.error("Could not update the account", message);
    }
  }

  async function invite(user: User) {
    try {
      const result = await resendInvitation.mutateAsync(user.uuid);
      toast.success("Invitation sent", result.message ?? undefined);
    } catch (err) {
      const message =
        err && typeof err === "object" && "userMessage" in err
          ? (err as { userMessage: () => string }).userMessage()
          : "The invitation could not be sent.";
      toast.error("Could not send the invitation", message);
    }
  }

  return (
    <>
      <PageHeader
        title="Users"
        description="Manage accounts, roles, and invitations."
        actions={
          isAdmin ? (
            <Button variant="primary" onClick={() => setCreating(true)}>
              <Plus className="size-4" />
              Provision account
            </Button>
          ) : null
        }
      />

      {!isAdmin && (
        <Alert tone="info" className="mb-4">
          You can read the register. Provisioning, role changes and deactivation are
          restricted to administrators.
        </Alert>
      )}

      {person && (
        <Alert tone="info" className="mb-4">
          <span className="flex flex-wrap items-center justify-between gap-2">
            Showing one person.
            <Button variant="ghost" size="sm" onClick={() => setPerson("")}>
              Show everyone
            </Button>
          </span>
        </Alert>
      )}

      <FilterBar>
        <SearchBox
          value={q}
          instant={false}
          placeholder="Name, or a whole email, mobile or id"
          onSubmit={(term) => {
            setQ(term);
            stack.reset();
          }}
        />
        <FilterSelect
          label="Role"
          value={role}
          onChange={(v) => {
            setRole(v);
            stack.reset();
          }}
          options={enums?.user_role ?? []}
          allLabel="All roles"
        />
        <FilterSelect
          label="Status"
          value={status}
          onChange={(v) => {
            setStatus(v);
            stack.reset();
          }}
          options={enums?.user_status ?? []}
          allLabel="All statuses"
        />
      </FilterBar>

      <ResourceList<User>
        query={query}
        stack={stack}
        caption="Registered accounts"
        columns={["Name", "Role", "Person type", "Status", "Registered", ""]}
        keyOf={(u) => u.uuid}
        empty={{
          illustration: <EmptyRecords />,
          title: role || status || q ? "No accounts match" : "No accounts",
          description:
            "Staff are provisioned by an administrator; data subjects self-register through a consent link.",
        }}
        row={(u) => (
          <Tr>
            <Td>
              <PersonCell
                label={u.full_name}
                name={
                  <Link href={`/users/${u.uuid}`} className="font-medium text-text hover:text-accent-text hover:underline">
                    {u.full_name}
                  </Link>
                }
                secondary={u.email ?? u.mobile}
              />
            </Td>
            <Td>
              <StatusBadge kind="role" value={u.role} dot={false} />
            </Td>
            <Td className="text-text-muted">
              {u.person_type ? humanise(u.person_type) : "—"}
            </Td>
            <Td>
              <StatusBadge kind="user" value={u.status} />
            </Td>
            <Td className="whitespace-nowrap text-text-muted">
              {formatDate(u.created_at)}
            </Td>
            {/* Everything a row can do, in one menu (2026-10-10). Acting on
                your own row is how an organisation ends up with no
                administrator, so those items are absent there; resending an
                invitation is only while it is pending - once somebody has a
                password the way back in is theirs. */}
            <Td className="w-12 text-right">
              <RowActions
                label={`Actions for ${u.full_name}`}
                actions={[
                  { label: "View", icon: Eye, href: `/users/${u.uuid}` },
                  ...(isAdmin
                    ? [
                        { label: "Edit", icon: Pencil, onSelect: () => setEditing(u) },
                        ...(u.uuid !== me?.uuid && u.role !== "data_subject"
                          ? [
                              {
                                label: "Change role",
                                icon: ShieldEllipsis,
                                onSelect: () => setChangingRole(u),
                              },
                              {
                                label: "Reset MFA",
                                icon: KeyRound,
                                onSelect: () => setResettingMfa(u),
                              },
                            ]
                          : []),
                        ...(u.status === "pending" && u.role !== "data_subject"
                          ? [
                              {
                                label: "Resend invitation",
                                icon: Send,
                                disabled: resendInvitation.isPending,
                                onSelect: () => invite(u),
                              },
                            ]
                          : []),
                        ...(u.status === "deactivated"
                          ? [
                              {
                                label: "Reactivate",
                                icon: UserCheck,
                                disabled: reactivate.isPending,
                                onSelect: () => toggle(u),
                              },
                            ]
                          : []),
                        ...(u.uuid !== me?.uuid && u.status !== "deactivated"
                          ? [
                              {
                                label:
                                  u.role === "data_subject"
                                    ? "Deactivate"
                                    : u.role === "breach_holder"
                                      ? "End temporary access"
                                      : "End staff access",
                                icon: UserX,
                                destructive: true,
                                disabled: deactivate.isPending,
                                onSelect: () => toggle(u),
                              },
                            ]
                          : []),
                      ]
                    : []),
                ]}
              />
            </Td>
          </Tr>
        )}
      />

      <Dialog open={creating} onOpenChange={setCreating}>
        <DialogContent
          title="Provision an account"
          description="No password is set here - an email invites them to set their own."
          size="lg"
        >
          <UserForm onDone={() => setCreating(false)} />
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(editing)} onOpenChange={(o) => !o && setEditing(null)}>
        <DialogContent title="Edit account" size="lg">
          {editing && <UserForm user={editing} onDone={() => setEditing(null)} />}
        </DialogContent>
      </Dialog>

      <Dialog
        open={Boolean(changingRole)}
        onOpenChange={(o) => !o && setChangingRole(null)}
      >
        <DialogContent
          title="Change role"
          description="Audited, and it ends every session."
        >
          {changingRole && (
            <RoleChangeForm user={changingRole} onDone={() => setChangingRole(null)} />
          )}
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={Boolean(resettingMfa)}
        onOpenChange={(o) => !o && setResettingMfa(null)}
        title={`Reset MFA for ${resettingMfa?.full_name ?? ""}?`}
        confirmLabel="Reset MFA"
        loading={resetMfa.isPending}
        tone="primary"
        consequence={
          <p>
            Their outstanding verification code is discarded and every session ends. They
            will be asked for a fresh code the next time they sign in. Use this when
            somebody has lost access to their email, not as routine maintenance.
          </p>
        }
        onConfirm={async () => {
          if (!resettingMfa) return;
          try {
            await resetMfa.mutateAsync(resettingMfa.uuid);
            await forceLogout.mutateAsync(resettingMfa.uuid);
            toast.success("MFA reset", "They must sign in again.");
            setResettingMfa(null);
          } catch (err) {
            toast.error(
              "Could not reset MFA",
              err && typeof err === "object" && "userMessage" in err
                ? (err as { userMessage: () => string }).userMessage()
                : "Please try again.",
            );
          }
        }}
      />
    </>
  );
}

/**
 * `useFilterParam` reads the query string, which forces client rendering, so
 * Next wants a boundary around the view.
 */
export default function UsersPage() {
  return (
    <React.Suspense fallback={<Skeleton className="h-96" />}>
      <UsersPageView />
    </React.Suspense>
  );
}
