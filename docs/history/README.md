# History

Documents that described the platform at a moment, kept because they explain
why it has the shape it has. None of them is current, and none should be
edited to become current; the live documentation is under
[docs/](../README.md).

| Document | Written | What it was | What has changed since |
|---|---|---|---|
| [COMPASS-LLD.md](COMPASS-LLD.md) | August 2026 | A low-level design read out of the running application: routes, gates, tables, paths. Its header says it is generated; the generator was not kept in the repository. | 164 routes then, 233 now; one frontend then, two portals now; no rights module, no delegation, no respondents; migrations stopped at 0012. |
| [BACKEND-STRUCTURE.md](BACKEND-STRUCTURE.md) | August 2026 | A proposal for a module-oriented backend layout, measured against fifteen architecture rules. | The layered layout in `src/cmp/` is what was built; the proposal was not applied as written. Its rules survive in [layers.md](../architecture/layers.md). |
| [deployment-with-containers.md](deployment-with-containers.md) | September 2026 | How the whole platform was to run as containers: the images, the compose stack, nginx in front, the order of operations. | The images, the compose stack and the proxy were removed on 21 September 2026. Every service is a process in a virtualenv or under `npm run dev`; the one Docker file left starts PostgreSQL and Redis. |
| [api-deployment-with-containers.md](api-deployment-with-containers.md) | September 2026 | The API's own processes, health endpoints and gunicorn configuration inside its image. | The same. The health endpoints and the queue layout it describes are unchanged and live in the code. |
| [restructure-runbook.md](restructure-runbook.md) | September 2026 | The commands for moving the repository to `backend/`, `frontend/` and `docs/`, and everything each move would break, measured with `git grep`. | Phases 1, 2 and 5 were done on 21 September 2026 in `89b1e8e`, `209e1da` and `879bfc1`; its paths are the old ones. Phases 3 and 4, the shared frontend package, are still open in the [proposal](../architecture/proposed-repository-structure.md). |
| [FRONTEND-GAP-ANALYSIS.md](FRONTEND-GAP-ANALYSIS.md) | August 2026 | A measured gap analysis of the single Next.js application against the API and the Act. | The frontend was split into the console and the portal, and most gaps it lists were closed; the method in its §6 is still a good way to measure coverage. |

For the current picture, start at
[system-overview.md](../architecture/system-overview.md).
