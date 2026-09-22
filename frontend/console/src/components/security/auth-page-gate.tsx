/**
 * The auth pages, pointed the right way for whoever arrives.
 *
 * A sign-in form assumes a visitor with no session. Three other people reach
 * it, and each used to be shown the wrong thing:
 *
 * - **Already signed in**, from a bookmark or a link in an old email: the
 *   password form, which would sign them in a second time. They belong on the
 *   page they were after, or the dashboard.
 * - **Halfway through the second factor**, back on `/sign-in`: the password
 *   form again, when the code step is the one outstanding.
 * - **On the code step with no session at all** - the partial session
 *   expired, or the URL was typed: a code box that refuses every code with
 *   "invalid", when the honest answer is to start again.
 *
 * A data principal who somehow holds a session here is sent to her portal,
 * as `RequireAuth` does for a protected page.
 *
 * The form renders while the question is asked - a sign-in form discloses
 * nothing, so there is no flash to hide - and the redirect happens the moment
 * the answer arrives. `next` is honoured only as a same-origin path
 * (`safeRedirectPath`), exactly as the forms themselves honour it.
 */
"use client";

import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";

import { config } from "@/lib/config";
import { safeRedirectPath } from "@/lib/security";
import { useSessionState } from "@/providers";

/** Which step of sign-in this page is. */
export type AuthStep = "password" | "code" | "reset";

export function AuthPageGate({
  step,
  children,
}: {
  step: AuthStep;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const params = useSearchParams();
  const state = useSessionState();

  const next = safeRedirectPath(params.get("next"), "");
  const carry = next ? `?next=${encodeURIComponent(next)}` : "";

  React.useEffect(() => {
    switch (state.status) {
      case "loading":
        return;
      case "full":
        if (state.me.role === "data_subject") {
          // Another origin; the router cannot take her there.
          window.location.replace(config.subjectPortalUrl);
        } else if (step !== "reset") {
          // Somebody signed in has no business on the password or code step.
          // A reset page is different: a signed-in person may legitimately be
          // finishing a reset from an email, so it stays.
          router.replace(next || "/dashboard");
        }
        return;
      case "partial":
        if (step === "password") router.replace(`/sign-in/verify${carry}`);
        return;
      case "none":
        if (step === "code") router.replace(`/sign-in${carry}`);
        return;
    }
  }, [state, step, next, carry, router]);

  return <>{children}</>;
}
