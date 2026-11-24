/**
 * Leave for another page with a full load, not a client-side transition.
 *
 * For the moment the session changes under the page - a half-finished sign-in
 * just ended. A client-side transition keeps the old session state in memory
 * while the auth gates of both pages react to the new one, and one of them
 * wins the race; a full load starts from what the server says now.
 */
export function navigateFresh(href: string): void {
  window.location.replace(href);
}
