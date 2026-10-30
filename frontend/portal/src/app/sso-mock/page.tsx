/**
 * Development only: a stand-in for the organisation's sign-in page.
 *
 * With `SSO_MOCK` on the API (2026-10-30), "Continue with your organisation
 * account" on an `sso` link comes here instead of to a real provider. Any
 * email address is accepted: a code is sent to it (the development popup
 * shows it), and with the code back the browser goes to the sign-in's
 * callback, which carries on exactly as it would from the provider - the
 * employee is matched on an ID derived from the address, and one the register
 * has not met confirms a mobile next.
 *
 * Without the setting the API has no such routes, and this page says it is
 * not available.
 */
"use client";

import { Building2 } from "lucide-react";
import { useSearchParams } from "next/navigation";
import * as React from "react";

import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Field,
  Input,
} from "@/components/ui/primitives";
import { ssoMockCancel, ssoMockCode, ssoMockConfirm } from "@/features/public-consent";
import { ApiError } from "@/lib/errors";

export default function SsoMockPage() {
  return (
    <main id="main" className="grid min-h-dvh place-items-center bg-bg-subtle px-4 py-12">
      <div className="w-full max-w-md space-y-4">
        <Alert tone="warning" title="Development only">
          A stand-in for your organisation&apos;s sign-in. Any email address works: a code
          is sent to it.
        </Alert>
        <React.Suspense fallback={null}>
          <MockSignIn />
        </React.Suspense>
      </div>
    </main>
  );
}

function failure(err: unknown, fallback: string): string {
  if (err instanceof ApiError && err.status === 404) {
    return "This sign-in has expired or is not available. Go back to your link and start again.";
  }
  return err instanceof ApiError ? err.userMessage() : fallback;
}

function MockSignIn() {
  const state = useSearchParams().get("state") ?? "";
  const [email, setEmail] = React.useState("");
  const [code, setCode] = React.useState("");
  const [sent, setSent] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  async function send(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await ssoMockCode(state, email.trim());
      setSent(true);
    } catch (err) {
      setError(failure(err, "Could not send a code."));
    } finally {
      setBusy(false);
    }
  }

  async function confirm(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const { redirect_url } = await ssoMockConfirm(state, {
        email: email.trim(),
        code: code.trim(),
      });
      window.location.assign(redirect_url);
    } catch (err) {
      setError(failure(err, "Could not confirm the code."));
      setBusy(false);
    }
  }

  async function cancel() {
    setError(null);
    try {
      const { redirect_url } = await ssoMockCancel(state);
      window.location.assign(redirect_url);
    } catch (err) {
      setError(failure(err, "Could not go back."));
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <span className="inline-flex items-center gap-2">
            <Building2 className="size-5" aria-hidden="true" />
            Your organisation&apos;s sign-in
          </span>
        </CardTitle>
      </CardHeader>
      <CardBody className="space-y-4">
        {error && <Alert tone="danger">{error}</Alert>}
        {!sent ? (
          <form method="post" onSubmit={send} noValidate className="space-y-4">
            <Field label="Work email" required>
              {(p) => (
                <Input
                  {...p}
                  type="email"
                  autoComplete="email"
                  value={email}
                  placeholder="name@organisation.example"
                  onChange={(e) => setEmail(e.target.value)}
                />
              )}
            </Field>
            <Button
              type="submit"
              variant="primary"
              className="w-full"
              loading={busy}
              disabled={!state || !email.includes("@")}
            >
              Send a code
            </Button>
          </form>
        ) : (
          <form method="post" onSubmit={confirm} noValidate className="space-y-4">
            <p className="text-sm text-text-muted">
              We have sent a code to <strong>{email.trim()}</strong>.
            </p>
            <Field label="The code we sent" required>
              {(p) => (
                <Input
                  {...p}
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                />
              )}
            </Field>
            <Button
              type="submit"
              variant="primary"
              className="w-full"
              loading={busy}
              disabled={code.trim().length < 4}
            >
              Sign in
            </Button>
            <Button
              type="button"
              variant="ghost"
              className="w-full"
              onClick={() => setSent(false)}
            >
              Use another address
            </Button>
          </form>
        )}
        <Button
          type="button"
          variant="ghost"
          className="w-full"
          onClick={cancel}
          disabled={!state}
        >
          Cancel
        </Button>
      </CardBody>
    </Card>
  );
}
