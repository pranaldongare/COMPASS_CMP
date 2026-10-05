/**
 * The public consent flow.
 *
 * This is the only screen a data principal is *required* to use, and the one
 * that has to be right. Four steps: validate the link, identify herself by one
 * contact, confirm it with a code, read the notice and choose.
 *
 * Between confirming and the notice, an account with no date of birth is asked
 * for one. The server records no consent from an unknown age (S2-01), and
 * asking before the notice is read is kinder than refusing after it.
 *
 * The link authenticates; it does not enrol. Somebody without an account is
 * sent to sign up and returns here, so that every artefact this screen writes
 * belongs to a data principal who can find it, read it and withdraw it later -
 * rather than to a set of details typed once at a collection site.
 *
 * This file holds the state machine and nothing else — which step is current,
 * what the link resolved to, which notice was served. Each step owns its own
 * form state, its own submission and its own error handling, and reports back
 * through a callback. That division is what keeps the flow's *shape* legible:
 * everything below is the sequence a person walks, in order.
 *
 * The decisions that are not cosmetic live with the steps that implement them,
 * except for the one this file owns:
 *
 * **An invalid link renders no notice content and does not say why.** Expired,
 * revoked, exhausted and mistyped all land in the same place. Naming the reason
 * would tell somebody guessing tokens which of their guesses was structurally
 * valid, and the page offers every possibility at once instead — which helps a
 * legitimate visitor and tells an attacker nothing.
 *
 * **An outage is not an invalid link.** Only the API's 404 means the link is
 * no good; anything else - no answer, a 5xx, a 429 - says so and offers to try
 * again, rather than sending somebody away to ask for a new link because the
 * service blinked. **A spent code is not asked for again.** Once the code is
 * accepted the flow is past it: if her profile or the notice then fails to
 * load, the `opening` step retries that alone (review UX-3).
 */
"use client";

import { AlertCircle, CheckCircle2 } from "lucide-react";
import { useParams } from "next/navigation";
import * as React from "react";

import { Alert, Button, Card, CardBody, Skeleton } from "@/components/ui/primitives";
import { DateOfBirthPrompt } from "@/components/security";
import { getMe } from "@/features/auth/api";
import { getLink, serveNotice } from "@/features/public-consent/api";
import {
  DoneStep,
  NoticeStep,
  IdentifyStep,
  Shell,
  Steps,
  VerifyStep,
  type Step,
} from "@/features/public-consent/components";
import { ApiError } from "@/lib/errors";
import type { LanguageCode, LinkView, ServedNotice } from "@/types";

