/**
 * The address a consent link is actually served at.
 *
 * The API returns a path — `/c/{token}` — and deliberately so: the host a link
 * is served on is deployment configuration, and a backend that baked one in
 * would hand out URLs that are confidently wrong after a move.
 *
 * Which host to put in front of it is the part the console got wrong. All three
 * places that showed a link used `window.location.origin`, which is the
 * console's own origin — port 3000 in development. `/c/{token}` is not a route
 * on the console; it is a page on the data principal's portal, on 3001. So
 * every link copied, minted or reminted here pointed at a host that 404s, and
 * the person it was handed to had no way to tell it was the wrong door rather
 * than a dead token.
 *
 * `config.subjectPortalUrl` is the origin that already answers the same
 * question everywhere else in the console — the sign-in page and the auth
 * provider both send a data principal there — so it answers this one too, and
 * a deployment sets it in one place.
 *
 * It takes the path as it arrived, `null` included: an absent one means the
 * token was never kept (links minted before they were recoverable), and the
 * callers treat the empty answer as "cannot be copied" rather than rendering a
 * bare origin.
 */

import { config } from "@/lib/config";

export function consentLinkUrl(urlPath: string | null | undefined): string {
  if (!urlPath) return "";
  return `${config.subjectPortalUrl.replace(/\/+$/, "")}${urlPath}`;
}
