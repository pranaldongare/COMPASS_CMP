"""Builds OVS.json - Oversight UAT cases. Labels verified against frontend/console/src,
frontend/portal/src and backend/api/src/cmp (dashboard.py, permissions.py, audit vocabulary)."""
import json

PW = "SeedPassw0rd!2026"
CONSOLE = "http://localhost:3000"
PORTAL = "http://localhost:3001"
FRESH = ("Use a fresh private/incognito browser window in which nobody is signed in to the console "
         "or the portal (both sites share one sign-in on this machine).")
WIDE = ("Keep the browser window at least 1024 pixels wide so the left-hand sidebar is always shown "
        "(on a narrower window the sidebar is behind the 'Open navigation' menu button at top left).")
CODES = "The test coordinator can read the test outbox and relay the six-digit sign-in code."


def sign_in(email, first, badge):
    return {
        "action": (f"Open {CONSOLE}. Type {email} in 'Email or username' and {PW} in 'Password', click "
                   "'Sign in'. On the 'Verify it is you' page type the six-digit code the test coordinator "
                   "relays into '6-digit code' and click 'Verify and continue'."),
        "expected": (f"You land on the Dashboard with the heading 'Good day, {first}'. The top right of the "
                     f"header shows the person's name with the role badge '{badge}'."),
    }


def sign_out_in(email, first, badge):
    return {
        "action": (f"Click 'Sign out' at the bottom of the sidebar. Then sign in again as {email} "
                   f"(password {PW}, code from the coordinator, 'Verify and continue')."),
        "expected": f"The Dashboard opens with the heading 'Good day, {first}' and the role badge '{badge}'.",
    }


NOT_PART = ("The sidebar and header are still shown, but the main area shows only an information box "
            "titled 'Not part of your account' with the text 'This section belongs to a different role, "
            "so there is nothing here for you. Nothing has gone wrong — the link you followed pointed at a "
            "staff console.' and a 'Back to your dashboard' button. No part of the other role's screen "
            "(no table, filters, buttons or data) is shown.")

cases = []


def case(**kw):
    kw.setdefault("area", "Oversight and audit")
    kw.setdefault("ref", "Core")
    cases.append(kw)


# ---------------------------------------------------------------- dashboards
case(
    id="OVS-01",
    title="DPO dashboard lists only work the DPO can act on",
    feature="Dashboard - 'Needs you today', queues, recent activity",
    role="DPO on console",
    priority="High",
    type="Positive",
    preconditions=[FRESH, WIDE, CODES,
                   "Seed data is loaded (projects, notices, consents and rights requests exist)."],
    test_data=["Email or username: dpo@cmp.local (Priya Menon)", f"Password: {PW}"],
    steps=[
        sign_in("dpo@cmp.local", "Priya", "DPO"),
        {"action": "Read the line under the heading.",
         "expected": "It reads 'Notices awaiting publication, projects awaiting your review, and the consent position across the platform.'"},
        {"action": "Look at the first card, 'Needs you today'.",
         "expected": ("Each row shows a number, a label and an arrow, and the card's top right says how many things there are (e.g. '3 things'). "
                      "Every label is one of: 'Tickets past their date', 'Rights requests overdue', 'Rights requests due within 7 days', "
                      "'Requests awaiting verification', 'Teams have written on their tickets', 'Grievances about the DPO to escalate', "
                      "'Retention floors passed, erasure due', 'Tickets addressed to you', 'Notice text awaiting approval', "
                      "'Projects pending approval', 'New collectors awaiting your decision'. If nothing is waiting the card says "
                      "'Nothing needs you today. The queues below are clear or waiting on somebody else.'")},
        {"action": "Check the card for rows that belong to other roles.",
         "expected": ("There is no row about lockouts, sign-ins, access denials, 'Staff invitations not yet accepted', "
                      "'Sites awaiting a data source', 'Sources with nobody accountable' or 'Imports that did not reconcile'.")},
        {"action": "Click one of the rows in 'Needs you today' (for example 'Projects pending approval' or 'Rights requests due within 7 days').",
         "expected": ("The list behind that number opens already filtered (e.g. the Projects page showing only projects pending approval, or the "
                      "Rights requests page). The number of rows matches the count on the dashboard. Use the browser Back button to return.")},
        {"action": "Scroll down past 'Needs you today' to the queue cards.",
         "expected": ("Queues with work appear as cards named from: 'Rights requests, soonest due first', 'Tickets past their date', "
                      "'Teams have written on their tickets', 'Drafts whose purposes are not activated', 'Pending Approval', "
                      "'New collectors awaiting your decision', 'Retention floors passed - erasure due'. Each card shows a count badge. "
                      "Empty queues are listed together in one grey line that starts 'Clear:'. People's names in queue rows are readable.")},
        {"action": "Scroll further to the cards 'Projects by stage' and 'Consent position'.",
         "expected": ("'Projects by stage' shows bars labelled 'In draft', 'Pending approval' and 'Approved' with numbers; "
                      "'Consent position' shows one bar split into 'Agreed to all purposes', 'Agreed to some', 'Declined' and 'Withdrawn' with the caption "
                      "'Every record counted once, at its current state.'")},
        {"action": "Look at the 'Recent activity' card at the bottom.",
         "expected": ("Up to 8 entries, newest first, each with an event name, a time, who did it (name and role badge) and the record it concerns. "
                      "No sign-in events (titles starting 'Auth ...') are listed. A 'Full audit trail' link is at the card's top right.")},
        {"action": "Click 'Full audit trail'.",
         "expected": "The 'Audit trail' page opens."},
    ],
    pass_criteria=("'Needs you today' contains only DPO-actionable rows from the listed set, each row opens a filtered list that matches its count, "
                   "queues and position cards render, and Recent activity shows no sign-in events and links to the full audit trail."),
)

case(
    id="OVS-02",
    title="Administrator dashboard - lockouts are information, not tasks",
    feature="Dashboard - 'Needs you today', queues, recent activity",
    role="Administrator on console",
    priority="High",
    type="Positive",
    preconditions=[FRESH, WIDE, CODES,
                   "Ideally a staff account was locked out in the last 24 hours (see OVS-10 preconditions) so the 'Lockouts (24h)' queue has a row."],
    test_data=["Email or username: admin@cmp.local (System Admin)", f"Password: {PW}"],
    steps=[
        sign_in("admin@cmp.local", "System", "Administrator"),
        {"action": "Read the line under the heading.",
         "expected": "It reads 'Accounts, lockouts, and the state of the processor and source registry.'"},
        {"action": "Look at 'Needs you today'.",
         "expected": ("Only these labels can appear (each only when its count is above zero): 'Staff invitations not yet accepted', "
                      "'Grievances about the DPO to review', 'Tickets addressed to you'. Otherwise the card says "
                      "'Nothing needs you today. The queues below are clear or waiting on somebody else.'")},
        {"action": "Check 'Needs you today' for rows the administrator cannot act on.",
         "expected": ("There is no row about lockouts, access denials, consent withdrawals, projects, notices, or rights requests overdue.")},
        {"action": "If 'Staff invitations not yet accepted' is shown, click it.",
         "expected": ("The 'Users' page opens filtered to pending accounts; it lists staff whose invitation is not yet accepted and no data principals. "
                      "Use Back to return. (If the row is absent, note 'no pending invitations' and continue.)")},
        {"action": "Scroll to the queue cards and the 'Clear:' line.",
         "expected": ("The queues are 'Grievances about the DPO - yours to review', 'Lockouts (24h)' and 'Suspended sources and processors' "
                      "(as cards, or named in the 'Clear:' line when empty). A lockout from the last 24 hours appears as a row in 'Lockouts (24h)' "
                      "with the person's readable name - here, and not in 'Needs you today'.")},
        {"action": "Look for the cards 'Projects by stage' and 'Consent position'.",
         "expected": "Neither card is shown to the administrator."},
        {"action": "Look at 'Recent activity'.",
         "expected": ("Entries are refused requests - title 'Auth access denied' with the sentence 'A request was refused by the permission matrix.' - "
                      "each with who and when. A 'Full audit trail' link is at the card's top right.")},
    ],
    pass_criteria=("Administrator 'Needs you today' holds only invitations, grievances about the DPO and own tickets; lockouts appear only in the "
                   "'Lockouts (24h)' queue; no project or consent charts; Recent activity shows access denials with a 'Full audit trail' link."),
)

