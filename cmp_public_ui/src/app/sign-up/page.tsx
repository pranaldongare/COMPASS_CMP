/**
 * Self-registration for a data principal.
 *
 * A mobile is required and an email is optional, because the one-time codes
 * that *are* her sign-in should go to the thing she carries. Every contact she
 * gives is authenticated before the account is hers: a code goes to each, and
 * both are entered here, on the second step, after which she is signed in.
 *
 * The first step answers the same way whether or not the details are already
 * registered - sign-up is unauthenticated, and "this number is taken" would be
 * a membership oracle for who is a data principal on this platform.
 */
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ShieldCheck, UserPlus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import * as React from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { AuthLayout } from "@/components/layout/auth-layout";
import { Alert, Button, Field, Input } from "@/components/ui/primitives";
import { register as registerAccount, registerVerify } from "@/features/auth";
import { ApiError } from "@/lib/errors";
import { useAuth } from "@/providers";
import { email, mobile } from "@/schemas/contacts";

const EARLIEST = "1900-01-01";

const schema = z.object({
  full_name: z.string().min(2, "Enter your full name").max(120),
  mobile,
  email: z.union([z.literal(""), email]),
  dob: z
    .string()
    .min(1, "Enter your date of birth")
    .refine((v) => v > EARLIEST, "Enter a valid date of birth")
    .refine(
      (v) => v < new Date().toISOString().slice(0, 10),
      "Date of birth must be in the past",
    ),
});
type Values = z.infer<typeof schema>;

export default function SignUpPage() {
  const [given, setGiven] = React.useState<{ mobile: string; email: string | null } | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  // A contact that already belongs to an account. The message goes on that
  // field so it can be changed, and sign-in is offered with it filled in.
  const [taken, setTaken] = React.useState<{ field: "mobile" | "email"; value: string } | null>(null);

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { full_name: "", mobile: "", email: "", dob: "" },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    setError(null);
    setTaken(null);
    try {
      await registerAccount({
        full_name: values.full_name,
        mobile: values.mobile,
        dob: values.dob,
        email: values.email ? values.email : null,
      });
      setGiven({ mobile: values.mobile, email: values.email ? values.email : null });
    } catch (caught) {
      if (caught instanceof ApiError && caught.code === "contact_taken") {
        const field = caught.field === "email" ? "email" : "mobile";
        form.setError(field, { message: caught.userMessage() });
        setTaken({ field, value: field === "email" ? (values.email ?? "") : values.mobile });
        form.setFocus(field);
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
    return <VerifyStep mobile={given.mobile} email={given.email} />;
  }

  return (
    <AuthLayout
      title="Create your account"
      subtitle="For people whose data is being collected. Staff accounts are issued by your administrator."
      footer={
        <p className="text-center text-sm text-text-muted">
          Already registered?{" "}
          <Link href="/sign-in" className="font-medium text-accent-text hover:underline">
            Sign in
          </Link>
        </p>
      }
    >
      <form method="post" onSubmit={onSubmit} noValidate className="space-y-4">
        {error && <Alert tone="danger">{error}</Alert>}
        {taken && (
          <Alert tone="warning" title={`That ${taken.field} is already registered`}>
            <p>
              If it is yours, sign in with it - there is no password, we send a code. Otherwise
              change it below.
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

        <Field
          label="Mobile number"
          hint="Your sign-in codes come here. We will send one now to confirm it."
          error={form.formState.errors.mobile?.message}
          required
        >
          {(p) => (
            <Input {...p} {...form.register("mobile")} type="tel" autoComplete="tel" placeholder="+91 ..." />
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

        <Field
          label="Date of birth"
          hint="The law treats people under 18 differently: consent for a child has to come from a parent or guardian. We ask so we can apply the right rule to you."
          error={form.formState.errors.dob?.message}
          required
        >
          {(p) => (
            <Input
              {...p}
              {...form.register("dob")}
              type="date"
              max={new Date().toISOString().slice(0, 10)}
              min={EARLIEST}
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
 * a right mobile code. If the details were already registered, the codes that
 * arrived are sign-in codes and belong on the sign-in page; the message below
 * says so without saying which case this is.
 */
function VerifyStep({ mobile, email }: { mobile: string; email: string | null }) {
  const router = useRouter();
  const { refresh } = useAuth();
  const [mobileCode, setMobileCode] = React.useState("");
  const [emailCode, setEmailCode] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const ready = mobileCode.length === 6 && (!email || emailCode.length === 6);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await registerVerify({
        mobile,
        mobile_code: mobileCode,
        email_code: email ? emailCode : null,
      });
      await refresh();
      router.replace("/my-consents");
    } catch (err) {
      setError(err instanceof ApiError ? err.userMessage() : "Verification failed.");
    } finally {
      setBusy(false);
    }
  }

  const digits = (value: string) => value.replace(/\D/g, "").slice(0, 6);

  return (
    <AuthLayout
      title="Confirm your contacts"
      subtitle={
        email
          ? "If those details are new to us, a code has gone to your mobile and another to your email. Enter both."
          : "If that number is new to us, a code has gone to your mobile. Enter it to finish."
      }
      footer={
        <p className="text-center text-sm text-text-muted">
          Already had an account? The code you received is a sign-in code:{" "}
          <Link
            href={`/sign-in?contact=${encodeURIComponent(mobile)}`}
            className="font-medium text-accent-text hover:underline"
          >
            enter it on the sign-in page
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

        {email && (
          <Field label="Code sent to your email" hint={email} required>
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
        )}

        <Button type="submit" variant="primary" className="w-full" loading={busy} disabled={!ready}>
          <ShieldCheck className="size-4" />
          Confirm and sign in
        </Button>
      </form>
    </AuthLayout>
  );
}
