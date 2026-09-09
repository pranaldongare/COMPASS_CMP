/**
 * Data-principal sign-in.
 *
 * There is no password. `password_hash` is nullable on a data subject account
 * for exactly this reason: she registered with a mobile and, optionally, an
 * email, and signs in with a one-time code sent to whichever she chooses.
 *
 * Staff do not sign in here. Their console, with its password and second
 * factor, is a separate deployment; a link to it sits in the footer.
 *
 * Every failure message is identical by design. The server refuses to say
 * whether a contact is registered, and repeating a friendlier message here
 * would undo that.
 */
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { AuthLayout } from "@/components/layout/auth-layout";
import { Alert, Button, Field, Input } from "@/components/ui/primitives";
import { requestOtp, verifyOtp } from "@/features/auth";
import { config } from "@/lib/config";
import { ApiError } from "@/lib/errors";
import { safeRedirectPath, useHydrated } from "@/lib/security";
import { useAuth } from "@/providers";

const otpRequestSchema = z.object({
  contact: z.string().min(3, "Enter the email address or mobile you registered"),
});

type OtpRequestForm = z.infer<typeof otpRequestSchema>;

export default function SignInPage() {
  return (
    <AuthLayout
      title="Sign in"
      subtitle="Enter the mobile number or email address you registered with and we will
        send you a one-time code."
      footer={
        <div className="space-y-3">
          <p className="text-center text-sm text-text-muted">
            Never registered with us?{" "}
            <Link href="/sign-up" className="font-medium text-accent-text hover:underline">
              Create an account
            </Link>
          </p>
          <p className="text-center text-xs text-text-subtle">
            <Link href="/rights" className="underline underline-offset-2 hover:text-text-muted">
              Your rights and how to exercise them
            </Link>
          </p>
          <p className="text-center text-xs text-text-subtle">
            Nominated by someone? Once you have accepted, sign in here with the contact you
            accepted from - or{" "}
            <Link href="/rights/nominee" className="underline underline-offset-2 hover:text-text-muted">
              Act on their behalf here
            </Link>
          </p>
          <p className="text-center text-xs text-text-subtle">
            Staff?{" "}
            <a
              href={config.staffPortalUrl}
              className="underline underline-offset-2 hover:text-text-muted"
            >
              Sign in to the console
            </a>
          </p>
        </div>
      }
    >
      {/* useSearchParams() forces client-side rendering, so Next requires a
          suspense boundary around anything that reads it. Without this the
          whole page bails out of prerendering. */}
      <React.Suspense fallback={<FormSkeleton />}>
        <SubjectForm />
      </React.Suspense>
    </AuthLayout>
  );
}

function FormSkeleton() {
  return (
    <div className="space-y-4" aria-hidden="true">
      <div className="shimmer h-16 rounded-lg" />
      <div className="shimmer h-10 rounded-lg" />
    </div>
  );
}

function SubjectForm() {
  const hydrated = useHydrated();
  const params = useSearchParams();
  const [sent, setSent] = React.useState(false);
  const [contact, setContact] = React.useState("");
  // Mobile first: it is where her sign-in codes go by default. An email that
  // arrived in the URL from sign-up switches the choice for her.
  const [medium, setMedium] = React.useState<"mobile" | "email">(() =>
    (params.get("contact") ?? "").includes("@") ? "email" : "mobile",
  );

  // Prefilled when arriving from sign-up, which sends the address it just
  // registered. Retyping an address you entered one screen ago is the kind of
  // friction that loses people between registering and ever signing in.
  //
  // Only an address is accepted, and it only ever populates a form field — it
  // authorises nothing, and the code still has to arrive at that address.
  const form = useForm<OtpRequestForm>({
    resolver: zodResolver(otpRequestSchema),
    defaultValues: { contact: params.get("contact") ?? "" },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    // Deliberately ignores the outcome: the endpoint answers identically whether
    // or not the contact is registered, so that this form cannot be used to
    // discover who consented to a project.
    try {
      await requestOtp(values);
    } catch {
      // Even a failure must not distinguish. A network error still shows the
      // same screen; the code simply will not arrive.
    }
    setContact(values.contact);
    setSent(true);
  });

  if (sent) {
    return (
      <div className="space-y-4">
        <Alert tone="info" title="Check your messages">
          If <strong>{contact}</strong> is registered with us, a six-digit code is
          on its way. It expires in ten minutes.
        </Alert>
        <SubjectVerifyForm contact={contact} next={params.get("next")} />
        <Button variant="ghost" className="w-full" onClick={() => setSent(false)}>
          Use a different contact
        </Button>
      </div>
    );
  }

  return (
    // `method="post"` is not decorative. Before React attaches its handler the
    // browser would perform a native GET submission, putting the contact in
    // the URL, the access log and the next Referer header.
    <form method="post" onSubmit={onSubmit} className="space-y-4" noValidate>
      <fieldset className="space-y-2">
        <legend className="text-sm font-medium">Sign in with</legend>
        <div className="flex gap-4 text-sm">
          <label className="flex items-center gap-2">
            <input
              type="radio"
              name="medium"
              value="mobile"
              checked={medium === "mobile"}
              onChange={() => setMedium("mobile")}
            />
            Mobile
          </label>
          <label className="flex items-center gap-2">
            <input
              type="radio"
              name="medium"
              value="email"
              checked={medium === "email"}
              onChange={() => setMedium("email")}
            />
            Email
          </label>
        </div>
      </fieldset>
      <Field
        label={medium === "mobile" ? "Mobile number" : "Email address"}
        hint="The one you registered with. We will send a one-time code there."
        error={form.formState.errors.contact?.message}
        required
      >
        {(props) => (
          <Input
            {...props}
            {...form.register("contact")}
            type={medium === "mobile" ? "tel" : "email"}
            autoComplete={medium === "mobile" ? "tel" : "email"}
            placeholder={medium === "mobile" ? "+91 ..." : "you@example.org"}
            autoFocus
          />
        )}
      </Field>

      <Button
        type="submit"
        variant="primary"
        className="w-full"
        loading={form.formState.isSubmitting}
        disabled={!hydrated}
      >
        Send me a code
      </Button>
    </form>
  );
}

function SubjectVerifyForm({ contact, next }: { contact: string; next: string | null }) {
  const router = useRouter();
  const { refresh } = useAuth();
  const hydrated = useHydrated();
  const [code, setCode] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await verifyOtp({ contact, code });
      await refresh();
      // `next` is attacker-controlled - it is whatever was in the link that
      // sent them here. Anything not a same-origin path becomes her consents.
      router.replace(safeRedirectPath(next, "/my-consents"));
    } catch (err) {
      setError(err instanceof ApiError ? err.userMessage() : "Verification failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form method="post" onSubmit={submit} className="space-y-4" noValidate>
      {error && <Alert tone="danger">{error}</Alert>}
      <Field label="Six-digit code" required>
        {(props) => (
          <Input
            {...props}
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
            inputMode="numeric"
            autoComplete="one-time-code"
            placeholder="000000"
            className="h-14 text-center font-mono text-2xl tracking-[0.5em] indent-[0.5em]"
            autoFocus
          />
        )}
      </Field>
      <Button
        type="submit"
        variant="primary"
        className="w-full"
        loading={busy}
        disabled={!hydrated || code.length !== 6}
      >
        Verify
      </Button>
    </form>
  );
}
