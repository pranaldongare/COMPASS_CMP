import json

AREA = "Projects, notices and links"
PW = "SeedPassw0rd!2026"


def signin(email, who):
    return (
        f"Signed in to the console (http://localhost:3000) as {who} ({email}): on 'Sign in' enter "
        f"'Email or username' and 'Password' ({PW}), click 'Sign in', then type the 6-digit code "
        "relayed by the test coordinator on 'Verify it is you' and click 'Verify and continue'. "
        "If the sign-in page shows a 'Development accounts' panel (development builds only), its 'Use' "
        "button beside a login fills both boxes for you. To change user, use 'Sign out' in the sidebar."
    )


RND = signin("rnd@cmp.local", "Kavya Rao, R&D User")
DPO = signin("dpo@cmp.local", "Priya Menon, DPO")
DCO = signin("dco@cmp.local", "Arun Shetty, DCO")
DCOA = signin("dcoadmin@cmp.local", "Nikhil Bose, DCO Admin")
RCO = signin("rco@cmp.local", "Meera Iyer, RCO")


def s(action, expected):
    return {"action": action, "expected": expected}


def case(n, title, feature, role, priority, typ, pre, data, steps, pc):
    return {
        "id": f"PRJ-{n:02d}",
        "area": AREA,
        "title": title,
        "feature": feature,
        "role": role,
        "priority": priority,
        "type": typ,
        "ref": "Core",
        "preconditions": pre,
        "test_data": data,
        "steps": steps,
        "pass_criteria": pc,
    }


cases = []

# ---------------------------------------------------------------- 01
cases.append(case(
    1, "R&D User registers a new project naming a third-party and an in-house collector",
    "Register a project", "R&D User", "High", "Positive",
    [RND, "No project named 'UAT Study 01' exists yet (search for it first)."],
    ["Project name: UAT Study 01",
     "Description: Gait video and facial images collected at partner and in-house labs for UAT.",
     "Internal name: UAT-01", "Requesting team: Computer Vision",
     "Processors: SEED (collected by a third party) and SRIB (collected in-house)"],
    [
        s("In the left sidebar click 'Projects'.",
          "The 'Projects' page opens with the columns Project, Status, Data Collection Owner, Created by, Updated, and a 'Register a project' button at the top right."),
        s("Click 'Register a project'.",
          "A dialog titled 'Register a project' opens with the fields 'Project name', 'Description', 'Internal name', 'Requesting team' and a 'Who will collect' section listing processors as tick boxes (each marked 'collected in-house' or 'collected by a third party')."),
        s("Type the Project name, Description, Internal name and Requesting team from the test data.",
          "The text appears in each field; no error messages are shown."),
        s("Under 'Who will collect', tick 'SEED' (collected by a third party).",
          "A blue note appears: 'Once the DPO approves this, the DCO Admin assigns the data sources for the third-party collection.'"),
        s("Also tick 'SRIB' (collected in-house).",
          "The note now covers both: '...the DCO Admin assigns the data sources for the third-party collection, and it comes back to you to name the data sources and an R&D Collection Owner.'"),
        s("Click 'Register project'.",
          "The dialog closes and a green toast 'Project registered' says 'It starts in draft. Attach a notice and an approval, then send it to the DPO.'"),
        s("Look at the page that opens.",
          "The project's own page opens with the heading 'UAT Study 01', status badge 'In Draft', and the progress bar showing In Draft > Pending Approval > Approved."),
        s("Look at the 'Details' card at the top right, beside 'What happens next'.",
          "Internal name 'UAT-01', Requesting team 'Computer Vision', Data Collection Owner 'Not assigned', Created by 'Kavya Rao'."),
        s("Look at the tabs under it, then click 'Setup' and look at the 'Who is collecting' card.",
          "The tabs read 'Overview' (selected), 'Setup', 'Consent', 'Collections & exchanges' and 'Activity'. In 'Setup', SEED and SRIB are both listed with the chip 'approved'; SEED says 'collected by a third party' and SRIB says 'collected in-house'."),
        s("Click 'All projects' at the top of the page.",
          "The Projects list shows 'UAT Study 01' with status 'In Draft' and Created by 'Kavya Rao'."),
    ],
    "The project is created in 'In Draft', names both processors, shows the right routing note before saving, and opens on its own page."))

# ---------------------------------------------------------------- 02
cases.append(case(
    2, "Registering a project with missing required information is refused field by field",
    "Register a project - validation", "R&D User", "Medium", "Negative",
    [RND],
    ["Project name: UAT Incomplete 01", "Description: (leave blank, then fill) Test only"],
    [
        s("Click 'Projects' in the sidebar, then 'Register a project'.",
          "The 'Register a project' dialog opens."),
        s("Leave every field empty and click 'Register project'.",
          "The dialog stays open. Under 'Project name' the message 'A project name is required' appears, and under 'Description' the message 'Describe what this project collects and why' appears."),
        s("Type 'UAT Incomplete 01' in 'Project name' and click 'Register project' again.",
          "The dialog stays open; the name error is gone but 'Describe what this project collects and why' is still shown under 'Description'."),
        s("Type 'Test only' in 'Description', tick no processor, and click 'Register project'.",
          "The dialog stays open and 'Choose at least one processor' appears under the 'Who will collect' list. No routing note is shown because nothing is ticked."),
        s("Click 'Cancel'.",
          "The dialog closes. 'UAT Incomplete 01' does NOT appear in the Projects list."),
    ],
    "No project is created while the name, description or at least one processor is missing, and each problem is shown next to its own field."))

# ---------------------------------------------------------------- 03
cases.append(case(
    3, "Submitting a fresh draft is blocked and the panel names every missing prerequisite",
    "Project transitions - blockers panel", "R&D User", "High", "Negative",
    ["PRJ-01 completed (UAT Study 01 is In Draft with no notice and no approval).", RND],
    ["Project: UAT Study 01"],
    [
        s("Click 'Projects' in the sidebar, type 'UAT Study 01' in 'Search' (the list updates as you type). Click 'UAT Study 01'.",
          "The project page opens with status 'In Draft'."),
        s("Find the card titled 'What happens next'.",
          "It reads 'Currently In Draft. These are the moves your role can make from here.' and shows one row 'Moves the project to Pending Approval' with a 'Submit for approval' button."),
        s("Read the warning lines under 'Moves the project to Pending Approval'.",
          "All six missing items are listed at once, each with a warning icon: 'The project has no notice'; 'The notice has no purposes attached'; 'The notice is missing required Rule 3 elements'; 'The notice does not say who it applies to'; 'The notice has no text yet - add at least one language'; 'No approval with a proof file'."),
        s("Try to click the 'Submit for approval' button on that row.",
          "The button is greyed out (disabled); nothing happens and the status stays 'In Draft'."),
        s("Click the 'Setup' tab and look at the 'Notices' card.",
          "It shows 'No notice yet' with the buttons 'Upload a notice document', 'Copy an existing notice' and 'Use a notice template'. There is NO 'New notice' button."),
        s("Look at the 'Approvals' card.",
          "It shows count 0, 'No approval uploaded', the text 'A security approval with its proof file is what unlocks the move to pending approval.' and an 'Upload an approval' button."),
        s("Look at the buttons at the top of the page.",
          "Only the status badge 'In Draft' and 'Edit' are shown. Adding a notice, an approval or a site is done on its own card in the tabs, not here."),
    ],
    "The submit button is disabled and every one of the six missing prerequisites is named together, not one at a time."))

