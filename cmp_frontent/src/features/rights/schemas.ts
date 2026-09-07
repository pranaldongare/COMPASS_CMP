/**
 * The form a rights request passes through on the staff console, as a zod
 * schema.
 *
 * Fast feedback only. The API validates independently and its answer wins -
 * see `useApiForm`. What this pins down is the shape: which right is being
 * asked for, that a request says something, that a contact is a contact.
 */

import { z } from "zod";

import { RIGHTS_REQUEST_TYPES } from "@/types";

export const requestTypeSchema = z.enum(RIGHTS_REQUEST_TYPES);

const requestText = z
  .string()
  .trim()
  .min(10, "Say what you are asking for, in a sentence or two.")
  .max(20_000, "That is longer than we can accept in one request.");

/** The DPO logging a request that arrived by email. */
export const logRequestSchema = z.object({
  request_type: requestTypeSchema,
  contact: z.string().trim().min(3).max(255),
  name: z.string().trim().max(200).optional(),
  request_text: requestText,
  about_dpo: z.boolean().default(false),
});
export type LogRequestForm = z.input<typeof logRequestSchema>;
export type LogRequestValues = z.output<typeof logRequestSchema>;
