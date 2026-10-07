/** A notice template as the API returns one, for tests (0044). */
import type { NoticeTemplateDetail } from "@/types";

export function makeTemplate(over: Partial<NoticeTemplateDetail> = {}): NoticeTemplateDetail {
  return {
    template_uuid: "51515151-5151-4151-8151-515151515151",
    template_code: "TPL-0007",
    title: "Gait video studies, adults",
    withdraw_url: "https://example.org/withdraw",
    exercise_rights_url: "https://example.org/rights",
    board_complaint_url: "https://example.org/board",
    dpo_contact: "dpo@example.org",
    applicable_to: "data_subject",
    note: null,
    status: "active",
    created_by_name: "Dee Pee",
    created_at: "2026-10-07T09:00:00Z",
    updated_at: "2026-10-07T09:00:00Z",
    retired_at: null,
    purpose_count: 1,
    language_count: 1,
    used_count: 0,
    purposes: [
      {
        purpose_uuid: "61616161-6161-4161-8161-616161616161",
        purpose_code: "P-GAIT",
        name: "Gait model training",
        status: "active",
        lawful_basis: "consent_s6",
        data_categories: ["gait_video"],
        display_order: 0,
        is_mandatory: true,
      },
    ],
    languages: [
      {
        language_code: "english",
        rendered_text: "We collect your gait video.",
        updated_at: "2026-10-07T09:00:00Z",
        updated_by_name: "Dee Pee",
      },
    ],
    notices: [],
    ...over,
  };
}
