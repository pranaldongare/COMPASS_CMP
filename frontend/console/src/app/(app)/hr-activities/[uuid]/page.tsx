/**
 * One HR activity (ADR 0033).
 *
 * Its summary, its one open link - copy it, replace it, revoke it - the
 * register of who has consented, by name, and its exports. The HR PoC may
 * upgrade it to another approved version of its category (a new notice
 * version; the link moves with it) and close it; Legal may close it.
 */
"use client";

import { ArrowLeft, FileText, Hash, Link2, Sparkles, Upload, Users } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import { RecordHeader } from "@/components/layout/record-header";
import { ConfirmDialog, Dialog, DialogContent, DialogFooter } from "@/components/ui/dialog";
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  DescriptionItem,
  DescriptionList,
  Field,
  Mono,
  Select,
  Skeleton,
  Textarea,
} from "@/components/ui/primitives";
import { StatusBadge } from "@/components/ui/status";
import { Tab, TabList, TabPanel, Tabs, useHashTab } from "@/components/ui/tabs";
import { CopyLinkButton } from "@/features/consent/components/copy-link";
import { ProjectConsents } from "@/features/consent/components/project-consents";
import { useRemintLink, useRevokeLink } from "@/features/consent/mutations";
import { ExportForm } from "@/features/exchange/components/export-form";
import { ProjectExportsCard } from "@/features/exchange/components/project-exchanges";
import {
  useActivityOptions,
  useCloseHrActivity,
  useHrActivity,
  useUpgradeHrActivity,
} from "@/features/hr-activities";
import { PurposePicker } from "@/features/hr-activities/components/activity-wizard";
import { formatDateTime } from "@/lib/format";
import { useAuth, useToast } from "@/providers";
import type { HrActivityDetail } from "@/types";

const TABS = ["overview", "consents", "exports"] as const;

function messageOf(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}

