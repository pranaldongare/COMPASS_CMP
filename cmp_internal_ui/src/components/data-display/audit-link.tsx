/**
 * "Audit trail" from a record's own page.
 *
 * A DPO reading a consent record, a project or a request should be able to ask
 * "what happened to this?" without leaving it and rebuilding the question by
 * hand on the audit page. This carries the record over as a filter - its type,
 * its uuid, and the name to show in the chip - and renders nothing at all for
 * a role the server did not give the audit section to.
 */
"use client";

import { ScrollText } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/primitives";
import { useAuth } from "@/providers";

export function auditTrailHref(entityType: string, uuid: string, label: string): string {
  const params = new URLSearchParams({ entity_type: entityType, entity: uuid, label });
  return `/audit?${params.toString()}`;
}

export function AuditTrailLink({
  entityType,
  uuid,
  label,
}: {
  entityType: string;
  uuid: string;
  label: string;
}) {
  const { me } = useAuth();
  if (!me?.nav.includes("audit")) return null;
  return (
    <Button variant="secondary" size="sm" asChild>
      <Link href={auditTrailHref(entityType, uuid, label)}>
        <ScrollText className="size-4" aria-hidden="true" />
        Audit trail
      </Link>
    </Button>
  );
}
