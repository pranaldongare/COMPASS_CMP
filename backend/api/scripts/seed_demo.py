"""Demo data through the API: ten and more of everything, made the way people make it.

`seed.py` lays down the administrator and the starting configuration directly.
This script builds on it the way a deployment fills up: every row below is
written by an endpoint, as the person whose job it is, so the permission
matrix, the sealing of personal fields, the audit trail and every business
rule apply exactly as they do in the console and the portal.

What it makes, each through its own endpoint and actor:

* **staff** - 12 accounts the administrator invites (2 DPOs, 2 DCO Admins,
  3 DCOs, 2 RCOs, 3 R&D users). Each invitation's code sets the password, as
  the invited person would, so all of them can sign in afterwards;
* **processors** (10, the DPO) and **data sources** (10, the DCO or RCO
  who runs them, owners set by the DCO Admin or the DPO);
* **purposes** (10, the DPO, activated);
* **projects** (10, the R&D users) with a notice each (the DPO), an approval
  proof, and the submission; the DPO approves eight, one waits for approval
  and one stays a draft;
* **collection sites** (10) and a **consent link** on each (10);
* **data principals** (12) who open a link, register, prove both contacts and
  decide - most consent to everything, some to part, one declines - and
  **consents** (12), two of them later withdrawn in part or in full;
* **exports** and **imports** by the people who run each site, with the
  collections and assets the manifests describe;
* **rights requests** (12) the principals make from the portal, half of them
  acknowledged by the DPO; two **nominations** and two **cover arrangements**.

The application runs in-process, against the database the settings name, so
no server needs to be up. One-time codes are read off the messages as they are
handed to the task queue, the way the person would read them off a phone;
those messages are not sent. Run `seed.py` first.

Runs once per database: it stops before writing anything if any of its people
or organisations already exist. To start again, rebuild the database
(`scripts/reset_dev.py`), then `seed.py`, then this.

Refuses to run outside local/test.

    python scripts/seed_demo.py
    POSTGRES_DB=cmp_http python scripts/seed_demo.py   # into a scratch database
"""

from __future__ import annotations

import asyncio
import sys
import warnings
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from seed import ADMIN, PASSWORD

from cmp.core.config import settings
from cmp.core.logging import configure_logging, get_logger
from cmp.db.pool import close_pool, open_pool
from cmp.db.redis import K_RATE, close_redis, open_redis

log = get_logger("cmp.seed_demo")

# The per-request cookies below are how each actor keeps its own session on one
# client; httpx warns that the style is deprecated, and it is still the plain
# way to do exactly this.
warnings.filterwarnings("ignore", message=".*per-request cookies.*")

TODAY = datetime.now(UTC).date()

# =============================================================================
#  Staff - invited by the administrator; every one signs in with PASSWORD
# =============================================================================

STAFF: list[dict[str, str]] = [
    {
        "key": "dpo1",
        "full_name": "Kavitha Raman",
        "email": "kavitha.raman@cmp.local",
        "role": "dpo",
        "org": "EMP-1101",
    },
    {
        "key": "dpo2",
        "full_name": "Farhan Qureshi",
        "email": "farhan.qureshi@cmp.local",
        "role": "dpo",
        "org": "EMP-1102",
    },
    {
        "key": "dcoa1",
        "full_name": "Rohit Kulkarni",
        "email": "rohit.kulkarni@cmp.local",
        "role": "dco_admin",
        "org": "EMP-1201",
    },
    {
        "key": "dcoa2",
        "full_name": "Sneha Pillai",
        "email": "sneha.pillai@cmp.local",
        "role": "dco_admin",
        "org": "EMP-1202",
    },
    {
        "key": "dco1",
        "full_name": "Vikram Joshi",
        "email": "vikram.joshi@cmp.local",
        "role": "dco",
        "org": "EMP-1301",
    },
    {
        "key": "dco2",
        "full_name": "Lakshmi Iyer",
        "email": "lakshmi.iyer@cmp.local",
        "role": "dco",
        "org": "EMP-1302",
    },
    {
        "key": "dco3",
        "full_name": "Imran Sheikh",
        "email": "imran.sheikh@cmp.local",
        "role": "dco",
        "org": "EMP-1303",
    },
    {
        "key": "rco1",
        "full_name": "Deepa Menon",
        "email": "deepa.menon@cmp.local",
        "role": "rco",
        "org": "EMP-1401",
    },
    {
        "key": "rco2",
        "full_name": "Arjun Reddy",
        "email": "arjun.reddy@cmp.local",
        "role": "rco",
        "org": "EMP-1402",
    },
    {
        "key": "rnd1",
        "full_name": "Neha Gupta",
        "email": "neha.gupta@cmp.local",
        "role": "rnd_user",
        "org": "EMP-1501",
    },
    {
        "key": "rnd2",
        "full_name": "Siddharth Rao",
        "email": "siddharth.rao@cmp.local",
        "role": "rnd_user",
        "org": "EMP-1502",
    },
    {
        "key": "rnd3",
        "full_name": "Pooja Bhat",
        "email": "pooja.bhat@cmp.local",
        "role": "rnd_user",
        "org": "EMP-1503",
    },
]

# =============================================================================
#  Processors and their sources
# =============================================================================
#
# `owner` is the staff key of the collection owner who runs the source: a DCO
# for a third party, an RCO for an in-house team. A processor abroad is named
# by its country, and only a purpose that permits cross-border transfer may be
# exported to it (S2-04).

