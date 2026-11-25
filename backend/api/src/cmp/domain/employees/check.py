"""Is this account an active employee's? (2026-11-25, ADR 0046)

The organisation answers through VerifyEmail, at an address the administrator
sets, for an address on one of the organisation's own domains - a list the
administrator keeps too, and the one list of who is inside the organisation
(it replaced BREACH_TICKET_EMAIL_DOMAINS).

When it is asked, and what the answer does (the product owner, 2026-11-25):

* **Console.** At password sign-in, before the code is sent, for a member of
  staff whose email is on one of the domains. Active signs in; inactive, or no
  answer, is refused - the console fails closed. The administrator is never
  asked about, so a VerifyEmail outage cannot lock the platform out. Staff on
  any other domain sign in unchecked while `allow_other_domains` is on (it
  starts on: testing uses cmp.local and the like), and are refused once it is
  off.
* **Portal.** After a person's sign-in code is entered, by the worker, for the
  account's own company address. Never refused: a former employee is still a
  data principal, with every right over their consents. The answer is kept on
  the account, and an employee-only link refuses one found not active. No
  answer changes nothing - the portal fails open.

Switched off, nothing is asked anywhere, and sign-in is as it was before. A
change to the settings or the domains is on the trail (that the address or
key changed, never either). Each answer is on the trail against the account:
its flow and its result, never the address asked about.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from cmp.core.errors import ValidationFailed
from cmp.core.logging import get_logger
from cmp.core.security import seal_token, unseal_token
from cmp.db.repositories import employee_check as repo
from cmp.db.sql import Conn
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event
from cmp.infrastructure.datavault import usable_base_url
from cmp.infrastructure.employee_check import EmployeeCheckFailed, Verdict, verify_email

log = get_logger("cmp.employees")

Row = dict[str, Any]

DEFAULT_HEADER = "X-API-Key"
_HEADER = re.compile(r"^[A-Za-z0-9-]{1,64}$")
_RESERVED = frozenset({"host", "content-length", "content-type", "accept", "connection"})
_DOMAIN = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")

#: The flows an answer is recorded for.
CONSOLE = "console_sign_in"
PORTAL = "portal_sign_in"
TEST = "administrator_test"

#: For tests: the transport every call is made over (None: the network).
transport: Any = None

#: Why a call gave no answer, in the administrator's words.
FAILURES: dict[str, str] = {
    "timeout": "VerifyEmail did not answer in time.",
    "unreachable": "VerifyEmail could not be reached.",
    "unreadable": "VerifyEmail answered, but not in the agreed format.",
    "mismatch": "VerifyEmail answered about a different address.",
    "status_401": "VerifyEmail refused the key.",
    "status_403": "VerifyEmail refused the key.",
    "status_404": "VerifyEmail does not know this address.",
}


def failure_said(code: str) -> str:
    if code in FAILURES:
        return FAILURES[code]
    if code.startswith("status_"):
        return f"VerifyEmail answered with an error ({code.removeprefix('status_')})."
    return "VerifyEmail gave no answer."


@dataclass(frozen=True)
class Link:
    base_url: str
    api_key: str | None
    api_key_header: str


@dataclass(frozen=True)
class Settings:
    """What sign-in needs to know, read once per sign-in."""

    link: Link | None
    domains: frozenset[str]
    allow_other_domains: bool


@dataclass(frozen=True)
class Answer:
    """`active`, `inactive`, `failed` (with `code`), or `off` (not asked)."""

    result: str
    code: str | None = None

    @property
    def active(self) -> bool:
        return self.result == Verdict.ACTIVE


# -------------------------------------------------------------- the domains
def domain_of(email: str | None) -> str | None:
    if not email or "@" not in email:
        return None
    return email.rsplit("@", 1)[1].strip().lower() or None


def on_domains(email: str | None, domains: frozenset[str] | set[str]) -> bool:
    """On one of the domains, or a subdomain of one (mail.company.example is
    the company's as company.example is)."""
    domain = domain_of(email)
    if domain is None:
        return False
    return any(domain == d or domain.endswith(f".{d}") for d in domains)


async def company_domains(conn: Conn) -> frozenset[str]:
    """The organisation's own domains, as the administrator keeps them."""
    return frozenset(await repo.domains(conn))


async def is_company_address(conn: Conn, email: str | None) -> bool:
    """Inside the organisation: on one of its domains. The one test - breach
    and rights tickets ask it too."""
    return on_domains(email, await company_domains(conn))


def _clean_domain(raw: str) -> str:
    domain = raw.strip().lower().lstrip("@")
    if len(domain) > 253 or not _DOMAIN.match(domain):
        raise ValidationFailed(
            "Enter a domain such as company.example: letters, digits, hyphens and dots, "
            "with no @ or address before it.",
            field="domain",
        )
    return domain


async def add_domain(conn: Conn, raw: str, *, actor_id: int) -> list[Row]:
    domain = _clean_domain(raw)
    if await repo.add_domain(conn, domain, actor_id=actor_id):
        await audit.record(
            conn,
            event=Event.ORGANISATION_DOMAIN_ADDED,
            entity_type="employee_check_connection",
            entity_id=1,
            actor_user_id=actor_id,
            detail={"domain": domain},
        )
    return await repo.domain_rows(conn)


async def remove_domain(conn: Conn, raw: str, *, actor_id: int) -> list[Row]:
    domain = raw.strip().lower()
    row = await repo.connection(conn)
    remaining = [d for d in await repo.domains(conn) if d != domain]
    if not remaining and not row["allow_other_domains"]:
        raise ValidationFailed(
            "Keep at least one domain while staff on other domains are refused: "
            "otherwise no member of staff but the administrator could sign in.",
            field="domain",
        )
    if await repo.remove_domain(conn, domain):
        await audit.record(
            conn,
            event=Event.ORGANISATION_DOMAIN_REMOVED,
            entity_type="employee_check_connection",
            entity_id=1,
            actor_user_id=actor_id,
            detail={"domain": domain},
        )
    return await repo.domain_rows(conn)


# -------------------------------------------------------------- the settings
def _view(row: Row, domains: list[Row]) -> Row:
    return {
        "base_url": row["base_url"],
        "api_key_set": row["api_key_sealed"] is not None,
        "api_key_header": row["api_key_header"],
        "enabled": bool(row["enabled"]),
        "allow_other_domains": bool(row["allow_other_domains"]),
        "domains": domains,
        "updated_at": row["updated_at"] if row["updated_by_name"] is not None else None,
        "updated_by_name": row["updated_by_name"],
    }


async def overview(conn: Conn) -> Row:
    return _view(await repo.connection(conn), await repo.domain_rows(conn))


async def settings_for_sign_in(conn: Conn) -> Settings:
    row = await repo.connection(conn)
    link = None
    if row["enabled"] and row["base_url"]:
        link = Link(
            base_url=str(row["base_url"]),
            api_key=unseal_token(bytes(row["api_key_sealed"])) if row["api_key_sealed"] else None,
            api_key_header=str(row["api_key_header"]),
        )
    return Settings(
        link=link,
        domains=await company_domains(conn),
        allow_other_domains=bool(row["allow_other_domains"]),
    )


async def save(
    conn: Conn,
    *,
    base_url: str | None,
    api_key: str | None,
    clear_api_key: bool,
    api_key_header: str | None,
    enabled: bool,
    allow_other_domains: bool,
    actor_id: int,
) -> Row:
    """`api_key` None keeps the key that is there; `clear_api_key` removes it."""
    before = await repo.connection(conn)
    address: str | None = None
    if base_url and base_url.strip():
        address = usable_base_url(base_url)
        if address is None:
            raise ValidationFailed(
                "Enter the address as http:// or https:// and a host, with no user name, "
                "question mark or # in it. /VerifyEmail is added to it.",
                field="base_url",
            )
        if address.lower().endswith("/verifyemail"):
            raise ValidationFailed(
                "Enter the address without /VerifyEmail: the platform adds it.",
                field="base_url",
            )
    if enabled and address is None:
        raise ValidationFailed("Enter VerifyEmail's address before switching it on.")
    if not allow_other_domains and not await repo.domains(conn):
        raise ValidationFailed(
            "Add the organisation's domains before refusing staff on other domains: "
            "otherwise no member of staff but the administrator could sign in.",
            field="allow_other_domains",
        )
    header = (api_key_header or DEFAULT_HEADER).strip()
    if not _HEADER.match(header) or header.lower() in _RESERVED:
        raise ValidationFailed(
            "The header name may hold letters, digits and hyphens only, and cannot be "
            "one the call itself sets.",
            field="api_key_header",
        )
    key = api_key.strip() if api_key else None
    if key is not None and (len(key) > 4000 or any(ord(c) < 32 or ord(c) > 126 for c in key)):
        raise ValidationFailed("The key may hold printable characters only.", field="api_key")
    keep = key is None and not clear_api_key
    await repo.save_connection(
        conn,
        base_url=address,
        api_key_sealed=seal_token(key) if key else None,
        keep_key=keep,
        api_key_header=header,
        enabled=enabled,
        allow_other_domains=allow_other_domains,
        actor_id=actor_id,
    )
    changed = {
        "address_changed": address != before["base_url"],
        "key_changed": not keep,
        "enabled": enabled,
        "allow_other_domains": allow_other_domains,
    }
    await audit.record(
        conn,
        event=Event.EMPLOYEE_CHECK_CHANGED,
        entity_type="employee_check_connection",
        entity_id=1,
        actor_user_id=actor_id,
        detail=changed,
    )
    return await overview(conn)


# ----------------------------------------------------------------- the check
async def ask(link: Link | None, email: str) -> Answer:
    """One call, as an answer - never an exception."""
    if link is None:
        return Answer("off")
    try:
        verdict = await verify_email(
            base_url=link.base_url,
            email=email,
            api_key=link.api_key,
            api_key_header=link.api_key_header,
            transport=transport,
        )
    except EmployeeCheckFailed as exc:
        return Answer("failed", exc.code)
    return Answer(str(verdict))


async def record(conn: Conn, *, user_id: int, flow: str, answer: Answer) -> None:
    """The answer on the account and on the trail - the flow and the result,
    never the address."""
    if answer.result == "off":
        return
    if answer.result == "failed":
        await repo.record_employment(conn, user_id, None)
        await audit.record(
            conn,
            event=Event.EMPLOYEE_CHECK_FAILED,
            entity_type="auth_user",
            entity_id=user_id,
            subject_user_id=user_id,
            actor_user_id=None,
            detail={"flow": flow, "failure": answer.code},
        )
        return
    await repo.record_employment(conn, user_id, answer.result)
    await audit.record(
        conn,
        event=Event.EMPLOYEE_CHECKED,
        entity_type="auth_user",
        entity_id=user_id,
        subject_user_id=user_id,
        actor_user_id=None,
        detail={"flow": flow, "result": answer.result},
    )


async def test_address(conn: Conn, email: str, *, actor_id: int) -> Row:
    """The administrator's "Check an address": the answer, said in words, and
    nothing recorded against any account."""
    if domain_of(email) is None:
        raise ValidationFailed("Enter an email address.", field="email")
    found = await settings_for_sign_in(conn)
    if found.link is None:
        raise ValidationFailed("Set VerifyEmail's address and switch it on first.")
    answer = await ask(found.link, email.strip())
    await audit.record(
        conn,
        event=Event.EMPLOYEE_CHECKED if answer.result != "failed" else Event.EMPLOYEE_CHECK_FAILED,
        entity_type="employee_check_connection",
        entity_id=1,
        actor_user_id=actor_id,
        detail={"flow": TEST, "result": answer.result, "failure": answer.code},
    )
    return {
        "result": answer.result,
        "message": (
            "An active employee."
            if answer.result == "active"
            else "Not an active employee: left, or not known to the organisation."
            if answer.result == "inactive"
            else failure_said(answer.code or "")
        ),
        "on_company_domain": on_domains(email, found.domains),
    }


# ------------------------------------------------------------ console sign-in
#: Why a console sign-in was refused, as the trail records it, and what the
#: person is told. The password was right, so saying why tells nothing a
#: stranger could use.
REFUSALS: dict[str, str] = {
    "not_active_employee": (
        "Your account cannot sign in: the organisation does not list you as an active "
        "employee. Speak to your administrator if this is wrong."
    ),
    "employee_check_failed": (
        "We could not confirm your employment just now, so you cannot sign in yet. "
        "Try again in a few minutes."
    ),
    "not_organisation_domain": (
        "Your account cannot sign in: its email is not on one of the organisation's domains. "
        "Speak to your administrator."
    ),
}


async def console_refusal(conn: Conn, user: Row) -> str | None:
    """Why this member of staff may not sign in to the console, or None.

    The administrator is never asked about: an outage of VerifyEmail, or a
    domain list set wrong, must not lock out the one role that can put it
    right. Everyone else on a company domain is asked, while VerifyEmail is
    on; no answer refuses (the console fails closed). Anyone on another domain
    signs in while the administrator allows it, and not otherwise."""
    from cmp.core.permissions import Role
    from cmp.infrastructure.dkms import unseal_value

    if user["role"] == Role.ADMIN.value:
        return None
    found = await settings_for_sign_in(conn)
    email = await unseal_value("auth_user", "email", user.get("email"))
    if not on_domains(email, found.domains):
        return None if found.allow_other_domains else "not_organisation_domain"
    if found.link is None:
        return None
    answer = await ask(found.link, str(email))
    await record(conn, user_id=int(user["id"]), flow=CONSOLE, answer=answer)
    if answer.active:
        return None
    return "not_active_employee" if answer.result == "inactive" else "employee_check_failed"


# ------------------------------------------------------------- portal sign-in
async def portal_subject(conn: Conn, user_uuid: str) -> tuple[int, str, Link] | None:
    """What the worker asks about for a person just signed in to the portal:
    the account, its first address on a company domain, and the connection -
    or None when there is nothing to ask (switched off, or no company address).
    """
    from cmp.db.repositories import users as user_repo
    from cmp.infrastructure.dkms import unseal_value

    found = await settings_for_sign_in(conn)
    if found.link is None or not found.domains:
        return None
    user = await user_repo.by_uuid(conn, user_uuid)
    if user is None:
        return None
    for column in ("email", "secondary_email"):
        email = await unseal_value("auth_user", column, user.get(column))
        if isinstance(email, str) and on_domains(email, found.domains):
            return int(user["id"]), email, found.link
    return None


async def refuses_employee_link(conn: Conn, user_id: int) -> bool:
    """An employee-only link refuses a person VerifyEmail last said is not an
    active employee. Never asked, or no answer: allowed (the portal fails open)."""
    row = await repo.employment(conn, user_id)
    return bool(row and row["employment_status"] == "inactive")
