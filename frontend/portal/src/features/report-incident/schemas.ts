/**
 * The public incident form, as a zod schema.
 *
 * Fast feedback only, as everywhere: the API validates independently and its
 * answer wins. The limits are `IncidentReportIn`'s. Four things are asked for;
 * everything else may be left, and what is left goes as null.
 *
 * `code` is empty until one has been sent, so one schema serves both presses
 * of the form's button. `ReportForm` asks for it on the second.
 */

import { z } from "zod";

import { email } from "@/schemas/contacts";
import { dateTimeLocal, optional } from "@/schemas/primitives";

const CYBER_ATTACK_ANSWERS = ["yes", "no", "unknown"] as const;

const told = optional(z.string().trim().max(8000, "That is longer than we can accept here."));

export const reportSchema = z.object({
  name: z.string().trim().min(1, "Give your name.").max(200, "That name is too long."),
  email,
  title: z
    .string()
    .trim()
    .min(1, "Say in a line what happened.")
    .max(300, "That is longer than one line. The rest belongs in the box below."),
  incident_details: z
    .string()
    .trim()
    .min(1, "Say what happened.")
    .max(8000, "That is longer than we can accept here."),
  // The browser's zone is the person's: `new Date` reads the box in it, and the
  // API takes only a time that says its offset.
  noticed_at: optional(
    dateTimeLocal("The time").refine(
      (value) => new Date(value).getTime() <= Date.now(),
      "This time is in the future.",
    ),
  ).transform((value) => (value ? new Date(value).toISOString() : null)),
  origin: told,
  discovery: told,
  affected_systems: told,
  impact_scale: told,
  countries_involved: told,
  data_nature: told,
  subject_types: told,
  entities_involved: told,
  third_parties: told,
  cyber_attack: optional(z.enum(CYBER_ATTACK_ANSWERS)),
  code: z.string().trim().regex(/^\d{0,10}$/, "The code is digits only."),
});
export type ReportForm = z.input<typeof reportSchema>;
export type ReportValues = z.output<typeof reportSchema>;
