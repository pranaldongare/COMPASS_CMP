/**
 * The address links to the data principal's portal start with (0072).
 *
 * The administrator keeps it on the Portal address page. Until one is set the
 * API's configured address is used. Everybody signed in is told the address in
 * use by `GET /auth/me` (`portal_url`); `portalUrl()` is that value, and is
 * what goes in front of a consent link's path when the link is shown or
 * copied (`consentLinkUrl`). Before anybody is signed in - the sign-in page's
 * link to the portal - only the build's own setting is known.
 */
import { apiGet, apiPut } from "@/lib/api";
import { config } from "@/lib/config";
import type { Timestamp } from "@/types/primitives";

export interface PortalAddress {
  /** What the administrator set. Null: the configured address is used. */
  portal_url: string | null;
  /** The API's configured address (`PUBLIC_BASE_URL`). */
  configured_url: string;
  /** What links start with now. */
  in_use: string;
  updated_at: Timestamp | null;
  /** Sealed; opened by the API client. */
  updated_by_name: string | null;
}

export const portalAddressKey = ["portal-address"] as const;

export function getPortalAddress(): Promise<PortalAddress> {
  return apiGet<PortalAddress>("/portal-address");
}

export function savePortalAddress(portal_url: string | null): Promise<PortalAddress> {
  return apiPut<PortalAddress>("/portal-address", { portal_url });
}

/** The address the server last told this tab, if it has. */
let told: string | null = null;

/** Called with what `GET /auth/me` said, and by the page after a save. */
export function setPortalUrl(url: string | null | undefined): void {
  told = url ? url.replace(/\/+$/, "") : null;
}

/** The portal's address, with no trailing slash. */
export function portalUrl(): string {
  return told ?? config.subjectPortalUrl.replace(/\/+$/, "");
}

/**
 * What must be true of an address before it is sent: http or https, a host,
 * perhaps a port, and nothing after it. The server checks the same.
 */
export function isPortalAddress(value: string): boolean {
  return /^https?:\/\/[^/?#@\s]+\/?$/.test(value.trim());
}