PROCESSORS: list[dict[str, Any]] = [
    {
        "key": "bvl",
        "legal_name": "Bengaluru Vision Labs Pvt Ltd",
        "type": "lab",
        "contract_ref": "CTR-2026-0201",
        "is_in_house": False,
        "location_country": "IN",
        "source": {
            "source_code": "SRC-BVL-KOR",
            "name": "Koramangala studio",
            "owner": "dco1",
            "authoritative": ["facial_image"],
        },
    },
    {
        "key": "aic",
        "legal_name": "Ahmedabad Imaging Centre LLP",
        "type": "lab",
        "contract_ref": "CTR-2026-0202",
        "is_in_house": False,
        "location_country": "IN",
        "source": {
            "source_code": "SRC-AIC-NAV",
            "name": "Navrangpura imaging room",
            "owner": "dco2",
            "authoritative": ["facial_image"],
        },
    },
    {
        "key": "dst",
        "legal_name": "Delhi Speech Technologies Pvt Ltd",
        "type": "tool",
        "contract_ref": "CTR-2026-0203",
        "is_in_house": False,
        "location_country": "IN",
        "source": {
            "source_code": "SRC-DST-SAK",
            "name": "Saket recording booth",
            "owner": "dco1",
            "authoritative": ["voice_recording"],
        },
    },
    {
        "key": "mmc",
        "legal_name": "Mumbai Motion Capture Studio",
        "type": "lab",
        "contract_ref": "CTR-2026-0204",
        "is_in_house": False,
        "location_country": "IN",
        "source": {
            "source_code": "SRC-MMC-AND",
            "name": "Andheri capture floor",
            "owner": "dco3",
            "authoritative": ["gait_video"],
        },
    },
    {
        "key": "cbr",
        "legal_name": "Chennai Biometrics Research LLP",
        "type": "lab",
        "contract_ref": "CTR-2026-0205",
        "is_in_house": False,
        "location_country": "IN",
        "source": {
            "source_code": "SRC-CBR-GUI",
            "name": "Guindy sensor lab",
            "owner": "dco2",
            "authoritative": ["fingerprint"],
        },
    },
    {
        "key": "hdc",
        "legal_name": "Hyderabad Data Collection Services",
        "type": "other",
        "contract_ref": "CTR-2026-0206",
        "is_in_house": False,
        "location_country": "IN",
        "source": {
            "source_code": "SRC-HDC-HIT",
            "name": "HITEC City field team",
            "owner": "dco3",
            "authoritative": ["health_data", "sensor_reading"],
        },
    },
    {
        "key": "kfr",
        "legal_name": "Kolkata Field Research Associates",
        "type": "other",
        "contract_ref": "CTR-2026-0207",
        "is_in_house": False,
        "location_country": "IN",
        "source": {
            "source_code": "SRC-KFR-SLT",
            "name": "Salt Lake campus team",
            "owner": "dco1",
            "authoritative": ["location"],
        },
    },
    {
        "key": "sap",
        "legal_name": "Singapore Annotation Partners Pte Ltd",
        "type": "other",
        "contract_ref": "CTR-2026-0208",
        "is_in_house": False,
        "location_country": "SG",
        "source": {
            "source_code": "SRC-SAP-ONE",
            "name": "One-North annotation desk",
            "owner": "dco2",
            "authoritative": ["facial_image", "voice_recording"],
        },
    },
    {
        "key": "aar",
        "legal_name": "Applied AI Research (in-house)",
        "type": "other",
        "contract_ref": "in-house - no processor contract",
        "is_in_house": True,
        "location_country": "IN",
        "source": {
            "source_code": "SRC-AAR-BLR",
            "name": "Driver-monitoring rig",
            "owner": "rco1",
            "authoritative": ["facial_image", "sensor_reading"],
        },
    },
    {
        "key": "sal",
        "legal_name": "Speech and Audio Lab (in-house)",
        "type": "lab",
        "contract_ref": "in-house - no processor contract",
        "is_in_house": True,
        "location_country": "IN",
        "source": {
            "source_code": "SRC-SAL-STU",
            "name": "Anechoic studio",
            "owner": "rco2",
            "authoritative": ["voice_recording"],
        },
    },
]

# =============================================================================
#  Purposes
# =============================================================================

