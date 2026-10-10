/**
 * The component library.
 *
 * Small, composable, and typed. Every visual decision comes from the tokens in
 * `globals.css`; nothing here hardcodes a colour or a spacing value, which is
 * what lets the whole product change theme in one file.
 *
 * Accessibility is not a separate pass. Buttons announce their busy state,
 * inputs are always associated with a label, errors are wired through
 * `aria-describedby`, and every icon-only control carries a name.
 */
"use client";

import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";

import { cn } from "@/lib/format";

/* ==================================================================== Button */
const buttonVariants = cva(
  cn(
    "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full",
    "font-medium select-none",
    // Transform is in the transition so the press reads as physical. The active
    // state sinks 1px rather than changing colour: a finger expects the surface
    // to move under it.
    "transition-[background-color,border-color,color,box-shadow,transform,filter] duration-150",
    "active:translate-y-px",
    "disabled:pointer-events-none disabled:opacity-50 disabled:active:translate-y-0",
    "[&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg]:size-4",
  ),
  {
    variants: {
      variant: {
        // Pills (2026-10-10, the pill-chip style). The primary is a COMPASS
        // blue gradient with a soft glow - reserved for the single primary
        // action on a screen; two of these and neither leads.
        primary:
          "bg-linear-135 from-accent to-accent-hover text-accent-contrast shadow-[0_6px_16px_rgb(47_114_187/0.3)] hover:brightness-110 active:brightness-95",
        secondary:
          "border border-border bg-surface text-text shadow-[var(--shadow-xs)] hover:border-border-strong hover:bg-surface-hover",
        ghost: "text-text-muted hover:bg-accent-subtle hover:text-accent-text",
        danger:
          "border border-danger-border bg-danger-subtle text-danger-text hover:border-danger hover:bg-danger hover:text-white",
        // For the one destructive action on a page: reads as a link until
        // hovered, so it does not compete with the primary action.
        subtle: "text-danger-text hover:bg-danger-subtle",
        link: "text-accent-text underline-offset-4 hover:underline",
      },
      size: {
        sm: "h-8 px-3.5 text-xs",
        md: "h-9 px-4 text-sm",
        lg: "h-11 px-6 text-base",
        icon: "size-9",
      },
    },
    defaultVariants: { variant: "secondary", size: "md" },
  },
);

/**
 * The button's loading indicator.
 *
 * Module-private: it exists for `Button`, and a spinner used anywhere else
 * would be a loading state that should have been a skeleton. Skeletons say
 * what is coming; a spinner says only that something is happening.
 */
function Spinner({ className }: { className?: string }) {
  return (
    <svg
      className={cn("animate-spin", className)}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.25" />
      <path
        d="M12 2a10 10 0 0 1 10 10"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  );
}

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  /** Shows a spinner and blocks interaction. Prefer this to disabling the
   *  button silently - a control that stops responding with no explanation
   *  reads as broken. */
  loading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild, loading, children, disabled, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        ref={ref}
        className={cn(buttonVariants({ variant, size }), className)}
        disabled={disabled || loading}
        aria-busy={loading || undefined}
        {...props}
      >
        {loading ? (
          <>
            <Spinner className="size-4" />
            <span>{children}</span>
          </>
        ) : (
          children
        )}
      </Comp>
    );
  },
);
Button.displayName = "Button";

/* ====================================================================== Card */
export function Card({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        // White on the grey page (2026-10-10).
        "rounded-lg border border-border bg-surface shadow-[var(--shadow-card)]",
        className,
      )}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  // A lightly tinted band over the white body (2026-10-10).
  return <div className={cn("px-5 py-3.5 border-b border-border bg-[var(--card-head)] rounded-t-[inherit]", className)} {...props} />;
}

export function CardTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cn("text-base font-semibold", className)} {...props} />;
}

export function CardBody({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-5", className)} {...props} />;
}

/* ===================================================================== Badge */
const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium",
  {
    variants: {
      tone: {
        neutral: "bg-bg-inset text-text-muted border-border",
        accent: "bg-accent-subtle text-accent-text border-accent-border",
        success: "bg-success-subtle text-success-text border-success-border",
        warning: "bg-warning-subtle text-warning-text border-warning-border",
        danger: "bg-danger-subtle text-danger-text border-danger-border",
        info: "bg-info-subtle text-info-text border-info-border",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {
  /** A coloured dot in front of the label.
   *
   *  Colour alone never carries the meaning - the label is always present - so
   *  the badge stays readable for someone who cannot distinguish the hues.
   */
  dot?: boolean;
}

export function Badge({ className, tone, dot, children, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ tone }), className)} {...props}>
      {dot && <span className="size-1.5 rounded-full bg-current" aria-hidden="true" />}
      {children}
    </span>
  );
}

