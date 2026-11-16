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
 *
 * On an erasure request (0071) the card also tells DataVault to erase what it
 * listed: "Erase in DataVault", asked about first in a pop-up with the count,
 * sends what this request reaches and has not been sent, and "Check status"
 * asks how far each asset has got. Nothing about it runs by itself. Until it
 * may be pressed, the button stays greyed out with the server's reason beside
 * it. Each asset's place shows in the table.
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DatabaseZap } from "lucide-react";
import * as React from "react";

import { useConfirm } from "@/components/ui/confirm";
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
  checkErasureStatus,
  checkInDataVault,
  datavaultKeys,
  eraseInDataVault,
  getRequestDataVault,
  type DataVaultErasure,
  type DataVaultErasureStatus,
  type RequestDataVault,
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

const assets = (n: number) => `${n} ${n === 1 ? "asset" : "assets"}`;

/** The statuses as the summary line says them, in the order it says them. */
const SAID: [DataVaultErasureStatus, string][] = [
  ["erased", "erased"],
  ["pending", "pending"],
  ["unanswered", "not answered yet"],
  ["failed", "not erased"],
  ["not_held", "not held"],
];

/** "2 erased · 1 pending": where the request's assets stand, nothing for none. */
export function erasureSummary(e: DataVaultErasure): string {
  return SAID.filter(([status]) => e.counts[status] > 0)
    .map(([status, words]) => `${e.counts[status]} ${words}`)
    .join(" · ");
}

/** What an ask came back with, as a toast says it. */
function told(
  now: RequestDataVault,
  toast: ReturnType<typeof useToast>,
  first: boolean,
): void {
  const e = now.erasure;
  if (!e) return;
  if (e.last_failure) {
    toast.error(
      "DataVault did not answer",
      `${e.last_failure_said ?? ""} The instruction is kept: Check status sends it again.`,
    );
    return;
  }
  const line = erasureSummary(e);
  toast.success(first ? "Sent to DataVault" : "DataVault answered", line || undefined);
}

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
  const confirm = useConfirm();
  const afterErasure = (now: RequestDataVault, first: boolean) => {
    client.setQueryData(key, now);
    // On the request's trail, and the response warns of what is pending.
    void client.invalidateQueries({ queryKey: ["request", requestUuid, "trail"] });
    told(now, toast, first);
  };
  const erase = useMutation({
    mutationFn: () => eraseInDataVault(requestUuid),
    onSuccess: (now) => afterErasure(now, true),
    onError: (err) =>
      toast.error("Not sent to DataVault", said(err, "Try again in a moment.")),
  });
  const status = useMutation({
    mutationFn: () => checkErasureStatus(requestUuid),
    onSuccess: (now) => afterErasure(now, false),
    onError: (err) => toast.error("Not asked", said(err, "Try again in a moment.")),
  });

  async function pressErase(e: DataVaultErasure) {
    const n = e.to_send;
    const yes = await confirm.ask({
      title: `Tell DataVault to erase ${assets(n)}?`,
      consequence: (
        <>
          DataVault erases {n === 1 ? "it" : "each"} whole, and this cannot be taken back.
          {e.left_out > 0 &&
            ` ${assets(e.left_out)} DataVault listed ${e.left_out === 1 ? "is" : "are"} left out: this request does not reach ${e.left_out === 1 ? "it" : "them"}.`}{" "}
          What DataVault answers for each is shown here, and on the request&apos;s trail.
        </>
      ),
      confirmLabel: "Erase in DataVault",
      tone: "danger",
    });
    if (yes) erase.mutate();
  }

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
              <AssetTable assets={d.assets} erasure={d.erasure !== null} />
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
        {d.erasure && d.configured && (
          <ErasureControls
            e={d.erasure}
            erasing={erase.isPending}
            asking={status.isPending}
            onErase={() => void pressErase(d.erasure!)}
            onStatus={() => status.mutate()}
          />
        )}
        {confirm.dialog}
      </CardBody>
    </Card>
  );
}

/** "Erase in DataVault" and "Check status", with where things stand. The
 *  erase button shows greyed out with the reason while it may not be
 *  pressed; a reader who may not act on the request is shown neither. */
function ErasureControls({
  e,
  erasing,
  asking,
  onErase,
  onStatus,
}: {
  e: DataVaultErasure;
  erasing: boolean;
  asking: boolean;
  onErase: () => void;
  onStatus: () => void;
}) {
  const summary = erasureSummary(e);
  const offered = e.may_erase || e.why_not !== null;
  if (!offered && !e.may_check_status && !summary) return null;
  return (
    <section
      aria-label="Erasure in DataVault"
      className="space-y-2 border-t border-border pt-3"
    >
      <h3 className="text-sm font-semibold">Erasure in DataVault</h3>
      {summary ? (
        <p className="text-sm">
          {summary}
          {e.last_asked_at && (
            <span className="text-text-muted">
              {" · "}last asked {formatDateTime(e.last_asked_at)}
            </span>
          )}
        </p>
      ) : (
        <p className="text-sm text-text-muted">Nothing has been sent to DataVault yet.</p>
      )}
      {e.last_failure && (
        <Alert tone="warning" title="The last ask was not answered">
          {e.last_failure_said} The instruction is kept: Check status sends it again.
        </Alert>
      )}
      <div className="flex flex-wrap items-center gap-2">
        {offered && (
          <Button
            variant="danger"
            size="sm"
            onClick={onErase}
            disabled={!e.may_erase || erasing}
            loading={erasing}
            aria-describedby={e.why_not ? "datavault-erase-why-not" : undefined}
          >
            {e.may_erase
              ? `Erase in DataVault (${assets(e.to_send)})`
              : "Erase in DataVault"}
          </Button>
        )}
        {e.may_check_status && (
          <Button
            variant="secondary"
            size="sm"
            onClick={onStatus}
            disabled={asking}
            loading={asking}
          >
            Check status
          </Button>
        )}
      </div>
      {e.why_not && (
        <p id="datavault-erase-why-not" className="text-xs text-text-muted">
          {e.why_not}
        </p>
      )}
      {e.left_out > 0 && (
        <p className="text-xs text-text-muted">
          {assets(e.left_out)} DataVault listed {e.left_out === 1 ? "is" : "are"} left out:
          this request does not reach {e.left_out === 1 ? "it" : "them"}. A request reaches
          only assets matched to this person&apos;s records in its own office - and, about
          one consent, only that consent&apos;s - and DataVault must have given a consent
          for each.
        </p>
      )}
      {e.open > 0 && (
        <p className="text-xs text-text-muted">
          {assets(e.open)} {e.open === 1 ? "is" : "are"} still with DataVault. Nothing asks
          by itself: press Check status to hear where {e.open === 1 ? "it" : "they"} stand.
          The request can close meanwhile.
        </p>
      )}
    </section>
  );
}
