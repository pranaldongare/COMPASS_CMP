/**
 * The words of every message the platform sends.
 *
 * A *message* here is a junction: a moment at which the platform writes to a
 * person. Each has the channels it travels on, the variables its text may use,
 * the default words, and the words in force if the office replaced them. The
 * list is the server's and is complete by construction - a junction the code
 * can send is a junction that appears here.
 */

import type { Timestamp } from "@/types/primitives";

export type MessageChannel = "email" | "sms";

export interface MessageVariable {
  name: string;
  description: string;
  /** Used by the preview so the editor sees a real-looking message. */
  sample: string;
}

export interface MessageChannelTemplate {
  channel: MessageChannel;
  /** Null for SMS, which has no subject. */
  default_subject: string | null;
  default_body: string;
  /** The words in force: the office's if set, else the default. */
  subject: string | null;
  body: string;
  customised: boolean;
  updated_at: Timestamp | null;
  updated_by_name: string | null;
}

export interface MessageTemplate {
  key: string;
  title: string;
  description: string;
  group: string;
  variables: MessageVariable[];
  channels: MessageChannelTemplate[];
}

export interface MessagePreview {
  channel: MessageChannel;
  subject: string | null;
  body: string;
}

export interface MessageTemplateInput {
  /** Required for email; must be absent for SMS. The server says which. */
  subject?: string | null;
  body: string;
}
