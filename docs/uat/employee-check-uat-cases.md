# UAT: the employee check (VerifyEmail, ADR 0046)

On a test system, point the check at the development stand-in
(`http://localhost:8000/dev/verify-email`), or at the organisation's own
VerifyEmail with test addresses agreed with its team. With the stand-in, an
address whose local part starts with `left` is a leaver, `unknown` is not
known, and `down` gets no answer.

| ID | Who | Steps | Expected |
|---|---|---|---|
| EC-01 | DPO, Management | Open `/employee-check` | Not there for them (403); only the administrator has the page |
| EC-02 | Administrator | Employee check: address ending in `/VerifyEmail`, Save | Refused: enter it without /VerifyEmail |
| EC-03 | Administrator | Set the address and a key, tick *Check employees at sign-in*, Save | Saved; the key field is empty again and says a key is stored; the trail says the address and key changed, never what they are |
| EC-04 | Administrator | Add `company.example`, then `someone@company.example` | The first is added (lower case); the second is refused |
| EC-05 | Administrator | *Check an address* with an active and a leaver's address | "An active employee" / "Not an active employee"; nothing recorded on either account |
| EC-06 | Staff on a company domain, active | Sign in to the console | Code sent; signs in |
| EC-07 | Staff on a company domain, leaver | Sign in to the console | After the password: "Your account cannot sign in: the organisation does not list you as an active employee"; no code is sent |
| EC-08 | Staff on a company domain | VerifyEmail switched to an address that does not answer; sign in | "We could not confirm your employment just now"; Health shows *Employee checks not answered* |
| EC-09 | Administrator | Same outage; sign in | Signs in: the administrator is never checked |
| EC-10 | Staff on another domain | *Let staff on other domains…* ticked; sign in | Signs in, not checked |
| EC-11 | Staff on another domain | Untick it, Save; sign in | "its email is not on one of the organisation's domains" |
| EC-12 | Administrator | Untick it with no domains listed | Refused: add the organisation's domains first |
| EC-13 | Person with a company email, leaver | Sign in to the portal with a code | Signs in as normal; sees and can withdraw their consents and make requests |
| EC-14 | Same person | Open an employee-only consent link | "This link is for the organisation's current employees…"; other links work |
| EC-15 | Person with a company email | VerifyEmail not answering; sign in to the portal | Signs in as normal; employee links still open |
| EC-16 | DPO | Assign a breach ticket to an address on a domain just added on the page | Accepted as internal (the same list) |
| EC-17 | Auditor | Audit trail, *Employee check* events | Each check: the account, flow and result; never the email address |