PURPOSES: list[dict[str, Any]] = [
    {
        "purpose_code": "PUR-FACE-REC",
        "name": "Face recognition model training",
        "description": "Training and testing face-recognition models on consented images.",
        "uses": "Train, validate and benchmark models. No decisions are made about you.",
        "data_categories": ["facial_image", "name"],
        "retention_days": 1095,
        "erasure_trigger": "withdrawal",
    },
    {
        "purpose_code": "PUR-VOICE-ASR",
        "name": "Speech recognition training",
        "description": "Building speech-to-text models for Indian languages.",
        "uses": "Train and evaluate speech-recognition models.",
        "data_categories": ["voice_recording", "name"],
        "retention_days": 1095,
        "erasure_trigger": "withdrawal",
    },
    {
        "purpose_code": "PUR-GAIT-EVAL",
        "name": "Gait model evaluation",
        "description": "Measuring how well gait models identify people in the field.",
        "uses": "Evaluate existing models; recordings are not used to train new ones.",
        "data_categories": ["gait_video"],
        "retention_days": 730,
        "erasure_trigger": "purpose_served",
    },
    {
        "purpose_code": "PUR-FINGER-QA",
        "name": "Fingerprint sensor quality testing",
        "description": "Checking new fingerprint sensors against reference readings.",
        "uses": "Compare sensor readings; no identification is attempted.",
        "data_categories": ["fingerprint"],
        "retention_days": 365,
        "erasure_trigger": "purpose_served",
    },
    {
        "purpose_code": "PUR-HEALTH-WEAR",
        "name": "Wearable health signal research",
        "description": "Studying heart-rate signals from wrist-worn devices.",
        "uses": "Signal-processing research on anonymised windows.",
        "data_categories": ["health_data", "sensor_reading"],
        "retention_days": 730,
        "erasure_trigger": "withdrawal",
    },
    {
        "purpose_code": "PUR-APP-USAGE",
        "name": "Keyboard usage research",
        "description": "Understanding how people type on phone keyboards.",
        "uses": "Aggregate usage statistics for keyboard design.",
        "data_categories": ["usage_log", "device_identifier"],
        "retention_days": 365,
        "erasure_trigger": "period_elapsed",
    },
    {
        "purpose_code": "PUR-INDOOR-NAV",
        "name": "Indoor navigation research",
        "description": "Mapping how people move through large buildings.",
        "uses": "Build indoor positioning models.",
        "data_categories": ["location", "sensor_reading"],
        "retention_days": 365,
        "erasure_trigger": "withdrawal",
    },
    {
        "purpose_code": "PUR-ANNOTATE-XB",
        "name": "Offshore annotation of recordings",
        "description": "Labelling recordings by an annotation partner in Singapore.",
        "uses": "Human annotation of images and audio, outside India.",
        "data_categories": ["facial_image", "voice_recording"],
        "retention_days": 365,
        "erasure_trigger": "purpose_served",
        "cross_border_permitted": True,
    },
    {
        "purpose_code": "PUR-DRIVER-SAFE",
        "name": "Driver drowsiness detection",
        "description": "Detecting signs of drowsiness from in-cabin cameras.",
        "uses": "Train and test in-cabin safety models.",
        "data_categories": ["facial_image", "sensor_reading"],
        "retention_days": 1095,
        "erasure_trigger": "withdrawal",
    },
    {
        "purpose_code": "PUR-CONTACT",
        "name": "Study communications",
        "description": "Contacting you about the study you joined.",
        "uses": "Scheduling, reminders and results of the study.",
        "data_categories": ["name", "email", "mobile"],
        "retention_days": 365,
        "erasure_trigger": "purpose_served",
    },
]

# =============================================================================
#  Projects
# =============================================================================
#
# `owner` is the R&D user who registers it; `sites` are (processor key,
# location). `state` is where it ends: approved projects get sites and links.

PROJECTS: list[dict[str, Any]] = [
    {
        "key": "face",
        "project_name": "Face Recognition Benchmark 2026",
        "internal": "FACE-2026",
        "team": "Computer Vision",
        "owner": "rnd1",
        "purposes": ["PUR-FACE-REC", "PUR-CONTACT"],
        "sites": [("bvl", "Koramangala, Bengaluru"), ("aic", "Navrangpura, Ahmedabad")],
        "state": "approved",
    },
    {
        "key": "asr",
        "project_name": "Hindi Speech Corpus",
        "internal": "ASR-HI-2026",
        "team": "Speech",
        "owner": "rnd2",
        "purposes": ["PUR-VOICE-ASR", "PUR-CONTACT"],
        "sites": [("dst", "Saket, New Delhi"), ("sal", "Speech lab, Bengaluru")],
        "state": "approved",
    },
    {
        "key": "gait",
        "project_name": "Gait Recognition Field Trial",
        "internal": "GAIT-FT-2026",
        "team": "Computer Vision",
        "owner": "rnd1",
        "purposes": ["PUR-GAIT-EVAL"],
        "sites": [("mmc", "Andheri, Mumbai")],
        "state": "approved",
    },
    {
        "key": "finger",
        "project_name": "Fingerprint Sensor Validation",
        "internal": "FP-VAL-2026",
        "team": "Biometrics",
        "owner": "rnd3",
        "purposes": ["PUR-FINGER-QA"],
        "sites": [("cbr", "Guindy, Chennai")],
        "state": "approved",
    },
    {
        "key": "wear",
        "project_name": "Wearable Heart-Rate Study",
        "internal": "WEAR-HR-2026",
        "team": "Health",
        "owner": "rnd3",
        "purposes": ["PUR-HEALTH-WEAR", "PUR-CONTACT"],
        "sites": [("hdc", "HITEC City, Hyderabad")],
        "state": "approved",
    },
    {
        "key": "nav",
        "project_name": "Campus Indoor Navigation",
        "internal": "NAV-2026",
        "team": "Sensors",
        "owner": "rnd2",
        "purposes": ["PUR-INDOOR-NAV"],
        "sites": [("kfr", "Salt Lake, Kolkata")],
        "state": "approved",
    },
    {
        "key": "annot",
        "project_name": "Multilingual Annotation Programme",
        "internal": "ANNOT-XB-2026",
        "team": "Data Operations",
        "owner": "rnd2",
        "purposes": ["PUR-ANNOTATE-XB"],
        "sites": [("sap", "One-North, Singapore")],
        "state": "approved",
    },
    {
        "key": "drive",
        "project_name": "In-cabin Driver Monitoring",
        "internal": "DRIVE-2026",
        "team": "Automotive",
        "owner": "rnd1",
        "purposes": ["PUR-DRIVER-SAFE"],
        "sites": [("aar", "Automotive bay, Bengaluru")],
        "state": "approved",
    },
    {
        "key": "keys",
        "project_name": "Smart Keyboard Usage Study",
        "internal": "KEYS-2026",
        "team": "Input Methods",
        "owner": "rnd3",
        "purposes": ["PUR-APP-USAGE"],
        "sites": [("hdc", "HITEC City, Hyderabad")],
        "state": "pending_approval",
    },
    {
        "key": "foot",
        "project_name": "Retail Footfall Pilot",
        "internal": "FOOT-2026",
        "team": "Computer Vision",
        "owner": "rnd1",
        "purposes": ["PUR-GAIT-EVAL"],
        "sites": [("bvl", "Indiranagar, Bengaluru")],
        "state": "in_draft",
    },
]

