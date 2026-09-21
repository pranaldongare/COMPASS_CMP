/**
 * Registering, signing in with a one-time code, and one's own sessions.
 *
 * There is no password anywhere in this file: a data principal never has one.
 * Staff sign-in, with its password and second factor, lives on the staff
 * console.
 *
 * Two things about this module are deliberate and easy to undo by accident.
 *
 * **No response here says whether an account exists.** The API answers
 * identically for a wrong password and an unknown login, and for a code sent to
 * a registered contact and one that is not. Nothing in this file should start
 * distinguishing them in a return type or an error branch, because that puts
 * the distinction back into the client where an attacker can read it.
 *
 * **The session never appears in JavaScript.** It arrives as an HttpOnly
 * cookie, is sent by the browser, and is not readable here — which is why there
 * is no `getToken` and no place to put one.
 */

import { apiDelete, apiGet, apiPost } from "@/lib/api";
import type { Acknowledged, Me, SessionInfo, Uuid } from "@/types";

/* ------------------------------------------------------------- sign-up */

export interface RegistrationDetails {
  full_name: string;
  /** Required: her sign-in codes go here. */
  mobile: string;
  /** ISO date, YYYY-MM-DD. */
  dob: string;
  email?: string | null;
}

/** The second step of sign-up: a code for every contact given, checked together. */
export interface RegistrationVerification {
  mobile: string;
  mobile_code?: string | null;
  email_code?: string | null;
}

/**
 * Data-principal self-registration.
 *
 * Only this role can be created this way — the server writes the role itself
 * and there is no field here to carry one, which is what stops a public form
 * from minting staff accounts.
 *
 * A contact that already belongs to an active account is refused with
 * `contact_taken` and the field named, so the form can say which one to change
 * and offer sign-in with it. A product decision taken with its cost in view: it
 * lets a stranger test whether an address is registered here, and the server's
 * rate limits are what remain against that. A registration that was started
 * and never finished is not a conflict; its codes are sent again.
 */
export function register(body: RegistrationDetails): Promise<Acknowledged> {
  return apiPost<Acknowledged>("/auth/register", body);
}

export function registerVerify(body: RegistrationVerification): Promise<Acknowledged> {
  return apiPost<Acknowledged>("/auth/register/verify", body);
}

/* -------------------------------------------------------------- sign-in */

/** Ask for a one-time code. Answers the same way whether the contact is known. */
export function requestOtp(body: { contact: string }): Promise<Acknowledged> {
  return apiPost<Acknowledged>("/auth/otp/request", body);
}

export function verifyOtp(body: { contact: string; code: string }): Promise<Acknowledged> {
  return apiPost<Acknowledged>("/auth/otp/verify", body);
}

/* -------------------------------------------------------------- session */

/** Who the caller is, and what the server says they may reach. */
export function getMe(): Promise<Me> {
  return apiGet<Me>("/auth/me");
}

export function signOut(): Promise<Acknowledged> {
  return apiPost<Acknowledged>("/auth/logout");
}

export function listSessions(): Promise<SessionInfo[]> {
  return apiGet<SessionInfo[]>("/auth/sessions");
}

/** End one session — the one on the laptop somebody left on a train. */
export function revokeSession(uuid: Uuid): Promise<Acknowledged> {
  return apiDelete<Acknowledged>(`/auth/sessions/${uuid}`);
}
