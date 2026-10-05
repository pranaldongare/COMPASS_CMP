/**
 * "Back to the list I was using" - distinct from "go to this record's parent".
 *
 * A notice can be reached from the notices register or from its project, and
 * those are different places to go back to; a project reached from a filtered
 * list should go back to that filtered list, not to every project (UX review
 * 2026-10-05). A link that opens a record carries where it was opened from,
 * `?from=`; the record's page offers that place back, and falls back to the
 * record's parent when there is none.
 *
 * `from` is checked to be one of this site's own paths, and to start with
 * the prefix the page expects, before anything links to it - it arrives in a
 * URL anybody can write.
 */
"use client";

import { usePathname, useSearchParams } from "next/navigation";

import { safeRedirectPath } from "@/lib/security";

/** The current page, query string included: what a link out of it records. */
export function useHere(): string {
  const pathname = usePathname();
  const search = useSearchParams().toString();
  return search ? `${pathname}?${search}` : pathname;
}

/** `href` with `from` added, keeping any `#section` at the end. */
export function withFrom(href: string, from: string): string {
  const [path, hash] = href.split("#");
  const join = path.includes("?") ? "&" : "?";
  return `${path}${join}from=${encodeURIComponent(from)}${hash ? `#${hash}` : ""}`;
}

/** A `from` value, if it is a safe path under one of `prefixes`; otherwise null. */
export function returnTarget(
  from: string | null,
  prefixes: readonly string[],
): string | null {
  if (!from) return null;
  const target = safeRedirectPath(from, "");
  if (!target) return null;
  return prefixes.some(
    (p) =>
      target === p ||
      target.startsWith(`${p}?`) ||
      target.startsWith(`${p}/`) ||
      target.startsWith(`${p}#`),
  )
    ? target
    : null;
}

/** The page this one was opened from, under the given prefixes. */
export function useReturnTo(prefixes: readonly string[]): string | null {
  return returnTarget(useSearchParams().get("from"), prefixes);
}
