"""How CMP judges an asset's subjects (brief: "Asset events", verdict table).

One verdict per person, and one for the asset - the strictest of them:

* `valid` - a consent was in force at capture and still is; the asset may be
  used for the purposes granted.
* `restricted` - in force at capture, withdrawn or expired since, or nothing is
  granted any more.
* `invalid` - no consent in force at capture, or the IDs do not belong together
  (the person, the project or the lab site does not match the consent).
* `unknown` - CMP has no record of the consent ID.

`MockConsentResolver` reads a fixture file. The real resolver will read the
consent register (`v_current_consent` and its supersession chain) and replace
it behind the same `ConsentResolver` protocol, so the endpoints do not change.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Protocol
from uuid import UUID

from pydantic import AwareDatetime

from cmp.integration.databank.contracts import (
    AssetRecord,
    ConsentRecord,
    ConsentState,
    Contract,
    SubjectVerdict,
    Verdict,
    strictest,
)

#: The fixtures that ship with the stub: the brief's own example IDs, and one
#: consent for each verdict.
DEFAULT_FIXTURES = Path(__file__).with_name("fixtures.json")


class StubConsent(ConsentRecord):
    """A consent as the mock knows it: the record CMP shares, plus what CMP
    keeps to itself - where and when it was given."""

    site_id: UUID
    #: When the first consent in the chain was given.
    given_at: AwareDatetime


class ConsentResolver(Protocol):
    def lookup(self, consent_id: UUID) -> ConsentRecord | None:
        """The current state of the chain any consent ID belongs to."""
        ...

    def judge(self, asset: AssetRecord) -> tuple[Verdict, list[SubjectVerdict]]:
        """The asset's verdict and one per subject."""
        ...


class _Fixtures(Contract):
    consents: list[StubConsent]


class MockConsentResolver:
    """A consent register read from a JSON file."""

    def __init__(self, consents: list[StubConsent]) -> None:
        self._by_id: dict[UUID, StubConsent] = {}
        for record in consents:
            for consent_id in record.consent_ids:
                self._by_id[consent_id] = record

    @classmethod
    def from_file(cls, path: str | Path | None = None) -> MockConsentResolver:
        raw = json.loads(Path(path or DEFAULT_FIXTURES).read_text())
        return cls(_Fixtures.model_validate(raw).consents)

    def lookup(self, consent_id: UUID) -> ConsentRecord | None:
        record = self._by_id.get(consent_id)
        if record is None:
            return None
        # The shared record only: where and when it was given stay in CMP.
        return ConsentRecord.model_validate(record.model_dump(exclude={"site_id", "given_at"}))

    def judge(self, asset: AssetRecord) -> tuple[Verdict, list[SubjectVerdict]]:
        verdicts = [self._judge_subject(asset, s.person_id, s.consent_id) for s in asset.subjects]
        return strictest([v.verdict for v in verdicts]), verdicts

    def _judge_subject(
        self, asset: AssetRecord, person_id: UUID, consent_id: UUID
    ) -> SubjectVerdict:
        record = self._by_id.get(consent_id)
        if record is None:
            return SubjectVerdict(person_id=person_id, verdict=Verdict.UNKNOWN)
        belongs = (
            record.person_id == person_id
            and record.project_id == asset.project_id
            and record.site_id == asset.site_id
        )
        captured: datetime = asset.captured_at
        ended = record.state in (ConsentState.WITHDRAWN, ConsentState.EXPIRED)
        in_force_at_capture = captured >= record.given_at and not (
            ended and captured >= record.changed_at
        )
        if not belongs or not in_force_at_capture:
            return SubjectVerdict(person_id=person_id, verdict=Verdict.INVALID)
        granted = [p.code for p in record.purposes if p.granted]
        if ended or not granted:
            return SubjectVerdict(person_id=person_id, verdict=Verdict.RESTRICTED)
        return SubjectVerdict(person_id=person_id, verdict=Verdict.VALID, purposes=granted)
