/**
 * The sign-in and sign-up pages, pointed the right way for whoever arrives.
 *
 * Both forms assume a visitor with no session. Two other people reach them:
 *
 * - **A data principal already signed in**, from a bookmark or an old
 *   email: she was shown the form and could sign in a second time. She
 *   belongs on the page she was after, or her consents.
 * - **A member of staff**, whose session is shared with the console when
 *   both run on one host, or who is halfway through the console's second
 *   factor. Nothing here is for them: a full session goes to the console, a
 *   partial one to the console's code step, which is where `RequireAuth`
 *   already sends them from a protected page.
 *
 * The form renders while the question is asked - it discloses nothing - and
 * the redirect happens when the answer arrives. `next` is honoured only as a
 * same-origin path (`safeRedirectPath`), as the forms honour it.
 */
"use client";

import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";

import { config } from "@/lib/config";
import { safeRedirectPath } from "@/lib/security";
import { useSessionState } from "@/providers";

export function AuthPageGate({ children }: { children: React.ReactNode }) {
  // `useSearchParams` needs a boundary; the form itself is the right
  // fallback, since it is what renders in every case but the redirect.
  return (
    <React.Suspense fallback={<>{children}</>}>
      <Gate>{children}</Gate>
    </React.Suspense>
  );
}

function Gate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const params = useSearchParams();
  const state = useSessionState();
  const next = safeRedirectPath(params.get("next"), "");

  React.useEffect(() => {
    if (state.status === "full") {
      if (state.me.role === "data_subject") {
        router.replace(next || "/my-consents");
      } else {
        // Another origin; the router cannot take them there.
        window.location.replace(new URL("/dashboard", config.staffPortalUrl).toString());
      }
    } else if (state.status === "partial") {
      window.location.replace(new URL("/sign-in/verify", config.staffPortalUrl).toString());
    }
  }, [state, next, router]);

  return <>{children}</>;
}
