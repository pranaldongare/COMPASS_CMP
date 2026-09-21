# The CI edit this environment cannot make

`.github/workflows/ci.yml` carries nine paths that phase 1 of the restructure
invalidated. They are not in the restructure commits, and CI is red until they
are applied, because the credential this repository was worked on with lacks the
`workflow` OAuth scope — GitHub rejects a whole push that touches a workflow
file, not just that file.

Anyone with the scope can apply these nine changes. Nothing else in the file
needs to move.

| Line | From | To |
|---|---|---|
| 6 | `# It sat under `cmp_backend/` from` | `# It sat under `backend/api/` from` (a comment) |
| 42 | `working-directory: cmp_backend` | `working-directory: backend/api` |
| 54 | `cache-dependency-glob: cmp_backend/uv.lock` | `cache-dependency-glob: backend/api/uv.lock` |
| 117 | `cache-dependency-glob: cmp_backend/uv.lock` | `cache-dependency-glob: backend/api/uv.lock` |
| 156 | `path: cmp_backend/coverage.xml` | `path: backend/api/coverage.xml` |
| 165 | `portal: [cmp_internal_ui, cmp_public_ui]` | `portal: [console, portal]` |
| 168 | `working-directory: ${{ matrix.portal }}` | `working-directory: frontend/${{ matrix.portal }}` |
| 201 | `cache-dependency-glob: cmp_backend/uv.lock` | `cache-dependency-glob: backend/api/uv.lock` |
| 245-246 | `context: cmp_backend` / `file: cmp_backend/docker/Dockerfile` | `context: backend/api` / `file: backend/api/docker/Dockerfile` |

As a patch, from the repository root:

```bash
python3 - <<'EOF'
from pathlib import Path
p = Path(".github/workflows/ci.yml"); s = p.read_text()
s = s.replace("working-directory: cmp_backend", "working-directory: backend/api")
s = s.replace("cache-dependency-glob: cmp_backend/uv.lock", "cache-dependency-glob: backend/api/uv.lock")
s = s.replace("path: cmp_backend/coverage.xml", "path: backend/api/coverage.xml")
s = s.replace("portal: [cmp_internal_ui, cmp_public_ui]", "portal: [console, portal]")
s = s.replace("working-directory: ${{ matrix.portal }}", "working-directory: frontend/${{ matrix.portal }}")
s = s.replace("context: cmp_backend", "context: backend/api")
s = s.replace("file: cmp_backend/docker/Dockerfile", "file: backend/api/docker/Dockerfile")
s = s.replace("under `cmp_backend/` from", "under `backend/api/` from")
p.write_text(s)
print("ci.yml repointed")
EOF
```

**One unrelated line is worth fixing while you are in there.** The
`Build and scan the API image` job fails on
`uses: aquasecurity/trivy-action@0.28.0` — there is no such tag; every release
of that action carries a `v`. `@v0.36.0` is the fix, and it has been failing
since before the restructure.

The job names in CI will still say `cmp_internal_ui typecheck, lint, tests,
build` until line 160's `name:` is updated too; with `portal: [console, portal]`
it reads `console typecheck, …`, which is what you want.
