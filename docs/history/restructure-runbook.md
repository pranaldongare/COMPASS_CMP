> **Historical.** The commands for restructuring the repository, written
> before any of it was done. Phases 1, 2 and 5 were carried out in September
> 2026 (`89b1e8e`, `209e1da`, `879bfc1`): the services moved under `backend/`
> and `frontend/`, every document under `docs/`, and the API went from `uv`
> to `pip` and a virtualenv as Phase 5 below draws it, with the container
> images removed at the same time. Its paths (`cmp_backend/`, `cmp_internal_ui/`, the Dockerfile)
> no longer exist. Phases 3 and 4 have not been done; what remains of them is
> argued in the [proposal](../architecture/proposed-repository-structure.md).
> Current layout:
> [docs/architecture/repository-layout.md](../architecture/repository-layout.md).

# Restructure: how it is actually done

The [proposal](../architecture/proposed-repository-structure.md) says what the tree becomes.
This says how to get there, in commands, and what breaks on the way.

## Why this is cheaper than it looks

Every project in this repository is already self-contained. Checked rather than
assumed — the number of sibling paths (`../`) in each project's own
configuration:

| File | Sibling references |
|---|---|
| `cmp_backend/pyproject.toml` | 0 |
| `cmp_backend/alembic.ini` | 0 — `script_location = %(here)s/migrations` |
| `cmp_internal_ui/next.config.ts` | 0 |
| `cmp_internal_ui/playwright.config.ts` | 0 |
| `cmp_internal_ui/package.json` | 0 |
| `cmp_public_ui/next.config.ts` | 0 |
| `cmp_dkms/pyproject.toml` | 0 |

Ruff resolves `src`, TypeScript resolves `@/*` to `./src/*`, Alembic resolves
`%(here)s`. **Moving a whole project therefore breaks nothing inside it.** What
breaks is only what points *between* projects, and that is a short list.

## Everything that breaks, in full

Measured with `git grep`, not estimated.

### Seven files that break a build

| File | What it holds |
|---|---|
| `.github/workflows/ci.yml` | 9 paths: `working-directory`, two `cache-dependency-glob`, the coverage artefact, the `portal:` matrix, the Docker `context` and `file` |
| `api_docs/generate.py` | 6 paths: the OpenAPI source, `sys.path` for the permission matrix, three strings in the generated output |
| `docs/scripts/personal_data_scan.py` | `ROOT = parents[2]` and three paths under it |
| `cmp_backend/tests/unit/infrastructure/test_dkms_field_map.py` | `parents[3].parent / "cmp_dkms/app/dkms/types.py"` |
| `cmp_internal_ui/e2e/support/outbox.ts` | `../../../backend/api/var/outbox.log` |
| `cmp_internal_ui/e2e/notice-upload.spec.ts` | the same, spelled as path segments |
| `cmp_public_ui/e2e/support/outbox.ts` and `e2e/rights.spec.ts` | the same two |

That is the whole build-breaking surface of phase 1. Seven files.

### Documentation, which is mechanical but not nothing

| Kind | Count |
|---|---|
| Markdown files mentioning `cmp_backend` | 63 |
| Links in `docs/` pointing at a folder that moves | 23 |
| Outward links inside `cmp_backend/docs/` whose depth changes | 16 |

The 16 are the fiddly ones: a file moving from
`cmp_backend/docs/architecture/` to `docs/architecture/` goes from
`../domain/x.md` to `../domain/x.md`. Three levels become one.

### Two comments, cosmetic

`cmp_dkms/pyproject.toml` and `cmp_backend/src/cmp/infrastructure/dkms/*.py`
mention sibling folders in prose. They are wrong the moment the folders move,
and nothing fails.

## Before anything moves

```bash
git switch -c restructure/phase-1
cd cmp_backend && uv run pytest -q && cd ..
cd cmp_internal_ui && npm run verify && cd ..
cd cmp_public_ui && npm run verify && cd ..
cd cmp_dkms && .venv/bin/python -m pytest -q && cd ..
```

