"""What may cross: the public routes, the headers and cookies, and one input rule.

**Routes.** The public portal calls 58 of the API's ~340 operations. Those, and
nothing else, may cross: every staff route, `/auth/login`, the second factor,
`/metrics`, `/docs` - all refused. The collector enforces the list (it is the
side that matters); the bridge checks the same list first so a refused request
never costs a queue round trip. The table is method plus path template; a
template's segment matches one URL-safe path segment, no slashes.

The list was read off the portal's own API calls (`frontend/portal/src/features/
*/api.ts`, `src/providers/auth-provider.tsx`, `src/features/account/api.ts`).
A new portal call needs a new row here, or it answers 404 through the relay.

**Headers and cookies.** Requests carry only what the API reads; replies carry
only what the browser needs. Of the cookies, only the session, CSRF and ticket
cookies cross.

**No sealed values in.** The API opens the sealed values in a relayed response
(`cmp.api.middleware.relay_open_sealed`), and `seal()` passes an already-sealed
value through untouched. Together that would let someone submit another
person's ciphertext as "their" name and read it back opened. So the collector
refuses a request when the sealed-value prefix (`SE::`, also percent-encoded)
appears in:

* the query string;
* any forwarded header value except the cookie;
* a body that is not multipart - searched whole as text, and, when it parses
  as JSON, every key and string of the decoded document (a JSON escape can
  spell the prefix without its bytes). A document nested too deeply to parse
  is refused, not passed;
* a `multipart/form-data` body: the name, `filename` and `filename*` (RFC 2231
  decoded) of every part, every part header, and the bytes of every part that
  is not a file. A part is a file only when its Content-Disposition names a
  `filename`; a file's bytes are the person's own document and may hold
  anything, so they alone are not searched.

A multipart body is read only in the one shape a browser sends, because the
API reads it with another parser and the two must not disagree about what is a
field. Anything else is refused unread: a `charset` other than UTF-8 or any
parameter but `boundary` and `charset` on the body's Content-Type; a preamble
or an epilogue; a part header other than one Content-Disposition and at most
one Content-Type (so no Content-Transfer-Encoding); a part Content-Type with a
parameter other than `charset=utf-8`.

This is the first gate, kept as defence in depth. The API is the authority: on
a relayed request it checks again, with its own parser, before the route runs
(ADR 0032), so no difference between this parser and the API's can open a way
through.
"""

from __future__ import annotations

import codecs
import json
import re
from collections.abc import Iterable
from email.message import Message
from email.utils import collapse_rfc2231_value
from urllib.parse import unquote_plus

#: One URL path segment: a token, a uuid, a percent-encoded value. No slash.
_SEG = r"[A-Za-z0-9._~%-]+"

#: (method, template). `{x}` is one segment.
PUBLIC_ROUTES: tuple[tuple[str, str], ...] = (
    # Sign-up, code sign-in, the session (v1/auth, principal subset)
    ("POST", "/auth/register"),
    ("POST", "/auth/register/verify"),
    ("POST", "/auth/otp/request"),
    ("POST", "/auth/otp/verify"),
    ("GET", "/auth/me"),
    ("POST", "/auth/logout"),
    ("GET", "/auth/sessions"),
    ("DELETE", "/auth/sessions/{session}"),
    # The consent link (public/consent)
    ("GET", "/c/{token}"),
    ("POST", "/c/{token}/otp"),
    ("POST", "/c/{token}/otp/verify"),
    ("GET", "/c/{token}/notice"),
    ("POST", "/c/{token}/consent"),
    # Her own records (v1/me)
    ("PATCH", "/me"),
    ("POST", "/me/person-type"),
    ("POST", "/me/contacts/code"),
    ("POST", "/me/contact/verify"),
    ("DELETE", "/me/secondary-email"),
    ("GET", "/me/consents"),
    ("GET", "/me/consents/{consent}/grants"),
    ("GET", "/me/consents/{consent}/history"),
    ("GET", "/me/consents/{consent}/notice"),
    ("GET", "/me/consents/{consent}/trail"),
    ("GET", "/me/consents/{consent}/record"),
    ("POST", "/me/consents/{consent}/withdraw"),
    ("GET", "/me/disclosures"),
    ("GET", "/me/breach-notices"),
    # Her rights requests and nominations (v1/rights subject router)
    ("GET", "/me/requests"),
    ("POST", "/me/requests"),
    ("GET", "/me/requests/{request}"),
    ("GET", "/me/requests/{request}/trail"),
    ("GET", "/me/requests/{request}/download"),
    ("GET", "/me/requests/{request}/files/{file}"),
    ("POST", "/me/requests/{request}/attachments"),
    ("POST", "/me/requests/{request}/dispute"),
    ("GET", "/me/nominations"),
    ("POST", "/me/nominations"),
    ("DELETE", "/me/nominations/{nomination}"),
    ("GET", "/me/nominee-of"),
    # The public rights pages (public/rights)
    ("GET", "/rights"),
    ("POST", "/rights/requests"),
    ("POST", "/rights/requests/verify"),
    ("POST", "/rights/nominee/start"),
    ("POST", "/rights/nominee/requests"),
    ("GET", "/rights/nominations/{token}"),
    ("POST", "/rights/nominations/{token}/code"),
    ("POST", "/rights/nominations/{token}/accept"),
    ("POST", "/rights/nominations/{token}/decline"),
    # An outside holder's ticket (public/holder_tickets)
    ("POST", "/holder-tickets/{token}/code"),
    ("POST", "/holder-tickets/{token}/verify"),
    ("GET", "/holder-tickets/{token}/ticket"),
    ("POST", "/holder-tickets/{token}/messages"),
    ("GET", "/holder-tickets/{token}/messages/{message}/evidence"),
    ("POST", "/holder-tickets/{token}/answer"),
    ("POST", "/holder-tickets/{token}/sign-out"),
    # Reference data and the notifications page
    ("GET", "/meta/enums"),
    ("GET", "/meta/data-categories"),
    ("GET", "/notifications"),
)

