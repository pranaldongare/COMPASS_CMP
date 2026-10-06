/**
 * Modal dialog.
 *
 * Radix rather than a hand-rolled overlay, because the parts that are easy to
 * skip are the parts that matter: focus is trapped inside while open and
 * restored to the trigger on close, Escape dismisses, the rest of the page is
 * inert to screen readers, and the title is wired to `aria-labelledby`. A modal
 * missing any of those is unusable without a mouse.
 */
"use client";

import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/primitives";
import { cn } from "@/lib/format";

export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogClose = DialogPrimitive.Close;

/** Tells the dialog around it that what was typed has been saved. */
const SavedContext = React.createContext<() => void>(() => {});

/**
 * For a form that saves and stays open - a message sent on a thread, a move
 * made with a reason: call it after the save succeeds, and closing the dialog
 * no longer asks about changes that are already saved. Outside a dialog it
 * does nothing.
 */
export function useDialogSaved(): () => void {
  return React.useContext(SavedContext);
}

/** The same, for a dialog's owner, which sits outside it: render it inside
 *  the dialog and bump `count` after each save. */
export function DialogSaved({ count }: { count: number }) {
  const saved = useDialogSaved();
  React.useEffect(() => {
    if (count > 0) saved();
  }, [count, saved]);
  return null;
}

export function DialogContent({
  className,
  children,
  title,
  description,
  size = "md",
  onEscapeKeyDown,
  onInteractOutside,
  onInput,
  ...props
}: React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content> & {
  title: string;
  description?: string;
  size?: "sm" | "md" | "lg";
}) {
  // Typed in since it opened? The content mounts afresh each time the dialog
  // opens, so this starts false every time. A dialog nobody has typed in
  // closes as it always did; one somebody has asks before its typing is
  // thrown away (UX review 2026-10-05: a project draft vanished on Escape).
  // A form's own Cancel, and a save that closes it, are not dismissals and do
  // not ask. A save that keeps it open - a message sent on a thread - says so
  // through `useDialogSaved`, and typing after it starts the question again.
  const [dirty, setDirty] = React.useState(false);
  const [asking, setAsking] = React.useState(false);
  const markSaved = React.useCallback(() => {
    setDirty(false);
    setAsking(false);
  }, []);
  const guard = (event: { preventDefault: () => void }) => {
    if (!dirty) return;
    event.preventDefault();
    setAsking(true);
  };
  const widths = {
    sm: "max-w-md",
    md: "max-w-xl",
    lg: "max-w-3xl",
  };

  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay
        className="overlay-in fixed inset-0 z-40 bg-black/50 backdrop-blur-[3px]"
      />
      <DialogPrimitive.Content
        className={cn(
          "dialog-in fixed left-1/2 top-1/2 z-50 w-[calc(100vw-2rem)]",
          widths[size],
          "rounded-2xl border border-border bg-surface shadow-[var(--shadow-pop)]",
          // A tall form must scroll inside the dialog, not push the page.
          "max-h-[calc(100dvh-4rem)] overflow-y-auto",
          className,
        )}
        onInput={(event) => {
          setDirty(true);
          onInput?.(event);
        }}
        onEscapeKeyDown={(event) => {
          onEscapeKeyDown?.(event);
          if (!event.defaultPrevented) guard(event);
        }}
        onInteractOutside={(event) => {
          onInteractOutside?.(event);
          if (!event.defaultPrevented) guard(event);
        }}
        {...props}
      >
        <div className="glass sticky top-0 z-10 flex items-start justify-between gap-4 rounded-t-2xl border-b border-border px-5 py-4">
          <div className="min-w-0">
            <DialogPrimitive.Title className="text-base font-semibold">
              {title}
            </DialogPrimitive.Title>
            {description ? (
              <DialogPrimitive.Description className="mt-1 text-sm text-text-muted">
                {description}
              </DialogPrimitive.Description>
            ) : (
              // Radix warns when Content has no Description. An explicit empty
              // one is clearer than suppressing the warning.
              <DialogPrimitive.Description className="sr-only">
                {title}
              </DialogPrimitive.Description>
            )}
          </div>
          <DialogPrimitive.Close
            className="shrink-0 rounded-lg p-1.5 text-text-subtle transition-colors hover:bg-bg-inset hover:text-text"
            aria-label="Close"
            onClick={guard}
          >
            <X className="size-4" />
          </DialogPrimitive.Close>
        </div>

        {asking && (
          <div
            role="alert"
            className="flex flex-wrap items-center justify-between gap-2 border-b border-warning-border bg-warning-subtle px-5 py-3 text-sm text-warning-text"
          >
            <span>You have changes that are not saved.</span>
            <span className="flex gap-2">
              <Button variant="secondary" size="sm" onClick={() => setAsking(false)}>
                Keep editing
              </Button>
              <DialogPrimitive.Close asChild>
                <Button variant="danger" size="sm">
                  Discard changes
                </Button>
              </DialogPrimitive.Close>
            </span>
          </div>
        )}

        <div className="px-5 py-4">
          <SavedContext.Provider value={markSaved}>{children}</SavedContext.Provider>
        </div>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

export function DialogFooter({ children }: { children: React.ReactNode }) {
  return (
    <div className="mt-5 flex flex-wrap items-center justify-end gap-2 border-t border-border pt-4">
      {children}
    </div>
  );
}

/**
 * Confirmation for an action that cannot be undone.
 *
 * Separate from the generic dialog on purpose: destructive actions get a named
 * consequence and a button labelled with the verb, never "OK". "OK" gives the
 * user nothing to check their intent against.
 */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  consequence,
  confirmLabel,
  onConfirm,
  loading,
  tone = "danger",
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  consequence: React.ReactNode;
  confirmLabel: string;
  onConfirm: () => void;
  loading?: boolean;
  tone?: "danger" | "primary";
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent title={title} size="sm">
        <div className="text-sm leading-relaxed text-text-muted">{consequence}</div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button variant={tone} loading={loading} onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
