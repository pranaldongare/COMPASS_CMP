/**
 * The portal's help manual, open to anyone - the sign-in page links to it for
 * somebody who has not yet registered.
 */
"use client";

import Link from "next/link";

import { ContactPanel } from "@/features/help/components/contact-panel";
import { HelpHeader } from "@/features/help/components/help-header";
import { HelpManual } from "@/features/help/components/help-manual";
import { INTRO, SECTIONS } from "@/features/help/content";
import { useSessionState } from "@/providers";

export default function HelpPage() {
  const session = useSessionState();
  const signedIn = session.status === "full";

  return (
    <div id="top" className="min-h-dvh">
      <HelpHeader
        back={
          signedIn
            ? { href: "/my-consents", label: "Back to your consents" }
            : { href: "/sign-in", label: "Sign in" }
        }
      />
      <main id="main">
        <HelpManual
          product="Consent Portal"
          intro={INTRO}
          sections={SECTIONS}
          contact={
            <ContactPanel>
              You can also make a request without signing in, on{" "}
              <Link
                href="/rights"
                className="font-semibold text-white underline underline-offset-2"
              >
                Your rights and how to exercise them
              </Link>
              . If you are not satisfied with our answer, you may complain to the Data
              Protection Board of India.
            </ContactPanel>
          }
        />
      </main>
    </div>
  );
}