#: Development only (DEV_SHOW_CODES): the one-time-code popup. Refused unless
#: the relay runs with RELAY_ENVIRONMENT=local and RELAY_ALLOW_DEV_ROUTES=true.
DEV_ROUTES: tuple[tuple[str, str], ...] = (
    ("GET", "/dev/codes"),
    ("GET", "/dev/seed-accounts"),
)

#: An encoded slash, backslash or dot inside a segment: a token never needs one,
#: and a path that does is trying to change which route the API sees.
_ENCODED_SEPARATOR = re.compile(r"%(2f|5c|2e)", re.IGNORECASE)

#: Methods whose replay could change something. Everything else is a read.
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def _compile(template: str) -> re.Pattern[str]:
    pattern = re.sub(
        r"\{[a-z_]+\}", _SEG, re.escape(template).replace(r"\{", "{").replace(r"\}", "}")
    )
    return re.compile(pattern)


class RouteTable:
    """The allow-list, compiled. `match` returns the template, which is also what
    gets logged - never the path itself, which can carry a capability token."""

    def __init__(self, *, allow_dev_routes: bool = False) -> None:
        routes = PUBLIC_ROUTES + (DEV_ROUTES if allow_dev_routes else ())
        self._routes = [(m, t, _compile(t)) for m, t in routes]

    def match(self, method: str, path: str) -> str | None:
        method = method.upper()
        segments = path.split("/")
        if (
            not path.startswith("/")
            or "\\" in path
            or _ENCODED_SEPARATOR.search(path)
            # An empty, "." or ".." segment: an HTTP client normalises it away,
            # so the API would see a different route from the one checked here.
            or any(seg in ("", ".", "..") for seg in segments[1:])
        ):
            return None
        for allowed_method, template, pattern in self._routes:
            # fullmatch, not match with $: a "$" also matches before a final
            # newline, which would let "/c/tok\n" pass as "/c/{token}".
            if allowed_method == method and pattern.fullmatch(path):
                return template
        return None


# ------------------------------------------------------------------- headers

#: Request headers the API reads. The CSRF header's name is configurable and
#: added at run time; so is the development client header.
_REQUEST_HEADERS = frozenset(
    {"accept", "accept-language", "content-type", "user-agent", "x-request-id"}
)

#: Reply headers the browser needs.
_RESPONSE_HEADERS = frozenset(
    {
        "content-type",
        "content-disposition",
        "content-language",
        "cache-control",
        "pragma",
        "expires",
        "set-cookie",
        "retry-after",
        "x-request-id",
        "x-response-time-ms",
        "x-recorded-sha256",
        "x-content-sha256",
        "x-export-generated-at",
    }
)


def filter_cookie_header(value: str, allowed: frozenset[str]) -> str | None:
    """Keep only the named cookies of a `Cookie` header."""
    kept = []
    for part in value.split(";"):
        name, sep, cookie = part.strip().partition("=")
        if sep and name in allowed:
            kept.append(f"{name}={cookie}")
    return "; ".join(kept) or None


def request_headers(
    headers: Iterable[tuple[str, str]],
    *,
    csrf_header: str,
    cookie_names: frozenset[str],
    extra: frozenset[str] = frozenset(),
) -> list[tuple[str, str]]:
    """The request headers that may cross, names lower-cased."""
    allowed = _REQUEST_HEADERS | {csrf_header.lower()} | {h.lower() for h in extra}
    out: list[tuple[str, str]] = []
    for name, value in headers:
        lower = name.lower()
        if lower == "cookie":
            kept = filter_cookie_header(value, cookie_names)
            if kept:
                out.append(("cookie", kept))
        elif lower in allowed:
            out.append((lower, value))
    return out


