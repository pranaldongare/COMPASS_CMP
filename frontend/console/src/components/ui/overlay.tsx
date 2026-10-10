/**
 * Things that float over the page: tooltips, popovers and the row menu
 * (2026-10-10).
 *
 * All on Radix, so focus, Escape, outside clicks, collision with the screen
 * edge and the ARIA roles are the library's job rather than ours. The look is
 * the design system's: radius, shadow, border and the menu's enter animation.
 */
"use client";

import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import * as PopoverPrimitive from "@radix-ui/react-popover";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { MoreHorizontal } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { cn } from "@/lib/format";

/* =================================================================== Tooltip */

/** Hover or focus to see more. Wraps one focusable or hoverable element. */
export function Tooltip({
  content,
  children,
  side = "top",
}: {
  content: React.ReactNode;
  children: React.ReactElement;
  side?: "top" | "right" | "bottom" | "left";
}) {
  if (!content) return children;
  return (
    <TooltipPrimitive.Provider delayDuration={400} skipDelayDuration={150}>
      <TooltipPrimitive.Root>
        <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
        <TooltipPrimitive.Portal>
          <TooltipPrimitive.Content
            side={side}
            sideOffset={6}
            collisionPadding={8}
            className="menu-in z-50 max-w-xs rounded-md bg-text px-2.5 py-1.5 text-xs leading-snug text-text-inverse shadow-[var(--shadow-raised)]"
          >
            {content}
          </TooltipPrimitive.Content>
        </TooltipPrimitive.Portal>
      </TooltipPrimitive.Root>
    </TooltipPrimitive.Provider>
  );
}

/**
 * Text cut to one line, the whole of it in a tooltip. For table cells, where a
 * long name wrapping onto four lines is what made the registers hard to scan.
 */
export function Truncate({
  children,
  className,
}: {
  children: string;
  className?: string;
}) {
  return (
    <Tooltip content={children}>
      <span tabIndex={-1} className={cn("block max-w-full truncate", className)}>
        {children}
      </span>
    </Tooltip>
  );
}

/* =================================================================== Popover */

export const Popover = PopoverPrimitive.Root;
export const PopoverTrigger = PopoverPrimitive.Trigger;
export const PopoverClose = PopoverPrimitive.Close;

export function PopoverContent({
  className,
  align = "start",
  ...props
}: React.ComponentProps<typeof PopoverPrimitive.Content>) {
  return (
    <PopoverPrimitive.Portal>
      <PopoverPrimitive.Content
        align={align}
        sideOffset={6}
        collisionPadding={8}
        className={cn(
          "menu-in z-50 rounded-lg border border-border bg-surface p-3 shadow-[var(--shadow-pop)] outline-none",
          className,
        )}
        {...props}
      />
    </PopoverPrimitive.Portal>
  );
}

/* ================================================================ Row actions */

export interface RowAction {
  label: string;
  icon?: React.ComponentType<{ className?: string }>;
  /** A link, or ... */
  href?: string;
  /** ... something to do. */
  onSelect?: () => void;
  /** Red, and kept last. */
  destructive?: boolean;
  disabled?: boolean;
}

/**
 * One ⋯ button per table row, holding everything a row can do (2026-10-10).
 *
 * A row of text buttons - View, Reassign, Edit, Suspend - made the actions
 * column the widest thing on the page. Opening the record stays a link on the
 * row's name; the rest is here.
 */
export function RowActions({
  label,
  actions,
}: {
  /** What the menu is for: "Actions for Gait rig". */
  label: string;
  actions: RowAction[];
}) {
  const shown = actions.filter(Boolean);
  if (shown.length === 0) return null;
  const safe = shown.filter((a) => !a.destructive);
  const risky = shown.filter((a) => a.destructive);
  return (
    <DropdownMenu.Root modal={false}>
      <DropdownMenu.Trigger
        aria-label={label}
        className={cn(
          "grid size-8 place-items-center rounded-md text-text-subtle transition-colors",
          "hover:bg-bg-inset hover:text-text data-[state=open]:bg-bg-inset data-[state=open]:text-text",
          "outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-border)]",
        )}
      >
        <MoreHorizontal className="size-4" aria-hidden="true" />
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={4}
          collisionPadding={8}
          className="menu-in z-50 min-w-44 rounded-lg border border-border bg-surface p-1 shadow-[var(--shadow-pop)]"
        >
          {safe.map((action) => (
            <ActionItem key={action.label} action={action} />
          ))}
          {risky.length > 0 && safe.length > 0 && (
            <DropdownMenu.Separator className="my-1 h-px bg-border" />
          )}
          {risky.map((action) => (
            <ActionItem key={action.label} action={action} />
          ))}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}

function ActionItem({ action }: { action: RowAction }) {
  const Icon = action.icon;
  const className = cn(
    "flex w-full cursor-pointer items-center gap-2.5 rounded-md px-2.5 py-1.5 text-sm outline-none select-none",
    "data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
    action.destructive
      ? "text-danger-text data-[highlighted]:bg-danger-subtle"
      : "text-text data-[highlighted]:bg-bg-inset",
  );
  const inner = (
    <>
      {Icon && <Icon className="size-4 shrink-0 opacity-70" aria-hidden="true" />}
      {action.label}
    </>
  );
  if (action.href) {
    return (
      <DropdownMenu.Item asChild disabled={action.disabled} className={className}>
        <Link href={action.href}>{inner}</Link>
      </DropdownMenu.Item>
    );
  }
  return (
    <DropdownMenu.Item
      disabled={action.disabled}
      onSelect={() => action.onSelect?.()}
      className={className}
    >
      {inner}
    </DropdownMenu.Item>
  );
}
