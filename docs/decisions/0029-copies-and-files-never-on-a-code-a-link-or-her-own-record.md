# 0029. The office copies emails and attaches files, never on a code, a link or a person's own record

**Status:** accepted · 2026-10-08; extended 2026-10-08 (copies from the
deployment's settings - see the end). Migration 0046, commit 0359149; outside
holders' emails from migration 0049
([ADR 0024](0024-a-rights-tickets-holder-is-reached-three-ways.md)). Builds
on [ADR 0012](0012-side-effects-after-commit.md) (every email after the
commit) and [ADR 0016](0016-personal-data-sealed-by-a-separate-key-service.md)
(the worker opens what it sends).

## Context

Every email went to one recipient, with no copy and no file. The Privacy
Office wanted some copied: a ticket to a holder copied to the team mailbox
that follows it up, a project waiting for approval copied to an approvals
inbox. It also wanted a few emails to carry a file, so that a person did not
have to sign in to read something already hers.

Both are ways for data to leave the platform for somebody it was not
addressed to. A copy of a sign-in code hands the account to the person
copied. A copy of a consent receipt or a rights response tells somebody she
did not choose what she agreed to or asked for. A file on an email cannot be
withdrawn, its download cannot be audited, and it does not expire.

The plan of 2026-10-08 ([implementation-plan.md](../notifications/implementation-plan.md))
was decided with the product owner on that basis.

## Decision

- **No email is copied by default.** The office may copy an email to up to
  five addresses, chosen per email in *Message templates → Copy to*
  (`PUT /messages/{key}/copies`). The copies get the same email, in `Cc`.
  An SMS is never copied.
- **Only work between the office, its staff and its holders may be copied.**
  `COPYABLE` in `backend/api/src/cmp/core/messages.py` lists those emails.
  `deliver()` adds copies only to an email on that list, whatever the table
  holds, and the service refuses to set copies on any other. Two kinds are
  never copied:
  - an email carrying **a code or a link** - sign-in, sign-up, password
    reset, invitation, nomination, temporary access, an outside holder's
    ticket link or its code - because a copy hands somebody else the key;
  - an email to **a person about her own data** - a consent receipt, a
    withdrawal, a rights response, a breach notice - because a copy
    discloses her data to somebody she did not choose.
- **Copy addresses are sealed.** `message_copy` (migration 0046): one row per
  address per email, the address sealed with a blind index so it is listed
  once per email. It is configuration, not evidence: rows are replaced when
  the office changes its mind. Every change is on the trail with the count,
  never an address. The worker opens the addresses at `deliver()`, as it
  opens the recipient.
- **Files only where the recipient already owns them.** `ATTACHABLE` lists
  two emails:
  - the **consent receipt**, carrying her own consent record;
  - a **ticket message** to a rights ticket's holder, carrying the file the
    office put on that message for that holder.

  `deliver()` refuses a file on any other email. At most 10 MB of files per
  email; an SMS carries none.
- **A rights response stays download-only.** It is her data. Downloading it
  from her account is audited and its window closes
  (`RIGHTS_DOWNLOAD_TTL_DAYS`); an attachment could do neither.
- **A breach ticket's files never travel by email.** Breach ticket emails
  never name the breach (BD-18); the holder reads the thread and its files
  in the console.
- **An outside holder gets the link, never the request.** Every email about
  a rights ticket to an address outside the organisation is *Ticket link to
  an outside holder*: what happened, the date and the link
  (ADR 0024). It carries no file, since the ticket message that may is not
  sent to them, and is never copied, since it carries a link.

## Consequences

- A copy follows the office's choice for every email of that kind, not for
  one email. The office cannot copy a single message by hand.
- A team mailbox copied on a holder's ticket email receives the request's
  detail, as the holder does. That is the office's choice for that email,
  and only for holders inside the organisation, who are sent it in full.
- The lists are code. Making a new email copyable or attachable is a
  deliberate change to `core/messages.py`, seen in review, and the
  generated module documents show the result
  (`docs/tools/generate-email-docs.py`).
- A file a holder is sent by email has left the platform. The thread keeps
  its hash and the download is on the trail; the copy in the mailbox is
  beyond either.
- Copies are read from a Redis mirror of the settings and opened at
  `deliver()`. A copy address the key service cannot open holds the whole
  email back: it is not sent without its copies, and is retried when the
  key service is down, as a recipient that cannot be opened is.

## Revisit when

The office wants a copy on a single email rather than on every email of a
kind; a person asks for her rights response by email; a breach ticket email
needs to carry evidence; or an SMS needs copying.

## Extended 2026-10-08: copies set in the deployment's settings

`EMAIL_CC_ADDRESSES` in the API's `.env` names up to five addresses copied on
every copyable email, after the office's own copies, each once and never the
recipient (`infrastructure/messaging`, `deliver`). The same rule binds it: it
never reaches an email with a code, a link or a person's own record, whatever
the setting holds. It is for a deployment that wants one mailbox to follow
all the office's work without the office setting it email by email. The
addresses are checked when the API and worker start; Message templates shows
how many there are, never which, since they are the deployment's to change. A
copyable email may now carry up to ten copies: five the office sets, five the
deployment does.

