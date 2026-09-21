/**
 * A nominee acting - steps 4 to 8 of the nomination flow.
 *
 * Two steps on one page. First he identifies himself: the nomination's
 * reference and his contact, and a code goes to the contact *she* recorded -
 * checked against what she wrote down, not against what he now tells us.
 * Then the request itself, with evidence of the triggering event, which the
 * Privacy Office decides on before anything runs.
 *
 * Both steps answer neutrally. Whether a nomination exists is not confirmed
 * to somebody who has only its reference.
 */
"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import * as React from "react";

import { FileInput } from "@/components/forms";
import { BrandMark } from "@/components/ui/graphics";
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Field,
  Input,
  Select,
  Textarea,
} from "@/components/ui/primitives";
import { nomineeRequest, nomineeStart } from "@/features/rights/api";
import { REQUEST_TYPE_COPY } from "@/features/rights/components/copy";
import type { RightsRequestType, RightsTriggerEvent } from "@/types";
import { RIGHTS_REQUEST_TYPES } from "@/types";

function messageOf(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}

export default function NomineePage() {
  // useSearchParams() forces client rendering, so Next needs a suspense
  // boundary around anything that reads it.
  return (
    <React.Suspense fallback={null}>
      <NomineeForm />
    </React.Suspense>
  );
}

