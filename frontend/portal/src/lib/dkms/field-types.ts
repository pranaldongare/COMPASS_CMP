/**
 * Which data type each personal field was sealed as.
 *
 * The walker prefers to read the type off the envelope - byte 3 of every
 * `SE::` value says it, so a page needs to know nothing about its own
 * fields. That only works for a key service that writes *this* envelope.
 * A different one, sealing the same data under the same contract, produces
 * a blob this portal cannot label, and a value it cannot label is a value
 * it used to skip in silence: the page rendered `SE::…` where a name should
 * be, with nothing anywhere saying why.
 *
 * So this is the fallback: the field's own name. It is a mirror of
 * `ENCRYPTED_FIELDS` in `cmp.infrastructure.dkms.fields`, where the column
 * and its type are declared, and it holds because no column name in that
 * map carries two different types - a check the backend's
 * `test_dkms_field_map` keeps true.
 *
 * Two names are deliberately absent. `name` and `contact` are a
 * respondent's on one table and a purpose's, a queue's or a form field's
 * everywhere else; labelling every `name` in every response as a person's
 * would send a purpose's name to be decrypted. Those are read from the
 * envelope or not at all.
 */

import type { DataType } from "@/lib/dkms/api";

export const TYPE_BY_FIELD: Readonly<Record<string, DataType>> = {
  body: "FREE_TEXT",
  decision_reason: "FREE_TEXT",
  dob: "DOB",
  email: "EMAIL",
  evidence_name: "FILE_NAME",
  file_name: "FILE_NAME",
  full_name: "NAME",
  instruction: "FREE_TEXT",
  ip_address: "IP",
  mobile: "MOBILE",
  nominee_email: "EMAIL",
  nominee_mobile: "MOBILE",
  nominee_name: "NAME",
  organization_id: "ORG_ID",
  reason: "FREE_TEXT",
  refusal_reason: "FREE_TEXT",
  remedy_text: "FREE_TEXT",
  request_text: "FREE_TEXT",
  responder_contact: "CONTACT",
  responder_name: "NAME",
  response_text: "FREE_TEXT",
  return_summary: "FREE_TEXT",
  secondary_email: "EMAIL",
  sent_back_reason: "FREE_TEXT",
  submitted_contact: "CONTACT",
  submitted_name: "NAME",
  username: "NAME",
  verification_note: "FREE_TEXT",

  // Joined names and contacts: the same person's value, read through a
  // foreign key, under the name the response gives it.
  actor_name: "NAME",
  author_name: "NAME",
  changed_by_name: "NAME",
  confirmed_by_name: "NAME",
  created_by_name: "NAME",
  dco_name: "NAME",
  decided_by_name: "NAME",
  delegate_email: "EMAIL",
  delegate_name: "NAME",
  delegator_email: "EMAIL",
  delegator_name: "NAME",
  exported_by_name: "NAME",
  imported_by_name: "NAME",
  nominee_contact: "CONTACT",
  overridden_by_name: "NAME",
  owner_name: "NAME",
  principal_name: "NAME",
  responder_user_email: "EMAIL",
  responder_user_name: "NAME",
  reviewer_name: "NAME",
  subject_email: "EMAIL",
  subject_mobile: "MOBILE",
  subject_name: "NAME",
  updated_by_name: "NAME",
  uploaded_by_name: "NAME",
  verified_by_name: "NAME",
};
