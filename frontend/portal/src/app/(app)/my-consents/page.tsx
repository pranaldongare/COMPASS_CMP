/**
 * The data subject's own record.
 *
 * Three things she is entitled to see, and all three are here:
 *
 * - **What she agreed to**, per purpose.
 * - **The exact words she was shown** — matched on the hash copied into her
 *   artefact at capture, not the live notice, so a later correction cannot
 *   silently repoint her record at text she never saw.
 * - **Who her data was shared with** (s.11(1)(b)), answered from `export_line`
 *   rather than by somebody parsing an archived CSV.
 *
 * Withdrawal is one click from the record it concerns. Making it harder to find
 * than consent was is exactly what s.6(4) forbids.
 *
 * A list and the one chosen beside it (2026-11-12, mock-up B), as My requests
 * is: each consent was a card with four buttons, a sentence and two panels
 * that opened inside it, and the page read as complicated. The consents are
 * now a list; the chosen one shows its purposes, its notice and its history
 * as three tabs, with one button to withdraw and one to download. The words
 * are shorter: "View notice", not "Show the exact notice I was given".
 */
"use client";

import { ArrowLeft, FileDown, Share2, ShieldOff } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";

import { ActivityFeed } from "@/components/data-display/activity-feed";
import { PageHeader } from "@/components/layout/app-shell";
import { EmptyConsent } from "@/components/ui/graphics";
import {
  Alert,
  Button,
  Card,
  EmptyState,
  Mono,
  Skeleton,
} from "@/components/ui/primitives";
import { StatusBadge } from "@/components/ui/status";
import { Tab, TabList, TabPanel, Tabs } from "@/components/ui/tabs";
import {
  useMyConsentGrants,
  useMyConsentNotice,
  useMyConsentTrail,
  useMyConsents,
  useMyDisclosures,
  useWithdraw,
} from "@/features/my-consents";
import { downloadMyConsentRecord } from "@/features/my-consents/api";
import { langTag } from "@/features/public-consent/components/languages";
import { HomeStrip } from "@/features/rights/components/home-strip";
import { ApiError } from "@/lib/errors";
import {
  cn,
  formatDate,
  formatDateTime,
  formatDuration,
  humanise,
  saveBlob,
  shortHash,
} from "@/lib/format";
import { useToast } from "@/providers";
import type { MyConsent } from "@/types";

/** The list's last row, which opens who her data went to. */
const SHARING = "sharing";

interface Disclosure {
  export_uuid: string;
  export_type: string;
  exported_at: string;
  project_name: string;
  site_label: string;
  processor_name: string | null;
}

/**
 * Where a consent stands. Anything still granted can still be withdrawn -
 * including what remains after she withdrew one purpose of several:
 * `is_withdrawal` records that act; it does not mean nothing is left.
 */
function stateOf(c: MyConsent): "withdrawn" | "declined" | "partial" | "consented" {
  if (c.granted_count === 0) return c.is_withdrawal ? "withdrawn" : "declined";
  return c.granted_count < c.purpose_count ? "partial" : "consented";
}

/** How much of what she was asked she agreed to: "2 of 2 purposes". */
function purposeCount(granted: number, total: number): string {
  return `${granted} of ${total} ${total === 1 ? "purpose" : "purposes"}`;
}

