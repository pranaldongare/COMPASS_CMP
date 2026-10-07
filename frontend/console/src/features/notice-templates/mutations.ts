/**
 * Writing notice templates (0044). Every write answers with the whole
 * template, which goes straight into the detail cache; lists refresh.
 * Attaching one to a project makes a notice, so the notice views refresh too.
 */
"use client";

import { useMutation, useQueryClient, type QueryClient } from "@tanstack/react-query";

import * as api from "@/features/notice-templates/api";
import { effects, keys, type Result } from "@/lib/query";
import type { LanguageCode, Notice, NoticeTemplateDetail, Uuid } from "@/types";

function settle(qc: QueryClient, template: NoticeTemplateDetail) {
  qc.setQueryData(keys.noticeTemplate.detail(template.template_uuid), template);
  void qc.invalidateQueries({ queryKey: ["notice-templates"] });
  void qc.invalidateQueries({ queryKey: ["notice-template", "code"] });
}

export function useCreateNoticeTemplate(): Result<NoticeTemplateDetail, api.NoticeTemplateInput> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.createNoticeTemplate,
    onSuccess: (t) => settle(qc, t),
  });
}

export function useUpdateNoticeTemplate(
  uuid: Uuid,
): Result<NoticeTemplateDetail, Parameters<typeof api.updateNoticeTemplate>[1]> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => api.updateNoticeTemplate(uuid, body),
    onSuccess: (t) => settle(qc, t),
  });
}

export function useSetNoticeTemplateStatus(
  uuid: Uuid,
): Result<NoticeTemplateDetail, "active" | "retired"> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (status) => api.setNoticeTemplateStatus(uuid, status),
    onSuccess: (t) => settle(qc, t),
  });
}

export function useAttachTemplatePurpose(
  uuid: Uuid,
): Result<NoticeTemplateDetail, { purpose_uuid: Uuid; is_mandatory?: boolean }> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => api.attachTemplatePurpose(uuid, body),
    onSuccess: (t) => settle(qc, t),
  });
}

export function useDetachTemplatePurpose(uuid: Uuid): Result<NoticeTemplateDetail, Uuid> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (purposeUuid) => api.detachTemplatePurpose(uuid, purposeUuid),
    onSuccess: (t) => settle(qc, t),
  });
}

export function useSetTemplateLanguage(
  uuid: Uuid,
): Result<NoticeTemplateDetail, { language_code: LanguageCode; rendered_text: string }> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ language_code, rendered_text }) =>
      api.setTemplateLanguage(uuid, language_code, rendered_text),
    onSuccess: (t) => settle(qc, t),
  });
}

export function useRemoveTemplateLanguage(uuid: Uuid): Result<NoticeTemplateDetail, LanguageCode> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (code) => api.removeTemplateLanguage(uuid, code),
    onSuccess: (t) => settle(qc, t),
  });
}

export function useNoticeFromTemplate(projectUuid: Uuid): Result<Notice, string> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (code) => api.noticeFromTemplate(projectUuid, code),
    onSuccess: () => {
      effects.noticesChanged(qc, projectUuid);
      void qc.invalidateQueries({ queryKey: ["notice-templates"] });
    },
  });
}
