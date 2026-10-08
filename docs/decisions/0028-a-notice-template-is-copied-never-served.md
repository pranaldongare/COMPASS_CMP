# 0028. A notice template is a separate record, copied into a project's draft, never approved or served

**Status:** accepted · 2026-10-07. Migration 0044, commits 6d8acca and
7541f4f. Builds on [ADR 0004](0004-scope-in-the-where-clause.md) and
[ADR 0011](0011-server-held-notice-serving.md); changes neither.

## Context

The Privacy Office writes a notice when it knows what a kind of study will
collect, which is usually before anybody has registered the study. A notice
belonged to a project, and the project did not exist yet, so the DPO could
not write one. The work happened in a document outside the platform and was
retyped once the project appeared.

The plain answer was a `notice` row with no project. It breaks two things
the platform depends on:

- **Every notice read is scoped through its project.** Scope is compiled
  into the query (ADR 0004): an R&D User sees a notice because they can see
  its project, and out of scope is 404. A notice with no project has no
  scope to compile, so it would need a rule of its own on every notice
  route.
- **A served notice is evidence.** A consent records the notice version and
  the text hash it was given against (ADR 0011), and a published notice is
  never edited. Something the DPO is still drafting, and wants to change
  freely, cannot share a table whose rows are consent evidence.

The DPO also wanted to write as many as they like, and to hand one to a
study's team by an ID they can say on the phone.

## Decision

- **A template is its own record.** `notice_template`, with
  `notice_template_purpose` and `notice_template_language`: a name, the
  Rule 3 links and the DPO contact, who it addresses, the purposes it
  carries, and the text of each language. Nothing about it is a `notice`.
- **An ID the database mints.** `TPL-0007`, from its own sequence. The DPO
  gives it to the study's R&D User.
- **The DPO writes templates; the notice author looks one up.** Every route
  that changes a template is the DPO's (`RequireDPO`). Looking one up by its
  ID takes the notice author's guard, so the R&D User the ID was given to
  can find it before attaching it
  (`api/routers/v1/notice_templates.py`).
- **Never approved, never served, never consented to.** A template is not
  evidence, so it is edited in place and needs no approval. Legal sign-off
  is on what a project serves, not on the template.
- **Used only by being copied.** *Use a notice template* on a project
  (`POST /projects/{project_uuid}/notices/from-template`) makes that
  project's own draft notice from it: the links, the contact, the audience,
  the note, the purposes and every language, under a code of the project's
  own, nothing approved. That notice then goes the way every notice goes:
  each language approved, each purpose active, published
  (`domain/notices/templates.py`, `apply`).
- **The notice remembers its template, and nothing more.**
  `notice.template_id` records which template it came from. Changing the
  template afterwards reaches no notice already made from it. Two projects
  that use one template have two notices.
- **Retired, never deleted.** A template that should no longer be used is
  retired, and can be brought back. A retired template cannot be attached;
  the refusal says to ask the Privacy Office which to use. The notices made
  from it point at it, so it stays.
- **Where the DPO starts.** *New notice template* is on the DPO's dashboard
  and on the Notices screen (7541f4f).

## Consequences

- "Which text did she agree to, for which project" keeps one answer: the
  project's notice, whose version and hash the consent records. A template
  is never in that answer.
- A correction to a template does not reach the projects already using it.
  Each project's notice is changed through its own versioning, as any
  notice is. This is deliberate: a template edit silently changing a served
  notice would change consent evidence.
- A template may carry a purpose still in draft. The project's notice
  cannot be published until the DPO activates it, which the notice
  checklist says.
- Templates are DPO-wide, not scoped to any project. Anyone holding a
  template's ID and the notice author's role can read it; the ID is an
  identifier, not a secret, and a template holds no personal data of a data
  principal.
- The demo seed (`scripts/seed.py`) creates no template yet.

## Revisit when

The office wants template changes to flow to the projects using them, which
would need a link, a versioning rule and Legal's view of re-consent; Legal
wants templates approved before they are handed out; or templates need
scoping, for instance per department.