case(
    id="OVS-03",
    title="DCO and RCO dashboards show their collection work and no audit link",
    feature="Dashboard - 'Needs you today', queues, recent activity",
    role="DCO and RCO on console",
    priority="High",
    type="Positive",
    preconditions=[FRESH, WIDE, CODES],
    test_data=["dco@cmp.local (Arun Shetty)", "rco@cmp.local (Meera Iyer)", f"Password: {PW}"],
    steps=[
        sign_in("dco@cmp.local", "Arun", "Data Collection Owner"),
        {"action": "Read the line under the heading, then look at 'Needs you today'.",
         "expected": ("The line reads 'Your approved projects, the links collecting against them, and anything that failed to reconcile on import.' "
                      "'Needs you today' holds only rows from: 'Tickets past their date', 'Tickets addressed to you', 'Imports that did not reconcile', "
                      "'Assets with unmapped subjects' - or the sentence 'Nothing needs you today. ...'.")},
        {"action": "Check 'Needs you today' for rows belonging to other roles.",
         "expected": ("No 'Projects pending approval', 'Rights requests overdue', 'Notice text awaiting approval', 'Staff invitations not yet accepted', "
                      "lockout or 'Sites awaiting a data source' row appears.")},
        {"action": "Find the 'Import exceptions' queue (a card, or named in the 'Clear:' line). If it is a card, click its first row.",
         "expected": ("A card row names a collection and a project and says '<n> declared, <m> mapped — <k> unaccounted for'. Clicking it opens that "
                      "collection's page (not 'Not part of your account'). Use Back to return.")},
        {"action": "Look at the 'Recent activity' card.",
         "expected": ("It lists events on Arun's own projects or done by him, with no sign-in ('Auth ...') events. There is NO 'Full audit trail' link "
                      "on the card, because a DCO has no audit page.")},
        sign_out_in("rco@cmp.local", "Meera", "R&D Collection Owner"),
        {"action": "Read the line under the heading and 'Needs you today'.",
         "expected": ("The line reads 'The collection your team runs itself — your approved projects, the links collecting against them, and anything that "
                      "failed to reconcile on import.' 'Needs you today' uses the same four DCO labels only.")},
        {"action": "Look at the 'Recent activity' card.",
         "expected": "Events on Meera's projects only, no sign-in events, and no 'Full audit trail' link."},
    ],
    pass_criteria="Both collection owners see only their four kinds of actionable row, their own import exceptions, and a Recent activity feed without a 'Full audit trail' link.",
)

case(
    id="OVS-04",
    title="DCO Admin and R&D User dashboards show only their own queues",
    feature="Dashboard - 'Needs you today', queues, recent activity",
    role="DCO Admin and R&D User on console",
    priority="Medium",
    type="Positive",
    preconditions=[FRESH, WIDE, CODES],
    test_data=["dcoadmin@cmp.local (Nikhil Bose)", "rnd@cmp.local (Kavya Rao)", f"Password: {PW}"],
    steps=[
        sign_in("dcoadmin@cmp.local", "Nikhil", "DCO Admin"),
        {"action": "Read the line under the heading and look at 'Needs you today'.",
         "expected": ("The line reads 'Projects collected by a third party: which sites are still waiting for a data source, and who picks them up when you "
                      "attach one.' Rows come only from: 'Tickets past their date', 'Sites awaiting a data source', 'Sources with nobody accountable', "
                      "'Processors with no collection set up', 'Tickets addressed to you'.")},
        {"action": "If 'Sites awaiting a data source' is listed, click it.",
         "expected": ("The page scrolls down to the 'Sites awaiting a data source' queue card on the same dashboard; each row names a project and says "
                      "'Attach the data source that will collect here'.")},
        {"action": "If 'Sources with nobody accountable' is listed, click it.",
         "expected": "The 'Data sources' page opens (not 'Not part of your account'). Use Back to return."},
        {"action": "Look at 'Recent activity'.",
         "expected": "No sign-in events and no 'Full audit trail' link."},
        sign_out_in("rnd@cmp.local", "Kavya", "R&D User"),
        {"action": "Read the line under the heading and look at 'Needs you today'.",
         "expected": ("The line reads 'Your projects and what each one needs from you before it can move forward.' Rows come only from "
                      "'Projects needing something from you' and 'Tickets addressed to you'.")},
        {"action": "If 'Projects needing something from you' is listed, click it, then click the first row of the queue it jumps to.",
         "expected": ("The page scrolls to the 'Needs your action' queue; rows name Kavya's draft projects with 'Upload a security approval with its proof file'. "
                      "Clicking a row opens that project's page.")},
        {"action": "Scroll to the bottom of the dashboard.",
         "expected": ("'Projects by stage' is shown (counting only Kavya's projects); there is no 'Consent position' card; 'Recent activity' has no "
                      "'Full audit trail' link.")},
    ],
    pass_criteria="Each role sees only its own attention rows and queues, links open pages the role can use, and neither role is offered the full audit trail.",
)

