/**
 * The signed-in user acting on their own account.
 *
 * Everything here is scoped to the caller by the server — there is no uuid
 * parameter anywhere in this file, which is what makes that true rather than
 * merely intended.
 */

import { apiGet, apiPatch, apiPost, http } from "@/lib/api";
import type { Acknowledged, MeProfile, SessionInfo } from "@/types";

/** Every session this account holds, so somebody can spot one they don't recognise. */
export function listMySessions(): Promise<SessionInfo[]> {
  return apiGet<SessionInfo[]>("/auth/sessions");
}

export interface UpdateMeInput {
  full_name?: string;
  /** A new or changed number is sent a code in the same request and cannot
   *  sign her in until it comes back. */
  mobile?: string;
  /** Set or replace the second address; the code goes out with the request. */
  secondary_email?: string;
  dob?: string;
}

/**
 * Save part of the record, and read back what the server decided.
 *
 * The reply is the row as it now stands, which is how the account page
 * knows whether a code went out: a contact that comes back unconfirmed was
 * sent one. Guessing from what was typed got this wrong in the one case
 * that matters most - re-saving a number already on the account.
 */
export function updateMe(body: UpdateMeInput): Promise<MeProfile> {
  return apiPatch<MeProfile>("/me", body);
}

/**
 * A code to one of her own contacts, for confirming it.
 *
 * The server refuses a contact that is not on her account, so this cannot be
 * turned into a way of sending codes to a stranger.
 */
export function requestContactCode(contact: string): Promise<Acknowledged> {
  return apiPost<Acknowledged>("/me/contacts/code", { contact });
}

/** The code came back: the contact is hers, and may now sign her in. */
export function verifyContact(body: {
  contact: string;
  code: string;
}): Promise<Acknowledged> {
  return apiPost<Acknowledged>("/me/contact/verify", body);
}

export async function removeSecondaryEmail(): Promise<Acknowledged> {
  const { data } = await http.delete<Acknowledged>("/me/secondary-email");
  return data;
}

/**
 * Declare whether one is a minor, or acting for one.
 *
 * s.9 turns on this answer, so the change is recorded with a reason rather than
 * silently overwritten — a guardian taking over an account and a subject
 * turning eighteen are different events and the trail should say which.
 */
export function setPersonType(body: {
  person_type: string;
  reason?: string;
}): Promise<Acknowledged> {
  return apiPost<Acknowledged>("/me/person-type", body);
}
