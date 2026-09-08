"""Message templates: what the person on the other end actually receives."""

from __future__ import annotations


def test_the_acceptance_message_carries_the_reference_and_the_place_to_act() -> None:
    """A nominee has no account. On the day he needs it - which may be years
    away - the reference and the page where he acts are all that get him in,
    and this message is the only thing that ever gives him the reference."""
    from cmp.domain.rights.service import nominee_url
    from cmp.infrastructure.email import templates

    ref = "f832ee3a-1c3f-4c33-a9c8-0429c4f3edf3"
    url = nominee_url(ref)
    subject, body = templates.nomination_accepted("Anjali Verma", ref, url)

    assert "Anjali Verma" in subject
    assert ref in body
    assert url in body
    assert url.endswith(f"/rights/nominee?nomination={ref}")
    assert "no account" in body.lower()