# ---------------------------------------------------------------- sidebars
case(
    id="OVS-05",
    title="Sidebar for the DPO and the Administrator",
    feature="Role-based navigation",
    role="DPO and Administrator on console",
    priority="High",
    type="Positive",
    preconditions=[FRESH, WIDE, CODES],
    test_data=["dpo@cmp.local (Priya Menon)", "admin@cmp.local (System Admin)", f"Password: {PW}"],
    steps=[
        sign_in("dpo@cmp.local", "Priya", "DPO"),
        {"action": "Read the whole left-hand sidebar from top to bottom (section headings are shown in small capitals).",
         "expected": ("In this order: OVERVIEW - Dashboard; GOVERNANCE - Projects, Approvals, Notices, Purposes; CONSENT - Consents, Consent links, "
                      "Collection sites; REGISTRY - Processors, Data sources; DATA MOVEMENT - Collections, Exports, Imports; OVERSIGHT - Rights requests, "
                      "Audit trail, Users, Delegate, Messages; YOU - Tickets for you, Notifications, Your profile. A 'Sign out' button sits at the bottom.")},
        {"action": "Click each sidebar link in turn.",
         "expected": ("Every link opens a page with its own heading. None shows 'This page could not be found' or 'Not part of your account'. "
                      "The link for the open page is highlighted.")},
        sign_out_in("admin@cmp.local", "System", "Administrator"),
        {"action": "Read the whole sidebar.",
         "expected": ("OVERVIEW - Dashboard; REGISTRY - Processors, Data sources; OVERSIGHT - Grievances about the DPO, Audit trail, Users, Delegate, "
                      "Messages; YOU - Tickets for you, Notifications, Your profile.")},
        {"action": "Check what is absent for the administrator.",
         "expected": ("There are no GOVERNANCE, CONSENT or DATA MOVEMENT headings and no links to Projects, Approvals, Notices, Purposes, Consents, "
                      "Consent links, Collection sites, Collections, Exports or Imports. There is no 'Rights requests' link - that slot reads "
                      "'Grievances about the DPO'.")},
        {"action": "Click 'Grievances about the DPO'.",
         "expected": "A page headed 'Grievances about the DPO' opens."},
        {"action": "Click each remaining administrator link in turn.",
         "expected": "Every link opens a page with its own heading; none shows 'This page could not be found' or 'Not part of your account'."},
    ],
    pass_criteria="The DPO sees all 21 links in 7 sections; the Administrator sees exactly the 11 links listed, with the rights link relabelled 'Grievances about the DPO', and every link opens.",
)

case(
    id="OVS-06",
    title="Sidebar for DCO, DCO Admin and RCO has no Audit trail",
    feature="Role-based navigation",
    role="DCO, DCO Admin and RCO on console",
    priority="High",
    type="Negative",
    preconditions=[FRESH, WIDE, CODES],
    test_data=["dco@cmp.local (Arun Shetty)", "dcoadmin@cmp.local (Nikhil Bose)", "rco@cmp.local (Meera Iyer)", f"Password: {PW}"],
    steps=[
        sign_in("dco@cmp.local", "Arun", "Data Collection Owner"),
        {"action": "Read the whole sidebar.",
         "expected": ("OVERVIEW - Dashboard; GOVERNANCE - Projects; CONSENT - Consents, Consent links, Collection sites; REGISTRY - Data sources; "
                      "DATA MOVEMENT - Collections, Exports, Imports; OVERSIGHT - Delegate; YOU - Tickets for you, Notifications, Your profile.")},
        {"action": "Look under OVERSIGHT and the rest of the sidebar for oversight and governance links.",
         "expected": ("OVERSIGHT holds only 'Delegate'. There is no 'Audit trail', 'Users', 'Rights requests' or 'Messages', and no 'Approvals', "
                      "'Notices', 'Purposes' or 'Processors' anywhere in the sidebar.")},
        {"action": "Click each sidebar link in turn.",
         "expected": "Every link opens a page with its own heading; none shows 'This page could not be found' or 'Not part of your account'."},
        sign_out_in("dcoadmin@cmp.local", "Nikhil", "DCO Admin"),
        {"action": "Read the whole sidebar and repeat the check for absent links.",
         "expected": "Exactly the same links as the DCO; no 'Audit trail', 'Users', 'Rights requests', 'Messages', 'Approvals', 'Notices', 'Purposes' or 'Processors'."},
        sign_out_in("rco@cmp.local", "Meera", "R&D Collection Owner"),
        {"action": "Read the whole sidebar and repeat the check for absent links.",
         "expected": "Exactly the same links as the DCO; no 'Audit trail' and none of the other absent links."},
    ],
    pass_criteria="All three collection roles see the same 13 links, OVERSIGHT contains only 'Delegate', and no audit, user, rights, message, approval, notice, purpose or processor link is offered.",
)

case(
    id="OVS-07",
    title="Sidebar for the R&D User",
    feature="Role-based navigation",
    role="R&D User on console",
    priority="High",
    type="Positive",
    preconditions=[FRESH, WIDE, CODES],
    test_data=["rnd@cmp.local (Kavya Rao)", f"Password: {PW}"],
    steps=[
        sign_in("rnd@cmp.local", "Kavya", "R&D User"),
        {"action": "Read the whole sidebar.",
         "expected": ("OVERVIEW - Dashboard; GOVERNANCE - Projects, Approvals, Notices; REGISTRY - Processors; DATA MOVEMENT - Collections, Imports; "
                      "YOU - Tickets for you, Notifications, Your profile.")},
        {"action": "Check what is absent.",
         "expected": ("There is no CONSENT heading and no OVERSIGHT heading. There are no links to Purposes, Consents, Consent links, Collection sites, "
                      "Data sources, Exports, Rights requests, Audit trail, Users, Delegate or Messages.")},
        {"action": "Click 'Notices'.",
         "expected": "A page headed 'Notices' opens (the R&D User authors notices)."},
        {"action": "Click each remaining sidebar link in turn.",
         "expected": "Every link opens a page with its own heading; none shows 'This page could not be found' or 'Not part of your account'."},
    ],
    pass_criteria="The R&D User sees exactly the 10 links listed, no Consent or Oversight section, and every link opens.",
)

# ---------------------------------------------------------------- not part of your account
case(
    id="OVS-08",
    title="Following a link to another role's section shows 'Not part of your account'",
    feature="Section guard on the console",
    role="DCO, R&D User, Administrator and RCO on console",
    priority="High",
    type="Negative",
    preconditions=[FRESH, WIDE, CODES,
                   "Optional: a DPO has copied an audit link from a record page (OVS-17 step 2) to paste in step 4."],
    test_data=["dco@cmp.local", "rnd@cmp.local", "admin@cmp.local", "rco@cmp.local", f"Password: {PW}",
               f"Addresses to type: {CONSOLE}/audit, /users, /notices, /consents, /exports, /projects, /approvals"],
    steps=[
        sign_in("dco@cmp.local", "Arun", "Data Collection Owner"),
        {"action": f"In the browser address bar type {CONSOLE}/audit and press Enter.",
         "expected": NOT_PART + " There is no 'Export CSV' button, no filters and no audit entries."},
        {"action": f"Type {CONSOLE}/users and press Enter, then {CONSOLE}/notices.",
         "expected": "Both show the same 'Not part of your account' box instead of the account register or the notices list."},
        {"action": (f"Type {CONSOLE}/audit?event_group=consent (or paste the audit link a DPO copied from a record page) and press Enter."),
         "expected": "The same 'Not part of your account' box; no pre-filtered entries or chips are shown."},
        {"action": "Click 'Back to your dashboard'.",
         "expected": "Arun's Dashboard opens normally."},
        sign_out_in("rnd@cmp.local", "Kavya", "R&D User"),
        {"action": f"Type {CONSOLE}/consents, then {CONSOLE}/exports, then {CONSOLE}/audit.",
         "expected": "Each shows the 'Not part of your account' box; no consent register, export list or audit trail is shown."},
        sign_out_in("admin@cmp.local", "System", "Administrator"),
        {"action": f"Type {CONSOLE}/projects, then {CONSOLE}/consents.",
         "expected": "Each shows the 'Not part of your account' box."},
        {"action": f"Sign out, sign in as rco@cmp.local, and type {CONSOLE}/approvals. Then type {CONSOLE}/sites.",
         "expected": ("/approvals shows the 'Not part of your account' box. /sites (which IS in Meera's sidebar as 'Collection sites') opens normally - "
                      "the guard only blocks sections the role does not have.")},
    ],
    pass_criteria="Every address outside the role's sidebar shows only the 'Not part of your account' box with 'Back to your dashboard', never another role's screen or data; allowed sections still open.",
)

