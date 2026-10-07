/** Reading notice templates (0044). */
"use client";

import { useQuery } from "@tanstack/react-query";

import {
  findNoticeTemplate,
  getNoticeTemplate,
  listNoticeTemplates,
} from "@/features/notice-templates/api";
import type { ApiError } from "@/lib/errors";
import { keys } from "@/lib/query";
import type { NoticeTemplate, NoticeTemplateDetail, NoticeTemplateFound, Uuid } from "@/types";

export function useNoticeTemplates(
  filters: { status?: string; q?: string } = {},
  { enabled = true }: { enabled?: boolean } = {},
) {
  return useQuery<NoticeTemplate[], ApiError>({
    queryKey: keys.noticeTemplate.list(filters),
    queryFn: () => listNoticeTemplates(filters),
    enabled,
  });
}

export function useNoticeTemplate(uuid: Uuid | undefined) {
  return useQuery<NoticeTemplateDetail, ApiError>({
    queryKey: keys.noticeTemplate.detail(uuid ?? ""),
    queryFn: () => getNoticeTemplate(uuid!),
    enabled: Boolean(uuid),
  });
}

/** A template by the ID somebody was given; only once they ask. */
export function useFindNoticeTemplate(code: string | null) {
  const normalised = (code ?? "").trim().toUpperCase();
  return useQuery<NoticeTemplateFound, ApiError>({
    queryKey: keys.noticeTemplate.byCode(normalised),
    queryFn: () => findNoticeTemplate(normalised),
    enabled: normalised.length >= 3,
    retry: false,
  });
}
