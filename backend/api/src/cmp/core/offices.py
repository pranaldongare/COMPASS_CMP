"""The codes of the two offices migration 0051 inserts (ADR 0032).

An office is a row, not an enum: a third is an INSERT and assigned accounts.
These name the two that exist, for the code paths that belong to one track -
the R&D track writes its records in `rnd`, the HR track in `hr` - and for
`app.office`, which holds a code. What a session may read is never decided
here; that is the office on the session and the policies.
"""

from __future__ import annotations

from typing import Final

#: The DPO office: the R&D track's projects, purposes, notices, requests and
#: breaches.
RND: Final = "rnd"
#: The Legal office: the HR track's.
HR: Final = "hr"
#: Both, for a choice a caller makes between them.
CODES: Final = (RND, HR)

#: The office id for a code, inside a statement that writes one.
OFFICE_ID: Final = "(SELECT office_id FROM office WHERE office_code = %s)"
#: The same, for a statement with named parameters.
OFFICE_ID_NAMED: Final = "(SELECT office_id FROM office WHERE office_code = %(office)s)"
