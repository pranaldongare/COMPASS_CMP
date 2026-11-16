# 0041. The portal's address is kept by the administrator

**Status:** accepted · 2026-11-16. Migration 0072.

## Context

Every link the platform hands to a data principal starts with the address of
her portal: a consent link copied in the console, the public link for
reporting a breach, a holder's ticket, and the links in its mail. That address
was configuration in two places - `PUBLIC_BASE_URL` for the API and the
worker, `NEXT_PUBLIC_SUBJECT_PORTAL_URL` built into the console - read when a
process starts.

The deployment has no domain name yet. It is reached at an IP that keeps
changing, and each change meant editing two files, rebuilding the console and
restarting three services, or handing out links that go nowhere. The product
owner asked on 2026-11-16 for the address to be a setting in the
administrator's account.

## Decision

1. **One row, kept by the administrator**: `portal_address.portal_url`, on the
   console's Portal address page (`GET`/`PUT /portal-address`, resource
   `portal_address`, the administrator's alone). Empty means the configured
   address, so nothing changes until it is set.
2. **An origin and nothing more**: http or https, a host, perhaps a port. No
   path, query, fragment or user - links are made by appending a path, and the
   database refuses anything else as the API does.
3. **Every link built on the server reads it** (`portal_base()`): the breach
   reporting link, an HR activity's link, a holder's ticket link, the rights
   and nomination links, and every link in mail.
4. **The console is told it, not built with it.** `GET /auth/me` carries
   `portal_url`, the address in use, and a consent link shown or copied starts
   with that. The build's own setting is only what the sign-in page, where
   nobody is signed in yet, links to.
5. **No restart.** A process keeps the address for fifteen seconds and reads
   it again; the process that saved it has it at once. The read is a short
   connection of its own, because links are also built in plain functions and
   in the worker, where no request's connection is at hand.
6. **On the trail**, with the address before and after: an address names a
   machine, not a person, and the trail should say where links pointed when.

## Consequences

- Links already handed out keep the address they were copied or mailed with.
  When the address moves, a consent link in someone's hands has to be copied
  again; the token in it is unchanged.
- If the database cannot be read, a process keeps the last address it knew,
  or the configured one.
- The address of the staff console in mail to staff (`CONSOLE_BASE_URL`), and
  where a real organisation sign-in returns to (`SSO_REDIRECT_URL`), are still
  configuration. So are the allowed origins of the dev servers and CORS: a new
  address has to be allowed there before a browser at it can use the app.

## Not decided here

- The console's address as a second setting on the same page.
