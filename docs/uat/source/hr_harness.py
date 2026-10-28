"""The HR track UAT run's harness (see run_hr_track.py): a tester's hands on the live local API: sign in as a seeded account, read
the code the dev popup would show, call the routes the console calls."""

from __future__ import annotations

import time
import uuid
from typing import Any

import httpx

API = "http://127.0.0.1:8000"
SEED_PASSWORD = "SeedPassw0rd!2026"
UAT_PASSWORD = "UatPassw0rd!2026-hr"


class Session:
    def __init__(self, name: str) -> None:
        self.name = name
        self.client_id = uuid.uuid4().hex
        self.http = httpx.Client(
            base_url=API, headers={"X-CMP-Dev-Client": self.client_id}, timeout=60
        )

    def _headers(self, method: str) -> dict[str, str]:
        if method.upper() == "GET":
            return {}
        token = self.http.cookies.get("cmp_csrf") or ""
        return {"X-CSRF-Token": token}

    def call(self, method: str, path: str, **kw: Any) -> httpx.Response:
        headers = {**self._headers(method), **kw.pop("headers", {})}
        return self.http.request(method, path, headers=headers, **kw)

    def get(self, path: str, **kw: Any) -> httpx.Response:
        return self.call("GET", path, **kw)

    def post(self, path: str, **kw: Any) -> httpx.Response:
        return self.call("POST", path, **kw)

    def codes(self) -> list[dict[str, Any]]:
        r = self.http.get("/dev/codes")
        r.raise_for_status()
        return r.json().get("items", [])

    def wait_code(self, seen: set[str] | None = None, timeout: float = 30) -> str:
        seen = seen or set()
        end = time.time() + timeout
        while time.time() < end:
            for c in self.codes():
                code = str(c.get("code") or "")
                if code and code not in seen:
                    return code
            time.sleep(0.5)
        raise RuntimeError(f"{self.name}: no code arrived")

    def seen(self) -> set[str]:
        return {str(c.get("code")) for c in self.codes()}


def staff(name: str, login: str, password: str = SEED_PASSWORD) -> Session:
    s = Session(name)
    before = s.seen()
    r = s.post("/auth/login", json={"login": login, "password": password})
    if r.status_code != 200:
        raise RuntimeError(f"{name}: login {r.status_code} {r.text[:200]}")
    if r.json().get("mfa_required"):
        code = s.wait_code(before)
        v = s.post("/auth/mfa/verify", json={"code": code})
        if v.status_code != 200:
            raise RuntimeError(f"{name}: mfa {v.status_code} {v.text[:200]}")
    return s


def reset_password(email: str, password: str = UAT_PASSWORD) -> None:
    s = Session(f"reset {email}")
    before = s.seen()
    s.post("/auth/password/reset/request", json={"email": email}).raise_for_status()
    code = s.wait_code(before)
    r = s.post(
        "/auth/password/reset/confirm",
        json={"email": email, "code": code, "new_password": password},
    )
    if r.status_code != 200:
        raise RuntimeError(f"reset {email}: {r.status_code} {r.text[:200]}")


RESULTS: list[tuple[str, str, str]] = []


def record(case: str, result: str, note: str) -> None:
    RESULTS.append((case, result, note))
    print(f"{case:7} {result:8} {note}")
