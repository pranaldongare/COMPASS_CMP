/**
 * Self-registration for a data principal.
 *
 * A mobile is required and an email is optional, because the one-time codes
 * that *are* their sign-in should go to the thing they carry. Every contact
 * they give is authenticated before the account is theirs: a code goes to
 * each, and both are entered here, on the second step, after which they are
 * signed in.
 *
 * The first step refuses a contact that already belongs to an account, and
 * says which (409 `contact_taken`), so the form can be corrected: a product
 * decision taken with its cost in view, since "this number is taken" lets
 * anyone test who is a data principal here (`features/auth/api.ts`). A sign-up
 * that was started and never finished is not refused; its codes are sent
 * again, to the contacts it was started with.
 */
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ShieldCheck, UserPlus } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { AuthLayout } from "@/components/layout/auth-layout";
import { AuthPageGate } from "@/components/security";
import { Alert, Button, Field, Input } from "@/components/ui/primitives";
import {
  register as registerAccount,
  registerVerify,
  type RegistrationDetails,
} from "@/features/auth";
import { ApiError } from "@/lib/errors";
import { safeRedirectPath } from "@/lib/security";
import { useAuth } from "@/providers";
import { email, mobile } from "@/schemas/contacts";
import { EARLIEST_DOB, dateOfBirth, today } from "@/schemas/primitives";

const schema = z.object({
  full_name: z.string().min(2, "Enter your full name").max(120),
  mobile,
  email: z.union([z.literal(""), email]),
  dob: dateOfBirth,
});
type Values = z.infer<typeof schema>;

export default function SignUpPage() {
  return (
    <AuthPageGate>
      <SignUpFlow />
    </AuthPageGate>
  );
}

function SignUpFlow() {
  // Every detail given, not just the contacts: the second step sends them
  // again when the codes have to be sent again.
  const [given, setGiven] = React.useState<RegistrationDetails | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  // A contact that already belongs to an account. The message goes on that
  // field so it can be changed, and sign-in is offered with it filled in.
  const [taken, setTaken] = React.useState<{
    field: "mobile" | "email";
    value: string;
  } | null>(null);

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { full_name: "", mobile: "", email: "", dob: "" },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    setError(null);
    setTaken(null);
    const details: RegistrationDetails = {
      full_name: values.full_name,
      mobile: values.mobile,
      dob: values.dob,
      email: values.email ? values.email : null,
    };
    try {
      await registerAccount(details);
      setGiven(details);
    } catch (caught) {
      if (caught instanceof ApiError && caught.code === "contact_taken") {
        const field = caught.field === "email" ? "email" : "mobile";
        form.setError(field, { message: caught.userMessage() });
        setTaken({
          field,
          value: field === "email" ? (values.email ?? "") : values.mobile,
        });
        form.setFocus(field);
        return;
      }
      // Section 9 (S2-01): a date of birth under eighteen creates no account.
      // The server's sentence goes on the field it is about - it offers no
      // guardian route, because there is none to offer yet.
      if (caught instanceof ApiError && caught.code === "minor_not_permitted") {
        form.setError("dob", { message: caught.userMessage() });
        form.setFocus("dob");
        return;
      }
      setError(
        caught instanceof ApiError && caught.status === 429
          ? caught.userMessage()
          : "We could not complete that. Please try again.",
      );
    }
  });

  if (given) {
    // No way back to change the details: see VerifyStep.
    return <VerifyStep details={given} />;
  }

  return (
    <AuthLayout
      title="Create your account"
      subtitle="For people whose data is being collected. Staff accounts are issued by your administrator."
      aside={
        <>
          Already have an account?{" "}
          <Link href="/sign-in" className="font-medium text-accent-text underline underline-offset-2">
            Sign in
          </Link>
        </>
      }
    >
      <form method="post" onSubmit={onSubmit} noValidate className="space-y-4">
        {error && <Alert tone="danger">{error}</Alert>}
        {taken && (
          <Alert tone="warning" title={`That ${taken.field} is already registered`}>
            <p>
              If it is yours, sign in with it - there is no password, we send a code.
              Otherwise change it below.
            </p>
            <p className="mt-2">
              <Link
                href={`/sign-in?contact=${encodeURIComponent(taken.value)}`}
                className="font-medium text-accent-text underline underline-offset-2"
              >
                Sign in with this {taken.field}
              </Link>
            </p>
          </Alert>
        )}

        <Field label="Full name" error={form.formState.errors.full_name?.message} required>
          {(p) => <Input {...p} {...form.register("full_name")} autoComplete="name" />}
        </Field>

        {/* Side by side from a tablet up, as the sign-up screens pair them. */}
        <div className="grid gap-4 sm:grid-cols-2">
        <Field
          label="Mobile number"
          hint="Your sign-in codes come here. We will send one now to confirm it."
          error={form.formState.errors.mobile?.message}
          required
        >
          {(p) => (
            <Input
              {...p}
              {...form.register("mobile")}
              type="tel"
              autoComplete="tel"
              placeholder="+91 ..."
            />
          )}
        </Field>

        <Field
          label="Email address"
          hint="Optional. If you give one, we will confirm it too, and you can sign in with either."
          error={form.formState.errors.email?.message}
        >
          {(p) => (
            <Input {...p} {...form.register("email")} type="email" autoComplete="email" />
          )}
        </Field>
        </div>

        <Field
          label="Date of birth"
          hint="The law protects people under 18 differently, so we ask before an account is opened."
          error={form.formState.errors.dob?.message}
          required
        >
          {(p) => (
            <Input
              {...p}
              {...form.register("dob")}
              type="date"
              max={today()}
              min={EARLIEST_DOB}
              autoComplete="bday"
            />
          )}
        </Field>

        <Button
          type="submit"
          variant="primary"
          className="w-full"
          loading={form.formState.isSubmitting}
        >
          <UserPlus className="size-4" />
          Create account
        </Button>
      </form>
    </AuthLayout>
  );
}

