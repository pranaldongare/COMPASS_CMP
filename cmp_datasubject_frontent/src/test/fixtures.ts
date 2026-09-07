/**
 * Fixtures shaped like real API responses.
 *
 * Written by hand against `src/types` rather than captured from a live server,
 * for a reason worth stating: a captured fixture is a snapshot of one moment,
 * and when the API changes it keeps passing while the application breaks.
 *
 * **Nothing here is cast.** A `as Project` would make this file compile against
 * a shape that no longer exists, which is exactly the failure the fixtures are
 * meant to catch. When the API renames a field, `npm run api:types` updates
 * `src/types`, and this file stops compiling — on purpose.
 *
 * Every factory takes an override object. A test that cares about one field
 * says so and nothing else; a test that spells out fifteen fields to exercise
 * one of them has buried its own subject.
 */

import type {
  Clock,
  ConsentListRow,
  Me,
  MyRequest,
  NoticeListRow,
  Page,
  Project,
  Purpose,
  RightsRequestDetail,
  RightsRequestRow,
  Role,
  User,
} from "@/types";

const NOW = "2026-02-02T11:05:00+05:30";

/**
 * The nav each role gets from the server. Mirrors the API's `NAV_BY_ROLE`.
 *
 * A copy, and a knowing one — the application never derives nav locally, but a
 * test needs a plausible `me` to render against, and one that claims a DCO can
 * see the audit trail would prove nothing. `tests/e2e/nav-coverage` checks the
 * real thing against the real server.
 */
const NAV: Record<Role, string[]> = {
  admin: [
    "dashboard", "users", "processors", "sources", "requests", "audit", "cover",
    "notifications", "profile",
  ],
  dpo: [
    "dashboard", "projects", "notices", "purposes", "processors", "sources",
    "consents", "links", "exports", "imports", "requests", "audit", "users",
    "cover", "notifications", "profile",
  ],
  rnd_user: ["dashboard", "projects", "notices", "consents", "notifications", "profile"],
  dco: [
    "dashboard", "projects", "sites", "sources", "consents", "links",
    "collections", "imports", "notifications", "profile",
  ],
  dco_admin: [
    "dashboard", "projects", "sites", "sources", "consents", "links",
    "collections", "imports", "notifications", "profile",
  ],
  rco: [
    "dashboard", "projects", "sites", "sources", "consents", "links",
    "collections", "imports", "notifications", "profile",
  ],
  data_subject: ["consents", "requests", "notifications", "profile"],
};

export function makeMe(overrides: Partial<Me> = {}): Me {
  const role = overrides.role ?? "admin";
  return {
    uuid: "11111111-1111-4111-8111-111111111111",
    full_name: "Asha Rao",
    email: "asha.rao@organisation.example",
    role,
    person_type: null,
    status: "active",
    // Unknown by default, which is the honest default: most accounts in this
    // system were created through a consent link that never asked. A test that
    // needs a child or an adult says so explicitly.
    dob: null,
    is_minor: null,
    mfa_verified: true,
    // An hour out, so a test that does not care about expiry never trips the
    // session warning. Tests that do care set this deliberately.
    session_expires_at: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
    nav: NAV[role],
    ...overrides,
  };
}

export function makeProject(overrides: Partial<Project> = {}): Project {
  return {
    project_uuid: "22222222-2222-4222-8222-222222222222",
    project_name: "Retail footfall study",
    internal_project_name: null,
    description: "Counts visitors at partner stores to size a loyalty programme.",
    requesting_team: "Consumer Insights",
    project_status: "in_draft",
    dco_uuid: null,
    dco_name: null,
    created_by_name: "Asha Rao",
    current_notice_uuid: null,
    created_at: NOW,
    updated_at: NOW,
    ...overrides,
  };
}

export function makePurpose(overrides: Partial<Purpose> = {}): Purpose {
  return {
    purpose_uuid: "33333333-3333-4333-8333-333333333333",
    purpose_code: "LOYALTY_ENROL",
    version: 1,
    status: "active",
    name: "Loyalty programme enrolment",
    description: "Enrolling a customer in the loyalty programme.",
    uses: "Issuing a membership number and applying member pricing at checkout.",
    lawful_basis: "consent_s6",
    s7_clause: null,
    data_categories: ["contact.name", "contact.email"],
    retention_period: "P3Y",
    retention_basis: "Membership term plus statutory retention.",
    erasure_trigger: "withdrawal",
    consent_validity_period: null,
    cross_border_permitted: false,
    permitted_for_minors: false,
    lapse_behaviour: "stop_processing",
    created_at: NOW,
    updated_at: NOW,
    ...overrides,
  };
}

export function makeUser(overrides: Partial<User> = {}): User {
  return {
    uuid: "44444444-4444-4444-8444-444444444444",
    username: null,
    full_name: "Vikram Nair",
    email: "vikram.nair@organisation.example",
    mobile: null,
    organization_id: null,
    role: "dco",
    person_type: null,
    status: "active",
    created_at: NOW,
    updated_at: NOW,
    ...overrides,
  };
}

export function makeNoticeRow(overrides: Partial<NoticeListRow> = {}): NoticeListRow {
  return {
    notice_uuid: "55555555-5555-4555-8555-555555555555",
    notice_code: "NOT-0001",
    version: 1,
    status: "draft",
    published_at: null,
    created_at: NOW,
    updated_at: NOW,
    project_uuid: "22222222-2222-4222-8222-222222222222",
    project_name: "Retail footfall study",
    purpose_count: 2,
    language_count: 3,
    unapproved_languages: 1,
    ...overrides,
  };
}