export default function MyConsentsPage() {
  const router = useRouter();
  const params = useSearchParams();
  const consents = useMyConsents();
  const disclosures = useMyDisclosures();
  // The one she chose: a consent, or who her data was shared with. A link
  // may name a consent (`?consent=`) - a request "about one consent only"
  // opens it (UX review 2026-10-05). None chosen, a wide screen shows the
  // first beside the list; a phone shows the list.
  const [chosen, setChosen] = React.useState<string | null>(params.get("consent"));
  const all = consents.data ?? [];
  const current =
    chosen === SHARING ? null : (all.find((c) => c.consent_uuid === chosen) ?? all[0] ?? null);
  const sharing = chosen === SHARING;
  const shared = (disclosures.data ?? []) as Disclosure[];

  function choose(uuid: string) {
    setChosen(uuid);
    // The address names it, so a reload or a shared link opens the same one.
    router.replace(uuid === SHARING ? "/my-consents" : `/my-consents?consent=${uuid}`, {
      scroll: false,
    });
    // On a phone the record replaces the list: start it at its top.
    if (window.matchMedia?.("(max-width: 1023px)").matches) window.scrollTo({ top: 0 });
  }

  return (
    <>
      <PageHeader
        title="My consents"
        description="Your consents, the notices you were shown and where your data was shared. You can withdraw at any time."
      />

      <HomeStrip />

      {consents.isLoading && <Skeleton className="h-48" />}

      {consents.error && (
        <Alert tone="danger" title="Could not load your consents">
          {consents.error.userMessage()}
        </Alert>
      )}

      {consents.data && all.length === 0 && (
        <Card>
          <EmptyState
            illustration={<EmptyConsent />}
            title="No consent records"
            description="When you agree to a notice, it will appear here."
          />
        </Card>
      )}

      {all.length > 0 && (
        <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)]">
          <Card className={cn("overflow-hidden", chosen && "hidden lg:block")}>
            <ul aria-label="Your consents">
              {all.map((c) => (
                <li key={c.consent_uuid} className="border-b border-border">
                  <ConsentRow
                    consent={c}
                    selected={!sharing && c.consent_uuid === current?.consent_uuid}
                    onChoose={() => choose(c.consent_uuid)}
                  />
                </li>
              ))}
              <li>
                <button
                  type="button"
                  aria-current={sharing ? "true" : undefined}
                  onClick={() => choose(SHARING)}
                  className={cn(
                    "flex w-full items-center justify-between gap-2 px-4 py-3 text-left transition-colors hover:bg-surface-hover",
                    sharing &&
                      "bg-accent-subtle shadow-[inset_3px_0_0_var(--accent)] hover:bg-accent-subtle",
                  )}
                >
                  <span className="flex items-center gap-2 text-sm font-semibold text-accent-text">
                    <Share2 className="size-4" aria-hidden="true" />
                    Data sharing
                  </span>
                  {disclosures.data && (
                    <span className="text-xs text-text-muted">
                      {shared.length === 0
                        ? "None"
                        : shared.length === 1
                          ? "1 record"
                          : `${shared.length} records`}
                    </span>
                  )}
                </button>
              </li>
            </ul>
          </Card>

          <Card
            id="consent-detail"
            className={cn("scroll-mt-24 p-5 lg:sticky lg:top-6", !chosen && "hidden lg:block")}
          >
            <Button
              variant="ghost"
              size="sm"
              className="mb-3 lg:hidden"
              onClick={() => setChosen(null)}
            >
              <ArrowLeft className="size-4" />
              All consents
            </Button>
            {sharing ? (
              <Sharing
                items={shared}
                isLoading={disclosures.isLoading}
                error={disclosures.error}
                retry={disclosures.refetch}
              />
            ) : (
              current && (
                <ConsentDetail
                  key={current.consent_uuid}
                  consent={current}
                  // A withdrawal is a new record that takes the old one's
                  // place in the list: follow it there.
                  onReplaced={setChosen}
                />
              )
            )}
          </Card>
        </div>
      )}
    </>
  );
}

/** One consent in the list: the study, where it stands, how much, and when. */
function ConsentRow({
  consent: c,
  selected,
  onChoose,
}: {
  consent: MyConsent;
  selected: boolean;
  onChoose: () => void;
}) {
  return (
    <button
      type="button"
      aria-current={selected ? "true" : undefined}
      onClick={onChoose}
      className={cn(
        "block w-full px-4 py-3 text-left transition-colors hover:bg-surface-hover",
        selected && "bg-accent-subtle shadow-[inset_3px_0_0_var(--accent)] hover:bg-accent-subtle",
      )}
    >
      <span className="flex items-center justify-between gap-2">
        <span className="min-w-0 truncate text-sm font-semibold">{c.project_name}</span>
        <StatusBadge kind="consent" value={stateOf(c)} />
      </span>
      <span className="mt-0.5 block text-xs text-text-muted">
        {purposeCount(c.granted_count, c.purpose_count)} · {formatDate(c.affirmative_action_at)}
      </span>
    </button>
  );
}

type DetailTab = "purposes" | "notice" | "history";

