/**
 * A breach notice by its link, for somebody with no account (2026-11-20).
 *
 * A person a breach affected who has no account is sent a text with a link to
 * `/breach-notice/{token}`. The link alone shows the breach's reference and,
 * masked, the mobile a code will go to; the code, sent by text to the number
 * on the breach's list, opens the notice. Every way a link can fail is the
 * same 404.
 *
 * Nothing here stores anything: the notice and the code live in the page's
 * memory and are gone when it closes. Types are written by hand from the
 * API's `BreachNoticeLinkOut` and `BreachNoticeByLinkOut`, as the outside
 * holder's ticket does (`features/holder-ticket/api.ts`).
 */
import { apiGet, apiPost } from "@/lib/api";
import { isEncrypted } from "@/lib/dkms";
import type { Acknowledged } from "@/types";

/** What the link alone shows. */
export interface BreachNoticeLink {
  reference: string;
  /** The mobile the code goes to, masked. */
  code_goes_to: string;
}

/** The notice, in full: the five things Rule 7(1) requires. */
export interface BreachNoticeByLink {
  reference: string;
  version: number;
  approved_at: string | null;
  what_happened: string;
  consequences: string;
  measures: string;
  protective_steps: string;
  contact: string;
}

/** The five things the notice says, in the Rule's order, with the headings
 *  her account's notices use. */
export const NOTICE_SECTIONS: ReadonlyArray<{
  key: keyof Pick<
    BreachNoticeByLink,
    "what_happened" | "consequences" | "measures" | "protective_steps" | "contact"
  >;
  heading: string;
}> = [
  { key: "what_happened", heading: "What happened" },
  { key: "consequences", heading: "What it may mean for you" },
  { key: "measures", heading: "What we have done, and are doing" },
  { key: "protective_steps", heading: "What you can do" },
  { key: "contact", heading: "Questions" },
];

/** The token's shape, as the API checks it: anything else is not a link. */
export const isNoticeToken = (token: string) => /^[A-Za-z0-9_-]{64}$/.test(token);

const base = (token: string) => `/breach-notices/${encodeURIComponent(token)}`;

export const getNoticeLink = (token: string) => apiGet<BreachNoticeLink>(base(token));

export const sendNoticeCode = (token: string) =>
  apiPost<Acknowledged>(`${base(token)}/code`, {});

export const openNotice = (token: string, code: string) =>
  apiPost<BreachNoticeByLink>(`${base(token)}/open`, { code });

/**
 * Whether any of the five came back still sealed (`SE::…`). The API client
 * opens sealed values on every response; one it could not open is left as it
 * arrived, and a notice that reads as base64 must not be shown as if it were
 * the notice.
 */
export const stillSealed = (notice: BreachNoticeByLink) =>
  NOTICE_SECTIONS.some((s) => isEncrypted(notice[s.key]));
