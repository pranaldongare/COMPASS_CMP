"""A notice rendition has a floor and no ceiling.

Every other string crossing this API is bounded by what its column holds. The
notice rendition was bounded by 20,000 characters, which is not what its column
holds — `notice_language.rendered_text` is `text` — but a number somebody chose.

A notice is as long as the processing it has to describe. A fiduciary running
many purposes across several recipients, in the detail section 5 requires, can
write past forty pages without padding, and refusing that is refusing the
lawful document. So the maximum is gone and the minimum stays: an empty
rendition is still nothing, and publication still refuses a notice without one.

What bounds it now is the request body limit, which is the honest place for it —
`MAX_UPLOAD_BYTES`, enforced by the body-limit middleware. This file pins the
decision so that a later tidy-up of "unbounded string field" does not quietly
put the ceiling back.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from cmp.api.routers.v1.notices import LanguageIn, NoticeIn

#: Comfortably past the old ceiling, and past any round number near it.
#: Stripped, because the schema base strips: an unstripped fixture fails on
#: the trailing space rather than on the length, which is not the point here.
LONG = ("The fiduciary collects, uses and shares the following. " * 4_000).strip()


def test_a_rendition_far_past_the_old_ceiling_is_accepted() -> None:
    assert len(LONG) > 200_000, "the fixture has to clear the old bound by a long way"

    body = LanguageIn(rendered_text=LONG)

    assert body.rendered_text == LONG


def test_the_same_holds_where_a_notice_is_created_with_its_wording() -> None:
    notice = NoticeIn(
        withdraw_url="https://example.org/withdraw",
        exercise_rights_url="https://example.org/rights",
        board_complaint_url="https://example.org/board",
        dpo_contact="dpo@example.org",
        rendered_text=LONG,
    )

    assert notice.rendered_text == LONG


def test_an_empty_rendition_is_still_nothing() -> None:
    """The floor is the part worth keeping: a notice nobody can read is not a
    notice, and this is what stops one being saved."""
    with pytest.raises(ValidationError):
        LanguageIn(rendered_text="")
