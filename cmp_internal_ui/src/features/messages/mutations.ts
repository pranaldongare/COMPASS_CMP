/**
 * Replacing, resetting and previewing the words of a message.
 *
 * Save and reset return the whole message with the words now in force, and
 * the list is invalidated so every card agrees. Preview writes nothing and is
 * a mutation only because it carries a body.
 */
"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { previewMessage, resetMessage, saveMessage } from "@/features/messages/api";
import { keys, type Result } from "@/lib/query";
import type {
  MessageChannel,
  MessagePreview,
  MessageTemplate,
  MessageTemplateInput,
} from "@/types";

export interface MessageEdit {
  key: string;
  channel: MessageChannel;
  input: MessageTemplateInput;
}

export interface MessageReset {
  key: string;
  channel: MessageChannel;
}

export function useSaveMessage(): Result<MessageTemplate, MessageEdit> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ key, channel, input }: MessageEdit) => saveMessage(key, channel, input),
    onSuccess: () => void qc.invalidateQueries({ queryKey: keys.messages.all }),
  });
}

export function useResetMessage(): Result<MessageTemplate, MessageReset> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ key, channel }: MessageReset) => resetMessage(key, channel),
    onSuccess: () => void qc.invalidateQueries({ queryKey: keys.messages.all }),
  });
}

export function usePreviewMessage(): Result<MessagePreview, MessageEdit> {
  return useMutation({
    mutationFn: ({ key, channel, input }: MessageEdit) =>
      previewMessage(key, channel, input),
  });
}
