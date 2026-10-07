/**
 * Notice templates (0044): the DPO's notices before there is a project.
 *
 * Written, edited and retired by the DPO. Looked up by its ID - `TPL-0007` -
 * by whoever brings a notice to a project, and attached there, which copies it
 * into that project's own draft notice.
 */

import { apiDelete, apiGet, apiPost, apiPut, queryString } from "@/lib/api";
import type {
  LanguageCode,
  Notice,
  NoticeAudience,
  NoticeTemplate,
  NoticeTemplateDetail,
  NoticeTemplateFound,
  Uuid,
} from "@/types";

export interface NoticeTemplateInput {
  title: string;
  withdraw_url: string;
  exercise_rights_url: string;
  board_complaint_url: string;
  dpo_contact: string;
  applicable_to?: NoticeAudience | null;
  note?: string | null;
  rendered_text?: string | null;
  language_code?: LanguageCode | null;
}

const base = (uuid: Uuid) => `/notice-templates/${uuid}`;

export function listNoticeTemplates(
  filters: { status?: string; q?: string } = {},
): Promise<NoticeTemplate[]> {
  return apiGet<NoticeTemplate[]>(`/notice-templates${queryString(filters)}`);
}

export function getNoticeTemplate(uuid: Uuid): Promise<NoticeTemplateDetail> {
  return apiGet<NoticeTemplateDetail>(base(uuid));
}

/** By the ID the DPO gave out. Case and spacing are forgiven by the server. */
export function findNoticeTemplate(code: string): Promise<NoticeTemplateFound> {
  return apiGet<NoticeTemplateFound>(
    `/notice-templates/by-code/${encodeURIComponent(code.trim())}`,
  );
}

export function createNoticeTemplate(body: NoticeTemplateInput): Promise<NoticeTemplateDetail> {
  return apiPost<NoticeTemplateDetail>("/notice-templates", body);
}

export function updateNoticeTemplate(
  uuid: Uuid,
  body: Partial<Omit<NoticeTemplateInput, "rendered_text" | "language_code">>,
): Promise<NoticeTemplateDetail> {
  return apiPut<NoticeTemplateDetail>(base(uuid), body);
}

export function setNoticeTemplateStatus(
  uuid: Uuid,
  status: "active" | "retired",
): Promise<NoticeTemplateDetail> {
  return apiPost<NoticeTemplateDetail>(`${base(uuid)}/status`, { status });
}

export function attachTemplatePurpose(
  uuid: Uuid,
  body: { purpose_uuid: Uuid; is_mandatory?: boolean; display_order?: number },
): Promise<NoticeTemplateDetail> {
  return apiPost<NoticeTemplateDetail>(`${base(uuid)}/purposes`, body);
}

export function detachTemplatePurpose(
  uuid: Uuid,
  purposeUuid: Uuid,
): Promise<NoticeTemplateDetail> {
  return apiDelete<NoticeTemplateDetail>(`${base(uuid)}/purposes/${purposeUuid}`);
}

export function setTemplateLanguage(
  uuid: Uuid,
  code: LanguageCode,
  renderedText: string,
): Promise<NoticeTemplateDetail> {
  return apiPut<NoticeTemplateDetail>(`${base(uuid)}/languages/${code}`, {
    rendered_text: renderedText,
  });
}

export function removeTemplateLanguage(
  uuid: Uuid,
  code: LanguageCode,
): Promise<NoticeTemplateDetail> {
  return apiDelete<NoticeTemplateDetail>(`${base(uuid)}/languages/${code}`);
}

/** Make a project's draft notice from a template, by its ID. */
export function noticeFromTemplate(projectUuid: Uuid, templateCode: string): Promise<Notice> {
  return apiPost<Notice>(`/projects/${projectUuid}/notices/from-template`, {
    template_code: templateCode.trim(),
  });
}
