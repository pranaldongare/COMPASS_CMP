/**
 * Your account.
 *
 * Two parts earn their place. The session list, because a session you do not
 * recognise is the earliest signal available that credentials have leaked, and
 * ending it without calling support is the difference between a five-minute
 * problem and a five-day one.
 *
 * And the contacts. A member of staff here is also a data principal (ADR 0013)
 * and this address is not theirs to keep: the day they leave, the corporate
 * mailbox goes and the consents they gave do not. A personal address confirmed
 * while the first one still works is how they reach those afterwards. The
 * mobile is the same card because it is the same rule - a contact confirmed by
 * a code sent to it, or no contact at all.
 */
"use client";

import { LogOut, Mail, Monitor, UserRound } from "lucide-react";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  DescriptionItem,
  DescriptionList,
  Field,
  Input,
  Skeleton,
} from "@/components/ui/primitives";
import { StatusBadge } from "@/components/ui/status";
import { changePassword, revokeSession } from "@/features/auth";
import { ApiError } from "@/lib/errors";
import {
  useRemoveSecondaryEmail,
  useRequestContactCode,
  useSessions,
  useUpdateMe,
  useVerifyContact,
} from "@/features/account";
import { formatDateTime, formatRelative } from "@/lib/format";
import type { Me } from "@/types";
import { useAuth, useToast } from "@/providers";

