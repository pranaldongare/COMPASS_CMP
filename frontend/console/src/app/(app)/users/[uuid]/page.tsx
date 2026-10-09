/**
 * One account, to read (2026-10-09).
 *
 * The register only offered Edit, so reading an account meant opening a form
 * that could change it. This is the account as it stands - name, contacts,
 * role, person type, status - and how its person type has changed. An
 * administrator edits from here; role changes, deactivation and the rest stay
 * on the register, where they are made with the list in view.
 */
"use client";

import { ArrowLeft, Pencil } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  DescriptionItem,
  DescriptionList,
  Skeleton,
  Table,
  Td,
  Th,
  Tr,
} from "@/components/ui/primitives";
import { StatusBadge } from "@/components/ui/status";
import { UserForm } from "@/features/users/components/forms";
import { ProcessorsForm } from "@/features/users/components/processors";
import { usePersonTypeHistory, useUser } from "@/features/users";
import { formatDateTime, humanise } from "@/lib/format";
import { useAuth } from "@/providers";

export default function UserDetailPage() {
  const { uuid } = useParams<{ uuid: string }>();
  const { me } = useAuth();
  const user = useUser(uuid);
  const history = usePersonTypeHistory(uuid);
  const [editing, setEditing] = React.useState(false);
  const [settingProcessors, setSettingProcessors] = React.useState(false);
  const isAdmin = me?.role === "admin";

  if (user.error) {
    return (
      <>
        <PageHeader title="Account" breadcrumb={<BackLink />} />
        <Alert tone="danger" title="Could not load this account">
          {user.error.isForbidden ? "You don't have access to this record." : user.error.userMessage()}
        </Alert>
      </>
    );
  }
  if (user.isLoading || !user.data) {
    return (
      <>
        <PageHeader title="Account" breadcrumb={<BackLink />} />
        <Skeleton className="h-80" />
      </>
    );
  }

  const u = user.data;
  const changes = history.data ?? [];
  return (
    <>
      <PageHeader
        eyebrow="Account"
        title={u.full_name}
        description={u.email ?? u.mobile ?? undefined}
        breadcrumb={<BackLink />}
        actions={
          <div className="flex items-center gap-2">
            <StatusBadge kind="user" value={u.status} />
            {isAdmin && (
              <Button variant="secondary" size="sm" onClick={() => setEditing(true)}>
                <Pencil className="size-4" />
                Edit
              </Button>
            )}
          </div>
        }
      />

      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>The account</CardTitle>
          </CardHeader>
          <CardBody>
            <DescriptionList>
              <DescriptionItem term="Name">{u.full_name}</DescriptionItem>
              <DescriptionItem term="Email">{u.email ?? "None"}</DescriptionItem>
              <DescriptionItem term="Mobile">{u.mobile ?? "None"}</DescriptionItem>
              <DescriptionItem term="Username">{u.username ?? "None"}</DescriptionItem>
              <DescriptionItem term="Organisation id">{u.organization_id ?? "None"}</DescriptionItem>
              <DescriptionItem term="Role">
                <StatusBadge kind="role" value={u.role} dot={false} />
              </DescriptionItem>
              <DescriptionItem term="Person type">{u.person_type ? humanise(u.person_type) : "Not set"}</DescriptionItem>
              <DescriptionItem term="Registered">{formatDateTime(u.created_at)}</DescriptionItem>
              <DescriptionItem term="Last changed">{formatDateTime(u.updated_at)}</DescriptionItem>
            </DescriptionList>
            {isAdmin && (
              <p className="mt-4 text-xs text-text-muted">
                Changing the role, ending access, resending an invitation and resetting the second
                factor are on the <Link href="/users" className="text-accent-text hover:underline">register</Link>.
              </p>
            )}
          </CardBody>
        </Card>

        {(u.role === "dco" || u.role === "rco") && (
          <Card>
            <CardHeader className="flex items-center justify-between gap-2">
              <CardTitle>Collects for</CardTitle>
              {isAdmin && (
                <Button variant="secondary" size="sm" onClick={() => setSettingProcessors(true)}>
                  <Pencil className="size-4" />
                  Change processors
                </Button>
              )}
            </CardHeader>
            <CardBody>
              {!u.processors?.length ? (
                <p className="text-sm text-warning-text">
                  No processor yet, so they see no data sources and cannot add one.
                  {isAdmin ? " Click Change processors to say whom they collect for." : ""}
                </p>
              ) : (
                <>
                  <ul className="flex flex-wrap gap-1.5">
                    {u.processors.map((p) => (
                      <li key={p.processor_uuid}>
                        <Link
                          href={`/processors/${p.processor_uuid}`}
                          className="inline-flex rounded-full border border-border px-2.5 py-0.5 text-sm text-accent-text hover:bg-surface-hover"
                        >
                          {p.legal_name}
                        </Link>
                      </li>
                    ))}
                  </ul>
                  <p className="mt-3 text-xs text-text-muted">
                    They see these processors&apos; data sources and no others, and add new ones only
                    under them.
                  </p>
                </>
              )}
            </CardBody>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Person type, over time</CardTitle>
          </CardHeader>
          <CardBody>
            {history.isLoading ? (
              <Skeleton className="h-16" />
            ) : changes.length === 0 ? (
              <p className="text-sm text-text-muted">Never changed since the account was made.</p>
            ) : (
              <Table>
                <caption className="sr-only">How this account&apos;s person type changed</caption>
                <thead>
                  <tr>
                    <Th>When</Th>
                    <Th>From</Th>
                    <Th>To</Th>
                    <Th>By</Th>
                  </tr>
                </thead>
                <tbody>
                  {changes.map((c) => (
                    <Tr key={c.history_uuid}>
                      <Td className="whitespace-nowrap text-text-muted">{formatDateTime(c.changed_at)}</Td>
                      <Td>{c.from_type ? humanise(c.from_type) : "Not set"}</Td>
                      <Td>{humanise(c.to_type)}</Td>
                      <Td className="text-text-muted">{c.changed_by_name}</Td>
                    </Tr>
                  ))}
                </tbody>
              </Table>
            )}
          </CardBody>
        </Card>
      </div>

      <Dialog open={settingProcessors} onOpenChange={(o) => !o && setSettingProcessors(false)}>
        <DialogContent title="Processors they collect for" size="lg">
          {settingProcessors && <ProcessorsForm user={u} onDone={() => setSettingProcessors(false)} />}
        </DialogContent>
      </Dialog>

      <Dialog open={editing} onOpenChange={(o) => !o && setEditing(false)}>
        <DialogContent title="Edit account" size="lg">
          {editing && <UserForm user={u} onDone={() => setEditing(false)} />}
        </DialogContent>
      </Dialog>
    </>
  );
}

function BackLink() {
  return (
    <Link href="/users" className="inline-flex items-center gap-1 text-sm text-text-muted hover:text-text">
      <ArrowLeft className="size-4" aria-hidden="true" />
      Users
    </Link>
  );
}