/* ===================================================================== Input */
export interface FieldProps {
  label: string;
  hint?: string;
  error?: string;
  required?: boolean;
  children: (props: {
    id: string;
    "aria-invalid": boolean | undefined;
    "aria-describedby": string | undefined;
  }) => React.ReactNode;
}

/**
 * Label, control, hint and error as one unit.
 *
 * The wiring is the point: `htmlFor`/`id` associate the label, and
 * `aria-describedby` points at whichever of hint/error is present, so a screen
 * reader announces the requirement and the failure rather than just "edit box".
 */
export function Field({ label, hint, error, required, children }: FieldProps) {
  const id = React.useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [errorId, hintId].filter(Boolean).join(" ") || undefined;

  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-medium text-text">
        {label}
        {required && (
          <span className="text-danger ml-0.5" aria-label="required">
            *
          </span>
        )}
      </label>
      {children({ id, "aria-invalid": error ? true : undefined, "aria-describedby": describedBy })}
      {error ? (
        <p id={errorId} role="alert" className="text-xs text-danger-text">
          {error}
        </p>
      ) : hint ? (
        <p id={hintId} className="text-xs text-text-subtle">
          {hint}
        </p>
      ) : null}
    </div>
  );
}

// Outlined with icon tiles (2026-10-10, chosen from three form styles): a
// crisp white field with a hairline, rounder corners, a blue ring on focus and
// a red one on error. `control` is the hook for the icon tiles in
// styles/controls.css.
const controlBase = cn(
  "control w-full rounded-[0.625rem] border bg-surface px-3 text-sm text-text",
  "placeholder:text-text-subtle",
  // The hairline is what makes a field read as a well rather than a card.
  "border-border-strong shadow-[var(--shadow-xs)]",
  // A ring on focus, not a colour swap: it survives any background and, unlike a
  // border-width change, moves nothing on the page.
  "focus:border-accent focus:ring-3 focus:ring-[var(--accent-border)]/45 focus:outline-none",
  "disabled:cursor-not-allowed disabled:bg-bg-subtle disabled:text-text-subtle",
  "aria-[invalid=true]:border-danger aria-[invalid=true]:ring-3 aria-[invalid=true]:ring-[var(--danger-subtle)]",
  "transition-[border-color,box-shadow] duration-150",
);

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input ref={ref} className={cn(controlBase, "h-10", className)} {...props} />
  ),
);
Input.displayName = "Input";

export const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => (
  <textarea ref={ref} className={cn(controlBase, "py-2 min-h-24 leading-relaxed", className)} {...props} />
));
Textarea.displayName = "Textarea";

export const Select = React.forwardRef<
  HTMLSelectElement,
  React.SelectHTMLAttributes<HTMLSelectElement>
>(({ className, ...props }, ref) => (
  // Still the browser's own <select> - its keyboard, screen-reader and mobile
  // pickers are better than any imitation - drawn like the other fields, with
  // the product's chevron (`.select-chevron`, styles/controls.css).
  <select
    ref={ref}
    className={cn(controlBase, "select-chevron h-10 cursor-pointer appearance-none pr-9", className)}
    {...props}
  />
));
Select.displayName = "Select";

/* ===================================================================== Alert */
const alertVariants = cva("rounded-md border px-4 py-3 text-sm", {
  variants: {
    tone: {
      info: "bg-info-subtle border-info-border text-info-text",
      success: "bg-success-subtle border-success-border text-success-text",
      warning: "bg-warning-subtle border-warning-border text-warning-text",
      danger: "bg-danger-subtle border-danger-border text-danger-text",
    },
  },
  defaultVariants: { tone: "info" },
});

export interface AlertProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof alertVariants> {
  title?: string;
}

export function Alert({ className, tone, title, children, ...props }: AlertProps) {
  return (
    <div
      // Errors interrupt; everything else waits for a pause. Making every alert
      // assertive trains people to ignore the assertive ones.
      role={tone === "danger" ? "alert" : "status"}
      className={cn(alertVariants({ tone }), className)}
      {...props}
    >
      {title && <p className="font-semibold mb-1">{title}</p>}
      <div className="[&_p]:leading-relaxed">{children}</div>
    </div>
  );
}

/* ================================================================== Skeleton */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn("shimmer rounded-md", className)}
      aria-hidden="true"
      data-testid="skeleton"
    />
  );
}

/**
 * Loading placeholder for a table.
 *
 * Matched to the real row height so the layout does not jump when data arrives -
 * a shift at the moment someone reaches for a control makes them click the wrong
 * thing.
 */
export function TableSkeleton({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="space-y-px" aria-hidden="true">
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-4 px-4 py-3">
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={c} className={cn("h-4", c === 0 ? "w-1/3" : "flex-1")} />
          ))}
        </div>
      ))}
    </div>
  );
}

