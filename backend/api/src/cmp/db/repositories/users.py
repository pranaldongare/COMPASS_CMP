"""auth_user and person_type_history.

No business logic here. The repository knows how to fetch and store rows; whether
a person *may* have their role changed is a question for the service.

Every read that a scoped caller can reach takes the scope as a WHERE predicate,
not as a filter applied afterwards.
"""

from __future__ import annotations

from typing import Any

from cmp.core.pagination import PageRequest, build_page
from cmp.db.sql import Conn, Row, execute, fetch_all, fetch_one, keyset_clause, require_one
from cmp.infrastructure.dkms import seal
from cmp.infrastructure.dkms.blind import index_of
from cmp.validation import normalise_mobile

# The columns any caller may see. `password_hash` is not among them and must
# never be added: a SELECT * here is one refactor away from a response body.
PUBLIC_COLUMNS = """
  u.uuid, u.username, u.full_name, u.email, u.mobile, u.organization_id,
  u.role, u.person_type, u.status, u.dob, u.mobile_verified_at, u.email_verified_at,
  u.secondary_email, u.secondary_email_verified_at,
  -- Derived in SQL rather than in Python, because more than one caller asks and
  -- the answer changes on a birthday without the row being written to. NULL
  -- when the date of birth is unknown, which is not the same as adult. Read off
  -- minor_until, the one date about a birth that stays in the clear.
  cmp_is_minor(u.minor_until) AS is_minor,
  -- The blind indexes of the sealed contacts. Keyed hashes, not personal data;
  -- here so a row can be matched against a contact without opening anything.
  u.email_idx, u.mobile_idx, u.secondary_email_idx,
  u.created_at, u.updated_at
"""


def contact_indexes(contact: str) -> tuple[str | None, str | None]:
    """The index a contact would have as an email and as a mobile.

    A contact is one or the other, decided the way the platform decides it
    everywhere: an @ makes it an address. The other index is None, so a query
    comparing both columns matches only the one that applies.
    """
    if "@" in contact:
        return index_of("email", contact), None
    return None, index_of("mobile", contact)


async def by_uuid(conn: Conn, user_uuid: str) -> Row | None:
    return await fetch_one(
        conn, f"SELECT u.id, {PUBLIC_COLUMNS} FROM auth_user u WHERE u.uuid = %s", (user_uuid,)
    )


async def require_by_uuid(conn: Conn, user_uuid: str) -> Row:
    return await require_one(
        conn,
        f"SELECT u.id, {PUBLIC_COLUMNS} FROM auth_user u WHERE u.uuid = %s",
        (user_uuid,),
        entity="User",
    )


async def by_id(conn: Conn, user_id: int) -> Row | None:
    return await fetch_one(
        conn, f"SELECT u.id, {PUBLIC_COLUMNS} FROM auth_user u WHERE u.id = %s", (user_id,)
    )


async def credentials_by_login(conn: Conn, login: str) -> Row | None:
    """Fetch the hash for a sign-in attempt.

    Matched through the blind index of what was typed, as an email and as a
    username, so case and spacing do not matter - the index is computed on the
    normalised form. The stored columns are sealed and never compared.
    """
    return await fetch_one(
        conn,
        """
        SELECT u.id, u.uuid, u.email, u.username, u.full_name, u.role, u.status,
               u.password_hash
        FROM auth_user u
        WHERE u.email_idx = %s OR u.username_idx = %s
        """,
        (index_of("email", login), index_of("username", login)),
    )


async def credentials_by_id(conn: Conn, user_id: int) -> Row | None:
    """The hash for a signed-in person changing their own password.

    By id, because the row's email is sealed and cannot be looked up by; the
    person is already known.
    """
    return await fetch_one(
        conn,
        "SELECT u.id, u.uuid, u.role, u.status, u.password_hash FROM auth_user u WHERE u.id = %s",
        (user_id,),
    )


async def by_email(conn: Conn, email: str) -> Row | None:
    return await fetch_one(
        conn,
        f"SELECT u.id, {PUBLIC_COLUMNS} FROM auth_user u WHERE u.email_idx = %s",
        (index_of("email", email),),
    )


async def by_contact(conn: Conn, contact: str) -> Row | None:
    """Resolve a person by a contact they know: email, mobile, or a second
    email once a code sent to it has come back.

    The second address counts only when confirmed. Until then it is a claim
    somebody typed, and a claim must not be a way in - the address might be
    somebody else's, mistyped, or simply unreachable.

    Compared through the blind indexes, which are computed on the normalised
    form - so spacing and case in what was typed do not matter, and the sealed
    columns themselves are never read.
    """
    email_idx, mobile_idx = contact_indexes(contact)
    return await fetch_one(
        conn,
        f"""
        SELECT u.id, {PUBLIC_COLUMNS} FROM auth_user u
        WHERE (%s::text IS NOT NULL AND u.email_idx = %s)
           OR (%s::text IS NOT NULL AND u.mobile_idx = %s)
           OR (%s::text IS NOT NULL AND u.secondary_email_idx = %s
               AND u.secondary_email_verified_at IS NOT NULL)
        """,
        (email_idx, email_idx, mobile_idx, mobile_idx, email_idx, email_idx),
    )


