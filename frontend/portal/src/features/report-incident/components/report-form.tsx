/**
 * The report, and the code that lets it in.
 *
 * One form, pressed twice. The first press checks what was typed and sends a
 * code to the address; the second sends the report with that code. The form
 * stays on the page between the two, so a wrong code costs the person nothing
 * they typed, and a server's complaint about any field lands on that field.
 *
 * A code is good for the address it went to and no other. So the second step
 * shows only while the box still holds that address: changing it takes the form
 * back to the first press, rather than letting the person type a code that
 * could never work.
 *
 * What goes wrong with a press is said beside the buttons and brought into
 * view: at the foot of a long form, on a phone, the top of it is a long way off.
 *
 * No anonymous reports: the name and the proved address are the price of a
 * report reaching two officers' inboxes from an open page.
 */
"use client";

import * as React from "react";

import { FormError, useApiForm } from "@/components/forms";
import { Alert, Button, Field, Input, Textarea } from "@/components/ui/primitives";
import { nowLocal } from "@/lib/dates";
import {
  requestReportCode,
  submitIncidentReport,
  type CyberAttackAnswer,
  type IncidentReportReceipt,
} from "@/features/report-incident/api";
import {
  reportSchema,
  type ReportForm as ReportFormValues,
  type ReportValues,
} from "@/features/report-incident/schemas";

const EMPTY: ReportFormValues = {
  name: "",
  email: "",
  title: "",
  incident_details: "",
  noticed_at: "",
  origin: "",
  discovery: "",
  affected_systems: "",
  impact_scale: "",
  countries_involved: "",
  data_nature: "",
  subject_types: "",
  entities_involved: "",
  third_parties: "",
  cyber_attack: "",
  code: "",
};

/** The questions that may be left, in the order the office asks them. */
const MORE_DETAILS = [
  {
    key: "origin",
    label: "Where it started",
    hint: "The system, team, vendor or place it began in, if you know.",
  },
  { key: "discovery", label: "How it was found", hint: "Who noticed it, where and how." },
  {
    key: "affected_systems",
    label: "Systems affected",
    hint: "Applications, databases, servers, networks or devices involved.",
  },
  {
    key: "impact_scale",
    label: "How much is affected",
    hint: "Records, people or files involved. An estimate is fine.",
  },
  {
    key: "countries_involved",
    label: "Countries involved",
    hint: "Where the data was held or went, if it crossed a border.",
  },
  {
    key: "data_nature",
    label: "Kinds of personal data",
    hint: "For example names and contact details, or health, financial or biometric data.",
  },
  {
    key: "subject_types",
    label: "Whose data",
    hint: "For example customers, employees or study participants.",
  },
  {
    key: "entities_involved",
    label: "Our entities involved or affected",
    hint: "Which of our companies, institutes or offices.",
  },
  {
    key: "third_parties",
    label: "Third parties involved",
    hint: "Vendors, service providers or partners.",
  },
] as const;

const CYBER_ATTACK: { value: CyberAttackAnswer; label: string }[] = [
  { value: "yes", label: "Yes" },
  { value: "no", label: "No" },
  { value: "unknown", label: "Not sure" },
];