# ---------------------------------------------------------------- notifications
LOCK_PRE = ("Within the last 24 hours a staff account was locked out: the coordinator enters a wrong password five times on the console for an "
            "account nobody needs for the next 30 minutes (for example rco@cmp.local after the RCO cases are finished). The lock lifts by itself after 30 minutes.")
WD_PRE = ("At least one consent withdrawal exists (as the DPO, 'Consents' with 'Status' set to 'Withdrawn' shows at least one row).")

case(
    id="OVS-09",
    title="DPO notifications include withdrawals and lockouts and every link opens",
    feature="Notifications (staff)",
    role="DPO on console",
    priority="High",
    type="Positive",
    preconditions=[FRESH, WIDE, CODES, LOCK_PRE, WD_PRE],
    test_data=["dpo@cmp.local (Priya Menon)", f"Password: {PW}"],
    steps=[
        sign_in("dpo@cmp.local", "Priya", "DPO"),
        {"action": "In the sidebar under YOU, click 'Notifications' (the bell icon).",
         "expected": ("A page headed 'Notifications' opens with the text 'What has happened that concerns you, taken from the audit trail itself.' "
                      "Entries are listed newest first; each shows an event name, how long ago, a one-line explanation, the record it concerns as a link, "
                      "and 'by <name>'.")},
        {"action": "Find an entry titled 'Consent withdrawn'.",
         "expected": ("Its explanation reads 'Consent was withdrawn. The earlier record still stands as evidence of what was agreed at the time.' "
                      "Its record link reads 'Consent record: <person's name> — <project>' with the name readable.")},
        {"action": "Find an entry titled 'Auth login locked out' (from the precondition).",
         "expected": ("Its explanation reads 'An account was locked after repeated failed sign-ins.' and its record link reads 'Account: <name of the locked account>'.")},
        {"action": "Click the body of the 'Consent withdrawn' entry (not the link).",
         "expected": ("A dialog titled 'Consent withdrawn' opens showing 'What', 'When', 'Who', 'About', 'Event' (consent.withdrawn) and 'Record', "
                      "the note 'This entry is append-only and part of a hash chain. ...', and the buttons 'Open consent record' and 'Close'.")},
        {"action": "Click 'Open consent record'.",
         "expected": ("The consent record page opens, headed with the person's name and an 'All consents' back link - not 'Not part of your account' "
                      "and not 'This page could not be found'.")},
        {"action": "Go back to 'Notifications' and click the 'Account: ...' link on the lockout entry.",
         "expected": "The 'Users' page opens."},
        {"action": "Go back and click the record link on one entry of each other kind shown (e.g. 'Project transitioned', 'Notice published', 'Import rejected', 'Export generated', ticket events).",
         "expected": "Each link opens a page the DPO can use; none shows 'Not part of your account' or 'This page could not be found'."},
    ],
    pass_criteria="The DPO's feed contains both consent withdrawals and lockouts, each entry opens a detail dialog, and every link opens a working page.",
)

case(
    id="OVS-10",
    title="Administrator notifications show lockouts but not consent withdrawals",
    feature="Notifications (staff)",
    role="Administrator on console",
    priority="High",
    type="Negative",
    preconditions=[FRESH, WIDE, CODES, LOCK_PRE, WD_PRE,
                   "OVS-09 has confirmed that the DPO's feed shows a 'Consent withdrawn' entry."],
    test_data=["admin@cmp.local (System Admin)", f"Password: {PW}"],
    steps=[
        sign_in("admin@cmp.local", "System", "Administrator"),
        {"action": "In the sidebar under YOU, click 'Notifications'.",
         "expected": "The 'Notifications' page opens."},
        {"action": "Find the 'Auth login locked out' entry for the account locked in the precondition.",
         "expected": "It is listed with 'An account was locked after repeated failed sign-ins.' and the link 'Account: <name>'."},
        {"action": "Scroll the whole list looking for 'Consent withdrawn'.",
         "expected": "There is no 'Consent withdrawn' entry at all, even though the DPO sees one."},
        {"action": "Scroll the list looking for project events.",
         "expected": ("There are no 'Project transitioned', 'Notice published', 'Import rejected' or 'Export generated' entries - the administrator "
                      "cannot open projects. Only lockouts and events on tickets addressed to the administrator appear (or 'Nothing to report' if none).")},
        {"action": "Click the 'Account: <name>' link on the lockout entry.",
         "expected": "The 'Users' page opens (a page the administrator can use)."},
        {"action": "Go back, click the body of the lockout entry, then 'Close'.",
         "expected": "A dialog titled 'Auth login locked out' shows 'What', 'When', 'Who', 'Event' (auth.login_locked_out) and 'Record'; 'Close' dismisses it."},
    ],
    pass_criteria="The administrator sees lockouts and never consent withdrawals or project events, and the lockout link opens the Users page.",
)

case(
    id="OVS-11",
    title="DCO and R&D User notifications cover only projects they can see",
    feature="Notifications (staff)",
    role="DCO and R&D User on console",
    priority="High",
    type="Negative",
    preconditions=[FRESH, WIDE, CODES, LOCK_PRE, WD_PRE],
    test_data=["dco@cmp.local (Arun Shetty)", "rnd@cmp.local (Kavya Rao)", f"Password: {PW}"],
    steps=[
        sign_in("dco@cmp.local", "Arun", "Data Collection Owner"),
        {"action": "Click 'Notifications' in the sidebar and read the list.",
         "expected": ("Entries are only of these kinds: 'Project transitioned', 'Notice published', 'Import rejected', 'Export generated', plus events on "
                      "tickets addressed to Arun. Each names a project (or a notice, import or export on one).")},
        {"action": "Look for 'Consent withdrawn' and 'Auth login locked out' entries.",
         "expected": "Neither appears, although the DPO's feed shows both."},
        {"action": "Note the project named on two entries, then click 'Projects' in the sidebar.",
         "expected": "Both projects are in Arun's Projects list - no entry concerns a project he cannot see."},
        {"action": "Back on 'Notifications', click a 'Project: <name>' link, then an 'Export' link on an 'Export generated' entry (if present).",
         "expected": "The project page and the 'Exports' page open normally."},
        {"action": "If a 'Notice published' entry is present, click its 'Notice: ...' link (or 'Open notice' in its dialog).",
         "expected": ("A page Arun can use opens. It must NOT show 'Not part of your account' (the rule is that no notification link leads to a page the "
                      "reader cannot open). If it does, record a defect.")},
        sign_out_in("rnd@cmp.local", "Kavya", "R&D User"),
        {"action": "Click 'Notifications' and read the list.",
         "expected": "Only events on projects Kavya created (and her tickets); no 'Consent withdrawn' and no 'Auth login locked out'."},
        {"action": "Click the record link on each entry shown, including any 'Export generated' entry's 'Export' link.",
         "expected": ("Each opens a page Kavya can use. None may show 'Not part of your account' (R&D Users have no Exports section, so an export link "
                      "that lands there is a defect).")},
    ],
    pass_criteria="Scoped roles see only events on projects in their own register, never withdrawals or lockouts, and no notification link lands on 'Not part of your account'.",
)

