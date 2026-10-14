# Deployment

How COMPASS CMP is put on real infrastructure. Local setup is in
[operations/local-development.md](../operations/local-development.md).
Everything runs as plain processes on servers, with no Docker
([ADR 0018](../decisions/0018-pip-and-a-virtualenv-no-containers.md)).

| Document | Covers | Status |
|---|---|---|
| [portal-frontend-aws.md](portal-frontend-aws.md) | The data-principal portal (`frontend/portal`) on AWS: what it needs when it runs, the AWS services, the architecture, build-time vs start-time settings, the end-to-end process from network to first release, pipeline files, monitoring, rollback, and what must be fixed before go-live. The staff console's differences are in its section 13 | Proposal, 2026-10-14 |

Not written yet: the API and its worker, the key service (DKMS), PostgreSQL
and Redis on AWS. The portal document lists what it needs from each of them.
