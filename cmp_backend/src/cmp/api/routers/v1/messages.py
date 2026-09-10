"""The words of every message the platform sends - 5 endpoints.

Every junction in `cmp.core.messages` is listed with its variables, the
default words, and the words in force. The administrator and the DPO may
replace the subject and body per channel, preview the result with sample
values, and reset to the default. Nothing here can add a junction: that is a
code change, and the moment it lands the junction appears in this list.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path
from pydantic import Field

from cmp.api.dependencies import RequireResource
from cmp.auth.identity import Principal
from cmp.core.messages import MAX_EMAIL_BODY_CHARS, MAX_SUBJECT_CHARS
from cmp.db.pool import connection, transaction
from cmp.domain.messaging import service
from cmp.schemas.common import Out, Schema

router = APIRouter(prefix="/messages", tags=["messages"])

MessageReader = Annotated[Principal, Depends(RequireResource("message_template"))]
MessageWriter = Annotated[Principal, Depends(RequireResource("message_template", write=True))]

KeyPath = Annotated[str, Path(pattern=r"^[a-z_]{1,64}$")]
ChannelPath = Annotated[str, Path(pattern=r"^(email|sms)$")]


class VariableOut(Out):
    name: str
    description: str
    sample: str


class ChannelOut(Out):
    channel: str
    default_subject: str | None
    default_body: str
    #: The words in force: the office's if set, else the default.
    subject: str | None
    body: str
    customised: bool
    updated_at: datetime | None
    updated_by_name: str | None


class MessageOut(Out):
    key: str
    title: str
    description: str
    group: str
    variables: list[VariableOut]
    channels: list[ChannelOut]


class TemplateIn(Schema):
    """The words. `subject` is required for email and refused for SMS; the
    service says which, with every other problem, in one answer."""

    subject: Annotated[str | None, Field(default=None, max_length=MAX_SUBJECT_CHARS)] = None
    body: Annotated[str, Field(min_length=1, max_length=MAX_EMAIL_BODY_CHARS)]


class PreviewOut(Out):
    channel: str
    subject: str | None
    body: str


@router.get("", response_model=list[MessageOut], summary="Every message, with the words in force")
async def list_messages(principal: MessageReader) -> list[dict[str, Any]]:
    async with connection() as conn:
        return await service.catalogue(conn)


@router.get("/{key}", response_model=MessageOut, summary="One message")
async def get_message(key: KeyPath, principal: MessageReader) -> dict[str, Any]:
    async with connection() as conn:
        return await service.one(conn, key)


@router.post(
    "/{key}/{channel}/preview",
    response_model=PreviewOut,
    summary="Render words with sample values, saving nothing",
)
async def preview_message(
    key: KeyPath, channel: ChannelPath, body: TemplateIn, principal: MessageReader
) -> dict[str, Any]:
    return service.preview(key, channel, body.subject, body.body)


@router.put("/{key}/{channel}", response_model=MessageOut, summary="Replace the words")
async def save_message(
    key: KeyPath, channel: ChannelPath, body: TemplateIn, principal: MessageWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        return await service.save(
            conn,
            key=key,
            channel=channel,
            subject=body.subject,
            body=body.body,
            actor_id=principal.user_id,
        )


@router.delete("/{key}/{channel}", response_model=MessageOut, summary="Back to the default")
async def reset_message(
    key: KeyPath, channel: ChannelPath, principal: MessageWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        return await service.reset(conn, key=key, channel=channel, actor_id=principal.user_id)
