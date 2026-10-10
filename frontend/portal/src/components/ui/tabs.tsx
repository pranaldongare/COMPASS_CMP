/**
 * Tabs, following the WAI-ARIA tabs pattern.
 *
 * One tab stop for the whole row: the selected tab is focusable and the arrow
 * keys move between the others (Home and End to the ends), so a keyboard user
 * does not tab through every heading to reach the content. Panels that are not
 * selected stay mounted and hidden, so a half-typed form survives a look at
 * another tab.
 *
 *   <Tabs value={tab} onValueChange={setTab} label="Account">
 *     <TabList>
 *       <Tab value="contacts">Contacts</Tab>
 *       <Tab value="sessions" count={4}>Sessions</Tab>
 *     </TabList>
 *     <TabPanel value="contacts">…</TabPanel>
 *     <TabPanel value="sessions">…</TabPanel>
 *   </Tabs>
 */
"use client";

import * as React from "react";

import { cn } from "@/lib/format";

interface TabsContextValue {
  value: string;
  onValueChange: (value: string) => void;
  id: string;
  label: string;
}

const TabsContext = React.createContext<TabsContextValue | null>(null);

function useTabs(): TabsContextValue {
  const ctx = React.useContext(TabsContext);
  if (!ctx) throw new Error("Tab parts must sit inside <Tabs>");
  return ctx;
}

const slug = (value: string) => value.replace(/[^A-Za-z0-9_-]/g, "-");

export function Tabs({
  value,
  onValueChange,
  label,
  children,
  className,
}: {
  value: string;
  onValueChange: (value: string) => void;
  /** Names the tab list for assistive technology. */
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  const id = React.useId();
  const ctx = React.useMemo(
    () => ({ value, onValueChange, id, label }),
    [value, onValueChange, id, label],
  );
  return (
    <TabsContext.Provider value={ctx}>
      <div className={className}>{children}</div>
    </TabsContext.Provider>
  );
}

export function TabList({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  const { label } = useTabs();
  const ref = React.useRef<HTMLDivElement>(null);

  function onKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    const tabs = Array.from(
      ref.current?.querySelectorAll<HTMLButtonElement>('[role="tab"]:not([disabled])') ??
        [],
    );
    const at = tabs.findIndex((t) => t === document.activeElement);
    if (at < 0) return;
    const to =
      event.key === "ArrowRight"
        ? (at + 1) % tabs.length
        : event.key === "ArrowLeft"
          ? (at - 1 + tabs.length) % tabs.length
          : event.key === "Home"
            ? 0
            : event.key === "End"
              ? tabs.length - 1
              : -1;
    if (to < 0) return;
    event.preventDefault();
    tabs[to].focus();
    tabs[to].click();
  }

  return (
    <div
      ref={ref}
      role="tablist"
      aria-label={label}
      onKeyDown={onKeyDown}
      className={cn(
        "scroll-x mb-6 flex gap-1 border-b border-border [--scroll-bg:var(--bg)]",
        // The row scrolls sideways on a phone rather than wrapping into a
        // second line of tabs that reads as a second level.
        "[&::-webkit-scrollbar]:hidden",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function Tab({
  value,
  children,
  count,
  alert,
  icon: Icon,
  disabled,
}: {
  value: string;
  children: React.ReactNode;
  /** A number shown beside the label - how many rows the panel holds. */
  count?: number;
  /** Something in the panel is late: the count turns red, and says so to a
   *  screen reader, so it is seen from whichever tab is open. */
  alert?: string;
  icon?: React.ComponentType<{ className?: string }>;
  disabled?: boolean;
}) {
  const { value: selected, onValueChange, id } = useTabs();
  const active = selected === value;
  const ref = React.useRef<HTMLButtonElement>(null);
  // On a phone the row scrolls sideways; the selected tab - one opened from a
  // link, say - is brought inside it rather than left cut off at the edge.
  // The row alone scrolls: scrollIntoView would move the page as well.
  React.useEffect(() => {
    const tab = ref.current;
    const row = tab?.parentElement;
    if (!active || !tab || !row || row.scrollWidth <= row.clientWidth) return;
    const left = tab.offsetLeft - row.offsetLeft;
    const right = left + tab.offsetWidth;
    if (left < row.scrollLeft) row.scrollLeft = Math.max(0, left - 16);
    else if (right > row.scrollLeft + row.clientWidth) row.scrollLeft = right - row.clientWidth + 16;
  }, [active]);
  return (
    <button
      ref={ref}
      type="button"
      role="tab"
      id={`${id}-tab-${slug(value)}`}
      aria-selected={active}
      aria-controls={`${id}-panel-${slug(value)}`}
      tabIndex={active ? 0 : -1}
      disabled={disabled}
      onClick={() => onValueChange(value)}
      className={cn(
        "relative -mb-px inline-flex shrink-0 items-center gap-2 border-b-2 px-3.5 py-2.5 text-sm whitespace-nowrap",
        "transition-colors outline-none focus-visible:rounded-t-lg focus-visible:bg-bg-inset",
        "disabled:cursor-not-allowed disabled:opacity-50",
        active
          ? "border-accent font-semibold text-accent-text"
          : "border-transparent text-text-muted hover:border-border-strong hover:text-text",
      )}
    >
      {Icon && <Icon className="size-4" aria-hidden="true" />}
      {children}
      {count !== undefined && (
        <span
          className={cn(
            "tabular min-w-5 rounded-full px-1.5 text-center text-2xs font-semibold",
            alert
              ? "bg-danger-subtle text-danger-text"
              : active
                ? "bg-accent-subtle text-accent-text"
                : "bg-bg-inset text-text-subtle",
          )}
        >
          {count}
        </span>
      )}
      {alert && <span className="sr-only">({alert})</span>}
    </button>
  );
}

export function TabPanel({
  value,
  children,
  className,
}: {
  value: string;
  children: React.ReactNode;
  className?: string;
}) {
  const { value: selected, id } = useTabs();
  return (
    <div
      role="tabpanel"
      id={`${id}-panel-${slug(value)}`}
      aria-labelledby={`${id}-tab-${slug(value)}`}
      hidden={selected !== value}
      // Focusable so a screen-reader user can move from the tab straight into
      // a panel that has no focusable content of its own.
      tabIndex={0}
      className={cn("outline-none", className)}
    >
      {children}
    </div>
  );
}

/**
 * The selected tab, kept in the address's `#fragment` so a tab can be linked
 * to and survives a reload. Only values in `allowed` are adopted.
 *
 * `sections` names anchors *inside* a tab: `#sites` opens the tab holding the
 * sites card. Addresses that predate the tabs keep working that way, and a
 * link can name the record it means rather than the tab it happens to sit in.
 * The fragment itself comes back third, for a page that scrolls to it.
 */
export function useHashTab<T extends string>(
  allowed: readonly T[],
  fallback: T,
  sections: Readonly<Record<string, T>> = {},
): [T, (v: string) => void, string] {
  const hash = React.useSyncExternalStore(
    (notify) => {
      window.addEventListener("hashchange", notify);
      return () => window.removeEventListener("hashchange", notify);
    },
    () => window.location.hash.slice(1),
    () => "",
  );
  const value = (allowed as readonly string[]).includes(hash)
    ? (hash as T)
    : Object.hasOwn(sections, hash)
      ? sections[hash]
      : fallback;
  const set = React.useCallback(
    (next: string) => {
      if (!(allowed as readonly string[]).includes(next)) return;
      // A new history entry per tab would make Back walk through tabs; replace.
      window.history.replaceState(null, "", `#${next}`);
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    },
    [allowed],
  );
  return [value, set, hash];
}
