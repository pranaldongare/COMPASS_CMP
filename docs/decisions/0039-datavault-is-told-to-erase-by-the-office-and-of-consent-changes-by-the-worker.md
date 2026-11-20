# 0039. DataVault is told to erase by the office, and of consent changes by the worker

**Status:** accepted · 2026-11-13. Migration 0071. Follows [0038](0038-datavault-is-asked-by-the-platform-at-an-address-the-administrator-sets.md),
which asked DataVault what it holds and left erasure and consent changes
undecided. The unmerged branch `feature/datavault-integration` (ADR 0036
there) built both differently; it stays unmerged, and nothing is taken from it
but the contract handed to DataVault's developer on 2026-11-04, whose two calls
these are.

## Context

The lookup was tested against DataVault and works. Its team then asked for
the two calls after it:

    POST {erasure address}/erasures
    {"erasure_id", "request_id", "person_id",
     "assets": [{"asset_id", "consent_id"}, ..]}
    200 {"erasure_id", "assets": [{"asset_id", "status"}, ..]}

    POST {erasure address}/consent-changes
    {"message_id", "sequence", "person_id", "project_id", "consent_id",
     "consent_ids", "change", "action", "purposes_granted", "purposes_removed",
     "effective_at"}
    200 {"message_id", "result", "assets_affected"}

They are answered at an address of their own. DataVault's first build keys
what it holds by the numbers the console shows, and will move to uuids later.
The product owner settled the rest on 2026-11-13, one question at a time.

## Decision

1. **One switch for how things are named**, on the connection page: numeric
   IDs (Person ID, Consent ID, Project ID, and the request's reference as
   `request_id`) or uuids, for the person, the consent and the project in all
   three calls, the lookup included. Numeric to start; numbers go as JSON
   numbers. What names a message itself - `erasure_id`, `message_id` - is
   always a uuid. An asset goes back with the consent DataVault gave for it at
   the check, as it gave it, a number as a number.
2. **A second address, the same key.** Erasures and consent changes go to
   the erasure address; there is no third field.
3. **Erasure is a button, never automatic.** "Erase in DataVault" is offered
   on an erasure request once it is in progress - identity verified, classified
   as erasure, the intent confirmed, still open - with a check DataVault has
   answered, and while no legal hold stands on the person. Before that it is
   greyed out with the reason. A pop-up confirms it with the number of assets.
4. **What goes is what the last check listed and the request reaches.** A
   request is one office's, and so is what it erases: it reaches the assets
   matched to the person's records in its own office - DataVault's consent one
   of hers there, or its project one she gave a consent on there. A request
   confined to one consent reaches only the assets tagged with that consent or
   another of its chain. An asset DataVault gave no consent for is not sent:
   the contract sends each asset back with its consent. The rest - the other
   office's, and anything matching nothing of hers - are left out and shown so.
   Of what it reaches, a press sends what has not been sent and what DataVault
   did not erase, each once.
5. **Check status repeats the instruction.** The same `erasure_id` and the
   same assets ask how far each has got and start nothing new. It is a button
   too, and it works after the request has closed. An instruction is named as
   DataVault first took it: one it never answered is named as the switch says
   when it is sent again. While a legal hold stands, an instruction DataVault
   has never answered is not sent again - for all the platform knows,
   DataVault never received it. One DataVault refused outright (a 4xx but a
   timeout or too many at once) it never took: its assets are marked not
   erased, with why, and a later press sends them under a new `erasure_id`.
   **The last look (2026-11-20, review ARCH-8; Legal and Engineering agreed
   the cut-off).** Each instruction is made ready and committed, then sent
   with no transaction open. Just before it goes, a short transaction takes
   a lock per person that placing a hold on that person also takes, and reads
   the hold, the request's state and its office afresh: a hold placed, the
   request closed or moved to the other office since it was made ready
   withholds it, and it waits, unanswered, for "Check status". That commit is
   the point after which the instruction is DataVault's: a hold placed after
   it is recorded after the instruction went, which is accepted. An
   instruction DataVault has already answered may always be asked about
   again: it has it.