# ---------------------------------------------------------------- audit trail
case(
    id="OVS-12",
    title="Filter the audit trail by area, event, actor role, record type and period",
    feature="Audit trail - filters and chips",
    role="DPO on console",
    priority="High",
    type="Positive",
    preconditions=[FRESH, WIDE, CODES],
    test_data=["dpo@cmp.local (Priya Menon)", f"Password: {PW}", "Area: Sign-in and access; Event: Access denied; Actor role: Admin; Record type: Project; From/To: today's date"],
    steps=[
        sign_in("dpo@cmp.local", "Priya", "DPO"),
        {"action": "Click 'Audit trail' under OVERSIGHT in the sidebar.",
         "expected": ("The page headed 'Audit trail' opens with the text 'Append-only and hash-chained. Nothing here can be edited or deleted by anyone, "
                      "including the Privacy Office. Ask it a question: about a person, a record, an area, a period.' Buttons 'Export CSV' and "
                      "'Verify chain' are at the top right. The filter panel has 'Search', 'About', 'Name, email or mobile', 'Area', 'Event', "
                      "'Record type', 'Actor role', 'From' and 'To'. The table has the columns 'When', 'Event', 'Actor', 'About', 'Record'. "
                      "There is no edit or delete control anywhere.")},
        {"action": "In 'Area' choose 'Sign-in and access'.",
         "expected": ("A 'Filtered by' strip appears with the chip 'Area Sign-in and access'. Every row's Event starts with 'Auth' "
                      "(e.g. 'Auth login succeeded'). The address bar now contains event_group=auth.")},
        {"action": "Open 'Event'.",
         "expected": "The first option reads 'Every event in this area' and the list holds only sign-in and access events (e.g. 'Access denied', 'Login failed', 'Login locked out')."},
        {"action": "Choose 'Access denied'.",
         "expected": ("The chip changes to 'Event Access denied' (the Area chip is replaced). Every row is 'Auth access denied' with the line "
                      "'A request was refused by the permission matrix.'")},
        {"action": "Click the small x on the 'Event' chip. Then in 'Actor role' choose 'Admin'.",
         "expected": "The Event filter is removed. A chip 'Actor role Admin' appears and every row's Actor carries the badge 'Administrator'."},
        {"action": "In 'Record type' choose 'Project'.",
         "expected": ("A second chip 'Record type Project' appears next to 'Actor role Admin', and a 'Clear all' button appears. Every row's Record reads "
                      "'Project: <name>' (or 'Nothing matches these filters' if the administrator never touched a project).")},
        {"action": "Click 'Clear all'. Then set 'From' and 'To' to today's date.",
         "expected": "All earlier chips disappear. Chips 'From <date>' and 'To <date>' appear and every row's 'When' falls on today."},
        {"action": "Copy the address from the address bar, open a new tab, paste it and press Enter.",
         "expected": "The new tab shows the same filters, the same chips and the same rows - the question can be bookmarked or shared."},
        {"action": "Remove the 'From' chip only, using its x.",
         "expected": "Only the From filter is removed; the 'To' chip stays. Under the table, 'Showing <n> of <total>' and 'Previous' / 'Next' buttons page through results."},
    ],
    pass_criteria="Each filter narrows the rows as described, shows as a removable chip, combines with others, clears individually or all at once, and survives being shared as a URL.",
)

case(
    id="OVS-13",
    title="About picker finds a person by part of a name or a whole email",
    feature="Audit trail - About picker",
    role="DPO on console",
    priority="High",
    type="Positive",
    preconditions=[FRESH, WIDE, CODES, "The seeded data principal Anjali Verma (subject@cmp.local) exists and has consent events."],
    test_data=["dpo@cmp.local (Priya Menon)", f"Password: {PW}",
               "Search terms: 'Anj', 'Verm', 'subject@cmp.local', 'Priya', 'dco@cmp.local', part of a project name"],
    steps=[
        sign_in("dpo@cmp.local", "Priya", "DPO"),
        {"action": "Click 'Audit trail'. Open the 'About' dropdown.",
         "expected": ("It offers 'Data principal', 'Member of staff', 'Consent record', 'Processor', 'Data source', 'Project', 'Notice', "
                      "'Collection site', 'Rights request'. 'Data principal' is selected and the box beside it is labelled 'Name, email or mobile' "
                      "with the grey hint 'The whole address or number'.")},
        {"action": "With 'Data principal' selected, type Anj (three letters) in 'Name, email or mobile'.",
         "expected": ("A list opens under the box ('Looking…' briefly) and offers 'Anjali Verma' with 'subject@cmp.local' beneath it, both readable. "
                      "Other people whose names contain those letters may also be offered.")},
        {"action": "Click 'Anjali Verma'.",
         "expected": ("The box clears. A chip 'Data principal Anjali Verma' appears under 'Filtered by', every row's 'About' column reads 'Anjali Verma', "
                      "and the summary numbers change to her events only.")},
        {"action": "Remove the chip. Type the middle of her surname, Verm, and pick 'Anjali Verma' again.",
         "expected": "She is offered and the same chip returns - part of a name anywhere in it works."},
        {"action": "Remove the chip. Type her whole email subject@cmp.local.",
         "expected": "'Anjali Verma' is offered; picking her gives the same chip."},
        {"action": "Change 'About' to 'Member of staff' and type Priya, then pick 'Priya Menon'.",
         "expected": ("'Priya Menon' is offered with the hint 'dpo'. After picking, the Data principal chip is replaced by 'Actor Priya Menon' "
                      "(the two are not stacked) and every row's Actor reads 'Priya Menon' with the 'DPO' badge.")},
        {"action": "Still on 'Member of staff', type the whole address dco@cmp.local and pick the answer.",
         "expected": "'Arun Shetty' (hint 'dco') is offered; the chip becomes 'Actor Arun Shetty'."},
        {"action": "Change 'About' to 'Project'.",
         "expected": "The box label changes to 'Name' with the hint 'Type a few letters'. Typing part of a known project name offers matching projects with their status beneath; picking one gives a chip 'Project <name>'."},
    ],
    pass_criteria="Three letters or more of a name, or a whole email, find the person; picking sets exactly one About chip and filters the rows; names are always readable.",
)

case(
    id="OVS-14",
    title="About picker does not match two letters or part of an email",
    feature="Audit trail - About picker",
    role="DPO on console",
    priority="Medium",
    type="Negative",
    preconditions=[FRESH, WIDE, CODES],
    test_data=["dpo@cmp.local", f"Password: {PW}", "Terms: 'An', 'subject@cmp', 'Pr', 'Anjali' (in Search)"],
    steps=[
        sign_in("dpo@cmp.local", "Priya", "DPO"),
        {"action": "Click 'Audit trail'. With 'About' set to 'Data principal', type An (two letters) in 'Name, email or mobile'.",
         "expected": ("The list under the box says 'Nothing by that name.' No one is offered and no filter or chip is applied. "
                      "(Two letters are too few; a name needs three or more. Note: the screen does not currently say 'type more letters' - "
                      "record the wording you see.)")},
        {"action": "Add one letter so the box reads Anj.",
         "expected": "'Anjali Verma' is now offered - the control case works."},
        {"action": "Clear the box and type part of her email: subject@cmp",
         "expected": "'Nothing by that name.' - an email or mobile must be typed whole."},
        {"action": "Change 'About' to 'Member of staff' and type Pr.",
         "expected": "'Nothing by that name.'"},
        {"action": "Clear the About box. Set 'From' to 21 September 2026, type Anjali in 'Search' and click 'Search'.",
         "expected": ("No entry is found by her name through 'Search' ('Nothing matches these filters' / 'Widen the question: remove a filter, or extend "
                      "the dates.'), because Search reads event names and recorded details, which carry no names. Use About to find a person.")},
    ],
    pass_criteria="Two-letter and partial-contact searches offer nobody and apply no filter; the free-text Search never matches a person's name.",
)

