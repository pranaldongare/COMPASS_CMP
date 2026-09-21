/**
 * Editing the words of the messages the platform sends.
 *
 * Four calls. Saving replaces the subject and body for one message on one
 * channel; resetting deletes the replacement so the default is sent again;
 * preview renders any words with sample values without saving them. Nothing
 * here can add a message - that is a code change, and the list is the
 * server's.
 */

import { apiDelete, apiGet, apiPost, apiPut } from "@/lib/api";
import type {
  MessageChannel,
  MessagePreview,
  MessageTemplate,
  MessageTemplateInput,
} from "@/types";

export function listMessages(): Promise<MessageTemplate[]> {
  return apiGet<MessageTemplate[]>("/messages");
}

export function saveMessage(
  key: string,
  channel: MessageChannel,
  input: MessageTemplateInput,
): Promise<MessageTemplate> {
  return apiPut<MessageTemplate>(`/messages/${key}/${channel}`, input);
}

export function resetMessage(
  key: string,
  channel: MessageChannel,
): Promise<MessageTemplate> {
  return apiDelete<MessageTemplate>(`/messages/${key}/${channel}`);
}

export function previewMessage(
  key: string,
  channel: MessageChannel,
  input: MessageTemplateInput,
): Promise<MessagePreview> {
  return apiPost<MessagePreview>(`/messages/${key}/${channel}/preview`, input);
}
