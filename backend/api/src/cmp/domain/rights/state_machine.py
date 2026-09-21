# ruff: noqa: E501 - the transition table below is transcribed from the flow
# diagrams. Re-wrapping it to 100 columns would make it unreadable.
"""The rights request state machine.

Five states, walked forward, and closure carries an outcome:

| From               | To                 | Actor          | Requires                                                              |
|--------------------|--------------------|----------------|-----------------------------------------------------------------------|
| `received`         | `in_progress`      | DPO (reviewer) | identity verified; classified; erasure: intent confirmed;             |
|                    |                    |                | nominee: event evidenced; grievance about the DPO: reviewer assigned  |
| `in_progress`      | `awaiting_holders` | DPO            | at least one ticket issued                                            |
| `in_progress`      | `collating`        | DPO            | no ticket outstanding                                                 |
| `awaiting_holders` | `collating`        | DPO            | every outstanding ticket returned, or escalated once                  |
| `collating`        | `closed`           | DPO            | via `respond`: erasure needs every scope item decided                 |

The early exits on the flow diagrams - identity not verified, not a rights
request, she meant withdrawal, the event not evidenced - are not transitions.
They are *actions* that close the request with an outcome, and they are
permitted from any open state before collation. Listing them as transitions
would make the table say something it does not mean: that a request can be
"moved to not verified" the way it is moved to in progress.

**Who acts.** The DPO owns every request. A grievance *about* the DPO is the
one exception - accountability cannot review itself and be credible - and for
those the administrator stands in as the independent reviewer. That is
expressed here as an actor set that widens when the facts say the complaint
concerns the DPO, rather than as a second table.

**The clock does not pause.** Nothing in this module reads the deadline: a
request is allowed to move late, and the lateness is recorded rather than
prevented. "Escalate once, then respond partial and on time" needs the
transition to collation to be *possible* while tickets are outstanding, which
is what the escalation requirement expresses.

Pure, like the project machine it is modelled on. It takes a status, a role
and a snapshot of facts, and returns what is permitted.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from cmp.core.enums import RightsRequestStatus as Status
from cmp.core.enums import RightsRequestType as Kind
from cmp.core.errors import TransitionNotPermitted
from cmp.core.permissions import Role


@dataclass(frozen=True, slots=True)
class RequestFacts:
    """What the machine needs to know. Assembled by the service from one row.

    A value object on purpose: the machine cannot reach back into the database
    and get a different answer halfway through a decision.
    """

    request_type: str = Kind.ACCESS.value
    verified: bool = False
    verification_failed: bool = False
    #: The DPO has confirmed what this is - or reclassified it. Free text that
    #: arrived through the public form is nothing until somebody reads it.
    classified: bool = False
    #: Erasure only: she confirmed she means erasure rather than withdrawal.
    intent_confirmed: bool = False
    #: A nominee acting: the death or incapacity is evidenced to our standard.
    nominee: bool = False
    event_evidenced: bool = False
    #: A grievance that concerns the DPO's own handling.
    about_dpo: bool = False
    reviewer_assigned: bool = False
    holders_confirmed: int = 0
    tickets_issued: int = 0
    #: Issued or escalated, and not yet returned.
    tickets_outstanding: int = 0
    #: Outstanding and never escalated. Zero means every gap has been chased.
    tickets_unescalated: int = 0
    #: Erasure only: scope items with no decision recorded.
    items_undecided: int = 0


@dataclass(frozen=True, slots=True)
class Requirement:
    met: bool
    message: str


@dataclass(frozen=True, slots=True)
class Transition:
    to: Status
    actors: frozenset[Role]
    #: `respond` for closure: the move is made by the respond action, which
    #: also records the outcome, rather than by the generic transition route.
    via: str = "transition"
    reason_required: bool = False
    requirements: tuple[Requirement, ...] = field(default_factory=tuple)

    @property
    def allowed(self) -> bool:
        return all(r.met for r in self.requirements)

    @property
    def blocked_by(self) -> str | None:
        for r in self.requirements:
            if not r.met:
                return r.message
        return None


def actors_for(f: RequestFacts) -> frozenset[Role]:
    """Who may act on a request with these facts.

    The DPO always. The administrator only where the complaint is about the
    DPO, because that is the one case in which the DPO must not be the judge.
    """
    return frozenset({Role.DPO, Role.ADMIN}) if f.about_dpo else frozenset({Role.DPO})


def may_act(role: Role | str, f: RequestFacts) -> bool:
    try:
        return Role(role) in actors_for(f)
    except ValueError:
        return False


def _start(f: RequestFacts) -> Transition:
    """Everything that has to be settled before work begins, in the order the
    flow diagrams ask the questions."""
    requirements = [
        Requirement(
            not f.verification_failed, "Identity verification failed - the request is closed"
        ),
        Requirement(f.verified, "Identity is not verified"),
        Requirement(f.classified, "The request has not been classified as a rights request"),
    ]
    if f.request_type == Kind.ERASURE:
        requirements.append(
            Requirement(
                f.intent_confirmed,
                "Whether she means withdrawal or erasure is not yet confirmed",
            )
        )
    if f.nominee:
        requirements.append(Requirement(f.event_evidenced, "The triggering event is not evidenced"))
    if f.request_type == Kind.GRIEVANCE and f.about_dpo:
        requirements.append(
            Requirement(
                f.reviewer_assigned,
                "The complaint concerns the DPO - a reviewer independent of the DPO must be assigned",
            )
        )
    return Transition(to=Status.IN_PROGRESS, actors=actors_for(f), requirements=tuple(requirements))


def _close(f: RequestFacts) -> Transition:
    requirements: list[Requirement] = []
    if f.request_type == Kind.ERASURE:
        requirements.append(
            Requirement(
                f.items_undecided == 0,
                "Every item in the erasure scope needs a decision and the basis for it",
            )
        )
    return Transition(
        to=Status.CLOSED, actors=actors_for(f), via="respond", requirements=tuple(requirements)
    )


def _transitions(status: Status, f: RequestFacts) -> list[Transition]:
    match status:
        case Status.RECEIVED:
            return [_start(f)]

        case Status.IN_PROGRESS:
            return [
                Transition(
                    to=Status.AWAITING_HOLDERS,
                    actors=actors_for(f),
                    requirements=(
                        Requirement(f.tickets_issued >= 1, "No tickets have been issued yet"),
                    ),
                ),
                Transition(
                    to=Status.COLLATING,
                    actors=actors_for(f),
                    requirements=(
                        Requirement(
                            f.tickets_outstanding == 0,
                            "Tickets are outstanding - wait for them, or escalate and proceed",
                        ),
                    ),
                ),
            ]

        case Status.AWAITING_HOLDERS:
            return [
                Transition(
                    to=Status.COLLATING,
                    actors=actors_for(f),
                    requirements=(
                        Requirement(
                            f.tickets_unescalated == 0,
                            "A holder has not returned its ticket - escalate once before "
                            "responding partial",
                        ),
                    ),
                ),
            ]

        case Status.COLLATING:
            return [_close(f)]

        case Status.CLOSED:
            # Terminal. Disagreement with the outcome is a grievance, which is a
            # new request linked to this one - not a reopening.
            return []


def available(
    status: Status | str, role: Role | str, facts: RequestFacts
) -> list[dict[str, object]]:
    """The payload behind GET /requests/{uuid}/transitions.

    Only what this role may attempt, each annotated with whether it is allowed
    now and what blocks it. The console renders these as buttons with reasons
    rather than holding a copy of the table.
    """
    st = Status(status)
    r = Role(role)
    out: list[dict[str, object]] = []
    for t in _transitions(st, facts):
        if r not in t.actors:
            continue
        entry: dict[str, object] = {"to": t.to.value, "allowed": t.allowed, "via": t.via}
        if t.blocked_by:
            entry["blocked_by"] = t.blocked_by
        if t.reason_required:
            entry["reason_required"] = True
        out.append(entry)
    return out


def validate(
    *,
    current: Status | str,
    target: Status | str,
    role: Role | str,
    facts: RequestFacts,
    reason: str | None = None,
) -> Transition:
    """Authorise one move or raise. The single gate every status change goes through.

    Ordering matches the project machine: "no such transition" before "not your
    role" before "blocked", so an unauthorised caller learns nothing about the
    request's readiness.
    """
    st, tgt, r = Status(current), Status(target), Role(role)

    match = next((t for t in _transitions(st, facts) if t.to is tgt), None)
    if match is None:
        raise TransitionNotPermitted(
            f"There is no transition from {st.value} to {tgt.value}",
            details={"from": st.value, "to": tgt.value},
        )

    if r not in match.actors:
        raise TransitionNotPermitted(
            f"{r.value} may not move a request from {st.value} to {tgt.value}",
            code="transition_role_not_permitted",
            details={
                "from": st.value,
                "to": tgt.value,
                "permitted_roles": sorted(a.value for a in match.actors),
            },
        )

    if not match.allowed:
        raise TransitionNotPermitted(
            match.blocked_by or "Preconditions are not met",
            code="transition_blocked",
            details={"from": st.value, "to": tgt.value},
        )

    if match.reason_required and not (reason or "").strip():
        raise TransitionNotPermitted(
            "A reason is required for this transition",
            code="reason_required",
            field="reason",
        )

    return match


#: The states from which an early exit - not verified, refused, reclassified as
#: withdrawal, event not evidenced - may still be taken. Once the DPO is
#: collating there is a response in preparation, and the honest path is to
#: finish it.
OPEN_BEFORE_COLLATION: frozenset[Status] = frozenset(
    {Status.RECEIVED, Status.IN_PROGRESS, Status.AWAITING_HOLDERS}
)

ALL_STATUSES: tuple[str, ...] = tuple(s.value for s in Status)
