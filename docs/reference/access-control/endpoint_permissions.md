# Endpoint-by-endpoint permission matrix

[Guide](README.md) · [Detailed module entries](module_permissions.md)

**Legend:** `NO` = role cannot complete the operation; `YES` = eligible role (normal validation still applies); `ALL` = all rows within the named resource, not an administrator wildcard; `OWN` = own account or own-created project; `SCOPED` = assigned/project/site or about-DPO scope; `COND` = special conditions described in the module entry; `PUBLIC` = endpoint does not require a role. Anonymous `COND` means a link/code/capability is required, not a session role. These are implemented role eligibility and row scopes, not promises of success for invalid records or lifecycle states.

Roles refer to the **effective session role**. A staff account signed in through the portal OTP flow acts as `data_subject`. Ordinary staff sessions cannot use principal-only endpoints. The account itself retains its staff role.

## Audit

[Conditions and source evidence](modules/audit.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/audit` | NO | ALL | ALL | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/audit/verify` | NO | ALL | ALL | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/audit/{log_uuid}` | NO | ALL | ALL | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/audit/summary` | NO | ALL | ALL | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/audit/vocabulary` | NO | ALL | ALL | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/audit/lookup` | NO | ALL | ALL | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/audit/export.csv` | NO | ALL | ALL | NO | NO | NO | NO | NO | NO | ALL | NO |

## Auth

[Conditions and source evidence](modules/auth.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| POST | `/auth/login` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| POST | `/auth/logout` | NO | OWN | OWN | OWN | OWN | OWN | OWN | OWN | OWN | NO | NO |
| GET | `/auth/me` | NO | OWN | OWN | OWN | OWN | OWN | OWN | OWN | OWN | NO | NO |
| POST | `/auth/mfa/resend` | NO | COND | COND | COND | COND | COND | COND | COND | COND | NO | NO |
| POST | `/auth/mfa/verify` | NO | COND | COND | COND | COND | COND | COND | COND | COND | NO | NO |
| POST | `/auth/otp/request` | YES | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| POST | `/auth/otp/verify` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| POST | `/auth/password/change` | NO | OWN | OWN | OWN | OWN | OWN | OWN | OWN | OWN | NO | NO |
| POST | `/auth/password/reset/confirm` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| POST | `/auth/password/reset/request` | YES | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| POST | `/auth/register` | YES | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| POST | `/auth/register/verify` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| GET | `/auth/sessions` | NO | OWN | OWN | OWN | OWN | OWN | OWN | OWN | OWN | NO | NO |
| DELETE | `/auth/sessions/{session_uuid}` | NO | OWN | OWN | OWN | OWN | OWN | OWN | OWN | OWN | NO | NO |
| GET | `/auth/sso/callback` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |

## Breach tickets

[Conditions and source evidence](modules/breach_tickets.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/breach-tickets` | NO | OWN | OWN | OWN | OWN | OWN | OWN | NO | OWN | NO | NO |
| GET | `/breach-tickets/{ticket_uuid}` | NO | OWN | OWN | OWN | OWN | OWN | OWN | NO | OWN | NO | NO |
| POST | `/breach-tickets/{ticket_uuid}/messages` | NO | OWN | OWN | OWN | OWN | OWN | OWN | NO | OWN | NO | NO |
| GET | `/breach-tickets/{ticket_uuid}/messages/{message_uuid}/evidence` | NO | OWN | OWN | OWN | OWN | OWN | OWN | NO | OWN | NO | NO |
| POST | `/breach-tickets/{ticket_uuid}/return` | NO | OWN | OWN | OWN | OWN | OWN | OWN | NO | OWN | NO | NO |
| POST | `/breach-tickets/{ticket_uuid}/colleagues` | NO | OWN | OWN | OWN | OWN | OWN | OWN | NO | OWN | NO | NO |

## Breaches

[Conditions and source evidence](modules/breaches.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/breaches` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/breaches` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/breaches/{breach_uuid}` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/breaches/{breach_uuid}/determinations` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/breaches/{breach_uuid}/assessments` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/breaches/{breach_uuid}/assessments` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/breaches/{breach_uuid}/cert-in` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/breaches/{breach_uuid}/obligations/{duty}/complete` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/breaches/{breach_uuid}/obligations/board_report/extension` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/breaches/{breach_uuid}/transitions` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/breaches/{breach_uuid}/transition` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/breaches/{breach_uuid}/affected` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/breaches/{breach_uuid}/affected/preview` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/breaches/{breach_uuid}/notices` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/breaches/{breach_uuid}/notices` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| PUT | `/breaches/{breach_uuid}/notices/{notice_uuid}` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/breaches/{breach_uuid}/notices/{notice_uuid}/approve` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/breaches/{breach_uuid}/notices/send` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/breaches/{breach_uuid}/board/intimation` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/breaches/{breach_uuid}/board/report` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/breaches/{breach_uuid}/affected` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/breaches/{breach_uuid}/org-board/brief` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/breaches/{breach_uuid}/tickets` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/breaches/{breach_uuid}/tickets` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/breaches/{breach_uuid}/tickets/{ticket_uuid}` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/breaches/{breach_uuid}/tickets/{ticket_uuid}/messages` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/breaches/{breach_uuid}/tickets/{ticket_uuid}/messages/{message_uuid}/evidence` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/breaches/{breach_uuid}/tickets/{ticket_uuid}/send-back` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/breaches/{breach_uuid}/tickets/{ticket_uuid}/close` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/breaches/{breach_uuid}/tickets/{ticket_uuid}/withdraw` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/breaches/{breach_uuid}/tickets/{ticket_uuid}/reopen` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/breaches/{breach_uuid}/attachments` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/breaches/{breach_uuid}/attachments/{attachment_uuid}` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/breaches/{breach_uuid}/affected/upload/template` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/breaches/{breach_uuid}/affected/upload/check` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/breaches/{breach_uuid}/affected/upload` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/breaches/{breach_uuid}/affected/contacts` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

## Consent

[Conditions and source evidence](modules/consent.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/consents` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| GET | `/consents/{consent_uuid}` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| GET | `/consents/{consent_uuid}/assets` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| GET | `/consents/{consent_uuid}/grants` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| GET | `/links` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO | NO | ALL | SCOPED |
| GET | `/links/{link_uuid}` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO | NO | ALL | SCOPED |
| POST | `/links/{link_uuid}/remint` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO | NO | ALL | SCOPED |
| POST | `/links/{link_uuid}/revoke` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO | NO | ALL | SCOPED |
| GET | `/links/{link_uuid}/stats` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO | NO | ALL | SCOPED |
| GET | `/projects/{project_uuid}/consents` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| GET | `/projects/{project_uuid}/consents/summary` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| GET | `/projects/{project_uuid}/links` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO | NO | ALL | SCOPED |
| GET | `/consents/{consent_uuid}/record` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO | NO | ALL | SCOPED |
| GET | `/consent-records` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO | NO | ALL | SCOPED |
| POST | `/consent-records` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO | NO | ALL | SCOPED |

## Cross-border transfers

[Conditions and source evidence](modules/cross_border_transfers.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/restricted-countries` | NO | ALL | ALL | NO | NO | NO | NO | NO | NO | NO | NO |
| POST | `/restricted-countries` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO | NO |
| POST | `/restricted-countries/{country_uuid}/lift` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO | NO |

## Dashboard

[Conditions and source evidence](modules/dashboard.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/dashboard` | NO | COND | COND | COND | COND | COND | COND | COND | COND | NO | NO |
| GET | `/notifications` | NO | COND | COND | COND | COND | COND | COND | COND | COND | NO | NO |
| POST | `/notifications/{log_uuid}/resend` | NO | COND | NO | COND | NO | NO | NO | NO | NO | NO | NO |

## Delegations

[Conditions and source evidence](modules/delegations.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/delegations` | NO | ALL | ALL | NO | NO | NO | NO | NO | NO | NO | NO |
| POST | `/delegations` | NO | COND | COND | COND | NO | NO | NO | NO | NO | NO | NO |
| GET | `/delegations/held` | NO | OWN | OWN | OWN | OWN | OWN | OWN | OWN | OWN | NO | NO |
| GET | `/delegations/mine` | NO | OWN | OWN | OWN | OWN | OWN | OWN | OWN | OWN | NO | NO |
| DELETE | `/delegations/{delegation_uuid}` | NO | COND | COND | COND | COND | COND | COND | NO | NO | NO | NO |
| GET | `/delegations/candidates` | NO | OWN | OWN | OWN | OWN | OWN | OWN | NO | NO | NO | NO |

## Exchange

[Conditions and source evidence](modules/exchange.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/assets/{asset_uuid}` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | NO | NO |
| GET | `/assets/{asset_uuid}/subjects` | NO | ALL | NO | SCOPED | NO | NO | NO | NO | NO | NO | NO |
| GET | `/collections` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | NO | NO |
| GET | `/collections/{collection_uuid}` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | NO | NO |
| GET | `/collections/{collection_uuid}/assets` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | NO | NO |
| GET | `/collections/{collection_uuid}/exceptions` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | NO | NO |
| GET | `/exports` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO | NO | ALL | SCOPED |
| GET | `/exports/{export_uuid}` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO | NO | ALL | SCOPED |
| GET | `/exports/{export_uuid}/download` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO | NO | ALL | SCOPED |
| GET | `/exports/{export_uuid}/lines` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO | NO | ALL | SCOPED |
| GET | `/imports` | NO | COND | COND | COND | COND | COND | COND | COND | NO | NO | NO |
| POST | `/imports` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO | NO | NO | NO |
| GET | `/imports/template` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO | NO | NO | NO |
| POST | `/imports/validate` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO | NO | NO | NO |
| GET | `/imports/{batch_uuid}` | NO | COND | COND | COND | COND | COND | COND | COND | NO | NO | NO |
| GET | `/imports/{batch_uuid}/errors` | NO | COND | COND | COND | COND | COND | COND | COND | NO | NO | NO |
| GET | `/projects/{project_uuid}/collections` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | NO | NO |
| GET | `/projects/{project_uuid}/exports` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO | NO | ALL | SCOPED |
| POST | `/projects/{project_uuid}/exports` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO | NO | ALL | SCOPED |

## HR activities

[Conditions and source evidence](modules/hr_activities.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/hr/activities` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| GET | `/hr/activities/options` | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO | SCOPED |
| POST | `/hr/activities` | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO | SCOPED |
| GET | `/hr/activities/{activity_uuid}` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| POST | `/hr/activities/{activity_uuid}/upgrade` | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO | SCOPED |
| POST | `/hr/activities/{activity_uuid}/close` | NO | NO | NO | NO | NO | NO | NO | NO | NO | ALL | SCOPED |

## HR categories

[Conditions and source evidence](modules/hr_categories.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/hr/categories` | NO | NO | ALL | NO | NO | NO | NO | NO | NO | ALL | SCOPED |
| POST | `/hr/categories` | NO | NO | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/hr/categories/{category_uuid}` | NO | NO | ALL | NO | NO | NO | NO | NO | NO | ALL | SCOPED |
| PATCH | `/hr/categories/{category_uuid}` | NO | NO | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/hr/categories/{category_uuid}/status` | NO | NO | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/hr/categories/{category_uuid}/processors` | NO | NO | ALL | NO | NO | NO | NO | NO | NO | ALL | SCOPED |
| PUT | `/hr/categories/{category_uuid}/processors` | NO | NO | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

## Legal holds

[Conditions and source evidence](modules/legal_holds.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/legal-holds` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/legal-holds` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/legal-holds/{hold_uuid}/release` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

## Me

[Conditions and source evidence](modules/me.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/me` | NO | OWN | OWN | OWN | OWN | OWN | OWN | OWN | OWN | NO | NO |
| PATCH | `/me` | NO | OWN | OWN | OWN | OWN | OWN | OWN | OWN | OWN | NO | NO |
| GET | `/me/consents` | NO | NO | NO | NO | NO | NO | NO | OWN | NO | NO | NO |
| GET | `/me/consents/{consent_uuid}` | NO | NO | NO | NO | NO | NO | NO | OWN | NO | NO | NO |
| GET | `/me/consents/{consent_uuid}/grants` | NO | NO | NO | NO | NO | NO | NO | OWN | NO | NO | NO |
| GET | `/me/consents/{consent_uuid}/history` | NO | NO | NO | NO | NO | NO | NO | OWN | NO | NO | NO |
| GET | `/me/consents/{consent_uuid}/notice` | NO | NO | NO | NO | NO | NO | NO | OWN | NO | NO | NO |
| GET | `/me/consents/{consent_uuid}/trail` | NO | NO | NO | NO | NO | NO | NO | OWN | NO | NO | NO |
| POST | `/me/consents/{consent_uuid}/withdraw` | NO | NO | NO | NO | NO | NO | NO | OWN | NO | NO | NO |
| POST | `/me/contact/verify` | NO | OWN | OWN | OWN | OWN | OWN | OWN | OWN | OWN | NO | NO |
| POST | `/me/contacts/code` | NO | OWN | OWN | OWN | OWN | OWN | OWN | OWN | OWN | NO | NO |
| GET | `/me/disclosures` | NO | NO | NO | NO | NO | NO | NO | OWN | NO | NO | NO |
| GET | `/me/nominations` | NO | NO | NO | NO | NO | NO | NO | OWN | NO | NO | NO |
| POST | `/me/nominations` | NO | NO | NO | NO | NO | NO | NO | OWN | NO | NO | NO |
| DELETE | `/me/nominations/{nomination_uuid}` | NO | NO | NO | NO | NO | NO | NO | OWN | NO | NO | NO |
| GET | `/me/nominee-of` | NO | NO | NO | NO | NO | NO | NO | OWN | NO | NO | NO |
| GET | `/me/notifications` | NO | NO | NO | NO | NO | NO | NO | OWN | NO | NO | NO |
| POST | `/me/person-type` | NO | OWN | OWN | NO | NO | NO | NO | OWN | NO | NO | NO |
| GET | `/me/requests` | NO | NO | NO | NO | NO | NO | NO | OWN | NO | NO | NO |
| POST | `/me/requests` | NO | NO | NO | NO | NO | NO | NO | OWN | NO | NO | NO |
| GET | `/me/requests/{request_uuid}` | NO | NO | NO | NO | NO | NO | NO | OWN | NO | NO | NO |
| POST | `/me/requests/{request_uuid}/dispute` | NO | NO | NO | NO | NO | NO | NO | OWN | NO | NO | NO |
| GET | `/me/requests/{request_uuid}/download` | NO | NO | NO | NO | NO | NO | NO | OWN | NO | NO | NO |
| GET | `/me/requests/{request_uuid}/files/{file_uuid}` | NO | NO | NO | NO | NO | NO | NO | OWN | NO | NO | NO |
| GET | `/me/requests/{request_uuid}/trail` | NO | NO | NO | NO | NO | NO | NO | OWN | NO | NO | NO |
| DELETE | `/me/secondary-email` | NO | OWN | OWN | OWN | OWN | OWN | OWN | OWN | OWN | NO | NO |
| GET | `/me/breach-notices` | NO | NO | NO | NO | NO | NO | NO | OWN | NO | NO | NO |
| POST | `/me/requests/{request_uuid}/attachments` | NO | NO | NO | NO | NO | NO | NO | OWN | NO | NO | NO |
| GET | `/me/requests/offices` | NO | NO | NO | NO | NO | NO | NO | OWN | NO | NO | NO |
| GET | `/me/consents/{consent_uuid}/record` | NO | NO | NO | NO | NO | NO | NO | OWN | NO | NO | NO |

## Messages

[Conditions and source evidence](modules/messages.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/messages` | NO | ALL | ALL | NO | NO | NO | NO | NO | NO | NO | NO |
| GET | `/messages/{key}` | NO | ALL | ALL | NO | NO | NO | NO | NO | NO | NO | NO |
| DELETE | `/messages/{key}/{channel}` | NO | ALL | ALL | NO | NO | NO | NO | NO | NO | NO | NO |
| PUT | `/messages/{key}/{channel}` | NO | ALL | ALL | NO | NO | NO | NO | NO | NO | NO | NO |
| POST | `/messages/{key}/{channel}/preview` | NO | ALL | ALL | NO | NO | NO | NO | NO | NO | NO | NO |
| PUT | `/messages/{key}/copies` | NO | ALL | ALL | NO | NO | NO | NO | NO | NO | NO | NO |

## Notices

[Conditions and source evidence](modules/notices.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/notices` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| GET | `/notices/copy-sources` | NO | ALL | NO | NO | NO | NO | ALL | NO | NO | NO | NO |
| GET | `/notices/import/template` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| GET | `/notices/{notice_uuid}` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| PUT | `/notices/{notice_uuid}` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO | NO |
| GET | `/notices/{notice_uuid}/checklist` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| GET | `/notices/{notice_uuid}/languages` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| POST | `/notices/{notice_uuid}/languages` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO | NO |
| PUT | `/notices/{notice_uuid}/languages/{code}` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO | NO |
| POST | `/notices/{notice_uuid}/languages/{code}/approve` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | SCOPED |
| GET | `/notices/{notice_uuid}/preview` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| POST | `/notices/{notice_uuid}/publish` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | SCOPED |
| GET | `/notices/{notice_uuid}/purposes` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| POST | `/notices/{notice_uuid}/purposes` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO | NO |
| POST | `/notices/{notice_uuid}/purposes/activate` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | SCOPED |
| DELETE | `/notices/{notice_uuid}/purposes/{purpose_uuid}` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO | NO |
| PUT | `/notices/{notice_uuid}/purposes/{purpose_uuid}` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO | NO |
| GET | `/notices/{notice_uuid}/versions` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| GET | `/projects/{project_uuid}/notices` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| POST | `/projects/{project_uuid}/notices` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO | NO |
| POST | `/projects/{project_uuid}/notices/copy` | NO | ALL | NO | NO | NO | NO | OWN | NO | NO | NO | NO |
| POST | `/projects/{project_uuid}/notices/import` | NO | ALL | NO | NO | NO | NO | OWN | NO | NO | NO | NO |
| POST | `/projects/{project_uuid}/notices/import/validate` | NO | ALL | NO | NO | NO | NO | OWN | NO | NO | NO | NO |
| GET | `/notice-templates` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/notice-templates` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/notice-templates/{template_uuid}` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| PUT | `/notice-templates/{template_uuid}` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/notice-templates/{template_uuid}/status` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/notice-templates/{template_uuid}/purposes` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| DELETE | `/notice-templates/{template_uuid}/purposes/{purpose_uuid}` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| PUT | `/notice-templates/{template_uuid}/languages/{code}` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| DELETE | `/notice-templates/{template_uuid}/languages/{code}` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/notice-templates/by-code/{template_code}` | NO | ALL | NO | NO | NO | NO | OWN | NO | NO | ALL | SCOPED |
| POST | `/projects/{project_uuid}/notices/from-template` | NO | ALL | NO | NO | NO | NO | OWN | NO | NO | NO | NO |
| GET | `/notice-templates/{template_uuid}/versions` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/notice-templates/{template_uuid}/versions` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/notice-templates/{template_uuid}/versions/{number}` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| PATCH | `/notice-templates/{template_uuid}/versions/{number}` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| PUT | `/notice-templates/{template_uuid}/versions/{number}/languages/{code}` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| DELETE | `/notice-templates/{template_uuid}/versions/{number}/languages/{code}` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| PUT | `/notice-templates/{template_uuid}/versions/{number}/purposes` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/notice-templates/{template_uuid}/versions/{number}/approve` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/notice-templates/{template_uuid}/versions/{number}/status` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/notice-templates/{template_uuid}/versions/{number}/preview` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

## Projects

[Conditions and source evidence](modules/projects.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/approvals` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| GET | `/approvals/{approval_uuid}` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| GET | `/approvals/{approval_uuid}/proof` | NO | ALL | NO | NO | NO | NO | OWN | NO | NO | ALL | SCOPED |
| GET | `/projects` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| POST | `/projects` | NO | NO | NO | NO | NO | NO | OWN | NO | NO | ALL | SCOPED |
| GET | `/projects/{project_uuid}` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| PUT | `/projects/{project_uuid}` | NO | NO | NO | NO | NO | NO | OWN | NO | NO | ALL | SCOPED |
| GET | `/projects/{project_uuid}/approvals` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| POST | `/projects/{project_uuid}/approvals` | NO | NO | NO | NO | NO | NO | OWN | NO | NO | ALL | SCOPED |
| POST | `/projects/{project_uuid}/close` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO | NO | ALL | SCOPED |
| GET | `/projects/{project_uuid}/history` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| GET | `/projects/{project_uuid}/processors` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| POST | `/projects/{project_uuid}/processors` | NO | NO | NO | NO | NO | NO | OWN | NO | NO | ALL | SCOPED |
| PUT | `/projects/{project_uuid}/processors` | NO | NO | NO | NO | NO | NO | OWN | NO | NO | ALL | SCOPED |
| POST | `/projects/{project_uuid}/processors/{processor_uuid}/decision` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | SCOPED |
| GET | `/projects/{project_uuid}/sites` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| POST | `/projects/{project_uuid}/sites` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| GET | `/projects/{project_uuid}/summary` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| POST | `/projects/{project_uuid}/transition` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| GET | `/projects/{project_uuid}/transitions` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| GET | `/sites` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| GET | `/sites/{site_uuid}` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| PUT | `/sites/{site_uuid}` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |
| POST | `/sites/{site_uuid}/agent` | NO | ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO | NO | ALL | SCOPED |
| POST | `/sites/{site_uuid}/deactivate` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | SCOPED |
| PUT | `/sites/{site_uuid}/owner` | NO | ALL | NO | NO | SCOPED | NO | OWN | NO | NO | ALL | SCOPED |
| PUT | `/sites/{site_uuid}/source` | NO | ALL | NO | NO | SCOPED | NO | OWN | NO | NO | ALL | SCOPED |

## Public Consent

[Conditions and source evidence](modules/public_consent.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/c/{token}` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| POST | `/c/{token}/consent` | NO | NO | NO | NO | NO | NO | NO | OWN | NO | NO | NO |
| GET | `/c/{token}/notice` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| POST | `/c/{token}/otp` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| POST | `/c/{token}/otp/verify` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| POST | `/c/{token}/register` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| GET | `/c/{token}/sso/start` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| POST | `/c/{token}/sso/mobile` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| POST | `/c/{token}/sso/mobile/verify` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |

## Public Information

[Conditions and source evidence](modules/public_information.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/notice/{notice_uuid}` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| GET | `/rights` | YES | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| GET | `/rights/nominations/{token}` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| POST | `/rights/nominations/{token}/accept` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| POST | `/rights/nominations/{token}/code` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| POST | `/rights/nominations/{token}/decline` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| POST | `/rights/nominee/requests` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| POST | `/rights/nominee/start` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| POST | `/rights/requests` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| POST | `/rights/requests/verify` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| GET | `/holder-tickets/{token}` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| POST | `/holder-tickets/{token}/code` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| POST | `/holder-tickets/{token}/verify` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| POST | `/holder-tickets/{token}/sign-out` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| GET | `/holder-tickets/{token}/ticket` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| POST | `/holder-tickets/{token}/messages` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| POST | `/holder-tickets/{token}/answer` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| GET | `/holder-tickets/{token}/messages/{message_uuid}/evidence` | COND | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |

## Registry

[Conditions and source evidence](modules/registry.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/processors` | NO | ALL | ALL | ALL | ALL | ALL | ALL | NO | NO | NO | NO |
| POST | `/processors` | NO | ALL | ALL | NO | NO | NO | NO | NO | NO | NO | NO |
| GET | `/processors/{processor_uuid}` | NO | ALL | ALL | ALL | ALL | ALL | ALL | NO | NO | NO | NO |
| PUT | `/processors/{processor_uuid}` | NO | ALL | ALL | NO | NO | NO | NO | NO | NO | NO | NO |
| GET | `/processors/{processor_uuid}/respondents` | NO | ALL | ALL | ALL | ALL | ALL | ALL | NO | NO | NO | NO |
| POST | `/processors/{processor_uuid}/respondents` | NO | ALL | ALL | NO | NO | NO | NO | NO | NO | NO | NO |
| DELETE | `/processors/{processor_uuid}/respondents/{respondent_uuid}` | NO | ALL | ALL | NO | NO | NO | NO | NO | NO | NO | NO |
| POST | `/processors/{processor_uuid}/suspend` | NO | ALL | ALL | NO | NO | NO | NO | NO | NO | NO | NO |
| GET | `/purposes` | NO | ALL | ALL | ALL | ALL | ALL | ALL | NO | NO | ALL | NO |
| POST | `/purposes` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/purposes/{purpose_uuid}` | NO | ALL | ALL | ALL | ALL | ALL | ALL | NO | NO | NO | NO |
| PUT | `/purposes/{purpose_uuid}` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/purposes/{purpose_uuid}/activate` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/purposes/{purpose_uuid}/retire` | NO | ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/purposes/{purpose_uuid}/usage` | NO | ALL | ALL | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/purposes/{purpose_uuid}/versions` | NO | ALL | ALL | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/sources` | NO | ALL | ALL | SCOPED | ALL | SCOPED | ALL | NO | NO | NO | NO |
| POST | `/sources` | NO | ALL | ALL | SCOPED | ALL | SCOPED | NO | NO | NO | NO | NO |
| GET | `/sources/{source_uuid}` | NO | ALL | ALL | SCOPED | ALL | SCOPED | ALL | NO | NO | NO | NO |
| PUT | `/sources/{source_uuid}` | NO | ALL | ALL | SCOPED | ALL | SCOPED | NO | NO | NO | NO | NO |
| GET | `/sources/{source_uuid}/batches` | NO | COND | COND | COND | COND | COND | COND | COND | NO | NO | NO |
| PUT | `/sources/{source_uuid}/owner` | NO | ALL | ALL | SCOPED | ALL | SCOPED | NO | NO | NO | NO | NO |
| POST | `/sources/{source_uuid}/suspend` | NO | ALL | ALL | SCOPED | ALL | SCOPED | NO | NO | NO | NO | NO |
| GET | `/processors/import/template` | NO | NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |
| POST | `/processors/import/check` | NO | NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |
| POST | `/processors/import` | NO | NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |
| GET | `/sources/import/template` | NO | NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |
| POST | `/sources/import/check` | NO | NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |
| POST | `/sources/import` | NO | NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |

## Rights

[Conditions and source evidence](modules/rights.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/requests` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests` | NO | YES | YES | NO | NO | NO | NO | NO | NO | YES | NO |
| GET | `/requests/attention` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/requests/{request_uuid}` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/acknowledge` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/classify` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/decide` | NO | COND | COND | NO | NO | NO | NO | NO | NO | COND | NO |
| GET | `/requests/{request_uuid}/download` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/escalate` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/event` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/requests/{request_uuid}/event/evidence` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/requests/{request_uuid}/files/{file_uuid}` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/holders` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/holders/derive` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/confirm` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/contact` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/escalate` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/requests/{request_uuid}/holders/{holder_uuid}/evidence` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/requests/{request_uuid}/holders/{holder_uuid}/messages/{message_uuid}/evidence` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/reassign` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/remind` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/return` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/send-back` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/requests/{request_uuid}/holders/{holder_uuid}/thread` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/thread` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/withdraw` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/intent` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/requests/{request_uuid}/linked/trail` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/refuse` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/respond` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/reviewer` | NO | NO | SCOPED | NO | NO | NO | NO | NO | NO | NO | NO |
| POST | `/requests/{request_uuid}/scope/derive` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| PUT | `/requests/{request_uuid}/scope/{item_uuid}` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/scope/{item_uuid}/apply` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/tickets` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/requests/{request_uuid}/trail` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/transition` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/requests/{request_uuid}/transitions` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/verification/code` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/verification/confirm` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/verification/fail` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/verification/manual` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/withdrawal` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/scope/{item_uuid}/execute` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| GET | `/requests/{request_uuid}/attachments/{attachment_uuid}` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/accept` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/reopen` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| DELETE | `/requests/{request_uuid}/holders/{holder_uuid}` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| PUT | `/requests/{request_uuid}/holders/{holder_uuid}/instruction` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/correct-contact` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/claim` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/requests/{request_uuid}/transfer` | NO | ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |

## System

[Conditions and source evidence](modules/system.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/` | YES | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| GET | `/health` | YES | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| GET | `/health/live` | YES | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| GET | `/health/ready` | YES | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| GET | `/meta/data-categories` | YES | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| GET | `/meta/enums` | YES | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| GET | `/meta/version` | YES | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |
| GET | `/ready` | YES | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |

## Tickets

[Conditions and source evidence](modules/tickets.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/tickets` | NO | OWN | OWN | OWN | OWN | OWN | OWN | NO | OWN | NO | NO |
| GET | `/tickets/{holder_uuid}` | NO | OWN | OWN | OWN | OWN | OWN | OWN | NO | OWN | NO | NO |
| POST | `/tickets/{holder_uuid}/messages` | NO | OWN | OWN | OWN | OWN | OWN | OWN | NO | OWN | NO | NO |
| GET | `/tickets/{holder_uuid}/messages/{message_uuid}/evidence` | NO | OWN | OWN | OWN | OWN | OWN | OWN | NO | OWN | NO | NO |
| POST | `/tickets/{holder_uuid}/return` | NO | OWN | OWN | OWN | OWN | OWN | OWN | NO | OWN | NO | NO |

## Users

[Conditions and source evidence](modules/users.md)

| Method | Endpoint | Anonymous | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/users` | NO | ALL | ALL | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/users` | NO | NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |
| GET | `/users/collection-owners` | NO | ALL | ALL | ALL | ALL | ALL | ALL | NO | NO | NO | NO |
| GET | `/users/staff` | NO | ALL | ALL | NO | NO | NO | NO | NO | NO | NO | NO |
| GET | `/users/{user_uuid}` | NO | ALL | ALL | NO | NO | NO | NO | NO | NO | ALL | NO |
| PATCH | `/users/{user_uuid}` | NO | NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |
| POST | `/users/{user_uuid}/deactivate` | NO | NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |
| POST | `/users/{user_uuid}/invite` | NO | NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |
| POST | `/users/{user_uuid}/mfa/reset` | NO | NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |
| GET | `/users/{user_uuid}/person-type-history` | NO | ALL | ALL | NO | NO | NO | NO | NO | NO | ALL | NO |
| POST | `/users/{user_uuid}/reactivate` | NO | NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |
| POST | `/users/{user_uuid}/role` | NO | NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |
| DELETE | `/users/{user_uuid}/sessions` | NO | NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |
| PUT | `/users/{user_uuid}/processors` | NO | NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |
| GET | `/users/hr-pocs` | NO | NO | ALL | NO | NO | NO | NO | NO | NO | ALL | NO |
| PUT | `/users/{user_uuid}/categories` | NO | NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |
| GET | `/offices` | NO | ALL | ALL | ALL | ALL | ALL | ALL | NO | NO | ALL | ALL |
