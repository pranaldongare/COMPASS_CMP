"""The contracts, as the brief proposes them (sections "Metadata schema" and
"API contracts").

Version 1, in the path. Within a version a change only adds fields, so these
models *ignore* a field they do not know rather than refuse it - the other side
may be one release ahead. Every identifier CMP issues is a UUID; the lab's
`asset_id` is an opaque string.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

API_VERSION = "v1"
PREFIX = f"/integration/{API_VERSION}"
SCHEMA_VERSION = "1.0"


class Contract(BaseModel):
    """Base for every message in either direction."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True, use_enum_values=True)


#: The lab's asset ID: opaque, never reused, never built from a name.
AssetId = str


# ------------------------------------------------------------------ enums


class AssetType(StrEnum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    SENSOR = "sensor"
    DOCUMENT = "document"
    OTHER = "other"


class OtherPersons(StrEnum):
    """Anyone in the asset with no consent record."""

    NONE = "none"
    INCIDENTAL = "incidental"
    UNIDENTIFIED = "unidentified"


class EventType(StrEnum):
    REGISTERED = "registered"
    UPDATED = "updated"
    DELETED = "deleted"
    RELEASED = "released"


class DeleteReason(StrEnum):
    INSTRUCTION = "instruction"
    RETENTION = "retention"
    QUALITY = "quality"
    DUPLICATE = "duplicate"
    OTHER = "other"


class Verdict(StrEnum):
    """CMP's judgement of a subject, and of the asset (the strictest of them)."""

    VALID = "valid"
    RESTRICTED = "restricted"
    INVALID = "invalid"
    UNKNOWN = "unknown"


#: Strictest first: an asset takes the first of these any subject has.
VERDICT_STRICTNESS: tuple[Verdict, ...] = (
    Verdict.INVALID,
    Verdict.UNKNOWN,
    Verdict.RESTRICTED,
    Verdict.VALID,
)


class EventStatus(StrEnum):
    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"
    IGNORED_STALE = "ignored_stale"
    REJECTED = "rejected"


class ConsentState(StrEnum):
    IN_FORCE = "in_force"
    PARTLY_WITHDRAWN = "partly_withdrawn"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class AssetState(StrEnum):
    """Databank's four states; only `usable` allows use."""

    QUARANTINED = "quarantined"
    USABLE = "usable"
    RESTRICTED = "restricted"
    ERASED = "erased"


class Action(StrEnum):
    RESTRICT = "restrict"
    LIFT_RESTRICTION = "lift_restriction"
    ERASE = "erase"
    REDACT = "redact"
    HOLD = "hold"
    RELEASE_HOLD = "release_hold"


class InstructionReason(StrEnum):
    RIGHTS_REQUEST = "rights_request"
    CONSENT_WITHDRAWN = "consent_withdrawn"
    RETENTION_LAPSED = "retention_lapsed"
    LEGAL_HOLD = "legal_hold"


class Outcome(StrEnum):
    DONE = "done"
    PARTIAL = "partial"
    FAILED = "failed"


# ------------------------------------------------------- the lab delivery


class Subject(Contract):
    """One consenting person in an asset. Both IDs travel together, so CMP can
    reject a pair that does not belong together."""

    person_id: UUID
    consent_id: UUID


class DeliveredAsset(Contract):
    asset_id: AssetId = Field(min_length=1, max_length=128)
    asset_type: AssetType
    #: When it was captured, with its offset - not the upload time.
    captured_at: AwareDatetime
    subjects: list[Subject] = Field(min_length=1)
    other_persons: OtherPersons = OtherPersons.NONE


class Delivery(Contract):
    """What a lab sends with a delivery, in place of the consent PDF reference."""

    #: A delivery without it is treated as legacy.
    schema_version: str = SCHEMA_VERSION
    project_id: UUID
    site_id: UUID
    batch_ref: str = Field(min_length=1, max_length=128)
    declared_asset_count: int = Field(ge=0)
    assets: list[DeliveredAsset]


# ------------------------------------------------- call 1: asset events


class AssetRecord(DeliveredAsset):
    """An asset as Databank holds it."""

    asset_version: int = Field(ge=1)
    project_id: UUID
    site_id: UUID
    batch_ref: str
    content_sha256: str = Field(min_length=1, max_length=128)


class Release(Contract):
    recipient: str = Field(min_length=1, max_length=200)
    released_on: date


class AssetEvent(Contract):
    event_id: UUID
    type: EventType
    occurred_at: AwareDatetime
    #: The full record for `registered` and `updated`.
    asset: AssetRecord | None = None
    #: For `deleted` and `released`, which name the asset only.
    asset_id: AssetId | None = None
    reason: DeleteReason | None = None
    release: Release | None = None

    @model_validator(mode="after")
    def _shape(self) -> AssetEvent:
        if self.type in (EventType.REGISTERED, EventType.UPDATED) and self.asset is None:
            raise ValueError(f"a {self.type} event carries the full asset record")
        if self.type in (EventType.DELETED, EventType.RELEASED) and not (
            self.asset_id or self.asset
        ):
            raise ValueError(f"a {self.type} event names its asset_id")
        if self.type == EventType.DELETED and self.reason is None:
            raise ValueError("a deleted event carries its reason")
        if self.type == EventType.RELEASED and self.release is None:
            raise ValueError("a released event carries the recipient and the date")
        return self

    @property
    def target(self) -> AssetId:
        return self.asset.asset_id if self.asset else str(self.asset_id)


class AssetEvents(Contract):
    events: list[AssetEvent] = Field(min_length=1, max_length=500)


class SubjectVerdict(Contract):
    person_id: UUID
    verdict: Verdict
    #: Granted purposes, for a valid verdict.
    purposes: list[str] = Field(default_factory=list)


class EventResult(Contract):
    event_id: UUID
    status: EventStatus
    asset_id: AssetId
    #: For registered and updated: the asset's verdict, the strictest of its subjects'.
    verdict: Verdict | None = None
    subjects: list[SubjectVerdict] = Field(default_factory=list)
    detail: str | None = None


class AssetEventResults(Contract):
    results: list[EventResult]


# -------------------------------- calls 2 and 4: one consent record, both ways


class PurposeGrant(Contract):
    code: str
    granted: bool


class ConsentRecord(Contract):
    """The record Databank asks for (call 2) and CMP sends (call 4)."""

    #: Every consent ID in the chain: an asset tagged with any takes this state.
    consent_ids: list[UUID] = Field(min_length=1)
    current_consent_id: UUID
    person_id: UUID
    project_id: UUID
    state: ConsentState
    purposes: list[PurposeGrant]
    changed_at: AwareDatetime


class ConsentEvent(Contract):
    event_id: UUID
    consent: ConsentRecord


class ConsentEvents(Contract):
    events: list[ConsentEvent] = Field(min_length=1, max_length=500)


class Acknowledgement(Contract):
    accepted: list[UUID]
    duplicates: list[UUID] = Field(default_factory=list)


# ------------------------------------------------------- call 3: inventory


class InventoryAsset(Contract):
    asset_id: AssetId
    asset_version: int
    asset_type: AssetType
    captured_at: AwareDatetime
    project_id: UUID
    consent_id: UUID
    state: AssetState
    derivatives: int = 0
    releases: list[Release] = Field(default_factory=list)


class Inventory(Contract):
    person_id: UUID
    #: From a search of Databank's own index, not from what CMP told it.
    assets: list[InventoryAsset]


# --------------------------------------------- calls 5 and 6: instructions


class InstructionItem(Contract):
    asset_id: AssetId
    action: Action


class Instruction(Contract):
    instruction_id: UUID
    reason: InstructionReason
    #: CMP's own reference, e.g. the rights request it answers.
    reference: str | None = None
    person_id: UUID
    issued_at: AwareDatetime
    due_at: AwareDatetime | None = None
    items: list[InstructionItem] = Field(min_length=1, max_length=1000)


class InstructionAccepted(Contract):
    instruction_id: UUID
    status: str = "accepted"
    duplicate: bool = False


class ErasureEvidence(Contract):
    content_sha256: str | None = None
    derivatives_deleted: int | None = None
    backups_expire_on: date | None = None


class ItemResult(Contract):
    asset_id: AssetId
    action: Action
    outcome: Outcome
    completed_at: AwareDatetime | None = None
    reason: str | None = None
    evidence: ErasureEvidence | None = None


class InstructionResult(Contract):
    """May arrive in parts as items finish: an early partial result is better
    than a late complete one."""

    instruction_id: UUID
    items: list[ItemResult] = Field(min_length=1)


class InstructionStatus(Contract):
    """CMP's acknowledgement of a result: where the instruction now stands."""

    instruction_id: UUID
    items_reported: int
    items_done: int
    #: CMP closes a request only when every item is done.
    complete: bool


def strictest(verdicts: list[Verdict]) -> Verdict:
    """The asset's verdict: the strictest of its subjects'."""
    for verdict in VERDICT_STRICTNESS:
        if verdict in verdicts:
            return verdict
    return Verdict.UNKNOWN


def now_aware() -> datetime:
    from datetime import UTC

    return datetime.now(UTC)
