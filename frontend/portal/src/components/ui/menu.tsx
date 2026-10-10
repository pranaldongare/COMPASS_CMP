/**
 * A dropdown menu, following the WAI-ARIA menu button pattern.
 *
 * The trigger says it has a menu and whether it is open; opening moves focus to
 * the first item; the arrow keys, Home and End move between items; Escape
 * closes and hands focus back to the trigger; Tab, a click elsewhere or choosing
 * an item closes it. Items are buttons or links, so what they do is still a
 * button press or a navigation - the menu only arranges them.
 *
 *   <Menu label="Account" trigger={<>…</>}>
 *     <MenuLabel>Priya Menon</MenuLabel>
 *     <MenuItem href="/account" icon={UserRound}>Your profile</MenuItem>
 *     <MenuSeparator />
 *     <MenuItem onSelect={signOut} icon={LogOut}>Sign out</MenuItem>
 *   </Menu>
 */
"use client";

import Link from "next/link";
import * as React from "react";

import { cn } from "@/lib/format";

interface MenuContextValue {
  close: (refocus?: boolean) => void;
}

const MenuContext = React.createContext<MenuContextValue | null>(null);

function useMenu(): MenuContextValue {
  const ctx = React.useContext(MenuContext);
  if (!ctx) throw new Error("Menu parts must sit inside <Menu>");
  return ctx;
}

function items(root: HTMLElement | null): HTMLElement[] {
  return Array.from(root?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? []);
}

export function Menu({
  label,
  trigger,
  triggerClassName,
  align = "end",
  side = "bottom",
  children,
}: {
  /** The trigger's accessible name when its content is not text. */
  label: string;
  trigger: React.ReactNode;
  triggerClassName?: string;
  align?: "start" | "end";
  /** Which way it opens: down from a bar, up from the foot of a sidebar. */
  side?: "bottom" | "top";
  children: React.ReactNode;
}) {
  const [open, setOpen] = React.useState(false);
  const rootRef = React.useRef<HTMLDivElement>(null);
  const triggerRef = React.useRef<HTMLButtonElement>(null);
  const menuRef = React.useRef<HTMLDivElement>(null);
  const menuId = React.useId();

  const close = React.useCallback((refocus = true) => {
    setOpen(false);
    if (refocus) triggerRef.current?.focus();
  }, []);

  // Focus the first item once the menu is on screen.
  React.useEffect(() => {
    if (open) items(menuRef.current)[0]?.focus();
  }, [open]);

  // A press anywhere outside closes it, without stealing that press's focus.
  React.useEffect(() => {
    if (!open) return;
    function onPointerDown(event: PointerEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  function onMenuKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    const list = items(menuRef.current);
    const at = list.findIndex((el) => el === document.activeElement);
    const move = (to: number) => {
      event.preventDefault();
      list[(to + list.length) % list.length]?.focus();
    };
    if (event.key === "ArrowDown") move(at + 1);
    else if (event.key === "ArrowUp") move(at - 1);
    else if (event.key === "Home") move(0);
    else if (event.key === "End") move(list.length - 1);
    else if (event.key === "Escape") {
      event.preventDefault();
      close();
    } else if (event.key === "Tab") setOpen(false);
  }

  const ctx = React.useMemo(() => ({ close }), [close]);

  return (
    <div ref={rootRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        aria-label={label}
        onClick={() => setOpen((o) => !o)}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown" && !open) {
            event.preventDefault();
            setOpen(true);
          }
        }}
        className={cn(
          "rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-subtle)]",
          triggerClassName,
        )}
      >
        {trigger}
      </button>
      {open && (
        <MenuContext.Provider value={ctx}>
          <div
            ref={menuRef}
            id={menuId}
            role="menu"
            aria-label={label}
            onKeyDown={onMenuKeyDown}
            className={cn(
              "menu-in absolute z-50 w-64 overflow-hidden rounded-xl border border-border bg-surface p-1.5 shadow-[var(--shadow-pop)]",
              side === "top" ? "bottom-full mb-2" : "top-full mt-2",
              align === "end" ? "right-0" : "left-0",
              side === "top"
                ? align === "end" ? "origin-bottom-right" : "origin-bottom-left"
                : align === "end" ? "origin-top-right" : "origin-top-left",
            )}
          >
            {children}
          </div>
        </MenuContext.Provider>
      )}
    </div>
  );
}

const itemClass =
  "flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm outline-none transition-colors hover:bg-bg-inset focus:bg-bg-inset";

export function MenuItem({
  children,
  icon: Icon,
  href,
  onSelect,
  tone,
}: {
  children: React.ReactNode;
  icon?: React.ComponentType<{ className?: string }>;
  /** A link: navigating is the action. */
  href?: string;
  /** A button: this runs, then the menu closes. */
  onSelect?: () => void;
  tone?: "danger";
}) {
  const { close } = useMenu();
  const content = (
    <>
      {Icon && (
        <Icon
          className={cn(
            "size-4 shrink-0",
            tone === "danger" ? "text-danger" : "text-text-subtle",
          )}
          aria-hidden="true"
        />
      )}
      <span className="min-w-0 flex-1 truncate">{children}</span>
    </>
  );
  const className = cn(itemClass, tone === "danger" ? "text-danger-text" : "text-text");
  if (href) {
    return (
      <Link
        href={href}
        role="menuitem"
        tabIndex={-1}
        className={className}
        onClick={() => close(false)}
      >
        {content}
      </Link>
    );
  }
  return (
    <button
      type="button"
      role="menuitem"
      tabIndex={-1}
      className={className}
      onClick={() => {
        close(false);
        onSelect?.();
      }}
    >
      {content}
    </button>
  );
}

export function MenuLabel({ children }: { children: React.ReactNode }) {
  return <div className="px-2.5 pt-1.5 pb-2">{children}</div>;
}

export function MenuSeparator() {
  return <div role="separator" className="-mx-1.5 my-1.5 h-px bg-border" />;
}
