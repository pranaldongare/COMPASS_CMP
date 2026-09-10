/**
 * Reading the message catalogue.
 */
"use client";

import { useQuery } from "@tanstack/react-query";

import { listMessages } from "@/features/messages/api";
import type { ApiError } from "@/lib/errors";
import { keys } from "@/lib/query";
import type { MessageTemplate } from "@/types";

export function useMessages() {
  return useQuery<MessageTemplate[], ApiError>({
    queryKey: keys.messages.all,
    queryFn: listMessages,
  });
}