case(
    id="OVS-15",
    title="Summary strip, opening an entry and verifying the chain",
    feature="Audit trail - summary, entry detail, Verify chain",
    role="DPO on console",
    priority="Medium",
    type="Positive",
    preconditions=[FRESH, WIDE, CODES],
    test_data=["dpo@cmp.local", f"Password: {PW}", "Area: Consent"],
    steps=[
        sign_in("dpo@cmp.local", "Priya", "DPO"),
        {"action": "Click 'Audit trail' and look at the summary card above the table (no filters set).",
         "expected": ("It shows 'Entries' (a number), 'Span' ('<date> to <date>'), 'Most common event' ('<Area>: <Event> (<count>)') and 'Areas touched' "
                      "(a number), and four panels: 'By area', 'Top events', 'By actor role' and 'Last 30 days · <n> entries', each with bars and numbers.")},
        {"action": "Compare 'Entries' with the line under the table.",
         "expected": "'Showing 50 of <total>' - the total equals 'Entries'."},
        {"action": "In 'Area' choose 'Consent'.",
         "expected": "The summary recalculates: 'Areas touched' is 1, 'By area' lists only 'Consent', and 'Entries' again equals the '<total>' under the table."},
        {"action": "Click any row in the table.",
         "expected": ("A dialog opens titled with the event name (e.g. 'Consent given') and shows 'What', 'When', 'Who' (a name with role badge, or "
                      "'the system — no signed-in user'), 'About' (when a person is concerned), 'Event' (a code such as consent.given) and 'Record' "
                      "(a long id); a 'Recorded details' list; the note 'This entry is append-only and part of a hash chain. Nobody — including the "
                      "Privacy Office — can edit or delete it; the database refuses the statement.' There is no Edit or Delete button.")},
        {"action": "Click 'Show raw JSON', then 'Show as a list'.",
         "expected": "The details switch to raw JSON text and back to the labelled list."},
        {"action": "Click 'Open consent record' in the dialog.",
         "expected": "The consent record page opens. Use Back to return to the filtered audit trail."},
        {"action": "Click 'Verify chain' at the top right.",
         "expected": "A green box titled 'Chain intact' appears reading 'Chain intact across <n> rows.' (A red 'Chain broken' box is a defect to report immediately.)"},
    ],
    pass_criteria="Summary figures match the list for the same filters, an entry opens read-only with a working record link, and Verify chain reports the chain intact.",
)

case(
    id="OVS-16",
    title="Export CSV downloads the filtered rows and the export is itself recorded",
    feature="Audit trail - Export CSV",
    role="DPO on console",
    priority="High",
    type="Positive",
    preconditions=[FRESH, WIDE, CODES, "A spreadsheet program or text editor is available to open the downloaded file."],
    test_data=["dpo@cmp.local", f"Password: {PW}", "Area: Consent"],
    steps=[
        sign_in("dpo@cmp.local", "Priya", "DPO"),
        {"action": "Click 'Audit trail', choose 'Consent' in 'Area' and note the 'Entries' number in the summary.",
         "expected": "Chip 'Area Consent'; the rows are consent events only."},
        {"action": "Click 'Export CSV'.",
         "expected": ("A message 'Audit trail exported' appears with '<audit-trail-YYYYMMDD-HHMM.csv> - the download is itself recorded in the trail.' "
                      "A file with that name is saved to the browser's downloads.")},
        {"action": "Open the file.",
         "expected": ("The first row holds the column names occurred_at, event_type, actor_name, actor_role, subject_name, entity_type, entity_id, "
                      "entity_label, detail, log_uuid. Rows are newest first, every event_type starts 'consent.', and the number of data rows equals "
                      "the 'Entries' number (up to 10,000).")},
        {"action": "Search the file for '@', for a mobile number and for '127.0.0.1'.",
         "expected": "No email address, mobile number or IP address appears anywhere in the file."},
        {"action": "Look at the actor_name and subject_name columns.",
         "expected": ("Names are readable (e.g. 'Anjali Verma') or blank; no cell starts with 'SE::'. If scrambled 'SE::...' text appears, record a defect "
                      "quoting one cell.")},
        {"action": "Back in the console click 'Clear all' (or remove the chip), then choose Area 'Audit trail' and Event 'Exported'.",
         "expected": "The newest row is 'Audit exported' by 'Priya Menon' with the 'DPO' badge, timed at the moment of the download."},
        {"action": "Click that row.",
         "expected": ("The dialog 'Audit exported' shows 'Who' Priya Menon and, under 'Recorded details', 'Rows' equal to the file's data rows and "
                      "'Filters' showing the filter used (event_group consent). 'What' shows 'audit_log#0' with the words 'no longer exists' - the export is "
                      "recorded against the trail itself, which has no page of its own (note this wording as an observation, not a failure).")},
    ],
    pass_criteria="The CSV contains exactly the filtered rows with no contacts or IP addresses, and an 'Audit exported' entry records who exported, when, how many rows and with which filters.",
)

case(
    id="OVS-17",
    title="'Audit trail' button on a record page opens the trail pre-filtered; absent for other roles",
    feature="Audit trail - record-page button",
    role="DPO, then DCO and R&D User on console",
    priority="High",
    type="Positive",
    preconditions=[FRESH, WIDE, CODES, "At least one consent record, project, notice and rights request exist."],
    test_data=["dpo@cmp.local", "dco@cmp.local", "rnd@cmp.local", f"Password: {PW}"],
    steps=[
        sign_in("dpo@cmp.local", "Priya", "DPO"),
        {"action": "Click 'Consents' and click a person's name in the 'Data subject' column (e.g. Anjali Verma).",
         "expected": ("The consent record opens, headed with the person's readable name, '<project> · <site>' underneath, a status badge and an "
                      "'Audit trail' button at the top right.")},
        {"action": "Click 'Audit trail'. Copy the address bar for OVS-08.",
         "expected": ("The Audit trail page opens with the chip 'Consent record <name> — <project>'. The rows are only events on that record (e.g. "
                      "'Consent given'); each Record cell reads 'Consent record: <name> — <project>'; the summary counts only them.")},
        {"action": "Click 'Projects', open any project and click its 'Audit trail' button (next to the status badge).",
         "expected": "The trail opens with the chip 'Project <project name>' and events such as 'Project created' or 'Project transitioned'."},
        {"action": "Click 'Notices', open a notice and click 'Audit trail'.",
         "expected": "The trail opens with the chip 'Notice <code> v<version>'."},
        {"action": "Click 'Rights requests', open a request by its 'Reference' and click 'Audit trail'.",
         "expected": "The trail opens with the chip 'Rights request <reference>'."},
        sign_out_in("dco@cmp.local", "Arun", "Data Collection Owner"),
        {"action": "Click 'Consents', open a record, then open a project from 'Projects'.",
         "expected": "Both pages open, but neither shows an 'Audit trail' button (a DCO has no audit section)."},
        {"action": "Sign out, sign in as rnd@cmp.local and open one of Kavya's projects.",
         "expected": "The project page has no 'Audit trail' button."},
    ],
    pass_criteria="On consent, project, notice and rights-request pages the DPO's 'Audit trail' button opens the trail filtered to that record; DCO and R&D User pages show no such button.",
)

