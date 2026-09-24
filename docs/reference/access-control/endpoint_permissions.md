# Endpoint-by-endpoint permission matrix

[Guide](README.md) · [Detailed module entries](module_permissions.md)

**Legend:** `NO` = role cannot complete the operation; `YES` = eligible role (normal validation still applies); `ALL` = all rows within the named resource, not an administrator wildcard; `OWN` = own account or own-created project; `SCOPED` = assigned/project/site or about-DPO scope; `COND` = special conditions described in the module entry; `PUBLIC` = endpoint does not require a role. Anonymous `COND` means a link/code/capability is required, not a session role. These are implemented role eligibility and row scopes, not promises of success for invalid records or lifecycle states.

Roles refer to the **effective session role**. A staff account signed in through the portal OTP flow acts as `data_subject`. Ordinary staff sessions cannot use principal-only endpoints. The account itself retains its staff role.

## Audit

[Conditions and source evidence](modules/audit.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/audit` | NO | ALL | ALL | NO | NO | NO | NO | NO |
| GET | `/audit/verify` | NO | ALL | ALL | NO | NO | NO | NO | NO |
| GET | `/audit/summary` | NO | ALL | ALL | NO | NO | NO | NO | NO |
| GET | `/audit/vocabulary` | NO | ALL | ALL | NO | NO | NO | NO | NO |
| GET | `/audit/lookup` | NO | ALL | ALL | NO | NO | NO | NO | NO |
| GET | `/audit/export.csv` | NO | ALL | ALL | NO | NO | NO | NO | NO |
| GET | `/audit/{log_uuid}` | NO | ALL | ALL | NO | NO | NO | NO | NO |

## Auth

[Conditions and source evidence](modules/auth.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| POST | `/auth/login` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |
| POST | `/auth/logout` | NO | OWN | OWN | OWN | OWN | OWN | OWN | OWN |
| GET | `/auth/me` | NO | OWN | OWN | OWN | OWN | OWN | OWN | OWN |
| POST | `/auth/mfa/resend` | NO | COND | COND | COND | COND | COND | COND | COND |
| POST | `/auth/mfa/verify` | NO | COND | COND | COND | COND | COND | COND | COND |
| POST | `/auth/otp/request` | YES | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |
| POST | `/auth/otp/verify` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |
| POST | `/auth/password/change` | NO | OWN | OWN | OWN | OWN | OWN | OWN | OWN |
| POST | `/auth/password/reset/confirm` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |
| POST | `/auth/password/reset/request` | YES | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |
| POST | `/auth/register` | YES | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |
| POST | `/auth/register/verify` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |
| GET | `/auth/sessions` | NO | OWN | OWN | OWN | OWN | OWN | OWN | OWN |
| DELETE | `/auth/sessions/{session_uuid}` | NO | OWN | OWN | OWN | OWN | OWN | OWN | OWN |

## Consent

[Conditions and source evidence](modules/consent.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/consents` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| GET | `/consents/{consent_uuid}` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| GET | `/consents/{consent_uuid}/assets` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| GET | `/consents/{consent_uuid}/grants` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| GET | `/links` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |
| GET | `/links/{link_uuid}` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |
| POST | `/links/{link_uuid}/remint` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |
| POST | `/links/{link_uuid}/revoke` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |
| GET | `/links/{link_uuid}/stats` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |
| GET | `/projects/{project_uuid}/consents` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| GET | `/projects/{project_uuid}/consents/summary` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| GET | `/projects/{project_uuid}/links` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |

## Cross-border transfers

[Conditions and source evidence](modules/cross_border_transfers.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/restricted-countries` | NO | ALL | ALL | NO | NO | NO | NO | NO |
| POST | `/restricted-countries` | NO | ALL | NO | NO | NO | NO | NO | NO |
| POST | `/restricted-countries/{country_uuid}/lift` | NO | ALL | NO | NO | NO | NO | NO | NO |

## Dashboard

[Conditions and source evidence](modules/dashboard.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/dashboard` | NO | COND | COND | COND | COND | COND | COND | COND |
| GET | `/notifications` | NO | COND | COND | COND | COND | COND | COND | COND |
| POST | `/notifications/{log_uuid}/resend` | NO | COND | NO | COND | NO | NO | NO | NO |

## Delegations

[Conditions and source evidence](modules/delegations.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/delegations` | NO | ALL | ALL | NO | NO | NO | NO | NO |
| GET | `/delegations/candidates` | NO | OWN | OWN | OWN | OWN | OWN | OWN | NO |
| POST | `/delegations` | NO | COND | COND | COND | NO | NO | NO | NO |
| GET | `/delegations/held` | NO | OWN | OWN | OWN | OWN | OWN | OWN | OWN |
| GET | `/delegations/mine` | NO | OWN | OWN | OWN | OWN | OWN | OWN | OWN |
| DELETE | `/delegations/{delegation_uuid}` | NO | COND | COND | COND | COND | COND | COND | NO |

## Exchange

[Conditions and source evidence](modules/exchange.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/assets/{asset_uuid}` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| GET | `/assets/{asset_uuid}/subjects` | NO | ALL | NO | SCOPED | NO | NO | NO | NO |
| GET | `/collections` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| GET | `/collections/{collection_uuid}` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| GET | `/collections/{collection_uuid}/assets` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| GET | `/collections/{collection_uuid}/exceptions` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| GET | `/exports` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |
| GET | `/exports/{export_uuid}` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |
| GET | `/exports/{export_uuid}/download` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |
| GET | `/exports/{export_uuid}/lines` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |
| GET | `/imports` | NO | COND | COND | COND | COND | COND | COND | COND |
| POST | `/imports` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |
| GET | `/imports/template` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |
| POST | `/imports/validate` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |
| GET | `/imports/{batch_uuid}` | NO | COND | COND | COND | COND | COND | COND | COND |
| GET | `/imports/{batch_uuid}/errors` | NO | COND | COND | COND | COND | COND | COND | COND |
| GET | `/projects/{project_uuid}/collections` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| GET | `/projects/{project_uuid}/exports` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |
| POST | `/projects/{project_uuid}/exports` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |

## Legal holds

[Conditions and source evidence](modules/legal_holds.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/legal-holds` | NO | ALL | NO | NO | NO | NO | NO | NO |
| POST | `/legal-holds` | NO | ALL | NO | NO | NO | NO | NO | NO |
| POST | `/legal-holds/{hold_uuid}/release` | NO | ALL | NO | NO | NO | NO | NO | NO |

## Me

[Conditions and source evidence](modules/me.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/me` | NO | OWN | OWN | OWN | OWN | OWN | OWN | OWN |
| PATCH | `/me` | NO | OWN | OWN | OWN | OWN | OWN | OWN | OWN |
| GET | `/me/consents` | NO | NO | NO | NO | NO | NO | NO | OWN |
| GET | `/me/consents/{consent_uuid}` | NO | NO | NO | NO | NO | NO | NO | OWN |
| GET | `/me/consents/{consent_uuid}/grants` | NO | NO | NO | NO | NO | NO | NO | OWN |
| GET | `/me/consents/{consent_uuid}/history` | NO | NO | NO | NO | NO | NO | NO | OWN |
| GET | `/me/consents/{consent_uuid}/notice` | NO | NO | NO | NO | NO | NO | NO | OWN |
| GET | `/me/consents/{consent_uuid}/trail` | NO | NO | NO | NO | NO | NO | NO | OWN |
| POST | `/me/consents/{consent_uuid}/withdraw` | NO | NO | NO | NO | NO | NO | NO | OWN |
| POST | `/me/contact/verify` | NO | OWN | OWN | OWN | OWN | OWN | OWN | OWN |
| POST | `/me/contacts/code` | NO | OWN | OWN | OWN | OWN | OWN | OWN | OWN |
| GET | `/me/disclosures` | NO | NO | NO | NO | NO | NO | NO | OWN |
| GET | `/me/nominations` | NO | NO | NO | NO | NO | NO | NO | OWN |
| POST | `/me/nominations` | NO | NO | NO | NO | NO | NO | NO | OWN |
| DELETE | `/me/nominations/{nomination_uuid}` | NO | NO | NO | NO | NO | NO | NO | OWN |
| GET | `/me/nominee-of` | NO | NO | NO | NO | NO | NO | NO | OWN |
| GET | `/me/notifications` | NO | NO | NO | NO | NO | NO | NO | OWN |
| POST | `/me/person-type` | NO | OWN | OWN | NO | NO | NO | NO | OWN |
| GET | `/me/requests` | NO | NO | NO | NO | NO | NO | NO | OWN |
| POST | `/me/requests` | NO | NO | NO | NO | NO | NO | NO | OWN |
| GET | `/me/requests/{request_uuid}` | NO | NO | NO | NO | NO | NO | NO | OWN |
| POST | `/me/requests/{request_uuid}/dispute` | NO | NO | NO | NO | NO | NO | NO | OWN |
| GET | `/me/requests/{request_uuid}/download` | NO | NO | NO | NO | NO | NO | NO | OWN |
| GET | `/me/requests/{request_uuid}/files/{file_uuid}` | NO | NO | NO | NO | NO | NO | NO | OWN |
| GET | `/me/requests/{request_uuid}/trail` | NO | NO | NO | NO | NO | NO | NO | OWN |
| DELETE | `/me/secondary-email` | NO | OWN | OWN | OWN | OWN | OWN | OWN | OWN |

## Messages

[Conditions and source evidence](modules/messages.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/messages` | NO | ALL | ALL | NO | NO | NO | NO | NO |
| GET | `/messages/{key}` | NO | ALL | ALL | NO | NO | NO | NO | NO |
| DELETE | `/messages/{key}/{channel}` | NO | ALL | ALL | NO | NO | NO | NO | NO |
| PUT | `/messages/{key}/{channel}` | NO | ALL | ALL | NO | NO | NO | NO | NO |
| POST | `/messages/{key}/{channel}/preview` | NO | ALL | ALL | NO | NO | NO | NO | NO |

## Notices

[Conditions and source evidence](modules/notices.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/notices` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| GET | `/notices/import/template` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| GET | `/notices/{notice_uuid}` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| PUT | `/notices/{notice_uuid}` | NO | ALL | NO | NO | NO | NO | NO | NO |
| GET | `/notices/{notice_uuid}/checklist` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| GET | `/notices/{notice_uuid}/languages` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| POST | `/notices/{notice_uuid}/languages` | NO | ALL | NO | NO | NO | NO | NO | NO |
| PUT | `/notices/{notice_uuid}/languages/{code}` | NO | ALL | NO | NO | NO | NO | NO | NO |
| POST | `/notices/{notice_uuid}/languages/{code}/approve` | NO | ALL | NO | NO | NO | NO | NO | NO |
| GET | `/notices/{notice_uuid}/preview` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| POST | `/notices/{notice_uuid}/publish` | NO | ALL | NO | NO | NO | NO | NO | NO |
| GET | `/notices/{notice_uuid}/purposes` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| POST | `/notices/{notice_uuid}/purposes` | NO | ALL | NO | NO | NO | NO | NO | NO |
| POST | `/notices/{notice_uuid}/purposes/activate` | NO | ALL | NO | NO | NO | NO | NO | NO |
| DELETE | `/notices/{notice_uuid}/purposes/{purpose_uuid}` | NO | ALL | NO | NO | NO | NO | NO | NO |
| PUT | `/notices/{notice_uuid}/purposes/{purpose_uuid}` | NO | ALL | NO | NO | NO | NO | NO | NO |
| GET | `/notices/{notice_uuid}/versions` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| GET | `/projects/{project_uuid}/notices` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| POST | `/projects/{project_uuid}/notices` | NO | ALL | NO | NO | NO | NO | NO | NO |
| POST | `/projects/{project_uuid}/notices/copy` | NO | ALL | NO | NO | NO | NO | OWN | NO |
| POST | `/projects/{project_uuid}/notices/import` | NO | ALL | NO | NO | NO | NO | OWN | NO |
| POST | `/projects/{project_uuid}/notices/import/validate` | NO | ALL | NO | NO | NO | NO | OWN | NO |

## Projects

[Conditions and source evidence](modules/projects.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/approvals` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| GET | `/approvals/{approval_uuid}` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| GET | `/approvals/{approval_uuid}/proof` | NO | ALL | NO | NO | NO | NO | OWN | NO |
| GET | `/projects` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| POST | `/projects` | NO | NO | NO | NO | NO | NO | OWN | NO |
| GET | `/projects/{project_uuid}` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| PUT | `/projects/{project_uuid}` | NO | NO | NO | NO | NO | NO | OWN | NO |
| GET | `/projects/{project_uuid}/approvals` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| POST | `/projects/{project_uuid}/approvals` | NO | NO | NO | NO | NO | NO | OWN | NO |
| POST | `/projects/{project_uuid}/close` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |
| GET | `/projects/{project_uuid}/history` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| GET | `/projects/{project_uuid}/processors` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| POST | `/projects/{project_uuid}/processors` | NO | NO | NO | NO | NO | NO | OWN | NO |
| PUT | `/projects/{project_uuid}/processors` | NO | NO | NO | NO | NO | NO | OWN | NO |
| POST | `/projects/{project_uuid}/processors/{processor_uuid}/decision` | NO | ALL | NO | NO | NO | NO | NO | NO |
| GET | `/projects/{project_uuid}/sites` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| POST | `/projects/{project_uuid}/sites` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| GET | `/projects/{project_uuid}/summary` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| POST | `/projects/{project_uuid}/transition` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| GET | `/projects/{project_uuid}/transitions` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| GET | `/sites` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| GET | `/sites/{site_uuid}` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| PUT | `/sites/{site_uuid}` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |
| POST | `/sites/{site_uuid}/agent` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |
| POST | `/sites/{site_uuid}/deactivate` | NO | ALL | NO | NO | NO | NO | NO | NO |
| PUT | `/sites/{site_uuid}/owner` | NO | ALL | NO | NO | SCOPED | NO | OWN | NO |
| PUT | `/sites/{site_uuid}/source` | NO | ALL | NO | NO | SCOPED | NO | OWN | NO |

## Public Consent

[Conditions and source evidence](modules/public_consent.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/c/{token}` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |
| POST | `/c/{token}/consent` | NO | NO | NO | NO | NO | NO | NO | OWN |
| GET | `/c/{token}/notice` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |
| POST | `/c/{token}/otp` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |
| POST | `/c/{token}/otp/verify` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |
| POST | `/c/{token}/register` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

## Public Information

[Conditions and source evidence](modules/public_information.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/notice/{notice_uuid}` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |
| GET | `/rights` | YES | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |
| GET | `/rights/nominations/{token}` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |
| POST | `/rights/nominations/{token}/accept` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |
| POST | `/rights/nominations/{token}/code` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |
| POST | `/rights/nominations/{token}/decline` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |
| POST | `/rights/nominee/requests` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |
| POST | `/rights/nominee/start` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |
| POST | `/rights/requests` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |
| POST | `/rights/requests/verify` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

## Registry

[Conditions and source evidence](modules/registry.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/processors` | NO | ALL | ALL | ALL | ALL | ALL | ALL | NO |
| POST | `/processors` | NO | ALL | ALL | NO | NO | NO | NO | NO |
| GET | `/processors/{processor_uuid}` | NO | ALL | ALL | ALL | ALL | ALL | ALL | NO |
| PUT | `/processors/{processor_uuid}` | NO | ALL | ALL | NO | NO | NO | NO | NO |
| GET | `/processors/{processor_uuid}/respondents` | NO | ALL | ALL | ALL | ALL | ALL | ALL | NO |
| POST | `/processors/{processor_uuid}/respondents` | NO | ALL | ALL | NO | NO | NO | NO | NO |
| DELETE | `/processors/{processor_uuid}/respondents/{respondent_uuid}` | NO | ALL | ALL | NO | NO | NO | NO | NO |
| POST | `/processors/{processor_uuid}/suspend` | NO | ALL | ALL | NO | NO | NO | NO | NO |
| GET | `/purposes` | NO | ALL | ALL | ALL | ALL | ALL | ALL | NO |
| POST | `/purposes` | NO | ALL | NO | NO | NO | NO | NO | NO |
| GET | `/purposes/{purpose_uuid}` | NO | ALL | ALL | ALL | ALL | ALL | ALL | NO |
| PUT | `/purposes/{purpose_uuid}` | NO | ALL | NO | NO | NO | NO | NO | NO |
| POST | `/purposes/{purpose_uuid}/activate` | NO | ALL | NO | NO | NO | NO | NO | NO |
| POST | `/purposes/{purpose_uuid}/retire` | NO | ALL | NO | NO | NO | NO | NO | NO |
| GET | `/purposes/{purpose_uuid}/usage` | NO | ALL | ALL | NO | NO | NO | NO | NO |
| GET | `/purposes/{purpose_uuid}/versions` | NO | ALL | ALL | NO | NO | NO | NO | NO |
| GET | `/sources` | NO | ALL | ALL | ALL | ALL | ALL | ALL | NO |
| POST | `/sources` | NO | ALL | ALL | ALL | ALL | ALL | NO | NO |
| GET | `/sources/{source_uuid}` | NO | ALL | ALL | ALL | ALL | ALL | ALL | NO |
| PUT | `/sources/{source_uuid}` | NO | ALL | ALL | ALL | ALL | ALL | NO | NO |
| GET | `/sources/{source_uuid}/batches` | NO | COND | COND | COND | COND | COND | COND | COND |
| PUT | `/sources/{source_uuid}/owner` | NO | ALL | ALL | ALL | ALL | ALL | NO | NO |
| POST | `/sources/{source_uuid}/suspend` | NO | ALL | ALL | ALL | ALL | ALL | NO | NO |

## Rights

[Conditions and source evidence](modules/rights.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/requests` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests` | NO | YES | YES | NO | NO | NO | NO | NO |
| GET | `/requests/attention` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| GET | `/requests/{request_uuid}` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/acknowledge` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/classify` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/decide` | NO | COND | COND | NO | NO | NO | NO | NO |
| GET | `/requests/{request_uuid}/download` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/escalate` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/event` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| GET | `/requests/{request_uuid}/event/evidence` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| GET | `/requests/{request_uuid}/files/{file_uuid}` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/holders` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/holders/derive` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/confirm` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/contact` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/escalate` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| GET | `/requests/{request_uuid}/holders/{holder_uuid}/evidence` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| GET | `/requests/{request_uuid}/holders/{holder_uuid}/messages/{message_uuid}/evidence` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/reassign` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/remind` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/return` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/send-back` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| GET | `/requests/{request_uuid}/holders/{holder_uuid}/thread` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/thread` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/withdraw` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/intent` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| GET | `/requests/{request_uuid}/linked/trail` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/refuse` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/respond` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/reviewer` | NO | NO | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/scope/derive` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| PUT | `/requests/{request_uuid}/scope/{item_uuid}` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/scope/{item_uuid}/apply` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/scope/{item_uuid}/execute` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/tickets` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| GET | `/requests/{request_uuid}/trail` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/transition` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| GET | `/requests/{request_uuid}/transitions` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/verification/code` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/verification/confirm` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/verification/fail` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/verification/manual` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/withdrawal` | NO | ALL | SCOPED | NO | NO | NO | NO | NO |

## System

[Conditions and source evidence](modules/system.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/` | YES | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |
| GET | `/health` | YES | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |
| GET | `/health/live` | YES | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |
| GET | `/health/ready` | YES | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |
| GET | `/meta/data-categories` | YES | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |
| GET | `/meta/enums` | YES | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |
| GET | `/meta/version` | YES | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |
| GET | `/ready` | YES | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

## Tickets

[Conditions and source evidence](modules/tickets.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/tickets` | NO | OWN | OWN | OWN | OWN | OWN | OWN | NO |
| GET | `/tickets/{holder_uuid}` | NO | OWN | OWN | OWN | OWN | OWN | OWN | NO |
| POST | `/tickets/{holder_uuid}/messages` | NO | OWN | OWN | OWN | OWN | OWN | OWN | NO |
| GET | `/tickets/{holder_uuid}/messages/{message_uuid}/evidence` | NO | OWN | OWN | OWN | OWN | OWN | OWN | NO |
| POST | `/tickets/{holder_uuid}/return` | NO | OWN | OWN | OWN | OWN | OWN | OWN | NO |

## Users

[Conditions and source evidence](modules/users.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/users` | NO | ALL | ALL | NO | NO | NO | NO | NO |
| POST | `/users` | NO | NO | ALL | NO | NO | NO | NO | NO |
| GET | `/users/collection-owners` | NO | ALL | ALL | ALL | ALL | ALL | ALL | NO |
| GET | `/users/staff` | NO | ALL | ALL | NO | NO | NO | NO | NO |
| GET | `/users/{user_uuid}` | NO | ALL | ALL | NO | NO | NO | NO | NO |
| PATCH | `/users/{user_uuid}` | NO | NO | ALL | NO | NO | NO | NO | NO |
| POST | `/users/{user_uuid}/deactivate` | NO | NO | ALL | NO | NO | NO | NO | NO |
| POST | `/users/{user_uuid}/invite` | NO | NO | ALL | NO | NO | NO | NO | NO |
| POST | `/users/{user_uuid}/mfa/reset` | NO | NO | ALL | NO | NO | NO | NO | NO |
| GET | `/users/{user_uuid}/person-type-history` | NO | ALL | ALL | NO | NO | NO | NO | NO |
| POST | `/users/{user_uuid}/reactivate` | NO | NO | ALL | NO | NO | NO | NO | NO |
| POST | `/users/{user_uuid}/role` | NO | NO | ALL | NO | NO | NO | NO | NO |
| DELETE | `/users/{user_uuid}/sessions` | NO | NO | ALL | NO | NO | NO | NO | NO |
