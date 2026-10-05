/**
 * Help that returns you to where you were.
 *
 * The manual's "back" went to a fixed page - the dashboard, or My consents -
 * whatever page the person had left to read it (UX review 2026-10-05). Every
 * way into Help now carries the page it was opened from, `?from=`, and the
 * manual offers that page back. The manual checks it is one of this site's
 * own paths before linking to it (`safeRedirectPath`).
 */
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import * as React from "react";

/** `/help?from=<this page>`, read at the moment of leaving it. */
export function helpHref(): string {
  if (typeof window === "undefined") return "/help";
  const here = `${window.location.pathname}${window.location.search}`;
  if (here.startsWith("/help")) return "/help";
  return `/help?from=${encodeURIComponent(here)}`;
}

/** Where the manual's "back" should go: the page it was opened from, if safe. */
export function helpReturn(
  from: string | null,
  safe: (v: string | null) => string,
): string | null {
  if (!from) return null;
  const target = safe(from);
  return target === "" || target.startsWith("/help") ? null : target;
}

/** A link to Help that remembers the page it left. Plain `/help` without script. */
export const HelpLink = React.forwardRef<
  HTMLAnchorElement,
  Omit<React.ComponentPropsWithoutRef<typeof Link>, "href">
>(function HelpLink({ onClick, ...props }, ref) {
  const router = useRouter();
  return (
    <Link
      ref={ref}
      href="/help"
      onClick={(event) => {
        onClick?.(event);
        if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey)
          return;
        event.preventDefault();
        router.push(helpHref());
      }}
      {...props}
    />
  );
});