def response_headers(headers: Iterable[tuple[str, str]]) -> list[tuple[str, str]]:
    """The reply headers that may cross back, names lower-cased."""
    return [(n.lower(), v) for n, v in headers if n.lower() in _RESPONSE_HEADERS]


# --------------------------------------------------------------- input rule

SEALED_PREFIX = "SE::"
_MARKERS = (SEALED_PREFIX, "SE%3A%3A", "SE%3a%3a")

#: An RFC 2046 boundary: 1-70 characters from this set, not ending in a space.
_BOUNDARY = re.compile(r"[0-9A-Za-z'()+_,\-./:=? ]{0,69}[0-9A-Za-z'()+_,\-./:=?]")
#: An RFC 9110 token: what a part header's name may be.
_TOKEN = re.compile(rb"[!#$%&'*+\-.^_`|~0-9A-Za-z]+")
#: The part headers a browser sends, each at most once.
_PART_HEADERS = frozenset({"content-disposition", "content-type"})


class _Refused(Exception):
    """A multipart body not in the one shape a browser sends: refused unread."""


def _text_has_marker(text: str) -> bool:
    return any(m in text for m in _MARKERS) or SEALED_PREFIX in unquote_plus(text)


def _json_has_marker(document: object) -> bool:
    """Every string and key of a decoded JSON document. A JSON escape can spell
    the prefix without its bytes - "SE\\u003a\\u003a" - and the API's parser
    decodes it, so the raw text alone is not enough. Walked with a stack, not
    recursion: a deep document must not end the search early."""
    stack = [document]
    while stack:
        value = stack.pop()
        if isinstance(value, str):
            if _text_has_marker(value):
                return True
        elif isinstance(value, list):
            stack.extend(value)
        elif isinstance(value, dict):
            for key, item in value.items():
                if _text_has_marker(key):
                    return True
                stack.append(item)
    return False


def _body_text_has_marker(raw: bytes) -> bool:
    if _text_has_marker(raw.decode("utf-8", errors="replace")):
        return True
    # Whatever the declared type, a body that parses as JSON is checked decoded:
    # the declared type is the sender's claim, and parsers are lenient.
    try:
        document = json.loads(raw)
    except RecursionError:
        return True  # too deep to read here: refused, never waved through
    except ValueError:
        return False
    return _json_has_marker(document)


def _parseparam(s: str) -> list[str]:
    """A header split at its `;`s, outside double quotes - verbatim the function
    the API's form parser uses (python-multipart 0.0.32, itself vendored from
    CPython 3.14's `email.message._parseparam`), so both sides find the same
    parameters."""
    s = ";" + s
    plist: list[str] = []
    start = 0
    while s.find(";", start) == start:
        start += 1
        end = s.find(";", start)
        ind, diff = start, 0
        while end > 0:
            diff += s.count('"', ind, end) - s.count('\\"', ind, end)
            if diff % 2 == 0:
                break
            end, ind = ind, s.find(";", end + 1)
        if end < 0:
            end = len(s)
        i = s.find("=", start, end)
        if i == -1:  # noqa: SIM108 - kept as the API's parser has it
            f = s[start:end]
        else:
            f = s[start:i].rstrip().lower() + "=" + s[i + 1 : end].lstrip()
        plist.append(f.strip())
        start = end
    return plist


def _params(value: str) -> list[tuple[str, str]]:
    """A header's parameters as the API's form parser reads them (python-
    multipart's `parse_options_header`), but every one kept, in order: the
    extended `key*` forms it ignores, and repeats it would collapse."""
    if ";" not in value:
        return []
    _, *segments = _parseparam(value)
    out: list[tuple[str, str]] = []
    for segment in segments:
        key, _, val = segment.partition("=")
        if len(val) >= 2 and val[0] == '"' and val[-1] == '"':
            val = val[1:-1].replace("\\\\", "\\").replace('\\"', '"')
        out.append((key, val))
    return out


def _decoded_params(value: str) -> tuple[set[str], list[str]]:
    """(the parameter names, every name and value as text) as the standard
    library reads a header: RFC 2231 `key*=charset''%xx` values decoded and
    `key*0`, `key*1` continuations joined - the reading an older or other
    parser could take."""
    message = Message()
    message["x"] = value
    try:
        params: list[tuple[str, object]] = list(message.get_params(header="x", failobj=[]))
    except Exception as exc:
        raise _Refused("unreadable header parameters") from exc
    names: set[str] = set()
    texts: list[str] = []
    for key, val in params[1:]:
        names.add(key)
        texts.append(key)
        if isinstance(val, tuple):
            texts.extend(str(v) for v in val if v is not None)
            texts.append(collapse_rfc2231_value(val))
        else:
            texts.append(str(val))
    return names, texts


