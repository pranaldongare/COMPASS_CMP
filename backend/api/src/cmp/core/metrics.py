"""Every figure the analytics show, and every report they make (ADR 0045).

One catalogue, as the messages have one (`cmp.core.messages`): a metric is
declared here with its words - what it counts, exactly, in what unit, for
whom - and the screens, the reports and the docs read it from here, so the
same number cannot mean two things in two places. How it is counted is the
repository's (`cmp.db.repositories.analytics`), keyed the same; a test holds
the two together.

Three rules, all tested:

* **Figures, never records.** Every metric is a count, a rate, a median or a
  sum over rows; none names a person, and a breakdown is by a category the
  platform owns (a request type, a channel, a project, a holder's label).
* **Small numbers are withheld.** A metric that counts people (`people=True`)
  is shown as "fewer than N" when it is above nought and below the threshold
  the administrator sets (`analytics_setting`, 1 to start with: nothing is
  withheld).
* **The wall stays.** An officer reads their own office's figures, as their
  session reads its rows; management reads both, combined or one at a time.
  Breach figures go to the officers and management only, as breaches do.

Pure data. No SQL here, and no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

# --------------------------------------------------------------- audiences
MANAGEMENT: Final = "management"
DPO: Final = "dpo"
LEGAL: Final = "legal"
ADMIN: Final = "admin"
RND_USER: Final = "rnd_user"
DCO: Final = "dco"
DCO_ADMIN: Final = "dco_admin"
RCO: Final = "rco"
HR_USER: Final = "hr_user"

#: Who reads the management scorecard and the analytics: the people the
#: organisation reports to, and the two offices' officers.
OVERSIGHT: Final[frozenset[str]] = frozenset({MANAGEMENT, DPO, LEGAL})
#: The roles that do the work, each with figures of their own work only.
WORKERS: Final[frozenset[str]] = frozenset({RND_USER, DCO, DCO_ADMIN, RCO, HR_USER})
#: The collection roles.
COLLECTORS: Final[frozenset[str]] = frozenset({DCO, DCO_ADMIN, RCO})
#: The administrator's: audit and health, nothing else (the product owner).
HEALTH_READERS: Final[frozenset[str]] = frozenset({ADMIN})
#: Data quality: the administrator, with health, and the officers.
QUALITY_READERS: Final[frozenset[str]] = frozenset({ADMIN, DPO, LEGAL})
#: Audit reports: the administrator, and each officer for their own office.
AUDIT_READERS: Final[frozenset[str]] = frozenset({ADMIN, DPO, LEGAL})

#: The sections of the Analytics page, in order, and who sees each.
SECTIONS: Final[dict[str, frozenset[str]]] = {
    "management": OVERSIGHT,
    "analytics": OVERSIGHT,
    "mine": WORKERS,
    "audit": AUDIT_READERS,
    "health": HEALTH_READERS,
    "quality": QUALITY_READERS,
    "inventory": OVERSIGHT,
    "reports": OVERSIGHT | WORKERS | AUDIT_READERS | HEALTH_READERS,
}

#: How a figure is made from its rows.
COUNT: Final = "count"
MEDIAN: Final = "median"
RATIO: Final = "ratio"
#: As things stand now, whatever the period: open requests, active consents.
SNAPSHOT: Final = "snapshot"
#: Read from a running service, not the database: a queue's depth.
LIVE: Final = "live"

#: The breakdowns a metric may be split by, in words.
DIMENSIONS: Final[dict[str, str]] = {
    "office": "Office",
    "type": "Request type",
    "channel": "Channel",
    "outcome": "Outcome",
    "status": "Status",
    "location": "Where it happened",
    "duty": "Duty",
    "project": "Project",
    "category": "HR category",
    "holder": "Holder",
    "flow": "Code flow",
    "queue": "Queue",
    "event": "Event",
    "kind": "Review kind",
}


@dataclass(frozen=True, slots=True)
class Metric:
    key: str
    title: str
    #: Exactly what is counted, for a person reading the figure - and the docs.
    definition: str
    #: count | percent | days | hours
    unit: str
    #: management | analytics | mine | health | quality
    section: str
    #: The heading it sits under on its page.
    group: str
    audience: frozenset[str]
    kind: str = COUNT
    #: For a ratio: the two counts, both declared here.
    numerator: str | None = None
    denominator: str | None = None
    #: Counts people, so small numbers are withheld.
    people: bool = False
    dims: tuple[str, ...] = ()
    #: The default target and amber line; the administrator may replace both.
    #: None: the figure has no target.
    target: float | None = None
    amber: float | None = None
    higher_is_better: bool = True

    @property
    def has_target(self) -> bool:
        return self.target is not None


def _m(**kw: object) -> Metric:
    return Metric(**kw)  # type: ignore[arg-type]


_RIGHTS = "Rights requests"
_BREACH = "Breaches"
_CONSENT = "Consent"
_PROJECTS = "Projects"
_ERASURE = "Erasure in DataVault"
_HOLDERS = "Third parties"
_RETENTION = "Retention"
_DELIVERY = "Notice delivery"
_HR = "HR track"
_SIGNIN = "Sign-in and codes"
_INTEGRITY = "Integrity"
_PIPES = "Pipelines"
_QUALITY = "Data quality"
_MINE = "Your work"

CATALOGUE: Final[tuple[Metric, ...]] = (
    # =================================================== management scorecard
    _m(
        key="rights.received",
        title="Requests received",
        definition="Rights requests received in the period, of every type, by any channel.",
        unit="count",
        section="management",
        group=_RIGHTS,
        audience=OVERSIGHT,
        dims=("office", "type", "channel"),
    ),
    _m(
        key="rights.closed",
        title="Requests closed",
        definition="Rights requests closed in the period, whatever the outcome.",
        unit="count",
        section="management",
        group=_RIGHTS,
        audience=OVERSIGHT,
        dims=("office", "type", "outcome"),
    ),
    _m(
        key="rights.closed_on_time",
        title="Requests closed on time",
        definition="Rights requests closed in the period on or before the date due.",
        unit="count",
        section="management",
        group=_RIGHTS,
        audience=OVERSIGHT,
        dims=("office", "type"),
    ),
    _m(
        key="rights.on_time_rate",
        title="Closed on time",
        definition="Of the requests closed in the period, the share closed on or before the "
        "date due.",
        unit="percent",
        section="management",
        group=_RIGHTS,
        audience=OVERSIGHT,
        kind=RATIO,
        numerator="rights.closed_on_time",
        denominator="rights.closed",
        dims=("office", "type"),
        target=95,
        amber=85,
    ),
    _m(
        key="rights.median_days_to_close",
        title="Median days to close",
        definition="For requests closed in the period, the median number of days from receipt "
        "to closure.",
        unit="days",
        section="management",
        group=_RIGHTS,
        audience=OVERSIGHT,
        kind=MEDIAN,
        dims=("office", "type"),
        target=30,
        amber=60,
        higher_is_better=False,
    ),
    _m(
        key="rights.open",
        title="Requests open",
        definition="Rights requests not yet closed, as things stand now.",
        unit="count",
        section="management",
        group=_RIGHTS,
        audience=OVERSIGHT,
        kind=SNAPSHOT,
        dims=("office", "status", "type"),
    ),
    _m(
        key="rights.overdue",
        title="Requests overdue",
        definition="Rights requests not yet closed whose due date has passed, as things stand now.",
        unit="count",
        section="management",
        group=_RIGHTS,
        audience=OVERSIGHT,
        kind=SNAPSHOT,
        dims=("office", "type"),
        target=0,
        amber=2,
        higher_is_better=False,
    ),
    _m(
        key="rights.grievances",
        title="Grievances received",
        definition="Grievances received in the period.",
        unit="count",
        section="management",
        group=_RIGHTS,
        audience=OVERSIGHT,
        dims=("office", "channel"),
    ),
    _m(
        key="rights.grievances_upheld",
        title="Grievances upheld",
        definition="Grievances closed in the period as upheld.",
        unit="count",
        section="management",
        group=_RIGHTS,
        audience=OVERSIGHT,
        dims=("office",),
    ),
    _m(
        key="breach.incidents",
        title="Incidents recorded",
        definition="Incidents recorded in the period, by when they were detected.",
        unit="count",
        section="management",
        group=_BREACH,
        audience=OVERSIGHT,
        dims=("office", "location"),
    ),
    _m(
        key="breach.confirmed",
        title="Confirmed as breaches",
        definition="Incidents confirmed in the period as personal data breaches.",
        unit="count",
        section="management",
        group=_BREACH,
        audience=OVERSIGHT,
        dims=("office", "location"),
    ),
    _m(
        key="breach.open",
        title="Breaches open",
        definition="Incidents and breaches not yet closed, as things stand now.",
        unit="count",
        section="management",
        group=_BREACH,
        audience=OVERSIGHT,
        kind=SNAPSHOT,
        dims=("office",),
    ),
    _m(
        key="breach.duties_completed",
        title="Duties completed",
        definition="Breach duties completed in the period: the Board's intimation and report, "
        "CERT-In, the people affected, the organisation's board.",
        unit="count",
        section="management",
        group=_BREACH,
        audience=OVERSIGHT,
        dims=("office", "duty"),
    ),
    _m(
        key="breach.duties_on_time",
        title="Duties completed on time",
        definition="Breach duties completed in the period on or before their due time, as "
        "extended where an extension was allowed.",
        unit="count",
        section="management",
        group=_BREACH,
        audience=OVERSIGHT,
        dims=("office", "duty"),
    ),
    _m(
        key="breach.duty_on_time_rate",
        title="Duties met on time",
        definition="Of the breach duties completed in the period, the share completed on time.",
        unit="percent",
        section="management",
        group=_BREACH,
        audience=OVERSIGHT,
        kind=RATIO,
        numerator="breach.duties_on_time",
        denominator="breach.duties_completed",
        dims=("office", "duty"),
        target=100,
        amber=95,
    ),
    _m(
        key="breach.public_reports",
        title="Reports from the public link",
        definition="Incident reports received through the public link in the period.",
        unit="count",
        section="management",
        group=_BREACH,
        audience=OVERSIGHT,
        dims=("outcome",),
    ),
    _m(
        key="consent.given",
        title="Consents given",
        definition="Consents given in the period: each decision with at least one purpose "
        "agreed, a withdrawal not counted.",
        unit="count",
        section="management",
        group=_CONSENT,
        audience=OVERSIGHT,
        people=True,
        dims=("office", "project"),
    ),
    _m(
        key="consent.withdrawn",
        title="Withdrawals",
        definition="Withdrawals of consent, in full or in part, in the period.",
        unit="count",
        section="management",
        group=_CONSENT,
        audience=OVERSIGHT,
        people=True,
        dims=("office", "project"),
    ),
    _m(
        key="consent.withdrawal_rate",
        title="Withdrawal rate",
        definition="Withdrawals in the period as a share of consents given in the period.",
        unit="percent",
        section="management",
        group=_CONSENT,
        audience=OVERSIGHT,
        kind=RATIO,
        numerator="consent.withdrawn",
        denominator="consent.given",
        dims=("office", "project"),
        target=5,
        amber=10,
        higher_is_better=False,
    ),
    _m(
        key="consent.active",
        title="Consents in force",
        definition="Consent records in force now - the latest of each chain, not a withdrawal.",
        unit="count",
        section="management",
        group=_CONSENT,
        audience=OVERSIGHT,
        kind=SNAPSHOT,
        people=True,
        dims=("office", "project"),
    ),
    _m(
        key="consent.expiring_90d",
        title="Consents expiring within 90 days",
        definition="Consents in force now with at least one purpose whose consent validity "
        "ends in the next 90 days.",
        unit="count",
        section="management",
        group=_CONSENT,
        audience=OVERSIGHT,
        kind=SNAPSHOT,
        people=True,
        dims=("office",),
    ),
    _m(
        key="projects.approved",
        title="Projects approved",
        definition="Projects moved to approved in the period.",
        unit="count",
        section="management",
        group=_PROJECTS,
        audience=OVERSIGHT,
        dims=("office",),
    ),
    _m(
        key="projects.median_days_to_approve",
        title="Median days to approve",
        definition="For projects approved in the period, the median number of days from "
        "creation to approval.",
        unit="days",
        section="management",
        group=_PROJECTS,
        audience=OVERSIGHT,
        kind=MEDIAN,
        dims=("office",),
        target=14,
        amber=30,
        higher_is_better=False,
    ),
    _m(
        key="projects.sent_back",
        title="Projects sent back",
        definition="Projects sent back for changes in the period.",
        unit="count",
        section="management",
        group=_PROJECTS,
        audience=OVERSIGHT,
        dims=("office",),
    ),
    _m(
        key="projects.active",
        title="Projects by status",
        definition="Projects as they stand now, by status.",
        unit="count",
        section="management",
        group=_PROJECTS,
        audience=OVERSIGHT,
        kind=SNAPSHOT,
        dims=("office", "status"),
    ),
    _m(
        key="erasure.assets_sent",
        title="Assets sent for erasure",
        definition="Assets named in erasure instructions sent to DataVault in the period.",
        unit="count",
        section="management",
        group=_ERASURE,
        audience=OVERSIGHT,
        dims=("office",),
    ),
    _m(
        key="erasure.assets_erased",
        title="Assets erased",
        definition="Assets DataVault reported erased in the period.",
        unit="count",
        section="management",
        group=_ERASURE,
        audience=OVERSIGHT,
        dims=("office",),
    ),
    _m(
        key="erasure.assets_failed",
        title="Assets not erased",
        definition="Assets DataVault reported it could not erase, in the period.",
        unit="count",
        section="management",
        group=_ERASURE,
        audience=OVERSIGHT,
        dims=("office",),
        target=0,
        amber=1,
        higher_is_better=False,
    ),
    _m(
        key="erasure.completion_rate",
        title="Erasure completion",
        definition="Assets erased in the period as a share of assets sent for erasure in it.",
        unit="percent",
        section="management",
        group=_ERASURE,
        audience=OVERSIGHT,
        kind=RATIO,
        numerator="erasure.assets_erased",
        denominator="erasure.assets_sent",
        dims=("office",),
        target=95,
        amber=80,
    ),
    _m(
        key="holders.tickets_issued",
        title="Tickets to holders",
        definition="Tickets issued in the period to the holders of a requester's data.",
        unit="count",
        section="management",
        group=_HOLDERS,
        audience=OVERSIGHT,
        dims=("office", "holder"),
    ),
    _m(
        key="holders.median_days_to_return",
        title="Median days for a holder to return",
        definition="For tickets returned in the period, the median number of days from issue "
        "to return.",
        unit="days",
        section="management",
        group=_HOLDERS,
        audience=OVERSIGHT,
        kind=MEDIAN,
        dims=("office", "holder"),
        target=5,
        amber=10,
        higher_is_better=False,
    ),
    _m(
        key="holders.overdue",
        title="Holder tickets overdue",
        definition="Tickets issued and not returned whose due date has passed, as things stand "
        "now.",
        unit="count",
        section="management",
        group=_HOLDERS,
        audience=OVERSIGHT,
        kind=SNAPSHOT,
        dims=("office", "holder"),
        target=0,
        amber=3,
        higher_is_better=False,
    ),
    # Retention reviews (ADR 0047): consents running out and data that must go.
    _m(
        key="retention.reviews_opened",
        title="Retention reviews opened",
        definition="Reviews whose people were first asked in the period: consents whose "
        "validity runs out, and data whose retention has passed.",
        unit="count",
        section="management",
        group=_RETENTION,
        audience=OVERSIGHT,
        dims=("office", "kind"),
    ),
    _m(
        key="retention.reviews_closed",
        title="Retention reviews closed",
        definition="Reviews closed in the period, every answer accepted or set aside.",
        unit="count",
        section="management",
        group=_RETENTION,
        audience=OVERSIGHT,
        dims=("office", "kind"),
    ),
    _m(
        key="retention.closed_on_time",
        title="Retention reviews closed on time",
        definition="Reviews closed in the period no later than the last date their answers "
        "were due.",
        unit="count",
        section="management",
        group=_RETENTION,
        audience=OVERSIGHT,
        dims=("office", "kind"),
    ),
    _m(
        key="retention.on_time_rate",
        title="Retention reviews on time",
        definition="Reviews closed on time in the period as a share of reviews closed in it.",
        unit="percent",
        section="management",
        group=_RETENTION,
        audience=OVERSIGHT,
        kind=RATIO,
        numerator="retention.closed_on_time",
        denominator="retention.reviews_closed",
        dims=("office", "kind"),
        target=95,
        amber=80,
    ),
    _m(
        key="retention.actions_overdue",
        title="Retention answers overdue",
        definition="Answers asked for in a retention review and not given whose date has "
        "passed, as things stand now.",
        unit="count",
        section="management",
        group=_RETENTION,
        audience=OVERSIGHT,
        kind=SNAPSHOT,
        dims=("office", "kind"),
        target=0,
        amber=3,
        higher_is_better=False,
    ),
    _m(
        key="retention.kept_with_reason",
        title="Data kept past retention",
        definition="Answers accepted in the period that kept data past its retention, each "
        "with its reason and a date to look again.",
        unit="count",
        section="management",
        group=_RETENTION,
        audience=OVERSIGHT,
        dims=("office",),
    ),
    # ============================================================== analytics
    _m(
        key="funnel.links_opened",
        title="Consent links opened",
        definition="Times a consent link was opened in the period.",
        unit="count",
        section="analytics",
        group=_CONSENT,
        audience=OVERSIGHT,
        dims=("office", "project"),
    ),
    _m(
        key="funnel.notices_served",
        title="Notices shown",
        definition="Times a notice was shown to a person who had confirmed their contact, in "
        "the period.",
        unit="count",
        section="analytics",
        group=_CONSENT,
        audience=OVERSIGHT,
        dims=("office",),
    ),
    _m(
        key="funnel.declined",
        title="Consents declined",
        definition="Decisions in the period that agreed to no purpose.",
        unit="count",
        section="analytics",
        group=_CONSENT,
        audience=OVERSIGHT,
        people=True,
        dims=("office",),
    ),
    _m(
        key="consent.partial",
        title="Consents given in part",
        definition="Decisions in the period that agreed to some purposes and refused others - "
        "counted in Consents given as well, a withdrawal not counted.",
        unit="count",
        section="analytics",
        group=_CONSENT,
        audience=OVERSIGHT,
        people=True,
        dims=("office", "project"),
    ),
    _m(
        key="rights.median_days_to_acknowledge",
        title="Median days to acknowledge",
        definition="For requests acknowledged in the period, the median days from receipt.",
        unit="days",
        section="analytics",
        group=_RIGHTS,
        audience=OVERSIGHT,
        kind=MEDIAN,
        dims=("office", "type"),
        target=2,
        amber=5,
        higher_is_better=False,
    ),
    _m(
        key="rights.median_days_to_verify",
        title="Median days to verify",
        definition="For requests verified in the period, the median days from receipt.",
        unit="days",
        section="analytics",
        group=_RIGHTS,
        audience=OVERSIGHT,
        kind=MEDIAN,
        dims=("office", "channel"),
    ),
    _m(
        key="rights.median_days_to_respond",
        title="Median days to respond",
        definition="For requests responded to in the period, the median days from receipt to "
        "the response.",
        unit="days",
        section="analytics",
        group=_RIGHTS,
        audience=OVERSIGHT,
        kind=MEDIAN,
        dims=("office", "type"),
    ),
    _m(
        key="breach.median_hours_to_confirm",
        title="Median hours from detection to confirmation",
        definition="For breaches confirmed in the period, the median hours from detection to "
        "confirmation.",
        unit="hours",
        section="analytics",
        group=_BREACH,
        audience=OVERSIGHT,
        kind=MEDIAN,
        dims=("office",),
    ),
    _m(
        key="delivery.notices_delivered",
        title="Breach notices delivered",
        definition="Breach notices delivered in the period by email or SMS.",
        unit="count",
        section="analytics",
        group=_DELIVERY,
        audience=OVERSIGHT,
        dims=("office", "channel"),
    ),
    _m(
        key="delivery.notices_attempted",
        title="Breach notices with an outcome",
        definition="Breach notices by email or SMS with an outcome in the period, delivered or "
        "failed after retrying.",
        unit="count",
        section="analytics",
        group=_DELIVERY,
        audience=OVERSIGHT,
        dims=("office", "channel"),
    ),
    _m(
        key="delivery.notice_rate",
        title="Breach notice delivery",
        definition="Breach notices delivered as a share of those with an outcome, in the period.",
        unit="percent",
        section="analytics",
        group=_DELIVERY,
        audience=OVERSIGHT,
        kind=RATIO,
        numerator="delivery.notices_delivered",
        denominator="delivery.notices_attempted",
        dims=("office", "channel"),
        target=98,
        amber=90,
    ),
    _m(
        key="hr.consents",
        title="HR consents given",
        definition="Consents given in the period on HR activities, by category.",
        unit="count",
        section="analytics",
        group=_HR,
        audience=OVERSIGHT,
        people=True,
        dims=("category",),
    ),
    _m(
        key="hr.withdrawals",
        title="HR withdrawals",
        definition="Withdrawals in the period on HR activities, by category.",
        unit="count",
        section="analytics",
        group=_HR,
        audience=OVERSIGHT,
        people=True,
        dims=("category",),
    ),
    # ==================================================== your work (narrow)
    _m(
        key="mine.projects",
        title="Your projects by status",
        definition="The projects you work on, as they stand now: those you own, collect for "
        "or run in your categories.",
        unit="count",
        section="mine",
        group=_MINE,
        audience=WORKERS,
        kind=SNAPSHOT,
        dims=("status", "project"),
    ),
    _m(
        key="mine.consents_given",
        title="Consents given on your projects",
        definition="Consents given in the period on the projects you work on.",
        unit="count",
        section="mine",
        group=_MINE,
        audience=WORKERS,
        people=True,
        dims=("project",),
    ),
    _m(
        key="mine.consents_withdrawn",
        title="Withdrawals on your projects",
        definition="Withdrawals in the period on the projects you work on.",
        unit="count",
        section="mine",
        group=_MINE,
        audience=WORKERS,
        people=True,
        dims=("project",),
    ),
    _m(
        key="mine.links_opened",
        title="Consent links opened",
        definition="Times a consent link of the projects you work on was opened in the period.",
        unit="count",
        section="mine",
        group=_MINE,
        audience=WORKERS,
        dims=("project",),
    ),
    _m(
        key="mine.links_active",
        title="Consent links live",
        definition="Consent links of the projects you work on that are live now.",
        unit="count",
        section="mine",
        group=_MINE,
        audience=WORKERS,
        kind=SNAPSHOT,
        dims=("project",),
    ),
    _m(
        key="mine.sites_active",
        title="Collection sites active",
        definition="Active collection sites of the projects you work on, now.",
        unit="count",
        section="mine",
        group=_MINE,
        audience=frozenset({RND_USER, DCO, DCO_ADMIN, RCO}),
        kind=SNAPSHOT,
        dims=("project",),
    ),
    _m(
        key="mine.tickets_returned",
        title="Tickets you returned",
        definition="Rights tickets addressed to you that you returned in the period.",
        unit="count",
        section="mine",
        group=_MINE,
        audience=WORKERS,
    ),
    # ================================================================ health
    _m(
        key="health.otp_requested",
        title="Codes sent",
        definition="One-time codes sent to an account in the period - the staff second factor, "
        "the portal sign-in and confirming a contact - by flow.",
        unit="count",
        section="health",
        group=_SIGNIN,
        audience=HEALTH_READERS,
        dims=("flow",),
    ),
    _m(
        key="health.otp_verified",
        title="Codes entered correctly",
        definition="One-time codes entered correctly in the period, of the same flows as "
        "Codes sent, by flow.",
        unit="count",
        section="health",
        group=_SIGNIN,
        audience=HEALTH_READERS,
        dims=("flow",),
    ),
    _m(
        key="health.otp_success_rate",
        title="Code success",
        definition="Codes entered correctly as a share of codes sent, in the period.",
        unit="percent",
        section="health",
        group=_SIGNIN,
        audience=HEALTH_READERS,
        kind=RATIO,
        numerator="health.otp_verified",
        denominator="health.otp_requested",
        dims=("flow",),
        target=80,
        amber=60,
    ),
    _m(
        key="health.sign_in_failures",
        title="Failed sign-ins",
        definition="Staff sign-ins refused in the period: a wrong password or code.",
        unit="count",
        section="health",
        group=_SIGNIN,
        audience=HEALTH_READERS,
        dims=("event",),
    ),
    _m(
        key="health.lockouts",
        title="Accounts paused",
        definition="Staff accounts paused after repeated failed sign-ins, in the period.",
        unit="count",
        section="health",
        group=_SIGNIN,
        audience=HEALTH_READERS,
        target=0,
        amber=3,
        higher_is_better=False,
    ),
    _m(
        key="health.employee_check_failures",
        title="Employee checks not answered",
        definition="Times VerifyEmail gave no answer at a sign-in (ADR 0046), by flow: a "
        "console sign-in is refused then, a portal one goes ahead.",
        unit="count",
        section="health",
        group=_SIGNIN,
        audience=HEALTH_READERS,
        dims=("flow",),
        target=0,
        amber=5,
        higher_is_better=False,
    ),
    _m(
        key="health.access_denied",
        title="Requests refused (403)",
        definition="Requests refused in the period because the role may not do what was asked.",
        unit="count",
        section="health",
        group=_SIGNIN,
        audience=HEALTH_READERS,
    ),
    _m(
        key="health.audit_checks",
        title="Audit trail checks",
        definition="Nightly checks of the audit trail's hash chain in the period.",
        unit="count",
        section="health",
        group=_INTEGRITY,
        audience=HEALTH_READERS,
    ),
    _m(
        key="health.audit_breaks",
        title="Audit trail breaks",
        definition="Checks in the period that found the audit trail's chain broken.",
        unit="count",
        section="health",
        group=_INTEGRITY,
        audience=HEALTH_READERS,
        target=0,
        amber=0,
        higher_is_better=False,
    ),
    _m(
        key="health.breach_notice_failures",
        title="Breach notices not delivered",
        definition="Breach notice emails and texts that failed after retrying, in the period.",
        unit="count",
        section="health",
        group=_PIPES,
        audience=HEALTH_READERS,
        dims=("channel",),
        target=0,
        amber=5,
        higher_is_better=False,
    ),
    _m(
        key="health.board_mail_failures",
        title="Board report mail not delivered",
        definition="Mails of a report to the organisation's board or for the regulator that "
        "failed after retrying, in the period.",
        unit="count",
        section="health",
        group=_PIPES,
        audience=HEALTH_READERS,
        target=0,
        amber=0,
        higher_is_better=False,
    ),
    _m(
        key="health.datavault_pending",
        title="Consent changes waiting for DataVault",
        definition="Consent changes not yet delivered to DataVault, now.",
        unit="count",
        section="health",
        group=_PIPES,
        audience=HEALTH_READERS,
        kind=SNAPSHOT,
        target=0,
        amber=10,
        higher_is_better=False,
    ),
    _m(
        key="health.datavault_failing",
        title="Consent changes DataVault refused",
        definition="Consent changes not delivered whose last try failed, now.",
        unit="count",
        section="health",
        group=_PIPES,
        audience=HEALTH_READERS,
        kind=SNAPSHOT,
        target=0,
        amber=0,
        higher_is_better=False,
    ),
    _m(
        key="health.reports_failed",
        title="Reports that failed",
        definition="Reports asked for in the period that could not be made.",
        unit="count",
        section="health",
        group=_PIPES,
        audience=HEALTH_READERS,
        target=0,
        amber=0,
        higher_is_better=False,
    ),
    _m(
        key="health.queue_depth",
        title="Work waiting in each queue",
        definition="Tasks waiting in each of the workers' queues, now.",
        unit="count",
        section="health",
        group=_PIPES,
        audience=HEALTH_READERS,
        kind=LIVE,
        dims=("queue",),
    ),
    # ========================================================== data quality
    _m(
        key="quality.people_without_contact",
        title="People with no confirmed contact",
        definition="Accounts of data principals with neither a confirmed email nor a confirmed "
        "mobile, now.",
        unit="count",
        section="quality",
        group=_QUALITY,
        audience=QUALITY_READERS,
        kind=SNAPSHOT,
        people=True,
    ),
    _m(
        key="quality.unmapped_assets",
        title="Assets with people not matched",
        definition="Data assets holding records of people the platform could not match to a "
        "consent, now.",
        unit="count",
        section="quality",
        group=_QUALITY,
        audience=QUALITY_READERS,
        kind=SNAPSHOT,
        target=0,
        amber=10,
        higher_is_better=False,
    ),
    _m(
        key="quality.processors_unconfirmed",
        title="Processors without security confirmation",
        definition="Active processors with no date their security was confirmed, now.",
        unit="count",
        section="quality",
        group=_QUALITY,
        audience=QUALITY_READERS,
        kind=SNAPSHOT,
        target=0,
        amber=2,
        higher_is_better=False,
    ),
    _m(
        key="quality.processors_no_country",
        title="Processors with no location",
        definition="Active processors with no country recorded, so a cross-border check cannot "
        "be made, now.",
        unit="count",
        section="quality",
        group=_QUALITY,
        audience=QUALITY_READERS,
        kind=SNAPSHOT,
        target=0,
        amber=1,
        higher_is_better=False,
    ),
)

METRICS: Final[dict[str, Metric]] = {m.key: m for m in CATALOGUE}


def metric(key: str) -> Metric:
    return METRICS[key]


def for_role(role: str, section: str | None = None) -> list[Metric]:
    """The metrics this role may read, in catalogue order."""
    return [
        m for m in CATALOGUE if role in m.audience and (section is None or m.section == section)
    ]


def sections_for(role: str) -> list[str]:
    return [s for s, readers in SECTIONS.items() if role in readers]


# ================================================================ reports


@dataclass(frozen=True, slots=True)
class ReportKind:
    key: str
    title: str
    description: str
    audience: frozenset[str]
    formats: tuple[str, ...]
    #: Only the person who asked for it reads it: their own work's figures.
    private: bool = False
    #: May be made on a schedule and mailed.
    schedulable: bool = True


REPORTS: Final[dict[str, ReportKind]] = {
    r.key: r
    for r in (
        ReportKind(
            "management_scorecard",
            "Management scorecard",
            "Every scorecard figure for the period, against its target, with the previous "
            "period beside it.",
            OVERSIGHT,
            ("pdf", "xlsx"),
        ),
        ReportKind(
            "board_pack",
            "Board pack",
            "The scorecard, the breaches of the period with each duty's outcome, and the rights "
            "requests by type and outcome: for the organisation's board.",
            OVERSIGHT,
            ("pdf",),
        ),
        ReportKind(
            "analytics_summary",
            "Analytics summary",
            "Every analytics figure for the period, with its breakdowns.",
            OVERSIGHT,
            ("xlsx", "pdf"),
        ),
        ReportKind(
            "my_analytics",
            "Your work",
            "The figures of your own work for the period.",
            WORKERS,
            ("xlsx", "pdf"),
            private=True,
        ),
        ReportKind(
            "audit",
            "Audit report",
            "One of the ready-made audit reports, for the period.",
            AUDIT_READERS,
            ("csv", "xlsx", "pdf"),
        ),
        ReportKind(
            "health",
            "Platform health",
            "Sign-in and codes, the audit trail's checks, and the pipelines, for the period.",
            HEALTH_READERS,
            ("pdf", "xlsx"),
        ),
        ReportKind(
            "case_evidence",
            "Evidence pack",
            "The full trail of one rights request or one breach, in order, for a regulator or "
            "an auditor.",
            AUDIT_READERS,
            ("pdf",),
            schedulable=False,
        ),
        ReportKind(
            "data_inventory",
            "Record of processing",
            "Every purpose with what it covers, its lawful basis and retention, every processor "
            "with its country, and every data source.",
            OVERSIGHT,
            ("xlsx", "pdf"),
        ),
        ReportKind(
            "data_quality",
            "Data quality",
            "The data quality figures as they stand.",
            QUALITY_READERS,
            ("xlsx", "pdf"),
        ),
    )
}


def reports_for(role: str) -> list[ReportKind]:
    return [r for r in REPORTS.values() if role in r.audience]


# ========================================================== audit reports


@dataclass(frozen=True, slots=True)
class AuditReport:
    key: str
    title: str
    description: str
    events: tuple[str, ...] = field(default_factory=tuple)


AUDIT_REPORTS: Final[dict[str, AuditReport]] = {
    a.key: a
    for a in (
        AuditReport(
            "privileged",
            "Privileged actions",
            "Accounts made, invited, changed, reactivated or ended; roles changed; second "
            "steps reset; sessions ended; temporary access; cover arranged and ended.",
            (
                "user.created",
                "user.invited",
                "user.role_changed",
                "user.deactivated",
                "user.reactivated",
                "user.staff_access_ended",
                "user.mfa_reset",
                "user.sessions_revoked",
                "user.temporary_access_granted",
                "user.temporary_access_ended",
                "user.processors_set",
                "user.categories_set",
                "delegation.granted",
                "delegation.revoked",
            ),
        ),
        AuditReport(
            "data_access",
            "Access to personal data",
            "Every read or download of a record about a person: consent records, exports, rights "
            "responses and attachments, breach files and reports, approval proofs, the trail's "
            "own export, and generated reports.",
            (
                "consent.record_downloaded",
                "export.generated",
                "export.downloaded",
                "rights.response_downloaded",
                "rights.attachment_read",
                "breach.attachment_read",
                "breach_ticket.file_read",
                "breach.report_read",
                "approval.proof_downloaded",
                "audit.exported",
                "report.downloaded",
            ),
        ),
        AuditReport(
            "configuration",
            "Configuration changes",
            "The words and copies of messages, the DataVault connection, the portal address, "
            "breach settings, restricted countries, and analytics targets and settings.",
            (
                "message_template.updated",
                "message_template.reset",
                "message_template.copies_updated",
                "datavault.connection_changed",
                "portal_address.changed",
                "breach_settings.changed",
                "transfer.country_restricted",
                "transfer.country_lifted",
                "analytics.target_changed",
                "analytics.setting_changed",
            ),
        ),
        AuditReport(
            "security",
            "Security events",
            "Sign-ins refused, accounts paused, codes refused, requests refused (403), sign-in "
            "through the organisation's SSO refused or in conflict, passwords changed or reset, "
            "and breach notices opened by their link.",
            (
                "auth.login_failed",
                "auth.login_locked_out",
                "auth.mfa_failed",
                "auth.otp_failed",
                "auth.access_denied",
                "auth.sso_identity_conflict",
                "auth.sso_assertion_refused",
                "auth.password_changed",
                "auth.password_reset_completed",
                "breach_notice.opened",
            ),
        ),
        AuditReport(
            "integrity",
            "Audit trail integrity",
            "Every check of the trail's hash chain, intact or not, and every export of it.",
            ("audit.verified", "audit.exported"),
        ),
        AuditReport(
            "regulatory",
            "Regulatory evidence",
            "Exports refused for a restricted country, legal holds placed and released, assets "
            "quarantined or erased, DataVault told to erase or of a consent change, retention "
            "floors passed, and a reporter's details erased.",
            (
                "export.refused",
                "legal_hold.placed",
                "legal_hold.released",
                "asset.disposition_changed",
                "datavault.erasure_sent",
                "datavault.consent_change_delivered",
                "rights.retention_floor_passed",
                "incident_report.reporter_erased",
            ),
        ),
        AuditReport(
            "reports",
            "Reports made and read",
            "Every report made, downloaded or deleted, and every schedule set up or changed.",
            (
                "report.generated",
                "report.downloaded",
                "report.deleted",
                "report.schedule_created",
                "report.schedule_updated",
                "report.schedule_deleted",
            ),
        ),
    )
}