# ---------------------------------------------------------------- 04
cases.append(case(
    4, "Uploading the notice template with placeholders still in it is refused",
    "Upload a notice document - validation", "R&D User", "Medium", "Negative",
    ["PRJ-01 completed.", RND],
    ["Unfilled template: download it from the dialog's 'Download it' link (DPDP_Consent_Notice_Template_v0_2.docx) and do not edit it",
     "Optional: any PDF file, to check a non-Word file is refused"],
    [
        s("Open project 'UAT Study 01' (Projects > search > click the name).",
          "The project page opens, status 'In Draft'."),
        s("Click the 'Setup' tab, then 'Upload a notice document' in the 'Notices' card.",
          "A dialog 'Upload a notice document' opens: 'The filled-in .docx template. Its purpose table becomes the notice's purposes, which the DPO then activates.' It shows 'Need the template? Download it', a 'Notice document' file chooser, a disabled 'Check the document' button and a disabled 'Create the notice' button."),
        s("Click 'Download it'.",
          "The browser saves the blank template file (DPDP_Consent_Notice_Template...docx)."),
        s("Under 'Notice document' use the browser's file chooser ('Choose File') to pick the blank template you just downloaded.",
          "The file name and size appear under the chooser; 'Check the document' becomes clickable. 'Create the notice' stays disabled."),
        s("Click 'Check the document'.",
          "A red message appears starting with the number of placeholders, e.g. '... placeholder(s) are still unfilled: ...' and ending 'Fill the document in before uploading it - a notice served with a placeholder in it is one nobody read.' 'Create the notice' stays disabled."),
        s("(Optional) Pick a PDF file instead and click 'Check the document'.",
          "The chooser only offers .docx; if a PDF is forced through, the message 'This is not a readable Word document. Upload the .docx template, not a PDF or a scan of one.' appears."),
        s("Click 'Cancel'.",
          "The dialog closes; the 'Notices' card still says 'No notice yet'."),
    ],
    "A document with unfilled placeholders never creates a notice, and the reason is shown in plain words."))

# ---------------------------------------------------------------- 05
cases.append(case(
    5, "R&D User brings the notice by uploading the filled DPDP notice template",
    "Upload a notice document", "R&D User", "High", "Positive",
    ["PRJ-01 completed (UAT Study 01 has no notice yet).", RND,
     "The test coordinator has handed over a filled copy of the template (tests/fixtures/notice_filled.docx is a valid example: English, 9 purposes, 7 data categories)."],
    ["File: the filled notice .docx from the coordinator", "Project: UAT Study 01", "Expected notice code: NTC-UAT-STUDY-01-2026 (if a code with that name already exists from an earlier run, the system adds a suffix such as -2; use the code actually shown in later cases)"],
    [
        s("Open project 'UAT Study 01', click the 'Setup' tab and in the 'Notices' card click 'Upload a notice document'.",
          "The 'Upload a notice document' dialog opens with 'Check the document' and 'Create the notice' disabled."),
        s("Under 'Notice document' choose the filled .docx.",
          "The file name and size are shown; 'Check the document' becomes clickable."),
        s("Click 'Check the document'.",
          "A green box reads 'Read 9 purposes and 7 data categories, in english. Nothing has been written yet.' (numbers match your file). A 'Purposes' table lists each row with the columns In document, Name, Data categories, Retention, Consent (badges 'Required' or 'Declinable')."),
        s("Read any yellow warnings under the green box.",
          "If the document names a different project (the example file names 'Gait Identification Study 2026') a warning says 'The document names the project ... but this project is 'UAT Study 01'. Check you are uploading to the right one.' This is expected with the example file."),
        s("Click 'The text a data subject will read (... characters)' to expand it.",
          "An excerpt of the notice wording is shown."),
        s("Click 'Create the notice'.",
          "The dialog closes and a green toast 'Notice created' says 'NTC-UAT-STUDY-01-2026 carries 9 purposes. The DPO activates them before it can be published.'"),
        s("Look at the 'Notices' card.",
          "It lists 'NTC-UAT-STUDY-01-2026 v1' with '9 purposes · 1 language(s)' and the status badge 'Draft'."),
        s("Look at the 'What happens next' card.",
          "Under 'Moves the project to Pending Approval' only one line remains: 'No approval with a proof file'. The 'Submit for approval' button is still disabled."),
        s("Click 'NTC-UAT-STUDY-01-2026 v1' in the Notices card.",
          "The notice page opens titled 'NTC-UAT-STUDY-01-2026 · version 1' with 'Draft. Nothing here has been shown to a data subject yet.' The 'Purposes' card lists 9 purposes, each with the status 'Draft'."),
    ],
    "The notice, its purposes (as Draft) and its English text are created from the document in two steps (check, then create), and the notice-related blockers disappear from the project."))

# ---------------------------------------------------------------- 06
cases.append(case(
    6, "R&D User starts a second project's notice from an approved notice",
    "Copy an existing notice", "R&D User", "Medium", "Positive",
    [RND, "Seeded notice NTC-GAIT-2026 v1 is published."],
    ["Project name: UAT Study 02", "Description: Copy-notice UAT project.",
     "Processor: SEED", "Notice to copy: NTC-GAIT-2026 v1 — Gait Identification Study 2026"],
    [
        s("Click 'Projects' > 'Register a project'. Enter the name and description from the test data, tick 'SEED' and click 'Register project'.",
          "Toast 'Project registered'; the 'UAT Study 02' page opens with status 'In Draft'."),
        s("Click the 'Setup' tab, then 'Copy an existing notice' in the 'Notices' card.",
          "A dialog 'Copy an existing notice' opens: 'Copies the wording, the purposes and every language rendition into this project as a fresh draft.' with a 'Notice to copy' list and a disabled 'Copy into this project' button."),
        s("Open 'Notice to copy'.",
          "Every approved or published notice on the platform is offered, from any project and whoever wrote it - for example 'NTC-GAIT-2026 v1 — Gait Identification Study 2026'. Notices marked '(approved, not yet published)' come first. No draft notice is offered."),
        s("Choose 'NTC-GAIT-2026 v1 — Gait Identification Study 2026'.",
          "A yellow box 'What comes across, and what does not' explains the legal approvals are not copied and each rendition must be re-approved. 'Copy into this project' becomes clickable."),
        s("Click 'Copy into this project'.",
          "The dialog closes; a toast 'Copied into NTC-UAT-STUDY-02-2026' says 'It is a fresh draft. Review the wording, then approve and publish it.'"),
        s("Click the new notice in the 'Notices' card.",
          "The notice page 'NTC-UAT-STUDY-02-2026 · version 1' opens with status 'Draft'. The 'Purposes' card shows the purposes copied from the Gait notice."),
        s("Look at the 'Legal approval, per language' card.",
          "Each copied language shows 'Not legally approved' (approvals did not carry over)."),
    ],
    "Every approved or published notice is offered whoever wrote it; a fresh draft notice with the wording, purposes and renditions of the chosen one is created for the new project, without its legal approvals."))

# ---------------------------------------------------------------- 07
cases.append(case(
    7, "R&D User cannot compose or approve notice wording, purposes or renditions",
    "Notice authoring rights", "R&D User", "High", "Negative",
    ["PRJ-05 completed (NTC-UAT-STUDY-01-2026 v1 is a Draft).", RND],
    ["Project: UAT Study 01", "Notice: NTC-UAT-STUDY-01-2026 v1"],
    [
        s("Open project 'UAT Study 01', click the 'Setup' tab and look at the buttons on the 'Notices' card.",
          "'Upload a notice document', 'Copy an existing notice' and 'Use a notice template' are shown; there is NO 'New notice' button."),
        s("Click 'NTC-UAT-STUDY-01-2026 v1' in the 'Notices' card.",
          "The notice page opens. The header shows the 'Draft' badge but NO 'Edit' button."),
        s("Look at the 'Publication checklist' card.",
          "It is visible to the R&D User and reads '... item(s) blocking publication:' followed by lines such as 'the purpose ... is draft, not activated' and 'the english text is not legally approved', each with a 'fix this' link. There is NO 'Publish this notice' button."),
        s("Look at the 'Notice text' card.",
          "The English wording is displayed read-only with 'Not legally approved — the project cannot be approved until it is'. There is NO 'Edit English text' button."),
        s("Look at the 'Purposes' card.",
          "Each purpose shows the 'Draft' status. There is NO 'Manage', NO 'Activate' and NO 'Customise for this notice' button."),
        s("Look at the 'Legal approval, per language' card.",
          "The english row shows 'Not legally approved'. There is NO 'Add language', NO 'Edit' and NO 'Approve' button."),
    ],
    "The R&D User can read the notice and its checklist but has no control to write wording, add/edit renditions, attach/activate purposes, approve text or publish."))

