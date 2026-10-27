# HR track: the diagrams

Drawn 2026-10-26/27 in the programme's palette. PNG for slides; the SVG
sources are kept with the design pack outside the repository. Each is
referenced from [hr-track.md](../../domain/hr-track.md) and the plan.

| ID | File | Shows |
|---|---|---|
| UC-01 | `UC01-hr-track-governance-and-consent.png` | Use cases: template governance (Legal), activity set-up (HR PoC), consent (participant), administration |
| UC-02 | `UC02-hr-track-withdrawal-rights-breach.png` | Use cases: withdrawal, rights requests and breaches run by the Legal office |
| AR-01 | `AR01-context-and-integration-hr-track.png` | Context and integration: people, services, SSO, SMTP/SMS, HRMS, HR database, vendors; phase 1 and phase 2 flows |
| AR-02 | `AR02-layer-stack-hr-track-additions.png` | The layer stack with what the HR track adds per layer |
| AR-03 | `AR03-governance-and-data-model-delta.png` | Governance and data-model delta: new, changed and unchanged tables by owner, with `office` |
| AR-04 | `AR04-two-offices-one-platform.png` | The R&D track and the HR track side by side, and what is shared |
| AR-05 | `AR05-flow-hr-poc-sets-up-an-activity.png` | Flow: the HR PoC sets up an activity and mints its link |
| AR-06 | `AR06-flow-employee-consents-through-sso-link.png` | Flow: an employee consents through the SSO link |
| AR-07 | `AR07-flow-withdrawal-reaches-hr-holders.png` | Flow: a withdrawal reaches the HR holders |
| AR-08 | `AR08-which-office-receives-a-request-or-breach.png` | Which office receives a rights request or a breach |
| AR-09 | `AR09-offices-as-logical-tenants-in-one-database.png` | Offices as logical tenants: the office model, where the office is set, what each context runs as, the policies |
| UF-01 | `UF01-legal-authors-and-approves-a-template.png` | User flow: Legal authors a template and approves version 1 |
| UF-02 | `UF02-hr-poc-creates-an-activity-and-shares-the-link.png` | User flow: the HR PoC creates an activity and shares the link |
| UF-03 | `UF03-employee-consents-through-the-sso-link.png` | User flow: an employee consents through the SSO link |
| UF-04 | `UF04-candidate-vendor-visitor-consents-through-the-otp-link.png` | User flow: a candidate, vendor or visitor consents by one-time code |
| UF-05 | `UF05-participant-withdraws-a-consent.png` | User flow: a participant withdraws and the HR holders are told |
| UF-06 | `UF06-participant-raises-a-rights-request-legal-answers.png` | User flow: a rights request answered by the Legal office |

Where a diagram and a document disagree, the document wins: AR-03 was
drawn before the `track` column became `office_id` and shows the final
names; the flows name `track` in two labels that read as `office` in the
text. The agent does not redraw diagrams.
