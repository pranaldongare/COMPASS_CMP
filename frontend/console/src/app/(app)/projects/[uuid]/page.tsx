/**
 * Project detail.
 *
 * The transition controls are the interesting part. They are rendered entirely
 * from `GET /projects/{uuid}/transitions`: which transitions exist for this role,
 * whether each is currently allowed, and what is blocking the ones that are not.
 *
 * A blocked transition is shown as a *disabled button with its reason*, not
 * hidden. Hiding it leaves the user wondering why the thing they were told to do
 * is not there; showing the blocker tells them what to fix.
 */
"use client";

import {
  ArrowLeft,
  Copy,
  Download,
  FileCheck,
  FileStack,
  History as HistoryIcon,
  Info,
  Link2,
  MapPin,
  ScrollText,
  ShieldCheck,
  Upload,
  Database,
  UserCog,
  ArrowLeftRight,
  FolderKanban,
  LayoutGrid,
  Settings2,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import * as React from "react";

import { AuditTrailLink } from "@/components/data-display/audit-link";
import { useReturnTo, withFrom } from "@/lib/navigation/return-to";
import { PageHeader } from "@/components/layout/app-shell";
import { RecordHeader } from "@/components/layout/record-header";
import { Tab, TabList, TabPanel, Tabs, useHashTab } from "@/components/ui/tabs";
import { TransitionControls } from "@/features/projects/components/transition-controls";
import {
  AgentForm,
  ApprovalForm,
  AssignSiteDcoDialog,
  AssignSiteOwnerDialog,
  OverrideBadge,
  ProjectForm,
  ProjectProcessors,
  SiteForm,
  SiteOwner,
} from "@/features/projects/components";
import type { ConsentLink, SiteWithOwner } from "@/types";
import { ExportForm } from "@/features/exchange/components/export-form";
import {
  ProjectCollectionsCard as CollectionsCard,
  ProjectExportsCard as ExportsCard,
} from "@/features/exchange/components/project-exchanges";
import {
  NoticeCopyForm,
  NoticeForm,
  NoticeImportForm,
} from "@/features/notices/components";
import { UseTemplateForm } from "@/features/notice-templates/components/use-template-form";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  EmptyState,
  Mono,
  Skeleton,
} from "@/components/ui/primitives";
import { StatusBadge } from "@/components/ui/status";
import { useLinks } from "@/features/consent";
import { useNotices } from "@/features/notices";
import {
  CopyLinkButton,
  ProjectConsents,
  ReplaceLinkDialog,
} from "@/features/consent/components";
import {
  downloadApprovalProof,
  useApprovals,
  useProject,
  useProjectHistory,
  useProjectSummary,
  useSites,
} from "@/features/projects";
import { formatDate, formatDateTime, humanise, saveBlob, shortHash } from "@/lib/format";
import { useAuth, useToast } from "@/providers";

type Sheet =
  | { kind: "edit" }
  | { kind: "site" }
  | { kind: "notice" }
  | { kind: "notice-copy" }
  | { kind: "notice-template" }
  | { kind: "notice-import" }
  | { kind: "approval" }
  | { kind: "export" }
  | { kind: "agent"; siteUuid: string; siteLabel: string };

/**
 * The project as one workspace (UX review 2026-10-05). The fragment names the
 * tab, so a tab can be linked to and survives a reload; the anchors of the
 * cards inside a tab open it too, which keeps every `#notices` and `#sites`
 * written before the tabs - the dashboard's rows, a notice's way back -
 * landing on the card they meant.
 */
/** The counts the summary card shows; "At a glance" leaves them out. */
const SUMMARY_COUNTS = new Set(["notices", "sites", "active_links"]);

const TABS = ["overview", "setup", "consent", "exchanges", "activity"] as const;
type ProjectTab = (typeof TABS)[number];
const SECTIONS: Record<string, ProjectTab> = {
  notices: "setup",
  approvals: "setup",
  sites: "consent",
  links: "consent",
  consents: "consent",
  collections: "exchanges",
  exports: "exchanges",
  history: "activity",
};
/** Where each "At a glance" figure's records are. */
const COUNT_SECTION: Record<string, string> = {
  notices: "notices",
  purposes: "notices",
  approvals: "approvals",
  sites: "sites",
  active_links: "links",
  collections: "collections",
  exports: "exports",
};

