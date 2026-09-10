# 0008. An unknown enumerated value is a 422 with the choices named

Status: accepted. September 2026.

## Context

Enumerated request fields arrive as strings and are converted to a Python
`StrEnum` inside the service, where the domain rule that depends on them
lives. A bare `Enum("bogus")` raises `ValueError`, which the error handlers
turned into a 500 and, through the portal's proxy, into a dropped
connection. Negative testing found five routes that did this, and the notice
importer did it with a language name.

## Decision

One helper, `cmp.validation.choice(enum, value, field=...)`, performs every
conversion. An unknown value raises the validation error the API already
has, so the client gets 422, the field name, and the valid choices spelled
out. Request models keep the field as a string; the conversion stays in the
service so the enum stays a domain concern.

A notice document naming a language the platform does not store is refused
by name for the same reason.

## Consequences

- No route can leak a stack trace for a typo in a filter.
- Regression tests post an unknown value to every enumerated field and
  expect 422.
- Adding an enumerated field means calling the helper, and the review asks
  for it.

## Revisit when

Pydantic enums on the request model become preferable. They would move the
error earlier at the cost of the domain owning the conversion.