# =============================================================================
#  Data principals - they arrive through a site's consent link
# =============================================================================
#
# `site` is (project key, site index). `decision`: "all", "decline", or the
# list of purpose codes refused. `later`: "withdraw_one" (the first purpose
# still granted) or "withdraw_all". `request`: (type, text), made from the
# portal; `acknowledge` has the DPO pick it up.

PRINCIPALS: list[dict[str, Any]] = [
    {
        "full_name": "Aarav Sharma",
        "mobile": "+919003000101",
        "email": "aarav.sharma@example.org",
        "dob": "1994-03-12",
        "site": ("face", 0),
        "decision": "all",
        "request": ("access", "Please send me a summary of the images you hold of me."),
        "acknowledge": True,
    },
    {
        "full_name": "Ishita Banerjee",
        "mobile": "+919003000102",
        "email": "ishita.banerjee@example.org",
        "dob": "1990-11-02",
        "site": ("face", 1),
        "decision": ["PUR-CONTACT"],
        "request": (
            "correction",
            "My surname is spelt Banerjee, not Banerji, in the study letter.",
        ),
        "acknowledge": True,
    },
    {
        "full_name": "Rahul Nair",
        "mobile": "+919003000103",
        "email": "rahul.nair@example.org",
        "dob": "1988-07-21",
        "site": ("asr", 0),
        "decision": "all",
        "later": "withdraw_one",
        "request": ("erasure", "Please erase my voice recordings from the speech corpus."),
        "acknowledge": True,
    },
    {
        "full_name": "Meenakshi Sundaram",
        "mobile": "+919003000104",
        "email": "meenakshi.s@example.org",
        "dob": "1979-01-30",
        "site": ("asr", 1),
        "decision": "all",
        "request": ("access", "Who have you shared my recordings with?"),
        "acknowledge": False,
    },
    {
        "full_name": "Karan Malhotra",
        "mobile": "+919003000105",
        "email": "karan.malhotra@example.org",
        "dob": "1996-09-05",
        "site": ("gait", 0),
        "decision": "all",
        "request": ("access", "Everything you hold about me, please."),
        "acknowledge": True,
    },
    {
        "full_name": "Divya Krishnan",
        "mobile": "+919003000106",
        "email": "divya.krishnan@example.org",
        "dob": "1992-04-18",
        "site": ("finger", 0),
        "decision": "all",
        "later": "withdraw_all",
        "request": ("erasure", "I withdrew; please also delete my fingerprint readings."),
        "acknowledge": False,
    },
    {
        "full_name": "Sameer Patil",
        "mobile": "+919003000107",
        "email": "sameer.patil@example.org",
        "dob": "1985-12-09",
        "site": ("wear", 0),
        "decision": ["PUR-CONTACT"],
        "request": ("correction", "My date of birth on file is wrong."),
        "acknowledge": True,
    },
    {
        "full_name": "Ananya Das",
        "mobile": "+919003000108",
        "email": "ananya.das@example.org",
        "dob": "1998-06-25",
        "site": ("nav", 0),
        "decision": "all",
        "request": ("access", "A copy of the location data from the campus study."),
        "acknowledge": False,
    },
    {
        "full_name": "Joseph Mathew",
        "mobile": "+919003000109",
        "email": "joseph.mathew@example.org",
        "dob": "1983-02-14",
        "site": ("annot", 0),
        "decision": "all",
        "request": ("access", "Which company outside India received my recordings?"),
        "acknowledge": True,
    },
    {
        "full_name": "Harpreet Kaur",
        "mobile": "+919003000110",
        "email": "harpreet.kaur@example.org",
        "dob": "1991-08-08",
        "site": ("drive", 0),
        "decision": "all",
        "request": ("grievance", "My access request has had no reply for three weeks."),
        "acknowledge": False,
    },
    {
        "full_name": "Nikhil Verma",
        "mobile": "+919003000111",
        "email": "nikhil.verma@example.org",
        "dob": "1987-10-27",
        "site": ("face", 0),
        "decision": "decline",
        "request": ("access", "Confirm you hold nothing about me after I declined."),
        "acknowledge": False,
    },
    {
        "full_name": "Fatima Siddiqui",
        "mobile": "+919003000112",
        "email": "fatima.siddiqui@example.org",
        "dob": "1995-05-03",
        "site": ("gait", 0),
        "decision": "all",
        "request": ("correction", "Please update my email address on the study record."),
        "acknowledge": False,
    },
]

#: Principals who name someone to act for them (s.14): (principal index, nominee).
NOMINATIONS: list[tuple[int, dict[str, Any]]] = [
    (
        0,
        {
            "nominee_name": "Priyanka Sharma",
            "nominee_mobile": "+919003000201",
            "rights": ["access", "correction", "erasure"],
        },
    ),
    (
        4,
        {
            "nominee_name": "Rajesh Malhotra",
            "nominee_mobile": "+919003000202",
            "rights": ["access", "erasure"],
        },
    ),
]