export function ReportForm({ onDone }: { onDone: (receipt: IncidentReportReceipt) => void }) {
  const [pending, setPending] = React.useState(false);
  const [sentTo, setSentTo] = React.useState<string | null>(null);
  const [notice, setNotice] = React.useState<string | null>(null);
  const [expanded, setExpanded] = React.useState(false);
  const cyberLabel = React.useId();
  const banner = React.useRef<HTMLDivElement>(null);
  const form = useApiForm<ReportValues, ReportFormValues>(reportSchema, EMPTY);
  const { errors } = form.formState;
  const { setFocus, setValue, clearErrors } = form;

  const address = form.watch("email").trim().toLowerCase();
  const awaitingCode = sentTo !== null && sentTo === address;
  // An error nobody can see is no error: a complaint about a folded field unfolds it.
  const showMore = expanded || MORE_DETAILS.some((f) => errors[f.key]);

  // The code box arrives at the foot of a long form, out of sight on a phone.
  React.useEffect(() => {
    if (awaitingCode) setFocus("code");
  }, [awaitingCode, setFocus]);

  // A box that has gone keeps its value, and would fail a press with no word
  // on the page: a code is for the address it went to, so it goes with it.
  React.useEffect(() => {
    if (awaitingCode) return;
    setValue("code", "");
    clearErrors("code");
  }, [awaitingCode, setValue, clearErrors]);

  // Arriving above the buttons it pushes them down, and can land past the fold.
  React.useEffect(() => {
    if (form.formError) banner.current?.scrollIntoView({ block: "center" });
  }, [form.formError]);

  const sendCode = form.submit(async (values) => {
    setPending(true);
    try {
      const sent = await requestReportCode(values.email);
      setNotice(awaitingCode ? "We have sent a new code. Use that one." : (sent.message ?? null));
      setSentTo(values.email);
    } finally {
      setPending(false);
    }
  });

  const sendReport = form.submit(async (values) => {
    if (!values.code) {
      form.setError("code", { message: "Enter the code we sent you." });
      return;
    }
    setPending(true);
    try {
      onDone(await submitIncidentReport(values));
    } finally {
      setPending(false);
    }
  });

  /** Whatever is in the code box was for the old code, and must not stop a new one. */
  function resend(event: React.MouseEvent) {
    form.setValue("code", "");
    form.clearErrors("code");
    sendCode(event);
  }

  return (
    <form method="post" onSubmit={awaitingCode ? sendReport : sendCode} noValidate className="space-y-4">
      <Field label="Your name" required error={errors.name?.message}>
        {(p) => <Input {...p} autoComplete="name" maxLength={200} {...form.register("name")} />}
      </Field>

      <Field
        label="Your email"
        hint="We send a code here to confirm it is yours, and your reference once the report is in."
        required
        error={errors.email?.message}
      >
        {(p) => (
          <Input
            {...p}
            type="email"
            inputMode="email"
            autoComplete="email"
            maxLength={255}
            {...form.register("email")}
          />
        )}
      </Field>

      <Field label="What happened in one line" required error={errors.title?.message}>
        {(p) => <Input {...p} autoComplete="off" maxLength={300} {...form.register("title")} />}
      </Field>

      <Field
        label="What happened"
        hint="As much as you know. Please leave out passwords, and other people's details unless they are needed to explain it."
        required
        error={errors.incident_details?.message}
      >
        {(p) => <Textarea {...p} rows={5} maxLength={8000} {...form.register("incident_details")} />}
      </Field>

      <Field
        label="When did you notice it"
        hint="If you can say. An estimate is fine."
        error={errors.noticed_at?.message}
      >
        {(p) => <Input {...p} type="datetime-local" max={nowLocal()} {...form.register("noticed_at")} />}
      </Field>

      <details
        open={showMore}
        onToggle={(e) => setExpanded(e.currentTarget.open)}
        className="rounded-lg border border-border"
      >
        <summary className="cursor-pointer px-3 py-2.5 text-sm font-medium">
          More details (optional)
        </summary>
        <div className="space-y-4 border-t border-border p-3">
          <p className="text-xs text-text-muted">Answer what you can, and leave the rest.</p>
          {MORE_DETAILS.map((f) => (
            <Field key={f.key} label={f.label} hint={f.hint} error={errors[f.key]?.message}>
              {(p) => <Textarea {...p} rows={2} maxLength={8000} {...form.register(f.key)} />}
            </Field>
          ))}
          <div className="space-y-1.5">
            <p id={cyberLabel} className="text-sm font-medium">
              Is it a cyber attack?
            </p>
            <div role="radiogroup" aria-labelledby={cyberLabel} className="flex flex-wrap gap-4">
              {CYBER_ATTACK.map((o) => (
                <label key={o.value} className="flex items-center gap-2 text-sm">
                  <input
                    type="radio"
                    value={o.value}
                    className="size-4 accent-[var(--accent)]"
                    {...form.register("cyber_attack")}
                  />
                  {o.label}
                </label>
              ))}
            </div>
            <p className="text-xs text-text-subtle">
              For example hacking, malicious software or a phishing email.
            </p>
          </div>
        </div>
      </details>

      {awaitingCode && (
        <>
          {notice && <Alert tone="info">{notice}</Alert>}
          <Field
            label="The code we sent"
            hint={`Six digits, sent to ${sentTo}. It expires in ten minutes.`}
            required
            error={errors.code?.message}
          >
            {(p) => (
              <Input
                {...p}
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={10}
                {...form.register("code")}
              />
            )}
          </Field>
        </>
      )}

      {form.formError && (
        <div ref={banner}>
          <FormError message={form.formError} />
        </div>
      )}

      {awaitingCode ? (
        <div className="flex flex-wrap gap-2">
          <Button type="submit" variant="primary" loading={pending}>
            Send the report
          </Button>
          <Button type="button" variant="ghost" disabled={pending} onClick={resend}>
            Send a new code
          </Button>
        </div>
      ) : (
        <Button type="submit" variant="primary" loading={pending}>
          Send me a code
        </Button>
      )}
    </form>
  );
}
