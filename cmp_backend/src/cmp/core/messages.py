"""Every message the platform sends, in one place, with its default words.

A *junction* is a moment at which the platform writes to a person: a sign-in
code, a consent receipt, a ticket to a holder. Each has a key, the channels it
can travel on, the variables its text may use, and a default subject and body
per channel. The administrator and the DPO may replace the words for any
junction from the console; the defaults here are what is sent until they do.

Two rules keep the set honest, and both are tested:

* **A message cannot be sent except through a junction.** The delivery helper
  takes a `Message` key, never free text, so a new kind of message has to be
  declared here - and the moment it is declared it appears in the console,
  with its variables and its defaults, without anybody remembering to add it.
* **A template may only use the variables its junction declares.** Saving a
  template that names anything else is refused with the allowed names listed,
  and a stored template that goes stale renders its unknown placeholders as
  written rather than failing the message.

Plain text, not HTML. A one-time code that arrives as a rendering failure is a
sign-in nobody can complete, and none of these messages carries branding worth
that risk. SMS bodies are separate and short: a code, what it is for, how long
it lasts.

This module is data and pure functions. Storage, caching and transports live
in `cmp.infrastructure.messaging`; the console's editing surface in
`cmp.domain.messaging`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from string import Formatter
from typing import Any, Final


class Channel(StrEnum):
    EMAIL = "email"
    SMS = "sms"


class Message(StrEnum):
    """The junctions. Adding one here is the whole of registering it."""

    # sign-in and account
    MFA_CODE = "mfa_code"
    LOGIN_CODE = "login_code"
    REGISTRATION_CODE = "registration_code"
    CONSENT_CODE = "consent_code"
    PASSWORD_RESET = "password_reset"  # noqa: S105 - a message key, not a secret
    # consent
    CONSENT_RECEIPT = "consent_receipt"
    WITHDRAWAL_CONFIRMATION = "withdrawal_confirmation"
    # rights
    RIGHTS_ACKNOWLEDGEMENT = "rights_acknowledgement"
    RIGHTS_VERIFICATION_CODE = "rights_verification_code"
    RIGHTS_RESPONSE_READY = "rights_response_ready"
    RIGHTS_RESPONSE = "rights_response"
    RIGHTS_CLOSED = "rights_closed"
    NOMINATION_CODE = "nomination_code"
    NOMINATION_INVITATION = "nomination_invitation"
    NOMINATION_ACCEPTED = "nomination_accepted"
    HOLDER_INSTRUCTION = "holder_instruction"
    TICKET_REMINDER = "ticket_reminder"
    TICKET_MESSAGE = "ticket_message"
    # staff
    OFFICE_NOTE = "office_note"


@dataclass(frozen=True, slots=True)
class Variable:
    name: str
    description: str
    #: Used by the console's preview, so an editor sees a real-looking message.
    sample: str


@dataclass(frozen=True, slots=True)
class Junction:
    key: Message
    title: str
    description: str
    group: str
    channels: tuple[Channel, ...]
    variables: tuple[Variable, ...]
    email_subject: str | None
    email_body: str | None
    sms_body: str | None

    def default(self, channel: Channel | str) -> tuple[str | None, str]:
        if Channel(channel) is Channel.EMAIL:
            assert self.email_subject is not None and self.email_body is not None
            return self.email_subject, self.email_body
        assert self.sms_body is not None
        return None, self.sms_body

    @property
    def variable_names(self) -> frozenset[str]:
        return frozenset(v.name for v in self.variables)

    @property
    def samples(self) -> dict[str, str]:
        return {v.name: v.sample for v in self.variables}


# ------------------------------------------------------------- shared pieces
ORGANISATION = Variable("organisation", "The organisation's name (ORGANISATION_NAME).", "COMPASS")
PORTAL_URL = Variable(
    "portal_url", "The data principal's portal (PUBLIC_BASE_URL).", "https://portal.example.org"
)
CODE = Variable("code", "The six-digit one-time code.", "482913")
MINUTES = Variable("minutes", "How many minutes the code is valid for.", "10")
REFERENCE = Variable("reference", "The rights request reference.", "RR-2026-000042")

_SIGN_OFF_EMAIL = (
    "\n\nIf you were not expecting this message, please tell the Privacy Office at {organisation}."
)
_BOARD_ROUTE = (
    "\n\nIf you are not satisfied with how this was handled you may raise a grievance with "
    "us, and you may also complain to the Data Protection Board of India. The route to "
    "the Board is independent of ours."
)

BOTH: Final = (Channel.EMAIL, Channel.SMS)
EMAIL_ONLY: Final = (Channel.EMAIL,)

CATALOGUE: Final[tuple[Junction, ...]] = (
    # ------------------------------------------------------ sign-in and account
    Junction(
        key=Message.MFA_CODE,
        title="Staff sign-in code",
        description="The second factor sent to a member of staff's email after a correct password.",
        group="Sign-in",
        channels=EMAIL_ONLY,
        variables=(CODE, MINUTES, ORGANISATION),
        email_subject="{code} is your {organisation} sign-in code",
        email_body=(
            "Your sign-in code is:\n\n    {code}\n\n"
            "Enter it on the sign-in page to finish. It works once and expires in {minutes} "
            "minutes.\n\n"
            "We will never ask for this code by phone or message. If you did not just enter "
            "your password on the {organisation} console, somebody else has it: change it, "
            "and tell the Privacy Office."
        ),
        sms_body=None,
    ),
    Junction(
        key=Message.LOGIN_CODE,
        title="Data principal sign-in code",
        description=(
            "The code a data principal signs in with, sent to the mobile or email she chose."
        ),
        group="Sign-in",
        channels=BOTH,
        variables=(CODE, MINUTES, ORGANISATION),
        email_subject="{code} is your sign-in code",
        email_body=(
            "Your sign-in code is:\n\n    {code}\n\n"
            "Enter it to open your account. It works once and expires in {minutes} minutes.\n\n"
            "There is no password on your account: this code is how you sign in each time."
            + _SIGN_OFF_EMAIL
        ),
        sms_body=(
            "{organisation}: your sign-in code is {code}. It expires in {minutes} minutes. "
            "Not you? Ignore this message."
        ),
    ),
    Junction(
        key=Message.REGISTRATION_CODE,
        title="Sign-up verification code",
        description=(
            "One per contact given at sign-up. Every contact must answer before the account opens."
        ),
        group="Sign-in",
        channels=BOTH,
        variables=(CODE, MINUTES, ORGANISATION),
        email_subject="{code} confirms this email address",
        email_body=(
            "Welcome. To finish creating your account, enter this code where you signed up:"
            "\n\n    {code}\n\n"
            "It confirms that this email address is yours and that we can reach you here. "
            "It works once and expires in {minutes} minutes.\n\n"
            "If you gave a mobile number as well, a separate code has gone there; both are "
            "needed." + _SIGN_OFF_EMAIL
        ),
        sms_body=(
            "{organisation}: {code} confirms this mobile number. Enter it to finish signing "
            "up. Expires in {minutes} minutes."
        ),
    ),
    Junction(
        key=Message.CONSENT_CODE,
        title="Consent link contact code",
        description="Confirms a contact given through a consent link, before the notice is shown.",
        group="Sign-in",
        channels=BOTH,
        variables=(
            CODE,
            MINUTES,
            Variable("project_name", "The project the notice belongs to.", "Gait Study 2026"),
            ORGANISATION,
        ),
        email_subject="{code} confirms your contact details",
        email_body=(
            "Your confirmation code is:\n\n    {code}\n\n"
            "It expires in {minutes} minutes.\n\n"
            "You are about to read a notice for {project_name}. You have not agreed to "
            "anything yet: this code only confirms that we can reach you, so that the record "
            "of whatever you decide is yours." + _SIGN_OFF_EMAIL
        ),
        sms_body=(
            "{organisation}: {code} confirms your contact for {project_name}. You have not "
            "agreed to anything yet. Expires in {minutes} minutes."
        ),
    ),
    Junction(
        key=Message.PASSWORD_RESET,
        title="Password reset code",
        description="Sent to a member of staff who asked to reset their password.",
        group="Sign-in",
        channels=EMAIL_ONLY,
        variables=(CODE, MINUTES, ORGANISATION),
        email_subject="Reset your {organisation} password",
        email_body=(
            "Somebody asked to reset the password on this account. If it was you, enter this "
            "code on the reset page:\n\n    {code}\n\n"
            "It works once and expires in {minutes} minutes. Your current password keeps "
            "working until a new one is set.\n\n"
            "If it was not you, nothing has changed and nothing will; you can ignore this "
            "message, and you may want to tell the Privacy Office."
        ),
        sms_body=None,
    ),
    # ---------------------------------------------------------------- consent
    Junction(
        key=Message.CONSENT_RECEIPT,
        title="Consent receipt",
        description="Her copy of the record, sent after consent is given through a link.",
        group="Consent",
        channels=BOTH,
        variables=(
            Variable("project_name", "The project the consent is for.", "Gait Study 2026"),
            Variable(
                "reference",
                "The consent record's reference.",
                "7c3cbb28-4b74-4600-975c-a3d0cc169368",
            ),
            Variable(
                "purposes",
                "The purposes agreed to, one per line, each starting with a dash.",
                "  - Gait analysis for the study\n  - Contact about follow-up sessions",
            ),
            Variable("purpose_count", "How many purposes were agreed to.", "2"),
            Variable(
                "withdraw_url",
                "Where she can review or withdraw.",
                "https://portal.example.org/my-consents",
            ),
            ORGANISATION,
        ),
        email_subject="Your consent record for {project_name}",
        email_body=(
            "Thank you. We have recorded your decision for {project_name}.\n\n"
            "You agreed to:\n{purposes}\n\n"
            "Your record reference is {reference}. Keep this message: it is your copy of "
            "what you agreed to, and you can quote the reference if you ever ask us about "
            "it.\n\n"
            "You can review or withdraw at any time, and withdrawing is as easy as agreeing "
            "was:\n{withdraw_url}\n\n"
            "Withdrawing stops future processing for the purposes you withdraw. It does not "
            "by itself delete data already collected; if that is what you want, ask for "
            "erasure from the same page." + _SIGN_OFF_EMAIL
        ),
        sms_body=(
            "{organisation}: your consent for {project_name} is recorded ({purpose_count} "
            "purpose(s)). Ref {reference}. Review or withdraw any time: {withdraw_url}"
        ),
    ),
    Junction(
        key=Message.WITHDRAWAL_CONFIRMATION,
        title="Withdrawal confirmation",
        description=(
            "Sent when she withdraws some or all purposes. Says what stops and what continues."
        ),
        group="Consent",
        channels=BOTH,
        variables=(
            Variable(
                "reference", "The new record's reference.", "9d1f0a6e-2c44-4d0e-8f7a-3b5e6c7d8e9f"
            ),
            Variable(
                "stopped",
                "The purposes withdrawn, comma-separated.",
                "Contact about follow-up sessions",
            ),
            Variable(
                "continuing",
                "The purposes still in force, comma-separated, or empty.",
                "Gait analysis for the study",
            ),
            Variable(
                "continuing_note",
                "A sentence about what continues, or empty when nothing does.",
                "Still in force: Gait analysis for the study.",
            ),
            Variable(
                "rights_url", "Where to ask for erasure.", "https://portal.example.org/rights"
            ),
            ORGANISATION,
        ),
        email_subject="Your withdrawal has been recorded",
        email_body=(
            "We have recorded your withdrawal. Reference: {reference}.\n\n"
            "Stopped: {stopped}.\n{continuing_note}\n\n"
            "Processing for the purposes you withdrew ceases within a reasonable period. "
            "The earlier record is kept as evidence of what was agreed at the time; it "
            "permits nothing further.\n\n"
            "Data already collected is not deleted by a withdrawal. To ask for erasure, "
            "make a rights request:\n{rights_url}" + _SIGN_OFF_EMAIL
        ),
        sms_body=(
            "{organisation}: your withdrawal is recorded. Stopped: {stopped}. Ref "
            "{reference}. To ask for erasure of data already collected: {rights_url}"
        ),
    ),
    # ----------------------------------------------------------------- rights
    Junction(
        key=Message.RIGHTS_ACKNOWLEDGEMENT,
        title="Rights request acknowledged",
        description=(
            "Sent on receipt of a rights request: the reference, the date she will hear by, "
            "and what to expect."
        ),
        group="Rights",
        channels=BOTH,
        variables=(
            REFERENCE,
            Variable("request_kind", "What was asked for, in words.", "access request"),
            Variable("due_on", "The date the response is due by.", "9 December 2026"),
            Variable("period_days", "The published response period, in days.", "90"),
            PORTAL_URL,
            ORGANISATION,
        ),
        email_subject="We have received your {request_kind} ({reference})",
        email_body=(
            "We have received your {request_kind}. Your reference is {reference}; please "
            "quote it if you contact us about it.\n\n"
            "We respond within {period_days} days of receipt, so you will hear from us by "
            "{due_on}. If we need to confirm anything we will use the contact details we "
            "already hold for you.\n\n"
            "When the response is ready you will be told, and it will be available to you "
            "signed in to your account at {portal_url}. We do not send personal data as an "
            "attachment." + _SIGN_OFF_EMAIL
        ),
        sms_body=(
            "{organisation}: we have received your {request_kind}, ref {reference}. You will "
            "hear from us by {due_on}. Track it at {portal_url}"
        ),
    ),
    Junction(
        key=Message.RIGHTS_VERIFICATION_CODE,
        title="Rights request verification code",
        description=(
            "Confirms that a request made through the public form came from the person on file."
        ),
        group="Rights",
        channels=BOTH,
        variables=(CODE, MINUTES, REFERENCE, ORGANISATION),
        email_subject="{code} confirms request {reference} is yours",
        email_body=(
            "Your verification code is:\n\n    {code}\n\n"
            "It confirms that request {reference} came from you. It expires in {minutes} "
            "minutes. Nothing has yet been decided about the request itself.\n\n"
            "If you did not make a request, ignore this message: without the code, the "
            "request goes no further." + _SIGN_OFF_EMAIL
        ),
        sms_body=(
            "{organisation}: {code} confirms request {reference} is yours. Expires in "
            "{minutes} minutes. Not you? Ignore this message."
        ),
    ),
    Junction(
        key=Message.RIGHTS_RESPONSE_READY,
        title="Response ready",
        description="Tells her the Privacy Office's response can be read from her account.",
        group="Rights",
        channels=BOTH,
        variables=(
            REFERENCE,
            Variable(
                "availability",
                "Until when the response can be downloaded, as a sentence, or empty.",
                "It is available until 9 January 2027.",
            ),
            PORTAL_URL,
            ORGANISATION,
        ),
        email_subject="Our response to your request {reference} is ready",
        email_body=(
            "Our response to your request {reference} is ready. Sign in to read it and, "
            "where there is a file, download it from your account:\n{portal_url}\n\n"
            "{availability}" + _BOARD_ROUTE + _SIGN_OFF_EMAIL
        ),
        sms_body=(
            "{organisation}: our response to request {reference} is ready. Sign in to read "
            "it: {portal_url}. {availability}"
        ),
    ),
    Junction(
        key=Message.RIGHTS_RESPONSE,
        title="Response",
        description=(
            "The response itself: the decision, the Privacy Office's words, and her record. "
        ),
        group="Rights",
        channels=BOTH,
        variables=(
            REFERENCE,
            Variable(
                "headline",
                "The outcome, as a sentence.",
                "Our response to your request is complete.",
            ),
            Variable(
                "response_text",
                "What the Privacy Office wrote.",
                "We hold the records listed below and no others.",
            ),
            Variable(
                "digest",
                "Her record as held by the platform: consents, disclosures, returns.",
                "CONSENTS\n  - Gait Study 2026: agreed on 1 September 2026",
            ),
            Variable(
                "availability",
                "Where and until when the full file can be downloaded, as a sentence.",
                "The full record, as a file, is available from your account until 9 January 2027: https://portal.example.org/my-requests",
            ),
            ORGANISATION,
        ),
        email_subject="Our response to your request {reference}",
        email_body=(
            "Regarding your request {reference}: {headline}\n\n"
            "FROM THE PRIVACY OFFICE\n{response_text}\n\n"
            "{digest}\n\n{availability}" + _BOARD_ROUTE + _SIGN_OFF_EMAIL
        ),
        sms_body=(
            "{organisation}: regarding request {reference}: {headline} Sign in to read the "
            "full response. {availability}"
        ),
    ),
    Junction(
        key=Message.RIGHTS_CLOSED,
        title="Request closed",
        description=(
            "A refusal, a reclassification, an unverified request or a grievance decision, "
            "with the reason."
        ),
        group="Rights",
        channels=BOTH,
        variables=(
            REFERENCE,
            Variable(
                "headline",
                "What happened, as a clause.",
                "we are not able to act on it as a rights request",
            ),
            Variable(
                "explanation",
                "The reason, in the Privacy Office's words.",
                "The request asked for records of a different organisation.",
            ),
            ORGANISATION,
        ),
        email_subject="About your request {reference}",
        email_body=(
            "Regarding your request {reference}: {headline}.\n\n{explanation}"
            + _BOARD_ROUTE
            + _SIGN_OFF_EMAIL
        ),
        sms_body=(
            "{organisation}: regarding request {reference}: {headline}. {explanation} You "
            "may raise a grievance with us or complain to the Data Protection Board."
        ),
    ),
    Junction(
        key=Message.NOMINATION_CODE,
        title="Nomination code",
        description="Proves a nominee's recorded contact before an acceptance or a refusal counts.",
        group="Rights",
        channels=BOTH,
        variables=(CODE, MINUTES, ORGANISATION),
        email_subject="{code} is your nomination code",
        email_body=(
            "Your verification code is:\n\n    {code}\n\n"
            "Enter it to accept or decline the nomination. It expires in {minutes} minutes. "
            "Entering it is not itself an acceptance: you choose on the page." + _SIGN_OFF_EMAIL
        ),
        sms_body=(
            "{organisation}: {code} is your nomination code. Enter it to accept or decline. "
            "Expires in {minutes} minutes."
        ),
    ),
    Junction(
        key=Message.NOMINATION_INVITATION,
        title="Nomination invitation",
        description=(
            "Tells a person that somebody has nominated them, and how to accept or decline. "
        ),
        group="Rights",
        channels=BOTH,
        variables=(
            Variable("principal_name", "Who made the nomination.", "Anjali Verma"),
            Variable(
                "accept_url",
                "The single-use link to accept or decline.",
                "https://portal.example.org/rights/nominations/abc123",
            ),
            Variable("expires_on", "When the link lapses.", "10 October 2026"),
            ORGANISATION,
        ),
        email_subject="{principal_name} has nominated you",
        email_body=(
            "{principal_name} has nominated you to exercise their data protection rights on "
            "their behalf under section 14 of the Digital Personal Data Protection Act 2023, "
            "should they die or become unable to act.\n\n"
            "Nothing is in effect until you accept, and you may decline. Open this link to "
            "choose:\n{accept_url}\n\n"
            "You will be asked for a code sent to one of the contacts {principal_name} "
            "recorded for you, so that nobody else can answer for you. The link can be used "
            "once and expires on {expires_on}.\n\n"
            "If you do not know {principal_name}, or do not want this, simply decline."
            + _SIGN_OFF_EMAIL
        ),
        sms_body=(
            "{organisation}: {principal_name} has nominated you to act for them under the "
            "DPDP Act. Accept or decline by {expires_on}: {accept_url}"
        ),
    ),
    Junction(
        key=Message.NOMINATION_ACCEPTED,
        title="Nomination accepted",
        description=(
            "Kept for the day it is needed: the reference, the account, and the place to act."
        ),
        group="Rights",
        channels=BOTH,
        variables=(
            Variable("principal_name", "Who made the nomination.", "Anjali Verma"),
            Variable(
                "reference", "The nomination reference.", "f832ee3a-1c3f-4c33-a9c8-0429c4f3edf3"
            ),
            Variable(
                "nominee_url",
                "The page to act from without signing in.",
                "https://portal.example.org/rights/nominee?nomination=f832ee3a",
            ),
            Variable(
                "sign_in_url", "The portal's sign-in page.", "https://portal.example.org/sign-in"
            ),
            ORGANISATION,
        ),
        email_subject="You are {principal_name}'s nominee - keep this message",
        email_body=(
            "You have accepted {principal_name}'s nomination under section 14 of the Digital "
            "Personal Data Protection Act 2023. Nothing happens until the event they named, "
            "death or incapacity, and you will be asked to evidence it when it does.\n\n"
            "When that day comes you can sign in at {sign_in_url} with the mobile or email "
            "you accepted from; a code is sent to it each time and there is no password. "
            "Your nominations are shown under My requests, with the way to act.\n\n"
            "Your nomination reference: {reference}\n\n"
            "You can also act without signing in, here:\n{nominee_url}\n\n"
            "Enter the reference above and the mobile or email that was recorded for you; a "
            "code is sent to that contact, and the request is made once you have entered it."
            + _SIGN_OFF_EMAIL
        ),
        sms_body=(
            "{organisation}: you are now {principal_name}'s nominee. Keep this: ref "
            "{reference}. To act when needed, sign in at {sign_in_url}"
        ),
    ),
    Junction(
        key=Message.HOLDER_INSTRUCTION,
        title="Ticket to a holder",
        description=(
            "The instruction to a party holding her data, with the brief and the date it is due by."
        ),
        group="Rights",
        channels=BOTH,
        variables=(
            REFERENCE,
            Variable("holder_label", "The holder the ticket is addressed to.", "Pune Motion Lab"),
            Variable(
                "instruction",
                "What the holder is asked to do.",
                "Confirm what you hold about this person and return it.",
            ),
            Variable("due_on", "The date the return is due by.", "24 September 2026"),
            Variable(
                "brief",
                "What the platform already holds from this holder, or empty.",
                "Records naming your site: 1 export on 3 September 2026.",
            ),
            ORGANISATION,
        ),
        email_subject="Action required by {due_on}: rights request {reference}",
        email_body=(
            "To {holder_label}:\n\n{brief}\n\n{instruction}\n\n"
            "Please return your confirmation by {due_on}. The Privacy Office answers the "
            "person concerned on a fixed statutory clock, and a return after this date may "
            "mean our response has to name your part as outstanding.\n\n"
            "Rights request {reference}, {organisation} Privacy Office."
        ),
        sms_body=(
            "{organisation} Privacy Office: rights request {reference} needs your return by "
            "{due_on}. {instruction}"
        ),
    ),
    Junction(
        key=Message.TICKET_REMINDER,
        title="Ticket reminder",
        description=(
            "A ticket's date is near, today, or past. Sent on a cadence by the platform and "
            "on demand by the office."
        ),
        group="Rights",
        channels=BOTH,
        variables=(
            REFERENCE,
            Variable("holder_label", "The holder the ticket is addressed to.", "Pune Motion Lab"),
            Variable("timing", "How near the date is, for the subject.", "Due in 3 days"),
            Variable("when", "The date, as a clause.", "is due in 3 days, on 24 September 2026"),
            Variable(
                "return_route",
                "How to return it, as a sentence.",
                "Return it on the portal: https://console.example.org/tickets",
            ),
            ORGANISATION,
        ),
        email_subject="{timing}: rights request {reference}",
        email_body=(
            "To {holder_label}:\n\n"
            "Your ticket on rights request {reference} {when}. The Privacy Office answers "
            "the person concerned on a fixed statutory clock, and a return after the date "
            "may mean the response has to name your part as outstanding.\n\n{return_route}"
        ),
        sms_body=(
            "{organisation} Privacy Office: your ticket on rights request {reference} "
            "{when}. {return_route}"
        ),
    ),
    Junction(
        key=Message.TICKET_MESSAGE,
        title="Ticket message",
        description="A message written on a ticket's thread, copied to the other side.",
        group="Rights",
        channels=BOTH,
        variables=(
            REFERENCE,
            Variable("holder_label", "The holder the ticket is addressed to.", "Pune Motion Lab"),
            Variable("author", "Who wrote the message.", "Priya Nair, Privacy Office"),
            Variable(
                "message",
                "The message itself.",
                "Could you confirm whether the recording from 3 September includes audio?",
            ),
            Variable(
                "return_route",
                "How to reply, as a sentence.",
                "Reply on the portal: https://console.example.org/tickets",
            ),
            ORGANISATION,
        ),
        email_subject="Rights request {reference}, {holder_label}: message from {author}",
        email_body=(
            "{author} wrote on the ticket for {holder_label} (rights request {reference}):"
            "\n\n{message}\n\n{return_route}"
        ),
        sms_body=(
            "{organisation}: {author} wrote on rights request {reference}: {message} {return_route}"
        ),
    ),
    # ------------------------------------------------------------------ staff
    Junction(
        key=Message.OFFICE_NOTE,
        title="Note from the Privacy Office",
        description="A notification resent to a person by the office from the console.",
        group="Staff",
        channels=EMAIL_ONLY,
        variables=(
            Variable("event", "What the notification was about.", "project.approved"),
            Variable("occurred_on", "When it happened.", "8 September 2026"),
            Variable(
                "console_url",
                "The staff console (CONSOLE_BASE_URL).",
                "https://console.example.org",
            ),
            ORGANISATION,
        ),
        email_subject="A message from the {organisation} Privacy Office",
        email_body=(
            "This is a copy of a notification from the {organisation} Privacy Office, "
            "regarding {event} on {occurred_on}.\n\n"
            "Sign in to the console to see it in context:\n{console_url}"
        ),
        sms_body=None,
    ),
)

JUNCTIONS: Final[dict[str, Junction]] = {j.key.value: j for j in CATALOGUE}

#: Bounds a template must fit within. Three SMS segments is the most anyone
#: should be asked to read on a lock screen; the email limits are generous.
MAX_SUBJECT_CHARS: Final = 200
MAX_EMAIL_BODY_CHARS: Final = 6000
MAX_SMS_BODY_CHARS: Final = 480


def junction(key: Message | str) -> Junction:
    return JUNCTIONS[Message(key).value]


# ---------------------------------------------------------------- rendering
class _Safe(dict[str, Any]):
    """A placeholder the template names but the caller did not supply is
    rendered as written, never as a crash: a stale template must not stop a
    sign-in code."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def render_text(template: str, variables: Mapping[str, Any]) -> str:
    values = _Safe({k: ("" if v is None else v) for k, v in variables.items()})
    try:
        return template.format_map(values)
    except (ValueError, KeyError, IndexError):
        # A template that cannot be parsed at all - which validation on save
        # prevents - is still better sent as it is than not sent.
        return template


