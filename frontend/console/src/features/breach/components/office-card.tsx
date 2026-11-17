/**
 * Whose an incident or breach is, and two things an officer does about that
 * (0073, ADR 0042).
 *
 * **Reassign to the other office.** For one an office took up and then found
 * was the other's. It goes as it stands: its status, its validation, its
 * duties and their clocks, its people, reports and tickets are not touched,
 * and nothing starts again. It leaves this office's register, so the page
 * goes back to the list.
 *
 * **Send acknowledgement.** The person who reported it through the public
 * link is thanked and told the office is dealing with it - and no more. They
 * may be nobody the incident touched, so what the office found or did is not
 * sent to them.
 */
"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowRightLeft, MailCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import * as React from "react";

import { useConfirm } from "@/components/ui/confirm";
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
import { acknowledgeReporter, transferBreach } from "@/features/breach/api";
import { messageOf } from "@/features/breach/components/record-breach";
import { formatDateTime } from "@/lib/format";
import { keys } from "@/lib/query";
import { useAuth, useToast } from "@/providers";
import type { Breach } from "@/types";

const OFFICE_TITLES: Record<string, string> = { rnd: "DPO office", hr: "Legal office" };
const officeTitle = (office: string) => OFFICE_TITLES[office] ?? office;

export function BreachOfficeCard({ breach: b }: { breach: Breach }) {
  const toast = useToast();
  const router = useRouter();
  const qc = useQueryClient();
  const { me } = useAuth();
  const [moving, setMoving] = React.useState(false);
  const [reason, setReason] = React.useState("");
  const other = b.office === "rnd" ? "hr" : "rnd";
  const what = b.breach_reference ? "breach" : "incident";
  const transfer = useMutation({
    mutationFn: () => transferBreach(b.breach_uuid, { office: other, reason: reason.trim() }),
    onSuccess: (moved) => {
      // It is not this office's any more: nothing cached of it may be shown
      // again, by Back or by a link, as if it were.
      qc.removeQueries({ queryKey: keys.breach.detail(b.breach_uuid) });
      void qc.invalidateQueries({ queryKey: ["breaches"] });
      toast.success(
        `${moved.reference} reassigned to the ${officeTitle(moved.office)}`,
        "It has left your register. Their officers have been emailed.",
      );
      router.push("/breaches");
    },
    onError: (err) => toast.error("Not reassigned", messageOf(err, "The server refused.")),
  });
  const mayMove = b.status === "open" && Boolean(me?.office);

  return (
    <Card data-testid="breach-office">
      <CardHeader>
        <CardTitle>With the {officeTitle(b.office)}</CardTitle>
      </CardHeader>
      <CardBody className="space-y-3">
        {b.transferred && (
          <>
            <p className="text-sm text-text-muted">
              Reassigned from the {officeTitle(b.transferred.from_office)} on {formatDateTime(b.transferred.at)}
              {b.transferred.transferred_by_name ? ` by ${b.transferred.transferred_by_name}` : ""}.
            </p>
            <p className="rounded-md bg-bg-inset p-3 text-sm break-words whitespace-pre-wrap">
              {b.transferred.transfer_reason}
            </p>
          </>
        )}
        {mayMove && !moving && (
          <>
            <p className="text-sm text-text-muted">
              If this {what} belongs to the other office, reassign it. It goes exactly as it stands.
            </p>
            <Button variant="secondary" size="sm" onClick={() => setMoving(true)}>
              <ArrowRightLeft className="size-4" aria-hidden="true" />
              Reassign to the {officeTitle(other)}
            </Button>
          </>
        )}
        {moving && (
          <div className="space-y-2">
            <Alert tone="info">
              <p className="text-sm">
                Its status, validation, duties and their clocks, people, reports and tickets stay as they are: nothing
                starts again. The {officeTitle(other)} is emailed, and the {what} leaves your register.
              </p>
            </Alert>
            <Field label="Why it belongs to the other office" required>
              {(p) => (
                <Textarea {...p} rows={3} maxLength={2000} value={reason} onChange={(e) => setReason(e.target.value)} />
              )}
            </Field>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="primary"
                size="sm"
                loading={transfer.isPending}
                disabled={!reason.trim()}
                onClick={() => transfer.mutate()}
              >
                Reassign
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

/** Under "Reported by": whether the reporter has been acknowledged, and the
 *  button that does it. Asked first: a mail cannot be taken back. */
export function AcknowledgeReporter({ breach: b }: { breach: Breach }) {
  const toast = useToast();
  const qc = useQueryClient();
  const asking = useConfirm();
  const { me } = useAuth();
  const send = useMutation({
    mutationFn: () => acknowledgeReporter(b.breach_uuid),
    onSuccess: (fresh) => {
      qc.setQueryData(keys.breach.detail(b.breach_uuid), fresh);
      toast.success("Acknowledgement sent", "The reporter is thanked and told the office is dealing with it.");
    },
    onError: (err) => toast.error("Not sent", messageOf(err, "The server refused.")),
  });
  const r = b.reported;
  if (!r) return null;
  const sent = r.acknowledgements > 0;
  return (
    <div className="space-y-2" data-testid="acknowledge-reporter">
      <p className="text-sm">
        {sent && r.acknowledged_at
          ? `Sent ${formatDateTime(r.acknowledged_at)}${r.acknowledged_by_name ? ` by ${r.acknowledged_by_name}` : ""}${
              r.acknowledgements > 1 ? ` (${r.acknowledgements} times in all)` : ""
            }`
          : "Not sent yet"}
      </p>
      {Boolean(me?.office) && (
        <Button
          variant="secondary"
          size="sm"
          loading={send.isPending}
          onClick={async () => {
            if (
              await asking.ask({
                title: sent ? "Send the acknowledgement again?" : "Send an acknowledgement to the reporter?",
                consequence: `${r.reporter_email} is thanked for the report and told the office is dealing with it. Nothing about what was found, decided or done is sent.`,
                confirmLabel: "Send acknowledgement",
              })
            )
              send.mutate();
          }}
        >
          <MailCheck className="size-4" aria-hidden="true" />
          {sent ? "Send acknowledgement again" : "Send acknowledgement"}
        </Button>
      )}
      <p className="text-xs text-text-subtle">
        Only an acknowledgement goes to the reporter. The breach&apos;s actions and reports are not sent to them.
      </p>
      {asking.dialog}
    </div>
  );
}
