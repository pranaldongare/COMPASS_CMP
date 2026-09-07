/**
 * What a valid sign-in and profile edit look like.
 *
 * The sign-in schema is the loosest in the codebase, and that is correct. A
 * credential form must not tell an unauthenticated visitor anything about the
 * account they are guessing at — refusing "that is not a valid email address"
 * before the request is sent confirms which strings are *shaped* like accounts
 * here. So it checks only that a field is filled. The server decides everything
 * else, and answers the same way whether the account exists or not.
 */

import { z } from "zod";

import { contact, mobile } from "@/schemas/contacts";
import { optional, shortText } from "@/schemas/primitives";
import { otpCode } from "@/schemas/security";

/** Data subject sign-in: a one-time code to an email or mobile. */
export const otpRequestSchema = z.object({
  contact,
});

export type OtpRequestValues = z.infer<typeof otpRequestSchema>;

/**
 * The code itself.
 *
 * `otpCode` rather than a bare string: the digits-only rule opens a numeric
 * keyboard on a phone, which is worth the small risk of being marginally
 * stricter than the server.
 */
export const otpVerifySchema = z.object({
  code: otpCode,
});

export type OtpVerifyValues = z.infer<typeof otpVerifySchema>;

/** The signed-in user editing their own profile. */
export const profileSchema = z.object({
  full_name: shortText("Your name"),
  mobile: optional(mobile),
});

export type ProfileValues = z.infer<typeof profileSchema>;

/**
 * Declaring whether one is a minor, or acting for one.
 *
 * s.9 turns on this answer, so the reason field exists to record *why* somebody
 * changed it — a guardian taking over an account, a subject turning eighteen.
 */
export const personTypeSchema = z.object({
  person_type: z.string().min(1, "Choose how you are acting"),
  reason: optional(z.string().trim().max(500, "Keep the reason under 500 characters")),
});

export type PersonTypeValues = z.infer<typeof personTypeSchema>;