def placeholders(template: str) -> set[str]:
    """The variable names a template uses. Raises ValueError for a malformed one.

    Only plain `{name}` placeholders are allowed. A format spec or a conversion
    (`{code:>10}`, `{name!r}`) would let a template reach into a value's
    formatting, and nothing here needs that.
    """
    names: set[str] = set()
    for _literal, field_name, spec, conversion in Formatter().parse(template):
        if field_name is None:
            continue
        if field_name == "" or spec or conversion or not field_name.isidentifier():
            shown = (
                field_name + ("!" + conversion if conversion else "") + (":" + spec if spec else "")
            )
            raise ValueError(f"only plain {{name}} placeholders are allowed, not {{{shown}}}")
        names.add(field_name)
    return names


def check_template(
    key: Message | str, channel: Channel | str, subject: str | None, body: str
) -> list[str]:
    """Why a template cannot be saved, as sentences; empty when it can."""
    j = junction(key)
    ch = Channel(channel)
    problems: list[str] = []
    if ch not in j.channels:
        problems.append(f"'{j.title}' is not sent by {ch.value}")
        return problems
    allowed = ", ".join("{" + v.name + "}" for v in j.variables)

    if ch is Channel.EMAIL:
        if not subject or not subject.strip():
            problems.append("an email needs a subject")
        elif len(subject) > MAX_SUBJECT_CHARS:
            problems.append(f"the subject must fit in {MAX_SUBJECT_CHARS} characters")
        elif "\n" in subject:
            problems.append("a subject is one line")
        if len(body) > MAX_EMAIL_BODY_CHARS:
            problems.append(f"the body must fit in {MAX_EMAIL_BODY_CHARS} characters")
    else:
        if subject:
            problems.append("an SMS has no subject")
        if len(body) > MAX_SMS_BODY_CHARS:
            problems.append(f"an SMS must fit in {MAX_SMS_BODY_CHARS} characters (three segments)")
    if not body.strip():
        problems.append("the body cannot be empty")

    for label, text in (("subject", subject or ""), ("body", body)):
        try:
            used = placeholders(text)
        except ValueError as exc:
            problems.append(f"the {label} is malformed: {exc}")
            continue
        unknown = sorted(used - j.variable_names)
        if unknown:
            problems.append(
                f"the {label} uses {', '.join('{' + u + '}' for u in unknown)}, which this "
                f"message does not provide; it can use {allowed}"
            )
    return problems
