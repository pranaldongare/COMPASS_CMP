"""Reports, made by the workers on the `reports` queue (ADR 0045).

Two tasks: one makes a report that was asked for - counting, laying out,
rendering, storing and hashing it - and one, on the beat every hour, makes
each scheduled report that is due and mails it to the roles it names.
"""

from cmp.tasks.reports.generate import generate_report, run_report_schedules

__all__ = ["generate_report", "run_report_schedules"]
