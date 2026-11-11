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

import { Eye, Pencil, Plus } from "lucide-react";
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
import { useAccountActions } from "@/features/users/components/account-actions";
import { UserForm } from "@/features/users/components/forms";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { EmptyRecords } from "@/components/ui/graphics";
import { RowActions } from "@/components/ui/overlay";
import { Alert, Button, Td, Tr, Skeleton, PersonCell } from "@/components/ui/primitives";
import { StatusBadge } from "@/components/ui/status";
import { useEnums } from "@/features/meta";
import { useUsers } from "@/features/users";
import type { User } from "@/types";
import { formatDate, humanise } from "@/lib/format";
import { useAuth } from "@/providers";

function UsersPageView() {
  const { me } = useAuth();
  const stack = useCursorStack();
  // In the address, so a link from the dashboard ("accounts awaiting
  // activation") opens the register already filtered.
  const [role, setRole] = useFilterParam("role");
  const [status, setStatus] = useFilterParam("status");
  const [q, setQ] = useFilterParam("q");
  // One account, by uuid: where a link names somebody - the requester on a
  // rights request - it opens them, not the whole register (UX review).
  const [person, setPerson] = useFilterParam("person");

  // Change role, reset MFA, invitations and access: shared with the
  // account's own page (2026-11-11).
  const account = useAccountActions();

  const [creating, setCreating] = React.useState(false);
  const [editing, setEditing] = React.useState<User | null>(null);

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
            {/* Everything a row can do, in one menu (2026-10-10); the guards
                are `useAccountActions`', shared with the account's page. */}
            <Td className="w-12 text-right">
              <RowActions
                label={`Actions for ${u.full_name}`}
                actions={[
                  { label: "View", icon: Eye, href: `/users/${u.uuid}` },
                  ...(isAdmin ? [{ label: "Edit", icon: Pencil, onSelect: () => setEditing(u) }] : []),
                  ...account.actionsFor(u),
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

      {account.dialogs}
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
