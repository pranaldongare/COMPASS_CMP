"""The UAT workbook: one row per test case, one per step, a defect log, a summary.

Built from the same JSON the Word document is, so the two cannot disagree.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

HERE = Path(__file__).parent
OUT = sys.argv[1]
AREAS = ["ACC", "REG", "PRJ", "CON", "RGT", "OVS"]
cases = [c for a in AREAS if (HERE / f"{a}.json").exists() for c in json.loads((HERE / f"{a}.json").read_text())]
AREA_NAMES = list(dict.fromkeys(c["area"] for c in cases))

FONT = "Arial"
HEAD = PatternFill("solid", fgColor="1F4E79")
INPUT = PatternFill("solid", fgColor="FFF2CC")  # the cells a tester fills in
SOFT = PatternFill("solid", fgColor="F3F4F6")
thin = Side(style="thin", color="BFBFBF")
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
WRAP = Alignment(wrap_text=True, vertical="top")

STATUSES = ["Not run", "Pass", "Fail", "Blocked"]


def style_header(ws, row, widths):
    for i, w in enumerate(widths, 1):
        c = ws.cell(row=row, column=i)
        c.font = Font(name=FONT, bold=True, color="FFFFFF", size=10)
        c.fill = HEAD
        c.alignment = Alignment(wrap_text=True, vertical="center")
        c.border = BOX
        ws.column_dimensions[get_column_letter(i)].width = w


def body(cell, *, fill=None, bold=False):
    cell.font = Font(name=FONT, size=10, bold=bold)
    cell.alignment = WRAP
    cell.border = BOX
    if fill:
        cell.fill = fill


def numbered(items):
    return "\n".join(f"{i}. {t}" for i, t in enumerate(items, 1))


def bullets(items):
    return "\n".join(f"- {t}" for t in items) if items else "None"


def status_dropdown(ws, rng, values=STATUSES):
    dv = DataValidation(type="list", formula1='"' + ",".join(values) + '"', allow_blank=True)
    dv.error = "Choose one of: " + ", ".join(values)
    dv.errorTitle = "Not a status"
    ws.add_data_validation(dv)
    dv.add(rng)


def colour_status(ws, rng):
    for text, colour in (("Pass", "C6EFCE"), ("Fail", "FFC7CE"), ("Blocked", "FFEB9C")):
        ws.conditional_formatting.add(
            rng, CellIsRule(operator="equal", formula=[f'"{text}"'], fill=PatternFill("solid", fgColor=colour))
        )


wb = Workbook()

# ------------------------------------------------------------------ Read Me
ws = wb.active
ws.title = "Read Me"
ws.column_dimensions["A"].width = 26
ws.column_dimensions["B"].width = 110
rows = [
    ("COMPASS CMP - User Acceptance Testing", None),
    ("Build under test", "Branch refactor/frontend-architecture, commit 14576a2 - 29 September 2026"),
    ("Read first", "COMPASS-CMP-UAT-Runbook-and-Test-Cases.docx, Part A (the runbook). It explains the system, the accounts, the test outbox for one-time codes, and how to record results."),
    ("Where to record results", "Test Cases sheet: one row per case - fill in Tester, Date, Status, Actual result / notes, Defect IDs. Test Steps sheet: optional, one row per step, for a failed or complex case. Defect Log: one row per defect."),
    ("Cells you fill in", "Only the pale yellow cells. Everything else is the test definition - do not edit it; tell the coordinator if a step is wrong."),
    ("Status values", "Not run (default), Pass, Fail, Blocked - choose from the drop-down. The Summary sheet counts them."),
    ("Severity values", "Critical, High, Medium, Low - see the runbook, section 7."),
    ("Staff password", "SeedPassw0rd!2026 for every staff account (see the Accounts sheet)."),
    ("Console / portal", "Staff console http://localhost:3000  -  Data principal portal http://localhost:3001"),
    ("Example of a filled result row", None),
]
r = 1
for label, value in rows:
    a = ws.cell(row=r, column=1, value=label)
    a.font = Font(name=FONT, size=16 if r == 1 else 10, bold=True, color="1F4E79" if r == 1 else "000000")
    if value:
        b = ws.cell(row=r, column=2, value=value)
        b.font = Font(name=FONT, size=10)
        b.alignment = WRAP
    r += 1
example_head = ["Tester", "Date", "Status", "Actual result / notes", "Defect IDs"]
example = ["Tester 07 (Ravi)", "25-Sep-2026", "Fail", "Step 4: toast read \"Saved\" instead of \"Processor updated\". Screenshot DEF-003.png", "DEF-003"]
ws.cell(row=r, column=1, value="Columns").font = Font(name=FONT, size=10, bold=True)
ws.cell(row=r, column=2, value="  |  ".join(example_head)).font = Font(name=FONT, size=10, italic=True)
ws.cell(row=r + 1, column=1, value="Example values").font = Font(name=FONT, size=10, bold=True)
ex = ws.cell(row=r + 1, column=2, value="  |  ".join(example))
ex.font = Font(name=FONT, size=10)
ex.fill = INPUT

# ------------------------------------------------------------------ Test Cases
tc = wb.create_sheet("Test Cases")
head = ["ID", "Area", "Title", "Feature", "Performed by", "Priority", "Type", "Ref", "Preconditions",
        "Test data", "Steps", "Expected results", "Pass criteria", "Tester", "Date", "Status",
        "Actual result / notes", "Defect IDs"]
widths = [9, 18, 34, 20, 20, 9, 10, 8, 38, 30, 60, 60, 36, 14, 12, 11, 38, 12]
tc.append(head)
style_header(tc, 1, widths)
for c in cases:
    tc.append([
        c["id"], c["area"], c["title"], c["feature"], c["role"], c["priority"], c["type"], c["ref"],
        bullets(c.get("preconditions")), bullets(c.get("test_data")),
        numbered([s["action"] for s in c["steps"]]), numbered([s["expected"] for s in c["steps"]]),
        c["pass_criteria"], None, None, "Not run", None, None,
    ])
last_tc = tc.max_row
for row in tc.iter_rows(min_row=2, max_row=last_tc):
    for cell in row:
        body(cell, fill=INPUT if cell.column >= 14 else None, bold=cell.column == 1)
tc.freeze_panes = "D2"
tc.auto_filter.ref = f"A1:{get_column_letter(len(head))}{last_tc}"
status_dropdown(tc, f"P2:P{last_tc}")
colour_status(tc, f"P2:P{last_tc}")
for row in range(2, last_tc + 1):
    tc.cell(row=row, column=15).number_format = "DD-MMM-YYYY"

# ------------------------------------------------------------------ Test Steps
ts = wb.create_sheet("Test Steps")
head = ["Case ID", "Case title", "Step", "Action", "Expected result", "Step result", "Actual / notes"]
ts.append(head)
style_header(ts, 1, [9, 34, 6, 62, 62, 11, 40])
for c in cases:
    for i, s in enumerate(c["steps"], 1):
        ts.append([c["id"], c["title"], i, s["action"], s["expected"], None, None])
last_ts = ts.max_row
for row in ts.iter_rows(min_row=2, max_row=last_ts):
    for cell in row:
        body(cell, fill=INPUT if cell.column >= 6 else None, bold=cell.column == 1)
ts.freeze_panes = "D2"
ts.auto_filter.ref = f"A1:G{last_ts}"
status_dropdown(ts, f"F2:F{last_ts}", ["Pass", "Fail", "Blocked", "Not run"])
colour_status(ts, f"F2:F{last_ts}")

# ------------------------------------------------------------------ Defect Log
dl = wb.create_sheet("Defect Log")
head = ["Defect ID", "Test case", "Step", "Title", "Severity", "Steps to reproduce", "Expected",
        "Actual", "Screenshot", "Raised by", "Date raised", "Status", "Resolution / notes"]
dl.append(head)
style_header(dl, 1, [10, 10, 6, 36, 10, 50, 34, 34, 18, 14, 12, 10, 34])
dl.append(["DEF-000 (example)", "REG-05", 4, "Processor edit toast has the wrong wording", "Low",
           "1. Sign in as dpo@cmp.local. 2. Processors > Edit on UAT Lab 07. 3. Change Country to IN. 4. Save changes.",
           "Toast \"Processor updated\"", "Toast \"Saved\"", "DEF-000.png", "Tester 07", "25-Sep-2026", "Open",
           "Example row - delete or overwrite"])
for row in range(2, 202):
    for col in range(1, len(head) + 1):
        body(dl.cell(row=row, column=col), fill=INPUT)
dl.freeze_panes = "B2"
dv = DataValidation(type="list", formula1='"Critical,High,Medium,Low"', allow_blank=True)
dl.add_data_validation(dv)
dv.add("E2:E201")
dv2 = DataValidation(type="list", formula1='"Open,In progress,Fixed,Retest,Closed,Rejected"', allow_blank=True)
dl.add_data_validation(dv2)
dv2.add("L2:L201")

# ------------------------------------------------------------------ Summary
sm = wb.create_sheet("Summary", 1)
sm["A1"] = "UAT progress"
sm["A1"].font = Font(name=FONT, size=14, bold=True, color="1F4E79")
sm["A2"] = "Counts come from the Status column of the Test Cases sheet and update as it is filled in."
sm["A2"].font = Font(name=FONT, size=9, italic=True)
head = ["Area", "Cases", "Pass", "Fail", "Blocked", "Not run", "% executed", "% passed"]
for i, h in enumerate(head, 1):
    sm.cell(row=4, column=i, value=h)
style_header(sm, 4, [30, 9, 9, 9, 9, 9, 11, 11])
TC = "'Test Cases'"
first = 5
for i, area in enumerate(AREA_NAMES):
    r = first + i
    sm.cell(row=r, column=1, value=area)
    sm.cell(row=r, column=2, value=f"=COUNTIFS({TC}!$B$2:$B${last_tc},$A{r})")
    for col, status in zip(range(3, 7), ["Pass", "Fail", "Blocked", "Not run"]):
        sm.cell(row=r, column=col, value=f'=COUNTIFS({TC}!$B$2:$B${last_tc},$A{r},{TC}!$P$2:$P${last_tc},"{status}")')
    sm.cell(row=r, column=7, value=f"=IFERROR((C{r}+D{r}+E{r})/B{r},0)")
    sm.cell(row=r, column=8, value=f"=IFERROR(C{r}/B{r},0)")
total = first + len(AREA_NAMES)
sm.cell(row=total, column=1, value="All areas")
for col in range(2, 7):
    L = get_column_letter(col)
    sm.cell(row=total, column=col, value=f"=SUM({L}{first}:{L}{total - 1})")
sm.cell(row=total, column=7, value=f"=IFERROR((C{total}+D{total}+E{total})/B{total},0)")
sm.cell(row=total, column=8, value=f"=IFERROR(C{total}/B{total},0)")
hp = total + 1
sm.cell(row=hp, column=1, value="High priority only")
sm.cell(row=hp, column=2, value=f'=COUNTIFS({TC}!$F$2:$F${last_tc},"High")')
for col, status in zip(range(3, 7), ["Pass", "Fail", "Blocked", "Not run"]):
    sm.cell(row=hp, column=col, value=f'=COUNTIFS({TC}!$F$2:$F${last_tc},"High",{TC}!$P$2:$P${last_tc},"{status}")')
sm.cell(row=hp, column=7, value=f"=IFERROR((C{hp}+D{hp}+E{hp})/B{hp},0)")
sm.cell(row=hp, column=8, value=f"=IFERROR(C{hp}/B{hp},0)")
for row in sm.iter_rows(min_row=first, max_row=hp, max_col=8):
    for cell in row:
        body(cell, bold=cell.row >= total or cell.column == 1)
        if cell.column >= 7:
            cell.number_format = "0%"
        if cell.row >= total:
            cell.fill = SOFT

d0 = hp + 3
sm.cell(row=d0 - 1, column=1, value="Open defects by severity").font = Font(name=FONT, size=12, bold=True, color="1F4E79")
for i, h in enumerate(["Severity", "Open", "All raised"], 1):
    sm.cell(row=d0, column=i, value=h)
style_header(sm, d0, [30, 9, 9])
for i, sev in enumerate(["Critical", "High", "Medium", "Low"], 1):
    r = d0 + i
    sm.cell(row=r, column=1, value=sev)
    sm.cell(row=r, column=2, value=f"=COUNTIFS('Defect Log'!$E$3:$E$201,$A{r},'Defect Log'!$L$3:$L$201,\"<>Closed\",'Defect Log'!$L$3:$L$201,\"<>Rejected\")")
    sm.cell(row=r, column=3, value=f"=COUNTIFS('Defect Log'!$E$3:$E$201,$A{r})")
    for col in range(1, 4):
        body(sm.cell(row=r, column=col), bold=col == 1)
note = sm.cell(row=d0 + 6, column=1, value="Row 2 of the Defect Log is the example and is not counted. Acceptance: every High-priority case passes and no Critical or High defect is open.")
note.font = Font(name=FONT, size=9, italic=True)

# ------------------------------------------------------------------ Accounts
ac = wb.create_sheet("Accounts")
head = ["Person", "Sign in as", "Role", "Where", "What they do"]
ac.append(head)
style_header(ac, 1, [16, 34, 28, 14, 80])
ACCOUNTS = [
    ["Priya Menon", "dpo@cmp.local", "DPO (Data Protection Officer)", "Console", "Runs the Privacy Office: purposes, notices, approvals, rights requests, audit, legal holds, restricted countries."],
    ["System Admin", "admin@cmp.local", "Administrator", "Console", "Creates staff accounts and sets roles; reviews grievances about the DPO."],
    ["Kavya Rao", "rnd@cmp.local", "R&D User", "Console", "Registers research projects, brings the notice, submits for approval."],
    ["Nikhil Bose", "dcoadmin@cmp.local", "DCO Admin", "Console", "Routes approved third-party projects: assigns data sources and a DCO."],
    ["Arun Shetty", "dco@cmp.local", "DCO (Data Collection Owner)", "Console", "Runs collection sites: consent links, exports, imports."],
    ["Meera Iyer", "rco@cmp.local", "RCO (R&D Collection Owner)", "Console", "Runs in-house collection; answers rights tickets addressed to in-house teams."],
    ["Anjali Verma", "subject@cmp.local / +91 90000 00001", "Data principal", "Portal", "Gives and withdraws consent, raises rights requests. No password - one-time code."],
]
for a in ACCOUNTS:
    ac.append(a)
for row in ac.iter_rows(min_row=2, max_row=ac.max_row):
    for cell in row:
        body(cell, bold=cell.column == 1)
ac.cell(row=ac.max_row + 2, column=1, value="Staff password").font = Font(name=FONT, size=10, bold=True)
ac.cell(row=ac.max_row, column=2, value="SeedPassw0rd!2026 (test environment only)").font = Font(name=FONT, size=10)

for sheet in wb.worksheets:
    sheet.sheet_view.zoomScale = 100
wb.calculation.fullCalcOnLoad = True
wb.save(OUT)
print(f"wrote {OUT}: {len(cases)} cases, {last_ts - 1} steps")
