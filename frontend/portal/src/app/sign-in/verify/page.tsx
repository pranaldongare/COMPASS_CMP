/**
 * `/sign-in/verify` exists on the staff console, not here: nobody who belongs
 * on this portal has a password, so there is no second factor to complete.
 * The path still gets typed, bookmarked and carried in `?next=` by people who
 * use both sites, and answering it with a 404 told them nothing. It forwards
 * to the console's code step, query string and all.
 */
"use client";

import { useSearchParams } from "next/navigation";
import * as React from "react";

import { AuthLayout } from "@/components/layout/auth-layout";
import { config } from "@/lib/config";

export default function VerifyForwardPage() {
  return (
    <AuthLayout
      title="Verify it is you"
      subtitle="Staff sign in on the console. Taking you there."
    >
      <React.Suspense fallback={null}>
        <Forward />
      </React.Suspense>
      <p className="text-center text-sm text-text-muted">
        If nothing happens,{" "}
        <a
          href={new URL("/sign-in/verify", config.staffPortalUrl).toString()}
          className="font-medium text-accent-text hover:underline"
        >
          continue on the staff console
        </a>
        .
      </p>
    </AuthLayout>
  );
}

function Forward() {
  const params = useSearchParams();
  React.useEffect(() => {
    const target = new URL("/sign-in/verify", config.staffPortalUrl);
    // Carried as it came; the console applies its own same-origin rule to it.
    const next = params.get("next");
    if (next) target.searchParams.set("next", next);
    window.location.replace(target.toString());
  }, [params]);
  return null;
}
