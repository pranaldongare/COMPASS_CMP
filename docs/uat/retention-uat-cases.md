# UAT: retention reviews (ADR 0047)

On a test system, shorten a test purpose's periods to make a review fall due
at once: a consent validity of a day, or a retention period of a day on a
withdrawn consent. Then, as the DPO or Legal, click *Look again now* on
*Retention* rather than wait for the night. Use a processor whose respondent
has no console login for the link cases, and read the emails in the mail
catcher.

| ID | Who | Steps | Expected |
|---|---|---|---|
| RT-01 | DCO, R&D User, Administrator, Management | Open `/retention` | Not there for them; only the DPO and Legal have the register |
| RT-02 | DPO | A purpose whose consents run out within 90 days; *Look again now* | A *Consent validity* review for the project and month, with its people counted; the DCO Admin is asked at once and emailed |
| RT-03 | DCO Admin | *Retention actions*, open it, *Send the answer* with nothing chosen | "Choose whether to invite these people to consent again" |
| RT-04 | DCO Admin | Choose *Yes, invite them*, send | Answered; the DPO is emailed |
| RT-05 | DPO | Open the review, *Accept* | Asked first: each person is sent the consent link; on yes, every person gets the link and the review says *Invited* |
| RT-06 | DPO | The same on a closed project | Nobody is asked to invite them again |
| RT-07 | DPO | A withdrawn consent whose retention has passed; *Look again now* | A *Data retention* review; the owner is asked in the console, the processor by an emailed link |
| RT-08 | DCO Admin | Answer *Anonymised* with no reason | Refused: a reason is needed |
| RT-09 | DCO Admin | Answer *Kept* with a reason and today's date | Refused: a date after today |
| RT-10 | DPO | *Send back* the owner's answer with what is missing | The owner is emailed the reason; it shows above their form; they answer again |
| RT-11 | Processor (no login) | Open the emailed link | The reference, the processor, where the code goes (masked); nothing else until the code |
| RT-12 | Processor | *Send code*, type it, *Open the review* | The project, purpose, how many people and the dates; no person named |
| RT-13 | Processor | Answer *Not held*, send | "Your answer is with the Privacy Office"; the DPO is emailed |
| RT-14 | Anyone | Change one letter of the link | "This link is not valid", the same as for every link |
| RT-15 | DPO | *Close the review* with an answer not accepted | Not offered: says how many are not settled |
| RT-16 | DPO | Accept the last answer, *Close the review* | Closed; the *Certificate* card appears |
| RT-17 | DPO | *PDF* and *CSV* | The certificate: consents by number, every answer with its reason, who accepted, who closed; the trail shows each download |
| RT-18 | DPO | Place a legal hold on a person in a review; *Look again now* | The person shows *Legal hold* and is not counted; released, they are counted again |
| RT-19 | Person | Their data is due to be erased within 48 hours, the purpose's *Tell each person before their data is erased* on | One email and text saying so; none when it is off |
| RT-20 | DPO | Move an action's date into the past by waiting, or in the test database; *Look again now* | The one asked is reminded once; 14 days later the officers are told once |
| RT-21 | DPO | *Settings*: reminder days `0` | Refused; `60, 14` saves and is on the trail |
| RT-22 | Management | Analytics | *Retention*: reviews opened, closed, on time, answers overdue, data kept past retention |
| RT-23 | Auditor | Audit trail | Each step against the review: asked, answered, accepted, sent back, set aside, invited, closed, certificate downloaded; never a person |
| RT-24 | DCO Admin | Before answering, attach a `.txt` deletion log in *Proof (optional)*, send *Erased* | Answered; the DPO sees *Proof* on the answer with its SHA-256, downloads the same file; the trail shows it added and downloaded |
| RT-25 | DCO Admin | Attach a `.sh` or a file over 25 MB | Refused, saying which files are allowed |
| RT-26 | Processor (link) | Attach a PDF with the answer | The DPO downloads it from the review |
| RT-27 | DPO | Close the review, *CSV* certificate | Each answer's proof by name and SHA-256 |