export default function ProjectDetailPage() {
  const params = useParams<{ uuid: string }>();
  const uuid = params.uuid;
  const { me } = useAuth();
  // The list this project was opened from, as it was filtered; a link from
  // anywhere else falls back to every project.
  const fromList = useReturnTo(["/projects"]);
  const allProjects =
    fromList && !fromList.startsWith("/projects/") ? fromList : "/projects";
  const [sheet, setSheet] = React.useState<Sheet | null>(null);
  const close = () => setSheet(null);

  const project = useProject(uuid);
  const summary = useProjectSummary(uuid);
  const history = useProjectHistory(uuid);
  const notices = useNotices(uuid);
  const sites = useSites(uuid);
  // Only for the roles that may read them. An R&D User owns the project but
  // holds no grant on `link`, so asking anyway answered 403 on every visit to
  // every project page - a red line in their console and an audited denial in
  // ours, for a card they cannot see. `writes` comes from the server, so this
  // is not a second copy of the permission matrix.
  const canReadLinks = me?.writes.includes("link") ?? false;
  // The project's consents, listed on its Consent tab, for whoever reads them.
  const canReadConsents = me?.nav.includes("consents") ?? false;
  const [consentStatus, setConsentStatus] = React.useState("");
  const links = useLinks(canReadLinks ? uuid : undefined);

  /** The live link for a site, if it has one. At most one by design. */
  const activeLinkFor = React.useCallback(
    (siteUuid: string) =>
      (links.data ?? []).find((l) => l.site_uuid === siteUuid && l.status === "active"),
    [links.data],
  );

  // Above the early returns: a hook after one runs in a different order on
  // the render that takes the branch, which React refuses.
  const [assigning, setAssigning] = React.useState<SiteWithOwner | null>(null);
  const [namingDco, setNamingDco] = React.useState<SiteWithOwner | null>(null);
  const [replacing, setReplacing] = React.useState<ConsentLink | null>(null);

  const [tab, setTab, hash] = useHashTab(TABS, "overview", SECTIONS);
  const loaded = Boolean(project.data);
  // A fragment naming a card, not a tab: the tab is open by now, so bring the
  // card itself into view - the browser's own jump ran before it existed.
  React.useEffect(() => {
    if (!loaded || !Object.hasOwn(SECTIONS, hash)) return;
    document.getElementById(hash)?.scrollIntoView?.({ block: "start" });
  }, [hash, loaded]);

  if (project.isLoading) return <DetailSkeleton />;

  if (project.error) {
    return (
      <Alert tone="danger" title="Could not load this project">
        {project.error.isNotFound
          ? "This project does not exist, or it is outside your scope."
          : project.error.userMessage()}
      </Alert>
    );
  }

  const p = project.data!;

  // Mirrors the server's permission matrix. The API is the authority - these
  // only decide whether a control is worth rendering, never whether it is
  // permitted, and every one of them is re-checked server-side.
  const isDpo = me?.role === "dpo";
  const isOwner = me?.role === "rnd_user";
  // The R&D User is included because they are the one who knows where collection
  // will physically happen. Leaving it to the DPO meant the DPO inventing a site
  // to get past their own publication screen.
  // The R&D User knows where collection will happen; the DCO Admin and the RCO
  // register the sites they are about to route. Widened on the API first, and
  // this is the button that had to follow it — without it the DCO Admin's whole
  // job was unreachable from the project they were meant to do it on.
  const canAddSite =
    isDpo ||
    me?.role === "dco" ||
    me?.role === "dco_admin" ||
    me?.role === "rco" ||
    isOwner;
  // Minting a Field Agent link stays with the DPO and DCO: it is a credential
  // for the collection floor, not a project-setup step.
  // Whoever is accountable for collection at a site. Three roles now, not one:
  // an RCO was refused a consent link for their own lab because this list — and
  // the API gate behind it — predated them. Which *site* each may act on is
  // enforced server-side by the site scope, so this only decides whether the
  // control is worth rendering.
  const isCollectionOwner =
    me?.role === "dco" || me?.role === "rco" || me?.role === "dco_admin";
  const canManageSites = isDpo || isCollectionOwner;
  // Mirrors the server's rule in `projects.service.add_approval`. Draft is
  // where an approval is attached now: submitting for review *requires* one, so
  // it has to be possible before submitting. Still open while pending, because
  // a DPO asking for a second sign-off should not need the project sent back.
  const canUploadApproval =
    p.project_status === "in_draft" ||
    p.project_status === "under_process" ||
    p.project_status === "pending_approval";
  // Attaching a source is the routing step. The DCO Admin does it on
  // third-party collection, the R&D owner on in-house; the DPO and an
  // administrator can correct either. A DCO is deliberately absent - reassigning
  // their own sites would let them hand themselves somebody else's project.
  const canAssignSiteOwner =
    isDpo || me?.role === "admin" || me?.role === "dco_admin" || isOwner;
  const canExport = isDpo || isCollectionOwner;
  // An R&D User reads their own project's collections; `nav` is the server's
  // word on it, as `writes` is for links above.
  const canReadCollections = me?.nav.includes("collections") ?? false;
  // The R&D User writes the notice now: they are the one who knows what the
  // study collects and why. The DPO keeps the same control and reviews it.
  const canAuthorNotice = isDpo || isOwner;
  const noticePublished = Boolean(p.current_notice_uuid);

  // Only the project's own controls sit under the title. Every other action
  // lives on the card it changes - a notice upload on the notices card, a site
  // on the sites card - and nowhere else: the page used to carry each one up to
  // three times (header, card, and a repeat at the foot), which read as three
  // different things to choose between (UX review 2026-10-05).
  const projectActions = (
    <div className="flex flex-wrap items-center gap-2">
      <AuditTrailLink entityType="project" uuid={p.project_uuid} label={p.project_name} />
      {/* Editing is permitted only while the project is in draft. */}
      {isOwner && p.project_status === "in_draft" && (
        <Button variant="secondary" size="sm" onClick={() => setSheet({ kind: "edit" })}>
          Edit
        </Button>
      )}
    </div>
  );

  // How a notice arrives, in the order it usually does. The first is how one
  // actually comes: drafted in Word by the people whose job that is; typing it
  // in again is where the notice and the document it was approved as start to
  // differ. Most projects are a variation on one that already exists, and the
  // server copies rather than shares - a notice belongs to one project.
  // Composing one from nothing is the Privacy Office's alone; the API refuses
  // it to anybody else either way.
  const noticeActions = (primary: boolean) => (
    <div className={`flex flex-wrap items-center gap-2 ${primary ? "justify-center" : ""}`}>
      <Button
        variant={primary ? "primary" : "secondary"}
        size="sm"
        onClick={() => setSheet({ kind: "notice-import" })}
      >
        <Upload className="size-4" />
        Upload a notice document
      </Button>
      <Button
        variant="secondary"
        size="sm"
        onClick={() => setSheet({ kind: "notice-copy" })}
      >
        <Copy className="size-4" />
        Copy an existing notice
      </Button>
      <Button
        variant="secondary"
        size="sm"
        onClick={() => setSheet({ kind: "notice-template" })}
      >
        <FileStack className="size-4" />
        Use a notice template
      </Button>
      {isDpo && (
        <Button variant="secondary" size="sm" onClick={() => setSheet({ kind: "notice" })}>
          <ScrollText className="size-4" />
          New notice
        </Button>
      )}
    </div>
  );

  const addSite = (
    <Button variant="secondary" size="sm" onClick={() => setSheet({ kind: "site" })}>
      <MapPin className="size-4" />
      Add site
    </Button>
  );

  // Which "At a glance" figures lead somewhere this person can see. A count
  // whose records sit in a card their role does not get stays a number.
  const reachable = new Set<string>([
    "notices",
    "approvals",
    "sites",
    ...(canReadLinks ? ["links"] : []),
    ...(canReadCollections ? ["collections"] : []),
    ...(canExport ? ["exports"] : []),
  ]);

  return (
    <>
      {/* The trail, then the project's summary card (2026-10-10, the detail
          look the user settled on): its name, status and controls over four
          key figures, each opening the records it counts. */}
      <PageHeader
        heading={false}
        breadcrumb={
          <Link
            href={allProjects}
            className="inline-flex items-center gap-1 hover:text-text"
          >
            <ArrowLeft className="size-3.5" aria-hidden="true" />
            All projects
          </Link>
        }
        title={p.project_name}
      />
      <RecordHeader
        icon={FolderKanban}
        title={p.project_name}
        meta={
          <>
            <StatusBadge kind="project" value={p.project_status} />
            <span>
              {[p.internal_project_name, p.requesting_team].filter(Boolean).join(" · ")}
            </span>
          </>
        }
        actions={projectActions}
        facts={[
          {
            label: "Consents",
            value: summary.data?.consents.total ?? "—",
            icon: FileCheck,
            tint: 0,
            href: canReadConsents ? "#consents" : undefined,
          },
          {
            label: "Notices",
            value: summary.data?.counts.notices ?? "—",
            icon: ScrollText,
            tint: 3,
            href: "#notices",
          },
          {
            label: "Active links",
            value: summary.data?.counts.active_links ?? "—",
            icon: Link2,
            tint: 2,
            href: canReadLinks ? "#links" : undefined,
          },
          {
            label: "Sites",
            value: summary.data?.counts.sites ?? "—",
            icon: MapPin,
            tint: 1,
            href: "#sites",
          },
        ]}
      />

      <Tabs value={tab} onValueChange={setTab} label="Project sections" layout="underline">
        <TabList>
          <Tab value="overview" icon={LayoutGrid}>
            Overview
          </Tab>
          <Tab value="setup" icon={Settings2}>
            Setup
          </Tab>
          <Tab value="consent" icon={FileCheck} count={sites.data?.length}>
            Consent
          </Tab>
          <Tab value="exchanges" icon={ArrowLeftRight}>
            Collections &amp; exchanges
          </Tab>
          <Tab value="activity" icon={HistoryIcon} count={history.data?.length}>
            Activity
          </Tab>
        </TabList>

        <TabPanel value="overview">
          <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_20rem] lg:items-start">
            <div className="min-w-0 space-y-5">
              {/* The move this person can make next, or exactly what blocks it. */}
              <TransitionControls
                projectUuid={uuid}
                currentStatus={p.project_status}
                noticeUuid={p.current_notice_uuid ?? notices.data?.[0]?.notice_uuid}
              />
              <Card>
                <CardHeader className="flex items-center gap-2">
                  <Info className="size-4 text-text-subtle" aria-hidden="true" />
                  <CardTitle>Project details</CardTitle>
                </CardHeader>
                <dl className="grid gap-x-5 gap-y-4 p-5 sm:grid-cols-2 xl:grid-cols-3">
                  {(
                    [
                      ["Internal name", p.internal_project_name ?? "—"],
                      ["Requesting team", p.requesting_team ?? "—"],
                      ["Data Collection Owner", p.dco_name ?? "Not assigned"],
                      ["Created by", p.created_by_name ?? "—"],
                      ["Created", formatDateTime(p.created_at)],
                      ["Reference", <Mono key="ref">{p.project_uuid}</Mono>],
                    ] as const
                  ).map(([term, value]) => (
                    <div key={term} className="min-w-0">
                      <dt className="mb-1 text-2xs font-semibold tracking-wider text-text-subtle uppercase">
                        {term}
                      </dt>
                      <dd className="text-sm break-words">{value}</dd>
                    </div>
                  ))}
                  {p.description && (
                    <div className="sm:col-span-2 xl:col-span-3">
                      <dt className="mb-1 text-2xs font-semibold tracking-wider text-text-subtle uppercase">
                        Description
                      </dt>
                      <dd className="text-sm text-text-muted">{p.description}</dd>
                    </div>
                  )}
                </dl>
              </Card>
              {summary.isLoading ? (
                <Skeleton className="h-40" />
              ) : summary.data ? (
                <Card>
                  <CardHeader>
                    <CardTitle>At a glance</CardTitle>
                  </CardHeader>
                  <CardBody className="space-y-4">
                    {/* Each figure opens the records it counts (UX review
                    2026-10-05); a number that goes nowhere invites a search. */}
                    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                      {Object.entries(summary.data.counts)
                        // Notices, sites and active links are in the summary
                        // card's strip; they are not counted twice.
                        .filter(([key]) => !SUMMARY_COUNTS.has(key))
                        .map(([key, value]) => {
                          const section = COUNT_SECTION[key];
                          const figure = (
                            <>
                              <span className="block text-xs text-text-subtle">
                                {humanise(key)}
                              </span>
                              <span className="tabular block text-lg font-semibold">
                                {value}
                              </span>
                            </>
                          );
                          return section && reachable.has(section) ? (
                            <a
                              key={key}
                              href={`#${section}`}
                              className="-m-1.5 rounded-lg p-1.5 hover:bg-surface-hover"
                            >
                              {figure}
                            </a>
                          ) : (
                            <div key={key}>{figure}</div>
                          );
                        })}
                    </div>

                    <div className="border-t border-border pt-3">
                      <p className="mb-2 text-xs font-medium tracking-wide text-text-subtle uppercase">
                        Consent
                      </p>
                      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
                        {Object.entries(summary.data.consents).map(([key, value]) => {
                          const figure = (
                            <>
                              <p className="text-xs text-text-subtle">{humanise(key)}</p>
                              <p className="tabular text-lg font-semibold">{value}</p>
                            </>
                          );
                          // Each figure opens the list below, narrowed to what it counted.
                          return canReadConsents ? (
                            <a
                              key={key}
                              href="#consents"
                              onClick={() => setConsentStatus(key === "total" ? "" : key)}
                              className="-m-1.5 rounded-lg p-1.5 hover:bg-surface-hover"
                            >
                              {figure}
                            </a>
                          ) : (
                            <div key={key}>{figure}</div>
                          );
                        })}
                      </div>
                    </div>
                  </CardBody>
                </Card>
              ) : null}
            </div>

            {/* The latest of the project's history, beside the details. */}
            <Card>
              <CardHeader className="flex items-center gap-2">
                <HistoryIcon className="size-4 text-text-subtle" aria-hidden="true" />
                <CardTitle>Activity</CardTitle>
              </CardHeader>
              {history.isLoading ? (
                <CardBody>
                  <Skeleton className="h-24" />
                </CardBody>
              ) : history.data && history.data.length > 0 ? (
                <ol className="space-y-3.5 px-5 py-4">
                  {history.data.slice(0, 5).map((entry) => (
                    <li key={entry.history_uuid} className="flex gap-3">
                      <span
                        aria-hidden="true"
                        className="mt-1.5 size-2 shrink-0 rounded-full bg-accent ring-4 ring-accent-subtle"
                      />
                      <div className="min-w-0 text-sm">
                        <p>
                          {entry.from_status
                            ? `${humanise(entry.from_status)} → ${humanise(entry.to_status)}`
                            : `Created as ${humanise(entry.to_status)}`}
                        </p>
                        <p className="text-xs text-text-subtle">
                          {formatDateTime(entry.occurred_at)} · {entry.actor_name}
                        </p>
                      </div>
                    </li>
                  ))}
                </ol>
              ) : (
                <CardBody className="text-sm text-text-muted">Nothing yet.</CardBody>
              )}
              {(history.data?.length ?? 0) > 5 && (
                <div className="border-t border-border px-5 py-2.5">
                  <Button variant="ghost" size="sm" onClick={() => setTab("activity")}>
                    See all {history.data?.length}
                  </Button>
                </div>
              )}
            </Card>
          </div>
        </TabPanel>

        <TabPanel value="setup" className="space-y-6">
          <ProjectProcessors
            projectUuid={uuid}
            projectStatus={p.project_status}
            canRequest={isOwner}
            canDecide={isDpo}
          />

          {/* `#notices`: where a notice opened from this project comes back to. */}
          <Card id="notices" className="scroll-mt-20">
            <CardHeader className="flex flex-wrap items-center justify-between gap-2">
              <CardTitle>Notices</CardTitle>
              {/* Once there is a notice, a new version starts here. Before
                  that the empty state below offers the same, and one place to
                  start is enough. */}
              {canAuthorNotice && Boolean(notices.data?.length) && noticeActions(false)}
            </CardHeader>
            {notices.isLoading ? (
              <CardBody>
                <Skeleton className="h-16" />
              </CardBody>
            ) : notices.isError ? (
              /* A failed query is not an empty project. Without this branch the
                 two were the same screen, and a 500 on this list read as "the
                 notice you just uploaded was not saved" - which sent people
                 looking for the fault in the upload. */
              <CardBody>
                <Alert tone="danger" title="Could not load this project's notices">
                  {notices.error.userMessage()}
                </Alert>
              </CardBody>
            ) : !notices.data?.length ? (
              <EmptyState
                title="No notice yet"
                description={
                  canAuthorNotice
                    ? "Upload the filled-in notice document and its purposes are created with it. A project cannot leave draft without a notice carrying at least one purpose and every Rule 3 element."
                    : "A project cannot leave draft without a notice carrying at least one purpose and every Rule 3 element."
                }
                action={canAuthorNotice ? noticeActions(true) : undefined}
              />
            ) : (
              <ul className="divide-y divide-border">
                {notices.data.map((notice) => (
                  <li key={notice.notice_uuid}>
                    <Link
                      href={withFrom(
                        `/notices/${notice.notice_uuid}`,
                        `/projects/${uuid}#notices`,
                      )}
                      className="flex items-center justify-between gap-4 px-5 py-3 hover:bg-surface-hover"
                    >
                      <div className="min-w-0">
                        <p className="text-sm font-medium">
                          {notice.notice_code}{" "}
                          <span className="text-text-subtle">v{notice.version}</span>
                        </p>
                        <p className="mt-0.5 text-xs text-text-muted">
                          {notice.purpose_count ?? 0}{" "}
                          {notice.purpose_count === 1 ? "purpose" : "purposes"} ·{" "}
                          {notice.language_count ?? 0} language(s)
                          {notice.published_at &&
                            ` · published ${formatDateTime(notice.published_at)}`}
                        </p>
                      </div>
                      <StatusBadge kind="notice" value={notice.status} />
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <ApprovalsCard
            projectUuid={uuid}
            canUpload={isOwner && canUploadApproval}
            // Passed so the empty state can say *why* there is no upload
            // control, rather than leaving somebody to conclude the feature is
            // missing or that they lack the permission.
            projectStatus={p.project_status}
            onUpload={() => setSheet({ kind: "approval" })}
          />
        </TabPanel>

        <TabPanel value="consent" className="space-y-6">
          {/* Said where a site is added, which is the moment it matters. */}
          {p.project_status === "approved" && canAddSite && (
            <Alert tone="info">
              <p className="flex items-start gap-2">
                <Info className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                <span>
                  Adding a site now is a material change: it adds a recipient to a published
                  notice, so it requires a new notice version before collection starts
                  there.
                </span>
              </p>
            </Alert>
          )}

          {/* `#sites`: where a dashboard row about a site lands. */}
          <Card id="sites" className="scroll-mt-20">
            <CardHeader className="flex flex-wrap items-center justify-between gap-2">
              <CardTitle>Collection sites</CardTitle>
              {canAddSite && Boolean(sites.data?.length) && addSite}
            </CardHeader>
            {sites.isLoading ? (
              <CardBody>
                <Skeleton className="h-16" />
              </CardBody>
            ) : !sites.data?.length ? (
              <EmptyState
                title="No sites yet"
                description="Sites are the recipients named in the notice. Collection cannot start at a site that is not registered here, and a notice with none says so in its recipient line."
                action={canAddSite ? addSite : undefined}
              />
            ) : (
              <ul className="divide-y divide-border">
                {sites.data.map((site) => (
                  <li
                    key={site.site_uuid}
                    className="flex flex-col gap-3 px-5 py-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium">{site.site_label}</p>
                      <p className="mt-0.5 text-xs text-text-muted">
                        {site.location ?? "Location not recorded"}
                        {site.processor_name && ` · operated by ${site.processor_name}`}
                      </p>
                      {/* Who is accountable, and whether this is the site the
                          project follows. A project spanning three campuses run
                          by three people needs to say which one decides. */}
                      <div className="mt-1 flex flex-wrap items-center gap-1.5">
                        <SiteOwner site={site} />
                        {/* Says the owner is a named exception rather than the
                            source's. Without it the two read identically and
                            nobody can tell the rig has a different owner. */}
                        <OverrideBadge site={site} />
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      {typeof site.active_links === "number" && site.active_links > 0 && (
                        <span className="text-xs text-text-subtle">
                          {site.active_links} active link(s)
                        </span>
                      )}
                      <StatusBadge kind="record" value={site.status} />
                      {/* Two controls, deliberately worded apart. "Data source"
                          attaches the rig and picks its owner; "Who runs it"
                          names somebody for this site alone and leaves the rig
                          where it is. Somebody reaching for the wrong one would
                          move three studies believing they had moved one.

                          A DCO holds neither: reassigning their own sites would
                          let them hand themselves somebody else's project. */}
                      {canAssignSiteOwner && site.status === "active" && (
                        <>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setAssigning(site)}
                          >
                            <Database className="size-4" />
                            {site.source_uuid ? "Change source" : "Attach source"}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setNamingDco(site)}
                            disabled={!site.source_uuid}
                            title={
                              site.source_uuid
                                ? undefined
                                : "Attach a data source first — that picks the owner"
                            }
                          >
                            <UserCog className="size-4" />
                            Who runs it
                          </Button>
                        </>
                      )}
                      {/* A link may only exist for an approved project, so the
                          control is absent until it is.

                          Which control depends on whether one already exists.
                          Minting a second for a site that has a live one leaves
                          two working URLs and only one of them tracked — the
                          Links page has always guarded that, and this page did
                          not.

                          The token is shown once at mint and never stored, so
                          "I need the URL again" has exactly one honest answer:
                          replace it. The button says so rather than leaving
                          somebody hunting for a copy affordance that cannot
                          exist. */}
                      {canManageSites &&
                        site.status === "active" &&
                        p.project_status === "approved" &&
                        (activeLinkFor(site.site_uuid) ? (
                          <>
                            {/* Copy without leaving the project. Falls back to
                                "URL not kept" for links minted before they were
                                recoverable, which offers the replace instead. */}
                            <CopyLinkButton
                              link={activeLinkFor(site.site_uuid)!}
                              onReplace={() => setReplacing(activeLinkFor(site.site_uuid)!)}
                            />
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setReplacing(activeLinkFor(site.site_uuid)!)}
                              title="Revoke this link and issue a fresh one. Use it if the URL has circulated further than intended."
                            >
                              <Link2 className="size-4" />
                              Replace link
                            </Button>
                          </>
                        ) : (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() =>
                              setSheet({
                                kind: "agent",
                                siteUuid: site.site_uuid,
                                siteLabel: site.site_label,
                              })
                            }
                          >
                            <Link2 className="size-4" />
                            Create link
                          </Button>
                        ))}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          {canReadLinks && (
            <Card id="links" className="scroll-mt-20">
              <CardHeader>
                <CardTitle>Consent links</CardTitle>
              </CardHeader>
              {links.isLoading ? (
                <CardBody>
                  <Skeleton className="h-16" />
                </CardBody>
              ) : !links.data?.length ? (
                <CardBody className="text-sm text-text-muted">
                  {p.project_status === "approved"
                    ? "No link yet. Create one from a site above."
                    : "A link can only be created once the project is approved."}
                </CardBody>
              ) : (
                <ul className="divide-y divide-border">
                  {links.data.map((link) => (
                    <li key={link.link_uuid} className="px-5 py-3">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-sm font-medium">{link.site_label}</p>
                        <StatusBadge kind="link" value={link.status} />
                      </div>
                      <p className="mt-1 text-xs text-text-muted">
                        {link.use_count}
                        {link.max_uses !== null && ` of ${link.max_uses}`} used · expires{" "}
                        {formatDateTime(link.expires_at)}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          )}

          {canReadConsents && (
            <ProjectConsents
              projectUuid={uuid}
              sites={sites.data ?? []}
              status={consentStatus}
              onStatus={setConsentStatus}
            />
          )}
        </TabPanel>

        <TabPanel value="exchanges" className="space-y-6">
          {canReadCollections && (
            <CollectionsCard projectUuid={uuid} from={`/projects/${uuid}#collections`} />
          )}
          {canExport && (
            <ExportsCard
              projectUuid={uuid}
              canGenerate={p.project_status === "approved"}
              onGenerate={() => setSheet({ kind: "export" })}
            />
          )}
          {!canReadCollections && !canExport && (
            <Card>
              <CardBody className="text-sm text-text-muted">
                Collections and exports are handled by the collection owners for this
                project.
              </CardBody>
            </Card>
          )}
        </TabPanel>

        <TabPanel value="activity">
          <Card id="history" className="scroll-mt-20">
            <CardHeader className="flex items-center justify-between">
              <div>
                <CardTitle>History</CardTitle>
                <p className="mt-0.5 text-xs text-text-muted">
                  Append-only. Every transition, who made it, and why.
                </p>
              </div>
              <HistoryIcon className="size-4 text-text-subtle" aria-hidden="true" />
            </CardHeader>
            {history.isLoading ? (
              <CardBody>
                <Skeleton className="h-24" />
              </CardBody>
            ) : (
              <ol className="divide-y divide-border">
                {history.data?.map((entry) => (
                  <li key={entry.history_uuid} className="px-5 py-3">
                    <div className="flex flex-wrap items-center gap-2 text-sm">
                      {entry.from_status ? (
                        <>
                          <StatusBadge
                            kind="project"
                            value={entry.from_status}
                            dot={false}
                          />
                          <span aria-hidden="true" className="text-text-subtle">
                            →
                          </span>
                        </>
                      ) : (
                        <span className="text-text-subtle">Created as</span>
                      )}
                      <StatusBadge kind="project" value={entry.to_status} dot={false} />
                    </div>
                    <p className="mt-1 text-xs text-text-muted">
                      {entry.actor_name} ({humanise(entry.actor_role)}) ·{" "}
                      {formatDateTime(entry.occurred_at)}
                    </p>
                    {entry.reason && (
                      <p className="mt-1 rounded bg-bg-inset px-2 py-1 text-xs text-text">
                        “{entry.reason}”
                      </p>
                    )}
                  </li>
                ))}
              </ol>
            )}
          </Card>
        </TabPanel>
      </Tabs>

      <Dialog open={sheet?.kind === "edit"} onOpenChange={(o) => !o && close()}>
        <DialogContent title="Edit project" description="Drafts only.">
          <ProjectForm project={p} onDone={close} />
        </DialogContent>
      </Dialog>

      <Dialog open={sheet?.kind === "notice"} onOpenChange={(o) => !o && close()}>
        <DialogContent
          title="New notice"
          description="Every Rule 3 element is required before it can be published."
          size="lg"
        >
          <NoticeForm projectUuid={uuid} onDone={close} />
        </DialogContent>
      </Dialog>

      <Dialog open={sheet?.kind === "site"} onOpenChange={(o) => !o && close()}>
        <DialogContent title="Add a collection site">
          <SiteForm projectUuid={uuid} noticePublished={noticePublished} onDone={close} />
        </DialogContent>
      </Dialog>

      <Dialog open={sheet?.kind === "notice-import"} onOpenChange={(o) => !o && close()}>
        <DialogContent
          title="Upload a notice document"
          description="The filled-in .docx template. Its purpose table becomes the notice's purposes, which the DPO then activates."
          size="lg"
        >
          <NoticeImportForm projectUuid={uuid} onDone={close} />
        </DialogContent>
      </Dialog>

      <Dialog open={sheet?.kind === "notice-copy"} onOpenChange={(o) => !o && close()}>
        <DialogContent
          title="Copy an existing notice"
          description="Copies the wording, the purposes and every language rendition into this project as a fresh draft."
        >
          <NoticeCopyForm projectUuid={uuid} onDone={close} />
        </DialogContent>
      </Dialog>

      <Dialog open={sheet?.kind === "notice-template"} onOpenChange={(o) => !o && close()}>
        <DialogContent
          title="Use a notice template"
          description="A notice the Privacy Office wrote ahead of the project. Enter the ID they gave you."
        >
          <UseTemplateForm projectUuid={uuid} onDone={close} />
        </DialogContent>
      </Dialog>

      <Dialog open={sheet?.kind === "approval"} onOpenChange={(o) => !o && close()}>
        <DialogContent
          title="Upload an approval"
          description="The proof file is mandatory - an approval without one does not unlock the transition."
        >
          <ApprovalForm projectUuid={uuid} onDone={close} />
        </DialogContent>
      </Dialog>

      <Dialog open={sheet?.kind === "export"} onOpenChange={(o) => !o && close()}>
        <DialogContent title="Generate an export">
          <ExportForm projectUuid={uuid} onDone={close} />
        </DialogContent>
      </Dialog>

      <Dialog open={sheet?.kind === "agent"} onOpenChange={(o) => !o && close()}>
        <DialogContent
          title={
            sheet?.kind === "agent" ? `Consent link for ${sheet.siteLabel}` : "Consent link"
          }
          description="The token is shown once and cannot be retrieved again."
        >
          {sheet?.kind === "agent" && (
            <AgentForm siteUuid={sheet.siteUuid} onDone={close} />
          )}
        </DialogContent>
      </Dialog>
      <AssignSiteOwnerDialog
        site={assigning}
        projectUuid={uuid}
        onClose={() => setAssigning(null)}
      />
      <AssignSiteDcoDialog site={namingDco} onClose={() => setNamingDco(null)} />
      <ReplaceLinkDialog link={replacing} onClose={() => setReplacing(null)} />
    </>
  );
}

function DetailSkeleton() {
  return (
    <div className="min-w-0 space-y-6">
      <Skeleton className="h-8 w-72" />
      <Skeleton className="h-4 w-96" />
      <Skeleton className="h-10 w-full max-w-xl" />
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="min-w-0 space-y-6 lg:col-span-2">
          <Skeleton className="h-40" />
          <Skeleton className="h-48" />
        </div>
        <Skeleton className="h-64" />
      </div>
    </div>
  );
}

/* ==================================================================== approvals */

/**
 * The approvals already on this project, and their proof files.
 *
 * The R&D User uploads a security approval to unlock `in_draft ->
 * pending_approval`, and until now the page gave them an upload button and no
 * way to see what they had already uploaded — so the honest reading of the
 * screen was "nothing is here", which sent people uploading it twice.
 *
 * The proof download compares the hash the server served against the one
 * recorded at upload. A mismatch means the stored file is not the file that was
 * approved, and that is worth interrupting somebody about.
 */
function ApprovalsCard({
  projectUuid,
  canUpload,
  projectStatus,
  onUpload,
}: {
  projectUuid: string;
  canUpload: boolean;
  projectStatus: string;
  onUpload: () => void;
}) {
  const approvals = useApprovals(projectUuid);
  const toast = useToast();
  const [busy, setBusy] = React.useState<string | null>(null);

  const items = approvals.data ?? [];

  async function download(uuid: string, reference: string, recorded: string) {
    setBusy(uuid);
    try {
      const file = await downloadApprovalProof(uuid);
      saveBlob(file.blob, file.filename || `approval-${reference}`);

      if (file.contentHash && recorded && file.contentHash !== recorded) {
        toast.error(
          "Proof does not match its recorded hash",
          "The stored file differs from what was uploaded. Report this to the Privacy Office.",
        );
      } else {
        toast.success("Proof downloaded", "Hash matches the record.");
      }
    } catch (err) {
      toast.error(
        "Could not download the proof",
        err && typeof err === "object" && "userMessage" in err
          ? (err as { userMessage: () => string }).userMessage()
          : "The request failed.",
      );
    } finally {
      setBusy(null);
    }
  }

  return (
    <Card>
      <CardHeader className="flex items-center justify-between">
        <CardTitle>Approvals</CardTitle>
        <div className="flex items-center gap-2">
          <span className="tabular rounded-full bg-bg-inset px-2.5 py-0.5 text-xs font-medium text-text-muted">
            {items.length}
          </span>
          {/* With none yet, the empty state below offers it instead. */}
          {canUpload && items.length > 0 && (
            <Button variant="ghost" size="sm" onClick={onUpload}>
              <FileCheck className="size-4" />
              Upload
            </Button>
          )}
        </div>
      </CardHeader>

      {approvals.isLoading ? (
        <CardBody>
          <Skeleton className="h-16" />
        </CardBody>
      ) : approvals.error ? (
        <CardBody>
          <Alert tone={approvals.error.isForbidden ? "info" : "danger"}>
            {approvals.error.isForbidden
              ? "Your role does not permit the approvals list."
              : approvals.error.userMessage()}
          </Alert>
        </CardBody>
      ) : items.length === 0 ? (
        <EmptyState
          title="No approval uploaded"
          description={
            canUpload
              ? "A security approval with its proof file is what unlocks the move to pending approval."
              : projectStatus === "in_draft"
                ? "The R&D User who owns this project uploads the security approval and its proof. It is the last thing between the project and review."
                : "Approvals are added while a project is in draft or under review. This one has moved past that."
          }
          action={
            canUpload ? (
              <Button variant="primary" size="sm" onClick={onUpload}>
                Upload an approval
              </Button>
            ) : undefined
          }
        />
      ) : (
        <ul className="divide-y divide-border">
          {items.map((approval) => (
            <li
              key={approval.approval_uuid}
              className="flex flex-wrap items-center justify-between gap-3 px-5 py-3"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium">
                  {humanise(approval.approval_type)}
                  <span className="ml-1.5 font-normal text-text-muted">
                    {approval.reference_no}
                  </span>
                </p>
                <p className="mt-0.5 text-xs text-text-muted">
                  Approved {formatDate(approval.approved_on)} · uploaded{" "}
                  {formatDateTime(approval.uploaded_at)}
                  {approval.uploaded_by_name && ` by ${approval.uploaded_by_name}`}
                </p>
                <p className="mt-1 flex items-center gap-1.5 text-2xs text-text-subtle">
                  <ShieldCheck className="size-3" aria-hidden="true" />
                  <span className="font-mono">{shortHash(approval.proof_file_hash)}</span>
                </p>
              </div>

              <Button
                variant="secondary"
                size="sm"
                loading={busy === approval.approval_uuid}
                onClick={() =>
                  download(
                    approval.approval_uuid,
                    approval.reference_no,
                    approval.proof_file_hash,
                  )
                }
              >
                <Download className="size-4" />
                Proof
              </Button>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