export function makeConsentRow(overrides: Partial<ConsentListRow> = {}): ConsentListRow {
  return {
    consent_uuid: "66666666-6666-4666-8666-666666666666",
    subject_uuid: "77777777-7777-4777-8777-777777777777",
    subject_name: "Meera Iyer",
    subject_email: "meera.iyer@example.com",
    subject_mobile: null,
    site_uuid: "88888888-8888-4888-8888-888888888888",
    site_label: "Bengaluru — Indiranagar",
    served_at: "2026-02-02T11:04:12+05:30",
    affirmative_action_at: NOW,
    action_type: "checkbox",
    is_withdrawal: false,
    consent_status: "consented",
    granted_count: 3,
    refused_count: 0,
    project_uuid: "22222222-2222-4222-8222-222222222222",
    project_name: "Retail footfall study",
    ...overrides,
  };
}

/* ==========================================================================
   Rights requests
   ========================================================================== */

const RECEIVED = "2026-09-01T09:00:00+05:30";
const DUE = "2026-11-30T09:00:00+05:30";

/** The clock as the server returns it: every checkpoint laid out, nothing derived here. */
export function makeClock(overrides: Partial<Clock> = {}): Clock {
  return {
    received_at: RECEIVED,
    due_at: DUE,
    acknowledge_by: "2026-09-03T09:00:00+05:30",
    tickets_by: "2026-09-06T09:00:00+05:30",
    halfway_at: "2026-10-16T09:00:00+05:30",
    collate_by: "2026-11-25T09:00:00+05:30",
    days_remaining: 90,
    overdue: false,
    at_risk: false,
    progress: 0,
    checkpoints: [
      { key: "received", label: "Received", at: RECEIVED, passed: true },
      { key: "acknowledge", label: "Acknowledge", at: "2026-09-03T09:00:00+05:30", passed: false },
      { key: "tickets", label: "Tickets issued", at: "2026-09-06T09:00:00+05:30", passed: false },
      { key: "halfway", label: "Halfway", at: "2026-10-16T09:00:00+05:30", passed: false },
      { key: "collate", label: "Collate", at: "2026-11-25T09:00:00+05:30", passed: false },
      { key: "due", label: "Respond", at: DUE, passed: false },
    ],
    next_checkpoint: "acknowledge",
    ...overrides,
  };
}

export function makeRequestRow(overrides: Partial<RightsRequestRow> = {}): RightsRequestRow {
  return {
    request_uuid: "99999999-9999-4999-8999-999999999999",
    reference: "RR-2026-000001",
    request_type: "access",
    original_type: null,
    status: "received",
    outcome: null,
    channel: "portal",
    subject_uuid: "77777777-7777-4777-8777-777777777777",
    subject_name: "Meera Iyer",
    submitted_name: "Meera Iyer",
    submitted_contact: "meera.iyer@example.com",
    received_at: RECEIVED,
    due_at: DUE,
    acknowledged_at: RECEIVED,
    verification_status: "verified",
    about_dpo: false,
    linked_reference: null,
    holder_count: 0,
    tickets_outstanding: 0,
    closed_at: null,
    clock: makeClock(),
    ...overrides,
  };
}

/** The DPO's full view. Fresh, verified, not yet classified. */
export function makeRequestDetail(overrides: Partial<RightsRequestDetail> = {}): RightsRequestDetail {
  return {
    ...makeRequestRow(),
    request_text: "What do you hold about me, and who has it?",
    subject_email: "meera.iyer@example.com",
    subject_mobile: null,
    verification_method: "session",
    verified_at: RECEIVED,
    verified_by_name: null,
    verification_note: null,
    classified_at: null,
    refusal_reason: null,
    intent_confirmed_at: null,
    linked_request_uuid: null,
    linked_request_type: null,
    nomination_uuid: null,
    nominee_name: null,
    nominee_contact: null,
    trigger_event: null,
    trigger_evidence_hash: null,
    trigger_evidenced_at: null,
    reviewer_uuid: null,
    reviewer_name: null,
    escalated_at: null,
    grievance_upheld: null,
    remedy_text: null,
    response_text: null,
    response_file_hash: null,
    responded_at: null,
    download_expires_at: null,
    created_at: RECEIVED,
    updated_at: RECEIVED,
    holders_confirmed: 0,
    tickets_issued: 0,
    tickets_returned: 0,
    item_count: 0,
    items_undecided: 0,
    holders: [],
    items: [],
    transitions: [],
    ...overrides,
  };
}

/** Her own view: what she is entitled to see, and nothing that is ours. */
export function makeMyRequest(overrides: Partial<MyRequest> = {}): MyRequest {
  return {
    request_uuid: "99999999-9999-4999-8999-999999999999",
    reference: "RR-2026-000001",
    request_type: "access",
    status: "received",
    outcome: null,
    channel: "portal",
    request_text: "What do you hold about me, and who has it?",
    received_at: RECEIVED,
    due_at: DUE,
    acknowledged_at: RECEIVED,
    verification_status: "verified",
    responded_at: null,
    response_text: null,
    refusal_reason: null,
    remedy_text: null,
    grievance_upheld: null,
    download_available: false,
    download_expires_at: null,
    linked_reference: null,
    closed_at: null,
    clock: makeClock(),
    ...overrides,
  };
}

/**
 * A page of results.
 *
 * `next_cursor` defaults to null — one page, no more. A test for pagination
 * has to set it, and by having to set it, says out loud that pagination is
 * what it is about.
 */
export function makePage<T>(
  items: T[],
  { nextCursor = null, total = null }: { nextCursor?: string | null; total?: number | null } = {},
): Page<T> {
  return { items, next_cursor: nextCursor, total };
}
