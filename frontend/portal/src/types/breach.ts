/**
 * A notice about a personal data breach, as written to her account (Rule 7(1)).
 *
 * The five things the Rule requires, in its order, and the breach's reference
 * to quote when she asks about it.
 */
import type { Timestamp, Uuid } from "@/types/primitives";

export interface MyBreachNotice {
  notice_uuid: Uuid;
  reference: string;
  /** A later version is an update, sent when the facts changed. */
  version: number;
  what_happened: string;
  consequences: string;
  measures: string;
  protective_steps: string;
  contact: string;
  delivered_at: Timestamp;
}
