/**
 * Steps 5 and 6 of erasure: scope determined; inside the one-year floor?
 *
 * One row per appearance of her in a collected asset. The number that decides
 * the shape of each decision is `other_subjects`: zero is ordinary erasure,
 * anything else is redaction, because deleting the file would erase the other
 * people's validly given consent along with her contribution. The server
 * refuses "erase" on such an asset; this screen says why before the click.
 *
 * Disposition sits on her junction row. Applying a decision quarantines her
 * appearance at once - the platform's own flag, and the first step whatever
 * the decision. An erasure or redaction is then carried out store by store
 * (S2-03): the holder's copy, confirmed by its returned ticket, and for an
 * erasure the platform's pointer to the asset. Each store's state is the
 * server's, shown as it stands - done, waiting, failed or stopped by a legal
 * hold - and "erased" only appears once every store is done.
 */
"use client";

import { Lock, RotateCcw, ShieldAlert, Unlock, Wand2 } from "lucide-react";
import * as React from "react";

import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Field,
  Input,
  Select,
  Textarea,
} from "@/components/ui/primitives";
import { ConfinedNote } from "@/features/rights/components/consent-scope";
import {
  useApplyItem,
  useDecideItem,
  useDeriveScope,
  useExecuteItem,
  usePlaceHold,
  useReleaseHold,
} from "@/features/rights/mutations";
import { formatDate } from "@/lib/format";
import { useToast } from "@/providers";
import type {
  RightsItemExecution,
  RightsRequestDetail,
  RightsScopeDecision,
  RightsScopeItem,
} from "@/types";

function messageOf(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}

const DECISION_COPY: Record<RightsScopeDecision, string> = {
  erase: "Erase - the asset holds only her",
  redact: "Redact - remove her, keep the others",
  retain: "Retain - a floor binds, erased when it passes",
  quarantine: "Quarantine - removal cannot be assured; the DPO decides",
};

const STORE_COPY: Record<RightsItemExecution["store"], string> = {
  holder_copy: "The holder's copy",
  platform_pointer: "The platform's pointer to it",
  legal_hold: "Legal hold",
};

const WAITING_COPY: Record<string, string> = {
  no_holder: "no holder has been asked for this asset's copy - confirm the source's holder and issue its ticket",
  awaiting_return: "waiting for the holder's ticket to come back",
  ticket_not_issued: "the holder's ticket has not been issued",
  ticket_withdrawn: "the holder's ticket was withdrawn",
  ticket_unreturned: "the holder did not return its ticket",
};

/** One store's state in words. The facts are the server's; this only phrases them. */
function executionText(e: RightsItemExecution): string {
  const reason = typeof e.detail.reason === "string" ? e.detail.reason : "";
  switch (e.status) {
    case "done":
      return e.store === "holder_copy" ? "confirmed gone by the holder" : "cleared";
    case "waiting":
      return WAITING_COPY[reason] ?? "waiting";
    case "held":
      return "stopped until the hold is released";
    case "failed":
      return `failed (${String(e.detail.error ?? "error")}) - retried daily, or try again now`;
  }
}