# ---------------------------------------------------------------- 08
cases.append(case(
    8, "R&D User uploads the security approval and submits the project for DPO review",
    "Upload approval and submit (In Draft to Pending Approval)", "R&D User", "High", "Positive",
    ["PRJ-05 completed (only 'No approval with a proof file' still blocks).", RND],
    ["Type: Security", "Reference number: SEC-UAT-0001",
     "Approved on: first a date in the future (negative check), then today's date",
     "Proof document: any small PDF, PNG or JPEG under 25 MB"],
    [
        s("Open project 'UAT Study 01', click the 'Setup' tab and click 'Upload an approval' in the 'Approvals' card.",
          "A dialog 'Upload an approval' opens: 'The proof file is mandatory - an approval without one does not unlock the transition.' Fields: 'Type' (preset to Security), 'Reference number', 'Approved on', 'Proof document'."),
        s("Leave 'Reference number' and 'Proof document' empty, set 'Approved on' to a future date, and click 'Upload approval'.",
          "The dialog stays open with field errors: 'A reference number is required', 'The approval date cannot be in the future' and 'Choose an approval document'."),
        s("Enter 'SEC-UAT-0001', set 'Approved on' to today, choose the proof file and click 'Upload approval'.",
          "The dialog closes; toast 'Approval uploaded' says 'The project can now move to pending approval.'"),
        s("Look at the 'Approvals' card.",
          "Count 1; the row reads 'Security SEC-UAT-0001', 'Approved <today> · uploaded ... by Kavya Rao', a short hash, and a 'Proof' button."),
        s("Click 'Proof'.",
          "The file downloads and a toast 'Proof downloaded' says 'Hash matches the record.'"),
        s("Look at 'What happens next'.",
          "'Moves the project to Pending Approval' has no warning lines and the 'Submit for approval' button is active (highlighted)."),
        s("Scroll to the bottom of the page.",
          "The page ends with the tabbed sections. The move is not repeated at the foot: 'Submit for approval' is only in 'What happens next' at the top."),
        s("Click 'Submit for approval'.",
          "Toast 'Moved to Pending Approval'. The status badge changes to 'Pending Approval' and the progress bar moves to its second step."),
        s("Look at 'What happens next' again, then click the 'Activity' tab and look at the 'History' card.",
          "'What happens next' reads 'There is nothing for your role to do at this stage.' History shows 'In Draft → Pending Approval' by 'Kavya Rao (Rnd user)' with the time. The 'Edit' button is no longer shown in the page header."),
    ],
    "The approval with proof is recorded and the project moves to 'Pending Approval', after which the R&D User has no further move."))

# ---------------------------------------------------------------- 09
cases.append(case(
    9, "DPO review: approval is blocked until the DPO's own notice decisions are made; sending back needs a reason",
    "Project transitions - DPO blockers and send back", "DPO", "High", "Negative",
    ["PRJ-08 completed (UAT Study 01 is Pending Approval; its notice's purposes are Draft and English text is not approved).", DPO],
    ["Project: UAT Study 01", "Reason: (leave empty)"],
    [
        s("On the 'Dashboard' look at 'Needs attention'.",
          "A row 'Projects pending approval' shows a count of 1 or more."),
        s("Click 'Projects' in the sidebar, set 'Status' to 'Pending Approval', and click 'UAT Study 01'.",
          "The project page opens with status 'Pending Approval'."),
        s("Look at the 'What happens next' card.",
          "It reads 'Currently Pending Approval.' and offers two rows: 'Moves the project to Approved' (with the tag 'publishes the notice' and an 'Approve project' button) and 'Moves the project to In Draft' (with a 'Return to draft' button)."),
        s("Read the warning lines under 'Moves the project to Approved'.",
          "Both DPO-side blockers are listed: 'The notice text is not legally approved - approve every language on the notice first' with a link 'Approve the notice', and 'The notice carries purposes that are not activated - activate them before approving' with a link 'Open the notice'. The 'Approve project' button is disabled."),
        s("Under 'Moves the project to In Draft' note the hint, then click the 'Return to draft' button.",
          "The hint reads 'A reason is required and is recorded in the history.' A panel 'Return to draft' opens with a required 'Reason' box."),
        s("Leave 'Reason' empty and click 'Return to draft' in the panel.",
          "The message 'A reason is required for this transition.' appears; the project stays 'Pending Approval'."),
        s("Click 'Cancel' in the panel.",
          "The panel closes; status is still 'Pending Approval' and History has no new entry."),
        s("Click the 'Open the notice' link on the blocker line.",
          "The notice page 'NTC-UAT-STUDY-01-2026 · version 1' opens."),
    ],
    "The DPO cannot approve while text is unapproved or purposes are not activated, every blocker is named with a link to the notice, and a send-back cannot be done without a reason."))

# ---------------------------------------------------------------- 10
cases.append(case(
    10, "DPO activates each purpose from the notice that carries it",
    "Notice review - activate purposes", "DPO", "High", "Positive",
    ["PRJ-09 completed (DPO is on the notice page of NTC-UAT-STUDY-01-2026 v1).", DPO],
    ["Notice: NTC-UAT-STUDY-01-2026 v1 (9 draft purposes from the uploaded document)"],
    [
        s("Look at the 'Publication checklist' card.",
          "It reads '<n> item(s) blocking publication:' with one line per purpose 'the purpose <code> is draft, not activated' plus 'the english text is not legally approved'; each line has a 'fix this' link."),
        s("Click 'fix this' next to a purpose line.",
          "The page scrolls to the 'Purposes' card ('Rule 3(b): what each purpose enables, itemised, with its retention.')."),
        s("Review the first purpose (name, description, Basis, Retention, Categories), then click its 'Activate' button.",
          "Toast '<purpose name> activated' says 'It no longer blocks publication.' Its status changes from 'Draft' to 'Active' and its 'Activate' button disappears."),
        s("Scroll back to the 'Publication checklist'.",
          "The blocking count has gone down by one and that purpose's line is gone, without reloading the page."),
        s("Repeat 'Activate' for every remaining Draft purpose, one at a time.",
          "Each shows its own toast; there is no single 'activate all' control."),
        s("Check the checklist once all purposes are active.",
          "No 'the purpose ... is draft, not activated' lines remain; only 'the english text is not legally approved' is left. The 'Purposes' stat shows 9."),
    ],
    "Every purpose is activated individually from the notice page and each activation removes its checklist line straight away."))

