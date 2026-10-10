/**
 * Notice detail and publication.
 *
 * The publication checklist is the centrepiece. `GET /notices/{uuid}/checklist`
 * returns exactly what is blocking publication, so the DPO sees a list of things
 * to fix rather than a submit button that rejects her with one error at a time.
 *
 * Publication is presented as irreversible, because it is: the text and its hash
 * freeze at that moment, and every consent captured afterwards is consent to
 * exactly those words. A correction is a new version, never an edit.
 *
 * Under the summary card, tabs (2026-10-10): the checklist and the Rule 3
 * elements on Overview, then the text, the purposes and the sign-off. The
 * fragment names the tab, and the cards' old anchors open the tab that holds
 * them, so every "fix this" on the checklist still lands on its card.
 */
"use client";

import {
  AlertTriangle,
  ArrowLeft,
  Check,
  CheckCircle2,
  FileText,
  Globe,
  LayoutGrid,
  ListChecks,
  Lock,
  MapPin,
  Pencil,
  Plus,
  ScrollText,
  SlidersHorizontal,
  StickyNote,
  X,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import * as React from "react";

import { AuditTrailLink } from "@/components/data-display/audit-link";
import { useReturnTo } from "@/lib/navigation/return-to";
import { PageHeader } from "@/components/layout/app-shell";
import { RecordHeader } from "@/components/layout/record-header";
import { Tab, TabList, TabPanel, Tabs, useHashTab } from "@/components/ui/tabs";
import {
  LanguageForm,
  NoticeForm,
  NoticePurposesForm,
} from "@/features/notices/components";
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
  EmptyState,
  Mono,
  Skeleton,
} from "@/components/ui/primitives";
import { StatusBadge } from "@/components/ui/status";
import {
  useNotice,
  useNoticeChecklist,
  useNoticeLanguages,
  useNoticePurposes,
  usePublishNotice,
} from "@/features/notices";
import { useApproveLanguage } from "@/features/notices";
import type { LanguageCode } from "@/types";
import { formatDateTime, formatDuration, humanise, shortHash } from "@/lib/format";
import { useActivatePurpose } from "@/features/registry";
import { ApiError } from "@/lib/errors";
import { useAuth, useToast } from "@/providers";
import {
  Rule3Badge,
  Rule3OverrideDialog,
} from "@/features/notices/components/rule3-override";
import { NoticeText } from "@/features/notices/components/notice-text";
import type { Notice, PurposeOnNotice } from "@/types";

/**
 * Which card on this page clears a checklist line.
 *
 * The checklist arrives as sentences, and until this existed every one of them
 * was dead text: a DPO read "the purpose X is draft, not activated" and had to
 * work out for themselves that the Purposes card below could fix it. Matching
 * the server's wording is a compromise, and a deliberate one - the only
 * alternative is a section name per line in the API, and this list is the only
 * caller that would ever read it. A line that stops matching loses its link and
 * nothing else.
 */
function sectionFor(item: string): string | null {
  if (/purpose/i.test(item)) return "notice-purposes";
  if (/text is not legally approved|no text yet/i.test(item)) return "notice-languages";
  if (/URL|DPO contact|who it addresses/i.test(item)) return "notice-rule3";
  return null;
}

const TABS = ["overview", "text", "purposes", "approval"] as const;
type NoticeTab = (typeof TABS)[number];
/** The cards' own anchors - the checklist's "fix this" links, and any link
 *  written before the tabs - open the tab that holds the card. */
const SECTIONS: Record<string, NoticeTab> = {
  "notice-purposes": "purposes",
  "notice-languages": "approval",
  "notice-rule3": "overview",
};