def medium_of(user: Row, contact: str) -> str | None:
    """Which of this row's own contacts the given one is, or None if it is not
    one of them. Compared by blind index, so spacing and case do not matter and
    the sealed value is never opened."""
    email_idx, mobile_idx = contact_indexes(contact)
    if mobile_idx and user.get("mobile_idx") == mobile_idx:
        return "mobile"
    if email_idx and user.get("email_idx") == email_idx:
        return "email"
    if email_idx and user.get("secondary_email_idx") == email_idx:
        return "secondary_email"
    return None


def unverified_mediums(user: Row) -> list[str]:
    """The contacts on the account that no code has yet come back from."""
    return [
        medium
        for medium, contact, verified_at in (
            ("mobile", user.get("mobile"), user.get("mobile_verified_at")),
            ("email", user.get("email"), user.get("email_verified_at")),
        )
        if contact and not verified_at
    ]


async def mark_contact_verified(conn: Conn, user_id: int, medium: str) -> Row:
    """A code sent to this medium came back. The first time stands."""
    column = {
        "mobile": "mobile_verified_at",
        "email": "email_verified_at",
        "secondary_email": "secondary_email_verified_at",
    }[medium]
    row = await fetch_one(
        conn,
        f"""
        UPDATE auth_user u SET {column} = coalesce({column}, now())
         WHERE u.id = %s
        RETURNING u.id, {PUBLIC_COLUMNS}
        """,
        (user_id,),
    )
    assert row is not None
    return row


async def create(
    conn: Conn,
    *,
    full_name: str,
    email: str | None,
    role: str,
    username: str | None = None,
    mobile: str | None = None,
    organization_id: str | None = None,
    person_type: str | None = None,
    status: str = "pending",
    password_hash: str | None = None,
    registered_via_link_id: int | None = None,
    #: Section 9 makes this load-bearing for a data subject: it decides whether
    #: the account is a child's. Optional here because a consent link does not
    #: ask, and an assumed date would be worse than an absent one.
    dob: str | None = None,
) -> Row:
    # Every personal column goes in sealed. The ones the platform finds rows by
    # - email, mobile, username, the employee id - also get their blind index,
    # computed on the normalised form, which is what every lookup compares.
    mobile_n = normalise_mobile(mobile) if mobile else None
    email_n = email.strip().lower() if email else None
    sealed = await seal(
        "auth_user",
        {
            "full_name": full_name,
            "organization_id": organization_id,
            "email": email_n,
            "mobile": mobile_n,
            "username": username,
            "dob": dob,
        },
    )
    row = await fetch_one(
        conn,
        """
        INSERT INTO auth_user (username, full_name, email, mobile, organization_id,
                               role, person_type, status, password_hash,
                               registered_via_link_id, dob, minor_until,
                               email_idx, mobile_idx, username_idx, organization_id_idx)
        VALUES (%s, %s, %s, %s, %s, %s::user_role, %s::person_type, %s::user_status, %s, %s,
                %s, %s::date + INTERVAL '18 years', %s, %s, %s, %s)
        RETURNING id, uuid, username, full_name, email, mobile, organization_id,
                  role, person_type, status, dob, cmp_is_minor(minor_until) AS is_minor,
                  email_idx, mobile_idx, secondary_email_idx,
                  created_at, updated_at
        """,
        (
            sealed["username"],
            sealed["full_name"],
            sealed["email"],
            sealed["mobile"],
            sealed["organization_id"],
            role,
            person_type,
            status,
            password_hash,
            registered_via_link_id,
            sealed["dob"],
            dob,
            index_of("email", email_n),
            index_of("mobile", mobile_n),
            index_of("username", username),
            index_of("text", organization_id),
        ),
    )
    assert row is not None
    return row