case(
    id="OVS-18",
    title="The audit trail carries no personal words - reasons flagged, addresses hashed",
    feature="Audit trail - no erasable data (ADR 0015)",
    role="DPO on console",
    priority="High",
    type="Negative",
    preconditions=[FRESH, WIDE, CODES,
                   "Since 21 September 2026 at least one project has changed stage, one staff invitation was sent and, ideally, one cover (delegation) was granted. Rows before that date may still hold raw addresses by design, so always filter from 21 September 2026."],
    test_data=["dpo@cmp.local", f"Password: {PW}", "From: 21 September 2026",
               "Search terms: 127.0.0.1, subject@cmp.local, @cmp.local"],
    steps=[
        sign_in("dpo@cmp.local", "Priya", "DPO"),
        {"action": "Click 'Audit trail' and set 'From' to 21 September 2026. Look at the table columns.",
         "expected": "The columns are 'When', 'Event', 'Actor', 'About', 'Record' - there is no IP address column."},
        {"action": "Choose Area 'Projects', Event 'Transitioned', and click the newest row.",
         "expected": ("'Recorded details' lists 'From', 'To', 'Reason given' (a 'yes' or 'no' badge) and 'Published notice'. The words of any reason "
                      "are not shown anywhere in the dialog.")},
        {"action": "Click 'Show raw JSON' and read it.",
         "expected": ("It shows \"reason_given\": true or false - no free-text reason. If an \"ip\" line is present its value is a long string of letters "
                      "and digits (a keyed hash), never an address like 127.0.0.1 or 192.168.x.x. Close the dialog.")},
        {"action": "Change to Area 'Accounts', Event 'Invited', and open the newest row; click 'Show raw JSON'.",
         "expected": "No email address appears in the details; the person is identified only through 'Who' / 'About' and the record link."},
        {"action": "Clear the Area and Event filters (keep From). Type 127.0.0.1 in 'Search' and click 'Search'.",
         "expected": "'Nothing matches these filters'."},
        {"action": "Search for subject@cmp.local, then for @cmp.local.",
         "expected": "'Nothing matches these filters' both times - no contact is written into the trail."},
        {"action": "If entries exist, choose Area 'Delegation', Event 'Granted', open the newest row and click 'Open cover arrangement'.",
         "expected": ("The details show 'Reason given' yes/no and no reason text. The button opens the 'Delegate' page. If it shows 'This page could not "
                      "be found', record a defect.")},
    ],
    pass_criteria="Entries from 21 September 2026 carry no reason text, no email or mobile, and no readable IP address; reasons appear only as 'Reason given' yes/no.",
)

case(
    id="OVS-19",
    title="Personal data is never shown as scrambled 'SE::' text on staff screens",
    feature="Data protection on screen (sealed values opened for display)",
    role="DPO, Administrator and DCO on console",
    priority="High",
    type="Negative",
    preconditions=[FRESH, WIDE, CODES],
    test_data=["dpo@cmp.local", "admin@cmp.local", "dco@cmp.local", f"Password: {PW}"],
    steps=[
        sign_in("dpo@cmp.local", "Priya", "DPO"),
        {"action": "Click 'Users' and read the 'Name' column (wait for the table to finish loading).",
         "expected": "Every name is readable (e.g. 'Priya Menon', 'Anjali Verma'); no text starting 'SE::' appears anywhere on the page."},
        {"action": "Click 'Consents' and read the 'Data subject' column, including the email shown under each name.",
         "expected": "Names and emails are readable; no 'SE::' text."},
        {"action": "Click 'Rights requests' and read the 'Who' column; open one request.",
         "expected": "Names and the request's details are readable; no 'SE::' text."},
        {"action": "Click 'Audit trail'; read the 'Actor', 'About' and 'Record' columns; type Anj in the About box and read the offered names; open one entry.",
         "expected": "All names, emails and record labels are readable in the table, the About list and the dialog; no 'SE::' text."},
        {"action": "Click 'Dashboard' and read the queue rows and 'Recent activity'.",
         "expected": "People's names are readable; no 'SE::' text."},
        sign_out_in("admin@cmp.local", "System", "Administrator"),
        {"action": "Click 'Users', click 'Edit' on any row, read 'Full name', 'Email' and 'Mobile', then close the dialog without saving.",
         "expected": "The 'Edit account' form is filled with the readable name and a readable email and/or mobile; no field contains 'SE::'."},
        {"action": "Sign out, sign in as dco@cmp.local, click 'Consents' and open one record.",
         "expected": "The register and the record's heading show the person's readable name; no 'SE::' text."},
    ],
    pass_criteria="On every screen visited, names, emails and mobiles display as readable text; the string 'SE::' never appears.",
)

# ---------------------------------------------------------------- portal
case(
    id="OVS-20",
    title="Data principal's portal notifications show only her own events and open her own pages",
    feature="Notifications (data principal portal)",
    role="Data principal on portal",
    priority="High",
    type="Positive",
    preconditions=[FRESH, CODES,
                   f"The portal is running at {PORTAL}.",
                   "Anjali Verma (subject@cmp.local) has at least one consent and ideally a rights request."],
    test_data=["Email address: subject@cmp.local (Anjali Verma)"],
    steps=[
        {"action": (f"Open {PORTAL}/sign-in. Under 'Sign in with' choose 'Email', type subject@cmp.local in 'Email address' and click 'Send me a code'."),
         "expected": "A 'Check your messages' notice appears and a 'Six-digit code' box is shown."},
        {"action": "Type the code the test coordinator relays and click 'Verify'.",
         "expected": ("The 'Your consents' page opens. The sidebar shows YOUR DATA - 'My consents', 'My requests' and YOU - 'Notifications', "
                      "'Your profile', and nothing else.")},
        {"action": "Click 'Notifications'.",
         "expected": ("The page 'Notifications' opens with 'What has happened that concerns you, taken from the audit trail itself.' Entries are about "
                      "Anjali only, e.g. 'Consent given', 'Consent withdrawn', 'Notice served', 'Subject registered', 'Rights request received'. "
                      "If there are none it says 'Nothing to report'.")},
        {"action": "Check the list for events that are not hers to see.",
         "expected": ("No sign-in events ('Auth ...'), no 'Project transitioned', no office working on her request (e.g. 'Rights ticket issued', "
                      "'Rights holders derived') and no events about other people.")},
        {"action": "Click the body of a 'Consent given' entry.",
         "expected": ("A dialog shows 'What' ('Consent record: Anjali Verma — <project>'), 'When', 'Who', 'Event' (consent.given) and 'Record', with an "
                      "'Open consent record' button. All names are readable; no 'SE::' text.")},
        {"action": "Click 'Open consent record'.",
         "expected": "The 'Your consents' page on the portal opens - not a staff page and not 'Not part of your account'."},
        {"action": "Back on 'Notifications', click the record link on a rights request entry (if present) and on a 'Subject registered' entry ('Account: Anjali Verma' / 'Open account').",
         "expected": ("The request link opens 'My requests'. The account link opens her own account page ('Your account'). If either shows 'This page "
                      "could not be found', record a defect.")},
        {"action": f"Type {PORTAL}/users in the address bar, then {PORTAL}/audit.",
         "expected": "Both show the '404 | This page could not be found.' page - no staff screen exists on the portal."},
    ],
    pass_criteria="The data principal's feed contains only her own permitted events, entries open with readable details, every link lands on her own portal pages, and staff URLs do not exist on the portal.",
)