/* ================================================================ EmptyState */
export function EmptyState({
  icon,
  illustration,
  title,
  description,
  action,
}: {
  icon?: React.ReactNode;
  /** An illustration from `ui/graphics`. Preferred over a bare icon: the empty
   *  screen is where a product either looks considered or looks unfinished. */
  illustration?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="relative flex flex-col items-center justify-center overflow-hidden px-6 py-14 text-center">
      <span aria-hidden="true" className="grid-texture absolute inset-0" />
      <div className="relative">
        {illustration ? (
          <div className="mb-4 flex justify-center">{illustration}</div>
        ) : icon ? (
          <div className="mb-3 flex justify-center text-text-subtle [&_svg]:size-8">{icon}</div>
        ) : null}
        <p className="text-sm font-medium text-text">{title}</p>
        {description && (
          <p className="mx-auto mt-1 max-w-sm text-sm text-text-muted">{description}</p>
        )}
        {action && <div className="mt-4">{action}</div>}
      </div>
    </div>
  );
}

/* ===================================================================== Table */
/*
 * Clean lines (2026-10-10, chosen from three table styles): no card and no
 * fills - small capital headings over a firm rule, roomy rows split by
 * hairlines, and a blue marker on the row under the pointer.
 */
export function Table({ className, ...props }: React.TableHTMLAttributes<HTMLTableElement>) {
  return (
    <div className="scroll-x">
      <table className={cn("w-full text-sm", className)} {...props} />
    </div>
  );
}

export function Th({ className, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      scope="col"
      className={cn(
        "px-3.5 py-2.5 text-left text-2xs font-semibold tracking-[0.07em] uppercase",
        "whitespace-nowrap text-text-subtle border-b-2 border-border",
        className,
      )}
      {...props}
    />
  );
}

export function Td({ className, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td
      className={cn("px-3.5 py-4 border-b border-border/70 align-middle", className)}
      {...props}
    />
  );
}

export function Tr({ className, ...props }: React.HTMLAttributes<HTMLTableRowElement>) {
  return (
    <tr
      className={cn(
        "transition-colors hover:bg-[var(--row-hover)]",
        "hover:[&>td:first-child]:shadow-[inset_3px_0_0_var(--accent)]",
        className,
      )}
      {...props}
    />
  );
}

/* ====================================================== Definition list ==== */
export function DescriptionList({ children }: { children: React.ReactNode }) {
  return <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-[minmax(9rem,auto)_1fr]">{children}</dl>;
}

export function DescriptionItem({
  term,
  children,
}: {
  term: string;
  children: React.ReactNode;
}) {
  return (
    <>
      <dt className="text-sm text-text-muted">{term}</dt>
      <dd className="text-sm text-text break-words">{children}</dd>
    </>
  );
}

/* ==================================================================== Avatar */
/** Soft fills for initials, picked by name so a person keeps one colour. */
const AVATAR_TONES = [
  "bg-accent-subtle text-accent-text",
  "bg-success-subtle text-success-text",
  "bg-warning-subtle text-warning-text",
  "bg-info-subtle text-info-text",
  "bg-danger-subtle text-danger-text",
  "bg-bg-inset text-text-muted",
];

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  const first = parts[0][0] ?? "";
  const last = parts.length > 1 ? (parts[parts.length - 1][0] ?? "") : "";
  return (first + last).toUpperCase();
}

/**
 * A person's initials in a soft circle (2026-10-10), beside their name in a
 * table or list. Decorative: the name next to it is what is read out.
 */
export function Avatar({ name, size = "md", className }: { name: string; size?: "sm" | "md"; className?: string }) {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) | 0;
  const tone = AVATAR_TONES[Math.abs(hash) % AVATAR_TONES.length];
  return (
    <span
      aria-hidden="true"
      className={cn(
        "inline-grid shrink-0 place-items-center rounded-full font-semibold",
        size === "sm" ? "size-6 text-[0.625rem]" : "size-8 text-xs",
        tone,
        className,
      )}
    >
      {initials(name)}
    </span>
  );
}

/**
 * Avatar, name and a muted second line: how a person reads in a register.
 * `name` is a node so the caller can make it the row's link.
 */
export function PersonCell({
  name,
  label,
  secondary,
}: {
  name: React.ReactNode;
  /** The plain name, for the initials. */
  label: string;
  secondary?: React.ReactNode;
}) {
  return (
    <span className="flex min-w-0 items-center gap-3">
      <Avatar name={label} />
      <span className="min-w-0">
        <span className="block truncate">{name}</span>
        {secondary && <span className="block truncate text-xs text-text-subtle">{secondary}</span>}
      </span>
    </span>
  );
}

/* ================================================================= Monospace */
/** For hashes, uuids and tokens: things that are compared character by character. */
export function Mono({ className, ...props }: React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn("font-mono text-xs text-text-muted break-all", className)}
      {...props}
    />
  );
}
