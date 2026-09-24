# 0018. pip and a virtualenv; nothing ships as a container

**Status:** accepted · 2026-09-21. Supersedes the container deployment in
[deployment-with-containers.md](../history/deployment-with-containers.md) and
[api-deployment-with-containers.md](../history/api-deployment-with-containers.md).

## Context

The platform was planned to run as containers: an image each for the API, the
console and the portal, a compose stack, and nginx in front terminating TLS,
rate-limiting and scrubbing tokens from its log. The API's dependencies were
managed with uv and a lockfile. The key service, added later, was already a
plain `python -m venv` and `pip install`.

None of the images was what anybody actually ran. Development ran the
processes directly, the stack was not deployed anywhere, and the image job in
CI had been failing for weeks on an action tag that does not exist. Two
toolchains for Python meant two ways for a dependency to differ.

## Decision

- **The API is installed as the key service is.** `python3.12 -m venv .venv`,
  then `pip install -r requirements-dev.txt`. uv and `uv.lock` are gone.
- **`requirements.txt` is the runtime, pinned exactly**: 84 pins, transitive
  dependencies included, at the versions `uv.lock` had resolved on the day, so
  nothing changed version in the move. `requirements-dev.txt` adds the test
  suite, the linters, the type checker and the project itself, editable.
  `pyproject.toml` keeps its `[tool.*]` blocks and reads its dependencies from
  `requirements.txt` through setuptools, so there is one list.
- **No image of ours.** The three Dockerfiles, the compose stack, the nginx
  configuration and the `.dockerignore` files are removed, and the
  standalone-output block leaves both Next configs. Every service is a process:
  `python -m cmp` and `celery` in the API's virtualenv, the key service in its
  own, the portals under `npm`.
- **One Docker file stays, for the datastores only.**
  `backend/api/dev-services.yml` starts PostgreSQL and Redis on a machine that
  has no other, under the project and volume names the development database
  already lived in, so it adopts the existing data.
- The two deployment documents moved to [docs/history/](../history/README.md),
  because the queue names, worker counts and the single Beat they record still
  hold.

## Consequences

- Whatever nginx would have done, the application does or a deployment must
  provide. The body-size cap was always the application's, and the comments
  now say so. Tokens are scrubbed from the access path by the application.
  TLS is a deployment's to terminate.
- **Trusting `X-Forwarded-For` is now an assertion.** In production the
  client address is read from that header
  (`api/middleware/request_context.py`, `client_ip`), which is only safe if a
  proxy the deployment controls is the only way in and overwrites it. Nothing
  in this repository provides that proxy any more.
- Dependency upgrades are an edit to a pin, and a transitive one is visible in
  the diff.
- **Live CI has not followed yet.** `.github/workflows/ci.yml` still installs
  with `astral-sh/setup-uv` and `uv sync --frozen` against a `uv.lock` that no
  longer exists, still uses the pre-restructure `cmp_backend` paths, and still
  builds the deleted image. The corrected workflow is
  [docs/tools/ci.yml.proposed](../tools/ci.yml.proposed). It cannot be pushed
  from the environment this was done in, because the credential lacks the
  `workflow` scope. CI is red until someone with that scope applies it
  ([ci-paths.md](../tools/ci-paths.md)).
- How to set up a machine is in
  [local-development.md](../operations/local-development.md).

## Revisit when

A deployment target needs an image: a platform that runs containers only, or a
scale-out that needs identical, reproducible units. That is a new record and a
Dockerfile written against the pinned requirements, not a restoration of the
old stack.
