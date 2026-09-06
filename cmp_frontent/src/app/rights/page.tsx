/**
 * Rights information and the request form — public, no authentication.
 *
 * Rule 9 and Rule 14(1). Published so someone who has lost their notice can
 * still find out what they are entitled to and how to ask for it - and, since
 * Rule 3 puts the grievance route in every notice, ask for it from here without
 * an account. The form answers with one neutral sentence whatever happened,
 * and the verification code goes to the contact already on file.
 *
 * The Board complaint route is stated alongside the internal one, not instead of
 * it. Telling someone only about the grievance process misstates the remedy
 * available to them.
 */
"use client";

import { ArrowLeft, ArrowRight } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { BrandMark, SignalField } from "@/components/ui/graphics";
import { Alert, Card, CardBody, CardHeader, CardTitle, Mono, Skeleton } from "@/components/ui/primitives";
import { getRights, type RightsPayload } from "@/features/rights";
import { PublicRequestForm } from "@/features/rights/components/request-form";
import { VerifyForm } from "@/features/rights/components/verify-form";
import type { PublicRequestReceipt, PublicVerifyResult } from "@/types";

export default function RightsPage() {
  const [data, setData] = React.useState<RightsPayload | null>(null);
  const [failed, setFailed] = React.useState(false);
  const [receipt, setReceipt] = React.useState<PublicRequestReceipt | null>(null);
  const [verified, setVerified] = React.useState<PublicVerifyResult | null>(null);
  const [verifyOnly, setVerifyOnly] = React.useState(false);

  React.useEffect(() => {
    getRights()
      .then(setData)
      .catch(() => setFailed(true));
  }, []);

  return (
    <div className="min-h-dvh bg-bg-subtle">
      <header className="brand-gradient relative overflow-hidden">
        <SignalField className="absolute -right-24 -top-32 h-96 w-96 text-white/35" />
        <div className="relative mx-auto max-w-2xl px-4 py-10 sm:py-14">
          <span className="grid size-11 place-items-center rounded-xl bg-white/15 ring-1 ring-white/25">
            <BrandMark className="size-6 text-white" />
          </span>
          <h1 className="mt-4 text-3xl font-semibold tracking-tight text-white">
            Your rights
          </h1>
          <p className="mt-3 max-w-xl text-sm leading-relaxed text-white/80">
            Under the Digital Personal Data Protection Act 2023, you have rights over
            the personal data we hold about you. This page explains what they are, how
            to use them, and lets you make a request without an account.
          </p>
        </div>
      </header>

      <main id="main" className="mx-auto max-w-2xl px-4 py-8 sm:py-10">
      {failed && (
        <Alert tone="warning" className="mb-6">
          We could not load our current contact details. The rights below still
          apply; please try again shortly.
        </Alert>
      )}

      {!data && !failed && <Skeleton className="h-96" />}

      {data && (
        <div className="space-y-5">
          <Card>
            <CardHeader>
              <CardTitle>What you can ask for</CardTitle>
            </CardHeader>
            <CardBody>
              <dl className="space-y-5">
                {data.how_to_exercise.map((item) => (
                  <div key={item.right}>
                    <dt className="flex flex-wrap items-baseline gap-2">
                      <span className="text-sm font-semibold">{item.right}</span>
                      <span className="rounded-full border border-border bg-bg-inset px-2 py-0.5 text-2xs text-text-subtle">
                        {item.section}
                      </span>
                    </dt>
                    <dd className="mt-1 text-sm leading-relaxed text-text-muted">
                      {item.description}
                    </dd>
                  </div>
                ))}
              </dl>
            </CardBody>
          </Card>

          <Card id="request">
            <CardHeader>
              <CardTitle>Make a request</CardTitle>
              <p className="mt-1 text-xs text-text-muted">
                {data.response_time}{" "}
                <Link href="/sign-in" className="text-accent-text underline underline-offset-2">
                  Signed in
                </Link>
                , your request is verified at once; from here, we send a code to the contact we
                already hold for you.
              </p>
            </CardHeader>
            <CardBody className="space-y-4">
              {verified ? (
                <Alert tone="success" title="Verified">
                  <p>{verified.message}</p>
                  <p className="mt-1 text-xs">
                    Your reference is <Mono>{verified.reference}</Mono>. Keep it.
                  </p>
                </Alert>
              ) : receipt ? (
                <>
                  <Alert tone="info" title="Recorded">
                    <p>{receipt.message}</p>
                    <p className="mt-1 text-xs">
                      Your reference is <Mono>{receipt.reference}</Mono>. Quote it if you contact us.
                    </p>
                  </Alert>
                  <VerifyForm reference={receipt.reference} onDone={setVerified} />
                </>
              ) : verifyOnly ? (
                <>
                  <VerifyForm onDone={setVerified} />
                  <button type="button" className="text-xs text-text-subtle underline underline-offset-2" onClick={() => setVerifyOnly(false)}>
                    Make a new request instead
                  </button>
                </>
              ) : (
                <>
                  <PublicRequestForm onDone={setReceipt} />
                  <button type="button" className="text-xs text-text-subtle underline underline-offset-2" onClick={() => setVerifyOnly(true)}>
                    Already have a reference and a code? Verify it here.
                  </button>
                </>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Withdrawing your consent</CardTitle>
            </CardHeader>
            <CardBody className="space-y-3">
              <p className="text-sm leading-relaxed text-text-muted">
                {data.withdraw_consent}
              </p>
              <Link
                href="/sign-in"
                className="inline-block text-sm text-accent-text underline underline-offset-2"
              >
                Sign in to review or withdraw your consents
              </Link>
              <p className="text-xs text-text-subtle">
                Withdrawing stops future processing for the purposes you withdraw.
                It does not by itself delete data already collected — ask for
                erasure if that is what you want.
              </p>
            </CardBody>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Acting for someone who nominated you</CardTitle>
            </CardHeader>
            <CardBody className="space-y-2">
              <p className="text-sm leading-relaxed text-text-muted">
                Under section 14 a person may name somebody to exercise these rights if they die
                or cannot act. If that person is you, and the time has come, start here.
              </p>
              <Link href="/rights/nominee" className="inline-flex items-center gap-1 text-sm text-accent-text underline underline-offset-2">
                Make a request as a nominee
                <ArrowRight className="size-3.5" aria-hidden="true" />
              </Link>
            </CardBody>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Contacting us</CardTitle>
            </CardHeader>
            <CardBody className="space-y-2">
              <p className="text-sm">
                <span className="text-text-muted">Data Protection Officer: </span>
                <a
                  href={`mailto:${data.dpo_contact}`}
                  className="text-accent-text underline underline-offset-2"
                >
                  {data.dpo_contact}
                </a>
              </p>
              <p className="text-sm text-text-muted">{data.response_time}</p>
            </CardBody>
          </Card>

          <Alert tone="info" title="If you are not satisfied">
            <p className="leading-relaxed">{data.board_complaint}</p>
          </Alert>
        </div>
      )}

      <p className="mt-8 text-center text-xs">
        <Link
          href="/sign-in"
          className="inline-flex items-center gap-1 text-text-subtle underline underline-offset-2 hover:text-text-muted"
        >
          <ArrowLeft className="size-3.5" aria-hidden="true" />
          Back to sign in
        </Link>
      </p>
      </main>
    </div>
  );
}