Green on all four, recorded, before the first `git mv`. A restructure that
starts on a red suite cannot tell you which failure it caused.

## Phase 1 — the four moves

### The commands

```bash
mkdir -p backend frontend

git mv cmp_backend      backend/api
git mv cmp_dkms         backend/dkms
git mv cmp_internal_ui  frontend/console
git mv cmp_public_ui    frontend/portal

git commit -m "refactor: the four services move under backend/ and frontend/"
```

Four commands. `git mv` stages the rename; because the content is byte-identical
Git records it as a rename and `git log --follow` keeps working on every file.

One caveat worth knowing before you panic at the diff: Git does not store
renames, it *detects* them. A `git show --stat` on that commit may print
hundreds of lines until the rename detection limit is raised. `git show -M
--find-renames=40%` shows what actually happened, and
`git config diff.renameLimit 4000` makes it the default for this repository.

### Then the seven files

Nothing here is a search-and-replace across the tree; each is a specific edit.

```bash
# 1. CI — 9 paths
#    working-directory: cmp_backend            -> backend/api
#    cache-dependency-glob: cmp_backend/uv.lock -> backend/api/uv.lock   (x2)
#    path: cmp_backend/coverage.xml            -> backend/api/coverage.xml
#    portal: [cmp_internal_ui, cmp_public_ui]  -> [console, portal]  + working-directory
#    context: cmp_backend                      -> backend/api
#    file: cmp_backend/docker/Dockerfile       -> backend/api/docker/Dockerfile

# 2. the api-docs generator
sed -i '' 's|"cmp_backend"|"backend" / "api"|; s|cd cmp_backend|cd backend/api|' \
  api_docs/generate.py     # then read it: three of the six are prose in the output

# 3. the personal-data scanner — ROOT is parents[2] today and stays parents[2],
#    but the three paths under it change
sed -i '' 's|cmp_backend/openapi.json|backend/api/openapi.json|; \
           s|database_schema/schema_inventory.json|docs/reference/database/schema_inventory.json|' \
  docs/scripts/personal_data_scan.py

# 4. the DKMS field-map test — parents[3].parent stops being right
#    "cmp_dkms/app/dkms/types.py" -> ROOT / "backend/dkms/app/dkms/types.py"

# 5-7. the outbox path in four e2e files
#      ../../../backend/api/var/outbox.log -> ../../../../backend/api/var/outbox.log
#      (one level deeper, because console/ and portal/ now sit inside frontend/)
```

### Verify

```bash
cd backend/api        && uv run pytest -q
cd ../dkms            && .venv/bin/python -m pytest -q
cd ../../frontend/console && npm run verify && E2E_API_URL=http://127.0.0.1:8000 npm run e2e
cd ../portal          && npm run verify
```

Four suites, the same numbers as the baseline. The e2e run matters because the
outbox path is the one thing a unit test cannot catch.

### The one thing I cannot do for you

`.github/workflows/ci.yml` cannot be pushed from this environment — the
credential lacks the `workflow` OAuth scope, and a push containing a workflow
edit is rejected whole. Either apply that file's nine path changes yourself, or
grant the scope. It is nine lines, and CI is red until they are made.

## Phase 2 — all documentation into `docs/`

### The moves