export function ScopeCard({ request: r }: { request: RightsRequestDetail }) {
  const toast = useToast();
  const derive = useDeriveScope(r.request_uuid);
  const canWork = r.status !== "closed" && r.status !== "received";

  return (
    <Card>
      <CardHeader className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle>5–6 · Scope determined; inside the one-year floor?</CardTitle>
          <p className="mt-1 text-xs text-text-muted">
            What can go, what must stay, and the legal basis for each. Rule 6 and Rule 8(3) bind
            even against her own request.
          </p>
          {r.consent_uuid && <ConfinedNote project={r.consent_project} />}
        </div>
        {canWork && (
          <Button
            variant="secondary"
            size="sm"
            loading={derive.isPending}
            onClick={async () => {
              try {
                const items = await derive.mutateAsync();
                toast.success("Scope derived", `${items.length} appearance${items.length === 1 ? "" : "s"} of her in collected assets.`);
              } catch (err) {
                toast.error("Not derived", messageOf(err, "The server refused."));
              }
            }}
          >
            <Wand2 className="size-4" />
            Derive from asset_consent
          </Button>
        )}
      </CardHeader>
      <CardBody className="space-y-4">
        <Alert tone="info">
          <p className="text-sm">
            Consent artefacts are never erased. They are the evidence that past processing was
            lawful - s.6(4) depends on them surviving. Erasure changes what is held, not what was
            agreed.
          </p>
        </Alert>
        {r.items.length === 0 ? (
          <p className="text-sm text-text-muted">
            {canWork ? "No scope yet. Derive it from the records she appears in." : "Nothing in scope."}
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {r.items.map((item) => (
              <ItemRow key={item.item_uuid} request={r} item={item} canWork={canWork} />
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}

function ItemRow({ request: r, item, canWork }: { request: RightsRequestDetail; item: RightsScopeItem; canWork: boolean }) {
  const toast = useToast();
  const decide = useDecideItem(r.request_uuid);
  const apply = useApplyItem(r.request_uuid);
  const execute = useExecuteItem(r.request_uuid);
  const placeHold = usePlaceHold(r.request_uuid);
  const releaseHold = useReleaseHold(r.request_uuid);
  const [holdReason, setHoldReason] = React.useState("");
  const [holding, setHolding] = React.useState(false);
  const execution = item.execution ?? [];
  const hold = execution.find((e) => e.store === "legal_hold" && e.status === "held");
  const carriedOut = Boolean(item.executed_at);
  const [decision, setDecision] = React.useState<RightsScopeDecision>(
    item.decision ?? (item.other_subjects > 0 ? "redact" : "erase"),
  );
  const [basis, setBasis] = React.useState(item.basis ?? "");
  const [until, setUntil] = React.useState(item.retain_until ?? "");
  const holdsOthers = item.other_subjects > 0;
  const applied = item.state === "applied";
  const inProgress = applied && !carriedOut && item.decision !== "quarantine";

  async function save() {
    try {
      await decide.mutateAsync({
        itemUuid: item.item_uuid,
        decision,
        basis,
        retain_until: decision === "retain" ? until || null : null,
        holder_uuid: item.holder_uuid,
      });
      toast.success("Decision recorded");
    } catch (err) {
      toast.error("Not recorded", messageOf(err, "The server refused."));
    }
  }

  async function doApply() {
    try {
      const result = await apply.mutateAsync(item.item_uuid);
      toast.success(
        result.executed_at ? `Her row is now ${result.disposition}` : "Quarantined",
        result.executed_at
          ? "Every store holding it is confirmed."
          : "It is out of use now; it is erased when every store holding it is confirmed.",
      );
    } catch (err) {
      toast.error("Not applied", messageOf(err, "The server refused."));
    }
  }

  async function retry() {
    try {
      const result = await execute.mutateAsync(item.item_uuid);
      toast.success(result.executed_at ? "Carried out" : "Tried again", result.executed_at ? undefined : "Something is still outstanding; it is shown below.");
    } catch (err) {
      toast.error("Not tried", messageOf(err, "The server refused."));
    }
  }

  async function doHold() {
    try {
      await placeHold.mutateAsync({ asset_uuid: item.asset_uuid, reason: holdReason });
      setHolding(false);
      setHoldReason("");
      toast.success("Legal hold placed", "Nothing covered by it is erased until it is released.");
    } catch (err) {
      toast.error("No hold placed", messageOf(err, "The server refused."));
    }
  }

  async function doRelease(holdUuid: string) {
    try {
      await releaseHold.mutateAsync(holdUuid);
      toast.success("Hold released", "What it was stopping carries on.");
    } catch (err) {
      toast.error("Not released", messageOf(err, "The server refused."));
    }
  }

  return (
    <li className="space-y-3 py-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="flex flex-wrap items-center gap-2 text-sm font-medium">
            {item.source_asset_ref}
            <Badge tone="neutral" dot={false}>{item.asset_type}</Badge>
            {holdsOthers ? (
              <Badge tone="warning">
                <ShieldAlert className="mr-1 size-3" aria-hidden="true" />
                holds {item.other_subjects} other {item.other_subjects === 1 ? "person" : "people"}
              </Badge>
            ) : (
              <Badge tone="neutral" dot={false}>only her</Badge>
            )}
            {applied && (carriedOut || item.decision === "quarantine") && <Badge tone="success">{item.disposition}</Badge>}
            {inProgress && !hold && <Badge tone="warning">quarantined - being {item.decision === "redact" ? "redacted" : "erased"}</Badge>}
            {hold && <Badge tone="danger"><Lock className="mr-1 size-3" aria-hidden="true" />legal hold</Badge>}
            {!applied && item.decision && <Badge tone="info" dot={false}>decided: {item.decision}</Badge>}
          </p>
          <p className="mt-0.5 text-xs text-text-muted">
            {item.project_name} · {item.source_name} ({item.source_code})
            {item.processor_name && ` · held by ${item.processor_name}`} · collected {formatDate(item.collected_on)}
            {item.holder_label && ` · ticket: ${item.holder_label} (${item.holder_ticket_status})`}
          </p>
          {item.retain_until && (
            <p className="mt-0.5 text-xs text-warning-text">
              Retained until {formatDate(item.retain_until)}
              {item.floor_passed_at && " - the floor has passed; apply the erasure"}
            </p>
          )}
          {item.basis && <p className="mt-1 text-xs italic text-text-subtle">&ldquo;{item.basis}&rdquo;</p>}
          {applied && execution.length > 0 && (
            <ul className="mt-2 space-y-0.5 text-xs" aria-label="Where each store stands">
              {execution.map((e) => (
                <li key={e.store} className={e.status === "done" ? "text-success-text" : e.status === "failed" ? "text-danger-text" : "text-text-muted"}>
                  {STORE_COPY[e.store]}: {executionText(e)}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          {canWork && !applied && item.decision && (
            <Button variant="primary" size="sm" loading={apply.isPending} onClick={doApply}>
              Apply
            </Button>
          )}
          {inProgress && !hold && (
            <Button variant="secondary" size="sm" loading={execute.isPending} onClick={retry}>
              <RotateCcw className="size-4" />
              Try again now
            </Button>
          )}
          {hold && typeof hold.detail.hold === "string" && (
            <Button variant="secondary" size="sm" loading={releaseHold.isPending} onClick={() => doRelease(String(hold.detail.hold))}>
              <Unlock className="size-4" />
              Release hold
            </Button>
          )}
          {!carriedOut && !hold && !holding && (
            <Button variant="ghost" size="sm" onClick={() => setHolding(true)}>
              <Lock className="size-4" />
              Place a legal hold
            </Button>
          )}
        </div>
      </div>

      {holding && (
        <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
          <Field label="Why this asset must not be erased" hint="Sealed, and shown only to the Privacy Office." required>
            {(p) => <Textarea {...p} rows={1} value={holdReason} onChange={(e) => setHoldReason(e.target.value)} />}
          </Field>
          <div className="flex items-end gap-2">
            <Button variant="primary" size="sm" disabled={holdReason.trim().length < 3} loading={placeHold.isPending} onClick={doHold}>
              Place the hold
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setHolding(false)}>
              Cancel
            </Button>
          </div>
        </div>
      )}

      {canWork && !applied && (
        <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,2fr)_auto]">
          <Field label="Decision">
            {(p) => (
              <Select {...p} value={decision} onChange={(e) => setDecision(e.target.value as RightsScopeDecision)}>
                <option value="erase" disabled={holdsOthers}>{DECISION_COPY.erase}</option>
                <option value="redact">{DECISION_COPY.redact}</option>
                <option value="retain">{DECISION_COPY.retain}</option>
                <option value="quarantine">{DECISION_COPY.quarantine}</option>
              </Select>
            )}
          </Field>
          <Field label="Basis" hint="The legal basis, in a sentence. It is stated in the response." required>
            {(p) => <Textarea {...p} rows={1} value={basis} onChange={(e) => setBasis(e.target.value)} />}
          </Field>
          {decision === "retain" ? (
            <Field label="Until" required>
              {(p) => <Input {...p} type="date" value={until} onChange={(e) => setUntil(e.target.value)} />}
            </Field>
          ) : (
            <div />
          )}
          <div className="sm:col-span-3">
            <Button variant="secondary" size="sm" disabled={basis.trim().length < 3 || (decision === "retain" && !until)} loading={decide.isPending} onClick={save}>
              Record the decision
            </Button>
            {holdsOthers && (
              <span className="ml-3 text-xs text-text-muted">
                Erase is not offered: deleting this asset would erase the other people&apos;s validly given consent.
              </span>
            )}
          </div>
        </div>
      )}
    </li>
  );
}