async def update_profile(
    conn: Conn,
    user_id: int,
    *,
    full_name: str | None = None,
    mobile: str | None = None,
    organization_id: str | None = None,
    dob: str | None = None,
) -> Row:
    """Partial update. COALESCE keeps an omitted field unchanged rather than nulling it.

    A mobile that changes is unconfirmed until a code sent to the new number
    comes back - the old confirmation was of the old number. Every SET reads
    the row as it was, so `%s = mobile` compares with the previous value.
    """
    new_mobile = normalise_mobile(mobile) if mobile else None
    new_mobile_idx = index_of("mobile", new_mobile)
    sealed = await seal(
        "auth_user",
        {
            "full_name": full_name,
            "organization_id": organization_id,
            "mobile": new_mobile,
            "dob": dob,
        },
    )
    row = await fetch_one(
        conn,
        """
        UPDATE auth_user
           SET full_name          = COALESCE(%s, full_name),
               mobile             = COALESCE(%s, mobile),
               mobile_idx         = COALESCE(%s, mobile_idx),
               -- A changed number is unconfirmed; the comparison is on the
               -- index, because the sealed value differs on every write.
               mobile_verified_at = CASE WHEN %s::text IS NULL OR %s::text = mobile_idx
                                         THEN mobile_verified_at ELSE NULL END,
               organization_id    = COALESCE(%s, organization_id),
               organization_id_idx = COALESCE(%s, organization_id_idx),
               dob                = COALESCE(%s, dob),
               minor_until        = COALESCE(%s::date + INTERVAL '18 years', minor_until)
         WHERE id = %s
        RETURNING id, uuid, username, full_name, email, mobile, organization_id,
                  role, person_type, status, dob, cmp_is_minor(minor_until) AS is_minor,
                  mobile_verified_at, email_verified_at,
                  secondary_email, secondary_email_verified_at,
                  email_idx, mobile_idx, secondary_email_idx,
                  created_at, updated_at
        """,
        (
            sealed["full_name"],
            sealed["mobile"],
            new_mobile_idx,
            new_mobile_idx,
            new_mobile_idx,
            sealed["organization_id"],
            index_of("text", organization_id),
            sealed["dob"],
            dob,
            user_id,
        ),
    )
    assert row is not None
    return row


async def set_secondary_email(conn: Conn, user_id: int, email: str | None) -> Row:
    """Set, replace or clear the second address.

    A *changed* address is unconfirmed: a code has to come back from the new one
    before it signs anyone in. An address re-saved unchanged keeps the
    confirmation it already earned, the way a re-saved mobile does - otherwise
    pressing save on a row she had already proved would quietly take away a way
    of signing in. "Unchanged" is decided on the blind index, since the sealed
    value differs on every write.
    """
    email_n = email.strip().lower() if email else None
    idx = index_of("email", email_n)
    sealed = await seal("auth_user", {"secondary_email": email_n})
    row = await fetch_one(
        conn,
        f"""
        UPDATE auth_user u
           SET secondary_email_verified_at =
                 CASE WHEN %s::text IS NOT NULL AND %s::text = u.secondary_email_idx
                      THEN u.secondary_email_verified_at ELSE NULL END,
               secondary_email = %s,
               secondary_email_idx = %s
         WHERE u.id = %s
        RETURNING u.id, {PUBLIC_COLUMNS}
        """,
        (idx, idx, sealed["secondary_email"], idx, user_id),
    )
    assert row is not None
    return row


async def set_role(conn: Conn, user_id: int, role: str) -> Row:
    row = await fetch_one(
        conn,
        """
        UPDATE auth_user SET role = %s::user_role WHERE id = %s
        RETURNING id, uuid, full_name, email, role, status
        """,
        (role, user_id),
    )
    assert row is not None
    return row


async def set_status(conn: Conn, user_id: int, status: str) -> Row:
    row = await fetch_one(
        conn,
        """
        UPDATE auth_user SET status = %s::user_status WHERE id = %s
        RETURNING id, uuid, full_name, email, role, status
        """,
        (status, user_id),
    )
    assert row is not None
    return row


async def set_password(conn: Conn, user_id: int, password_hash: str) -> None:
    await execute(
        conn, "UPDATE auth_user SET password_hash = %s WHERE id = %s", (password_hash, user_id)
    )


async def clear_password(conn: Conn, user_id: int) -> None:
    """No password at all, which is what a data principal has. Not a random one:
    a random hash is a credential that exists, and this is a row that must
    never again answer the console's sign-in form."""
    await execute(conn, "UPDATE auth_user SET password_hash = NULL WHERE id = %s", (user_id,))


async def set_person_type(conn: Conn, user_id: int, person_type: str) -> Row:
    row = await fetch_one(
        conn,
        """
        UPDATE auth_user SET person_type = %s::person_type WHERE id = %s
        RETURNING id, uuid, full_name, person_type
        """,
        (person_type, user_id),
    )
    assert row is not None
    return row


# ------------------------------------------------------------------ listing
LIST_SORTS = ("created_at", "full_name", "email", "role", "status")


