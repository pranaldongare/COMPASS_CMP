/**
 * A contact handed from one sign-in page to the other outside the URL
 * (review SEC-6).
 *
 * Sign-in and a consent link send somebody with no account to `/sign-up` with
 * what they typed filled in (ADR 0040, decision 2); sign-up sends somebody
 * whose contact is already registered, or who has finished, to `/sign-in`
 * with it filled in. In the query string a mobile or an email would stay in
 * the browser's history, in the server's and any proxy's request logs, and in
 * a `Referer`. So it goes through this tab's sessionStorage instead, under a
 * key per page it is for: written just before the navigation, read once by
 * that page and removed at once, and ignored when older than a few minutes.
 *
 * Storage can be blocked (a private window, a policy) or throw. Then nothing
 * is handed over and the field is simply empty: it only ever populates a form
 * field, it authorises nothing.
 */

import * as React from "react";

/** The page a contact is handed to. */
export type HandoverPage = "sign-up" | "sign-in";

const KEYS: Record<HandoverPage, string> = {
  "sign-up": "cmp.signUp.contact",
  "sign-in": "cmp.signIn.contact",
};
/** Long enough for one navigation, short enough not to linger in the tab. */
const TTL_MS = 5 * 60 * 1000;

/**
 * What the current visit to each page took, so every render of it sees the
 * same value although storage was emptied by the first read. Forgotten when
 * the page is left, and by the next handover to it.
 */
const taken: Partial<Record<HandoverPage, string>> = {};
const forgetting: Partial<Record<HandoverPage, ReturnType<typeof setTimeout>>> = {};

/** Keep `contact` for the page this tab is about to open. */
export function handOverContact(contact: string, to: HandoverPage): void {
  const value = contact.trim().slice(0, 254);
  delete taken[to];
  if (!value) return;
  try {
    window.sessionStorage.setItem(
      KEYS[to],
      JSON.stringify({ contact: value, at: Date.now() }),
    );
  } catch {
    // Blocked storage: the page opens with the field empty.
  }
}

/** The contact handed over, once: it is removed as it is read. `""` when there
 *  is none, it has expired, or storage cannot be read. */
export function takeHandedOverContact(to: HandoverPage): string {
  try {
    const raw = window.sessionStorage.getItem(KEYS[to]);
    if (raw === null) return "";
    window.sessionStorage.removeItem(KEYS[to]);
    const parsed: unknown = JSON.parse(raw);
    if (
      typeof parsed === "object" &&
      parsed !== null &&
      typeof (parsed as { contact?: unknown }).contact === "string" &&
      typeof (parsed as { at?: unknown }).at === "number"
    ) {
      const { contact, at } = parsed as { contact: string; at: number };
      const age = Date.now() - at;
      if (age >= 0 && age <= TTL_MS) return contact.trim().slice(0, 254);
    }
    return "";
  } catch {
    return "";
  }
}

function snapshot(to: HandoverPage): string {
  if (taken[to] === undefined) taken[to] = takeHandedOverContact(to);
  return taken[to];
}

const never = () => () => {};

/**
 * The contact handed to page `to`. `""` on the server and in the render that
 * hydrates (the server has no storage), then the value; `""` too when
 * `sentHere` is false, and storage is then left alone.
 */
export function useHandedOverContact(to: HandoverPage, sentHere: boolean): string {
  React.useEffect(() => {
    clearTimeout(forgetting[to]);
    // Forgotten a moment after unmounting, not at once: Strict Mode unmounts
    // and mounts again straight away, and that is not leaving the page. A
    // later visit (back, or a link) then finds nothing (review SEC-6).
    return () => {
      forgetting[to] = setTimeout(() => {
        delete taken[to];
      }, 0);
    };
  }, [to]);
  return React.useSyncExternalStore(
    never,
    () => (sentHere ? snapshot(to) : ""),
    () => "",
  );
}
