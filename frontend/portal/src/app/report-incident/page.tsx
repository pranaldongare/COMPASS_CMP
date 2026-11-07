/**
 * Reporting an incident - public, no authentication (ADR 0037).
 *
 * The one link anybody can be given. It says what happens before it asks for
 * anything, because a person who has found something wrong wants to know who
 * will read it and what becomes of their name: both offices hear of it, one of
 * them takes it up or closes it, and the name and address stay with the report.
 * What the page does not promise is an outcome. A report starts nothing by
 * itself; an officer reads it first.
 */
"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { BrandMark, SignalField } from "@/components/ui/graphics";
import { Alert, Card, CardBody, CardHeader, CardTitle, Mono } from "@/components/ui/primitives";
import type { IncidentReportReceipt } from "@/features/report-incident";
import { ReportForm } from "@/features/report-incident/components/report-form";

export default function ReportIncidentPage() {
  const [receipt, setReceipt] = React.useState<IncidentReportReceipt | null>(null);

  return (
    <div className="min-h-dvh bg-bg-subtle">
      <header className="brand-gradient relative overflow-hidden">
        <SignalField className="absolute -right-24 -top-32 h-96 w-96 text-white/35" />
        <div className="relative mx-auto max-w-2xl px-4 py-10 sm:py-14">
          <span className="grid size-11 place-items-center rounded-xl bg-white/15 ring-1 ring-white/25">
            <BrandMark className="size-6 text-white" />
          </span>
          <h1 className="mt-4 text-3xl font-semibold tracking-tight text-white">
            Report an incident
          </h1>
          <p className="mt-3 max-w-xl text-sm leading-relaxed text-white/80">
            Tell us if you think personal data we hold has been lost, stolen, seen by someone who
            should not have seen it, or put at risk in any other way. Anyone can use this page, and
            you do not need an account.
          </p>
        </div>
      </header>

      <main id="main" className="mx-auto max-w-2xl px-4 py-8 sm:py-10">
        {receipt ? (
          <Alert tone="success" title="Report received">
            <p>{receipt.message}</p>
            <p className="mt-1 text-xs">
              Your reference is <Mono>{receipt.reference}</Mono>. Keep it, and quote it if you
              contact us. You will also get an email with this reference.
            </p>
          </Alert>
        ) : (
          <div className="space-y-5">
            <Card>
              <CardHeader>
                <CardTitle>What happens to your report</CardTitle>
              </CardHeader>
              <CardBody>
                <ol className="list-decimal space-y-2 pl-5 text-sm leading-relaxed text-text-muted">
                  <li>
                    We email a code to the address you give, to confirm it is yours. Nothing is
                    saved until you send the report with that code.
                  </li>
                  <li>
                    Your report is given a reference, which we show you here and email to you.
                  </li>
                  <li>
                    Our Privacy Office, which is the Data Protection Officer and the Legal team, is
                    told straight away. They read it, and either take it up as an incident or close
                    it and record why.
                  </li>
                  <li>
                    We keep your name and email with the report. The people handling it can see
                    them, and may contact you if they need to know more. If we close your report
                    without taking it up, you can ask us through your rights, from the same email
                    address, to see it or to erase your name and email from it.
                  </li>
                </ol>
                <p className="mt-3 text-xs text-text-subtle">
                  To ask what we hold about you, or to make a complaint, go to{" "}
                  <Link href="/rights" className="underline underline-offset-2 hover:text-text-muted">
                    your rights
                  </Link>
                  .
                </p>
              </CardBody>
            </Card>

            <Card id="report">
              <CardHeader>
                <CardTitle>Your report</CardTitle>
              </CardHeader>
              <CardBody>
                <ReportForm onDone={setReceipt} />
              </CardBody>
            </Card>
          </div>
        )}

        <p className="mt-8 text-center text-xs">
          <Link
            href="/rights"
            className="inline-flex items-center gap-1 text-text-subtle underline underline-offset-2 hover:text-text-muted"
          >
            <ArrowLeft className="size-3.5" aria-hidden="true" />
            Your rights
          </Link>
        </p>
      </main>
    </div>
  );
}
