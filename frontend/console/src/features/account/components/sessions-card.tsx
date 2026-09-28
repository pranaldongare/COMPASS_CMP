/**
 * Where you are signed in, as a table: the device, where from, when last used,
 * and when it ends on its own. Anything not recognised can be ended one at a
 * time, or all at once. The newest-first list is long for anyone who signs in
 * from several places, so it shows a handful and folds the rest.
 */
"use client";

import { LogOut, Monitor } from "lucide-react";
import * as React from "react";

import {
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Skeleton,
  Table,
  Td,
  Th,
  Tr,
} from "@/components/ui/primitives";
import { revokeSession } from "@/features/auth";
import { ApiError } from "@/lib/errors";
import { formatDateTime, formatRelative } from "@/lib/format";
import { useToast } from "@/providers";

export type AccountSession = {
  uuid: string;
  created_at: string;
  last_seen_at: string;
  expires_at: string;
  ip_address: string | null;
  user_agent: string | null;
  mfa_verified: boolean;
  current: boolean;
};

/** "Chrome on macOS" from a user-agent string; the full string stays in the title. */
export function describeAgent(ua: string | null): string {
  if (!ua) return "Unknown client";
  const browser = /Edg\//.test(ua)
    ? "Edge"
    : /HeadlessChrome/.test(ua)
      ? "Headless Chrome"
      : /Chrome\//.test(ua)
        ? "Chrome"
        : /Firefox\//.test(ua)
          ? "Firefox"
          : /Safari\//.test(ua)
            ? "Safari"
            : (ua.split(/[/\s]/)[0] ?? "Unknown client");
  const os = /iPhone|iPad/.test(ua)
    ? "iOS"
    : /Android/.test(ua)
      ? "Android"
      : /Mac OS X|Macintosh/.test(ua)
        ? "macOS"
        : /Windows/.test(ua)
          ? "Windows"
          : /Linux/.test(ua)
            ? "Linux"
            : null;
  return os ? `${browser} on ${os}` : browser;
}

/** How many sessions show before "Show all". This device is always first. */
const SESSIONS_SHOWN = 5;

/**
 * Where else you are signed in, as a table: the device, where from, when last
 * used, and when it ends on its own. Anything not recognised can be ended one
 * at a time, or all at once.
 */
export function SessionsCard({
  sessions,
  loading,
  onChanged,
  warning,
}: {
  sessions: AccountSession[] | undefined;
  loading: boolean;
  onChanged: () => void;
  /** Why ending an unknown session matters, in this audience's words. */
  warning: string;
}) {
  const toast = useToast();
  const [showAll, setShowAll] = React.useState(false);
  const [endingAll, setEndingAll] = React.useState(false);
  const ordered = [...(sessions ?? [])].sort(
    (a, b) => Number(b.current) - Number(a.current),
  );
  const others = ordered.filter((s) => !s.current);
  const shown = showAll ? ordered : ordered.slice(0, SESSIONS_SHOWN);

  async function endAllOthers() {
    setEndingAll(true);
    let failed = 0;
    for (const s of others) {
      try {
        await revokeSession(s.uuid);
      } catch {
        failed += 1;
      }
    }
    setEndingAll(false);
    onChanged();
    if (failed) toast.error("Some sessions could not be ended", "Please try again.");
    else toast.success("Every other session ended", "Only this device is signed in now.");
  }

  return (
    <Card>
      <CardHeader className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <CardTitle className="flex items-center gap-2">
            <Monitor className="size-4" aria-hidden="true" />
            Active sessions
          </CardTitle>
          <p className="mt-1 text-xs text-text-muted">{warning}</p>
        </div>
        {others.length > 0 && (
          <Button variant="subtle" size="sm" loading={endingAll} onClick={endAllOthers}>
            <LogOut className="size-4" />
            End all other sessions
          </Button>
        )}
      </CardHeader>

      {loading ? (
        <CardBody>
          <Skeleton className="h-24" />
        </CardBody>
      ) : (
        <CardBody className="space-y-3">
          <Table>
            <caption className="sr-only">Where you are signed in</caption>
            <thead>
              <tr>
                <Th>Device</Th>
                <Th className="hidden sm:table-cell">Address</Th>
                <Th>Last active</Th>
                <Th className="hidden md:table-cell">Expires</Th>
                <Th>
                  <span className="sr-only">Action</span>
                </Th>
              </tr>
            </thead>
            <tbody>
              {shown.map((s) => (
                <SessionRow key={s.uuid} session={s} onRevoked={onChanged} />
              ))}
            </tbody>
          </Table>
          {ordered.length > SESSIONS_SHOWN && (
            <Button variant="ghost" size="sm" onClick={() => setShowAll(!showAll)}>
              {showAll ? "Show fewer" : `Show all ${ordered.length} sessions`}
            </Button>
          )}
        </CardBody>
      )}
    </Card>
  );
}

function SessionRow({
  session,
  onRevoked,
}: {
  session: AccountSession;
  onRevoked: () => void;
}) {
  const toast = useToast();
  const [busy, setBusy] = React.useState(false);

  async function revoke() {
    setBusy(true);
    try {
      await revokeSession(session.uuid);
      toast.success("Session ended");
      onRevoked();
    } catch (err) {
      toast.error(
        "Could not end that session",
        err instanceof ApiError ? err.userMessage() : "Please try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Tr>
      <Td>
        <span className="font-medium" title={session.user_agent ?? undefined}>
          {describeAgent(session.user_agent)}
        </span>
        {session.current && (
          <Badge tone="success" className="ml-2">
            this device
          </Badge>
        )}
      </Td>
      <Td className="hidden text-text-muted sm:table-cell">
        {session.ip_address ?? "Unknown"}
      </Td>
      <Td className="whitespace-nowrap text-text-muted">
        {formatRelative(session.last_seen_at)}
      </Td>
      <Td className="hidden whitespace-nowrap text-text-muted md:table-cell">
        {formatDateTime(session.expires_at)}
      </Td>
      <Td className="text-right">
        {!session.current && (
          <Button variant="subtle" size="sm" loading={busy} onClick={revoke}>
            <LogOut className="size-4" />
            End session
          </Button>
        )}
      </Td>
    </Tr>
  );
}
