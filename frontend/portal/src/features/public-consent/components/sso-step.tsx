/**
 * An employee link's two steps (ADR 0034).
 *
 * `SsoStep` is the only way in on an `sso` link: "Continue with your
 * organisation account" sends the browser to the organisation's sign-in. If
 * the service does not answer it says so and offers to try again - never that
 * the link is invalid (review UX-3).
 *
 * `SsoMobileStep` follows a first sign-in, for an employee the register has
 * not met: her account is created once she confirms a mobile by code, which
 * every account here carries (ADR 0007) - so she can still sign in by code
 * after she leaves.
 */
"use client";

import { Building2 } from "lucide-react";
import * as React from "react";

import {
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Field,
  Input,
} from "@/components/ui/primitives";
import { ssoMobile, ssoMobileVerify, ssoStart } from "@/features/public-consent/api";
import { ApiError } from "@/lib/errors";

export function SsoStep({
  token,
  note,
  onError,
}: {
  token: string;
  /** A line above the button: why she is here again, when she is. */
  note?: string | null;
  onError: (message: string | null) => void;
}) {
  const [busy, setBusy] = React.useState(false);

  async function go() {
    setBusy(true);
    onError(null);
    try {
      const { redirect_url } = await ssoStart(token);
      window.location.assign(redirect_url);
    } catch (err) {
      setBusy(false);
      onError(
        err instanceof ApiError && err.status !== 404
          ? "The sign-in service did not answer. Your link is fine - try again in a moment."
          : "We could not start the sign-in. Please ask for a current link.",
      );
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Sign in with your organisation account</CardTitle>
      </CardHeader>
      <CardBody className="space-y-4">
        {note && <p className="text-sm text-text-muted">{note}</p>}
        <p className="text-sm text-text-muted">
          This link is for employees. You sign in with the account you use at work; we then
          show you the notice and ask for your choice.
        </p>
        <Button variant="primary" className="w-full" loading={busy} onClick={go}>
          <Building2 className="size-4" aria-hidden="true" />
          Continue with your organisation account
        </Button>
      </CardBody>
    </Card>
  );
}

export function SsoMobileStep({
  token,
  onDone,
  onError,
}: {
  token: string;
  onDone: () => void | Promise<void>;
  onError: (message: string | null) => void;
}) {
  const [mobile, setMobile] = React.useState("");
  const [code, setCode] = React.useState("");
  const [sent, setSent] = React.useState(false);
  const [busy, setBusy] = React.useState(false);

  async function send(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    onError(null);
    try {
      await ssoMobile(token, mobile.trim());
      setSent(true);
    } catch (err) {
      onError(err instanceof ApiError ? err.userMessage() : "Could not send a code.");
    } finally {
      setBusy(false);
    }
  }

  async function confirm(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    onError(null);
    try {
      await ssoMobileVerify(token, { mobile: mobile.trim(), code: code.trim() });
      await onDone();
    } catch (err) {
      onError(err instanceof ApiError ? err.userMessage() : "Could not confirm the code.");
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Your mobile number</CardTitle>
      </CardHeader>
      <CardBody className="space-y-4">
        <p className="text-sm text-text-muted">
          You are signed in with your organisation account. Your account here needs a mobile
          number, so you can still see and change your choices if you leave the organisation.
        </p>
        {!sent ? (
          <form method="post" onSubmit={send} noValidate className="space-y-4">
            <Field label="Mobile number" required>
              {(p) => (
                <Input
                  {...p}
                  type="tel"
                  inputMode="tel"
                  autoComplete="tel"
                  value={mobile}
                  placeholder="+91 98xxxxxxxx"
                  onChange={(e) => setMobile(e.target.value)}
                />
              )}
            </Field>
            <Button
              type="submit"
              variant="primary"
              className="w-full"
              loading={busy}
              disabled={mobile.trim().length < 6}
            >
              Send a code
            </Button>
          </form>
        ) : (
          <form method="post" onSubmit={confirm} noValidate className="space-y-4">
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
              Confirm
            </Button>
            <Button type="button" variant="ghost" className="w-full" onClick={() => setSent(false)}>
              Use another number
            </Button>
          </form>
        )}
      </CardBody>
    </Card>
  );
}