/**
 * The second step: a code for every contact given, entered together.
 *
 * Both are checked before either is spent, so a wrong email code does not burn
 * a right mobile code. Every refusal is the same sentence, whoever is asking
 * and whichever code was wrong (2026-11-08): a wrong code, an expired one and
 * one cancelled by its fifth wrong try all read "Invalid or expired code", on
 * no particular field. So what the server can no longer say to one person is
 * said here to everybody: how long a code lasts, and how to get new ones.
 *
 * There is no way back to change the details. A sign-up keeps the contacts it
 * was begun with: details given again find it by the mobile, or else the
 * email, and its codes go where they went before, not to anything typed
 * since. A corrected contact would be named here while no code went to it,
 * and a corrected mobile would never finish (2026-11-08).
 */
function VerifyStep({ details }: { details: RegistrationDetails }) {
  const { mobile } = details;
  const email = details.email ?? null;
  const params = useSearchParams();
  /**
   * Where they were going before they were asked to sign up.
   *
   * A consent link sends people here when they have no account, and landing
   * them on their consents afterwards would leave them to find that link again
   * - which at a collection site means asking somebody to re-open it. It is
   * attacker-controlled, being whatever was in the URL, so only a same-origin
   * path survives `safeRedirectPath`; anything else becomes their home.
   */
  const next = safeRedirectPath(params.get("next"), "/home");
  const router = useRouter();
  const { refresh } = useAuth();
  const [mobileCode, setMobileCode] = React.useState("");
  const [emailCode, setEmailCode] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [resending, setResending] = React.useState(false);
  const [resent, setResent] = React.useState(false);

  // Both codes whenever both contacts were given: the server finishes a
  // sign-up only when every contact on it has answered. With a mobile alone
  // the email's box may stay empty, and a code half typed is not sent.
  const ready =
    mobileCode.length === 6 &&
    (email ? emailCode.length === 6 : emailCode.length === 0 || emailCode.length === 6);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setResent(false);
    try {
      await registerVerify({
        mobile,
        mobile_code: mobileCode,
        email_code: emailCode || null,
      });
      await refresh();
      router.replace(next);
    } catch (err) {
      setError(err instanceof ApiError ? err.userMessage() : "Verification failed.");
    } finally {
      setBusy(false);
    }
  }

  /**
   * New codes, by giving the same details again.
   *
   * `POST /auth/register` finds the unfinished sign-up that holds this
   * mobile, or else this email, and sends a new code to every contact it was
   * begun with, each replacing the last and its count of wrong tries. It
   * answers that the same way as a sign-up it has just made, so the page
   * cannot tell the two apart and does not try. A sixth request in an hour
   * for a contact, the first step's counted, is refused in the server's own
   * words. So is a contact that has meanwhile become an account's (409
   * `contact_taken`), except that the server's sentence also offers a
   * different contact, which this step cannot take; the page says only to
   * sign in.
   */
  async function resend() {
    setResending(true);
    setResent(false);
    setError(null);
    try {
      await registerAccount(details);
      setMobileCode("");
      setEmailCode("");
      setResent(true);
    } catch (err) {
      if (err instanceof ApiError && err.code === "contact_taken") {
        const field = err.field === "email" ? "email" : "mobile";
        setError(
          `An account already holds this ${field}. If it is yours, sign in with it instead.`,
        );
        return;
      }
      setError(
        err instanceof ApiError
          ? err.userMessage()
          : "We could not send new codes just now.",
      );
    } finally {
      setResending(false);
    }
  }

  const digits = (value: string) => value.replace(/\D/g, "").slice(0, 6);

  return (
    <AuthLayout
      title="Confirm your contacts"
      subtitle={
        email
          ? "A code has gone to your mobile and another to your email. Enter both."
          : "A code has gone to your mobile. Enter it below."
      }
      footer={
        <p className="text-center text-sm text-text-muted">
          If you have already finished signing up,{" "}
          <Link
            href={`/sign-in?contact=${encodeURIComponent(mobile)}`}
            className="font-medium text-accent-text hover:underline"
          >
            sign in instead
          </Link>
          .
        </p>
      }
    >
      <form method="post" onSubmit={submit} noValidate className="space-y-4">
        {error && <Alert tone="danger">{error}</Alert>}

        <Field label="Code sent to your mobile" hint={mobile} required>
          {(p) => (
            <Input
              {...p}
              value={mobileCode}
              onChange={(e) => setMobileCode(digits(e.target.value))}
              inputMode="numeric"
              autoComplete="one-time-code"
              placeholder="000000"
              className="text-center font-mono text-lg tracking-[0.4em]"
              autoFocus
            />
          )}
        </Field>

        {/* With a mobile alone, still a box for an email's code: a sign-up
            started before with an email has sent a code there too, and may
            need it to finish. Shown to everybody alike, since the page cannot
            know. It replaces a way back to the details, which could not
            change where the codes go. */}
        <Field
          label={
            email
              ? "Code sent to your email"
              : "Code sent to your email, if you gave one before"
          }
          hint={
            email ??
            "Only if you started signing up before and gave an email then: a code has gone there too. Otherwise leave this empty."
          }
          required={Boolean(email)}
        >
          {(p) => (
            <Input
              {...p}
              value={emailCode}
              onChange={(e) => setEmailCode(digits(e.target.value))}
              inputMode="numeric"
              autoComplete="one-time-code"
              placeholder="000000"
              className="text-center font-mono text-lg tracking-[0.4em]"
            />
          )}
        </Field>

        {/* Said to everybody alike: the server's one refusal cannot say that a
            code was cancelled, or which one. */}
        <p className="text-sm text-text-muted">
          Each code expires in ten minutes, or after five wrong tries; then send the codes
          again. They go to the contacts given when this sign-up began.
        </p>

        <Button
          type="submit"
          variant="primary"
          className="w-full"
          loading={busy}
          disabled={!ready}
        >
          <ShieldCheck className="size-4" />
          Confirm and sign in
        </Button>
      </form>
      {resent && (
        <p className="mt-3 text-sm text-text-muted" role="status">
          A new code is on its way to each contact given when this sign-up began. The
          earlier ones no longer work.
        </p>
      )}
      <div className="border-border-subtle mt-4 flex flex-wrap justify-between gap-2 border-t pt-4">
        <Button type="button" variant="ghost" loading={resending} onClick={resend}>
          Send the codes again
        </Button>
      </div>
    </AuthLayout>
  );
}
