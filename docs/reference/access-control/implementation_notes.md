# Implementation notes and documentation differences

[Guide](README.md)

These observations explain why the endpoint tables sometimes differ from general role descriptions. They describe the inspected code; they are not proposed permission changes. No application access controls were modified. Static review does not establish deployed behavior or replace runtime authorization tests.

## R&D consent access is broader than the matrix comment

The consent matrix comment says “summary counts only”. ConsentReader also gates individual lists, artefacts, grants and assets, and the repository scopes R&D to own-created projects. The reference therefore includes R&D on those endpoints.

Evidence: [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/core/permissions.py#L235), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/consents.py#L201), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/consent.py#L21).

## Admin site routing is admitted, then blocked

PUT /sites/{site_uuid}/source and /owner explicitly admit Admin. Their services subsequently require project scope, but Admin has no project grant. The endpoint matrix marks Admin NO for completing these operations and preserves the wider route guard in the detailed entry. The documented R&D in-house-only intent also has no additional type check in these service paths; ownership still applies.

Evidence: [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/projects.py#L676), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/projects/service.py#L429), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/projects/service.py#L502), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/projects.py#L82).

## R&D site changes use route behavior, not the site write cell

R&D has only a read grant on site in the static table, but site creation explicitly includes R&D and site update uses ProjectReader plus site scope without a site-write check. Own-project R&D access is included in this reference.

Evidence: [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/projects.py#L611), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/projects.py#L654), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/projects/service.py#L688).

## Unassigned import batches are visible to every signed-in role

GET /imports, /imports/{batch_uuid}, /imports/{batch_uuid}/errors and /sources/{source_uuid}/batches use CurrentUser and the predicate b.project_id IS NULL OR scoped-project. Admin and data_subject can therefore receive unassigned batches even without an import grant. This is conditional access, not an all-imports grant.

Evidence: [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/exchange.py#L374), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/registry.py#L904), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/exchange.py#L380).

## Source write permission is global for its admitted roles

DPO, Admin, DCO, DCO Admin and RCO are data_source writers. Existing-source update, owner reassignment and suspension resolve UUIDs without caller/source ownership filtering. Creating a source checks DCO/RCO processor type; that create check should not be generalized to all writes. Owner reassignment checks the target owner type.

Evidence: [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/registry.py#L664), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/registry.py#L758), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/registry.py#L816).

## Notification scope is broader than project scope

The staff notification feed reads selected global audit event types without a project ownership predicate. Resend admits DPO/DCO and resolves the event by UUID without caller scope. Principal notifications are own-subject; ticket events have separate respondent/office filters.

Evidence: [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/dashboard.py#L766), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/dashboard.py#L830).

## Delegation creation has a narrower successful role set

RequireStaff is only the outer gate. The service permits delegable roles DPO/DCO, requires same-role cover, and requires self-arrangement unless the actor is Admin. DCO Admin, RCO and R&D cannot create cover under these rules. Revocation instead checks Admin or named participant.

Evidence: [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/delegations.py#L79), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/delegations/service.py#L26).

## Rights administration has endpoint-specific exceptions

Admin reads all about-DPO rows, not just assigned-reviewer rows. Reviewer assignment is Admin-only. Deciding an about-DPO grievance is Admin-only and honors an assigned reviewer. Request creation admits Admin without an existing-row predicate, including requests it may not later read. Other DPO actions are not universally barred just because about_dpo is true.

Evidence: [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L654), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/service.py#L660), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/service.py#L2350), [source 5](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## Shared account routes and MFA cannot be inferred from their names

The profile/contact routes use CurrentUser and accept staff sessions; /me/person-type explicitly narrows to DPO/Admin/data_subject. PartialUser does not require a partial session or a staff role, and both MFA routes use it. Password/code prerequisites still apply where stated.

Evidence: [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/me.py#L212), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/dependencies/authentication.py#L61), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/auth.py#L181).

## Public consent capture has a manual session path

POST /c/{token}/consent requires a session acting as data_subject and uses server-side notice-serving evidence, but it loads the cookie with sessions.load directly. The standard session_from_request CSRF guard is not invoked by this handler. This reference does not assume it is protected by that dependency.

Evidence: [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/public/consent.py#L232), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/dependencies/sessions.py#L30).

## Three registered system routes are absent from the API docs

GET /, /health/live and /health/ready set include_in_schema=False. The new inventory includes them explicitly: 241 OpenAPI operations plus three hidden system operations. Framework-generated development documentation endpoints and CORS middleware responses are outside this business/router inventory.

Evidence: [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/system.py#L104), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/system.py#L143), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/system.py#L174).