6. **Closing does not wait for DataVault.** The page shows each asset's
   status and warns before closing how many are still pending.
7. **Every consent change is told, by the worker.** A withdrawal in full or
   in part, a second consent that declines or grants purposes, and a validity
   that runs out (by the retention sweep's own test, a daily run) - on every
   consent, an HR activity's included. The action is `restrict` or
   `lift_restriction`, never a deletion: deletion only comes through an erasure
   the office decided.
8. **Worked out from what was saved, not inside the consent flow.** The
   worker reads the consents it has not read, chain by chain, and queues one
   message for where each chain now stands; each message carries the whole
   state, so a later one sets an earlier unsent one aside. A saved consent
   nudges the worker after its commit; a run every minute is the net under it.
   Messages are retried until DataVault answers `applied`, `duplicate` or
   `stale`.
9. **Off until the administrator says so, and never about the past.** A
   switch on the connection page. The first time it is switched on fixes where
   consent changes start: no consent on record then is read, and no validity
   that had run out by then is reported. What happens afterwards is told,
   whatever the consent's age.
10. **On the trail of all three.** A consent change is recorded when queued
    and when delivered, on the consent, against the person, and read with the
    project's trail. An erasure is recorded on the request. The trail keeps
    counts, codes and purpose codes - never an asset, a path or DataVault's
    reason (ADR 0015).

## Consequences

- Nothing in the consent flow can fail for DataVault. The nudge is queued
  after the commit and cannot raise; the worker takes a chain's capture lock
  without waiting, so a consent being saved is left to finish and read on the
  next run. The cost is a delay of up to a minute when the broker is down.
- Reading several unread consents at once gives the answer reading them one
  by one would: each is folded in order into what DataVault was last told,
  and only the end is sent. A withdrawal never lifts a restriction, and a
  purpose whose validity has run out stays out though a withdrawal copies its
  grant forward. A change that both takes one purpose away and gives another
  back says `partly_withdrawn` and `restrict`, with every purpose now granted.
- The switch-on point is kept once and never moves. Switched off and on
  again, the changes made meanwhile are read then.
- A refused message (4xx) is retried hourly and logged as an error; a passing
  failure (timeout, unreachable, 5xx) waits longer each time, up to an hour.
  The connection page shows how many wait, when the last was delivered, and
  why the last try failed.
- A worker may be the only one there is, sending sign-in codes too. A run
  stops delivering at the first try DataVault does not answer, and no run
  delivers for the next minute; a run also stops after ninety seconds of
  delivering, well inside its five-minute lock. So a DataVault that is down
  costs one wait of the call's timeout a minute, however many consents are
  saved meanwhile.
- The fold measures whether a purpose had run out at the withdrawal's own
  moment, so a withdrawal reads the same however late it is read. The nightly
  run reads every lapse, a page at a time.
- Where consent changes start is put a minute back from the first switch-on:
  a consent still being saved then is read, at the cost of telling DataVault
  of up to a minute of the past.
- Presses of Erase on one request are taken one at a time.
- More than a thousand assets go as several instructions (the contract's
  limit). An answer about an asset the instruction did not name is not kept.
- The erase and status calls run with no transaction open; the instruction
  and its assets are committed first, so an unanswered call leaves something
  to ask about again.
- Nothing crosses the relay. The portal makes no new call.

## Not decided here

- A withdrawal of a purpose whose lawful basis is a legitimate use (s.7): the
  person is told its processing continues, but DataVault is told it is
  withdrawn like any other, the cautious side. The product owner to say.

- Whether a new asset a later check lists, under a request already sent, is
  sent by a second press (it is, today) or needs its own confirmation.
- Telling the person what DataVault erased.
- Retiring numeric IDs once DataVault keys by uuid: the switch stays until
  then.