```bash
# the backend's own 17 documents
git mv backend/api/docs/architecture/layers.md            docs/architecture/
git mv backend/api/docs/architecture/dependency-rules.md  docs/architecture/
git mv backend/api/docs/architecture/request-lifecycle.md docs/architecture/
git mv backend/api/docs/architecture/rights.md            docs/architecture/
git mv backend/api/docs/architecture/overview.md          docs/architecture/api-internals.md
git mv backend/api/docs/security                          docs/security
git mv backend/api/docs/database                          docs/database
git mv backend/api/docs/operations/configuration.md       docs/operations/
git mv backend/api/docs/operations/monitoring.md          docs/operations/
git mv backend/api/docs/operations/deployment.md          docs/operations/api-deployment.md
rmdir -p backend/api/docs/{architecture,operations} backend/api/docs 2>/dev/null

# the three reference trees
mkdir -p docs/reference
git mv api_docs            docs/reference/api
git mv database_schema     docs/reference/database
git mv api_access_control  docs/reference/access-control

# the generators
mkdir -p docs/tools
git mv docs/reference/api/generate.py   docs/tools/generate-api-docs.py
git mv docs/scripts/personal_data_scan.py docs/tools/personal-data-scan.py
rmdir docs/scripts
```

Two renames are deliberate, not tidying: `overview.md` and `deployment.md`
already exist under `docs/`, describing the whole system. The backend's are
about the API alone, so they arrive as `api-internals.md` and
`api-deployment.md` rather than overwriting.

### Then the links

The depth changes, so the rewrite is per-source-directory rather than global:

```bash
# files that moved from cmp_backend/docs/*/ to docs/*/ : three levels become one
sed -i '' 's|\.\./\.\./\.\./docs/|../|g' docs/architecture/*.md docs/security/*.md docs/database/*.md

# files already in docs/ that pointed at a moved folder
sed -i '' 's|\.\./cmp_backend/|../backend/api/|g; \
           s|\.\./cmp_internal_ui/|../frontend/console/|g; \
           s|\.\./cmp_public_ui/|../frontend/portal/|g; \
           s|\.\./cmp_dkms/|../backend/dkms/|g; \
           s|\.\./api_docs/|reference/api/|g; \
           s|\.\./database_schema/|reference/database/|g; \
           s|\.\./api_access_control/|reference/access-control/|g' docs/*.md docs/*/*.md
```

### Verify, with a check rather than by reading

```bash
python3 - <<'EOF'
import re, pathlib
bad = []
for md in pathlib.Path(".").rglob("*.md"):
    if any(p in md.parts for p in ("node_modules", ".venv", ".next")):
        continue
    for text, target in re.findall(r"\[([^\]]+)\]\(([^)]+)\)", md.read_text()):
        if target.startswith(("http", "#", "mailto:")):
            continue
        if not (md.parent / target.split("#")[0]).exists():
            bad.append(f"{md}: [{text}]({target})")
print("\n".join(bad) if bad else "every relative link resolves")
EOF
```

**Put that script in `docs/tools/check-links.py` and run it in CI.** Two
hundred documents cross-referencing each other need a check, not a convention —
and the same script proves phase 2 landed.

Then regenerate what the generators produce, and confirm the output is
byte-identical apart from the paths quoted inside it:

```bash
python3 docs/tools/generate-api-docs.py
python3 docs/tools/personal-data-scan.py --check
git diff --stat docs/reference/
```

## Phase 3 — the 65 duplicated files become one copy

This is the phase with actual engineering in it. The three before and after it
are moves; this one changes how the two apps build.

### The workspace

```jsonc
// frontend/package.json                                            new file
{
  "name": "compass-frontend",
  "private": true,
  "workspaces": ["console", "portal", "shared/*"]
}
```

Each shared folder becomes a workspace package with a three-line
`package.json`:

```jsonc
// frontend/shared/ui/package.json
{ "name": "@compass/ui", "version": "0.0.0", "private": true, "main": "src/index.ts" }
```

No build step, and **no `transpilePackages` entry either**: Next 16 transpiles
workspace packages automatically — Turbopack under both routers, webpack under
the App Router, which is the one both portals use. The source is imported
directly and there is no `dist/` to keep in step. (`transpilePackages` is for a
`node_modules` dependency shipping raw TypeScript, which this is not. Checked
against `next/dist/docs`, not from memory: this version's behaviour differs from
the one most guides describe.)

