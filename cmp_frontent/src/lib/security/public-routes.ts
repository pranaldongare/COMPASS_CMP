/**
 * The routes that exist for somebody with no session.
 *
 * One list, imported by everything that needs the answer. It used to be three:
 * the proxy had one, the auth provider had another, and the section guard a
 * third - and they disagreed. The provider's copy did not know about
 * `/sign-up`, so a person registering triggered a "who am I" request, got the
 * 401 that anonymous visitors get, and was bounced to sign-in - which is the
 * one thing they could not yet do. It also listed `/notice/` and `/verify`,
 * neither of which is a route in this application.
 *
 * Kept free of imports so the proxy can use it on the edge runtime.
 */

/** Path prefixes reachable with no session at all. */
export const PUBLIC_PREFIXES = ["/sign-in", "/sign-up", "/rights", "/c/"] as const;

/**
 * Is this path public?
 *
 * `/` counts: the root page is a server redirect to the dashboard, and the
 * proxy's redirect-to-sign-in runs before it, so it has to be let through.
 */
export function isPublicPath(pathname: string): boolean {
  return pathname === "/" || PUBLIC_PREFIXES.some((prefix) => pathname.startsWith(prefix));
}
