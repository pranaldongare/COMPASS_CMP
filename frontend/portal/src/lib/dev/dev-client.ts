/**
 * Development only: which browser tab this is, for the one-time-code popup.
 *
 * Every open portal and console polls the API for codes it has sent. Without
 * a way to tell them apart, a code asked for on one screen popped up on every
 * screen on every machine. Each tab now names itself on its API calls; the API
 * keeps that name with any code the call causes - through the worker that
 * sends it - and hands a tab only its own codes.
 *
 * sessionStorage, so the name is per tab and survives a reload in it. Sent
 * only while `NEXT_PUBLIC_DEV_SHOW_CODES=true`; the API ignores it otherwise.
 */

export const DEV_CODES_ON = process.env.NEXT_PUBLIC_DEV_SHOW_CODES === "true";
export const DEV_CLIENT_HEADER = "X-CMP-Dev-Client";

const KEY = "cmp.devClient";
let fallback: string | null = null;

function fresh(): string {
  const bytes = new Uint8Array(12);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

/** This tab's name, made on first use; null on the server. */
export function devClientId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    let id = window.sessionStorage.getItem(KEY);
    if (!id || !/^[A-Za-z0-9_-]{8,64}$/.test(id)) {
      id = fresh();
      window.sessionStorage.setItem(KEY, id);
    }
    return id;
  } catch {
    // Storage blocked: still one name for as long as this page lives.
    fallback ??= fresh();
    return fallback;
  }
}
