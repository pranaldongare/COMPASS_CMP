/**
 * The shape of a help manual: sections of blocks, written as data so the page
 * that renders them can number, search and filter them without knowing what
 * they say.
 *
 * In text, `[[Label]]` marks the words of a control or a heading as it appears
 * on screen - a button, a field, a page - and is rendered as a label chip, so a
 * reader can match the instruction to the screen at a glance.
 */

export type HelpBlock =
  | { kind: "p"; text: string }
  | { kind: "steps"; title?: string; items: string[] }
  | { kind: "list"; title?: string; items: string[] }
  | { kind: "note" | "tip" | "warning"; title?: string; text: string }
  | { kind: "faq"; items: { q: string; a: string }[] }
  | { kind: "terms"; items: { term: string; meaning: string }[] };

export interface HelpSection {
  /** The anchor: `/help#<id>` opens the manual at this section. */
  id: string;
  title: string;
  /** One sentence under the heading, and the line the contents list shows. */
  summary: string;
  /** Roles the section is written for. Absent: everybody. */
  roles?: string[];
  blocks: HelpBlock[];
}

export interface RoleOption {
  value: string;
  label: string;
}
