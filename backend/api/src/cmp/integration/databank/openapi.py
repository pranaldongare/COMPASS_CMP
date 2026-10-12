"""The six calls as one OpenAPI document - the draft specification the brief's
next steps ask for, generated from the same models the stub runs on.

    python -m cmp.integration.databank.openapi > docs/integration/databank/openapi.json
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute

from cmp.api.routers.integration import databank_router
from cmp.integration.databank.contracts import PREFIX
from cmp.integration.databank.mock_server import MockDatabank, create_app

DESCRIPTION = """\
The COMPASS CMP <-> Databank integration, version 1 - a draft for both teams
to settle. CMP hosts calls 1, 2 and 6; Databank hosts calls 3, 4 and 5. JSON
over HTTPS inside the organisation network, a service identity in each
direction (a bearer token in the stub), every event and instruction carrying
its own ID so a repeat changes nothing.
"""


def build() -> dict[str, Any]:
    app = FastAPI(title="COMPASS CMP <-> Databank", version="1.0.0-draft", description=DESCRIPTION)
    app.include_router(databank_router)
    mock = create_app(MockDatabank(cmp_url="http://cmp", token="-"))  # noqa: S106 - unused
    for route in mock.routes:
        if isinstance(route, APIRoute) and route.path.startswith(PREFIX):
            route.tags = ["hosted by Databank"]
            app.router.routes.append(route)
    spec = app.openapi()
    for operations in spec["paths"].values():
        for operation in operations.values():
            if operation.get("tags") != ["hosted by Databank"]:
                operation["tags"] = ["hosted by CMP"]
    # Keep the six calls in their numbered order.
    spec["paths"] = dict(
        sorted(spec["paths"].items(), key=lambda kv: next(iter(kv[1].values()))["summary"])
    )
    return spec


def main() -> None:  # pragma: no cover - a command line
    print(json.dumps(build(), indent=2))  # noqa: T201 - a CLI


if __name__ == "__main__":  # pragma: no cover
    main()