def _is_utf8(charset: str) -> bool:
    try:
        return codecs.lookup(charset).name == "utf-8"
    except LookupError:
        return False


def _boundary(content_type: str) -> bytes | None:
    """The boundary, None when there is none (the API cannot read the body as a
    form either), or `_Refused` for any parameter a browser does not send."""
    params = _params(content_type)
    names = [key for key, _ in params]
    if len(names) != len(set(names)):
        raise _Refused("a repeated parameter")
    boundary: str | None = None
    for key, value in params:
        if key == "boundary":
            boundary = value
        elif not (key == "charset" and _is_utf8(value)):
            raise _Refused("a charset or parameter a browser does not send")
    if boundary is None:
        return None
    if not _BOUNDARY.fullmatch(boundary):
        raise _Refused("not an RFC 2046 boundary")
    return boundary.encode("ascii")


def _part(chunk: bytes) -> tuple[dict[str, str], bytes]:
    """One part's headers (names lower-cased) and its bytes."""
    split = -1 if chunk.startswith(b"\r\n") else chunk.find(b"\r\n\r\n")
    if split < 0:
        raise _Refused("a part without headers")
    headers: dict[str, str] = {}
    for line in chunk[:split].split(b"\r\n"):
        name, colon, value = line.partition(b":")
        if not colon or not _TOKEN.fullmatch(name) or any(c in value for c in b"\r\n\0"):
            raise _Refused("a malformed part header")
        lower = name.decode("ascii").lower()
        if lower not in _PART_HEADERS or lower in headers:
            raise _Refused("a part header a browser does not send, or sends once")
        headers[lower] = value.lstrip(b" ").decode("latin-1")
    if "content-disposition" not in headers:
        raise _Refused("a part without a Content-Disposition")
    return headers, chunk[split + 4 :]


def _parts(body: bytes, boundary: bytes) -> list[tuple[dict[str, str], bytes]]:
    """The parts, split exactly where the API's parser splits them, or
    `_Refused` for anything that parser might read differently."""
    dash = b"--" + boundary
    if body in (dash + b"--", dash + b"--\r\n"):
        return []  # an empty form
    if not body.startswith(dash + b"\r\n"):
        raise _Refused("a preamble")
    delimiter = b"\r\n" + dash
    parts: list[tuple[dict[str, str], bytes]] = []
    position = len(dash) + 2
    while True:
        end = body.find(delimiter, position)
        if end < 0:
            raise _Refused("no closing delimiter")
        parts.append(_part(body[position:end]))
        after = end + len(delimiter)
        if body[after : after + 2] == b"--":
            if body[after + 2 :] not in (b"", b"\r\n"):
                raise _Refused("an epilogue")
            return parts
        if body[after : after + 2] != b"\r\n":
            raise _Refused("the boundary inside a part")
        position = after + 2


def _part_has_marker(headers: dict[str, str], payload: bytes) -> bool:
    if any(_text_has_marker(value) for value in headers.values()):
        return True
    disposition = headers["content-disposition"]
    plain = {key for key, _ in _params(disposition)}
    decoded, texts = _decoded_params(disposition)
    if any(_text_has_marker(text) for text in texts):
        return True
    if "content-type" in headers:
        content_type = headers["content-type"]
        if any(not (key == "charset" and _is_utf8(value)) for key, value in _params(content_type)):
            raise _Refused("a part Content-Type parameter other than charset=utf-8")
        if decoded_names := _decoded_params(content_type)[0] - {"charset"}:
            raise _Refused(f"part Content-Type parameters {sorted(decoded_names)}")
    # A file only when both readings find a plain `filename`: the API's parser
    # ignores `filename*` and keeps such a part as a text field.
    if "filename" in plain and "filename" in decoded:
        return False
    return _body_text_has_marker(payload)


def _multipart_has_marker(content_type: str, body: bytes) -> bool:
    try:
        boundary = _boundary(content_type)
        if boundary is None:
            return _body_text_has_marker(body)
        return any(_part_has_marker(h, p) for h, p in _parts(body, boundary))
    except _Refused:
        return True


def carries_sealed_value(
    query: str,
    content_type: str | None,
    body: bytes | None,
    headers: Iterable[tuple[str, str]] = (),
) -> bool:
    """True when the request carries a sealed value - or is a multipart body
    not in a browser's shape, which is treated as carrying one.

    `headers` are the header pairs that will be forwarded; the cookie is not
    searched (the module docstring says what is)."""
    if query and _text_has_marker(query):
        return True
    for name, value in headers:
        if name.lower() != "cookie" and _text_has_marker(value):
            return True
    if not body:
        return False
    if (content_type or "").strip().lower().startswith("multipart/"):
        return _multipart_has_marker(content_type or "", body)
    return _body_text_has_marker(body)