# ---------------------------------------------------------------- 11
cases.append(case(
    11, "DPO composes the wording, adds a Hindi rendition and legally approves each language",
    "Notice review - renditions and legal approval", "DPO", "High", "Positive",
    ["PRJ-10 completed.", DPO],
    ["Extra sentence for English: 'Contact the Privacy Office at dpo@example.org with any question.'",
     "Hindi text: 'यह UAT परीक्षण सूचना है। (UAT test notice - Hindi rendition)'"],
    [
        s("On notice NTC-UAT-STUDY-01-2026 v1, find the 'Notice text' card and click 'Edit English text'.",
          "A dialog 'Edit English text' opens: 'This exact text is hashed at publication and becomes the record of what was agreed to.' 'Language' is locked to English; 'Notice text' holds the current wording."),
        s("Add the extra sentence at the end of the text and click 'Save text'.",
          "Toast 'Rendition saved' says 'It must be legally approved before the notice can be published.' The new sentence is visible in the 'Notice text' card."),
        s("In the 'Legal approval, per language' card click 'Add language'.",
          "A dialog 'Add language' opens with 'Language' and 'Notice text'."),
        s("Choose Language 'Hindi', paste the Hindi text and click 'Save text'.",
          "Toast 'Rendition saved'. The card now lists English and Hindi, both 'Not legally approved'. The 'Notice text' card shows language tabs (english / hindi)."),
        s("Look at the 'Publication checklist'.",
          "Lines 'the english text is not legally approved' and 'the hindi text is not legally approved' are shown; 'Languages' stat is 2, 'Approved' is 0."),
        s("Read the English text, then click 'Approve' on the English row.",
          "Toast 'english approved' says 'Its hash is what a data subject's consent will be matched against.' The row shows 'Approved' with 'Priya Menon' and the time."),
        s("Click the 'hindi' tab in 'Notice text', read it, then click 'Approve' on the Hindi row.",
          "Toast 'hindi approved'. Both rows show 'Approved'; 'Approved' stat equals 2."),
        s("Look at the 'Publication checklist'.",
          "It reads 'This notice is complete and ready to publish.' and shows a 'Publish this notice' button. Do NOT click it - publication happens with the project approval in PRJ-12."),
    ],
    "The Privacy Office can edit the wording and add a language, each saved text starts unapproved, and approving every language clears the checklist."))

# ---------------------------------------------------------------- 12
cases.append(case(
    12, "DPO approves the project, which publishes and freezes its notice",
    "Project approval (Pending Approval to Approved)", "DPO", "High", "Positive",
    ["PRJ-11 completed (checklist says the notice is complete).", DPO],
    ["Project: UAT Study 01", "Note: 'UAT approval - all purposes reviewed.'"],
    [
        s("Click the project name link at the top of the notice page ('UAT Study 01') to return to the project.",
          "The project page opens with status 'Pending Approval'."),
        s("Look at 'Moves the project to Approved' in 'What happens next'.",
          "No warning lines remain; the 'Approve project' button is active and the row carries the tag 'publishes the notice'."),
        s("Click 'Approve project'.",
          "A panel 'Approve project' opens with a yellow warning: 'This publishes the project's notice. Its text and hash are frozen at that moment and cannot be edited afterwards - a correction requires a new version...' and an optional 'Note (optional)' box."),
        s("Type the note and click 'Approve project' in the panel.",
          "Toast 'Moved to Approved' says 'The notice has been published and its text is now frozen.'"),
        s("Check the page header and progress bar.",
          "Status badge 'Approved'; progress bar at the last step."),
        s("Click the 'Setup' tab and look at the 'Notices' card.",
          "'NTC-UAT-STUDY-01-2026 v1' shows the badge 'Published' and '· published <date/time>'."),
        s("Click the 'Activity' tab and look at the 'History' card.",
          "The newest entry is 'Pending Approval → Approved' by 'Priya Menon (Dpo)' with the note shown in quotes."),
        s("Click the 'Consent' tab.",
          "Above 'Collection sites' an info note reads 'Adding a site now is a material change: it adds a recipient to a published notice, so it requires a new notice version before collection starts there.'"),
    ],
    "The project is Approved and, in the same step, its notice becomes Published with a timestamp."))

# ---------------------------------------------------------------- 13
cases.append(case(
    13, "A published notice is frozen - no edits, and an upload cannot replace it",
    "Notice freeze after publication", "DPO, R&D User", "High", "Negative",
    ["PRJ-12 completed (NTC-UAT-STUDY-01-2026 v1 is Published).", DPO, "Kavya Rao (rnd@cmp.local) available for the second half."],
    ["Notice: NTC-UAT-STUDY-01-2026 v1", "File: the same filled notice .docx used in PRJ-05"],
    [
        s("As the DPO open 'Notices' in the sidebar and click 'NTC-UAT-STUDY-01-2026'.",
          "The notice page shows 'Published <date>. This text is frozen.' and the badge 'Published'."),
        s("Look for editing controls across the page.",
          "There is NO 'Edit' in the header, NO 'Edit English text', NO 'Manage', NO 'Activate', NO 'Customise for this notice', NO 'Add language' and NO 'Publish this notice'. The 'Publication checklist' card is not shown."),
        s("Read the info note in the right-hand column.",
          "'This notice is published. Its text and hashes are immutable — the database refuses an edit. To change anything, publish a new version.'"),
        s("Look at 'Rule 3 elements' > 'Recipients'.",
          "It shows the recipient text fixed at publication (no longer 'Generated from the project's sites at publication')."),
        s("Sign out and sign in as rnd@cmp.local. Open project 'UAT Study 01', click the 'Setup' tab and click 'Upload a notice document' in the 'Notices' card.",
          "The 'Upload a notice document' dialog opens."),
        s("Choose the filled .docx and click 'Check the document'.",
          "A red message says 'This project already has the published notice NTC-UAT-STUDY-01-2026. Its text is hashed into every consent taken against it, so an upload cannot replace it - create a new version of the notice instead.' 'Create the notice' stays disabled."),
        s("Click 'Cancel'.",
          "The dialog closes; the Notices card still shows only v1 'Published'."),
    ],
    "Once published, the notice offers no way to change its text or purposes, and a re-upload is refused with a message pointing to a new version."))

# ---------------------------------------------------------------- 14
cases.append(case(
    14, "Third-party routing: DCO Admin registers the partner's collection site and it passes to the DCO",
    "Routing after approval - third party; Add site; Who runs it", "DCO Admin", "High", "Positive",
    ["PRJ-12 completed (UAT Study 01 Approved, names SEED).", DCOA,
     "Seeded data source 'CIT' (SRC-SEED-CIT) under SEED is owned by Arun Shetty."],
    ["Project: UAT Study 01", "Data source: CIT · SEED · Arun Shetty", "Location: CIT campus, Coimbatore"],
    [
        s("Click 'Projects' in the sidebar, set 'Status' to 'Approved' and open 'UAT Study 01'.",
          "The project is visible to the DCO Admin (it names a third-party processor). Status 'Approved'."),
        s("Click the 'Setup' tab and look at the 'Who is collecting' card.",
          "SEED shows 'approved', 'collected by a third party' and '· no collection set up yet'."),
        s("Click the 'Consent' tab, then 'Add site' in the 'Collection sites' card.",
          "A dialog 'Add a collection site' opens with a yellow note that the notice is already published and adding a site is a material change requiring a new notice version; fields 'Data source' and 'Location'. There is no site-name or processor field."),
        s("Open 'Data source'.",
          "Only sources under this project's processors (SEED, SRIB) are offered, each as '<name> · <processor> · <owner or unowned>'. Sources of other processors are not listed."),
        s("Choose 'CIT · SEED · Arun Shetty'.",
          "A blue note reads 'Arun Shetty owns SRC-SEED-CIT and will pick up this site.'"),
        s("Type the Location and click 'Add collection site'.",
          "Toast 'Collection site added' says 'This adds a recipient the published notice does not name. A new notice version is required before collecting here.'"),
        s("Look at the 'Collection sites' card.",
          "A row 'CIT' with 'CIT campus, Coimbatore · operated by SEED', owner line 'CIT · Arun Shetty' with a 'decides' tag, status 'Active', and the buttons 'Change source' and 'Who runs it'."),
        s("Look at 'Details' at the top right.",
          "'Data Collection Owner' now reads 'Arun Shetty'."),
        s("Click 'Who runs it' on the CIT row.",
          "A dialog 'Who runs CIT?' opens: 'Only on this project. The data source keeps its own owner.' It explains 'Arun Shetty owns SRC-SEED-CIT and runs this site by default... every other project collecting from it is untouched.' The field is labelled 'Data Collection Owner' with the default 'No exception — Arun Shetty runs it'. The 'Name them'/'Clear the exception' button is disabled until the choice changes."),
        s("Click 'Cancel'.",
          "The dialog closes with nothing changed."),
    ],
    "The DCO Admin can see the approved third-party project, register the site by choosing a data source, and the site (and project) is owned by the source's DCO."))

