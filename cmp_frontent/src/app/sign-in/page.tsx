/**
 * Staff sign-in.
 *
 * A password, then a second factor: the response says `mfa_required` and we
 * move to the verification step; the partial session the server issued
 * authorises nothing else.
 *
 * Data principals do not sign in here. They have no password - `password_hash`
 * is nullable for exactly this reason - and their portal, with its one-time
 * codes, sign-up and consent links, is a separate deployment. A link to it
 * sits in the footer for anyone who arrived at the wrong door.
 *
 * Every failure message is identical by design. The server refuses to say
 * whether an account exists, and repeating a friendlier message here would undo
 * that.
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
import { signInWithPassword } from "@/features/auth";
import { config } from "@/lib/config";
import { ApiError } from "@/lib/errors";
import { safeRedirectPath, useHydrated } from "@/lib/security";
import { useAuth } from "@/providers";

const passwordSchema = z.object({
  login: z.string().min(3, "Enter your email address or username"),
  password: z.string().min(1, "Enter your password"),
});

type PasswordForm = z.infer<typeof passwordSchema>;

export default function SignInPage() {
  return (
    <AuthLayout
      title="Sign in"
      subtitle="Sign in with your password, then the code sent to your email."
      footer={
        <p className="text-center text-xs text-text-subtle">
          Consented to a project, or want to exercise your rights?{" "}
          <a
            href={config.subjectPortalUrl}
            className="underline underline-offset-2 hover:text-text-muted"
          >
            Go to the consent portal
          </a>
        </p>
      }
    >
      {/* useSearchParams() forces client-side rendering, so Next requires a
          suspense boundary around anything that reads it. Without this the
          whole page bails out of prerendering. */}
      <React.Suspense fallback={<FormSkeleton />}>
        <StaffForm />
      </React.Suspense>
    </AuthLayout>
  );
}

function FormSkeleton() {
  return (
    <div className="space-y-4" aria-hidden="true">
      <div className="shimmer h-16 rounded-lg" />
      <div className="shimmer h-16 rounded-lg" />
      <div className="shimmer h-10 rounded-lg" />
    </div>
  );
}

function StaffForm() {
  const router = useRouter();
  const params = useSearchParams();
  const { refresh } = useAuth();
  const hydrated = useHydrated();
  const [formError, setFormError] = React.useState<string | null>(null);

  const form = useForm<PasswordForm>({
    resolver: zodResolver(passwordSchema),
    defaultValues: { login: "", password: "" },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    setFormError(null);
    try {
      const result = await signInWithPassword(values);

      if (result.mfa_required) {
        // The partial session is already set as a cookie. The verify screen is
        // the only thing it unlocks.
        router.push("/sign-in/verify");
        return;
      }

      await refresh();
      // `next` is attacker-controlled - it is whatever was in the link that
      // sent them here. Anything not a same-origin path becomes the dashboard.
      router.replace(safeRedirectPath(params.get("next"), "/dashboard"));
    } catch (error) {
      if (error instanceof ApiError) {
        // Field errors go on the field; everything else goes in the banner.
        const fields = error.fieldErrors();
        for (const [name, message] of Object.entries(fields)) {
          if (name === "login" || name === "password") {
            form.setError(name, { message });
          }
        }
        if (!Object.keys(fields).length) {
          setFormError(
            error.isRateLimited
              ? `${error.userMessage()} Try again in about ${Math.ceil(
                  (error.retryAfterSeconds ?? 60) / 60,
                )} minutes.`
              : error.userMessage(),
          );
        }
      } else {
        setFormError("Could not reach the server. Check your connection.");
      }
    }
  });

  return (
    // `method="post"` is not decorative, and removing it leaks the password.
    //
    // React attaches `onSubmit` at hydration. Press Sign in before that lands -
    // a cold cache, a slow connection, a chunk that 404s - and the browser does
    // the *native* submission instead. HTML's default method is GET, so every
    // field goes into the query string: the URL becomes
    // `/sign-in?login=...&password=...`, and that lands in browser history, in
    // the server's access log, and in the Referer header of the next request.
    //
    // With POST the unhydrated case is a POST to a page route, which fails
    // visibly and puts nothing in the URL. Observed, not theorised: this
    // happened on a first page load in development.
    <form
      method="post"
      onSubmit={onSubmit}
      className="space-y-4"
      noValidate
    >
      {formError && <Alert tone="danger">{formError}</Alert>}

      <Field label="Email or username" error={form.formState.errors.login?.message} required>
        {(props) => (
          <Input
            {...props}
            {...form.register("login")}
            type="text"
            autoComplete="username"
            autoFocus
            placeholder="you@organisation.example"
          />
        )}
      </Field>

      <Field label="Password" error={form.formState.errors.password?.message} required>
        {(props) => (
          <Input
            {...props}
            {...form.register("password")}
            type="password"
            autoComplete="current-password"
          />
        )}
      </Field>

      <Button
        type="submit"
        variant="primary"
        className="w-full"
        loading={form.formState.isSubmitting}
        // Before React attaches its handler the browser would perform a native
        // submission instead, and a disabled control cannot fire one. On a warm
        // load this lasts a few milliseconds; on a cold one it is honest.
        disabled={!hydrated}
      >
        Sign in
      </Button>

      <p className="text-center text-xs text-text-subtle">
        <Link
          href="/sign-in/reset"
          className="underline underline-offset-2 hover:text-text-muted"
        >
          Forgotten your password?
        </Link>
      </p>
    </form>
  );
}
