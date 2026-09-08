"""The words the system sends.

Kept out of the task bodies for one reason that is not tidiness: these are the
only messages a data subject receives from us, and they should be reviewable as
a set. Somebody changing the tone of a withdrawal confirmation should be able to
see it next to the consent receipt, not hunt for it inside a Celery task.

Plain text, not HTML. A one-time code that arrives as a rendering failure is a
sign-in nobody can complete, and these messages carry no branding worth the
risk.

Every template is a function returning `(subject, body)` rather than a format
string, so the caller cannot forget a placeholder and ship `{code}` to a user.
"""

from __future__ import annotations

from cmp.core.config import settings

_SIGN_OFF = "\n\nIf you were not expecting this, tell the Privacy Office."


def mfa_code(code: str) -> tuple[str, str]:
    minutes = settings.mfa_ttl_s // 60
    return (
        "Your verification code",
        f"Your verification code is {code}.\nIt expires in {minutes} minutes." + _SIGN_OFF,
    )


def login_code(code: str) -> tuple[str, str]:
    minutes = settings.otp_ttl_s // 60
    return (
        "Your sign-in code",
        f"Your sign-in code is {code}.\nIt expires in {minutes} minutes." + _SIGN_OFF,
    )


def consent_code(code: str, project_name: str) -> tuple[str, str]:
    minutes = settings.otp_ttl_s // 60
    return (
        "Confirm your contact details",
        f"Your confirmation code is {code}.\n"
        f"It expires in {minutes} minutes.\n\n"
        f"You are being asked to read a notice for: {project_name}.\n"
        "You have not agreed to anything yet — the code only confirms we can "
        "reach you." + _SIGN_OFF,
    )


def password_reset(token_url: str) -> tuple[str, str]:
    return (
        "Reset your password",
        f"Open this link to set a new password:\n\n{token_url}\n\n"
        "It can be used once, and it expires shortly." + _SIGN_OFF,
    )


def consent_receipt(project_name: str, purposes: list[str], withdraw_url: str) -> tuple[str, str]:
    """Sent after consent is captured.

    Lists the purposes individually rather than a count. "You agreed to 3
    purposes" is not a record of what somebody agreed to, and this message is
    often the only copy they keep.
    """
    lines = "\n".join(f"  - {name}" for name in purposes) or "  (none)"
    return (
        f"Your consent record — {project_name}",
        f"Thank you. We have recorded your consent for {project_name}.\n\n"
        f"You agreed to:\n{lines}\n\n"
        f"You can withdraw at any time, and it is as easy as giving consent was:\n"
        f"{withdraw_url}\n\n"
        "Withdrawing stops future processing for the purposes you withdraw. It "
        "does not by itself delete data already collected — ask for erasure if "
        "that is what you want.",
    )


# ---------------------------------------------------------------- rights
_RIGHT_NAMES = {
    "access": "access request",
    "correction": "correction request",
    "erasure": "erasure request",
    "grievance": "grievance",
}

_BOARD_ROUTE = (
    "\n\nIf you are not satisfied with how this was handled, you may raise a grievance "
    "with us, and you may complain to the Data Protection Board of India. The route to "
    "the Board is independent of ours."
)


def rights_acknowledgement(
    reference: str, request_type: str, due_on: str, period_days: int
) -> tuple[str, str]:
    """Reference, expected date, and what she will receive."""
    what = _RIGHT_NAMES.get(request_type, "request")
    return (
        f"Your {what} - reference {reference}",
        f"We have received your {what}. Your reference is {reference}; please quote "
        f"it if you contact us.\n\n"
        f"We respond within {period_days} days of receipt, so you will hear from us by "
        f"{due_on}. If we need to confirm anything, we will use the contact details we "
        "already hold for you.\n\n"
        "When the response is ready you will be told, and it will be available to you "
        "signed in, from your own account - we do not send personal data as an "
        "attachment." + _SIGN_OFF,
    )


def rights_verification_code(code: str, reference: str) -> tuple[str, str]:
    minutes = settings.otp_ttl_s // 60
    return (
        "Confirm it is you",
        f"Your verification code is {code}. It expires in {minutes} minutes.\n\n"
        f"It confirms that the request {reference} came from you. Nothing has been "
        "decided about the request itself." + _SIGN_OFF,
    )