# ---------------------------------------------------------------- 15
cases.append(case(
    15, "In-house routing: the R&D owner names the in-house source and the RCO sees only her site",
    "Routing after approval - in-house; Add site; site scope", "R&D User, RCO", "High", "Positive",
    ["PRJ-14 completed.", RND, "Meera Iyer (rco@cmp.local) available. Seeded source 'SE' (SRC-SRIB-SE) under SRIB is owned by Meera Iyer."],
    ["Project: UAT Study 01", "Data source: SE · SRIB · Meera Iyer", "Location: SRIB lab, Bengaluru"],
    [
        s("As Kavya Rao open project 'UAT Study 01'.",
          "Status 'Approved'. 'What happens next' says 'There is nothing for your role to do at this stage.' In the 'Setup' tab, the 'Who is collecting' button now reads 'Request a collector'."),
        s("Click the 'Consent' tab, then 'Add site'.",
          "The 'Add a collection site' dialog opens with the material-change note."),
        s("Choose Data source 'SE · SRIB · Meera Iyer', enter the Location, and click 'Add collection site'.",
          "Before saving the note reads 'Meera Iyer owns SRC-SRIB-SE and will pick up this site.' After saving, toast 'Collection site added'."),
        s("Look at the new 'SE' row in 'Collection sites'.",
          "Owner line 'SE · Meera Iyer' with the tag 'in-house'; buttons 'Change source' and 'Who runs it' are available to the R&D owner. There is NO 'Create link' button for the R&D User."),
        s("Click 'Who runs it' on the SE row.",
          "Dialog 'Who runs SE?' opens; the field is labelled 'R&D Collection Owner' and lists R&D Collection Owners (e.g. Meera Iyer · rco@cmp.local), not Data Collection Owners. Click 'Cancel'."),
        s("Sign out, sign in as rco@cmp.local and click 'Collection sites' in the sidebar.",
          "The list includes 'SE' with project 'UAT Study 01', 'Operated by' SRIB. The 'CIT' site of UAT Study 01 is NOT listed."),
        s("Click 'UAT Study 01' on the SE row.",
          "The project page opens on its 'Consent' tab. In 'Collection sites', the SE row shows a 'Create link' button; Meera has no link control for CIT."),
    ],
    "The in-house site is set up by the R&D owner and is visible to (and actionable by) the RCO only, separate from the third-party site."))

# ---------------------------------------------------------------- 16
cases.append(case(
    16, "A correction after publication is made as a new notice version, which supersedes the old one",
    "Notice versioning", "DPO", "Medium", "Positive",
    ["PRJ-14 and PRJ-15 completed (two sites added after publication).", DPO],
    ["Notice code (set by hand): NTC-UAT-STUDY-01-2026", "DPO contact: dpo@example.org",
     "Applies to: Data subjects — people outside the organisation",
     "Withdraw consent URL: https://example.org/withdraw", "Exercise rights URL: https://example.org/rights",
     "Board complaint URL: https://example.org/complain", "Language: English",
     "Notice text: copy the English text of v1 from its 'Notice text' card and add 'Collection sites: CIT campus, Coimbatore; SRIB lab, Bengaluru.'",
     "Purposes: the same 9 purposes shown on v1"],
    [
        s("Open project 'UAT Study 01' and click 'New notice' (DPO only).",
          "Dialog 'New notice' opens: 'Every Rule 3 element is required before it can be published.' It says 'The notice code is generated for you' with a link 'Set the code myself'."),
        s("Click 'Set the code myself' and type NTC-UAT-STUDY-01-2026 in 'Notice code'. Fill 'DPO contact', 'Applies to', the three URLs, 'Language' and 'Notice text' from the test data. Click 'Create notice'.",
          "Toast 'Notice NTC-UAT-STUDY-01-2026 created' with 'Attach purposes, then approve the text and publish.' The Notices card lists 'NTC-UAT-STUDY-01-2026 v2' as 'Draft' and v1 as 'Published'."),
        s("Open v2. In 'Purposes' click 'Attach a purpose' (or 'Manage').",
          "Dialog 'Purposes on this notice' opens with 'Attach a purpose' (only active purposes listed), a 'Cannot be refused' tick box, and 'Attach'."),
        s("Attach each of the 9 purposes that v1 carries, one by one: choose it and click 'Attach'. The dialog stays open after each - there is no 'Done' button - so close it with the × at its top right when all 9 are attached.",
          "Toast 'Purpose attached' each time; the Purposes card lists 9 purposes, all 'Active'."),
        s("In 'Legal approval, per language' click 'Approve' on the English row.",
          "Toast 'english approved'. The checklist reads 'This notice is complete and ready to publish.' and the 'Sites' stat shows 2."),
        s("Click 'Publish this notice'.",
          "A box 'Publishing is not reversible' explains the text is hashed and frozen and the recipient list is generated from the project's active sites; buttons 'Publish and freeze' and 'Cancel'."),
        s("Click 'Publish and freeze'.",
          "Toast 'Notice published' says 'The text and its hash are frozen. Edits now require a new version.' Title 'NTC-UAT-STUDY-01-2026 · version 2', badge 'Published'; 'Recipients' now names CIT and SE."),
        s("Return to the project (breadcrumb 'UAT Study 01') and look at the 'Notices' card.",
          "v2 shows 'Published'; v1 shows 'Superseded' - only one notice on the project is ever 'Published'. Opening v1 still shows its original frozen text."),
    ],
    "The change is made as version 2 with the same code; publishing it supersedes version 1, which stays readable and unchanged."))

# ---------------------------------------------------------------- 17
cases.append(case(
    17, "A consent link cannot be created without a future expiry",
    "Create consent link - validation", "DCO", "High", "Negative",
    ["PRJ-14 completed (CIT site on UAT Study 01 owned by Arun Shetty, no live link).", DCO],
    ["Expires at: empty, then yesterday's date/time", "Maximum uses: 0"],
    [
        s("Click 'Collection sites' in the sidebar.",
          "The list shows 'CIT' for project 'UAT Study 01'. The 'SE' site of UAT Study 01 is NOT listed for the DCO."),
        s("Click 'UAT Study 01' on the CIT row.",
          "The project page opens on its 'Consent' tab. The CIT site row shows a 'Create link' button."),
        s("Click 'Create link'.",
          "Dialog 'Consent link for CIT' opens: 'The token is shown once and cannot be retrieved again.' Fields 'Expires at' (required; hint 'Required, with no default and no maximum...'), 'Maximum uses', 'Field agent reference'. 'Expires at' is empty - there is no default."),
        s("Leave 'Expires at' empty and click 'Create link'.",
          "The dialog stays open with 'The expiry is required' under 'Expires at'. No link is created."),
        s("Set 'Expires at' to yesterday and click 'Create link'.",
          "'The expiry has to be in the future' is shown. No link is created."),
        s("Set 'Expires at' to 7 days ahead, enter 0 in 'Maximum uses' and click 'Create link'.",
          "'A link that can be used zero times is not worth minting' is shown under 'Maximum uses'."),
        s("Click 'Cancel'.",
          "The dialog closes; the CIT row still shows 'Create link' and no active link count."),
    ],
    "No consent link can be minted without an expiry in the future (and a use limit, if given, of at least 1)."))

