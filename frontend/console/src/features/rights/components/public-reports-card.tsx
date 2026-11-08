/**
 * Reports from the public link: what an access or erasure request finds of the
 * reports the requester sent that an office dismissed (0065; the product
 * owner's fifth answer of 2026-11-07).
 *
 * A claimed report became an incident, the office's record of what it did, and
 * stays as it is. A dismissed one has nothing behind it, so the person who sent
 * it may see it and have their name and email taken off it. The server finds
 * them by email once identity is verified: the address a request with no
 * account gave, however it was verified, or an account's address once a code
 * sent to it has come back (never by the rights form's code, an officer's, or
 * one that accepted a nomination on an account already there). It says
 * whether they may be erased now and why not, and erases them all in one act:
 * this card names no report to the server, and holds no copy of the rule. It
 * says only what the server knows. Which of an account's addresses were looked
 * for is not served, so neither the header nor an empty list claims an address
 * was proved, or that the email shown for the requester was one of them. With
 * no address to look by it has not looked, and says so; the reports already
 * erased under the request are listed all the same.
 *
 * Shown to the DPO and Legal alone (`public_reports` is null for anyone else),
 * and never with the office's reason or who dismissed it.
 */
"use client";

import { Eraser } from "lucide-react";
import * as React from "react";

import { ConfirmDialog } from "@/components/ui/dialog";
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Mono,
} from "@/components/ui/primitives";
import { useErasePublicReports } from "@/features/rights/mutations";
import { formatDateTime } from "@/lib/format";
import { useToast } from "@/providers";
import type { RightsPublicReport, RightsRequestDetail } from "@/types";

function messageOf(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}

const reports = (n: number) => `${n} ${n === 1 ? "report" : "reports"}`;

function ReportLine({ report: p }: { report: RightsPublicReport }) {
  return (
    <li className="space-y-0.5 py-3 first:pt-0 last:pb-0">
      <p className="text-xs text-text-muted">
        <Mono>{p.reference}</Mono> · arrived {formatDateTime(p.received_at)} · dismissed{" "}
        {formatDateTime(p.dismissed_at)}
      </p>
      <p className="text-sm font-medium break-words">{p.title}</p>
      <p className="text-xs break-words text-text-muted">
        {p.reporter_erased_at
          ? `Name and email erased ${formatDateTime(p.reporter_erased_at)}`
          : `From ${[p.reporter_name, p.reporter_email].filter(Boolean).join(", ")}`}
      </p>
    </li>
  );
}

export function PublicReportsCard({ request: r }: { request: RightsRequestDetail }) {
  const toast = useToast();
  const erase = useErasePublicReports(r.request_uuid);
  const [confirming, setConfirming] = React.useState(false);
  const found = r.public_reports;
  if (!found) return null;
  const erasure = r.request_type === "erasure";
  const named = found.items.filter((p) => !p.reporter_erased_at).length;
  const more = found.total - named;

  async function go() {
    try {
      await erase.mutateAsync();
      toast.success(
        "Erased",
        "Their name and email are gone from those reports. The references, what they wrote, and why each was dismissed are kept.",
      );
    } catch (err) {
      toast.error("Not erased", messageOf(err, "The server refused."));
    } finally {
      setConfirming(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Reports from the public link</CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          Reports sent through the public link that an office did not take up, found by
          email once identity was verified: the address a request with no account gave, or
          an account&apos;s address once a code sent to it has come back, as at sign-up or
          sign-in. A code from the rights form, one read back to an officer, or one that
          accepted a nomination on an account already there, does not count. Both offices
          can read them under Dismissed reports.
        </p>
      </CardHeader>
      <CardBody className="space-y-4">
        {/* Not looked for, and why: with no address to look by, the reports
            erased under this request are still listed below it. */}
        {!found.looked && <Alert tone="info">{found.not_looked_because}</Alert>}
        {found.looked && found.items.length === 0 && (
          // Only what the server can see: a report an earlier erasure took the
          // address off is no longer found by it, though it came from them.
          // Said only once it has looked by an address, and never that the
          // email shown for the requester was one: an account's unproved
          // email is not looked for beside a proved second email.
          <p className="text-sm text-text-muted">
            No dismissed report from the public link carries an address that was looked for.
            An account&apos;s email is looked for only once a code sent to it has come back,
            so the email shown for the requester may not have been.
          </p>
        )}
        {found.items.length > 0 && (
          <ul className="divide-y divide-border">
            {found.items.map((p) => (
              <ReportLine key={p.report_uuid} report={p} />
            ))}
          </ul>
        )}
        {more > 0 && (
          <p className="text-xs text-text-muted">And {more} more, not listed here.</p>
        )}
        {found.looked && !erasure && found.total > 0 && (
          <p className="text-xs text-text-muted">These go to them with the response.</p>
        )}
        {erasure && found.total > 0 && (
          <div className="flex flex-wrap items-center gap-3">
            <Button
              variant="secondary"
              size="sm"
              disabled={!found.may_erase}
              title={found.erase_blocked_by ?? undefined}
              onClick={() => setConfirming(true)}
            >
              <Eraser className="size-4" />
              Erase their name and email from {reports(found.total)}
            </Button>
            {!found.may_erase && found.erase_blocked_by && (
              <span className="text-xs text-text-muted">{found.erase_blocked_by}</span>
            )}
          </div>
        )}
      </CardBody>
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title="Erase their name and email?"
        consequence="Their name and email are blanked on each report. The reference, what they wrote, why it was dismissed and who dismissed it are kept. This cannot be undone."
        confirmLabel="Erase name and email"
        loading={erase.isPending}
        onConfirm={go}
      />
    </Card>
  );
}
