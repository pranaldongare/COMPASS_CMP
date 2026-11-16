/**
 * DataVault (0070, 0071): the store the labs' assets live in.
 *
 * Each thin: where DataVault is reached (the administrator's page), what it
 * holds of a rights request's person (the DPO's or Legal's "Check in
 * DataVault"), on an erasure request telling it to erase what it listed
 * ("Erase in DataVault", then "Check status"), and, on a DCO Admin's own
 * ticket, the assets it listed for their project. Consent changes have no
 * button: the server tells DataVault of them by itself, and the
 * administrator's page shows how that queue stands. The server makes every
 * call; the console never talks to DataVault and never holds its key.
 */
import { BACKGROUND, apiGet, apiPost, apiPut } from "@/lib/api";
import type { Timestamp, Uuid } from "@/types";

/** How a person, a consent and a project are named in every call. */
export type DataVaultIdFormat = "numeric" | "uuid";

export interface DataVaultConnection {
  /** Where the lookup goes. */
  base_url: string | null;
  /** Where erasures and consent changes go (0071). */
  erasure_url: string | null;
  /** Whether a key is stored. The key itself is never served. */
  api_key_set: boolean;
  api_key_header: string;
  enabled: boolean;
  id_format: DataVaultIdFormat;
  /** Whether DataVault is told of consent changes by itself. */
  consent_changes: boolean;
  /** How that queue stands: counts and times only. */
  consent_changes_waiting: number;
  consent_changes_last_delivered_at: Timestamp | null;
  /** Why the last try failed, in words. */
  consent_changes_last_failure: string | null;
  updated_at: Timestamp | null;
  updated_by_name: string | null;
}

export interface DataVaultConnectionInput {
  base_url: string | null;
  erasure_url: string | null;
  /** A new key; left out, the stored one stays. */
  api_key?: string;
  clear_api_key?: boolean;
  api_key_header: string;
  enabled: boolean;
  id_format: DataVaultIdFormat;
  consent_changes: boolean;
}

/** Where an asset stands in DataVault on an erasure request. `null`: not
 *  sent. `unanswered`: sent, and DataVault has not said. `pending`, or one of
 *  the final `erased`, `failed` and `not_held`. */
export type DataVaultErasureStatus =
  "unanswered" | "pending" | "erased" | "failed" | "not_held";

export interface DataVaultAsset {
  asset_ref: string;
  /** The consent and project as DataVault named them. */
  consent_ref: string | null;
  project_ref: string | null;
  /** Ours, where what DataVault named is one of this person's. */
  consent_uuid: Uuid | null;
  consent_no: number | null;
  project_uuid: Uuid | null;
  project_no: number | null;
  project_name: string | null;
  mid: string | null;
  datapath: string | null;
  /** On an erasure request: whether the request reaches this asset - one
   *  confined to a consent reaches that consent's assets only. Always true on
   *  any other. */
  in_scope: boolean;
  erasure_status: DataVaultErasureStatus | null;
  erasure_status_at: Timestamp | null;
  erasure_completed_at: Timestamp | null;
  /** Why DataVault did not erase it, in its words. */
  erasure_reason: string | null;
}

/** What may be done about erasing in DataVault now, on an erasure request. */
export interface DataVaultErasure {
  /** This reader may press "Erase in DataVault" now; else why not, in words. */
  may_erase: boolean;
  why_not: string | null;
  /** How many assets a press would send, and how many the check listed that
   *  this request does not reach. */
  to_send: number;
  left_out: number;
  /** Assets DataVault has not said the last word on. */
  open: number;
  may_check_status: boolean;
  counts: Record<DataVaultErasureStatus, number>;
  last_asked_at: Timestamp | null;
  last_failure: string | null;
  last_failure_said: string | null;
}

export interface DataVaultCheck {
  check_uuid: Uuid;
  asked_at: Timestamp;
  automatic: boolean;
  asked_by_name: string | null;
  outcome: "answered" | "failed";
  failure: string | null;
  failure_said: string | null;
  asset_count: number;
}

export interface RequestDataVault {
  configured: boolean;
  may_check: boolean;
  why_not: string | null;
  answer: DataVaultCheck | null;
  assets: DataVaultAsset[];
  last_failure: DataVaultCheck | null;
  /** On an erasure request (0071); null on any other. */
  erasure: DataVaultErasure | null;
}

export interface TicketDataVault {
  asked_at: Timestamp | null;
  assets: DataVaultAsset[];
}

export const datavaultKeys = {
  connection: ["datavault", "connection"] as const,
  /** Under the request's own key (`keys.rights.detail`), as its trail is: every
   *  act on the request - starting it, finding holders - reads this again. */
  request: (uuid: Uuid) => ["request", uuid, "datavault"] as const,
  ticket: (uuid: Uuid) => ["datavault", "ticket", uuid] as const,
};

export function getConnection(): Promise<DataVaultConnection> {
  return apiGet<DataVaultConnection>("/datavault-connection");
}

export function saveConnection(
  body: DataVaultConnectionInput,
): Promise<DataVaultConnection> {
  return apiPut<DataVaultConnection>("/datavault-connection", body);
}

/** `background`: the page looking again by itself, which must not keep the
 *  session awake. */
export function getRequestDataVault(
  requestUuid: Uuid,
  background = false,
): Promise<RequestDataVault> {
  return apiGet<RequestDataVault>(
    `/requests/${requestUuid}/datavault`,
    background ? BACKGROUND : undefined,
  );
}

export function checkInDataVault(requestUuid: Uuid): Promise<RequestDataVault> {
  return apiPost<RequestDataVault>(`/requests/${requestUuid}/datavault/check`);
}

/** Tell DataVault to erase what its last check listed and this request
 *  reaches: what has not been sent yet, and what it failed to erase. */
export function eraseInDataVault(requestUuid: Uuid): Promise<RequestDataVault> {
  return apiPost<RequestDataVault>(`/requests/${requestUuid}/datavault/erase`);
}

/** Ask DataVault how far each asset it was told to erase has got: the same
 *  instruction again, which starts nothing new. */
export function checkErasureStatus(requestUuid: Uuid): Promise<RequestDataVault> {
  return apiPost<RequestDataVault>(`/requests/${requestUuid}/datavault/erase/status`);
}

export function getTicketDataVault(holderUuid: Uuid): Promise<TicketDataVault> {
  return apiGet<TicketDataVault>(`/tickets/${holderUuid}/datavault`);
}