# ---------------------------------------------------------------- 18
cases.append(case(
    18, "DCO creates a consent link for the site, copies it, and it opens on the portal",
    "Create and copy consent link", "DCO", "High", "Positive",
    ["PRJ-17 completed.", DCO, "PRJ-16 completed is recommended so the link serves notice v2."],
    ["Expires at: 7 days from now, 18:00", "Maximum uses: 50", "Field agent reference: UAT-AGENT-01"],
    [
        s("On project 'UAT Study 01' click the 'Consent' tab, then 'Create link' on the CIT row.",
          "Dialog 'Consent link for CIT' opens."),
        s("Fill in the test data and click 'Create link'.",
          "Toast 'Consent link created'. The dialog now shows a yellow box titled 'Copy this now' and the full URL."),
        s("Read the URL.",
          "It begins with the data-principal portal address http://localhost:3001/c/ followed by a long token - NOT http://localhost:3000."),
        s("Click 'Copy link'.",
          "The button changes to 'Copied' for a moment. Paste into a notepad to confirm the same URL."),
        s("Click 'Done'.",
          "The dialog closes. The CIT row now shows '1 active link(s)', 'Copy link' and 'Replace link' instead of 'Create link' (refresh the page if the count has not updated)."),
        s("Look at the 'Consent links' card under 'Collection sites'.",
          "A row 'CIT' with the badge 'Active' and '0 of 50 used · expires <date/time>'."),
        s("Click 'Copy link' on the CIT row.",
          "It shows 'Copied'; the pasted URL is the same one you saved."),
        s("Open the saved URL in a private/incognito browser window.",
          "The portal opens a consent page with 'UAT Study 01' and 'CIT' in the top banner and the steps 'Your details', 'Confirm', 'The notice', 'Done', asking for a 'Mobile number'. Close the window without continuing."),
    ],
    "An active link is minted with the chosen expiry and limit, its URL points at the portal (port 3001), it can be copied again later, and it opens the consent page for the right project and site."))

# ---------------------------------------------------------------- 19
cases.append(case(
    19, "DCO replaces a consent link; the old URL stops working and the new one works",
    "Replace consent link", "DCO", "High", "Positive",
    ["PRJ-18 completed (URL saved in a notepad as 'old URL').", DCO],
    ["Site: CIT (UAT Study 01)"],
    [
        s("Click 'Consent links' in the sidebar.",
          "Page 'Consent links' opens with the info box 'The link is a credential' and a table with Site, Project, Status, Uses, Registrations, Expires, Actions."),
        s("Set the 'Status' filter to 'Active' and find the CIT row for UAT Study 01.",
          "The row shows 'Active', 'Copy link', 'Replace' and 'Revoke'."),
        s("Click 'Replace' on that row.",
          "Dialog 'Replace the link for CIT?' opens: 'The old link stops working immediately. The new URL is shown once.', a yellow box 'This revokes the current link', Site/Expires/Uses, and 'The replacement inherits the same expiry and use limit...'. Buttons 'Cancel' and 'Revoke and replace'."),
        s("Click 'Revoke and replace'.",
          "The dialog changes to 'Copy this now' with a yellow box 'This is the only time you will see this' and the new URL (starting http://localhost:3001/c/)."),
        s("Click 'Copy link', save it as 'new URL', then click 'I have copied it'.",
          "The dialog closes."),
        s("Set 'Status' to 'All statuses' and look at the CIT rows.",
          "The old link shows 'Revoked' (with 'New link' offered instead of Replace); a new link shows 'Active' with the same expiry and use limit."),
        s("Open the old URL in a private window.",
          "The portal shows 'This link is not valid' and 'It may have expired, been withdrawn, or been mistyped. Please ask the person who gave it to you for a current one.' No project or notice details are shown."),
        s("Open the new URL in a private window.",
          "The consent page for 'UAT Study 01' / 'CIT' opens at 'Your details'."),
    ],
    "Replacing revokes the old link and issues a new one in one step; only the new URL works on the portal."))

# ---------------------------------------------------------------- 20
cases.append(case(
    20, "A revoked consent link shows 'This link is not valid' on the portal",
    "Revoke consent link", "RCO", "High", "Negative",
    ["PRJ-15 completed (SE site on UAT Study 01 owned by Meera Iyer).", RCO],
    ["Site: SE (UAT Study 01)", "Expires at: 3 days from now", "Maximum uses: (blank = unlimited)"],
    [
        s("Open 'Collection sites', click 'UAT Study 01' on the SE row, and click 'Create link' on SE.",
          "Dialog 'Consent link for SE' opens."),
        s("Set 'Expires at' and click 'Create link'. Copy the URL, then click 'Done'.",
          "Toast 'Consent link created'; the URL starts http://localhost:3001/c/. The SE row shows 'Copy link' and 'Replace link'."),
        s("Open the URL in a private window.",
          "The consent page for 'UAT Study 01' / 'SE' opens. Close it."),
        s("Click 'Consent links' in the sidebar and find the SE row for UAT Study 01.",
          "The row shows 'Active' with 'Copy link', 'Replace' and 'Revoke'. Meera does not see the CIT link of UAT Study 01."),
        s("Click 'Revoke'.",
          "Toast 'Link revoked' says 'SE no longer resolves for anyone holding it.' The status changes to 'Revoked'; 'Copy link', 'Replace' and 'Revoke' disappear and 'New link' is offered."),
        s("Open the same URL again in a private window.",
          "The portal shows only 'This link is not valid' with 'It may have expired, been withdrawn, or been mistyped...'. It does not say the link was revoked and shows no project or notice."),
    ],
    "A revoked link no longer opens the consent flow and the portal gives only the neutral 'This link is not valid' message."))

# ---------------------------------------------------------------- 21
cases.append(case(
    21, "An expired consent link shows 'This link is not valid' on the portal",
    "Consent link expiry", "RCO", "Medium", "Negative",
    ["PRJ-20 completed (SE link revoked, no live link on SE).", RCO],
    ["Expires at: about 3 minutes from now"],
    [
        s("On 'Consent links', click 'New link' on the revoked SE row.",
          "Dialog 'New link for SE' opens: 'The URL is shown once and then only its digest is kept. Copy it before closing.'"),
        s("Set 'Expires at' to about 3 minutes from now and click 'Create link'.",
          "Toast 'Consent link created' and the URL is shown under 'Copy this now'."),
        s("Click 'Copy link', save the URL, click 'Done', and open the URL in a private window straight away.",
          "Before the expiry time, the consent page for 'UAT Study 01' / 'SE' opens. Close it."),
        s("Wait until the expiry time has passed (about 4 minutes), then open the same URL again.",
          "The portal shows 'This link is not valid' with 'It may have expired, been withdrawn, or been mistyped...'. It does not say it expired."),
        s("Back in the console, refresh 'Consent links'.",
          "The link row's 'Expires' time is in the past. Its status turns to 'Expired' when the platform's periodic clean-up runs (every 15 minutes where scheduled); until then it may still read 'Active' - that is not a failure, the portal already refuses it."),
    ],
    "The portal refuses the link as soon as its expiry time passes, with the same neutral 'This link is not valid' message."))