async def list_users(
    conn: Conn,
    req: PageRequest,
    *,
    role: str | None = None,
    status: str | None = None,
    person_type: str | None = None,
    q: str | None = None,
) -> tuple[list[Row], str | None, int]:
    where = ["1 = 1"]
    params: list[Any] = []

    if role:
        where.append("u.role = %s::user_role")
        params.append(role)
    if status:
        where.append("u.status = %s::user_status")
        params.append(status)
    if person_type:
        where.append("u.person_type = %s::person_type")
        params.append(person_type)
    if q:
        # Every column a person used to be searched by is sealed, and a
        # substring of ciphertext matches nothing. What still works, and is
        # what people actually paste in: an exact email, mobile, username or
        # employee id, matched through its blind index.
        email_idx, mobile_idx = contact_indexes(q.strip())
        where.append(
            "(u.email_idx = %s OR u.secondary_email_idx = %s OR u.mobile_idx = %s "
            "OR u.username_idx = %s OR u.organization_id_idx = %s)"
        )
        params.extend(
            [email_idx, email_idx, mobile_idx, index_of("username", q), index_of("text", q)]
        )

    clause = " AND ".join(where)
    keyset, keyset_params = keyset_clause(req, alias="u", id_column="id")

    rows = await fetch_all(
        conn,
        f"SELECT u.id AS _row_id, {PUBLIC_COLUMNS} FROM auth_user u WHERE {clause}{keyset}",
        [*params, *keyset_params],
    )
    total = await fetch_one(conn, f"SELECT count(*) AS n FROM auth_user u WHERE {clause}", params)
    items, next_cursor = build_page(rows, req)
    return items, next_cursor, int((total or {}).get("n", 0))


# --------------------------------------------------------- person type history
async def record_person_type_change(
    conn: Conn,
    *,
    user_id: int,
    from_type: str | None,
    to_type: str,
    reason: str | None,
    changed_by: int,
) -> Row:
    sealed = await seal("person_type_history", {"reason": reason})
    row = await fetch_one(
        conn,
        """
        INSERT INTO person_type_history (auth_user_id, from_type, to_type, reason, changed_by)
        VALUES (%s, %s::person_type, %s::person_type, %s, %s)
        RETURNING history_uuid, from_type, to_type, reason, changed_at
        """,
        (user_id, from_type, to_type, sealed["reason"], changed_by),
    )
    assert row is not None
    return row


async def person_type_history(conn: Conn, user_id: int) -> list[Row]:
    return await fetch_all(
        conn,
        """
        SELECT h.history_uuid, h.from_type, h.to_type, h.reason, h.changed_at,
               a.uuid AS changed_by_uuid, a.full_name AS changed_by_name
        FROM person_type_history h
        JOIN auth_user a ON a.id = h.changed_by
        WHERE h.auth_user_id = %s
        ORDER BY h.changed_at DESC
        """,
        (user_id,),
    )


async def count_by_role(conn: Conn) -> dict[str, int]:
    rows = await fetch_all(
        conn, "SELECT role::text AS role, count(*) AS n FROM auth_user GROUP BY role"
    )
    return {r["role"]: int(r["n"]) for r in rows}


async def count_by_status(conn: Conn) -> dict[str, int]:
    rows = await fetch_all(
        conn, "SELECT status::text AS status, count(*) AS n FROM auth_user GROUP BY status"
    )
    return {r["status"]: int(r["n"]) for r in rows}


async def collection_owners(conn: Conn) -> list[Row]:
    """Active people who can be accountable for a data source.

    Deliberately its own query rather than a filter on the register. A DCO Admin
    routing a project, or an R&D owner naming an RCO, has to pick a person and
    has no business reading the account register - so this returns the minimum
    that makes the choice possible: who they are, enough to tell two people with
    the same name apart, and which kind of owner they are. No status, no person
    type, no organisation id, no contact history.

    The role comes back because it constrains the choice rather than merely
    describing it: an RCO is accountable for collection the R&D team does itself
    and a DCO for a third party's, so the caller filters by which the source is.
    """
    return await fetch_all(
        conn,
        """SELECT u.uuid, u.full_name, u.email, u.role
           FROM auth_user u
           WHERE u.role IN ('dco', 'rco') AND u.status = 'active'
           ORDER BY u.role, u.full_name""",
    )


async def staff_directory(conn: Conn) -> list[Row]:
    """Active members of staff, for naming one as a processor's respondent.

    The minimum that makes the choice possible: who they are, enough to tell
    two people with the same name apart, and their role. Offered only to the
    roles that manage the registry.
    """
    return await fetch_all(
        conn,
        """SELECT u.uuid, u.full_name, u.email, u.role
           FROM auth_user u
           WHERE u.role <> 'data_subject' AND u.status = 'active'
           ORDER BY u.full_name""",
    )


async def active_emails_for_role(conn: Conn, role: str) -> list[str]:
    """Where to tell a role something: every active account holding it."""
    rows = await fetch_all(
        conn,
        "SELECT u.email FROM auth_user u WHERE u.role = %s::user_role AND u.status = 'active'",
        (role,),
    )
    return [str(r["email"]) for r in rows if r.get("email")]
