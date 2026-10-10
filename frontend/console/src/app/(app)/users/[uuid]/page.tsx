/**
 * One account, to read (2026-10-09).
 *
 * The register only offered Edit, so reading an account meant opening a form
 * that could change it. This is the account as it stands - name, contacts,
 * role, person type, status - and how its person type has changed. An
 * administrator edits from here; role changes, deactivation and the rest stay
 * on the register, where they are made with the list in view.
 *
 * Laid out as the other record pages (2026-10-10): a summary card over
 * underline tabs - the account, whom a collection owner collects for (their
 * roles only, as before), and the person type's history. The fragment names
 * the tab, so each can be linked to.
 */
"use client";

import {
  ArrowLeft,
  BadgeCheck,
  Building2,
  CalendarDays,
  Hash,
  History as HistoryIcon,
  IdCard,
  LayoutGrid,
  Pencil,
  UserRound,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import { RecordHeader } from "@/components/layout/record-header";
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
import { StatusBadge, statusLabel } from "@/components/ui/status";
import { Tab, TabList, TabPanel, Tabs, useHashTab } from "@/components/ui/tabs";
import { UserForm } from "@/features/users/components/forms";
import { ProcessorsForm } from "@/features/users/components/processors";
import { usePersonTypeHistory, useUser } from "@/features/users";
import { formatDate, formatDateTime, humanise } from "@/lib/format";
import { useAuth } from "@/providers";

const TABS = ["overview", "collects", "history"] as const;

export default function UserDetailPage() {
  const { uuid } = useParams<{ uuid: string }>();
  const { me } = useAuth();
  const user = useUser(uuid);
  const history = usePersonTypeHistory(uuid);
  const [editing, setEditing] = React.useState(false);
  const [settingProcessors, setSettingProcessors] = React.useState(false);
  const [tab, setTab] = useHashTab(TABS, "overview");
  const isAdmin = me?.role === "admin";

  if (user.error) {
    return (
      <>
        <PageHeader title="Account" breadcrumb={<BackLink />} />
        <Alert tone="danger" title="Could not load this account">
          {user.error.isForbidden
            ? "You don't have access to this record."
            : user.error.userMessage()}
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
  // A DCO's or an RCO's processors; every other role collects for nobody.
  const collects = u.role === "dco" || u.role === "rco";
  const processors = u.processors ?? [];
  // The tab is for collection owners alone; an address naming it on any
  // other account opens the account instead of an empty panel.
  const shown = tab === "collects" && !collects ? "overview" : tab;
  return (
    <>
      <PageHeader heading={false} title={u.full_name} breadcrumb={<BackLink />} />
      <RecordHeader
        icon={UserRound}
        title={u.full_name}
        meta={
          <>
            <span className="text-2xs font-semibold tracking-wider text-accent-text uppercase">
              Account
            </span>
            <StatusBadge kind="user" value={u.status} />
            <StatusBadge kind="role" value={u.role} dot={false} />
            {(u.email ?? u.mobile) && <span>{u.email ?? u.mobile}</span>}
          </>
        }
        actions={
          isAdmin && (
            <Button variant="secondary" size="sm" onClick={() => setEditing(true)}>
              <Pencil className="size-4" />
              Edit
            </Button>
          )
        }
        facts={[
          { label: "Role", value: statusLabel("role", u.role), icon: BadgeCheck, tint: 0 },
          {
            label: "Person type",
            value: u.person_type ? humanise(u.person_type) : "Not set",
            icon: IdCard,
            tint: 1,
          },
          collects
            ? {
                label: "Collects for",
                value: `${processors.length} ${processors.length === 1 ? "processor" : "processors"}`,
                icon: Building2,
                tint: 2,
                href: "#collects",
              }
            : {
                label: "Organisation id",
                value: u.organization_id ?? "None",
                icon: Hash,
                tint: 2,
              },
          {
            label: "Registered",
            value: formatDate(u.created_at),
            icon: CalendarDays,
            tint: 3,
          },
        ]}
      />

      <Tabs
        value={shown}
        onValueChange={setTab}
        label="Account sections"
        layout="underline"
      >
        <TabList>
          <Tab value="overview" icon={LayoutGrid}>
            Overview
          </Tab>
          {collects && (
            <Tab value="collects" icon={Building2} count={processors.length}>
              Collects for
            </Tab>
          )}
          <Tab value="history" icon={HistoryIcon} count={history.data?.length}>
            Person type history
          </Tab>
        </TabList>

        <TabPanel value="overview">
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
                <DescriptionItem term="Organisation id">
                  {u.organization_id ?? "None"}
                </DescriptionItem>
                <DescriptionItem term="Role">
                  <StatusBadge kind="role" value={u.role} dot={false} />
                </DescriptionItem>
                <DescriptionItem term="Person type">
                  {u.person_type ? humanise(u.person_type) : "Not set"}
                </DescriptionItem>
                <DescriptionItem term="Registered">
                  {formatDateTime(u.created_at)}
                </DescriptionItem>
                <DescriptionItem term="Last changed">
                  {formatDateTime(u.updated_at)}
                </DescriptionItem>
              </DescriptionList>
              {isAdmin && (
                <p className="mt-4 text-xs text-text-muted">
                  Changing the role, ending access, resending an invitation and resetting
                  the second factor are on the{" "}
                  <Link href="/users" className="text-accent-text hover:underline">
                    register
                  </Link>
                  .
                </p>
              )}
            </CardBody>
          </Card>
        </TabPanel>

        {collects && (
          <TabPanel value="collects">
            <Card>
              <CardHeader className="flex items-center justify-between gap-2">
                <CardTitle>Collects for</CardTitle>
                {isAdmin && (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setSettingProcessors(true)}
                  >
                    <Pencil className="size-4" />
                    Change processors
                  </Button>
                )}
              </CardHeader>
              <CardBody>
                {!u.processors?.length ? (
                  <p className="text-sm text-warning-text">
                    No processor yet, so they see no data sources and cannot add one.
                    {isAdmin
                      ? " Click Change processors to say whom they collect for."
                      : ""}
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
                      They see these processors&apos; data sources and no others, and add
                      new ones only under them.
                    </p>
                  </>
                )}
              </CardBody>
            </Card>
          </TabPanel>
        )}

        <TabPanel value="history">
          <Card>
            <CardHeader>
              <CardTitle>Person type, over time</CardTitle>
            </CardHeader>
            <CardBody>
              {history.isLoading ? (
                <Skeleton className="h-16" />
              ) : changes.length === 0 ? (
                <p className="text-sm text-text-muted">
                  Never changed since the account was made.
                </p>
              ) : (
                <Table>
                  <caption className="sr-only">
                    How this account&apos;s person type changed
                  </caption>
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
                        <Td className="whitespace-nowrap text-text-muted">
                          {formatDateTime(c.changed_at)}
                        </Td>
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
        </TabPanel>
      </Tabs>

      <Dialog
        open={settingProcessors}
        onOpenChange={(o) => !o && setSettingProcessors(false)}
      >
        <DialogContent title="Processors they collect for" size="lg">
          {settingProcessors && (
            <ProcessorsForm user={u} onDone={() => setSettingProcessors(false)} />
          )}
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
    <Link
      href="/users"
      className="inline-flex items-center gap-1 text-sm text-text-muted hover:text-text"
    >
      <ArrowLeft className="size-4" aria-hidden="true" />
      Users
    </Link>
  );
}
