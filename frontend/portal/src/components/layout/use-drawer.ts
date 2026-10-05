/**
 * What a drawer over the page owes a keyboard user (review 2026-10-01, UX-4).
 *
 * The phone navigation is the same `<nav>` the desktop shows beside the page,
 * so it cannot simply become a Radix dialog. This hook gives it the parts of
 * one that matter: focus moves into it when it opens, Tab and Shift+Tab stay
 * inside it, Escape closes it, and closing returns focus to whatever opened
 * it - unless a link inside it already took the person somewhere else.
 *
 * Returns the ref to put on the drawer's root element.
 */
"use client";

import * as React from "react";

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

function focusables(root: HTMLElement): HTMLElement[] {
  return Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
    (el) => !el.hasAttribute("inert") && el.getAttribute("aria-hidden") !== "true",
  );
}

export function useDrawer<T extends HTMLElement = HTMLElement>(
  open: boolean,
  onClose: () => void,
): React.RefObject<T | null> {
  const panel = React.useRef<T | null>(null);
  // The latest close, without re-running the effect - and moving focus - on
  // every render that passes a new arrow.
  const close = React.useRef(onClose);
  React.useEffect(() => {
    close.current = onClose;
  }, [onClose]);

  React.useEffect(() => {
    if (!open) return;
    const opener = document.activeElement as HTMLElement | null;
    const root = panel.current;
    if (root) focusables(root)[0]?.focus();

    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        close.current();
        return;
      }
      const node = panel.current;
      if (event.key !== "Tab" || !node) return;
      const items = focusables(node);
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      const at = document.activeElement;
      if (!node.contains(at)) {
        event.preventDefault();
        first.focus();
      } else if (event.shiftKey && at === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && at === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      // Back to the opener only if focus is still in the drawer or nowhere:
      // a link that navigated has put the person where they asked to be.
      const at = document.activeElement;
      if (!at || at === document.body || root?.contains(at) || !at.isConnected) {
        opener?.focus();
      }
    };
  }, [open]);

  return panel;
}