export default function ConsentPage() {
  const { token } = useParams<{ token: string }>();

  const [step, setStep] = React.useState<Step>("loading");
  const [link, setLink] = React.useState<LinkView | null>(null);
  const [contact, setContact] = React.useState("");
  const [language, setLanguage] = React.useState<LanguageCode>("english");
  const [notice, setNotice] = React.useState<ServedNotice | null>(null);
  const [receipt, setReceipt] = React.useState<{ uuid: string; declined: boolean } | null>(
    null,
  );
  const [error, setError] = React.useState<string | null>(null);
  /** Bumped by "Try again" on an outage, to check the link once more. */
  const [attempt, setAttempt] = React.useState(0);
  const [opening, setOpening] = React.useState<{ busy: boolean; failed: string | null }>({
    busy: false,
    failed: null,
  });

  React.useEffect(() => {
    let cancelled = false;
    getLink(token)
      .then((data) => {
        if (cancelled) return;
        setLink(data);
        setLanguage(data.available_languages[0] ?? "english");
        setStep("identify");
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        // Only the API's own "no such link" means the link is no good.
        setStep(err instanceof ApiError && err.isNotFound ? "invalid" : "unavailable");
      });
    return () => {
      cancelled = true;
    };
  }, [token, attempt]);

  /**
   * Serve the notice in a language, and record which one was served.
   *
   * Called on entry to the notice step and again on every language change —
   * and the second is not a wasted request. Re-serving stamps a fresh
   * `served_at`, because she is now reading a different rendition and the
   * evidence has to say which one she was shown.
   */
  const serve = React.useCallback(
    async (next: LanguageCode) => {
      const served = await serveNotice(token, next);
      setNotice(served);
      setLanguage(next);
    },
    [token],
  );

  if (step === "loading") {
    return (
      <Shell>
        <Card>
          <CardBody className="space-y-3">
            <Skeleton className="h-6 w-2/3" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
          </CardBody>
        </Card>
      </Shell>
    );
  }

  /**
   * Past the code: her age if the account has none, then the notice. Run
   * again by "Try again" without asking for a code - the one she typed is
   * spent.
   */
  async function proceed() {
    setOpening({ busy: true, failed: null });
    setError(null);
    try {
      const me = await getMe();
      if (me.is_minor === null) {
        setStep("age");
        return;
      }
      await serve(language);
      setStep("notice");
    } catch (err) {
      setOpening({
        busy: false,
        failed: err instanceof ApiError ? err.userMessage() : "Could not load the notice.",
      });
      return;
    }
    setOpening({ busy: false, failed: null });
  }

  if (step === "unavailable") {
    return (
      <Shell>
        <Card>
          <CardBody className="py-10 text-center">
            <AlertCircle className="mx-auto size-8 text-text-subtle" aria-hidden="true" />
            <h1 className="mt-4 text-lg font-semibold">We could not open this link just now</h1>
            <p className="mx-auto mt-2 max-w-sm text-sm text-text-muted">
              The service did not answer. Your link may be fine - try again in a moment.
            </p>
            <Button
              variant="primary"
              className="mt-6"
              onClick={() => {
                setStep("loading");
                setAttempt((n) => n + 1);
              }}
            >
              Try again
            </Button>
          </CardBody>
        </Card>
      </Shell>
    );
  }

  if (step === "invalid") {
    return (
      <Shell>
        <Card>
          <CardBody className="py-10 text-center">
            <AlertCircle className="mx-auto size-8 text-text-subtle" aria-hidden="true" />
            <h1 className="mt-4 text-lg font-semibold">This link is not valid</h1>
            <p className="mx-auto mt-2 max-w-sm text-sm text-text-muted">
              It may have expired, been withdrawn, or been mistyped. Please ask the person
              who gave it to you for a current one.
            </p>
            <p className="mt-6 text-xs text-text-subtle">
              <a href="/rights" className="underline underline-offset-2">
                Your rights under the DPDP Act
              </a>
            </p>
          </CardBody>
        </Card>
      </Shell>
    );
  }

  return (
    <Shell projectName={link?.project_name} siteLabel={link?.site_label}>
      {error && (
        <Alert tone="danger" className="mb-4">
          {error}
        </Alert>
      )}

      <Steps current={step} />

      {step === "identify" && (
        <IdentifyStep
          token={token}
          languages={link?.available_languages ?? []}
          language={language}
          onLanguageChange={setLanguage}
          onDone={(given) => {
            setContact(given);
            setError(null);
            setStep("verify");
          }}
          onError={setError}
        />
      )}

      {step === "verify" && (
        <VerifyStep
          token={token}
          contact={contact}
          onDone={async () => {
            setStep("opening");
            await proceed();
          }}
          onError={setError}
          onChangeContact={() => {
            setError(null);
            setContact("");
            setStep("identify");
          }}
        />
      )}

      {step === "opening" && (
        <Card>
          <CardBody className="space-y-4 py-8 text-center">
            <CheckCircle2 className="mx-auto size-8 text-success-text" aria-hidden="true" />
            <h2 className="text-lg font-semibold">Your contact is confirmed</h2>
            {opening.failed ? (
              <>
                <p className="text-sm text-text-muted" role="alert">
                  {opening.failed} You do not need a new code.
                </p>
                <Button variant="primary" loading={opening.busy} onClick={proceed}>
                  Try again
                </Button>
              </>
            ) : (
              <p className="text-sm text-text-muted" role="status">
                Opening the notice…
              </p>
            )}
          </CardBody>
        </Card>
      )}

      {step === "age" && (
        <DateOfBirthPrompt
          onSaved={async () => {
            setStep("opening");
            await proceed();
          }}
        />
      )}

      {step === "notice" && notice && (
        <NoticeStep
          token={token}
          notice={notice}
          languages={link?.available_languages ?? []}
          language={language}
          onLanguageChange={async (next) => {
            try {
              await serve(next);
            } catch {
              setError("Could not switch language.");
            }
          }}
          onDone={(uuid, declined) => {
            setReceipt({ uuid, declined });
            setStep("done");
          }}
          onError={setError}
          onAgeRequired={() => {
            setError(null);
            setStep("age");
          }}
        />
      )}

      {step === "done" && receipt && <DoneStep receipt={receipt} />}
    </Shell>
  );
}