export default function NoticeDetailPage() {
  const { uuid } = useParams<{ uuid: string }>();
  const toast = useToast();
  // Opened from the notices register: offer that list back, as it was filtered.
  // Opened from the project, the hierarchy below already leads there.
  const fromRegister = useReturnTo(["/notices"]);
  const { me } = useAuth();

  const notice = useNotice(uuid);
  const checklist = useNoticeChecklist(uuid);
  const purposes = useNoticePurposes(uuid);
  const [narrowing, setNarrowing] = React.useState<PurposeOnNotice | null>(null);
  const languages = useNoticeLanguages(uuid);
  const publish = usePublishNotice(uuid);
  const approve = useApproveLanguage(uuid);
  const activatePurpose = useActivatePurpose();
  const [activating, setActivating] = React.useState<string | null>(null);

  /** The officer's sign-off on one purpose, taken from the notice that carries it. */
  async function onActivate(purpose: PurposeOnNotice) {
    setActivating(purpose.purpose_uuid);
    try {
      await activatePurpose.mutateAsync(purpose.purpose_uuid);
      toast.success(`${purpose.name} activated`, "It no longer blocks publication.");
    } catch (err) {
      toast.error(
        "Could not activate that purpose",
        err instanceof ApiError ? err.userMessage() : "Try again.",
      );
    } finally {
      setActivating(null);
    }
  }

  const [confirming, setConfirming] = React.useState(false);
  const [editingNotice, setEditingNotice] = React.useState(false);
  const [editingPurposes, setEditingPurposes] = React.useState(false);
  const [languageSheet, setLanguageSheet] = React.useState<{
    code?: LanguageCode;
    approved?: boolean;
  } | null>(null);

  // Above the early returns, like every hook here.
  const [tab, setTab, hash] = useHashTab(TABS, "overview", SECTIONS);
  const loaded = Boolean(notice.data);
  // A fragment naming a card, not a tab: the tab is open by now, so bring the
  // card itself into view - the browser's own jump ran before it existed.
  React.useEffect(() => {
    if (!loaded || !Object.hasOwn(SECTIONS, hash)) return;
    document.getElementById(hash)?.scrollIntoView?.({ block: "start" });
  }, [hash, loaded]);

  if (notice.isLoading) return <Skeleton className="h-96" />;
  if (notice.error) {
    return (
      <Alert tone="danger" title="Could not load this notice">
        {notice.error.userMessage()}
      </Alert>
    );
  }

  const n = notice.data!;
  const isDpo = me?.role === "dpo";
  // Assembly belongs to the author. The R&D User writes the notice because they
  // are the one who knows what the study collects and why; asking the DPO to
  // author it meant the DPO transcribing an email and then reviewing their own
  // transcription, which is not a review.
  //
  // The server confines an R&D User to their own projects, so this flag being
  // role-wide is not a widening: a notice they cannot reach does not load.
  // Who may *read* this notice's working surface: the checklist, which is
  // usually blocking the author rather than the officer. Composing it is no
  // longer theirs - the wording, the purposes and each rendition's text are the
  // Privacy Office's, and every control that changes one is gated on `isDpo`.
  // The author brings a notice by uploading a document or picking an approved
  // one, both from the project page.
  const canAuthor = isDpo || me?.role === "rnd_user";
  const isDraft = n.status === "draft" || n.status === "approved";
  const showChecklist = canAuthor && isDraft && Boolean(checklist.data);
  const approvedCount = (languages.data ?? []).filter((l) => l.approved_at).length;

  async function onPublish() {
    try {
      await publish.mutateAsync();
      toast.success(
        "Notice published",
        "The text and its hash are frozen. Edits now require a new version.",
      );
      setConfirming(false);
    } catch (err) {
      const message =
        err && typeof err === "object" && "userMessage" in err
          ? (err as { userMessage: () => string }).userMessage()
          : "Publication failed.";
      toast.error("Could not publish", message);
    }
  }

  return (
    <>
      <PageHeader
        // Where it sits - Projects, its project, the project's notices - and,
        // when the notices register opened it, a way back to that list as it
        // was filtered. The two are different places (UX review).
        breadcrumb={
          <nav
            aria-label="Where this notice sits"
            className="flex flex-wrap items-center gap-x-1.5 gap-y-1"
          >
            {fromRegister && (
              <>
                <Link
                  href={fromRegister}
                  className="inline-flex items-center gap-1 hover:text-text"
                >
                  <ArrowLeft className="size-3.5" aria-hidden="true" />
                  Back to notices
                </Link>
                <span aria-hidden="true" className="mx-1 text-text-subtle">
                  ·
                </span>
              </>
            )}
            <Link href="/projects" className="hover:text-text">
              Projects
            </Link>
            <span aria-hidden="true">/</span>
            <Link href={`/projects/${n.project_uuid}`} className="hover:text-text">
              {n.project_name}
            </Link>
            <span aria-hidden="true">/</span>
            <Link href={`/projects/${n.project_uuid}#notices`} className="hover:text-text">
              Notices
            </Link>
          </nav>
        }
        heading={false}
        title={`${n.notice_code} · version ${n.version}`}
      />
      {/* The notice's summary card (2026-10-10, the detail look the user
          settled on): what it is and whether it is frozen, over the four
          figures that say how far it is from publication - or when it got
          there. */}
      <RecordHeader
        icon={ScrollText}
        title={`${n.notice_code} · version ${n.version}`}
        meta={
          <>
            <span className="text-2xs font-semibold tracking-wider text-accent-text uppercase">
              Notice
            </span>
            <StatusBadge kind="notice" value={n.status} />
            <span>{n.project_name}</span>
            <span className="basis-full">
              {n.published_at
                ? `Published ${formatDateTime(n.published_at)}. This text is frozen.`
                : "Draft. Nothing here has been shown to a data subject yet."}
            </span>
          </>
        }
        actions={
          <>
            <AuditTrailLink
              entityType="notice"
              uuid={n.notice_uuid}
              label={`${n.notice_code} v${n.version}`}
            />
            {isDpo && isDraft && (
              <Button variant="secondary" size="sm" onClick={() => setEditingNotice(true)}>
                <Pencil className="size-4" />
                Edit
              </Button>
            )}
          </>
        }
        facts={[
          {
            label: "Purposes",
            value: purposes.data?.length ?? "—",
            icon: ListChecks,
            tint: 0,
            href: "#notice-purposes",
          },
          {
            label: "Languages approved",
            value: languages.data ? `${approvedCount} of ${languages.data.length}` : "—",
            icon: Globe,
            tint: 2,
            href: "#notice-languages",
          },
          {
            // The checklist is the only thing that counts the project's
            // sites; a reader it does not load for sees a dash.
            label: "Sites",
            value: checklist.data?.site_count ?? "—",
            icon: MapPin,
            tint: 1,
          },
          isDraft
            ? {
                label: "Blocking publication",
                value: checklist.data?.blocking.length ?? "—",
                icon: AlertTriangle,
                tint: 3,
                href: showChecklist ? "#overview" : undefined,
              }
            : {
                label: "Published",
                value: n.published_at ? formatDateTime(n.published_at) : "—",
                icon: Lock,
                tint: 3,
              },
        ]}
      />

      <Tabs value={tab} onValueChange={setTab} label="Notice sections" layout="underline">
        <TabList>
          <Tab value="overview" icon={LayoutGrid}>
            Overview
          </Tab>
          <Tab value="text" icon={FileText} count={languages.data?.length}>
            Text
          </Tab>
          <Tab value="purposes" icon={ListChecks} count={purposes.data?.length}>
            Purposes
          </Tab>
          <Tab value="approval" icon={Globe} count={languages.data?.length}>
            Legal approval
          </Tab>
        </TabList>

        <TabPanel value="overview">
          <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_20rem] lg:items-start">
            <div className="min-w-0 space-y-5">
              {showChecklist && checklist.data ? (
                <Card
                  className={
                    checklist.data.publishable
                      ? "border-success-border"
                      : "border-warning-border"
                  }
                >
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      {checklist.data.publishable ? (
                        <Check className="size-4 text-success" aria-hidden="true" />
                      ) : (
                        <AlertTriangle className="size-4 text-warning" aria-hidden="true" />
                      )}
                      Publication checklist
                    </CardTitle>
                    <p className="mt-1 text-xs text-text-muted">
                      Everything Rule 3 requires, and everything still missing.
                    </p>
                  </CardHeader>

                  <CardBody className="space-y-4">
                    {checklist.data.publishable ? (
                      <Alert tone="success">
                        This notice is complete and ready to publish.
                      </Alert>
                    ) : (
                      <div>
                        <p className="mb-2 text-sm font-medium">
                          {checklist.data.blocking.length} item(s) blocking publication:
                        </p>
                        <ul className="space-y-1.5">
                          {checklist.data.blocking.map((item) => (
                            <li key={item} className="flex items-start gap-2 text-sm">
                              <X
                                className="mt-0.5 size-4 shrink-0 text-danger"
                                aria-hidden="true"
                              />
                              <span>
                                {item}{" "}
                                {/* Each line points at the card that fixes it, on
                                this page. Matched on the server's own wording,
                                which is the same trade the transitions card
                                makes: the alternative is the API returning a
                                section name per line, and this list is the only
                                thing that would read it. */}
                                {sectionFor(item) && (
                                  <a
                                    href={`#${sectionFor(item)}`}
                                    className="font-medium whitespace-nowrap text-accent-text underline underline-offset-2"
                                  >
                                    fix this
                                  </a>
                                )}
                              </span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    <dl className="grid grid-cols-2 gap-3 border-t border-border pt-3 sm:grid-cols-4">
                      <Stat label="Purposes" value={checklist.data.purpose_count} />
                      <Stat label="Languages" value={checklist.data.language_count} />
                      <Stat
                        label="Approved"
                        value={checklist.data.approved_language_count}
                        warn={
                          checklist.data.approved_language_count <
                          checklist.data.language_count
                        }
                      />
                      <Stat label="Sites" value={checklist.data.site_count} />
                    </dl>

                    {/* The officer's, and only theirs: the endpoint is DPO-only, so
                    offering this to an author was a button that always failed. */}
                    {isDpo && checklist.data.publishable && !confirming && (
                      <Button variant="primary" onClick={() => setConfirming(true)}>
                        Publish this notice
                      </Button>
                    )}

                    {!isDpo && checklist.data.publishable && (
                      <Alert tone="success">
                        This notice is complete. The Privacy Office publishes it.
                      </Alert>
                    )}

                    {confirming && (
                      <div className="rounded-md border border-warning-border bg-warning-subtle p-4">
                        <p className="flex items-start gap-2 text-sm font-medium text-warning-text">
                          <Lock className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                          Publishing is not reversible
                        </p>
                        <p className="mt-2 text-sm text-warning-text">
                          Every language rendition is hashed and frozen. The recipient list
                          is generated from the project&apos;s active sites. From then on,
                          everyone who consents is consenting to exactly this text — a
                          correction means a new version, and the people who already
                          consented will have consented to the old one.
                        </p>
                        <div className="mt-3 flex gap-2">
                          <Button
                            variant="primary"
                            size="sm"
                            loading={publish.isPending}
                            onClick={onPublish}
                          >
                            Publish and freeze
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setConfirming(false)}
                          >
                            Cancel
                          </Button>
                        </div>
                      </div>
                    )}
                  </CardBody>
                </Card>
              ) : (
                <NoticeSummary
                  n={n}
                  purposes={purposes.data?.length}
                  languages={languages.data?.length}
                  approved={approvedCount}
                />
              )}
            </div>
            <div className="min-w-0 space-y-5">
              <Card id="notice-rule3" className="scroll-mt-20">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <FileText className="size-4" aria-hidden="true" />
                    Rule 3 elements
                  </CardTitle>
                </CardHeader>
                <CardBody>
                  <DescriptionList>
                    <DescriptionItem term="Withdraw consent">
                      <a
                        href={n.withdraw_url}
                        className="break-all text-accent-text underline underline-offset-2"
                      >
                        {n.withdraw_url}
                      </a>
                    </DescriptionItem>
                    <DescriptionItem term="Exercise rights">
                      <a
                        href={n.exercise_rights_url}
                        className="break-all text-accent-text underline underline-offset-2"
                      >
                        {n.exercise_rights_url}
                      </a>
                    </DescriptionItem>
                    <DescriptionItem term="Board complaint">
                      <a
                        href={n.board_complaint_url}
                        className="break-all text-accent-text underline underline-offset-2"
                      >
                        {n.board_complaint_url}
                      </a>
                      <p className="mt-0.5 text-xs text-text-subtle">
                        The Data Protection Board portal — not the internal grievance form.
                      </p>
                    </DescriptionItem>
                    <DescriptionItem term="DPO contact">{n.dpo_contact}</DescriptionItem>
                    <DescriptionItem term="Applies to">
                      {n.applicable_to ? (
                        humanise(n.applicable_to)
                      ) : (
                        // Named as blocking rather than left blank, because it is:
                        // publication refuses without it, and "—" would read as a
                        // field nobody needed to fill in.
                        <span className="text-warning-text">
                          Not set — publication is blocked until this says who the notice
                          addresses
                        </span>
                      )}
                    </DescriptionItem>
                    {n.template_code && (
                      <DescriptionItem term="Made from">
                        Template <Mono>{n.template_code}</Mono>
                        <span className="block text-xs text-text-subtle">
                          A copy: later changes to the template do not reach this notice.
                        </span>
                      </DescriptionItem>
                    )}
                    <DescriptionItem term="Recipients">
                      {n.recipients_text ?? (
                        <span className="text-text-subtle">
                          Generated from the project&apos;s sites at publication
                        </span>
                      )}
                    </DescriptionItem>
                  </DescriptionList>
                </CardBody>
              </Card>

              {/* Its own card rather than a row in the list above, because it is
              addressed to a different reader. Everything above describes the
              notice; this is an instruction to whoever collects against it, and
              somebody scanning a description list will not read it as one.

              Never served to a data principal: the public endpoints name their
              columns explicitly, so it cannot reach them by being shown here. */}
              {n.note && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <StickyNote className="size-4" aria-hidden="true" />
                      For whoever collects against this notice
                    </CardTitle>
                  </CardHeader>
                  <CardBody>
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{n.note}</p>
                    <p className="mt-2 text-xs text-text-subtle">
                      Not part of the notice. The data principal never sees this.
                    </p>
                  </CardBody>
                </Card>
              )}

              {!isDraft && (
                <Alert tone="info">
                  <p className="flex items-start gap-2">
                    <Lock className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                    <span>
                      This notice is {n.status}. Its text and hashes are immutable — the
                      database refuses an edit. To change anything, publish a new version.
                    </span>
                  </p>
                </Alert>
              )}
            </div>
          </div>
        </TabPanel>

        <TabPanel value="text" className="space-y-6">
          <NoticeText
            languages={languages.data}
            isLoading={languages.isLoading}
            canEdit={isDpo && isDraft}
            onEdit={(lang) =>
              setLanguageSheet({
                code: lang.language_code,
                approved: Boolean(lang.approved_at),
              })
            }
          />
        </TabPanel>

        <TabPanel value="purposes" className="space-y-6">
          <Card id="notice-purposes" className="scroll-mt-20">
            <CardHeader className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <CardTitle>Purposes</CardTitle>
                <p className="mt-1 text-xs text-text-muted">
                  Rule 3(b): what each purpose enables, itemised, with its retention.
                </p>
              </div>
              {isDpo && isDraft && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setEditingPurposes(true)}
                >
                  <Plus className="size-4" />
                  Manage
                </Button>
              )}
            </CardHeader>
            {purposes.isLoading ? (
              <CardBody>
                <Skeleton className="h-24" />
              </CardBody>
            ) : !purposes.data?.length ? (
              <EmptyState
                title="No purposes attached"
                description="A notice with no purposes asks a data subject to agree to nothing in particular."
                action={
                  isDpo && isDraft ? (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setEditingPurposes(true)}
                    >
                      <Plus className="size-4" />
                      Attach a purpose
                    </Button>
                  ) : undefined
                }
              />
            ) : (
              <ul className="divide-y divide-border">
                {purposes.data.map((purpose) => (
                  <li key={purpose.purpose_uuid} className="px-5 py-4">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="text-sm font-medium">{purpose.name}</p>
                        <p className="mt-0.5 text-xs text-text-muted">
                          {purpose.description}
                        </p>
                      </div>
                      <div className="flex shrink-0 items-center gap-1.5">
                        {purpose.is_mandatory && (
                          <span className="rounded-full border border-warning-border bg-warning-subtle px-2 py-0.5 text-2xs font-medium text-warning-text">
                            cannot be refused
                          </span>
                        )}
                        <Rule3Badge purpose={purpose} />
                        <StatusBadge kind="purpose" value={purpose.status} dot={false} />
                        {/* One decision per purpose, deliberately, and taken
                            here rather than in the register. The officer used to
                            read "the purpose X is draft, not activated" on the
                            checklist above, copy that code, open Purposes, filter
                            to drafts and find it, nine times for one imported
                            document. The set is what they are reading; this is
                            where they should be able to act on it. */}
                        {isDpo && purpose.status === "draft" && isDraft && (
                          <Button
                            variant="secondary"
                            size="sm"
                            loading={activating === purpose.purpose_uuid}
                            onClick={() => onActivate(purpose)}
                            title="Make this purpose usable by a notice"
                          >
                            <CheckCircle2 className="size-4" />
                            Activate
                          </Button>
                        )}
                        {/* Draft only. A published notice is frozen and hashed;
                            changing what it says is a new version, not an edit,
                            and the API refuses it either way. */}
                        {isDpo && isDraft && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setNarrowing(purpose)}
                            title="State Rule 3(b) more narrowly on this notice"
                          >
                            <SlidersHorizontal className="size-4" />
                            Customise for this notice
                          </Button>
                        )}
                      </div>
                    </div>

                    <dl className="mt-2 grid gap-1 text-xs text-text-subtle sm:grid-cols-3">
                      <div>
                        <dt className="inline font-medium">Basis: </dt>
                        <dd className="inline">
                          {purpose.lawful_basis === "consent_s6"
                            ? "Consent (s.6)"
                            : `s.7 ${purpose.s7_clause ?? ""}`}
                        </dd>
                      </div>
                      <div>
                        <dt className="inline font-medium">Retention: </dt>
                        <dd className="inline">
                          {formatDuration(purpose.retention_period)}
                        </dd>
                      </div>
                      <div>
                        <dt className="inline font-medium">Categories: </dt>
                        <dd className="inline">
                          {purpose.data_categories.map(humanise).join(", ")}
                          {/* Named where they differ, because otherwise a
                              reviewer comparing this against the purpose
                              register would find two lists and no explanation. */}
                          {purpose.is_overridden && (
                            <span className="text-accent-text"> (this notice only)</span>
                          )}
                        </dd>
                      </div>
                    </dl>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </TabPanel>

        <TabPanel value="approval" className="space-y-6">
          <Card id="notice-languages" className="scroll-mt-20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Globe className="size-4" aria-hidden="true" />
                Legal approval, per language
              </CardTitle>
              <p className="mt-1 text-xs text-text-muted">
                The register of sign-off — read the text itself on the{" "}
                <a href="#text" className="text-accent-text underline underline-offset-2">
                  Text tab
                </a>
                . Approval is per language, not once per notice: a DPO who reads English and
                approves eight renditions has approved one.
              </p>
              {isDpo && isDraft && (
                <Button
                  variant="secondary"
                  size="sm"
                  className="mt-2"
                  onClick={() => setLanguageSheet({})}
                >
                  <Plus className="size-4" />
                  Add language
                </Button>
              )}
            </CardHeader>
            {languages.isLoading ? (
              <CardBody>
                <Skeleton className="h-20" />
              </CardBody>
            ) : !languages.data?.length ? (
              <EmptyState
                title="No text yet"
                description="A notice cannot be published until it says something. Each rendition is approved on its own."
                action={
                  isDpo && isDraft ? (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setLanguageSheet({})}
                    >
                      <Plus className="size-4" />
                      Add language
                    </Button>
                  ) : undefined
                }
              />
            ) : (
              <ul className="divide-y divide-border">
                {languages.data.map((lang) => (
                  <li
                    key={lang.notice_language_uuid}
                    className="flex flex-wrap items-center justify-between gap-3 px-5 py-3"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium capitalize">{lang.language_code}</p>
                      <p className="mt-0.5 text-xs">
                        <span className="text-text-subtle">sha256 </span>
                        <Mono>{shortHash(lang.content_hash)}</Mono>
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {lang.approved_at ? (
                        <div className="text-right">
                          <span className="inline-flex items-center gap-1 text-xs text-success-text">
                            <Check className="size-3.5" aria-hidden="true" />
                            Approved
                          </span>
                          <p className="text-2xs text-text-subtle">
                            {lang.approved_by_name} · {formatDateTime(lang.approved_at)}
                          </p>
                        </div>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs text-warning-text">
                          <AlertTriangle className="size-3.5" aria-hidden="true" />
                          Not legally approved
                        </span>
                      )}

                      {isDpo && isDraft && (
                        <>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() =>
                              setLanguageSheet({
                                code: lang.language_code,
                                approved: Boolean(lang.approved_at),
                              })
                            }
                          >
                            <Pencil className="size-4" />
                            Edit
                          </Button>
                          {/* Approving stays with the DPO even though editing
                              does not. An author who could sign off their own
                              text would make the review a formality — and the
                              approved hash is what a data subject's consent is
                              matched against. */}
                          {isDpo && !lang.approved_at && (
                            <Button
                              variant="secondary"
                              size="sm"
                              loading={approve.isPending}
                              onClick={async () => {
                                try {
                                  await approve.mutateAsync(lang.language_code);
                                  toast.success(
                                    `${lang.language_code} approved`,
                                    "Its hash is what a data subject's consent will be matched against.",
                                  );
                                } catch (err) {
                                  toast.error(
                                    "Could not approve",
                                    err && typeof err === "object" && "userMessage" in err
                                      ? (err as { userMessage: () => string }).userMessage()
                                      : "Please try again.",
                                  );
                                }
                              }}
                            >
                              <Check className="size-4" />
                              Approve
                            </Button>
                          )}
                        </>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </TabPanel>
      </Tabs>

      <Dialog open={editingNotice} onOpenChange={setEditingNotice}>
        <DialogContent title="Edit notice" description="Drafts only." size="lg">
          <NoticeForm notice={n} onDone={() => setEditingNotice(false)} />
        </DialogContent>
      </Dialog>

      <Dialog open={editingPurposes} onOpenChange={setEditingPurposes}>
        <DialogContent
          title="Purposes on this notice"
          description="Only active purposes can be attached, and only while the notice is a draft."
          size="lg"
        >
          <NoticePurposesForm noticeUuid={uuid} />
        </DialogContent>
      </Dialog>

      <Dialog
        open={Boolean(languageSheet)}
        onOpenChange={(o) => !o && setLanguageSheet(null)}
      >
        <DialogContent
          title={
            languageSheet?.code
              ? `Edit ${humanise(languageSheet.code)} text`
              : "Add language"
          }
          description="This exact text is hashed at publication and becomes the record of what was agreed to."
          size="lg"
        >
          {languageSheet && (
            <LanguageForm
              noticeUuid={uuid}
              existingCode={languageSheet.code}
              existingText={
                languages.data?.find((l) => l.language_code === languageSheet.code)
                  ?.rendered_text
              }
              wasApproved={languageSheet.approved}
              onDone={() => setLanguageSheet(null)}
            />
          )}
        </DialogContent>
      </Dialog>
      <Rule3OverrideDialog
        noticeUuid={uuid}
        purpose={narrowing}
        onClose={() => setNarrowing(null)}
      />
    </>
  );
}

/**
 * The Overview's main card when there is no checklist to show (2026-10-10):
 * a published notice, or a reader the checklist is not for. Where it stands
 * and where its parts are, so the tab is never just the side column.
 */
function NoticeSummary({
  n,
  purposes,
  languages,
  approved,
}: {
  n: Notice;
  purposes: number | undefined;
  languages: number | undefined;
  approved: number;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ScrollText className="size-4" aria-hidden="true" />
          This notice
        </CardTitle>
      </CardHeader>
      <CardBody>
        <DescriptionList>
          <DescriptionItem term="Project">
            <Link
              href={`/projects/${n.project_uuid}`}
              className="text-accent-text underline underline-offset-2"
            >
              {n.project_name}
            </Link>
          </DescriptionItem>
          <DescriptionItem term="Status">
            {n.published_at
              ? `Published ${formatDateTime(n.published_at)}. This text is frozen.`
              : "Draft. Nothing here has been shown to a data subject yet."}
          </DescriptionItem>
          <DescriptionItem term="Purposes">
            <a href="#purposes" className="text-accent-text underline underline-offset-2">
              {purposes ?? "—"}
            </a>
          </DescriptionItem>
          <DescriptionItem term="Languages approved">
            <a href="#approval" className="text-accent-text underline underline-offset-2">
              {languages === undefined ? "—" : `${approved} of ${languages}`}
            </a>
          </DescriptionItem>
        </DescriptionList>
      </CardBody>
    </Card>
  );
}

function Stat({ label, value, warn }: { label: string; value: number; warn?: boolean }) {
  return (
    <div>
      <dt className="text-xs text-text-subtle">{label}</dt>
      <dd
        className={[
          "tabular text-lg font-semibold",
          warn ? "text-warning-text" : "text-text",
        ].join(" ")}
      >
        {value}
      </dd>
    </div>
  );
}