# ---------------------------------------------------------------- finding your way
case(
    id="OVS-21",
    title="Find your way: the command palette, breadcrumb, account menu, foldable sidebar and folding cards",
    feature="Console navigation (command palette, header, sidebar)",
    role="DPO on console",
    priority="Medium",
    type="Positive",
    preconditions=[FRESH, WIDE, CODES],
    test_data=["Account: dpo@cmp.local (Priya Menon)"],
    steps=[
        sign_in("dpo@cmp.local", "Priya", "DPO"),
        {"action": "Click 'Projects' in the sidebar and look to the right of the logo in the header.",
         "expected": "A breadcrumb reads 'Governance › Projects'. In the header are a box 'Search or jump to…' showing ⌘K (on a Mac) or Ctrl K, a help (?) button, a bell, and Priya's name with the 'DPO' badge and her initials."},
        {"action": "Press Ctrl+K (⌘K on a Mac), or click 'Search or jump to…'. Type 'aud'.",
         "expected": "A search box opens over the page ('Search pages and actions…'). Typing narrows the list to 'Audit trail' under the heading 'Oversight'. The footer reads '↑ ↓ to move', '↵ to open', 'Esc to close'."},
        {"action": "Press Enter.",
         "expected": "The 'Audit trail' page opens and the box closes. The breadcrumb reads 'Oversight › Audit trail'."},
        {"action": "Open the box again (Ctrl+K / ⌘K) without typing.",
         "expected": "A 'Recent' group lists the pages just visited (for example 'Projects'), but not the page you are on. An 'Actions' group offers 'Open the help manual', 'Switch to dark theme' and 'Sign out'. Type 'zzz': it says 'Nothing matches “zzz”'. Press Esc to close it."},
        {"action": "Click Priya's name at the top right of the header.",
         "expected": "An account menu opens showing 'Priya Menon' and 'DPO', then 'Your profile', 'Help manual', 'Switch to dark theme' and 'Sign out'. Press Esc: it closes and nothing else changes."},
        {"action": "In the sidebar click the heading 'GOVERNANCE', then click it again.",
         "expected": "The first click folds away Projects, Approvals, Notices and Purposes; the second brings them back. The group holding the page you are on cannot be folded away."},
        {"action": "Click 'Collapse sidebar' at the bottom of the sidebar, then reload the page.",
         "expected": "The sidebar becomes a narrow strip of icons (hovering an icon shows its name) and stays that way after the reload. Click 'Expand sidebar' to restore it."},
        {"action": "Open 'Rights requests', open any request, and click the card 'Clock and path'.",
         "expected": "The card folds to its heading, so the working cards below move up. Clicking it again unfolds it. On a project page, the 'History' card folds the same way and shows its number of entries."},
    ],
    pass_criteria="Pages can be reached from the keyboard through the command palette; the breadcrumb shows where you are; the account menu offers profile, help, theme and sign-out; sidebar groups and the long reference cards fold away and are remembered.",
)

case(
    id="OVS-22",
    title="The help manual opens from the sign-in page, the header and the command palette, and follows your role",
    feature="Help manual (console and portal)",
    role="Anyone on console and portal; DCO on console",
    priority="Medium",
    type="Positive",
    preconditions=[FRESH, CODES],
    test_data=["Account: dco@cmp.local (Arun Shetty)", "Search word: export"],
    steps=[
        {"action": f"Open {CONSOLE}/sign-in and click 'Read the help manual' under the form ('New here, or stuck?').",
         "expected": "The page 'COMPASS CMP Manual' opens without signing in, with a search box, an 'Every role' choice, '24 sections', a numbered 'Table of contents' and a 'Sign in' button at the top right."},
        {"action": "In the table of contents click '16 Rights requests'.",
         "expected": "The page scrolls to section 16 'Rights requests', whose badges read 'DPO' and 'Administrator'. Its numbered steps show the screen's own words in grey label boxes, for example 'Confirm classification'."},
        {"action": "Type 'export' in 'Search the manual'.",
         "expected": "Only sections that mention exports remain, and the line under the box reads '8 of 24 sections mentioning “export”' (Exports, Purposes, Processors, the audit trail and others). Clicking the × clears it."},
        {"action": "Scroll to the end of the manual.",
         "expected": "A panel 'Have any questions? Contact us' shows the Privacy Office's email address and response time, and says to ask your administrator about sign-in or role problems."},
        {"action": f"Sign in to the console as dco@cmp.local ({PW} and the relayed code). Click the help (?) button in the header.",
         "expected": "The manual opens already set to 'For the DCO', reading '15 of 24 sections for the DCO'. Section numbers keep their places (for example 8, 12, 13, 14). The top-right button now reads 'Back to the console'."},
        {"action": "Choose 'Every role' in the role box. Then click 'Back to the console', press Ctrl+K (⌘K) and choose 'Open the help manual'.",
         "expected": "'Every role' shows all 24 sections. The command palette opens the manual again."},
        {"action": f"Open {PORTAL}/sign-in and click 'Help manual' next to 'Your rights and how to exercise them'.",
         "expected": "The page 'Consent Portal Manual' opens without signing in, with 15 sections written for data principals (creating an account, giving consent through a link, withdrawing, requests, nominations) and no role choice."},
        {"action": "Narrow the browser window to phone width (or use a phone) and look at the portal manual.",
         "expected": "The table of contents folds into a 'Table of contents · 15' bar above the sections; opening it lists them. Nothing is cut off at the side."},
    ],
    pass_criteria="Both manuals open without signing in and from the places that link to them; the console manual follows the reader's role and can show every section; search narrows the sections; the manual ends with the Privacy Office's contact.",
)

ids = [c["id"] for c in cases]
assert len(ids) == len(set(ids))
for c in cases:
    assert 4 <= len(c["steps"]) <= 10, (c["id"], len(c["steps"]))
    for s in c["steps"]:
        assert s["action"] and s["expected"]
    order = ["id", "area", "title", "feature", "role", "priority", "type", "ref", "preconditions", "test_data", "steps", "pass_criteria"]
    assert set(c) == set(order), c["id"]

ordered = [{k: c[k] for k in ["id", "area", "title", "feature", "role", "priority", "type", "ref",
                                "preconditions", "test_data", "steps", "pass_criteria"]} for c in cases]
out = str(__import__("pathlib").Path(__file__).with_name("OVS.json"))
with open(out, "w", encoding="utf-8") as f:
    json.dump(ordered, f, ensure_ascii=False, indent=2)
print(len(ordered), "cases;", sum(len(c["steps"]) for c in ordered), "steps")
