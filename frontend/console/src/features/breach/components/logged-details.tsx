/**
 * What else is known when an incident is logged (0047, 2026-10-08).
 *
 * The Privacy Office's intake questions, every one optional: much is not
 * known in the first minutes, and the incident is logged anyway - its clocks
 * run from when it was first noticed. The answers are kept as logged; what is
 * learned later goes in the assessment. One question is a choice: a cyber
 * attack is reportable to CERT-In, and saying yes starts that duty at once.
 */
"use client";

import * as React from "react";

import { DescriptionItem, Field, Textarea } from "@/components/ui/primitives";
import type { BreachCyberAttack, BreachLogged } from "@/types";

/** The questions, in the order the office asks them. */
export const LOGGED_FIELDS: {
  key: keyof BreachLogged;
  label: string;
  hint: string;
  rows?: number;
}[] = [
  {
    key: "origin",
    label: "Where it started",
    hint: "The system, team, vendor or place it began in, if known.",
  },
  {
    key: "discovery",
    label: "How it was found",
    hint: "Who noticed it, where and how - a monitoring alert, a staff report, a complaint.",
  },
  {
    key: "affected_systems",
    label: "Systems affected",
    hint: "Applications, databases, servers, networks or devices involved.",
  },
  {
    key: "incident_details",
    label: "What happened",
    hint: "As much as is known now. Later findings go in the assessment.",
    rows: 4,
  },
  {
    key: "impact_scale",
    label: "How much is affected",
    hint: "Records, people or files involved - an estimate is fine.",
  },
  {
    key: "countries_involved",
    label: "Countries involved",
    hint: "Where the data was held or went, if it crossed a border.",
  },
  {
    key: "data_nature",
    label: "Kinds of personal data",
    hint: "E.g. names and contact details; or sensitive data such as health, financial or biometric.",
  },
  {
    key: "subject_types",
    label: "Whose data",
    hint: "E.g. study participants, employees, customers - if known.",
  },
  {
    key: "entities_involved",
    label: "Our entities involved or affected",
    hint: "Which of the organisation's own companies, institutes or offices.",
  },
  {
    key: "third_parties",
    label: "Third parties involved",
    hint: "Vendors, service providers, processors or partners.",
  },
];

export const CYBER_ATTACK: Record<BreachCyberAttack, string> = {
  yes: "Yes - reportable to CERT-In",
  no: "No",
  unknown: "Not known yet",
};

export function LoggedFields({
  value,
  onChange,
  cyber,
  onCyber,
}: {
  value: BreachLogged;
  onChange: (next: BreachLogged) => void;
  cyber: BreachCyberAttack | null;
  onCyber: (next: BreachCyberAttack | null) => void;
}) {
  return (
    <fieldset className="space-y-3 rounded-md border border-border p-3">
      <legend className="px-1 text-sm font-medium">What is known so far</legend>
      <p className="text-xs text-text-muted">
        All optional - answer what you can now. These are kept as logged; what is learned later
        goes in the assessment.
      </p>

      <div className="space-y-1.5">
        <p id="cyber-attack-label" className="text-sm font-medium">
          Is it a cyber attack?
        </p>
        <div role="radiogroup" aria-labelledby="cyber-attack-label" className="flex flex-wrap gap-4">
          {(Object.keys(CYBER_ATTACK) as BreachCyberAttack[]).map((k) => (
            <label key={k} className="flex items-center gap-2 text-sm">
              <input
                type="radio"
                name="cyber-attack"
                className="size-4 accent-[var(--accent)]"
                checked={cyber === k}
                onChange={() => onCyber(k)}
              />
              {CYBER_ATTACK[k]}
            </label>
          ))}
          {cyber !== null && (
            <button
              type="button"
              className="text-xs text-accent-text underline underline-offset-2"
              onClick={() => onCyber(null)}
            >
              Clear
            </button>
          )}
        </div>
        <p className="text-xs text-text-subtle">
          Yes starts the CERT-In duty: six hours from when it was first noticed.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {LOGGED_FIELDS.map((f) => (
          <div key={f.key} className={f.rows ? "sm:col-span-2" : undefined}>
            <Field label={f.label} hint={f.hint}>
              {(p) => (
                <Textarea
                  {...p}
                  rows={f.rows ?? 2}
                  maxLength={8000}
                  value={value[f.key] ?? ""}
                  onChange={(e) => onChange({ ...value, [f.key]: e.target.value })}
                />
              )}
            </Field>
          </div>
        ))}
      </div>
    </fieldset>
  );
}

/** The answers as logged, for the breach's details. Only what was said. */
export function LoggedDetails({
  logged,
  cyber,
}: {
  logged: BreachLogged | undefined;
  cyber: BreachCyberAttack | null | undefined;
}) {
  return (
    <>
      {cyber && <DescriptionItem term="Cyber attack">{CYBER_ATTACK[cyber]}</DescriptionItem>}
      {LOGGED_FIELDS.filter((f) => logged?.[f.key]).map((f) => (
        <DescriptionItem key={f.key} term={f.label}>
          <span className="whitespace-pre-wrap">{logged?.[f.key]}</span>
        </DescriptionItem>
      ))}
    </>
  );
}