#: Cover while somebody is away: (delegator key, delegate key, reason).
COVER: list[tuple[str, str, str]] = [
    ("dco1", "dco2", "Annual leave"),
    ("dpo1", "dpo2", "Conference travel"),
]

# =============================================================================
#  The machinery: one in-process client, an actor per session
# =============================================================================

MFA_CODE = "cmp.notifications.send_mfa_code"
INVITATION = "cmp.notifications.send_staff_invitation"
CONSENT_CODE = "cmp.notifications.send_consent_code"


class SeedError(RuntimeError):
    pass


class AlreadySeeded(SeedError):
    """Found before anything was written."""


@dataclass
class Actor:
    """Somebody signed in: the cookies of their session, and the CSRF header."""

    name: str
    cookies: dict[str, str] = field(default_factory=dict)
    uuid: str = ""

    @property
    def headers(self) -> dict[str, str]:
        return {settings.csrf_header_name: self.cookies.get(settings.csrf_cookie_name, "")}


class Api:
    def __init__(self, client: httpx.AsyncClient, sent: list[tuple[str, tuple[Any, ...]]]) -> None:
        self.client = client
        self.sent = sent
        self.counts: Counter[str] = Counter()

    async def call(
        self,
        method: str,
        path: str,
        *,
        actor: Actor | None = None,
        expect: tuple[int, ...] = (200, 201, 204),
        **kwargs: Any,
    ) -> httpx.Response:
        if actor is not None:
            kwargs["cookies"] = {**actor.cookies, **kwargs.get("cookies", {})}
            kwargs["headers"] = {**actor.headers, **kwargs.get("headers", {})}
        response = await self.client.request(method, path, **kwargs)
        if response.status_code not in expect:
            who = f" as {actor.name}" if actor else ""
            raise SeedError(
                f"{method} {path}{who} -> {response.status_code}: {response.text[:600]}"
            )
        return response

    def code(self, task: str, position: int) -> str:
        """The code in the latest message of this kind, where the person would read it."""
        for name, args in reversed(self.sent):
            if name == task:
                return str(args[position])
        raise SeedError(f"no {task} was sent")


async def sign_in(api: Api, name: str, email: str) -> Actor:
    """A staff sign-in: the password, then the second factor from the mail."""
    first = await api.call("POST", "/auth/login", json={"login": email, "password": PASSWORD})
    actor = Actor(name=name, cookies=dict(first.cookies))
    code = api.code(MFA_CODE, 2)
    verified = await api.call("POST", "/auth/mfa/verify", actor=actor, json={"code": code})
    actor.cookies.update(dict(verified.cookies))
    me = await api.call("GET", "/auth/me", actor=actor)
    actor.uuid = me.json()["uuid"]
    return actor


async def clear_loopback_limits(redis: Any) -> None:
    """Every request here comes from 127.0.0.1, and the public forms limit by
    address per hour. Twelve people signing up from one address is the seed,
    not an attack, so the loopback buckets - those only - are dropped."""
    async for key in redis.scan_iter(match=f"{K_RATE}:*_ip:127.0.0.1"):
        await redis.delete(key)


# =============================================================================
#  The steps
# =============================================================================


async def refuse_if_seeded(api: Api, admin: Actor) -> None:
    """Stop before writing anything if any of these people already exist."""
    found = []
    for s in STAFF:
        r = await api.call("GET", "/users", actor=admin, params={"q": s["email"]})
        if r.json()["items"]:
            found.append(s["email"])
    for p in PRINCIPALS:
        r = await api.call("GET", "/users", actor=admin, params={"q": p["mobile"]})
        if r.json()["items"]:
            found.append(p["mobile"])
    r = await api.call("GET", "/purposes", actor=admin, params={"q": PURPOSES[0]["purpose_code"]})
    if any(i.get("purpose_code") == PURPOSES[0]["purpose_code"] for i in r.json()["items"]):
        found.append(PURPOSES[0]["purpose_code"])
    if found:
        raise AlreadySeeded(
            "The demo data is already here (found "
            + ", ".join(found[:4])
            + ("…" if len(found) > 4 else "")
            + "). It runs once per database: rebuild it with scripts/reset_dev.py, "
            "run seed.py, then this."
        )


async def invite_staff(api: Api, admin: Actor) -> dict[str, Actor]:
    """The administrator invites each person; the invitation's code sets the
    password, which activates the account; then each signs in."""
    staff: dict[str, Actor] = {}
    for s in STAFF:
        await api.call(
            "POST",
            "/users",
            actor=admin,
            expect=(201,),
            json={
                "full_name": s["full_name"],
                "email": s["email"],
                "role": s["role"],
                "organization_id": s["org"],
                "person_type": "employee",
            },
        )
        code = api.code(INVITATION, 4)
        await api.call(
            "POST",
            "/auth/password/reset/confirm",
            json={"email": s["email"], "code": code, "new_password": PASSWORD},
        )
        staff[s["key"]] = await sign_in(api, s["full_name"], s["email"])
        api.counts["staff accounts"] += 1
        log.info("seed_demo.staff", role=s["role"], email=s["email"])
    return staff