function NomineeForm() {
  // Prefilled from the acceptance page and from the message sent on
  // acceptance, both of which carry `?nomination=`. Typing a UUID by hand was
  // the step people got wrong, and the neutral reply then told them nothing.
  const params = useSearchParams();
  const [nominationUuid, setNominationUuid] = React.useState(params.get("nomination") ?? "");
  const [contact, setContact] = React.useState("");
  const [started, setStarted] = React.useState<string | null>(null);
  const [code, setCode] = React.useState("");
  const [type, setType] = React.useState<RightsRequestType>("access");
  const [text, setText] = React.useState("");
  const [event, setEvent] = React.useState<RightsTriggerEvent>("death");
  const [evidence, setEvidence] = React.useState<File | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [pending, setPending] = React.useState(false);
  const [done, setDone] = React.useState<{ reference: string; message: string } | null>(null);

  async function start(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setPending(true);
    try {
      const result = await nomineeStart({ nomination_uuid: nominationUuid.trim(), contact: contact.trim() });
      setStarted(result.message ?? "If the details match, a code has been sent.");
    } catch (err) {
      setError(messageOf(err, "Could not start. Check the reference and try again."));
    } finally {
      setPending(false);
    }
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setPending(true);
    try {
      setDone(
        await nomineeRequest({
          nomination_uuid: nominationUuid.trim(),
          code: code.trim(),
          request_type: type,
          request_text: text,
          trigger_event: event,
          evidence,
        }),
      );
    } catch (err) {
      setError(messageOf(err, "Could not record the request."));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="min-h-dvh bg-bg-subtle">
      <header className="brand-gradient">
        <div className="mx-auto max-w-2xl px-4 py-10">
          <span className="grid size-11 place-items-center rounded-xl bg-white/15 ring-1 ring-white/25">
            <BrandMark className="size-6 text-white" />
          </span>
          <h1 className="mt-4 text-3xl font-semibold tracking-tight text-white">
            Acting for someone who nominated you
          </h1>
          <p className="mt-3 max-w-xl text-sm leading-relaxed text-white/80">
            Section 14. If the person who nominated you has died or cannot act, you may
            exercise the rights they granted you. We verify you against the contact they
            recorded, and we decide whether the event is evidenced before anything runs.
          </p>
        </div>
      </header>

      <main id="main" className="mx-auto max-w-2xl space-y-5 px-4 py-8">
        {done ? (
          <Alert tone="success" title={`Recorded as ${done.reference}`}>
            <p>{done.message}</p>
          </Alert>
        ) : (
          <>
            <Card>
              <CardHeader>
                <CardTitle>1. Who you are</CardTitle>
              </CardHeader>
              <CardBody>
                <form method="post" onSubmit={start} noValidate className="space-y-4">
                  {error && !started && <Alert tone="danger">{error}</Alert>}
                  <Field
                    label="The nomination reference"
                    hint="It was shown when you accepted, and sent to your recorded contacts in the message titled “keep this message”. The person who nominated you can also see it on their account. You do not sign in anywhere: this page is where you act."
                    required
                  >
                    {(p) => (
                      <Input
                        {...p}
                        value={nominationUuid}
                        onChange={(e) => setNominationUuid(e.target.value)}
                        autoComplete="off"
                        disabled={Boolean(started)}
                      />
                    )}
                  </Field>
                  <Field
                    label="Your email or mobile"
                    hint="The one they recorded for you. The code goes there, whatever is typed here."
                    required
                  >
                    {(p) => (
                      <Input
                        {...p}
                        value={contact}
                        onChange={(e) => setContact(e.target.value)}
                        autoComplete="off"
                        disabled={Boolean(started)}
                      />
                    )}
                  </Field>
                  {started ? (
                    <Alert tone="info">
                      <p>{started}</p>
                    </Alert>
                  ) : (
                    <Button type="submit" variant="primary" loading={pending} disabled={!nominationUuid || !contact}>
                      Send me a code
                    </Button>
                  )}
                </form>
              </CardBody>
            </Card>

            {started && (
              <Card>
                <CardHeader>
                  <CardTitle>2. The request</CardTitle>
                </CardHeader>
                <CardBody>
                  <form method="post" onSubmit={submit} noValidate className="space-y-4">
                    {error && <Alert tone="danger">{error}</Alert>}
                    <Field label="The code we sent" required>
                      {(p) => (
                        <Input
                          {...p}
                          value={code}
                          onChange={(e) => setCode(e.target.value)}
                          inputMode="numeric"
                          autoComplete="one-time-code"
                          maxLength={10}
                        />
                      )}
                    </Field>
                    <Field label="What you are asking for on their behalf" required>
                      {(p) => (
                        <Select {...p} value={type} onChange={(e) => setType(e.target.value as RightsRequestType)}>
                          {RIGHTS_REQUEST_TYPES.map((t) => (
                            <option key={t} value={t}>
                              {REQUEST_TYPE_COPY[t].label} ({REQUEST_TYPE_COPY[t].section})
                            </option>
                          ))}
                        </Select>
                      )}
                    </Field>
                    <p className="text-xs text-text-muted">{REQUEST_TYPE_COPY[type].blurb}</p>
                    <Field label="The request" required>
                      {(p) => (
                        <Textarea {...p} rows={4} value={text} onChange={(e) => setText(e.target.value)} maxLength={20_000} />
                      )}
                    </Field>
                    <Field
                      label="What has happened"
                      hint="The Act gives no standard of proof; we publish ours and apply it consistently. The Privacy Office decides whether the event is evidenced before the request runs."
                      required
                    >
                      {(p) => (
                        <Select {...p} value={event} onChange={(e) => setEvent(e.target.value as RightsTriggerEvent)}>
                          <option value="death">They have died</option>
                          <option value="incapacity">They are unable to act</option>
                        </Select>
                      )}
                    </Field>
                    <FileInput
                      label="Evidence"
                      hint="A certificate or a medical letter. PDF or image, up to 25 MB."
                      accept="application/pdf,image/png,image/jpeg"
                      maxBytes={25 * 1024 * 1024}
                      file={evidence}
                      onChange={setEvidence}
                    />
                    <Button type="submit" variant="primary" loading={pending} disabled={!code || text.trim().length < 10}>
                      Record the request
                    </Button>
                  </form>
                </CardBody>
              </Card>
            )}
          </>
        )}

        <p className="mt-4 text-center text-xs">
          <Link
            href="/rights"
            className="inline-flex items-center gap-1 text-text-subtle underline underline-offset-2 hover:text-text-muted"
          >
            <ArrowLeft className="size-3.5" aria-hidden="true" />
            Your rights under the Act
          </Link>
        </p>
      </main>
    </div>
  );
}
