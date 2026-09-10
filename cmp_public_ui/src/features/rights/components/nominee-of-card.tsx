/**
 * Nominations that name her - the other side of `NominationCard`.
 *
 * A data principal can also be somebody else's nominee, and until this existed
 * her account said nothing about it: the acceptance link came by message, she
 * accepted, and then nothing in her console showed who she could act for, or
 * how. Everything she needs is here - the reference, whose rights, whether it
 * is in effect - and the way onward is the same nominee page everyone uses,
 * with the reference filled in. Acting still needs a code to the contact the
 * principal recorded; being signed in is not that proof.
 *
 * Renders nothing when there is nothing: most people are nobody's nominee.
 */
"use client";

import { ArrowRight, Copy, UserRoundCheck } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { Alert, Badge, Button, Card, CardBody, CardHeader, CardTitle, Mono } from "@/components/ui/primitives";
import { REQUEST_TYPE_COPY } from "@/features/rights/components/copy";
import { useNominationsNamingMe } from "@/features/rights/queries";
import { formatDate } from "@/lib/format";
import type { NomineeOf } from "@/types";

export function NomineeOfCard() {
  const naming = useNominationsNamingMe();
  const list = naming.data ?? [];
  if (!naming.data || list.length === 0) return null;

  return (
    <Card data-testid="nominee-of">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <UserRoundCheck className="size-4" aria-hidden="true" />
          Somebody has named you to act for them
        </CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          Section 14. If they die or cannot act, you may exercise the rights they granted you.
          Nothing runs until then, and the Privacy Office decides first whether the event is
          evidenced.
        </p>
      </CardHeader>
      <CardBody className="space-y-5">
        {list.map((n) => (
          <NomineeOfRow key={n.nomination_uuid} n={n} />
        ))}
      </CardBody>
    </Card>
  );
}

function NomineeOfRow({ n }: { n: NomineeOf }) {
  const [copied, setCopied] = React.useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(n.nomination_uuid);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // No clipboard here - the reference is still on screen to select.
    }
  }
  const rights = n.rights.map((r) => REQUEST_TYPE_COPY[r].label.toLowerCase()).join(", ");

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium">{n.principal_name}</p>
          <p className="text-xs text-text-muted">
            Recorded you as {n.contact}. May ask for: {rights}.
          </p>
        </div>
        <Badge tone={n.status === "active" ? "success" : "warning"}>
          {n.status === "active" ? "In place" : "Awaiting your acceptance"}
        </Badge>
      </div>

      {n.invoked_at && (
        <Alert tone="info" title={`You acted on ${formatDate(n.invoked_at)}`}>
          <p className="text-sm">
            You reported {n.invoked_event === "death" ? "that they have died" : "that they cannot act for themselves"}
            {n.invoked_reference && (
              <>
                {" "}
                and made request <Mono>{n.invoked_reference}</Mono>
              </>
            )}
            .{" "}
            {n.invoked_evidenced_at
              ? `The Privacy Office found the event evidenced on ${formatDate(n.invoked_evidenced_at)}.`
              : "The Privacy Office decides first whether the event is evidenced."}
          </p>
        </Alert>
      )}

      {n.status === "pending" ? (
        <Alert tone="warning">
          <p className="text-sm">
            Not yet in effect. Accept or decline from the link we sent to {n.contact}
            {n.accept_expires_at && ` - it expires on ${formatDate(n.accept_expires_at)}`}. The
            link alone is not enough; a code goes to that contact.
          </p>
        </Alert>
      ) : (
        <div className="space-y-3">
          <p className="text-xs text-text-muted">
            Your nomination reference - you will need it to act, and it was also sent to you
            when you accepted:
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <Mono className="break-all text-sm" data-testid="nominee-of-reference">
              {n.nomination_uuid}
            </Mono>
            <Button type="button" variant="subtle" size="sm" onClick={copy}>
              <Copy className="size-4" aria-hidden="true" />
              {copied ? "Copied" : "Copy"}
            </Button>
          </div>
          <Button asChild variant="primary" size="sm">
            <Link href={`/rights/nominee?nomination=${encodeURIComponent(n.nomination_uuid)}`}>
              Act on {n.principal_name}&apos;s behalf
              <ArrowRight className="size-4" aria-hidden="true" />
            </Link>
          </Button>
        </div>
      )}
    </div>
  );
}
