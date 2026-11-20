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
 * A contact no account carries is said to be that (2026-11-16, the product
 * owner's decision): the server answers `account_not_found`, and she is taken
 * to sign-up with the contact filled in and the reason at the top. Before,
 * the reply was the same sentence either way and somebody who had never
 * registered waited for a code that was never coming.
 *
 * A wrong code, a spent one and one never sent still get one refusal, and a
 * failure to *send* - a rate limit, the broker down - is shown as it is.
 */
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { AuthLayout } from "@/components/layout/auth-layout";
import { ReportIncidentLink } from "@/components/layout/report-incident-link";
import { AuthPageGate } from "@/components/security";
import { Alert, Button, Field, Input } from "@/components/ui/primitives";
import { requestOtp, verifyOtp } from "@/features/auth";
import { handOverContact, useHandedOverContact } from "@/features/auth/contact-handover";
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
      aside={
        <>
          New user?{" "}
          <Link href="/sign-up" className="font-medium text-accent-text underline underline-offset-2">
            Register
          </Link>
        </>
      }
      footer={
        <div className="space-y-3">
          <ReportIncidentLink />
          <p className="text-center text-xs text-text-subtle">
            <Link
              href="/rights"
              className="underline underline-offset-2 hover:text-text-muted"
            >
              Your rights and how to exercise them
            </Link>
          </p>
          <p className="text-center text-xs text-text-subtle">
            Nominated by someone? Once you have accepted, sign in here with the contact you
            accepted from - or{" "}
            <Link
              href="/rights/nominee"
              className="underline underline-offset-2 hover:text-text-muted"
            >
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
        <AuthPageGate>
          <SubjectForm />
        </AuthPageGate>
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
  const router = useRouter();
  const hydrated = useHydrated();
  const params = useSearchParams();
  const [sent, setSent] = React.useState(false);
  const [contact, setContact] = React.useState("");
  const [failed, setFailed] = React.useState<string | null>(null);
  // Prefilled when arriving from sign-up, which hands over the address it just
  // registered, or found already registered. Retyping an address you entered
  // one screen ago is the kind of friction that loses people between
  // registering and ever signing in.
  //
  // The URL says only that one was handed over (`prefill=1`); the address
  // itself comes through this tab's storage, read once and removed, so it is
  // never in the history, a log or a Referer (review SEC-6). A `contact` in
  // the URL is not read. Only an address is accepted, and it only ever
  // populates a form field — it authorises nothing, and the code still has
  // to arrive at that address.
  const arrivedWith = useHandedOverContact("sign-in", params.get("prefill") === "1");
  // Mobile first: it is where her sign-in codes go by default. An email handed
  // over from sign-up switches the choice for her, until she chooses.
  const [chosen, setMedium] = React.useState<"mobile" | "email" | null>(null);
  const medium = chosen ?? (arrivedWith.includes("@") ? "email" : "mobile");

  const form = useForm<OtpRequestForm>({
    resolver: zodResolver(otpRequestSchema),
    defaultValues: { contact: arrivedWith },
  });

  // When the page hydrates, the first render has no storage to read, so the
  // address arrives a render later than the form's defaults.
  React.useEffect(() => {
    if (arrivedWith && !form.getValues("contact")) form.setValue("contact", arrivedWith);
  }, [arrivedWith, form]);

  const onSubmit = form.handleSubmit(async (values) => {
    setFailed(null);
    try {
      await requestOtp(values);
    } catch (err) {
      if (err instanceof ApiError && err.code === "account_not_found") {
        // No account: to sign-up, which says why and has the contact filled in.
        // The contact goes through this tab's storage, not the URL (SEC-6).
        handOverContact(values.contact, "sign-up");
        const to = new URLSearchParams({ unregistered: "1" });
        const next = params.get("next");
        if (next) to.set("next", next);
        router.push(`/sign-up?${to.toString()}`);
        return;
      }
      setFailed(
        err instanceof ApiError ? err.userMessage() : "We could not send a code just now.",
      );
      return;
    }
    setContact(values.contact);
    setSent(true);
  });

  if (sent) {
    return (
      <div className="space-y-4">
        {/* Said to everybody alike. A wrong code, a spent one and one never
            sent get the same refusal, so the page says once, for all, that
            five wrong tries cancel a code (2026-11-08). */}
        <Alert tone="info" title="Check your messages">
          A six-digit code is on its way to <strong>{contact}</strong>. It expires in ten
          minutes, or after five wrong tries; then ask for another.
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
      {failed && <Alert tone="danger">{failed}</Alert>}
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
        Send code
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
      // sent them here. Anything not a same-origin path becomes her home.
      router.replace(safeRedirectPath(next, "/home"));
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
            className="h-14 text-center indent-[0.5em] font-mono text-2xl tracking-[0.5em]"
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
