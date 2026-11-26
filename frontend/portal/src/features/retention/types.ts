/**
 * The words of a retention answer (ADR 0047), the same in the console and on
 * the portal: the one asked answers in the console, an outside processor by
 * its link on the portal, with one form.
 */

export type ReviewKind = "validity" | "retention";
export type Outcome = "erased" | "anonymised" | "kept" | "not_held" | "reviewed";

export interface RetentionAnswer {
  outcome?: Outcome | null;
  reason?: string | null;
  keep_until?: string | null;
  reconsent?: boolean | null;
}
