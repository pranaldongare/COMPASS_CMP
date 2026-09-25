/**
 * The data principal's requests - sections 11 to 14, from her side.
 *
 * What she sees of a request is what she is entitled to: the reference, the
 * clock, where it is on the path, and the response when there is one. The
 * verification notes and the holder tickets are ours and are not here; the
 * holders themselves are in the response, which is where they belong.
 *
 * Two things are one click away because the Act says they should be: making
 * a request, and disputing a response. A grievance is not an appeal against
 * the outcome alone - late, incomplete, or sent the wrong way all count.
 *
 * A grievance and the request it disputes are both hers, so they are both on
 * this page: the grievance card says what she disputed and jumps to it, and
 * the original says it was disputed and jumps back. No second page to find.
 */
"use client";

import { Plus } from "lucide-react";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { EmptyRecords } from "@/components/ui/graphics";
import { Alert, Button, Card, EmptyState, Skeleton } from "@/components/ui/primitives";
import { NominationCard } from "@/features/rights/components/nomination-card";
import { NomineeOfCard } from "@/features/rights/components/nominee-of-card";
import { MyRequestForm } from "@/features/rights/components/request-form";
import { useMyRequests } from "@/features/rights/queries";
import { RequestCard, cardId } from "@/features/rights/components/request-card";
import {
  FILTER_FROM,
  RequestFilter,
  useRequestFilter,
} from "@/features/rights/components/request-filter";
import { relate } from "@/features/rights/relate";

export default function MyRequestsPage() {
  const requests = useMyRequests();
  const [asking, setAsking] = React.useState(false);
  const [open, setOpen] = React.useState<string | null>(null);
  const [flash, setFlash] = React.useState<string | null>(null);
  const { byUuid, followers } = relate(requests.data ?? []);
  const filter = useRequestFilter(requests.data ?? []);
  const filtering = (requests.data?.length ?? 0) >= FILTER_FROM;
  // A card to bring into view once it is rendered: after a jump that had to
  // widen the filter, the card does not exist until the next commit. The jump
  // itself always renders (it sets the flash), and this runs after it.
  const scrollTo = React.useRef<string | null>(null);
  React.useEffect(() => {
    if (!scrollTo.current) return;
    document
      .getElementById(cardId(scrollTo.current))
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
    scrollTo.current = null;
  });

  React.useEffect(() => {
    if (!flash) return;
    const timer = window.setTimeout(() => setFlash(null), 1800);
    return () => window.clearTimeout(timer);
  }, [flash]);

  function jump(uuid: string) {
    setOpen(uuid);
    setFlash(uuid);
    if (!filter.isShown(uuid)) filter.reset();
    scrollTo.current = uuid;
  }

  return (
    <>
      <PageHeader
        title="Your requests"
        description="Ask for access to your data, a correction, erasure, or raise a grievance. Every request runs on a published clock, and you can see where it is."
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

      {filtering && <RequestFilter filter={filter} />}

      {filtering && filter.shown.length === 0 && (
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

      <div className="space-y-4">
        {(filtering ? filter.shown : (requests.data ?? [])).map((r) => (
          <RequestCard
            key={r.request_uuid}
            request={r}
            about={
              r.linked_request_uuid ? (byUuid.get(r.linked_request_uuid) ?? null) : null
            }
            followedBy={followers.get(r.request_uuid) ?? []}
            expanded={open === r.request_uuid}
            highlighted={flash === r.request_uuid}
            onToggle={() => setOpen(open === r.request_uuid ? null : r.request_uuid)}
            onJump={jump}
          />
        ))}
      </div>

      <div className="mt-8 space-y-6">
        {/* First: something somebody else needs from her is more pressing
            than something she may one day arrange. Absent when there is none. */}
        <NomineeOfCard />
        <NominationCard />
      </div>

      <Dialog open={asking} onOpenChange={(next) => !next && setAsking(false)}>
        <DialogContent
          title="Make a request"
          description="You are signed in, so this counts as verified and the clock starts now."
        >
          <MyRequestForm
            onDone={(created) => {
              setAsking(false);
              setOpen(created.request_uuid);
            }}
          />
        </DialogContent>
      </Dialog>
    </>
  );
}
