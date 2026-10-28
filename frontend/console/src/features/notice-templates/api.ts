/**
 * Notice templates (0044): the DPO's notices before there is a project.
 *
 * Written, edited and retired by the DPO. Looked up by its ID - `TPL-0007` -
 * by whoever brings a notice to a project, and attached there, which copies it
 * into that project's own draft notice.
 */

import { apiDelete, apiGet, apiPatch, apiPost, apiPut, queryString } from "@/lib/api";
import type {
  LanguageCode,
  Notice,
  NoticeAudience,
  NoticeTemplate,
  NoticeTemplateDetail,
  NoticeTemplateFound,
  TemplateVersion,
  TemplateVersionDetail,
  TemplateVersionPreview,
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
  /** The category of a Legal office template (0052); none for the DPO's. */
  category_uuid?: Uuid | null;
}

const base = (uuid: Uuid) => `/notice-templates/${uuid}`;

export function listNoticeTemplates(
  filters: { status?: string; q?: string; category?: string } = {},
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
  body: Partial<
    Omit<NoticeTemplateInput, "rendered_text" | "language_code" | "category_uuid">
  >,
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

// ------------------------------------------------------------------ versions
//
// A Legal office template's versions (0053, ADR 0033): the legal text Legal
// approves once. A DPO office template has none.

export interface VersionInput {
  reconsent_required?: boolean;
  slot_guidance?: string | null;
  slot_max_length?: number;
  withdraw_url?: string;
  exercise_rights_url?: string;
  board_complaint_url?: string;
  dpo_contact?: string;
  applicable_to?: NoticeAudience | null;
}

const versionsOf = (uuid: Uuid) => `${base(uuid)}/versions`;

export function listTemplateVersions(uuid: Uuid): Promise<TemplateVersion[]> {
  return apiGet<TemplateVersion[]>(versionsOf(uuid));
}

export function getTemplateVersion(uuid: Uuid, n: number): Promise<TemplateVersionDetail> {
  return apiGet<TemplateVersionDetail>(`${versionsOf(uuid)}/${n}`);
}

/** The next version, as a draft carrying what the last one said. */
export function openTemplateVersion(uuid: Uuid): Promise<TemplateVersionDetail> {
  return apiPost<TemplateVersionDetail>(versionsOf(uuid), {});
}

export function updateTemplateVersion(
  uuid: Uuid,
  n: number,
  body: VersionInput,
): Promise<TemplateVersionDetail> {
  return apiPatch<TemplateVersionDetail>(`${versionsOf(uuid)}/${n}`, body);
}

export function setVersionLanguage(
  uuid: Uuid,
  n: number,
  code: LanguageCode,
  lockedText: string,
): Promise<TemplateVersionDetail> {
  return apiPut<TemplateVersionDetail>(`${versionsOf(uuid)}/${n}/languages/${code}`, {
    locked_text: lockedText,
  });
}

export function removeVersionLanguage(
  uuid: Uuid,
  n: number,
  code: LanguageCode,
): Promise<TemplateVersionDetail> {
  return apiDelete<TemplateVersionDetail>(`${versionsOf(uuid)}/${n}/languages/${code}`);
}

/** The whole list, in order. */
export function setVersionPurposes(
  uuid: Uuid,
  n: number,
  purposes: { purpose_uuid: Uuid; is_mandatory: boolean }[],
): Promise<TemplateVersionDetail> {
  return apiPut<TemplateVersionDetail>(`${versionsOf(uuid)}/${n}/purposes`, { purposes });
}

export function approveTemplateVersion(uuid: Uuid, n: number): Promise<TemplateVersionDetail> {
  return apiPost<TemplateVersionDetail>(`${versionsOf(uuid)}/${n}/approve`, {});
}

export function retireTemplateVersion(uuid: Uuid, n: number): Promise<TemplateVersionDetail> {
  return apiPost<TemplateVersionDetail>(`${versionsOf(uuid)}/${n}/status`, {
    status: "retired",
  });
}

export function previewTemplateVersion(
  uuid: Uuid,
  n: number,
  description: string,
): Promise<TemplateVersionPreview[]> {
  return apiGet<TemplateVersionPreview[]>(
    `${versionsOf(uuid)}/${n}/preview${queryString({ description: description || undefined })}`,
  );
}
