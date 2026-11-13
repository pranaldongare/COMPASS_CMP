/**
 * Check in DataVault, on a rights request (0070).
 *
 * The DPO or Legal presses the button and the server asks DataVault what it
 * holds of this request's person; the platform also asks by itself when the
 * holders it finds include a project's DCO Admin. The card shows the last
 * answer and, if a later attempt failed, says so beside it: a failure does not
 * unsay what DataVault listed before.
 *
 * It changes nothing else on the request. With DataVault not set up, the
 * card says who sets it up and offers no button.
 *
 * The platform's own check runs in the background, a moment after the request
 * is started or its holders are found again, so its answer is not there when
 * the page reads the request back. While one is expected and nothing has come,
 * the card looks again for a short while, then stops: the button is still
 * there for whoever wants to ask now.
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DatabaseZap } from "lucide-react";
import * as React from "react";

import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Skeleton,
} from "@/components/ui/primitives";
import {
  checkInDataVault,
  datavaultKeys,
  getRequestDataVault,
} from "@/features/datavault/api";
import { AssetTable } from "@/features/datavault/components/asset-table";
import { formatDateTime } from "@/lib/format";
import { useToast } from "@/providers";
import type { Uuid } from "@/types";

function said(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}

/** How long the card looks for the platform's own check, and how often. */
const WATCH_FOR_MS = 45_000;
const WATCH_EVERY_MS = 2_500;

export function RequestDataVaultCard({
  requestUuid,
  platformAsks = false,
  holdersReadAt = null,
  watchEveryMs = WATCH_EVERY_MS,
}: {
  requestUuid: Uuid;
  /** A project's DCO Admin is among the holders found: the case in which the
   *  platform asks DataVault by itself. */
  platformAsks?: boolean;
  /** When the records were last read for who holds the data. Each reading
   *  may start the platform's check, so each starts the card looking afresh. */
  holdersReadAt?: string | null;
  watchEveryMs?: number;
}) {
  const toast = useToast();
  const client = useQueryClient();
  const key = datavaultKeys.request(requestUuid);
  const watch = React.useRef<{ of: string; since: number } | null>(null);
  const found = useQuery({
    queryKey: key,
    // The first read is somebody opening the page; a later one may be the
    // page looking again by itself, which must not keep the session awake.
    queryFn: () => getRequestDataVault(requestUuid, client.getQueryData(key) !== undefined),
    refetchInterval: (query) => {
      const now = query.state.data;
      const expected =
        platformAsks &&
        !!now &&
        now.configured &&
        !now.why_not &&
        !now.answer &&
        !now.last_failure;
      if (!expected) return false;
      const of = `${requestUuid}:${holdersReadAt ?? ""}`;
      if (watch.current?.of !== of) watch.current = { of, since: Date.now() };
      return Date.now() - watch.current.since < WATCH_FOR_MS ? watchEveryMs : false;
    },
  });
  const check = useMutation({
    mutationFn: () => checkInDataVault(requestUuid),
    onSuccess: (now) => {
      client.setQueryData(key, now);
      // The check is on the request's trail.
      void client.invalidateQueries({ queryKey: ["request", requestUuid, "trail"] });
      if (now.last_failure)
        toast.error("DataVault did not answer", now.last_failure.failure_said ?? undefined);
      else if (now.answer) {
        const n = now.answer.asset_count;
        toast.success(
          n === 0
            ? "DataVault holds nothing of this person"
            : `DataVault listed ${n} ${n === 1 ? "asset" : "assets"}`,
        );
      }
    },
    onError: (err) => toast.error("Not checked", said(err, "Try again in a moment.")),
  });

  if (found.isLoading) return <Skeleton className="h-28" />;
  // A console that reaches an API without this route yet shows nothing here
  // rather than an error on the request page.
  if (found.error || !found.data) return null;
  const d = found.data;

  return (
    <Card>
      <CardHeader className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle>DataVault</CardTitle>
          <p className="mt-1 text-xs text-text-muted">
            What DataVault holds of this person: each asset with its consent, project, MID
            and data path.
          </p>
        </div>
        {d.may_check && (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => check.mutate()}
            disabled={check.isPending}
          >
            <DatabaseZap className="size-4" />
            {check.isPending
              ? "Checking…"
              : d.answer
                ? "Check again in DataVault"
                : "Check in DataVault"}
          </Button>
        )}
      </CardHeader>
      <CardBody className="space-y-3">
        {!d.configured && (
          <Alert tone="info">
            DataVault is not set up. An administrator sets its address under DataVault
            connection.
          </Alert>
        )}
        {d.configured && d.why_not && <Alert tone="info">{d.why_not}</Alert>}
        {d.last_failure && (
          <Alert tone="warning" title="The last check was not answered">
            {d.last_failure.failure_said} Tried {formatDateTime(d.last_failure.asked_at)}
            {d.last_failure.automatic ? " by the platform" : ""}.
            {d.answer ? " The earlier answer is shown below." : ""}
          </Alert>
        )}
        {d.answer ? (
          <>
            <p className="text-sm text-text-muted">
              {d.answer.automatic
                ? "Checked by the platform when holders were found"
                : `Checked${d.answer.asked_by_name ? ` by ${d.answer.asked_by_name}` : ""}`}
              {" · "}
              {formatDateTime(d.answer.asked_at)}
            </p>
            {d.assets.length === 0 ? (
              <p className="text-sm">DataVault holds nothing of this person.</p>
            ) : (
              <AssetTable assets={d.assets} />
            )}
          </>
        ) : (
          d.configured &&
          !d.last_failure &&
          !d.why_not && (
            <p className="text-sm text-text-muted">
              Not checked yet.
              {platformAsks &&
                " A DCO Admin is among the holders, so the platform asks DataVault by itself; its answer appears here."}
            </p>
          )
        )}
      </CardBody>
    </Card>
  );
}
