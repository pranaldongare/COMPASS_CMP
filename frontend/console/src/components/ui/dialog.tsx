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

/** Tells the dialog around it that what was typed has been dealt with:
 *  everything, or what was typed in one named part of it. */
type Saved = (part?: string) => void;
/** Marks a part of a dialog that finishes on its own (`useDialogPart`). */
const PART = "data-dialog-part";
/** Tells it that closing would lose something that is not typing, and why. */
type Hold = (reason: string | null) => void;
const DialogContext = React.createContext<{ saved: Saved; hold: Hold }>({
  saved: () => {},
  hold: () => {},
});

/**
 * For a dialog whose whole content is saved while it stays open - a wizard
 * that ends on a "created" panel: call it once the save succeeds, and closing
 * the dialog no longer asks about typing that is already saved. A form that
 * shares its dialog with others uses `useDialogPart`, and answers only for
 * itself. Outside a dialog it does nothing.
 */
export function useDialogSaved(): Saved {
  return React.useContext(DialogContext).saved;
}

/**
 * For a form that finishes and leaves the dialog open, beside other things
 * somebody may be typing in - a message sent on a thread, a respondent added,
 * a move made with a reason: spread `part` on the form's element, and call
 * `done()` once its save succeeds or its own Cancel gives it up. Closing the
 * dialog then no longer asks about what was typed in that form, and still
 * asks about anything typed outside it: a message sent does not answer for a
 * reason half-typed beside it.
 */
export function useDialogPart(): { part: { [PART]: string }; done: () => void } {
  const id = React.useId();
  const { saved } = React.useContext(DialogContext);
  const done = React.useCallback(() => saved(id), [saved, id]);
  return { part: { [PART]: id }, done };
}

/**
 * For something closing would lose that nobody typed - a link shown once and
 * never again. While `reason` is given, closing the dialog by Escape, a click
 * outside or its X asks first, in those words, and not as "changes that are
 * not saved", which it is not. The content's own button closes as it always
 * did. Outside a dialog it does nothing.
 */
export function useDialogHold(reason: string | null): void {
  const { hold } = React.useContext(DialogContext);
  React.useEffect(() => {
    hold(reason);
    return () => hold(null);
  }, [hold, reason]);
}

/** The same, for a dialog's owner, which sits outside it: render it inside
 *  the dialog and bump `count` after each save. With `part`, only what was
 *  typed inside the element carrying `data-dialog-part` of that name. */
export function DialogSaved({ count, part }: { count: number; part?: string }) {
  const saved = useDialogSaved();
  React.useEffect(() => {
    if (count > 0) saved(part);
  }, [count, part, saved]);
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
  // opens, so this starts empty every time. A dialog nobody has typed in
  // closes as it always did; one somebody has asks before its typing is
  // thrown away (UX review 2026-10-05: a project draft vanished on Escape).
  // A form's own Cancel, and a save that closes it, are not dismissals and do
  // not ask. A save that keeps it open - a message sent on a thread - says so
  // through `useDialogSaved`, and typing after it starts the question again.
  //
  // Kept as the fields typed in, each with the part of the dialog it sits in,
  // not as one flag (2026-11-12), so a form can answer for its own: a message
  // sent used to clear a reason half-typed beside it. Nothing is inferred
  // from a field emptying or going away - a wizard's earlier step and an
  // address added to a list not yet saved look exactly like finished work,
  // and are not.
  const typed = React.useRef(new Map<Element, string | null>());
  // What closing is being asked about, while it is: typing not saved, or
  // something the content says would be lost (`useDialogHold`).
  const [asking, setAsking] = React.useState<"unsaved" | "held" | null>(null);
  const markSaved = React.useCallback<Saved>((part) => {
    if (part === undefined) {
      typed.current.clear();
    } else {
      for (const [field, within] of typed.current) if (within === part) typed.current.delete(field);
    }
    if (typed.current.size === 0) setAsking((now) => (now === "unsaved" ? null : now));
  }, []);
  const [held, setHeld] = React.useState<string | null>(null);
  const context = React.useMemo(() => ({ saved: markSaved, hold: setHeld }), [markSaved]);
  const guard = (event: { preventDefault: () => void }) => {
    // Unsaved typing is the stronger reason, and is said first.
    const unsaved = typed.current.size > 0;
    if (!unsaved && !held) return;
    event.preventDefault();
    setAsking(unsaved ? "unsaved" : "held");
  };
  // Nothing left to lose: the question goes with its reason.
  const question = asking === "held" && !held ? null : asking;
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
          if (event.target instanceof Element) {
            const part = event.target.closest(`[${PART}]`)?.getAttribute(PART) ?? null;
            typed.current.set(event.target, part);
          }
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

        {question && (
          <div
            role="alert"
            className="flex flex-wrap items-center justify-between gap-2 border-b border-warning-border bg-warning-subtle px-5 py-3 text-sm text-warning-text"
          >
            <span>{question === "unsaved" ? "You have changes that are not saved." : held}</span>
            <span className="flex gap-2">
              <Button variant="secondary" size="sm" onClick={() => setAsking(null)}>
                {question === "unsaved" ? "Keep editing" : "Stay"}
              </Button>
              <DialogPrimitive.Close asChild>
                <Button variant="danger" size="sm">
                  {question === "unsaved" ? "Discard changes" : "Close anyway"}
                </Button>
              </DialogPrimitive.Close>
            </span>
          </div>
        )}

        <div className="px-5 py-4">
          <DialogContext.Provider value={context}>{children}</DialogContext.Provider>
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
