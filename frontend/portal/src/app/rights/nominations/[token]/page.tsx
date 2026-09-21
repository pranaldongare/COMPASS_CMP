/**
 * The acceptance link a nominee receives.
 *
 * Section 14: somebody named her nominee, and nothing is in effect until he
 * accepts. This page is what the link opens. Every failure - expired, used,
 * never existed - is the same "not valid" screen, because the link is a
 * capability and distinguishing the failures would tell a guesser which of
 * their guesses were structurally right.
 */
"use client";

import { ArrowLeft, ArrowRight, Copy } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import * as React from "react";

import { BrandMark } from "@/components/ui/graphics";
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Field,
  Input,
  Mono,
  Skeleton,
} from "@/components/ui/primitives";
import {
  acceptNomination,
  declineNomination,
  getNomination,
  requestNominationCode,
} from "@/features/rights/api";
import { REQUEST_TYPE_COPY } from "@/features/rights/components/copy";
import { ApiError } from "@/lib/errors";
import { formatDate } from "@/lib/format";
import type { NominationView } from "@/types";

type Phase = "loading" | "invalid" | "ready" | "accepted" | "declined";

export default function NominationAcceptPage() {
  const params = useParams<{ token: string }>();
  const token = params?.token ?? "";
  const [phase, setPhase] = React.useState<Phase>("loading");
  const [view, setView] = React.useState<NominationView | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [pending, setPending] = React.useState(false);
  // Proving a recorded contact before the link's accept or decline counts.
  const [medium, setMedium] = React.useState<"mobile" | "email" | null>(null);
  const [codeSent, setCodeSent] = React.useState<string | null>(null);
  const [code, setCode] = React.useState("");
  const [codeError, setCodeError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!token) return;
    getNomination(token)
      .then((v) => {
        setView(v);
        setPhase("ready");
      })
      .catch(() => setPhase("invalid"));
  }, [token]);

  async function sendCode() {
    if (!medium) return;
    setPending(true);
    setCodeError(null);
    try {
      const result = await requestNominationCode(token, medium);
      setCodeSent(result.message ?? "A code has been sent.");
    } catch (err) {
      setCodeError(err instanceof ApiError ? err.userMessage() : "Could not send a code.");
    } finally {
      setPending(false);
    }
  }

  async function act(kind: "accept" | "decline") {
    setPending(true);
    setCodeError(null);
    try {
      const result =
        kind === "accept" ? await acceptNomination(token, code) : await declineNomination(token, code);
      setMessage(result.message ?? null);
      setPhase(kind === "accept" ? "accepted" : "declined");
    } catch (err) {
      // A wrong code is a wrong code; anything else means the link is gone.
      if (err instanceof ApiError && err.status === 400) {
        setCodeError(err.userMessage());
      } else {
        setPhase("invalid");
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="min-h-dvh bg-bg-subtle">
      <header className="brand-gradient">
        <div className="mx-auto max-w-2xl px-4 py-10">
          <span className="grid size-11 place-items-center rounded-xl bg-white/15 ring-1 ring-white/25">
            <BrandMark className="size-6 text-white" />
          </span>
          <h1 className="mt-4 text-3xl font-semibold tracking-tight text-white">
            A nomination for you
          </h1>
          <p className="mt-3 max-w-xl text-sm leading-relaxed text-white/80">
            Under section 14 of the Digital Personal Data Protection Act 2023, a person may
            name somebody to exercise their data protection rights if they die or cannot act.
          </p>
        </div>
      </header>

      <main id="main" className="mx-auto max-w-2xl px-4 py-8">
        {phase === "loading" && <Skeleton className="h-64" />}

        {phase === "invalid" && (
          <Alert tone="warning" title="This link is not valid">
            <p>It may have expired, been used already, or been revoked. Nothing has been recorded.</p>
          </Alert>
        )}

        {phase === "ready" && view && (
          <Card>
            <CardHeader>
              <CardTitle>{view.principal_name} has nominated you</CardTitle>
            </CardHeader>
            <CardBody className="space-y-4 text-sm">
              <p>
                You are named as <span className="font-medium">{view.nominee_name}</span>. If{" "}
                {view.principal_name} dies or becomes unable to act, you would be able to ask
                us, on their behalf, for:
              </p>
              <ul className="list-disc space-y-1 pl-5">
                {view.rights.map((r) => (
                  <li key={r}>
                    <span className="font-medium">{REQUEST_TYPE_COPY[r].label}</span> ({REQUEST_TYPE_COPY[r].section}) -{" "}
                    <span className="text-text-muted">{REQUEST_TYPE_COPY[r].blurb}</span>
                  </li>
                ))}
              </ul>
              <Alert tone="info">
                <p>
                  Nothing happens now. When the time comes you would identify yourself with the
                  contact {view.principal_name} recorded for you, and evidence the event to the
                  standard we publish. Acting for someone means handling their personal data;
                  accept only if you are willing to.
                </p>
              </Alert>
              {view.accept_expires_at && (
                <p className="text-xs text-text-subtle">
                  This link expires on {formatDate(view.accept_expires_at)}.
                </p>
              )}
              <div className="space-y-3 rounded-md border border-border p-4">
                <p className="text-sm font-medium">First, prove it is you</p>
                <p className="text-sm text-text-muted">
                  We will send a code to one of the contacts {view.principal_name} recorded for
                  you. The link alone is not enough to accept or decline.
                </p>
                <fieldset className="space-y-2">
                  <legend className="sr-only">Where to send the code</legend>
                  {view.mediums.map((m) => (
                    <label key={m.kind} className="flex items-center gap-2 text-sm">
                      <input
                        type="radio"
                        name="medium"
                        value={m.kind}
                        checked={medium === m.kind}
                        onChange={() => setMedium(m.kind)}
                      />
                      <span>
                        {m.kind === "mobile" ? "Mobile" : "Email"}{" "}
                        <span className="text-text-muted">{m.masked}</span>
                      </span>
                    </label>
                  ))}
                </fieldset>
                <Button variant="secondary" disabled={!medium || pending} onClick={sendCode}>
                  Send me a code
                </Button>
                {codeSent && <p className="text-sm text-text-muted">{codeSent}</p>}
                {codeError && !codeSent && <p className="text-sm text-danger-text">{codeError}</p>}
                {codeSent && (
                  <Field label="Six-digit code" required error={codeError ?? undefined}>
                    {(p) => (
                      <Input
                        {...p}
                        value={code}
                        onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                        inputMode="numeric"
                        autoComplete="one-time-code"
                        placeholder="000000"
                        className="text-center font-mono text-lg tracking-[0.4em]"
                      />
                    )}
                  </Field>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="primary"
                  loading={pending}
                  disabled={code.length !== 6}
                  onClick={() => act("accept")}
                >
                  Accept the nomination
                </Button>
                <Button
                  variant="secondary"
                  disabled={pending || code.length !== 6}
                  onClick={() => act("decline")}
                >
                  Decline
                </Button>
              </div>
            </CardBody>
          </Card>
        )}

        {(phase === "accepted" || phase === "declined") && (
          <Alert
            tone={phase === "accepted" ? "success" : "info"}
            title={phase === "accepted" ? "Accepted" : "Declined"}
          >
            <p>{message}</p>
          </Alert>
        )}

        {phase === "accepted" && view && (
          // What he will need on a day that may be years away. There is no
          // account: the reference, plus a code to a contact she recorded, is
          // how he acts. It has also been sent to those contacts.
          <Card>
            <CardHeader>
              <CardTitle>Keep your nomination reference</CardTitle>
            </CardHeader>
            <CardBody className="space-y-4">
              <p className="text-sm text-text-muted">
                You can now sign in with the mobile or email you accepted from - a code is
                sent to it each time, there is no password - and you will find{" "}
                {view.principal_name}&apos;s nomination under My requests, with the way to
                act. You can also act without signing in, using this reference and the
                contact that was recorded for you. We have sent all of this to those
                contacts.
              </p>
              <p>
                <Link
                  href="/sign-in"
                  className="text-sm font-medium text-accent-text underline underline-offset-2"
                >
                  Sign in
                </Link>
              </p>
              <div className="flex flex-wrap items-center gap-2">
                <Mono className="break-all text-sm" data-testid="nomination-reference">
                  {view.nomination_uuid}
                </Mono>
                <CopyButton value={view.nomination_uuid} />
              </div>
              <Button asChild variant="primary">
                <Link href={`/rights/nominee?nomination=${encodeURIComponent(view.nomination_uuid)}`}>
                  Act on their behalf
                  <ArrowRight className="size-4" aria-hidden="true" />
                </Link>
              </Button>
            </CardBody>
          </Card>
        )}

        <p className="mt-8 text-center text-xs">
          <Link
            href="/rights"
            className="inline-flex items-center gap-1 text-text-subtle underline underline-offset-2 hover:text-text-muted"
          >
            <ArrowLeft className="size-3.5" aria-hidden="true" />
            Your rights under the Act
          </Link>
        </p>
      </main>
    </div>
  );
}

/** Copies the reference where the clipboard is available, and says so briefly. */
function CopyButton({ value }: { value: string }) {
  const [copied, setCopied] = React.useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // No clipboard here - the reference is still on screen to select.
    }
  }
  return (
    <Button type="button" variant="subtle" size="sm" onClick={copy}>
      <Copy className="size-4" aria-hidden="true" />
      {copied ? "Copied" : "Copy"}
    </Button>
  );
}