async def register(
    api: Api, staff: dict[str, Actor]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    """Purposes (DPO), processors (DPO), and a source under each (its runner)."""
    dpo = staff["dpo1"]
    purposes: dict[str, str] = {}
    for p in PURPOSES:
        r = await api.call(
            "POST",
            "/purposes",
            actor=dpo,
            expect=(201,),
            json={
                "purpose_code": p["purpose_code"],
                "name": p["name"],
                "description": p["description"],
                "uses": p["uses"],
                "lawful_basis": "consent_s6",
                "data_categories": p["data_categories"],
                "retention_days": p["retention_days"],
                "retention_basis": "business_policy",
                "erasure_trigger": p["erasure_trigger"],
                "consent_validity_days": 730,
                "lapse_behaviour": "quarantine",
                "cross_border_permitted": p.get("cross_border_permitted", False),
                "permitted_for_minors": False,
            },
        )
        uuid = r.json()["purpose_uuid"]
        await api.call("POST", f"/purposes/{uuid}/activate", actor=dpo)
        purposes[p["purpose_code"]] = uuid
        api.counts["purposes"] += 1

    processors: dict[str, Any] = {}
    sources: dict[str, str] = {}
    for p in PROCESSORS:
        r = await api.call(
            "POST",
            "/processors",
            actor=dpo,
            expect=(201,),
            json={
                "legal_name": p["legal_name"],
                "type": p["type"],
                "contract_ref": p["contract_ref"],
                "security_confirmed_at": (TODAY - timedelta(days=90)).isoformat(),
                "is_in_house": p["is_in_house"],
                "location_country": p["location_country"],
            },
        )
        processors[p["key"]] = {**p, "uuid": r.json()["processor_uuid"]}
        api.counts["processors"] += 1

        s = p["source"]
        runner = staff[s["owner"]]
        r = await api.call(
            "POST",
            "/sources",
            actor=runner,
            expect=(201,),
            json={
                "source_code": s["source_code"],
                "name": s["name"],
                "source_role": "collection",
                "exchange_mode": "manual_upload",
                "id_scheme": f"{p['key']}-participant",
                "processor_uuid": processors[p["key"]]["uuid"],
                "is_authoritative_for": s["authoritative"],
            },
        )
        source_uuid = r.json()["source_uuid"]
        # Who runs a third party's source is the DCO Admin's call; an in-house
        # team's, the DPO's.
        assigner = staff["dpo1"] if p["is_in_house"] else staff["dcoa1"]
        await api.call(
            "PUT",
            f"/sources/{source_uuid}/owner",
            actor=assigner,
            json={"owner_user_uuid": runner.uuid},
        )
        sources[p["key"]] = source_uuid
        api.counts["data sources"] += 1
    return purposes, processors, sources


NOTICE_TEXT = """\
NOTICE UNDER SECTION 5, DIGITAL PERSONAL DATA PROTECTION ACT 2023

Who is asking. Bharat Research Labs, acting as Data Fiduciary, for the study
"{name}".

What we will collect and why. {purposes}

How long we keep it. For the retention period of each purpose, after which it
is erased.

Your rights. You may ask for a summary of your data, ask us to correct or erase
it, nominate someone to act for you, and withdraw your consent at any time -
as easily as you gave it.

If you are not satisfied. Contact our Data Protection Officer first. You may
also complain to the Data Protection Board of India.
"""


async def build_projects(
    api: Api,
    staff: dict[str, Actor],
    purposes: dict[str, str],
    processors: dict[str, Any],
    sources: dict[str, str],
) -> dict[str, dict[str, Any]]:
    """Each project from registration to where its table says it ends; the
    approved ones get their sites and a consent link on each."""
    dpo = staff["dpo1"]
    by_code = {p["purpose_code"]: p for p in PURPOSES}
    projects: dict[str, dict[str, Any]] = {}
    for n, p in enumerate(PROJECTS, start=1):
        owner = staff[p["owner"]]
        processor_keys = list(dict.fromkeys(k for k, _ in p["sites"]))
        r = await api.call(
            "POST",
            "/projects",
            actor=owner,
            expect=(201,),
            json={
                "project_name": p["project_name"],
                "internal_project_name": p["internal"],
                "description": f"{p['project_name']}: collection for the {p['team']} team.",
                "requesting_team": p["team"],
                "processor_uuids": [processors[k]["uuid"] for k in processor_keys],
            },
        )
        uuid = r.json()["project_uuid"]
        project = {**p, "uuid": uuid, "sites_made": []}
        projects[p["key"]] = project
        api.counts["projects"] += 1

        # ---- the notice: the DPO writes it, names the purposes, approves the text
        text = NOTICE_TEXT.format(
            name=p["project_name"],
            purposes=" ".join(
                f"{by_code[c]['name']}: {by_code[c]['description']}" for c in p["purposes"]
            ),
        )
        r = await api.call(
            "POST",
            f"/projects/{uuid}/notices",
            actor=dpo,
            expect=(201,),
            json={
                "withdraw_url": "https://cmp.local/withdraw",
                "exercise_rights_url": "https://cmp.local/rights",
                "board_complaint_url": "https://dpb.gov.in/complaint",
                "dpo_contact": "privacy@bharatresearch.example",
                "applicable_to": "data_subject",
                "rendered_text": text,
                "language_code": "english",
            },
        )
        notice_uuid = r.json()["notice_uuid"]
        for order, code in enumerate(p["purposes"], start=1):
            await api.call(
                "POST",
                f"/notices/{notice_uuid}/purposes",
                actor=dpo,
                json={
                    "purpose_uuid": purposes[code],
                    "display_order": order,
                    "is_mandatory": False,
                },
            )
        project["notice_uuid"] = notice_uuid
        api.counts["notices"] += 1
        if p["state"] == "in_draft":
            continue
        await api.call("POST", f"/notices/{notice_uuid}/languages/english/approve", actor=dpo)

        # ---- the approval proof and the submission (R&D), the decision (DPO)
        proof = b"%PDF-1.4\n% seed approval proof\n" + p["internal"].encode()
        await api.call(
            "POST",
            f"/projects/{uuid}/approvals",
            actor=owner,
            expect=(201,),
            data={
                "approval_type": "security",
                "reference_no": f"SEC-2026-{300 + n:04d}",
                "approved_on": (TODAY - timedelta(days=30)).isoformat(),
            },
            files={"proof": (f"{p['internal']}-security.pdf", proof, "application/pdf")},
        )
        await api.call(
            "POST", f"/projects/{uuid}/transition", actor=owner, json={"to": "pending_approval"}
        )
        if p["state"] == "pending_approval":
            continue
        await api.call("POST", f"/projects/{uuid}/transition", actor=dpo, json={"to": "approved"})

        # ---- sites: the DCO Admin places a third party's; the R&D owner an
        #      in-house team's. Then whoever runs the source mints the link.
        for key, location in p["sites"]:
            proc = processors[key]
            placer = owner if proc["is_in_house"] else staff["dcoa1"]
            r = await api.call(
                "POST",
                f"/projects/{uuid}/sites",
                actor=placer,
                expect=(201,),
                json={"source_uuid": sources[key], "location": location},
            )
            site_uuid = r.json()["site_uuid"]
            runner = staff[proc["source"]["owner"]]
            r = await api.call(
                "POST",
                f"/sites/{site_uuid}/agent",
                actor=runner,
                json={
                    "expires_at": (datetime.now(UTC) + timedelta(days=60)).isoformat(),
                    "max_uses": 500,
                },
            )
            body = r.json()
            path = body.get("url_path") or body.get("link", {}).get("url_path", "")
            project["sites_made"].append(
                {
                    "uuid": site_uuid,
                    "processor": key,
                    "source_uuid": sources[key],
                    "runner": runner,
                    "token": path.rsplit("/", 1)[-1],
                    "location": location,
                    "consents": [],
                }
            )
            api.counts["collection sites"] += 1
            api.counts["consent links"] += 1
    return projects


async def principals_arrive(
    api: Api,
    redis: Any,
    purposes: dict[str, str],
    projects: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Each person opens their site's link, registers, proves both contacts and decides."""
    people: list[dict[str, Any]] = []
    for person in PRINCIPALS:
        await clear_loopback_limits(redis)
        project_key, site_index = person["site"]
        project = projects[project_key]
        site = project["sites_made"][site_index]
        token = site["token"]

        await api.call("GET", f"/c/{token}")
        await api.call("GET", f"/c/{token}/notice", params={"language_code": "english"})
        await api.call(
            "POST",
            f"/c/{token}/register",
            json={
                "full_name": person["full_name"],
                "mobile": person["mobile"],
                "email": person["email"],
                "dob": person["dob"],
                "person_type": "external",
            },
        )
        her = Actor(name=person["full_name"])
        for contact in (person["mobile"], person["email"]):
            await api.call("POST", f"/c/{token}/otp", json={"contact": contact})
            code = api.code(CONSENT_CODE, 1)
            verified = await api.call(
                "POST", f"/c/{token}/otp/verify", actor=her, json={"contact": contact, "code": code}
            )
            her.cookies.update(dict(verified.cookies))
        # The notice has to have been shown to her, signed in, before she decides.
        await api.call("GET", f"/c/{token}/notice", actor=her, params={"language_code": "english"})

        decision = person["decision"]
        if decision == "all":
            grants = {purposes[c]: True for c in project["purposes"]}
        elif decision == "decline":
            grants = {purposes[c]: False for c in project["purposes"]}
        else:
            grants = {purposes[c]: c not in decision for c in project["purposes"]}
        r = await api.call(
            "POST",
            f"/c/{token}/consent",
            actor=her,
            json={
                "language_code": "english",
                "grants": grants,
                "action_type": "button_press" if decision == "decline" else "checkbox_click",
            },
        )
        consent_uuid = r.json()["consent_uuid"]
        api.counts["data principals"] += 1
        api.counts["consents"] += 1
        granted = [u for u, g in grants.items() if g]
        if granted:
            site["consents"].append(consent_uuid)
        people.append(
            {
                **person,
                "actor": her,
                "consent_uuid": consent_uuid,
                "granted": granted,
                "project": project,
            }
        )
        log.info("seed_demo.principal", name=person["full_name"], decision=str(decision))
    return people


async def withdrawals(api: Api, people: list[dict[str, Any]]) -> None:
    """Withdrawn from the portal, as she would: part of one, all of another."""
    for person in people:
        later = person.get("later")
        if not later:
            continue
        body = {"all": True} if later == "withdraw_all" else {"purposes": person["granted"][:1]}
        r = await api.call(
            "POST",
            f"/me/consents/{person['consent_uuid']}/withdraw",
            actor=person["actor"],
            json=body,
        )
        # The withdrawal is a new record; what she still agrees to lives on it.
        person["consent_uuid"] = r.json().get("consent_uuid", person["consent_uuid"])
        api.counts["withdrawals"] += 1


async def exchange(api: Api, projects: dict[str, dict[str, Any]]) -> None:
    """Each site's runner exports the people on the project and imports what
    the site collected, under the consents given there."""
    exported: set[tuple[str, str]] = set()
    for project in projects.values():
        for n, site in enumerate(project["sites_made"], start=1):
            if not site["consents"]:
                continue
            runner = site["runner"]
            if (project["uuid"], runner.uuid) not in exported:
                await api.call("POST", f"/projects/{project['uuid']}/exports", actor=runner)
                exported.add((project["uuid"], runner.uuid))
                api.counts["exports"] += 1

            batch = f"{project['internal']}-S{n}"
            kind, ext = ("audio", "wav") if project["key"] == "asr" else ("video", "mp4")
            collected = (TODAY - timedelta(days=3)).isoformat()
            ref = f"{batch},{batch.lower()}"
            lines = [
                "source_collection_ref,source_asset_ref,asset_type,collected_on,"
                "subject_role,consent_uuid"
            ]
            for i, consent in enumerate(site["consents"], start=1):
                lines.append(f"{ref}-{i:03d}.{ext},{kind},{collected},consented,{consent}")
            # Somebody who walked through the frame: in the file, under nobody's consent.
            lines.append(f"{ref}-bystander.{ext},{kind},{collected},incidental,")
            manifest = ("\n".join(lines) + "\n").encode()
            form = {"source": site["source_uuid"], "project": project["uuid"]}
            await api.call(
                "POST",
                "/imports/validate",
                actor=runner,
                data=form,
                files={"manifest": ("manifest.csv", manifest, "text/csv")},
            )
            r = await api.call(
                "POST",
                "/imports",
                actor=runner,
                data=form,
                files={"manifest": ("manifest.csv", manifest, "text/csv")},
            )
            api.counts["imports"] += 1
            api.counts["assets"] += int(r.json().get("accepted_rows", 0))


async def rights(api: Api, staff: dict[str, Actor], people: list[dict[str, Any]]) -> None:
    """Requests from the portal, some acknowledged by the DPO; nominations; cover."""
    dpo = staff["dpo1"]
    for person in people:
        kind, text = person["request"]
        body: dict[str, Any] = {"request_type": kind, "request_text": text}
        if kind in ("correction", "erasure") and person["granted"]:
            body["consent_uuid"] = person["consent_uuid"]
        r = await api.call(
            "POST", "/me/requests", actor=person["actor"], expect=(200, 201), json=body
        )
        api.counts["rights requests"] += 1
        if person["acknowledge"]:
            await api.call("POST", f"/requests/{r.json()['request_uuid']}/acknowledge", actor=dpo)
            api.counts["requests acknowledged"] += 1

    for index, nominee in NOMINATIONS:
        await api.call(
            "POST", "/me/nominations", actor=people[index]["actor"], expect=(200, 201), json=nominee
        )
        api.counts["nominations"] += 1

    for delegator, delegate, reason in COVER:
        await api.call(
            "POST",
            "/delegations",
            actor=staff[delegator],
            expect=(200, 201),
            json={
                "delegate_user_uuid": staff[delegate].uuid,
                "reason": reason,
                "starts_at": datetime.now(UTC).isoformat(),
                "ends_at": (datetime.now(UTC) + timedelta(days=14)).isoformat(),
            },
        )
        api.counts["cover arrangements"] += 1


# =============================================================================
#  The run
# =============================================================================


async def seed_demo() -> None:
    if settings.environment not in ("local", "test"):
        log.error("seed_demo.refused", environment=settings.environment)
        sys.exit(f"Refusing to seed a {settings.environment} database.")

    await open_pool()
    redis = await open_redis()

    # Codes leave through the task queue. They are read here instead, the way
    # the person would read them, and the messages are not sent.
    from cmp.tasks import dispatch as dispatch_mod

    sent: list[tuple[str, tuple[Any, ...]]] = []

    def capture(task: Any, *args: Any, **kwargs: Any) -> str:
        sent.append((task.name, args))
        return "seeded"

    dispatch_mod.dispatch_required = capture
    dispatch_mod.dispatch_optional = capture

    from cmp.bootstrap.application import create_app

    transport = httpx.ASGITransport(app=create_app(), client=("127.0.0.1", 0))
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://seed.local") as client:
            api = Api(client, sent)
            await clear_loopback_limits(redis)
            try:
                admin = await sign_in(api, "administrator", ADMIN["email"])
            except SeedError as exc:
                sys.exit(
                    f"Could not sign in as {ADMIN['email']} with the seed password. "
                    f"Run seed.py first, or put the password back.\n  {exc}"
                )
            await refuse_if_seeded(api, admin)

            staff = await invite_staff(api, admin)
            purposes, processors, sources = await register(api, staff)
            projects = await build_projects(api, staff, purposes, processors, sources)
            people = await principals_arrive(api, redis, purposes, projects)
            await withdrawals(api, people)
            await exchange(api, projects)
            await rights(api, staff, people)
    except AlreadySeeded as exc:
        sys.exit(f"\nNothing written. {exc}")
    except SeedError as exc:
        sys.exit(f"\nSeed stopped: {exc}\n(Everything before this step is in the database.)")
    finally:
        await close_redis()
        await close_pool()

    print("\n" + "=" * 72)
    print(f"  DEMO SEED COMPLETE  (database {settings.postgres_db})")
    print("=" * 72)
    for what, n in api.counts.items():
        print(f"  {what:24} {n}")
    print(f"\n  Staff sign in at the console with password {PASSWORD}:")
    for s in STAFF:
        print(f"    {s['role']:10} {s['full_name']:18} {s['email']}")
    print("\n  Data principals sign in at the portal with a code to their mobile or email:")
    for p in PRINCIPALS[:3]:
        print(f"    {p['full_name']:18} {p['mobile']}  {p['email']}")
    print(f"    … and {len(PRINCIPALS) - 3} more (+91900300010x, +9190030001xx)")
    print("=" * 72 + "\n")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    configure_logging()
    asyncio.run(seed_demo())