export default function HrActivityPage() {
  const params = useParams<{ uuid: string }>();
  const { me } = useAuth();
  const activity = useHrActivity(params?.uuid);
  const [tab, setTab] = useHashTab(TABS, "overview");
  const [consentStatus, setConsentStatus] = React.useState("");
  const [exporting, setExporting] = React.useState(false);
  const [upgrading, setUpgrading] = React.useState(false);
  const [closing, setClosing] = React.useState(false);

  if (activity.isLoading) return <Skeleton className="h-96" />;
  if (activity.error)
    return (
      <Alert tone="danger" title="Could not load this activity">
        {activity.error.userMessage()}
      </Alert>
    );
  const a = activity.data;
  if (!a) return null;
  const running = a.status === "approved";
  const isPoc = me?.role === "hr_user";
  const canClose = running && (isPoc || me?.role === "legal");

  return (
    <>
      <PageHeader
        heading={false}
        breadcrumb={
          <Link href="/hr-activities" className="inline-flex items-center gap-1 hover:underline">
            <ArrowLeft className="size-3.5" aria-hidden="true" />
            HR activities
          </Link>
        }
        title={a.name}
      />
      <RecordHeader
        icon={Sparkles}
        title={a.name}
        meta={
          <>
            <span className="text-2xs font-semibold tracking-wider text-accent-text uppercase">
              HR activity
            </span>
            <StatusBadge kind="project" value={a.status} />
            <Mono className="text-text">{a.category_code}</Mono>
          </>
        }
        actions={
          <>
            {running && isPoc && (
              <Button variant="secondary" size="sm" onClick={() => setUpgrading(true)}>
                Upgrade
              </Button>
            )}
            {canClose && (
              <Button variant="subtle" size="sm" onClick={() => setClosing(true)}>
                Close
              </Button>
            )}
          </>
        }
        facts={[
          { label: "Category", value: a.category_code, icon: Hash, tint: 0 },
          {
            label: "Template",
            value: `${a.template_code} v${a.template_version}`,
            icon: FileText,
            tint: 1,
          },
          {
            label: "Consents",
            value: a.consent_count,
            icon: Users,
            tint: 2,
            href: "#consents",
          },
          {
            label: "Link",
            value: a.link ? a.link.status : "none",
            icon: Link2,
            tint: 3,
          },
        ]}
      />

      <Tabs value={tab} onValueChange={setTab} label="Activity sections" layout="underline">
        <TabList>
          <Tab value="overview" icon={Sparkles}>
            Overview
          </Tab>
          <Tab value="consents" icon={Users} count={a.consent_count}>
            Consents
          </Tab>
          <Tab value="exports" icon={Upload}>
            Exports
          </Tab>
        </TabList>
        <TabPanel value="overview" className="space-y-5">
          <div className="grid gap-5 lg:grid-cols-2 lg:items-start">
            <Card>
              <CardHeader>
                <CardTitle>The activity</CardTitle>
              </CardHeader>
              <CardBody>
                <DescriptionList>
                  <DescriptionItem term="Category">
                    {a.category_code} · {a.category_name}
                  </DescriptionItem>
                  <DescriptionItem term="Template version">
                    <Mono>{a.template_code}</Mono> v{a.template_version} · {a.template_title}
                    {a.version_status !== "approved" && (
                      <span className="text-xs text-text-muted"> ({a.version_status})</span>
                    )}
                  </DescriptionItem>
                  <DescriptionItem term="Description">
                    <span className="whitespace-pre-wrap">{a.description}</span>
                  </DescriptionItem>
                  <DescriptionItem term="Notice">
                    {a.notice_uuid ? (
                      <>
                        <Mono>{a.notice_code}</Mono> v{a.notice_version}
                      </>
                    ) : (
                      "None"
                    )}
                  </DescriptionItem>
                  <DescriptionItem term="Created">
                    {formatDateTime(a.created_at)} by {a.created_by_name}
                  </DescriptionItem>
                </DescriptionList>
              </CardBody>
            </Card>
            <LinkCard activity={a} />
          </div>
        </TabPanel>
        <TabPanel value="consents" className="space-y-5">
          <div id="consents" className="scroll-mt-20">
            <ProjectConsents
              projectUuid={a.activity_uuid}
              sites={[]}
              status={consentStatus}
              onStatus={setConsentStatus}
            />
          </div>
        </TabPanel>
        <TabPanel value="exports" className="space-y-5">
          <ProjectExportsCard
            projectUuid={a.activity_uuid}
            canGenerate={running}
            onGenerate={() => setExporting(true)}
          />
        </TabPanel>
      </Tabs>

      <Dialog open={exporting} onOpenChange={setExporting}>
        <DialogContent title="Export the consented list">
          {exporting && (
            <ExportForm projectUuid={a.activity_uuid} onDone={() => setExporting(false)} />
          )}
        </DialogContent>
      </Dialog>
      <Dialog open={upgrading} onOpenChange={setUpgrading}>
        <DialogContent
          title="Upgrade the activity"
          description="A new notice version from the version you choose; the link moves to it. Consents already given keep their text."
          size="lg"
        >
          {upgrading && <UpgradeForm activity={a} onDone={() => setUpgrading(false)} />}
        </DialogContent>
      </Dialog>
      <CloseDialog activity={a} open={closing} onOpenChange={setClosing} />
    </>
  );
}

function LinkCard({ activity: a }: { activity: HrActivityDetail }) {
  const toast = useToast();
  const remint = useRemintLink();
  const revoke = useRevokeLink();
  const link = a.link;
  return (
    <Card>
      <CardHeader>
        <CardTitle>The link</CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          One open link for the activity. Anyone with it can open the consent form.
        </p>
      </CardHeader>
      <CardBody className="space-y-3">
        {!link ? (
          <p className="text-sm text-text-muted">No link.</p>
        ) : (
          <>
            <DescriptionList>
              <DescriptionItem term="Status">{link.status}</DescriptionItem>
              <DescriptionItem term="Signs people in">
                {link.audience_mode === "sso"
                  ? "with their organisation account (employees)"
                  : "with a one-time code"}
              </DescriptionItem>
              <DescriptionItem term="Works until">{formatDateTime(link.expires_at)}</DescriptionItem>
              <DescriptionItem term="Opened">{link.use_count} times</DescriptionItem>
            </DescriptionList>
            {link.url_path && (
              <p className="truncate rounded-md border border-border p-2">
                <Mono className="text-xs">{link.url_path}</Mono>
              </p>
            )}
            {link.status === "active" && (
              <div className="flex flex-wrap gap-2">
                <CopyLinkButton link={{ url_path: link.url_path, status: link.status as "active" }} />
                <Button
                  variant="secondary"
                  size="sm"
                  loading={remint.isPending}
                  onClick={async () => {
                    try {
                      await remint.mutateAsync(link.link_uuid);
                      toast.success("Link replaced", "The old one no longer works.");
                    } catch (err) {
                      toast.error("Not replaced", messageOf(err, "The server refused."));
                    }
                  }}
                >
                  Replace
                </Button>
                <Button
                  variant="subtle"
                  size="sm"
                  loading={revoke.isPending}
                  onClick={async () => {
                    try {
                      await revoke.mutateAsync(link.link_uuid);
                      toast.success("Link revoked");
                    } catch (err) {
                      toast.error("Not revoked", messageOf(err, "The server refused."));
                    }
                  }}
                >
                  Revoke
                </Button>
              </div>
            )}
          </>
        )}
      </CardBody>
    </Card>
  );
}

