/**
 * MFA step-up.
 *
 * Reached only with a partial session: the password was accepted and this is the
 * one route that session authorises. Every other endpoint answers 401 with
 * `mfa_required` until this completes.
 *
 * The sign-in page hands over `?next=`, the page the person was trying to
 * reach, because this step is where it used to be lost: every staff role steps
 * up with a code, so without it a link in an email always ended on the
 * dashboard.
 */
"use client";

import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";

import { AuthLayout } from "@/components/layout/auth-layout";
import { AuthPageGate } from "@/components/security";
import { Alert, Button, Field, Input } from "@/components/ui/primitives";
import { resendMfa, verifyMfa } from "@/features/auth";
import { ApiError } from "@/lib/errors";
import { safeRedirectPath, useHydrated } from "@/lib/security";
import { useAuth } from "@/providers";

const CODE_LENGTH = 6;

export default function VerifyPage() {
  return (
    <AuthLayout
      title="Verify it is you"
      subtitle={`Your role requires a second factor. We have sent a ${CODE_LENGTH}-digit code to your registered email.`}
      assurances={[
        "A second factor is required for privileged roles",
        "Codes expire after ten minutes",
        "Requesting a new code invalidates the previous one",
      ]}
      footer={
        <p className="text-center text-xs text-text-subtle">
          If you did not try to sign in, tell the Privacy Office.
        </p>
      }
    >
      {/* useSearchParams() forces client-side rendering, so Next requires a
          suspense boundary around anything that reads it. Without this the
          whole page bails out of prerendering. */}
      <React.Suspense fallback={<FormSkeleton />}>
        <AuthPageGate step="code">
          <VerifyForm />
        </AuthPageGate>
      </React.Suspense>
    </AuthLayout>
  );
}

function FormSkeleton() {
  return (
    <div className="space-y-4" aria-hidden="true">
      <div className="shimmer h-20 rounded-lg" />
      <div className="shimmer h-10 rounded-lg" />
    </div>
  );
}

function VerifyForm() {
  const router = useRouter();
  const params = useSearchParams();
  const { refresh } = useAuth();
  const hydrated = useHydrated();

  // Carried over from the sign-in page, and attacker-controlled all the same:
  // the URL may have been crafted. Only a same-origin path is honoured, and an
  // absent one means the dashboard.
  const next = safeRedirectPath(params.get("next"), "");
  const destination = next || "/dashboard";
  const signInHref = next ? `/sign-in?next=${encodeURIComponent(next)}` : "/sign-in";

  const [code, setCode] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [notice, setNotice] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [resending, setResending] = React.useState(false);

  async function verify(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await verifyMfa({ code });
      await refresh();
      router.replace(destination);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.userMessage());
        // A rate limit here means the code was discarded after too many
        // attempts. Say so, rather than letting them keep typing into a code
        // that no longer exists.
        if (err.isRateLimited) {
          setCode("");
        }
        if (err.isAuthError && !err.needsMfa) {
          // The partial session expired - back to the start, still bound for
          // the same page.
          router.replace(signInHref);
        }
      } else {
        setError("Could not reach the server.");
      }
    } finally {
      setBusy(false);
    }
  }

  async function resend() {
    setResending(true);
    setError(null);
    try {
      await resendMfa();
      setNotice("A new code has been sent. The previous one no longer works.");
      setCode("");
    } catch (err) {
      setError(err instanceof ApiError ? err.userMessage() : "Could not resend the code.");
    } finally {
      setResending(false);
    }
  }

  return (
    <>
      <form method="post" onSubmit={verify} className="space-y-4" noValidate>
        {error && <Alert tone="danger">{error}</Alert>}
        {notice && <Alert tone="info">{notice}</Alert>}

        <Field label={`${CODE_LENGTH}-digit code`} required>
          {(props) => (
            <Input
              {...props}
              value={code}
              onChange={(e) =>
                setCode(e.target.value.replace(/\D/g, "").slice(0, CODE_LENGTH))
              }
              inputMode="numeric"
              autoComplete="one-time-code"
              placeholder="000000"
              autoFocus
              className="h-14 text-center indent-[0.5em] font-mono text-2xl tracking-[0.5em]"
            />
          )}
        </Field>

        <Button
          type="submit"
          variant="primary"
          className="w-full"
          loading={busy}
          // `!hydrated` is the important half. Before React attaches its
          // handler the browser would perform a native submission instead, and
          // a disabled control cannot fire one. See `useHydrated`.
          disabled={!hydrated || code.length !== CODE_LENGTH}
        >
          Verify and continue
        </Button>
      </form>

      <div className="mt-5 flex items-center justify-between text-xs">
        <button
          type="button"
          onClick={resend}
          disabled={resending}
          className="text-accent-text underline underline-offset-2 disabled:opacity-50"
        >
          {resending ? "Sending…" : "Send a new code"}
        </button>
        <a
          href={signInHref}
          className="text-text-subtle underline underline-offset-2 hover:text-text-muted"
        >
          Start over
        </a>
      </div>
    </>
  );
}