def rights_response_ready(reference: str, expires_on: str | None) -> tuple[str, str]:
    window = f" It is available until {expires_on}." if expires_on else ""
    return (
        f"Your response is ready - {reference}",
        f"Our response to your request {reference} is ready. Sign in to read it and, "
        f"where there is a file, download it from your account.{window}" + _BOARD_ROUTE + _SIGN_OFF,
    )


def rights_closed(reference: str, outcome: str, explanation: str) -> tuple[str, str]:
    """A refusal, a reclassification or a decision: reasoned, in writing, with the route onward."""
    headline = {
        "refused": "we are not able to act on it as a rights request",
        "reclassified_withdrawal": "it has been handled as a withdrawal of consent",
        "not_verified": "we could not verify the identity behind it",
        "upheld": "your grievance has been upheld",
        "not_upheld": "your grievance has not been upheld",
    }.get(outcome, "it has been closed")
    return (
        f"About your request {reference}",
        f"Regarding your request {reference}: {headline}.\n\n{explanation}"
        + _BOARD_ROUTE
        + _SIGN_OFF,
    )


def nomination_code(code: str) -> tuple[str, str]:
    """Proof of a recorded contact, before the link's accept or decline counts."""
    minutes = settings.otp_ttl_s // 60
    return (
        "Your verification code",
        f"Your verification code is {code}.\nEnter it to accept or decline the nomination. "
        f"It expires in {minutes} minutes." + _SIGN_OFF,
    )


def nomination_invitation(principal_name: str, accept_url: str, expires_on: str) -> tuple[str, str]:
    """A nomination he does not know about cannot safely be acted on."""
    return (
        f"{principal_name} has nominated you",
        f"{principal_name} has nominated you to exercise their data protection rights on "
        "their behalf, under section 14 of the Digital Personal Data Protection Act 2023, "
        "should they die or become unable to act.\n\n"
        "Nothing is in effect until you accept. Open this link to accept or decline:\n\n"
        f"{accept_url}\n\n"
        f"The link can be used once and expires on {expires_on}." + _SIGN_OFF,
    )


def nomination_accepted(principal_name: str, reference: str, nominee_url: str) -> tuple[str, str]:
    """Kept for the day it is needed, which may be years away.

    A nominee has no account and nothing to sign in to. What he needs when the
    time comes is the nomination's reference and the page where he acts - and
    a code will then go to the contact recorded for him, not to whatever he
    types. Without this message the reference existed nowhere he could see.
    """
    return (
        f"You are {principal_name}'s nominee - keep this message",
        f"You have accepted {principal_name}'s nomination under section 14 of the Digital "
        "Personal Data Protection Act 2023. Nothing happens until the event they named - "
        "death or incapacity - and you will need to evidence it when it does.\n\n"
        f"Your nomination reference: {reference}\n\n"
        "When the time comes, act on their behalf here:\n\n"
        f"{nominee_url}\n\n"
        "There is no account and nothing to sign in to. Enter the reference above and the "
        "email or mobile that was recorded for you; a code is sent to that contact, and the "
        "request is made once you have entered it." + _SIGN_OFF,
    )


def holder_instruction(
    reference: str, holder_label: str, instruction: str, due_on: str
) -> tuple[str, str]:
    """One ticket, to one holder of her data, with a date set early on purpose."""
    return (
        f"Action required by {due_on} - rights request {reference}",
        f"To {holder_label}:\n\n{instruction}\n\n"
        f"Please return your confirmation by {due_on}. The Privacy Office responds to the "
        "person concerned on a fixed statutory clock, and a return after this date may "
        "mean our response has to name your part as outstanding.",
    )


def withdrawal_confirmation(project_name: str, withdrawn: list[str]) -> tuple[str, str]:
    lines = "\n".join(f"  - {name}" for name in withdrawn) or "  (all purposes)"
    return (
        f"Your withdrawal — {project_name}",
        f"We have recorded your withdrawal for {project_name}.\n\n"
        f"Withdrawn:\n{lines}\n\n"
        "Processing for these purposes stops now. The earlier record is kept as "
        "evidence of what was agreed at the time — it is not deleted, and it "
        "does not permit any further processing.",
    )