export default function AccountPage() {
  const { me } = useAuth();
  const sessions = useSessions();

  if (!me) return <Skeleton className="h-64" />;

  return (
    <>
      <PageHeader
        title="Your account"
        description="Who you are signed in as, where else you are signed in, and how to change your password."
      />

      <div className="grid gap-6 lg:grid-cols-3">
        {/* `min-w-0` on both columns: a grid item defaults to `min-width: auto`,
            so one long unbroken string - a user-agent on a single line - makes the
            column wider than its track and the whole page scroll sideways. */}
        <div className="min-w-0 space-y-6 lg:col-span-2">
          <ContactsCard me={me} />

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Monitor className="size-4" aria-hidden="true" />
                Active sessions
              </CardTitle>
              <p className="mt-1 text-xs text-text-muted">
                End anything you do not recognise. A session you cannot account for is the
                earliest sign that a password has leaked.
              </p>
            </CardHeader>

            {sessions.isLoading ? (
              <CardBody>
                <Skeleton className="h-24" />
              </CardBody>
            ) : (
              <ul className="divide-y divide-border">
                {sessions.data?.map((s) => (
                  <SessionRow
                    key={s.uuid}
                    session={s}
                    onRevoked={() => sessions.refetch()}
                  />
                ))}
              </ul>
            )}
          </Card>

          <PasswordCard />
        </div>

        <Card className="min-w-0">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserRound className="size-4" aria-hidden="true" />
              Identity
            </CardTitle>
          </CardHeader>
          <CardBody>
            <DescriptionList>
              <DescriptionItem term="Name">{me.full_name}</DescriptionItem>
              {/* The addresses are in Contacts, with what is confirmed and what
                  is not. Repeating one here said the same thing twice and the
                  quieter copy was the one missing the part that matters. */}
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

/**
 * How you are reached, and how you sign in.
 *
 * A contact added here works only once a code sent to it has come back - a
 * typed address is a claim, and a claim is not a way in. The corporate address
 * is shown but not editable: it is the organisation's, and the register is
 * where it changes.
 */
function ContactsCard({ me }: { me: Me }) {
  const updateMe = useUpdateMe();
  const removeSecondary = useRemoveSecondaryEmail();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Mail className="size-4" aria-hidden="true" />
          Contacts
        </CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          How we reach you, and how you sign in to the data principal&apos;s portal. A
          contact you add works only once a code sent to it has come back.
        </p>
      </CardHeader>
      <CardBody className="space-y-4">
        {me.email && (
          <ContactRow
            testId="contact-email"
            label="Work email"
            value={me.email}
            verifiedAt={me.email_verified_at}
            hint="Your organisation's address, and how you sign in here. If you may lose it one day, add a personal one below."
            inputType="email"
          />
        )}
        <ContactRow
          testId="contact-mobile"
          label="Mobile"
          value={me.mobile}
          verifiedAt={me.mobile_verified_at}
          hint="An administrator may set this for you. Either way it is confirmed by a code sent to the number."
          inputType="tel"
          placeholder="+91 ..."
          onSave={(mobile) => updateMe.mutateAsync({ mobile })}
        />
        <ContactRow
          testId="contact-secondary_email"
          label="Personal email"
          value={me.secondary_email}
          verifiedAt={me.secondary_email_verified_at}
          hint="An address that stays yours. Once confirmed it signs you in to the portal, even if the work one no longer can."
          inputType="email"
          placeholder="you@example.org"
          onSave={(secondary_email) => updateMe.mutateAsync({ secondary_email })}
          onRemove={() => removeSecondary.mutateAsync()}
        />
      </CardBody>
    </Card>
  );
}

function ContactRow({
  testId,
  label,
  value,
  verifiedAt,
  hint,
  inputType,
  placeholder,
  onSave,
  onRemove,
}: {
  testId: string;
  label: string;
  value: string | null;
  verifiedAt: string | null;
  hint?: string;
  inputType: "email" | "tel";
  placeholder?: string;
  /** Absent means the contact is not theirs to change from here. */
  onSave?: (value: string) => Promise<unknown>;
  onRemove?: () => Promise<unknown>;
}) {
  const toast = useToast();
  const requestCode = useRequestContactCode();
  const verify = useVerifyContact();
  const [mode, setMode] = React.useState<"view" | "edit" | "code">("view");
  const [draft, setDraft] = React.useState("");
  const [code, setCode] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const fail = (err: unknown, fallback: string) =>
    setError(err instanceof ApiError ? err.userMessage() : fallback);

  async function save() {
    if (!onSave) return;
    setBusy(true);
    setError(null);
    try {
      await onSave(draft.trim());
      // The server sent the code as part of saving; ask for it straight away.
      setCode("");
      setMode("code");
      toast.success("Saved", `We have sent a code to ${draft.trim()}.`);
    } catch (err) {
      fail(err, "Could not save that contact.");
    } finally {
      setBusy(false);
    }
  }

  async function sendCode() {
    if (!value) return;
    setError(null);
    try {
      await requestCode.mutateAsync(value);
      setCode("");
      setMode("code");
    } catch (err) {
      fail(err, "Could not send a code.");
    }
  }

  async function confirm() {
    if (!value) return;
    setError(null);
    try {
      await verify.mutateAsync({ contact: value, code });
      setMode("view");
      toast.success("Confirmed", `${value} can now sign you in.`);
    } catch (err) {
      fail(err, "That code was not accepted.");
    }
  }

  async function remove() {
    if (!onRemove) return;
    setBusy(true);
    setError(null);
    try {
      await onRemove();
      toast.success("Removed");
    } catch (err) {
      fail(err, "Could not remove that contact.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      data-testid={testId}
      className="space-y-2 border-b border-border pb-4 last:border-0 last:pb-0"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-xs font-medium text-text-muted">{label}</p>
          {/* A long address wraps inside its box rather than running under the
              buttons, where on a narrow window it caught the click meant for them. */}
          <p className="text-sm break-all">
            {value ?? <span className="text-text-muted">None given</span>}
          </p>
          {hint && <p className="mt-0.5 max-w-prose text-xs text-text-subtle">{hint}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {value &&
            (verifiedAt ? (
              <Badge tone="success">Confirmed</Badge>
            ) : (
              <Badge tone="warning">Not confirmed</Badge>
            ))}
          {value && !verifiedAt && mode === "view" && (
            <Button
              size="sm"
              variant="secondary"
              onClick={sendCode}
              loading={requestCode.isPending}
            >
              Send a code
            </Button>
          )}
          {onSave && mode === "view" && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setDraft(value ?? "");
                setError(null);
                setMode("edit");
              }}
            >
              {value ? "Change" : "Add"}
            </Button>
          )}
          {onRemove && value && mode === "view" && (
            <Button size="sm" variant="ghost" onClick={remove} loading={busy}>
              Remove
            </Button>
          )}
        </div>
      </div>

      {error && <Alert tone="danger">{error}</Alert>}

      {/* Field above, buttons in a row below, and `method="post"`: before React
          attaches its handler the browser would submit natively, and HTML's
          default is GET, which puts the contact in the URL. */}
      {mode === "edit" && (
        <form
          method="post"
          onSubmit={(e) => {
            e.preventDefault();
            void save();
          }}
          className="space-y-2"
          noValidate
        >
          <Field label={label} required>
            {(p) => (
              <Input
                {...p}
                type={inputType}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder={placeholder}
                autoComplete={inputType === "tel" ? "tel" : "email"}
                autoFocus
              />
            )}
          </Field>
          <div className="flex flex-wrap gap-2">
            <Button
              type="submit"
              variant="primary"
              size="sm"
              loading={busy}
              disabled={!draft.trim()}
            >
              Save and send a code
            </Button>
            <Button type="button" variant="ghost" size="sm" onClick={() => setMode("view")}>
              Cancel
            </Button>
          </div>
        </form>
      )}

      {mode === "code" && value && (
        <form
          method="post"
          onSubmit={(e) => {
            e.preventDefault();
            void confirm();
          }}
          className="space-y-2"
          noValidate
        >
          <Field
            label="Six-digit code"
            hint="Sent to the contact above. It expires in ten minutes."
            required
          >
            {(p) => (
              <Input
                {...p}
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                inputMode="numeric"
                autoComplete="one-time-code"
                placeholder="000000"
                className="font-mono tracking-[0.3em]"
                autoFocus
              />
            )}
          </Field>
          <div className="flex flex-wrap gap-2">
            <Button
              type="submit"
              variant="primary"
              size="sm"
              loading={verify.isPending}
              disabled={code.length !== 6}
            >
              Confirm
            </Button>
            <Button type="button" variant="ghost" size="sm" onClick={() => setMode("view")}>
              Later
            </Button>
          </div>
        </form>
      )}
    </div>
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
      <div className="min-w-0 flex-1">
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

function PasswordCard() {
  const toast = useToast();
  const [current, setCurrent] = React.useState("");
  const [next, setNext] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await changePassword({ current_password: current, new_password: next });
      toast.success("Password changed", "Every other session has been signed out.");
      setCurrent("");
      setNext("");
    } catch (err) {
      setError(err instanceof ApiError ? err.userMessage() : "The change failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Change your password</CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          Changing it signs out every other session. A password change is usually a response
          to suspicion, and leaving other sessions alive would defeat it.
        </p>
      </CardHeader>
      <CardBody>
        <form method="post" onSubmit={submit} className="max-w-sm space-y-4" noValidate>
          {error && <Alert tone="danger">{error}</Alert>}

          <Field label="Current password" required>
            {(props) => (
              <Input
                {...props}
                type="password"
                autoComplete="current-password"
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
              />
            )}
          </Field>

          <Field label="New password" hint="At least 12 characters." required>
            {(props) => (
              <Input
                {...props}
                type="password"
                autoComplete="new-password"
                value={next}
                onChange={(e) => setNext(e.target.value)}
              />
            )}
          </Field>

          <Button
            type="submit"
            variant="primary"
            loading={busy}
            disabled={!current || next.length < 12}
          >
            Change password
          </Button>
        </form>
      </CardBody>
    </Card>
  );
}