# ---------------------------------------------------------------- 22
cases.append(case(
    22, "Publishing a replacement notice under a new code keeps one notice in force, and the consent links follow it",
    "One published notice per project; links move to the new notice", "DPO", "High", "Positive",
    ["PRJ-16 and PRJ-19 completed (NTC-UAT-STUDY-01-2026 v2 is published; the CIT link saved as 'new URL' is active).", DPO,
     "The test coordinator relays one-time codes, and Anjali Verma (+91 90000 00001) has a portal account."],
    ["Notice to copy: NTC-GAIT-2026 v1 — Gait Identification Study 2026", "A code that belongs to another project: NTC-GAIT-2026"],
    [
        s("Open project 'UAT Study 01', click the 'Setup' tab and in the 'Notices' card click 'Copy an existing notice', choose 'NTC-GAIT-2026 v1 — Gait Identification Study 2026' and click 'Copy into this project'.",
          "A toast 'Copied into NTC-UAT-STUDY-01-2026-2' (the code may end differently) says it is a fresh draft. The 'Notices' card now lists it as 'Draft' beside v2 'Published'."),
        s("Open the new notice. In 'Legal approval, per language' click 'Approve' on each language row.",
          "Each row shows 'Approved'. The 'Publication checklist' reads 'This notice is complete and ready to publish.'"),
        s("Click 'Publish this notice', then 'Publish and freeze'.",
          "Toast 'Notice published'. The notice's badge reads 'Published'."),
        s("Return to the project and look at the 'Notices' card.",
          "The new notice shows 'Published'. NTC-UAT-STUDY-01-2026 v2 now shows 'Superseded', and v1 'Superseded'. Only one notice on the project is 'Published'."),
        s("In a private window open the CIT 'new URL' saved in PRJ-19. Send a code to +91 90000 00001, type the relayed code and click 'Verify and continue'.",
          "The link still works - it is not 'This link is not valid'. The notice shown is the new one's wording (the Gait notice, starting 'NOTICE UNDER SECTION 5'), not v2's. Close the window without recording a choice."),
        s("Back in the console, on 'UAT Study 01' click 'New notice', then 'Set the code myself', type NTC-GAIT-2026 in 'Notice code', fill the other required fields and click 'Create notice'.",
          "The notice is not created. Under 'Notice code' a message reads 'NTC-GAIT-2026 is another project's notice code. Leave the code empty to have one generated, or use this project's own.' Close the dialog."),
    ],
    "Publishing a notice under a new code supersedes the one in force, so a project never has two published notices; an existing consent link keeps working and shows the notice now in force; another project's notice code cannot be used."))

# ---------------------------------------------------------------- 23
cases.append(case(
    23, "DPO writes a notice template before any project exists, finds it under Templates and edits it",
    "Notice templates - create, purposes, languages, edit (new in this release)", "DPO", "High", "Positive",
    [DPO, "The seed has no notice templates: this case makes the first one. The register holds the seeded purposes 'Gait model training' (PUR-GAIT-TRAIN) and 'Recording quality assurance' (PUR-QUALITY), both active."],
    ["Template name: UAT Gait template 01; after editing: UAT Gait template 01 (adults)",
     "DPO contact: dpo@example.org", "Applies to: Data subjects — people outside the organisation",
     "Note for the collector: Read the notice aloud if the person asks.",
     "Withdraw consent URL: https://example.org/withdraw", "Exercise rights URL: https://example.org/rights",
     "Board complaint URL: https://example.org/complain",
     "Language: English; Notice text: 'UAT template notice. We record gait video and facial images to train and check gait models. Contact the Privacy Office at dpo@example.org with any question.'",
     "Purposes: Gait model training (Mandatory ticked), Recording quality assurance (Mandatory not ticked)",
     "Hindi text: 'यह UAT टेम्पलेट सूचना है। (UAT template notice - Hindi)'",
     "Template ID: minted by the system as TPL- and four digits (for example TPL-0001). Write down the one you get; PRJ-24 and PRJ-25 use it."],
    [
        s("Click 'Dashboard' in the sidebar and look at the buttons at the top right of the page.",
          "Two buttons: 'Log an incident' (highlighted) and beside it 'New notice template'."),
        s("Click 'New notice template'.",
          "A dialog 'New notice template' opens: 'A notice written before any project exists. A project uses it by its ID, which makes that project's own draft notice from it.' Fields: 'Template name', 'DPO contact', 'Applies to' (showing 'Not decided yet'), 'Note for the collector', 'Withdraw consent URL', 'Exercise rights URL', 'Board complaint URL', then 'Language' (showing 'English') and 'Notice text'. Buttons 'Cancel' and 'Create template'. There is no project field and no notice-code field."),
        s("Fill every field from the test data (choose 'Data subjects — people outside the organisation' in 'Applies to', leave 'Language' on 'English' and paste the English text) and click 'Create template'.",
          "The dialog closes and a green toast 'Template TPL-<number> created' says 'Add its purposes and languages, then give the ID to the study's R&D User.' The template's own page opens: small heading 'Notice template', title 'UAT Gait template 01', the badge 'Active' and the buttons 'Edit details' and 'Retire'."),
        s("Read the 'Template ID' card at the top, then click 'Copy ID'.",
          "It shows the ID in large type (TPL- and four digits) with 'Give this to the study's R&D User. On their project they choose Use a notice template and enter it; the project gets its own draft notice from it, to approve and publish.' After 'Copy ID' a toast '<ID> copied' appears. Write the ID down."),
        s("Read the 'Details' card.",
          "'Written by Priya Menon on <date and time> · last changed <date and time>', and the values you typed under 'Applies to', 'DPO contact', 'Withdraw consent', 'Exercise rights', 'Board complaint' and 'Note for the collector'."),
        s("In the 'Purposes · 0' card ('No purposes yet.'), open 'Add a purpose', choose 'Gait model training (PUR-GAIT-TRAIN)', tick 'Mandatory' and click 'Add'.",
          "'Add' is greyed out until a purpose is chosen. After it, the card title reads 'Purposes · 1' and lists 'Gait model training PUR-GAIT-TRAIN' with 'Mandatory' and its data categories. A draft purpose would be offered too, ending ' - draft'."),
        s("Choose 'Recording quality assurance (PUR-QUALITY)', leave 'Mandatory' unticked and click 'Add'.",
          "'Purposes · 2'; the new line reads 'Optional'. 'Gait model training' is no longer offered in 'Add a purpose'."),
        s("In the 'Text · 1 language' card (one row 'English' with 'Priya Menon · <time>', 'Edit' and a bin icon), click 'Add a language'.",
          "A dialog 'Add a language' opens with 'Language' (English is not offered, it is already there) and 'Notice text'. 'Save text' is greyed out until text is typed."),
        s("Choose 'Hindi', paste the Hindi text and click 'Save text'.",
          "A toast 'Text saved'. The card reads 'Text · 2 languages' with rows 'English' and 'Hindi'. Nothing on the page asks for a legal approval: that is given on each project's notice made from the template."),
        s("Click 'Notice templates' at the top of the page.",
          "The 'Notices' page opens on its 'Templates' tab (beside 'Project notices'), with a blue note 'Write a notice here before the project exists...', 'Search' ('ID or name'), a 'Status' filter on 'Active', and a table ID, Name, Status, Purposes, Languages, Used by, Updated. Your template's row reads 'UAT Gait template 01', 'Active', 2, 2, '0 projects'. 'New notice template' is at the top right; click 'Project notices' and it is still there."),
        s("Click 'Templates', then your template's ID. Click 'Edit details', change 'Template name' to 'UAT Gait template 01 (adults)' and click 'Save changes'.",
          "A dialog 'Edit the template' opens with the same fields except 'Language' and 'Notice text' (those are edited on the page). After saving, the toast 'Template saved' appears and the title reads 'UAT Gait template 01 (adults)'; 'last changed' shows the new time. Purposes and text are unchanged."),
    ],
    "The DPO can write a notice with no project under a system-minted TPL- ID, give it purposes from the register and text in two languages with no approval step, find it under the Templates tab, and edit it in place."))

