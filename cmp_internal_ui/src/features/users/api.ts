/**
 * Every request the users feature makes.
 *
 * No password ever travels through here. A staff account is created without
 * one and the holder sets it through an emailed single-use link, so no
 * administrator learns a colleague's password and none is ever posted from this
 * console.
 */

import { apiGet, apiPatch, apiPost, http, queryString } from "@/lib/api";
import type { StaffMember, Acknowledged, Page, User, Uuid } from "@/types";

export function listUsers(filters: Record<string, unknown> = {}): Promise<Page<User>> {
  return apiGet<Page<User>>(`/users${queryString(filters)}`);
}

export interface UserInput {
  full_name: string;
  email: string;
  role: string;
  username?: string | null;
  mobile?: string | null;
  organization_id?: string | null;
  person_type?: string | null;
  /** Data sources this person becomes accountable for, assigned as part of
   *  creating them. Only meaningful for a DCO or an RCO — the server refuses it
   *  for any other role rather than ignoring it. */
  source_uuids?: string[];
}

export function createUser(body: UserInput): Promise<User> {
  return apiPost<User>("/users", body);
}

export function updateUser(uuid: Uuid, body: Partial<UserInput>): Promise<User> {
  return apiPatch<User>(`/users/${uuid}`, body);
}

export function changeUserRole(
  uuid: Uuid,
  body: { role: string; reason?: string },
): Promise<Acknowledged> {
  return apiPost<Acknowledged>(`/users/${uuid}/role`, body);
}

/** Deactivated, never deleted: the audit trail refers to this account. */
export function deactivateUser(uuid: Uuid): Promise<Acknowledged> {
  return apiPost<Acknowledged>(`/users/${uuid}/deactivate`);
}

export function reactivateUser(uuid: Uuid): Promise<Acknowledged> {
  return apiPost<Acknowledged>(`/users/${uuid}/reactivate`);
}

/**
 * Write to somebody again about the account waiting for them.
 *
 * The invitation is sent when the account is created, but it is dispatched as a
 * side effect of a write that has already succeeded - so a broker that was down
 * for a moment loses the message and nothing else. Only the person waiting for
 * it would ever know, which is why an administrator can send it again.
 *
 * Refused once the account is active: its owner has a password by then, and
 * "Forgotten your password?" is theirs to use.
 */
export function resendInvitation(uuid: Uuid): Promise<Acknowledged> {
  return apiPost<Acknowledged>(`/users/${uuid}/invite`);
}

/** Clears the enrolled factor so the user can enrol a new device. */
export function resetMfa(uuid: Uuid): Promise<Acknowledged> {
  return apiPost<Acknowledged>(`/users/${uuid}/mfa/reset`);
}

/** Ends every session this user holds. The response to a lost laptop. */
export async function forceLogout(uuid: Uuid): Promise<Acknowledged> {
  const { data } = await http.delete<Acknowledged>(`/users/${uuid}/sessions`);
  return data;
}

/** Active staff, four fields, for naming a processor's respondent. DPO and admin only. */
export function listStaff(): Promise<StaffMember[]> {
  return apiGet<StaffMember[]>("/users/staff");
}
