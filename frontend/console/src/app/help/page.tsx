/**
 * The staff console's help manual, open to anyone who reaches the console.
 *
 * Signed in, it opens filtered to the reader's own role; signed out, it shows
 * every section and offers the way to sign in.
 */
"use client";

import * as React from "react";
import { useSearchParams } from "next/navigation";
import { ContactPanel } from "@/features/help/components/contact-panel";
import { HelpHeader } from "@/features/help/components/help-header";
import { HelpManual } from "@/features/help/components/help-manual";
import { INTRO, ROLES, SECTIONS } from "@/features/help/content";
import { helpReturn } from "@/components/layout/help-link";
import { safeRedirectPath } from "@/lib/security";
import { useSessionState } from "@/providers";

export default function HelpPage() {
  return (
    <React.Suspense fallback={null}>
      <Help />
    </React.Suspense>
  );
}

function Help() {
  const session = useSessionState();
  // The page Help was opened from, if it is one of ours (`HelpLink`).
  const from = helpReturn(useSearchParams().get("from"), (v) => safeRedirectPath(v, ""));
  const me = session.status === "full" ? session.me : null;
  // A member of staff reading the console's manual reads their staff role's
  // sections, not the principal role a portal session would carry.
  const role = ROLES.some((r) => r.value === me?.role) ? (me?.role ?? "") : "";

  return (
    <div id="top" className="min-h-dvh">
      <HelpHeader
        back={
          me
            ? from
              ? { href: from, label: "Back to where you were" }
              : { href: "/dashboard", label: "Back to the console" }
            : { href: "/sign-in", label: "Sign in" }
        }
      />
      <main id="main">
        <HelpManual
          product="COMPASS CMP"
          intro={INTRO}
          sections={SECTIONS}
          roles={ROLES}
          initialRole={role}
          contact={
            <ContactPanel>
              Trouble signing in, or a page your role should have but does not? Ask your
              administrator - they manage staff accounts and roles.
            </ContactPanel>
          }
        />
      </main>
    </div>
  );
}
