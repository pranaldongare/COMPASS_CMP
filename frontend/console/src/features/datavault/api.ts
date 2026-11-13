/**
 * DataVault (0070): the store the labs' assets live in.
 *
 * Three things, each thin: where DataVault is reached (the administrator's
 * page), what it holds of a rights request's person (the DPO's or Legal's
 * "Check in DataVault"), and, on a DCO Admin's own ticket, the assets it
 * listed for their project. The server makes the call; the console never
 * talks to DataVault and never holds its key.
 */
import { BACKGROUND, apiGet, apiPost, apiPut } from "@/lib/api";
import type { Timestamp, Uuid } from "@/types";

export interface DataVaultConnection {
  base_url: string | null;
  /** Whether a key is stored. The key itself is never served. */
  api_key_set: boolean;
  api_key_header: string;
  enabled: boolean;
  updated_at: Timestamp | null;
  updated_by_name: string | null;
}

export interface DataVaultConnectionInput {
  base_url: string | null;
  /** A new key; left out, the stored one stays. */
  api_key?: string;
  clear_api_key?: boolean;
  api_key_header: string;
  enabled: boolean;
}

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

export function getTicketDataVault(holderUuid: Uuid): Promise<TicketDataVault> {
  return apiGet<TicketDataVault>(`/tickets/${holderUuid}/datavault`);
}
