/**
 * The data principal's requests - sections 11 to 14, from her side.
 *
 * A short list and the chosen request beside it (2026-10-30, mock-up B): the
 * list says what each is, where it stands and its one date; the request on
 * the right says the rest (`RequestDetail`). Opening one used to unfold it in
 * the list with the office's clock and flow diagram, pushing every other
 * request down the page. On a phone the list and the request are one screen
 * each, with a way back.
 *
 * Two things are one click away because the Act says they should be: making
 * a request, and disputing a response. A grievance is not an appeal against
 * the outcome alone - late, incomplete, or sent the wrong way all count.
 *
 * A grievance and the request it disputes are both hers, so they are both on
 * this page: the grievance says what she disputed and opens it, and the
 * original says it was disputed and opens that. No second page to find.
 */
"use client";

import { ArrowLeft, Download, Plus } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { EmptyRecords } from "@/components/ui/graphics";
import {
  Alert,
  Button,
  Card,
  EmptyState,
  Mono,
  Skeleton,
} from "@/components/ui/primitives";
import { REQUEST_TYPE_COPY, RequestStatusBadge } from "@/features/rights/components/copy";
import { MyRequestForm } from "@/features/rights/components/request-form";
import { RequestDetail } from "@/features/rights/components/request-detail";
import {
  FILTER_FROM,
  RequestFilter,
  useRequestFilter,
} from "@/features/rights/components/request-filter";
import { useMyRequests } from "@/features/rights/queries";
import { relate } from "@/features/rights/relate";
import { cn, formatDate } from "@/lib/format";
import type { MyRequest } from "@/types";

export default function MyRequestsPage() {
  const requests = useMyRequests();
  // A link may name a request (`?request=`) or the responses ready to download
  // (`?view=ready`) - "our response to RR-… is ready" used to open the top of
  // this page at a different request (UX review). Read once, as where the page
  // starts; after that the person is in charge.
  const params = useSearchParams();
  const router = useRouter();
  // `?new=1` opens the form: the home page's "Make a request" lands here.
  // Read once, like `?request=`; closing the form drops it from the address
  // so a reload does not open it again.
  const [asking, setAsking] = React.useState(params.get("new") === "1");
  function stopAsking() {
    setAsking(false);
    if (params.get("new")) router.replace("/my-requests", { scroll: false });
  }
  // The request she chose. None chosen, a wide screen shows the first in the
  // list beside it; a phone shows the list.
  const [chosen, setChosen] = React.useState<string | null>(params.get("request"));
  const all = requests.data ?? [];
  const { byUuid, followers } = relate(all);
  const filter = useRequestFilter(all, params.get("view") === "ready" ? "ready" : "all");
  const filtering = all.length >= FILTER_FROM || filter.view !== "all";
  const shown = filtering ? filter.shown : all;
  const current = (chosen ? byUuid.get(chosen) : undefined) ?? shown[0] ?? null;

  function choose(uuid: string) {
    setChosen(uuid);
    if (!filter.isShown(uuid)) filter.reset();
    // The address names it, so a reload or a shared link opens the same one.
    router.replace(`/my-requests?request=${uuid}`, { scroll: false });
    // On a phone the request replaces the list: start it at its top.
    if (window.matchMedia?.("(max-width: 1023px)").matches) window.scrollTo({ top: 0 });
  }

  return (
    <>
      <PageHeader
        title="My requests"
        description="Ask for access to everything we hold about you, ask for it to be erased, or raise a complaint. Every request runs on a published clock, and you can see where it is."
        actions={
          <Button variant="primary" onClick={() => setAsking(true)}>
            <Plus className="size-4" />
            Make a request
          </Button>
        }
      />

      {requests.isLoading && <Skeleton className="h-40" />}
      {requests.error && (
        <Alert tone="danger" title="Could not load your requests">
          {requests.error.userMessage()}
        </Alert>
      )}
      {requests.data && requests.data.length === 0 && (
        <Card>
          <EmptyState
            illustration={<EmptyRecords />}
            title="No requests yet"
            description="When you make one, its reference, its deadline and its progress appear here."
          />
        </Card>
      )}

      {filtering && (
        <div className={cn(chosen && "hidden lg:block")}>
          <RequestFilter filter={filter} />
        </div>
      )}

      {filtering && shown.length === 0 && (
        <Card>
          <EmptyState
            title="No requests match"
            description="Try another word, or show all of them."
            action={
              <Button variant="secondary" onClick={filter.reset}>
                Show all requests
              </Button>
            }
          />
        </Card>
      )}

      {shown.length > 0 && current && (
        <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)]">
          <Card className={cn("overflow-hidden", chosen && "hidden lg:block")}>
            <ul aria-label="Your requests">
              {shown.map((r) => (
                <li key={r.request_uuid} className="border-b border-border last:border-b-0">
                  <RequestRow
                    request={r}
                    selected={r.request_uuid === current.request_uuid}
                    onChoose={() => choose(r.request_uuid)}
                  />
                </li>
              ))}
            </ul>
          </Card>

          <Card
            id="request-detail"
            className={cn(
              "scroll-mt-24 p-5 lg:sticky lg:top-6",
              !chosen && "hidden lg:block",
            )}
          >
            <Button
              variant="ghost"
              size="sm"
              className="mb-3 lg:hidden"
              onClick={() => setChosen(null)}
            >
              <ArrowLeft className="size-4" />
              All requests
            </Button>
            <RequestDetail
              key={current.request_uuid}
              request={current}
              about={
                current.linked_request_uuid
                  ? (byUuid.get(current.linked_request_uuid) ?? null)
                  : null
              }
              followedBy={followers.get(current.request_uuid) ?? []}
              onJump={choose}
            />
          </Card>
        </div>
      )}

      {/* Nominations have their own page (UX review): below every request
          was the last place anybody looked for them. */}
      <p className="mt-8 text-sm text-text-muted">
        Naming someone to act for you, or acting for someone who named you, is under{" "}
        <Link
          href="/my-nominations"
          className="font-medium text-accent-text underline underline-offset-2"
        >
          My nominations
        </Link>
        .
      </p>

      <Dialog open={asking} onOpenChange={(next) => !next && stopAsking()}>
        <DialogContent
          title="Make a request"
          description="You are signed in, so this counts as verified and the clock starts now."
        >
          <MyRequestForm
            onDone={(created) => {
              stopAsking();
              choose(created.request_uuid);
            }}
          />
        </DialogContent>
      </Dialog>
    </>
  );
}