function UpgradeForm({ activity: a, onDone }: { activity: HrActivityDetail; onDone: () => void }) {
  const toast = useToast();
  const options = useActivityOptions();
  const upgrade = useUpgradeHrActivity(a.activity_uuid);
  const category = (options.data ?? []).find((c) => c.category_uuid === a.category_uuid);
  const [versionUuid, setVersionUuid] = React.useState(a.version_uuid);
  const [chosen, setChosen] = React.useState<string[]>([]);
  const [description, setDescription] = React.useState(a.description ?? "");
  const version = category?.versions.find((v) => v.version_uuid === versionUuid);
  const purposeUuids = version
    ? version.purposes
        .filter((p) => p.is_mandatory || chosen.includes(p.purpose_uuid))
        .map((p) => p.purpose_uuid)
    : [];

  async function submit() {
    try {
      const done = await upgrade.mutateAsync({
        template_version_uuid: versionUuid,
        purpose_uuids: purposeUuids,
        description: description.trim(),
      });
      toast.success(
        `Now on version ${done.version}`,
        done.reconsent_requested
          ? `${done.reconsent_requested} participant(s) asked to consent again.`
          : undefined,
      );
      onDone();
    } catch (err) {
      toast.error("Not upgraded", messageOf(err, "The server refused."));
    }
  }

  if (options.isLoading) return <Skeleton className="h-40" />;
  if (!category)
    return <Alert tone="info">This category has no approved version you can use.</Alert>;
  return (
    <div className="space-y-4">
      <Field label="Template version" required>
        {(p) => (
          <Select
            {...p}
            value={versionUuid}
            onChange={(e) => {
              setVersionUuid(e.target.value);
              setChosen([]);
            }}
          >
            {category.versions.map((v) => (
              <option key={v.version_uuid} value={v.version_uuid}>
                {v.template_code} v{v.version}
                {v.reconsent_required ? " · asks participants again" : ""}
              </option>
            ))}
          </Select>
        )}
      </Field>
      {version && <PurposePicker version={version} chosen={chosen} onChange={setChosen} />}
      <Field label="Description" hint={version?.slot_guidance ?? undefined} required>
        {(p) => (
          <Textarea
            {...p}
            rows={4}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        )}
      </Field>
      <DialogFooter>
        <Button variant="ghost" onClick={onDone}>
          Cancel
        </Button>
        <Button
          variant="primary"
          disabled={!version || !description.trim()}
          loading={upgrade.isPending}
          onClick={submit}
        >
          Upgrade
        </Button>
      </DialogFooter>
    </div>
  );
}

function CloseDialog({
  activity: a,
  open,
  onOpenChange,
}: {
  activity: HrActivityDetail;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const toast = useToast();
  const close = useCloseHrActivity(a.activity_uuid);
  return (
    <ConfirmDialog
      open={open}
      onOpenChange={onOpenChange}
      title={`Close ${a.name}?`}
      consequence="Its link stops working at once. Consents already given stand, and the register stays."
      confirmLabel="Close the activity"
      loading={close.isPending}
      onConfirm={async () => {
        try {
          await close.mutateAsync(null);
          toast.success("Activity closed");
          onOpenChange(false);
        } catch (err) {
          toast.error("Not closed", messageOf(err, "The server refused."));
        }
      }}
    />
  );
}
