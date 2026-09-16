/**
 * Step one: who is signing this.
 *
 * The link authenticates a person who already has an account; it does not
 * enrol one. That is the whole of this step's design, and the reason it asks
 * for a contact rather than a name, a mobile and an email:
 *
 * **Consent has to be attributable to somebody the register already knows.**
 * A record created from details typed at a collection site, confirmed by a code
 * sent to the same details, proves only that whoever stood there could read one
 * message. Binding the artefact to an existing data principal is what lets her
 * find it afterwards, withdraw it, and exercise her rights against it.
 *
 * **One contact, not two.** She proves one medium she already registered; the
 * others were proved when she signed up. Collecting a second here would be
 * personal data taken for no purpose, which is the thing this system exists to
 * prevent.
 *
 * **The mobile is the default** because a collection site is a place people
 * stand with a phone, and because a data principal may hold a mobile and no
 * email at all - the register allows exactly that.
 *
 * The reply to a code request is the same sentence whether or not the contact
 * is on the register, so this screen cannot tell somebody else's number from a
 * stranger's. That is why "create an account" is offered to everybody rather
 * than shown only to people who need it: the alternative is a screen that
 * answers "is this number registered?" to anyone who types one in.
 */
"use client";

import * as React from "react";

import {
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Field,
  Input,
} from "@/components/ui/primitives";
import { requestOtp } from "@/features/public-consent/api";
import { ApiError } from "@/lib/errors";

type Medium = "mobile" | "email";

export function IdentifyStep({
  token,
  onDone,
  onError,
}: {
  token: string;
  onDone: (contact: string) => void;
  onError: (message: string | null) => void;
}) {
  const [medium, setMedium] = React.useState<Medium>("mobile");
  const [contact, setContact] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    onError(null);
    try {
      await requestOtp(token, contact);
      onDone(contact);
    } catch (err) {
      onError(err instanceof ApiError ? err.userMessage() : "Could not send a code.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Your details</CardTitle>
        <p className="mt-1 text-sm text-text-muted">
          Consent is recorded against your account, so that you can read it, and withdraw
          it, whenever you like. Confirm one contact and we will show you the notice.
        </p>
      </CardHeader>
      <CardBody>
        {/* `method="post"`: before React attaches its handler the browser would
            submit natively, and HTML's default is GET - which would put the
            contact in the URL, the access log and the next Referer header. */}
        <form method="post" onSubmit={submit} className="space-y-4" noValidate>
          <fieldset className="space-y-2">
            <legend className="text-sm font-medium">Send my code to</legend>
            <div className="flex gap-4 text-sm">
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="medium"
                  value="mobile"
                  checked={medium === "mobile"}
                  onChange={() => {
                    setMedium("mobile");
                    setContact("");
                  }}
                />
                Mobile
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="medium"
                  value="email"
                  checked={medium === "email"}
                  onChange={() => {
                    setMedium("email");
                    setContact("");
                  }}
                />
                Email
              </label>
            </div>
          </fieldset>

          <Field
            label={medium === "mobile" ? "Mobile number" : "Email address"}
            hint="The one your account is registered with."
            required
          >
            {(props) => (
              <Input
                {...props}
                type={medium === "mobile" ? "tel" : "email"}
                value={contact}
                onChange={(e) => setContact(e.target.value)}
                autoComplete={medium === "mobile" ? "tel" : "email"}
                placeholder={medium === "mobile" ? "+91 ..." : "you@example.org"}
                autoFocus
                required
              />
            )}
          </Field>

          <Button
            type="submit"
            variant="primary"
            className="w-full"
            loading={busy}
            disabled={!contact.trim()}
          >
            Send the code
          </Button>
        </form>

        <p className="border-border-subtle mt-4 border-t pt-4 text-sm text-text-muted">
          No account yet?{" "}
          <a
            href={`/sign-up?next=${encodeURIComponent(`/c/${token}`)}`}
            className="font-medium underline underline-offset-2"
          >
            Create one
          </a>{" "}
          — it takes a minute, and this page will be waiting when you come back.
        </p>
      </CardBody>
    </Card>
  );
}
