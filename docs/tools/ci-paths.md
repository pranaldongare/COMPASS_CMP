# The CI edit this environment cannot make

`.github/workflows/ci.yml` is out of date in three ways, and none of them can be
pushed from the environment this repository was worked on with: the credential
lacks the `workflow` OAuth scope, and GitHub rejects a whole push that touches a
workflow file. CI is red until somebody with the scope applies this.

**The corrected file is beside this one: [`ci.yml.proposed`](ci.yml.proposed).**
It was produced from the current workflow by transformation rather than
retyped, parses as YAML, and is meant to replace `.github/workflows/ci.yml`
wholesale:

```bash
cp docs/tools/ci.yml.proposed .github/workflows/ci.yml
git add .github/workflows/ci.yml && git commit -m "ci: pip, the new paths, no image job"
git push
```

## What changes, and why

**1. The paths from the restructure.** `cmp_backend` → `backend/api`; the portal
matrix becomes `[console, portal]` under `frontend/`; the coverage artefact path
follows.

**2. `uv` → `pip`.** The three backend jobs used `astral-sh/setup-uv` and
`uv sync --frozen`. They now use `actions/setup-python` with pip caching keyed
on `requirements-dev.txt`, and `pip install -r requirements-dev.txt`. Every
`uv run X` is `X`, because the environment is on the path. The dependency audit
reads `requirements.txt` and `requirements-dev.txt` directly with
`--skip-editable`, since the project itself is installed editable and is not on
PyPI.

**3. The `image` job is gone.** It built `backend/api/docker/Dockerfile` and
scanned the result with Trivy. The Dockerfile no longer exists, so the job would
fail at checkout — and it had been failing for weeks before that on
`aquasecurity/trivy-action@0.28.0`, a tag that does not exist. Removing the job
removes both failures.

**Unchanged, and worth knowing:** the `test` job's PostgreSQL and Redis come from
GitHub's own `services:` containers on the runner. They never depended on the
repository's compose file, so removing it changes nothing in CI.

## After it lands

Four jobs: backend lint/format/types, backend tests (with migrations up, down
and up, and the OpenAPI freshness check), both portals, and the dependency and
secret scan. Nothing builds an image, because nothing ships as one.