function ConsentDetail({
  consent,
  onReplaced,
}: {
  consent: MyConsent;
  onReplaced: (uuid: string) => void;
}) {
  const toast = useToast();
  const [tab, setTab] = React.useState<DetailTab>("purposes");
  const grants = useMyConsentGrants(consent.consent_uuid);
  const withdraw = useWithdraw(consent.consent_uuid);
  // What she is about to withdraw, while she is asked: everything, or one
  // purpose. Asked both times - withdrawing is one click to reach, and one
  // more to mean.
  const [confirming, setConfirming] = React.useState<
    "all" | { purpose_uuid: string; name: string } | null
  >(null);
  const active = consent.granted_count > 0;

  async function doWithdraw() {
    if (!confirming) return;
    try {
      const result = await withdraw.mutateAsync(
        confirming === "all" ? { all: true } : { purposes: [confirming.purpose_uuid] },
      );
      toast.success(
        "Withdrawal recorded",
        result.stopped.length ? `Stopped: ${result.stopped.join(", ")}.` : undefined,
      );
      setConfirming(null);
      onReplaced(result.consent_uuid);
    } catch (err) {
      toast.error(
        "Withdrawal failed",
        err instanceof ApiError ? err.userMessage() : "Could not record the withdrawal.",
      );
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3 sm:flex-nowrap">
        <div className="min-w-0 flex-1">
          <h2 className="text-base font-semibold">{consent.project_name}</h2>
          <p className="mt-1 text-xs text-text-muted">
            {consent.notice_code} v{consent.version} · {humanise(consent.language_code)} ·{" "}
            {consent.granted_count === 0 && !consent.is_withdrawal ? "declined" : "given"}{" "}
            {formatDateTime(consent.affirmative_action_at)}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <StatusBadge kind="consent" value={stateOf(consent)} />
          {active && (
            <Button variant="subtle" size="sm" onClick={() => setConfirming("all")}>
              <ShieldOff className="size-4" />
              Withdraw consent
            </Button>
          )}
        </div>
      </div>

      {confirming && (
        <Alert
          tone="warning"
          title={
            confirming === "all" ? "Withdraw all purposes?" : `Withdraw “${confirming.name}”?`
          }
        >
          <p>
            Processing for {confirming === "all" ? "these purposes" : "this purpose"} stops. Data
            already collected is not deleted; to have it erased, make a rights request.
          </p>
          <div className="mt-3 flex gap-2">
            <Button variant="danger" size="sm" loading={withdraw.isPending} onClick={doWithdraw}>
              Withdraw
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setConfirming(null)}>
              Cancel
            </Button>
          </div>
        </Alert>
      )}

      <Tabs
        value={tab}
        onValueChange={(next) => setTab(next as DetailTab)}
        label="This consent"
        layout="underline"
      >
        <TabList>
          <Tab value="purposes" count={consent.purpose_count}>
            Purposes
          </Tab>
          <Tab value="notice">Notice</Tab>
          <Tab value="history">History</Tab>
        </TabList>

        <TabPanel value="purposes" className="pt-4">
          {grants.isLoading ? (
            <Skeleton className="h-24" />
          ) : grants.error ? (
            <LoadFailed what="your purposes" error={grants.error} retry={grants.refetch} />
          ) : (
            <ul className="space-y-2" aria-label="Purposes">
              {grants.data?.map((grant) => (
                <li key={grant.purpose_uuid} className="rounded-md border border-border p-3">
                  {/* Not wrapped: the badge and Withdraw stay at the right of
                      every purpose, however long its description. */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium">{grant.name}</p>
                      <p className="mt-0.5 text-xs text-text-muted">{grant.description}</p>
                    </div>
                    <div className="flex shrink-0 items-center gap-1">
                      <StatusBadge
                        kind="consent"
                        value={grant.granted ? "consented" : "declined"}
                        dot={false}
                      />
                      {grant.granted && active && (
                        <Button
                          variant="subtle"
                          size="sm"
                          aria-label={`Withdraw ${grant.name}`}
                          onClick={() =>
                            setConfirming({ purpose_uuid: grant.purpose_uuid, name: grant.name })
                          }
                        >
                          Withdraw
                        </Button>
                      )}
                    </div>
                  </div>
                  <dl className="mt-2 grid gap-1 text-xs text-text-subtle sm:grid-cols-2">
                    <div>
                      <dt className="inline font-medium">Data: </dt>
                      <dd className="inline">{grant.data_categories.map(humanise).join(", ")}</dd>
                    </div>
                    <div>
                      <dt className="inline font-medium">Kept for: </dt>
                      <dd className="inline">{formatDuration(grant.retention_period)}</dd>
                    </div>
                  </dl>
                </li>
              ))}
            </ul>
          )}
        </TabPanel>

        <TabPanel value="notice" className="pt-4">
          {tab === "notice" && (
            <ServedNotice consentUuid={consent.consent_uuid} languageCode={consent.language_code} />
          )}
        </TabPanel>

        {/* Every consent has a history, refused ones included. That is the
            point: "freely given" is not demonstrable if somebody cannot see
            that their refusal was recorded, when, and against which notice. */}
        <TabPanel value="history" className="pt-4">
          {tab === "history" && <History consentUuid={consent.consent_uuid} />}
        </TabPanel>
      </Tabs>

      <DownloadRecord consentUuid={consent.consent_uuid} />
    </div>
  );
}

function History({ consentUuid }: { consentUuid: string }) {
  const trail = useMyConsentTrail(consentUuid);
  return (
    <div>
      <p className="mb-3 text-xs text-text-muted">Every change to this consent, oldest first.</p>
      {trail.error ? (
        <LoadFailed what="the history of this consent" error={trail.error} retry={trail.refetch} />
      ) : (
        <ActivityFeed
          entries={trail.data}
          isLoading={trail.isLoading}
          order="oldest"
          emptyTitle="Nothing recorded yet"
          emptyDescription="Entries appear here as things happen to this record."
        />
      )}
    </div>
  );
}

/** Her copy of the record, as a PDF to keep (2026-10-15). */
function DownloadRecord({ consentUuid }: { consentUuid: string }) {
  const toast = useToast();
  const [busy, setBusy] = React.useState(false);

  async function download() {
    setBusy(true);
    try {
      const got = await downloadMyConsentRecord(consentUuid);
      saveBlob(got.blob, got.filename);
    } catch (err) {
      toast.error(
        "Could not make the PDF",
        err instanceof ApiError ? err.userMessage() : "Try again in a minute.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Button variant="secondary" size="sm" loading={busy} onClick={download}>
      <FileDown className="size-4" />
      Download record
    </Button>
  );
}

/** The exact notice she was given, as it was when she decided. */
function ServedNotice({
  consentUuid,
  languageCode,
}: {
  consentUuid: string;
  /** The rendition she was shown, so the text is marked as that language. */
  languageCode: string;
}) {
  const served = useMyConsentNotice(consentUuid);

  if (served.isLoading) return <Skeleton className="h-32" />;
  if (served.error) {
    return (
      <LoadFailed what="the notice you were given" error={served.error} retry={served.refetch} />
    );
  }

  const data = served.data as
    | {
        rendered_text: string;
        notice_content_hash: string;
        served_at: string;
        integrity: string;
        hash_matches: boolean;
      }
    | undefined;

  if (!data) return null;

  return (
    <div className="rounded-md border border-border bg-bg-subtle p-4">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-medium tracking-wide text-text-subtle uppercase">
          Shown {formatDateTime(data.served_at)}
        </p>
        <span
          className={[
            "text-xs",
            data.hash_matches ? "text-success-text" : "text-danger-text",
          ].join(" ")}
        >
          {data.hash_matches ? "Integrity verified" : "Integrity check failed"}
        </span>
      </div>

      <div
        lang={langTag(languageCode)}
        className="max-h-96 overflow-y-auto text-sm leading-relaxed whitespace-pre-wrap"
      >
        {data.rendered_text}
      </div>

      <p className="mt-3 text-xs">
        <span className="text-text-subtle">Notice hash: </span>
        <Mono>{shortHash(data.notice_content_hash, 12)}</Mono>
      </p>

      {!data.hash_matches && (
        <Alert tone="danger" className="mt-3">
          {data.integrity}
        </Alert>
      )}
    </div>
  );
}

/** Who her data went to (s.11(1)(b)): each file of it sent to a processor. */
function Sharing({
  items,
  isLoading,
  error,
  retry,
}: {
  items: Disclosure[];
  isLoading: boolean;
  error: unknown;
  retry: () => unknown;
}) {
  return (
    <div>
      <h2 className="flex items-center gap-2 text-base font-semibold">
        <Share2 className="size-4" aria-hidden="true" />
        Data sharing
      </h2>
      <p className="mt-1 mb-4 text-xs text-text-muted">Organisations that received your data.</p>

      {isLoading ? (
        <Skeleton className="h-20" />
      ) : error ? (
        <LoadFailed what="where your data was shared" error={error} retry={retry} />
      ) : items.length === 0 ? (
        <EmptyState
          title="No sharing recorded"
          description="None of your data has been sent to another organisation."
        />
      ) : (
        <ul className="divide-y divide-border rounded-md border border-border">
          {items.map((item) => (
            <li key={item.export_uuid} className="px-4 py-3">
              <p className="text-sm font-medium">{item.processor_name ?? item.site_label}</p>
              <p className="mt-0.5 text-xs text-text-muted">
                {item.project_name} · {formatDateTime(item.exported_at)}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/**
 * A panel whose request failed. It says so, and offers to ask again, rather
 * than falling through to its empty state: "Not shared with anyone" read after
 * a failed request is a false statement about her data (review UX-2).
 */
function LoadFailed({
  what,
  error,
  retry,
}: {
  what: string;
  error: unknown;
  retry: () => unknown;
}) {
  return (
    <Alert tone="danger" title={`Could not load ${what}`}>
      <p>{error instanceof ApiError ? error.userMessage() : "The request did not complete."}</p>
      <Button variant="secondary" size="sm" className="mt-2" onClick={() => void retry()}>
        Try again
      </Button>
    </Alert>
  );
}
