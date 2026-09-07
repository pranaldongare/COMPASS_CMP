/**
 * Your account.
 *
 * The session list is the part that earns its place. A session you do not
 * recognise is the earliest signal available that credentials have leaked, and
 * being able to end it without calling support is the difference between a
 * five-minute problem and a five-day one.
 */
"use client";

import { LogOut, Monitor, UserRound } from "lucide-react";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import {
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  DescriptionItem,
  DescriptionList,
  Skeleton,
} from "@/components/ui/primitives";
import { StatusBadge } from "@/components/ui/status";
import { revokeSession } from "@/features/auth";
import { ApiError } from "@/lib/errors";
import { useSessions } from "@/features/account";
import { formatDate, formatDateTime, formatRelative } from "@/lib/format";
import { useAuth, useToast } from "@/providers";

export default function AccountPage() {
  const { me } = useAuth();
  const sessions = useSessions();

  if (!me) return <Skeleton className="h-64" />;

  return (
    <>
      <PageHeader
        title="Your account"
        description="Who you are signed in as, and where else you are signed in."
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Monitor className="size-4" aria-hidden="true" />
                Active sessions
              </CardTitle>
              <p className="mt-1 text-xs text-text-muted">
                End anything you do not recognise. A session you cannot account for
                is the earliest sign that somebody else has your sign-in code.
              </p>
            </CardHeader>

            {sessions.isLoading ? (
              <CardBody>
                <Skeleton className="h-24" />
              </CardBody>
            ) : (
              <ul className="divide-y divide-border">
                {sessions.data?.map((s) => (
                  <SessionRow key={s.uuid} session={s} onRevoked={() => sessions.refetch()} />
                ))}
              </ul>
            )}
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserRound className="size-4" aria-hidden="true" />
              Identity
            </CardTitle>
          </CardHeader>
          <CardBody>
            <DescriptionList>
              <DescriptionItem term="Name">{me.full_name}</DescriptionItem>
              <DescriptionItem term="Email">{me.email}</DescriptionItem>
              <DescriptionItem term="Role">
                <StatusBadge kind="role" value={me.role} dot={false} />
              </DescriptionItem>
              <DescriptionItem term="Person type">
                {/* Separate from role on purpose: a DPO is also an employee, and
                    a change of employment must not alter permissions. */}
                {me.person_type ?? "—"}
              </DescriptionItem>
              <DescriptionItem term="Status">
                <StatusBadge kind="user" value={me.status} />
              </DescriptionItem>
              {/* The input to whether consent for her has to come from a
                  parent (s.9). */}
              <DescriptionItem term="Date of birth">
                {me.dob ? (
                  <span className="flex flex-wrap items-center gap-2">
                    {formatDate(me.dob)}
                    {me.is_minor && (
                      <Badge tone="warning">
                        Under 18 — consent must come from a parent or guardian
                      </Badge>
                    )}
                  </span>
                ) : (
                  // Absent rather than assumed. Saying "—" and nothing else
                  // would let an unanswered question read as an answered one.
                  <span className="text-text-muted">
                    Not recorded. Your account predates our asking.
                  </span>
                )}
              </DescriptionItem>
              <DescriptionItem term="Session expires">
                {formatDateTime(me.session_expires_at)}
              </DescriptionItem>
            </DescriptionList>
          </CardBody>
        </Card>
      </div>
    </>
  );
}

function SessionRow({
  session,
  onRevoked,
}: {
  session: {
    uuid: string;
    created_at: string;
    last_seen_at: string;
    expires_at: string;
    ip_address: string | null;
    user_agent: string | null;
    mfa_verified: boolean;
    current: boolean;
  };
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
    <li className="flex flex-wrap items-center justify-between gap-3 px-5 py-3">
      <div className="min-w-0">
        <p className="text-sm font-medium">
          {session.ip_address ?? "Unknown address"}
          {session.current && (
            <span className="ml-2 rounded-full border border-success-border bg-success-subtle px-2 py-0.5 text-2xs font-medium text-success-text">
              this device
            </span>
          )}
        </p>
        <p className="mt-0.5 truncate text-xs text-text-subtle">
          {session.user_agent ?? "Unknown client"}
        </p>
        <p className="mt-0.5 text-xs text-text-muted">
          Last active {formatRelative(session.last_seen_at)} · expires{" "}
          {formatDateTime(session.expires_at)}
        </p>
      </div>
      {!session.current && (
        <Button variant="subtle" size="sm" loading={busy} onClick={revoke}>
          <LogOut className="size-4" />
          End session
        </Button>
      )}
    </li>
  );
}
