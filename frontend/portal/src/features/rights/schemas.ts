/**
 * The forms a rights request passes through, as zod schemas.
 *
 * Fast feedback only. The API validates independently and its answer wins -
 * see `useApiForm`. What these pin down is the shape: which right is being
 * asked for, that a request says something, that a contact is a contact.
 */

import { z } from "zod";

import { email, mobile } from "@/schemas/contacts";
import { optional } from "@/schemas/primitives";
import { RIGHTS_REQUEST_TYPES } from "@/types";

export const requestTypeSchema = z.enum(RIGHTS_REQUEST_TYPES);

const requestText = z
  .string()
  .trim()
  .min(10, "Say what you are asking for, in a sentence or two.")
  .max(20_000, "That is longer than we can accept in one request.");

/** A signed-in data principal asking from her dashboard. */
export const myRequestSchema = z.object({
  request_type: requestTypeSchema,
  request_text: requestText,
  about_dpo: z.boolean().default(false),
  /** One of her consents to confine the request to; null is everything. */
  consent_uuid: z.string().nullable().default(null),
});
export type MyRequestForm = z.input<typeof myRequestSchema>;
export type MyRequestValues = z.output<typeof myRequestSchema>;

/** The public form, from the notice link. */
export const publicRequestSchema = z.object({
  request_type: requestTypeSchema,
  contact: z
    .string()
    .trim()
    .min(3, "The email or mobile you registered with.")
    .max(255),
  name: z.string().trim().max(200).optional(),
  request_text: requestText,
});
export type PublicRequestForm = z.input<typeof publicRequestSchema>;
export type PublicRequestValues = z.output<typeof publicRequestSchema>;

export const verifySchema = z.object({
  reference: z
    .string()
    .trim()
    .toUpperCase()
    .regex(/^RR-\d{4}-\d{6}$/, "A reference looks like RR-2026-000123."),
  code: z.string().trim().regex(/^\d{4,10}$/, "The code is digits only."),
});
export type VerifyForm = z.input<typeof verifySchema>;
export type VerifyValues = z.output<typeof verifySchema>;

export const nominationSchema = z.object({
  nominee_name: z.string().trim().min(2, "The nominee's name.").max(200),
  nominee_mobile: mobile,
  nominee_email: optional(email),
  rights: z
    .array(requestTypeSchema)
    .min(1, "Choose at least one right the nominee may exercise."),
});
export type NominationForm = z.input<typeof nominationSchema>;
export type NominationValues = z.output<typeof nominationSchema>;

export const disputeSchema = z.object({
  text: requestText,
  about_dpo: z.boolean().default(false),
});
export type DisputeForm = z.input<typeof disputeSchema>;
export type DisputeValues = z.output<typeof disputeSchema>;
