# 0038. DataVault is asked by the platform, at an address the administrator sets

**Status:** accepted · 2026-11-13. Migration 0070. Numbered 0038 because 0036
is taken on the unmerged DataVault branch (`feature/datavault-integration`),
which this does not merge: that branch's lookup, erasure and consent-change
calls stay where they are, and this builds the one call the product owner
asked for on 2026-11-13, with its contract, on its own tables.

## Context

DataVault is the store the labs' assets live in. When a rights request comes
in, the office that answers it must know what is held there. Until now it
asked a DCO Admin, who went and looked. DataVault's team offered one call:

    GET {address}/lookup?request_id=..&person_id=..
    200 {"person_id": .., "assets": [{"asset_id", "consent_id", "project_id",
                                      "mid", "datapath"}, ..]}

The address could not be shared when the work was asked for, so it cannot be
in the code or its configuration files.

## Decision

1. **The platform makes the call; the console never does.** The DPO or the
   Legal PoC presses "Check in DataVault" on a request. The platform also asks
   by itself when the holders it finds include a project's DCO Admin and
   DataVault has not answered for that request yet. And it finds the holders
   by itself as the request starts - the move from received to in progress,
   the point at which the office has found the request valid (the product
   owner, 2026-11-13) - so for such a request the office starts it and the
   assets follow. "Find who holds the data" stays, to read again.
2. **The address and the key are the administrator's to set**, on a page of
   their own (resource `datavault_connection`, the administrator alone). The
   key is encrypted with the application key and never served again. Switched
   off, nothing is called.
3. **What is sent** is the request's reference and the person's numeric
   Person ID (the product owner's choice), and nothing else.
4. **What comes back is kept as sent** and matched to ours only among this
   person's own consents in the request's office, by uuid or by number. An
   identifier that is somebody else's, or her own consent in the other
   office's project, resolves to nothing. The office is named in the matching
   and not left to the row policy, because the platform's own check reads
   across both offices.
5. **A failure is a short code** (`timeout`, `unreachable`, `status_503`,
   `unreadable`, `too_many`). DataVault's error body is never stored, shown or
   logged. A failed check does not unsay an earlier answer.
6. **A DCO Admin holder sees their project's assets on their own ticket.**
   The office sees all of them on the request.
7. **The check changes nothing else.** It adds no holder, moves no ticket and
   decides nothing about erasure. With DataVault not set up, every screen and
   route behaves as it did before 0070.

## Consequences

- An address somebody can set is a place the platform can be pointed at. It
  is limited to one role; it must be http or https with a host and no user,
  query or fragment; redirects are not followed; and every change is on the
  trail (`datavault.connection_changed`), which records that the address or
  the key changed and never either one. The platform does not restrict which
  hosts may be named: DataVault is on the internal network, where a block
  list of private ranges would refuse the real address.
- The call is made from the API (the button) and from the worker (the
  automatic check), both inside the network. Nothing crosses the relay, and
  the portal makes no new call.
- Finding holders as a request starts changes a step every access and erasure
  request takes, DataVault or not. It is done after the move has been saved
  and apart from it, so the start cannot fail for it; the holders found are
  not confirmed; and the reading is the one the button made, so nothing is
  found that would not have been.
- No transaction is open while DataVault is waited on. The automatic check is
  retried three times, two minutes apart, for a timeout or a 5xx; each attempt
  is recorded.
- `datapath` and `mid` are DataVault's own values and are shown to the office
  and to the DCO Admin holder as sent. They are not put on the audit trail,
  which records counts only.
- The header the key travels in defaults to `X-API-Key` and can be changed on
  the same page, since DataVault's team has not named one.

## Not decided here

- Erasure in DataVault and telling it of consent changes (the earlier
  branch's calls 2 and 3).
- Showing any of this to the data principal.
- Finding holders any earlier than the start. On arrival a request may be
  nobody's office's, unverified, or not a rights request at all; nothing is
  read, and nothing is sent to DataVault, until the office has started it.