/** One request in the list: what it is, where it stands, its one date, and
 *  what needs her - a code to confirm, an answer to download. */
function RequestRow({
  request: r,
  selected,
  onChoose,
}: {
  request: MyRequest;
  selected: boolean;
  onChoose: () => void;
}) {
  const closed = r.status === "closed";
  const answered = r.responded_at ?? r.closed_at;
  return (
    <button
      type="button"
      aria-current={selected ? "true" : undefined}
      onClick={onChoose}
      className={cn(
        "block w-full px-4 py-3 text-left transition-colors hover:bg-surface-hover",
        selected &&
          "bg-accent-subtle shadow-[inset_3px_0_0_var(--accent)] hover:bg-accent-subtle",
      )}
    >
      <span className="flex items-center justify-between gap-2">
        <Mono className="text-sm font-semibold">{r.reference}</Mono>
        <RequestStatusBadge status={r.status} outcome={r.outcome} voice="self" />
      </span>
      <span className="mt-0.5 block text-xs text-text-muted">
        {REQUEST_TYPE_COPY[r.request_type].label} ·{" "}
        {closed && answered
          ? `answered ${formatDate(answered)}`
          : `answer by ${formatDate(r.due_at)}`}
      </span>
      <span className="mt-0.5 line-clamp-1 text-xs text-text-subtle">{r.request_text}</span>
      {r.download_available && (
        <span className="mt-1 inline-flex items-center gap-1 text-xs font-medium text-accent-text">
          <Download className="size-3" aria-hidden="true" />
          Ready to download
          {r.download_expires_at && ` until ${formatDate(r.download_expires_at)}`}
        </span>
      )}
      {r.verification_status === "pending" && !closed && (
        <span className="mt-1 block text-xs font-medium text-warning-text">
          Confirm it was you
        </span>
      )}
    </button>
  );
}
