/**
 * The brief a rights ticket opened with. The thread itself is shared with
 * breach tickets and lives in `components/data-display/thread`.
 *
 * A ticket's thread and the brief it opened with.
 *
 * The same two pieces on both sides. The Privacy Office sees them on the
 * request, the team on its ticket; the messages are the same rows, and what
 * differs is which side is "you". The brief is what the platform wrote when
 * the ticket was issued - the person, and every record naming this holder -
 * and it is shown as data, not just as the prose that went in the mail.
 */
"use client";

import { ShieldCheck, UserRound } from "lucide-react";

import { Badge } from "@/components/ui/primitives";
import { formatDate } from "@/lib/format";
import type { HolderBrief } from "@/types";

/** The brief, as the reader would want to check it: lists, not prose. */
export function BriefPanel({ brief }: { brief: HolderBrief }) {
  const s = brief.subject;
  const nothing = brief.consents.length + brief.exports.length + brief.assets.length === 0;
  return (
    <div className="space-y-3 rounded-md border border-border bg-bg-inset p-3 text-sm">
      <p className="flex items-center gap-2 font-medium">
        <UserRound className="size-4 text-text-subtle" aria-hidden="true" />
        {s.full_name ?? "The person named"}
        <span className="font-normal text-text-muted">
          {[s.email, s.mobile].filter(Boolean).join(" · ")}
        </span>
      </p>
      {brief.scope && (
        <p className="flex flex-wrap items-baseline gap-x-2 rounded-md border border-accent-border bg-accent-subtle px-3 py-2 text-accent-text">
          <ShieldCheck className="size-4 self-center" aria-hidden="true" />
          <span className="font-medium">Confined to one consent:</span>
          <span>
            {[brief.scope.project, brief.scope.notice].filter(Boolean).join(" · ")}
            {brief.scope.at && ` · given ${formatDate(brief.scope.at)}`}
            {" · "}
            {brief.scope.purposes.length ? brief.scope.purposes.join(", ") : "no purpose granted"}
            {brief.scope.withdrawn && " · since withdrawn"}
          </span>
          <span className="w-full text-xs">
            Act only on data held under this consent. Anything held under another consent is
            outside this ticket.
          </span>
        </p>
      )}
      {nothing ? (
        <p className="text-text-muted">
          The platform holds no consent, export or asset record naming this holder as holding
          anything of theirs{brief.scope ? " under this consent" : ""}. The question is what, if anything, they hold.
        </p>
      ) : (
        <>
          <p className="text-xs font-medium uppercase tracking-wider text-text-subtle">
            What the platform already records this holder as holding
          </p>
          {brief.consents.length > 0 && (
            <ul className="space-y-1">
              {brief.consents.map((c) => (
                <li key={c.consent_uuid} className="flex flex-wrap items-baseline gap-x-2">
                  <Badge tone={c.withdrawal ? "warning" : "success"} dot={false}>
                    {c.withdrawal ? "withdrawal" : "consent"}
                  </Badge>
                  <span>
                    {c.at ? formatDate(c.at) : "-"} · {c.project} at {c.site}
                  </span>
                  <span className="text-text-muted">
                    {c.granted.length ? c.granted.join(", ") : "no purpose granted"}
                  </span>
                </li>
              ))}
            </ul>
          )}
          {brief.exports.length > 0 && (
            <ul className="space-y-1">
              {brief.exports.map((e) => (
                <li key={e.export_uuid} className="flex flex-wrap items-baseline gap-x-2">
                  <Badge tone="info" dot={false}>export</Badge>
                  <span>
                    {e.at ? formatDate(e.at) : "-"} · {e.project} · {e.type}
                  </span>
                </li>
              ))}
            </ul>
          )}
          {brief.assets.length > 0 && (
            <ul className="space-y-1">
              {brief.assets.map((a) => (
                <li key={a.asset_uuid} className="flex flex-wrap items-baseline gap-x-2">
                  <Badge tone="neutral" dot={false}>asset</Badge>
                  <span className="font-mono text-xs">{a.ref ?? a.asset_uuid}</span>
                  <span className="text-text-muted">
                    {a.source}
                    {a.collected_on && ` · collected ${a.collected_on}`}
                    {a.role && ` · ${a.role}`}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
