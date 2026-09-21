/**
 * The consent a request is confined to, said once and shown everywhere the
 * request is worked: the register, the request page, the holders and scope
 * cards, the ticket. A confined request touches the data under that consent
 * and nothing else, and every screen that acts on it says so before the
 * action, not after.
 */
"use client";

import { ShieldCheck } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/primitives";
import { formatDate } from "@/lib/format";
import type { Timestamp, Uuid } from "@/types";

export interface ConsentScopeProps {
  consent_uuid: Uuid;
  project: string | null;
  notice_code: string | null;
  notice_version: number | null;
  at: Timestamp | null;
  withdrawn?: boolean | null;
  purposes: string[] | null;
}

/** One line: which consent, and what it covered. */
export function consentScopeText(s: ConsentScopeProps): string {
  const notice = s.notice_code ? `${s.notice_code}${s.notice_version != null ? ` v${s.notice_version}` : ""}` : null;
  const head = [s.project, notice].filter(Boolean).join(" · ");
  const when = s.at ? `given ${formatDate(s.at)}` : null;
  const what = s.purposes && s.purposes.length ? s.purposes.join(", ") : "no purpose granted";
  return `${[head, when].filter(Boolean).join(" · ")}: ${what}`;
}

export function ConsentScope({ scope, link = true }: { scope: ConsentScopeProps; link?: boolean }) {
  const text = consentScopeText(scope);
  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      <Badge tone="accent" dot={false}>
        <ShieldCheck className="size-3" aria-hidden="true" />
        One consent
      </Badge>
      {link ? (
        <Link href={`/consents/${scope.consent_uuid}`} className="text-accent-text hover:underline">
          {text}
        </Link>
      ) : (
        <span>{text}</span>
      )}
      {scope.withdrawn && (
        <Badge tone="warning" dot={false}>
          since withdrawn
        </Badge>
      )}
    </span>
  );
}

/** The sentence a working card carries when the request is confined. */
export function ConfinedNote({ project }: { project: string | null }) {
  return (
    <p className="mt-1 text-xs font-medium text-accent-text">
      Confined to one consent{project ? ` for ${project}` : ""}: only records under it are derived, and only they may be acted on.
    </p>
  );
}