### Moving the files

One package at a time, each its own commit, in dependency order — `api-types`
first because everything imports it, `ui` next, `core` after, `dkms-client`
last. For each:

```bash
git mv frontend/console/src/types frontend/shared/api-types/src
git rm -r frontend/portal/src/types          # the identical copy
```

Then point both apps at it. The imports are already `@/types`, so the change is
one line per app rather than a hundred:

```jsonc
// frontend/console/tsconfig.json
"paths": {
  "@/*":      ["./src/*"],
  "@/types":  ["../shared/api-types/src"],       // and the same for the others
}
```

That alias is a deliberate intermediate step: it means **no import statement in
either app changes during the move**, so the diff is the files moving and
nothing else. Rewriting `@/types` to `@compass/api-types` across both apps is a
later, purely mechanical commit — or never, if the alias reads fine.

### The order that keeps it reviewable

| Commit | Moves | Files |
|---|---|---|
| 1 | `api-types` | 18 |
| 2 | `ui` — primitives, charts, dialog, status, graphics, styles | ~12 |
| 3 | `core` — providers, lib, schemas, test, proxy | ~25 |
| 4 | `dkms-client` | 4 |
| 5 | delete the portal's now-unreferenced copies | — |

After each, both suites run. A package that breaks one app is caught in the
commit that moved it, not three commits later.

### The route handler

`route.ts` must live inside `app/`, so it cannot move. The package exports the
handler and each app keeps three lines:

```ts
// frontend/console/src/app/dkms/decrypt/route.ts
import { createDecryptHandler } from "@compass/dkms-client/route-handler";
export const POST = createDecryptHandler();
```

## Phase 4 — the 37 near-duplicates

Not mechanical, and not automatable. For each file that exists in both apps
with different content:

```bash
diff frontend/console/src/lib/config/index.ts frontend/portal/src/lib/config/index.ts
```

and for every difference, one of three answers:

- **Drift.** Take the better version into `shared/`.
- **A real difference.** Move the file to `shared/`, take the differing value as
  a parameter, and have each app supply it in `src/app-config.ts`.
- **Genuinely one app's.** It stays where it is, and stops pretending to be
  shared by having the same path.

The candidates, in the order I would take them: `lib/config/index.ts`,
`providers/auth-provider.tsx`, `components/layout/app-shell.tsx`,
`components/security/require-section.tsx`, `components/ui/status.tsx`,
`test/fixtures.ts`, `app/page.tsx`, `app/sign-in/page.tsx`.

Do the small ones first. By the fourth you will know what `app-config.ts` needs
to hold, which is not knowable from the outside beforehand.

## Phase 5 — one Python toolchain

`backend/api` uses `uv` with a lockfile; `backend/dkms` uses `venv` + `pip`.
Converting the API to pip:

```bash
cd backend/api
uv export --no-hashes --no-dev > requirements.txt
uv export --no-hashes --only-dev > requirements-dev.txt
# then: pyproject.toml keeps the tool configuration, loses [project.dependencies]
# and CI's `uv sync` becomes `pip install -r requirements.txt`
```

The lockfile's exact resolution is preserved, which is the part that matters.
Going the other way — `uv` for both — is `uv add` from `requirements.txt` and
is equally fine. What is not fine is leaving both.

## If it goes wrong

Phases 1 and 2 are renames. To undo, `git revert` the commit; the files return
with their history intact, because Git never lost it.

Phase 3 is the only phase where a revert is inconvenient, because the app
configuration changed alongside the moves. Keep it on its own branch until both
suites and both e2e runs are green, and merge it as one unit.

## What "done" looks like

```bash
ls                              # backend  docs  frontend  .github  README.md …
git grep -l "cmp_backend"       # nothing outside docs/history/
git grep -l "useToast" frontend # one file
python3 docs/tools/check-links.py
```

Four entries at the root, one copy of every shared file, and every link
resolving.