# ---------------------------------------------------------------- 24
cases.append(case(
    24, "R&D User makes a new project's draft notice from a template with 'Use a notice template'",
    "Notice templates - use on a project (new in this release)", "R&D User, DPO", "High", "Positive",
    ["PRJ-23 completed (template 'UAT Gait template 01 (adults)' is Active; you have its ID).", RND,
     "Priya Menon (dpo@cmp.local) available for the second half."],
    ["Project name: UAT Study 03", "Description: Template-notice UAT project.", "Processor: SEED",
     "Template ID: the one from PRJ-23, typed in lower case (e.g. tpl-0001)", "A made-up ID: TPL-9999",
     "Expected notice code: NTC-UAT-STUDY-03-2026 (a suffix such as -2 is added if that code exists from an earlier run)",
     "Sentence added to the template afterwards: 'Template change after use.'"],
    [
        s("On the 'Dashboard' click 'Register a project' at the top right (the R&D User's only button there). Enter the name and description, tick 'SEED' and click 'Register project'.",
          "The same 'Register a project' dialog as on the Projects page. A toast 'Project registered' appears and the 'UAT Study 03' page opens straight away with status 'In Draft'."),
        s("Click the 'Setup' tab. In the 'Notices' card ('No notice yet') click 'Use a notice template'.",
          "The card offers 'Upload a notice document', 'Copy an existing notice' and 'Use a notice template'. A dialog 'Use a notice template' opens: 'A notice the Privacy Office wrote ahead of the project. Enter the ID they gave you.' with 'Template ID' (hint 'The ID the Privacy Office gave you, like TPL-0007.'), 'Look up', 'Cancel' and a greyed-out 'Make this project's notice from it'."),
        s("Type TPL-9999 in 'Template ID' and click 'Look up'.",
          "A yellow box: 'There is no template TPL-9999. Check the ID with the Privacy Office.' 'Make this project's notice from it' stays greyed out."),
        s("Clear the box, type the PRJ-23 ID in lower case and click 'Look up'.",
          "It is shown in capitals and found. A box shows '<ID> · UAT Gait template 01 (adults)', 'For Data subjects — people outside the organisation · 2 languages (english, hindi)', and the purposes 'Gait model training · mandatory' and 'Recording quality assurance · optional'. Below: 'This project gets its own draft notice: the wording, the purposes and every language are copied, under the project's own notice code. Nothing is approved yet, and a later change to the template does not reach it.' The 'Make this project's notice from it' button is now clickable."),
        s("Click 'Make this project's notice from it'.",
          "A toast 'NTC-UAT-STUDY-03-2026 made from <ID>' says 'A draft. Approve each language, then publish it.' The notice page opens: 'NTC-UAT-STUDY-03-2026 · version 1', badge 'Draft'."),
        s("Read the 'Rule 3 elements' card.",
          "'Withdraw consent', 'Exercise rights', 'Board complaint' and 'DPO contact' show the template's values. A line 'Made from' reads 'Template <ID>' with 'A copy: later changes to the template do not reach this notice.'"),
        s("Look at the 'Purposes', 'Legal approval, per language' and 'Publication checklist' cards.",
          "Purposes: 'Gait model training' and 'Recording quality assurance', both 'Active'. Legal approval: English and Hindi rows, each 'Not legally approved'. The checklist lists 'the english text is not legally approved' and 'the hindi text is not legally approved'. As for any draft, there is NO 'Approve' and NO 'Publish this notice' for the R&D User."),
        s("Click 'UAT Study 03' at the top of the notice page to return to the project, open the 'Setup' tab and look at the 'Notices' card and 'What happens next'.",
          "The card lists 'NTC-UAT-STUDY-03-2026 v1' with '2 purposes · 2 language(s)' and 'Draft'. Under 'Moves the project to Pending Approval' the notice lines are gone; only 'No approval with a proof file' remains. From here the project goes on as in PRJ-08 to PRJ-12."),
        s("Sign out and sign in as dpo@cmp.local. Click 'Notices', then the 'Templates' tab, and open the template.",
          "The list row now says '1 project' under 'Used by'. On the template page 'Used by · 1' lists 'NTC-UAT-STUDY-03-2026 v1', 'UAT Study 03' and 'Draft'. The template itself is unchanged: badge 'Active', 'Purposes · 2', 'Text · 2 languages'."),
        s("Click 'Edit details' and read the top of the dialog, then click 'Cancel'.",
          "A blue note: '1 project notice was made from this template. They are copies and keep what they were made with; changes here reach only notices made from now on.'"),
        s("In 'Text · 2 languages' click 'Edit' on the 'English' row. In 'Edit the text' add the sentence from the test data at the end and click 'Save text'.",
          "A toast 'Text saved'; the template's English text now ends with the new sentence."),
        s("In 'Used by' click 'NTC-UAT-STUDY-03-2026 v1' and read its 'Notice text' card.",
          "The project's notice still has the English text as it was copied, WITHOUT 'Template change after use.' It is still 'Draft' and its English row still reads 'Not legally approved'."),
    ],
    "'Use a notice template' looks the ID up first, then makes the project's own draft notice under the project's code with the template's links, purposes and both languages, nothing approved; the notice names the template it came from, the template is listed as used but otherwise untouched, and a later edit to the template does not reach the notice."))

# ---------------------------------------------------------------- 25
cases.append(case(
    25, "Only the DPO writes notice templates; an incomplete one is refused and a retired one cannot be used",
    "Notice templates - who, validation, retire (new in this release)", "R&D User, DCO, DPO", "Medium", "Negative",
    ["PRJ-23 and PRJ-24 completed.", RND,
     "Arun Shetty (dco@cmp.local) and Priya Menon (dpo@cmp.local) available."],
    ["Template ID: the one from PRJ-23", "Incomplete template: name 'UAT Bad template', DPO contact dpo@example.org, Withdraw consent URL example.org/withdraw (no https://), the other two URLs as in PRJ-23"],
    [
        s("As Kavya Rao look at the top right of the 'Dashboard', then click 'Notices' in the sidebar.",
          "The dashboard offers only 'Register a project' - no 'New notice template'. The 'Notices' page has no 'New notice template' button and no 'Project notices' / 'Templates' tabs: only the list of project notices."),
        s("Sign out and sign in as dco@cmp.local. Open project 'UAT Study 01' (Projects > search > click the name) and click the 'Setup' tab.",
          "The 'Notices' card lists the project's notices but offers none of 'Upload a notice document', 'Copy an existing notice' or 'Use a notice template': bringing a notice is for the project's R&D User and the DPO."),
        s("Sign out and sign in as dpo@cmp.local. Click 'Notices', then 'New notice template', and click 'Create template' with every field empty.",
          "The dialog stays open with messages under the fields: 'Give it a name the list can show - what kind of study it is for', 'State how the DPO can be reached', 'The withdrawal URL is required', 'The rights URL is required' and 'The Board complaint URL is required'."),
        s("Fill the fields from the 'Incomplete template' test data and click 'Create template'.",
          "Under 'Withdraw consent URL': 'The withdrawal URL has to start with http:// or https://'. No template is created."),
        s("Click 'Cancel'. On the 'Templates' tab type 'UAT Bad' in 'Search' (the list updates as you type).",
          "'No templates match'. Clear the search."),
        s("Open the PRJ-23 template and click 'Retire'.",
          "A toast '<ID> retired' says 'It can no longer be attached to a project.' The badge reads 'Retired', the button now reads 'Bring back', and the 'Template ID' card says 'Retired: it can no longer be used. Notices already made from it are unaffected. Bring it back to use it again.' 'Used by · 1' still lists the UAT Study 03 notice."),
        s("Click 'Notice templates'. With 'Status' on 'Active' look for the template, then set 'Status' to 'Retired'.",
          "It is not in the 'Active' list; under 'Retired' it is listed with the badge 'Retired'."),
        s("Sign out and sign in as rnd@cmp.local. Open 'UAT Study 03', click 'Setup', then 'Use a notice template' at the top of the 'Notices' card. Type the ID and click 'Look up'.",
          "The template is found and shown, with a yellow box 'The Privacy Office has retired this template. Ask them which one to use instead.' 'Make this project's notice from it' stays greyed out. Click 'Cancel': the Notices card still shows only NTC-UAT-STUDY-03-2026 v1."),
        s("Restore: sign in as dpo@cmp.local, open the template and click 'Bring back'.",
          "A toast '<ID> is back in use'; the badge reads 'Active' again."),
    ],
    "Only the DPO can create or change a template; a template without a name, contact or valid links is refused field by field and nothing is saved; a retired template is found by ID but cannot be used on a project, and the notice already made from it is unaffected."))

with open(
    str(__import__("pathlib").Path(__file__).with_name("PRJ.json")),
    "w", encoding="utf-8",
) as f:
    json.dump(cases, f, ensure_ascii=False, indent=2)
print(len(cases), [len(c["steps"]) for c in cases])
