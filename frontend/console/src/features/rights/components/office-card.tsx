/**
 * Which office answers a request, and moving it (0055).
 *
 * A request arrives in an office's queue when the person's consents say
 * which; otherwise in the shared intake, which both offices see until one
 * claims it. An office that holds a request can transfer it to the other
 * with a reason; the clock does not move, and the request leaves this
 * office's view with the transfer - so the page goes back to the register.
 *
 * The server decides who may do either; the buttons only ask.
 */
"use client";

import { ArrowRightLeft, Inbox } from "lucide-react";
import { useRouter } from "next/navigation";
import * as React from "react";

import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Field,
  Textarea,
} from "@/components/ui/primitives";
import { useClaimRequest, useTransferRequest } from "@/features/rights/mutations";
import { ApiError } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { useAuth, useToast } from "@/providers";
import type { RightsRequestDetail, RightsRequestRow } from "@/types";

export const OFFICE_TITLES: Record<string, string> = { rnd: "DPO office", hr: "Legal office" };

export function officeTitle(office: string | null): string {
  return office ? (OFFICE_TITLES[office] ?? office) : "Shared intake";
}

function messageOf(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.userMessage() : fallback;
}

/** On a row of the register: take a request out of the shared intake. */
export function ClaimButton({ request: r }: { request: RightsRequestRow }) {
  const toast = useToast();
  const { me } = useAuth();
  const claim = useClaimRequest(r.request_uuid);
  if (r.office !== null || r.status === "closed" || !me?.office) return null;
  return (
    <Button
      variant="secondary"
      size="sm"
      loading={claim.isPending}
      onClick={async () => {
        try {
          await claim.mutateAsync();
          toast.success(`${r.reference} is now with your office`);
        } catch (err) {
          toast.error("Not claimed", messageOf(err, "The server refused."));
        }
      }}
    >
      Claim
    </Button>
  );
}

export function OfficeCard({ request: r }: { request: RightsRequestDetail }) {
  const toast = useToast();
  const router = useRouter();
  const { me } = useAuth();
  const claim = useClaimRequest(r.request_uuid);
  const transfer = useTransferRequest(r.request_uuid);
  const [moving, setMoving] = React.useState(false);
  const [reason, setReason] = React.useState("");

  const closed = r.status === "closed";
  const officer = Boolean(me?.office);
  const other = r.office === "rnd" ? "hr" : "rnd";

  return (
    <Card>
      <CardHeader>
        <CardTitle>{r.office ? `With the ${officeTitle(r.office)}` : "In the shared intake"}</CardTitle>
      </CardHeader>
      <CardBody className="space-y-3">
        {r.office === null ? (
          <p className="text-sm text-text-muted">
            Nobody could tell on receipt which office holds this person&apos;s data, so both offices
            see it. Verify who it is, then claim it for your office; work starts once it is claimed.
          </p>
        ) : (
          <p className="text-sm text-text-muted">
            {r.claimed_at && `Claimed from the shared intake on ${formatDateTime(r.claimed_at)}. `}
            {r.transferred_from &&
              `Transferred from the ${officeTitle(r.transferred_from)}${
                r.transferred_at ? ` on ${formatDateTime(r.transferred_at)}` : ""
              }.`}
          </p>
        )}
        {r.transfer_reason && (
          <p className="rounded-md bg-bg-inset p-3 text-sm whitespace-pre-wrap">{r.transfer_reason}</p>
        )}

        {!closed && officer && r.office === null && (
          <Button
            variant="primary"
            size="sm"
            loading={claim.isPending}
            onClick={async () => {
              try {
                await claim.mutateAsync();
                toast.success("Claimed for your office");
              } catch (err) {
                toast.error("Not claimed", messageOf(err, "The server refused."));
              }
            }}
          >
            <Inbox className="size-4" aria-hidden="true" />
            Claim for my office
          </Button>
        )}

        {!closed && officer && r.office !== null && !moving && (
          <Button variant="secondary" size="sm" onClick={() => setMoving(true)}>
            <ArrowRightLeft className="size-4" aria-hidden="true" />
            Transfer to the {officeTitle(other)}
          </Button>
        )}
        {moving && (
          <div className="space-y-2">
            <Alert tone="info">
              <p className="text-sm">
                The received date and the due date stay as they are. The {officeTitle(other)} is
                emailed, and the request leaves your queue.
              </p>
            </Alert>
            <Field label="Why it belongs to the other office" required>
              {(p) => (
                <Textarea
                  {...p}
                  rows={3}
                  maxLength={1000}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
              )}
            </Field>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="primary"
                size="sm"
                loading={transfer.isPending}
                disabled={!reason.trim()}
                onClick={async () => {
                  try {
                    const moved = await transfer.mutateAsync({ office: other, reason: reason.trim() });
                    toast.success(`${moved.reference} transferred to the ${officeTitle(moved.office)}`);
                    router.push("/requests");
                  } catch (err) {
                    toast.error("Not transferred", messageOf(err, "The server refused."));
                  }
                }}
              >
                Transfer
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setMoving(false)}>
                Cancel
              </Button>
            </div>
          </div>
        )}
      </CardBody>
    </Card>
  );
}
