# History

Documents that described the platform at a moment, kept because they explain
why it has the shape it has. None of them is current, and none should be
edited to become current; the live documentation is under
[docs/](../README.md).

| Document | Written | What it was | What has changed since |
|---|---|---|---|
| [COMPASS-LLD.md](COMPASS-LLD.md) | August 2026 | A low-level design read out of the running application: routes, gates, tables, paths. Its header says it is generated; the generator was not kept in the repository. | 164 routes then, 233 now; one frontend then, two portals now; no rights module, no delegation, no respondents; migrations stopped at 0012. |
| [BACKEND-STRUCTURE.md](BACKEND-STRUCTURE.md) | August 2026 | A proposal for a module-oriented backend layout, measured against fifteen architecture rules. | The layered layout in `src/cmp/` is what was built; the proposal was not applied as written. Its rules survive in [layers.md](../../cmp_backend/docs/architecture/layers.md). |
| [FRONTEND-GAP-ANALYSIS.md](FRONTEND-GAP-ANALYSIS.md) | August 2026 | A measured gap analysis of the single Next.js application against the API and the Act. | The frontend was split into the console and the portal, and most gaps it lists were closed; the method in its §6 is still a good way to measure coverage. |

For the current picture, start at
[system-overview.md](../architecture/system-overview.md).
