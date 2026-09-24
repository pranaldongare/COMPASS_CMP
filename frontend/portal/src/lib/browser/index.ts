/**
 * Browser features that only exist in a *secure context*, with the fallback
 * each needs so a page works however it was opened.
 *
 * `https://…` and `http://localhost` are secure contexts. `http://<ip>:3000`
 * - the portal opened from another machine on the network, or by IP from
 * this one - is not, and there the browser simply leaves out
 * `crypto.randomUUID`, `crypto.subtle` and `navigator.clipboard`. Code that
 * reaches for them throws a TypeError. The toast shown when a save
 * succeeds took its id from `crypto.randomUUID`, so over plain http every
 * successful save threw *while saying it had succeeded*: the server had the
 * change, and the page reported a failure.
 *
 * Nothing in the app calls those three directly; it calls these.
 */

/**
 * A random id for things that live in the page - a toast, a list key.
 *
 * `crypto.getRandomValues` is available in every context, secure or not,
 * and is enough for an id nobody needs to be unguessable.
 */
export function uid(): string {
  const c = globalThis.crypto;
  if (c && typeof c.randomUUID === "function") return c.randomUUID();
  if (c && typeof c.getRandomValues === "function") {
    const bytes = c.getRandomValues(new Uint8Array(16));
    return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  }
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2)}`;
}

/**
 * Put text on the clipboard. Resolves `true` when it got there.
 *
 * `navigator.clipboard` where the browser offers it; otherwise the older
 * route every browser still supports - select the text in a hidden field
 * and ask for a copy. Never throws: a copy that did not happen is reported,
 * so the button can say so, rather than failing the page around it.
 */
export async function copyText(text: string): Promise<boolean> {
  try {
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // Refused - permission, or a focus rule. The fallback below may still work.
  }
  if (typeof document === "undefined") return false;
  const field = document.createElement("textarea");
  field.value = text;
  field.setAttribute("readonly", "");
  field.style.position = "fixed";
  field.style.opacity = "0";
  document.body.appendChild(field);
  field.select();
  try {
    return document.execCommand("copy");
  } catch {
    return false;
  } finally {
    field.remove();
  }
}
