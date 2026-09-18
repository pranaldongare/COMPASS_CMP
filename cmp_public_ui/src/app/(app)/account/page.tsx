/**
 * Your account.
 *
 * The session list is the part that earns its place. A session you do not
 * recognise is the earliest signal available that credentials have leaked, and
 * being able to end it without calling support is the difference between a
 * five-minute problem and a five-day one.
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
import { revokeSession } from "@/features/auth";
import { ApiError } from "@/lib/errors";
import {
  useRemoveSecondaryEmail,
  useRequestContactCode,
  useSessions,
  useUpdateMe,
  useVerifyContact,
} from "@/features/account";
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
        {/* `min-w-0`: a grid item's automatic minimum is its content's width, so
            one unbreakable line - a session's user-agent string, truncated on
            one line - stretched this column to 811px on a 412px phone and
            panned the whole page. Only with a minimum of zero can `truncate`
            below actually truncate. */}
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
                earliest sign that somebody else has your sign-in code.
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
              <DescriptionItem term="Mobile">{me.mobile ?? "—"}</DescriptionItem>
              <DescriptionItem term="Email">
                {me.email ?? <span className="text-text-muted">None given</span>}
              </DescriptionItem>
              <DescriptionItem term="Role">
                <StatusBadge kind="role" value={me.role} dot={false} />
              </DescriptionItem>
              {me.account_role !== "data_subject" && (
                <DescriptionItem term="Account">
                  {/* The session acts as a data principal whatever the row says;
                      the row's role is shown so the person knows which account
                      this is, and decides nothing here. */}
                  Your staff account, used here as a data principal.
                </DescriptionItem>
              )}
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

/* ------------------------------------------------------------- contacts */

type Me = NonNullable<ReturnType<typeof useAuth>["me"]>;

/**
 * How she is reached, and how she signs in.
 *
 * A contact she adds works only once a code sent to it has come back - a typed
 * address is a claim, and a claim is not a way in. The second email is the row
 * that earns its place: a member of staff is also a data principal, and the
 * day they leave, the corporate mailbox goes with them while their consents do
 * not. A personal address confirmed now is how they reach those later.
 */
function ContactsCard({ me }: { me: Me }) {
  const staff = me.account_role !== "data_subject";
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
          How we reach you, and how you sign in. A contact you add works only once a code
          sent to it has come back.
        </p>
      </CardHeader>
      <CardBody className="space-y-4">
        {me.email && (
          <ContactRow
            testId="contact-email"
            label="Email"
            value={me.email}
            verifiedAt={me.email_verified_at}
            hint={
              staff
                ? "Your staff address, managed by your organisation. If you may lose it one day, add a personal one below."
                : undefined
            }
            inputType="email"
          />
        )}
        <ContactRow
          testId="contact-mobile"
          label="Mobile"
          value={me.mobile}
          verifiedAt={me.mobile_verified_at}
          inputType="tel"
          placeholder="+91 ..."
          onSave={async (mobile) =>
            (await updateMe.mutateAsync({ mobile })).mobile_verified_at === null
          }
        />
        <ContactRow
          testId="contact-secondary_email"
          label={me.email ? "Second email" : "Email"}
          value={me.secondary_email}
          verifiedAt={me.secondary_email_verified_at}
          hint="A personal address that stays yours. Once confirmed it can sign you in, even if the first no longer can."
          inputType="email"
          placeholder="you@example.org"
          onSave={async (secondary_email) =>
            (await updateMe.mutateAsync({ secondary_email }))
              .secondary_email_verified_at === null
          }
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
  /** Absent means the contact is not hers to change from here. Resolves to
   *  whether a code was sent to it, which decides what the row says next. */
  onSave?: (value: string) => Promise<boolean>;
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
      // Whether a code went out is the server's answer, read off the saved
      // row. This used to be assumed, and the assumption was wrong in the one
      // case that mattered: re-saving a number already on the account, which
      // sent nothing while the screen said it had and offered a code box.
      const sent = await onSave(draft.trim());
      setCode("");
      setMode(sent ? "code" : "view");
      toast.success(
        "Saved",
        sent
          ? `We have sent a code to ${draft.trim()}.`
          : "That contact is already confirmed, so no code was needed.",
      );
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
              buttons, where on a phone it caught the tap meant for them. */}
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

      {/* Field above, buttons in a row below. Side by side on a phone put the
          field's hint under the buttons and swallowed the tap. `method="post"`:
          before React attaches its handler the browser would submit natively,
          and HTML's default is GET, which puts the contact in the URL. */}
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
