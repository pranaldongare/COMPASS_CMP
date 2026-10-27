# 0033. HR consent is governed by a template version Legal approves once; an activity inherits it and needs no approval of its own

**Status:** proposed · 2026-10-27. For the HR track. Builds on
[ADR 0028](0028-a-notice-template-is-copied-never-served.md) and
[ADR 0032](0032-offices-are-logical-tenants-in-one-database.md); amends
[ADR 0026](0026-a-rights-request-is-access-erasure-or-a-grievance-about-everything.md)
and ADR 0028.

## Context

Most HR data is processed under s.7 and never touches the platform. A
growing set of HR activities does need consent: mental wellness, CSR,
background verification, corporate communication, employee engagement. The
Legal office that governs them does not want to be in every approval loop as
the DPO is on the R&D track: it wants to write the legal text once per kind
of activity and let the HR point of contact run instances of it.

On the R&D track the unit of legal sign-off is the project: the DPO approves
every language, activates the purposes and approves the project, which
publishes its notice (`domain/projects/state_machine.py`). A notice template
(ADR 0028) is a convenience for the DPO, never approved and never served; a
project made from one still needs every one of those acts. That shape puts a
person in front of every HR activity, which is precisely what Legal declined.
ADR 0028's own *Revisit when* names the case: "Legal wants templates approved
before they are handed out; templates need scoping, for instance per
department."

Decided with the product owner on 2026-10-26, after the questions in the
design note were answered:

- consent is per **activity instance**, never standing per category;
- Legal owns **categories**, each with templates; a template belongs to one
  category;
- one Legal approver; a version flagged as a material change requires
  re-consent;
- the HR PoC chooses **purposes from the template's list**, mandatory ones
  always included;
- the **description** is the only free text;
- participants are employees, candidates, vendors and visitors;
- one open link per activity; the HR PoC is the default respondent;
- legacy data and languages other than English are out of scope for now.

## Decision

- **The unit of legal sign-off on the HR track is the template version.**
  `notice_template` gains versions (`template_version`), each
  `draft → approved → retired`. Approval is one Legal officer's act
  (`approved_by`, `approved_at`); it **freezes the version and hashes every
  language's locked text**, by trigger, as publication freezes a notice.
  A version may carry `reconsent_required`, set by Legal when the change is
  material.
- **A category is Legal's registry.** `hr_category` (code, name, status),
  owned by the `hr` office; a template belongs to exactly one category; the
  category names its **processors** (`category_processor`: HRMS, the HR
  database, vendors) with a default respondent.
- **An activity is a project of the `hr` office.** `project` gains
  `category_id`, `template_version_id` and `description`. Creating an
  activity composes its notice from the version - the locked sections, the
  chosen purposes, the description in its named slot - hashes it per
  language, publishes it, registers one implicit site under the in-house HR
  processor with the HR PoC as its owner, mints the open consent link and
  moves the project `in_draft → approved`, **in one transaction, by the HR
  PoC, with no approval step.** The transition exists only on the `hr`
  office and its guard is the version: approved, not retired, locked-text
  hash equal to the hash recorded at approval, purposes ⊆ the version's list
  and ⊇ its mandatory ones, description within the slot's limits.
- **The description is the only free text, and it is evidence.** It is
  rendered inside the served notice, so it is part of the text the consent
  artefact hashes. English required; a length cap and no placeholders or
  links, enforced by the composer. Changing it after the link is live makes
  a new notice version on the activity, as any notice change does.
- **Purposes are chosen, never written.** The HR PoC picks from
  `template_version_purpose`; a purpose with `is_mandatory` cannot be
  dropped; nothing outside the list can be added. HR purposes themselves are
  Legal's (`purpose.office_id = hr`), with the fields every purpose has.
- **A newer version does not move a running activity.** The activity keeps
  the version it was created on; the HR PoC may upgrade it, which composes a
  new notice version (existing artefacts keep their text, live links move to
  it as today) and, if the version is flagged, asks participants to
  re-consent.
- **Holders come from the category.** A rights request on the HR track
  derives holders from `category_processor` (`derived_from =
  activity_processor`) as well as from export lines; a withdrawal notifies
  the activity's respondents.
- **The R&D track is untouched.** The DPO's state machine, the notice
  workflow and ADR 0028's templates behave as before. "A request is about
  everything" (ADR 0026) now reads "about everything within one office's
  remit", with the routing and transfer rules in
  [hr-track.md](../domain/hr-track.md#rights-requests-and-breaches-by-office).

## Consequences

- An HR activity goes live in one request with nobody waiting on anybody:
  the legal review happened once, on the version, and is provable from the
  version's hash on every notice made from it.
- "Which text did she agree to" keeps one answer: the activity's notice,
  whose hash the artefact records; the version it came from is a second,
  independent proof.
- A template on the R&D track stays unversioned and unapproved (ADR 0028);
  the two tables share a name and a shape and differ in the office that owns
  them and in whether a version row exists. A later decision may give the
  R&D track versions too.
- An activity cannot be created from a draft or retired version, and a
  version in use cannot be edited: Legal corrects by making the next
  version.

## Revisit when

Legal wants two approvers (drafter and approver separated); HR activities
need languages other than English (the version then needs one locked text
per language and the composer one description per language); or the R&D
track wants the same version-and-approve model for its templates.
